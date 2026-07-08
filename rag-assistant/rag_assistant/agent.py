"""
Agent 决策循环
LLM 先看消息 → 决定：直接回答、查知识库、搜网页 → Agent 执行 → 返回
"""
import logging
import os
import re
import json
from typing import Optional

from .llm_client import LLMClient
from .rag_wrapper import RAGWrapper
from .memory import Memory
from .search import WebSearch

logger = logging.getLogger(__name__)

_ACTION_PATTERN = re.compile(r"<<(\w+)(?:\s+(.+?))?>>", re.DOTALL)


class Agent:
    """智能体主循环"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.data_dir = self.config.get("data_dir", "data")
        self.session_id = self.config.get("session_id", "default")
        self.rag = RAGWrapper(self.config)
        self.llm = LLMClient(self.config)
        self.memory = Memory(self.data_dir)
        self.search = WebSearch(self.config)

    def _system_prompt(self) -> str:
        return """你是 RAG 知识库助手。你可以使用以下动作：

## 知识库查询
<<ACTION type="query" entities="实体1,实体2" attrs="属性" rel="关系词" kb="知识库名（可选）">>
- entities：问题中的核心实体（逗号分隔）
- attrs：查询的属性/维度
- rel：实体间的关系（多个实体时填写）
Agent 会自动将 entities × attrs 穷举组合后查询。
不要用 question 参数，不会生效。

## 联网搜索
<<ACTION type="search" query="搜索词">>

## 导入入库
<<ACTION type="import" content="入库的完整文本内容">
  或
<<ACTION type="import" path="MANIFEST">
- **用户说"入库"且有"已上传文件到服务器"的通知 → 用 path="MANIFEST"**，系统自动处理所有待入库文件
- **用户说了"把这些入库"等引用对话内容 → 用 content 参数**，把要入库的完整文本写在 content 里
- **绝对不要自己编造文件路径！不要写具体的文件路径，用 path="MANIFEST" 让系统处理**

## 规则
- 闲聊/打招呼 → 直接回答
- 知识库查询 → 用 entities+attrs 标注成分，不要自己创造
- 入库 → 用户明确要求时才用
"""

    def chat(self, message: str, stream: bool = False) -> dict:
        """处理一条用户消息（带 LLM 自修正循环）"""
        self.memory.append_short_term(self.session_id, "user", message)

        # 自修正循环：LLM 输出 → Agent 校验 → 不通过则反馈给 LLM 重试
        decision, action = self._decide_with_retry(message, max_retries=2)

        reply = decision.get("text", "")

        # 导入动作（独立执行，不需要第二轮 LLM）
        if action and action["type"] == "import":
            result = self._exec_import(action, message)
            self.memory.append_short_term(self.session_id, "assistant", result.get("text", ""))
            self.memory.record_habit(message, is_rag=False, is_chat=False, is_import=True)
            result["success"] = True
            return result

        # 查询/搜索动作（执行后第二轮 LLM 生成回答）
        if action and action["type"] in ("query", "search"):
            context = self._exec_query(action, message)
            result = self._second_pass(message, context, action)
            reply2 = result.get("text", "")
            if reply2:
                self.memory.append_short_term(self.session_id, "assistant", reply2)
            self._compress_if_needed()
            self.memory.record_habit(message, is_rag=action["type"] == "query",
                                     is_chat=action["type"] != "query", is_import=False)
            result["success"] = True
            return result

        # 直接回答（无动作）
        if reply:
            self.memory.append_short_term(self.session_id, "assistant", reply)
        self._compress_if_needed()
        self.memory.record_habit(message, is_rag=False, is_chat=True, is_import=False)
        decision["success"] = True
        return decision

    def _decide_with_retry(self, message: str, max_retries: int = 5) -> tuple:
        """LLM 决策 + 自修正循环"""
        msgs = self._build_first_pass_messages(message)

        for attempt in range(max_retries + 1):
            resp = self.llm.chat(msgs, stream=False)
            reply = resp.get("text", "")
            action, parse_err = self._parse_action(reply)

            # 完全没动作（没有 <<ACTION 标记）→ 正常聊天
            if not action and not parse_err:
                return resp, None

            # 有动作但格式错误 → 反馈给 LLM 重试
            if parse_err:
                logger.info(f"LLM 动作解析失败 (attempt {attempt+1}): {parse_err}")
                msgs.append({"role": "assistant", "content": reply})
                msgs.append({"role": "user", "content": 
                    f"【修正提醒】\n"
                    f"- 问题：{parse_err}\n"
                    f"- 要求：修正后再输出，或直接回答用户不要输出指令"})
                continue

            # 校验动作合法性
            rejection = self._validate_action(action, message)
            if not rejection:
                return resp, action

            # 动作被拒绝 → 结构化反馈给 LLM 重试
            logger.info(f"LLM 动作被拒绝 (attempt {attempt+1}): {rejection}")
            msgs.append({"role": "assistant", "content": reply})
            msgs.append({"role": "user", "content": 
                f"【修正提醒】\n"
                f"- 问题：{rejection}\n"
                f"- 要求：修正后重新输出，或直接回答用户\n"
                f"- 注意：指令必须独占一行，不要和文字混在一起"})

        # 重试用完 → 清理上下文，给 LLM 最后一次机会
        logger.warning("LLM 重试耗尽，清理上下文重新回答")
        return self.llm.chat([
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": message},
        ]), None

    def _validate_action(self, action: dict, original_msg: str) -> Optional[str]:
        """校验动作是否合法，不合法返回明确的拒绝原因"""
        atype = action.get("type", "")

        if atype not in ("query", "search", "import"):
            return f"type 必须是 query / search / import 之一，收到: {atype}"

        if atype == "query":
            if not action.get("entities") and not action.get("attrs"):
                return "query 必须用 entities 和 attrs 参数标注成分，不要用 question。请标注出实体和属性后重试"
            if not action.get("entities"):
                return "query 缺少 entities（实体），请标出问题中的实体"
            if not action.get("attrs"):
                return "query 缺少 attrs（属性），请标出问题的属性维度"
            # kb 校验
            qkb = action.get("kb", "")
            if qkb and qkb not in original_msg:
                return f"知识库「{qkb}」不是用户说的名称，去掉 kb 参数"
            return None

        if atype == "import":
            if not any(kw in original_msg.lower() for kw in ["导入", "入库", "import", "加入", "放进去", "保存", "存档"]):
                return "用户没有说导入/入库，不要输出 import 指令，直接回答"
            if not action.get("path") and not action.get("content"):
                return "import 需要 content（文本内容）或 path（文件路径）。如果用户说'将这些入库'，用 content 参数把对话内容放进去"
            p = action.get("path", "")
            if p and p != "MANIFEST":
                cp = p.strip('"').strip("'").strip()
                if not os.path.exists(cp):
                    paths = [pp.strip() for pp in cp.split(",") if pp.strip()]
                    if not paths or not all(os.path.exists(pp) for pp in paths):
                        return f"路径不存在: {cp}。多个文件路径可以用逗号分隔"
            # kb 校验：只要用户没明确说知识库名，就不准用 kb 参数
            ikb = action.get("kb", "")
            if ikb:
                if ikb not in original_msg:
                    return f"知识库「{ikb}」不是用户说的名称。去掉 kb 参数让系统自动分类路由"
                # 即使出现在原话中也必须是真的知识库
                try:
                    kbs = self.rag.list_kbs() if self.rag and self.rag.ready else {}
                    if ikb not in kbs:
                        return f"知识库「{ikb}」系统中不存在。去掉 kb 参数让系统自动分类路由"
                except Exception:
                    pass
            return None

        # search 校验
        if atype == "search" and not action.get("query", ""):
            return "search 需要 query 参数"

        return None

    def _build_first_pass_messages(self, message: str) -> list:
        """构建第一轮 LLM 消息：系统提示 → 历史消息对 → 当前提问"""
        msgs = [{"role": "system", "content": self._system_prompt()}]

        # 解析 session 文件为真实的 user/assistant 消息对
        # 跳过最后一条（刚 append 的当前消息，避免重复），最后统一追加
        raw = self.memory.get_short_term(self.session_id)
        if raw.strip():
            lines = raw.strip().split("\n")
            # 去掉最后一行（刚写入的当前消息）
            if lines:
                lines = lines[:-1]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                m = re.match(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (\w+): (.+)', line)
                if m:
                    role = "user" if m.group(1) == "user" else "assistant"
                    msgs.append({"role": role, "content": m.group(2)})

        # 追加压缩摘要作为 System context（历史脉络，不占轮次位置）
        compressed = self.memory.get_compressed(self.session_id)
        if compressed:
            msgs.append({"role": "system", "content": f"【历史对话摘要】\n{compressed}"})

        msgs.append({"role": "user", "content": message})
        return msgs

    # ═══════════════ 第二轮：生成回答 ═══════════════

    def _second_pass(self, message: str, context: dict, action: dict) -> dict:
        """LLM 第二轮：有了检索结果后生成回答（也带历史对话）"""
        ctx_text = context.get("context", "")
        kb = action.get("kb", context.get("kb", ""))
        if ctx_text:
            sys_msg = f"基于以下资料回答用户问题。\n资料（来自 {kb}）：\n{ctx_text}"
        else:
            sys_msg = f"知识库（{kb}）中没有找到相关信息。请礼貌告知用户。"

        msgs = [{"role": "system", "content": sys_msg}]

        # 带上历史对话，保持上下文连贯
        raw = self.memory.get_short_term(self.session_id)
        if raw.strip():
            for line in raw.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                m = re.match(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (\w+): (.+)', line)
                if m:
                    role = "user" if m.group(1) == "user" else "assistant"
                    msgs.append({"role": role, "content": m.group(2)})

        msgs.append({"role": "user", "content": message})
        return self.llm.chat(msgs, stream=False)

    # ═══════════════ 动作解析 ═══════════════

    def _parse_action(self, text: str) -> tuple:
        """解析动作指令。返回 (params_dict, error_msg)
        - (None, None): 没有动作标记，正常聊天
        - (None, "原因"): 有 <<ACTION 但格式错误
        - ({...}, None): 解析成功
        """
        # 跨行匹配 <<ACTION ... >> 全文（content 可能含换行）
        m = re.search(r'<<ACTION\s+(.+?)>>', text, re.DOTALL)
        if not m:
            return None, None  # 没有动作

        raw_params = m.group(1).strip()
        # 解析 key="value"：手工状态机，正确处理 Windows 路径 `\` 和文件名内 `"` 
        params = {}
        i = 0
        while i < len(raw_params):
            # 跳过空白
            while i < len(raw_params) and raw_params[i] in ' \t\r\n':
                i += 1
            if i >= len(raw_params):
                break
            # 匹配 key=
            km = re.match(r'(\w+)=', raw_params[i:])
            if not km:
                break
            key = km.group(1)
            i += km.end()
            if i >= len(raw_params) or raw_params[i] not in '"\'':
                break
            quote = raw_params[i]
            i += 1
            # 收集 value：只有 \" 和 \\ 是转义，其他 \X 保持原样（适配 Windows 路径）
            val = []
            while i < len(raw_params):
                ch = raw_params[i]
                if ch == '\\' and i + 1 < len(raw_params) and raw_params[i + 1] in (quote, '\\'):
                    val.append(raw_params[i + 1])
                    i += 2
                elif ch == quote:
                    i += 1
                    break
                else:
                    val.append(ch)
                    i += 1
            params[key] = ''.join(val)

        action_type = params.get("type", "")
        if action_type not in ("query", "search", "import"):
            return None, f"未知动作类型: {action_type}，必须是 query/search/import"

        if action_type == "search" and not params.get("query"):
            return None, "search 动作缺少 query 参数"

        return params, None

    # ═══════════════ 执行查询/搜索 ═══════════════

    def _exec_query(self, action: dict, original_msg: str = "") -> dict:
        """组合式查询：LLM 标注成分，Agent 穷举组合，技能路由过滤"""
        entities = action.get("entities", "")
        attrs = action.get("attrs", "")
        rel = action.get("rel", "")
        kb = action.get("kb", "")

        if action["type"] == "search":
            q = action.get("query") or original_msg or ""
            result = self.search.search(q)
            snippets = "\n".join(
                f"{r.get('title','')}: {r.get('snippet','')}" for r in result.get("results", [])[:5]
            )
            return {"context": snippets, "kb": "web", "success": result.get("success", False)}

        if not entities and not attrs:
            return {"context": "", "kb": kb, "success": False, "has_context": False,
                    "error": "缺少 entities 或 attrs 参数"}

        # 穷举组合
        entity_list = [e.strip() for e in entities.split(",") if e.strip()]
        attr_list = [a.strip() for a in attrs.split(",") if a.strip()]
        _slices = set()
        for e in entity_list:
            for a in attr_list:
                _slices.add(f"{e} {a}")
        if len(entity_list) >= 2:
            for a in attr_list:
                _slices.add(f"{' '.join(entity_list)} {a}")
            if rel:
                _slices.add(f"{' '.join(entity_list)} {rel}")
        slices = list(_slices)

        logger.info(f"组合查询: entities={entity_list}, attrs={attr_list}, rel={rel}")
        logger.info(f"生成切片: {slices}")

        # 各切片独立走全流程，用技能 SM3 国密哈希去重
        from knowledge_base_manager import sm3
        seen_hashes = set()
        all_docs = []
        for sq in slices:
            try:
                r = self.rag.query(sq, kb_name=kb if kb else None)
                for d in r.get("docs", []):
                    content = d.get("content") if isinstance(d, dict) else (
                        d.page_content if hasattr(d, "page_content") else ""
                    )
                    h = sm3(content.encode("utf-8"))
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        all_docs.append(d)
            except Exception:
                continue

        if not all_docs:
            return {"context": "", "kb": kb, "success": False, "has_context": False}

        # 用技能自身的 build_context 拼接去重后的结果
        try:
            from rag_core import build_context
            context = build_context(all_docs)
        except Exception:
            context = "\n\n---\n\n".join(
                d.get("content", "")[:500] if isinstance(d, dict) else (
                    d.page_content[:500] if hasattr(d, "page_content") else str(d)[:500]
                ) for d in all_docs[:5]
            )
        return {"context": context, "kb": kb, "success": True, "has_context": True}

    def _exec_import(self, action: dict, original_msg: str) -> dict:
        """执行导入操作"""
        path = action.get("path", "")
        content = action.get("content", "")
        kb = action.get("kb", "")
        title = action.get("title", "")

        if content:
            return self._do_import_text(content, kb, title)
        if path:
            clean = path.strip('"').strip("'").strip()
            # path="MANIFEST" → 从 manifest 读取待入库文件列表
            if clean == "MANIFEST":
                manifest_path = os.path.join(self.data_dir, "import_manifest.json")
                if not os.path.exists(manifest_path):
                    return {"text": "没有待入库的文件", "success": False}
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                except Exception as e:
                    return {"text": f"读取文件清单失败: {e}", "success": False}
            else:
                # 逗号分隔的多个路径
                paths_to_import = [pp.strip() for pp in clean.split(",") if pp.strip()] if "," in clean else [clean]
                manifest = [{"path": pp, "count": 0} for pp in paths_to_import]
            imported_all = 0
            failed_all = 0
            for item in manifest:
                pp = item["path"] if isinstance(item, dict) else item
                if not os.path.exists(pp):
                    failed_all += 1
                    continue
                result = self._do_import(pp, kb)
                if result.get("success"):
                    imported_all += 1
                    # 导入成功后清理临时上传目录下的文件
                    imports_dir = os.path.join(self.data_dir, "imports")
                    if pp.startswith(imports_dir):
                        try:
                            os.unlink(pp)
                        except Exception:
                            pass
                else:
                    failed_all += 1
            # 清空 manifest
            if clean == "MANIFEST":
                try:
                    with open(manifest_path, "w", encoding="utf-8") as f:
                        json.dump([], f)
                except Exception:
                    pass
            if failed_all == 0 and imported_all > 0:
                return {"text": f"已导入 {imported_all} 个文件" + (f"，{failed_all} 个失败" if failed_all else ""), "success": True, "kb": kb or ""}
            elif imported_all == 0:
                return {"text": "导入失败", "success": False}
            else:
                return {"text": f"已导入 {imported_all} 个文件，{failed_all} 个失败", "success": True, "kb": kb or ""}
        return {"text": "指令缺少 path 或 content", "success": False}

    # ═══════════════ 导入实现 ═══════════════

    def _resolve_kb(self, content: str, filename: str = "") -> str:
        try:
            from knowledge_base_manager import auto_classify
            kb = auto_classify(content, filename=filename)
            return kb if kb else "default"
        except Exception:
            return "default"

    def _do_import(self, path: str, kb: str) -> dict:
        path = path.strip('"').strip("'")
        if not kb:
            kb = self._resolve_kb(os.path.basename(path), filename=os.path.basename(path))
        try:
            if os.path.isfile(path):
                r = self.rag.import_file(path, kb_name=kb)
                if r.get("success"):
                    return {"text": f"已导入 [{kb}]，{r.get('doc_count',0)} 个文档块", "success": True, "kb": kb}
                return {"text": f"导入失败: {r.get('error','')}", "success": False}
            if os.path.isdir(path):
                imported = 0
                for root, dirs, files in os.walk(path):
                    for f in files:
                        if f.endswith(('.pdf', '.txt', '.md', '.html', '.docx', '.csv')):
                            r = self.rag.import_file(os.path.join(root, f), kb_name=kb)
                            if r.get("success"):
                                imported += 1
                return {"text": f"已导入 {imported} 个文件", "success": True}
        except Exception as e:
            return {"text": f"导入异常: {e}", "success": False}
        return {"text": "路径无效", "success": False}

    def _do_import_text(self, content: str, kb: str, title: str = "") -> dict:
        if not kb:
            kb = self._resolve_kb(content, filename=title)
        try:
            r = self.rag.import_text(content, kb_name=kb, title=title)
            if r.get("success"):
                return {"text": f"已导入文本到 [{kb}]，{r.get('doc_count',0)} 个文档块", "success": True, "kb": kb}
            return {"text": f"导入失败: {r.get('error','')}", "success": False}
        except Exception as e:
            return {"text": f"导入异常: {e}", "success": False}

    # ═══════════════ 记忆压缩 ═══════════════

    def _compress_if_needed(self):
        try:
            if not self.memory.needs_compression(self.session_id):
                return
            old = self.memory.pop_oldest_lines(self.session_id)
            if not old.strip():
                return
            resp = self.llm.chat([
                {"role": "system", "content": "你是一个对话摘要助手。请保留以下关键信息：\n"
                 "1. 用户的核心需求/主题（如「白酒和啤酒香味物质对比」）\n"
                 "2. 已得到的结论/答案要点\n"
                 "3. 用户明确要继续追问的方向\n"
                 "4. 最近3条消息的原文（保留准确措辞）\n"
                 "压缩后控制在 200 字以内。"},
                {"role": "user", "content": f"压缩以下对话：\n{old}"},
            ])
            summary = resp.get("text", "")
            if summary:
                self.memory.store_compressed(self.session_id, summary)
        except Exception as e:
            logger.warning(f"压缩失败: {e}")

    def reset_session(self):
        self.memory.clear_short_term(self.session_id)
