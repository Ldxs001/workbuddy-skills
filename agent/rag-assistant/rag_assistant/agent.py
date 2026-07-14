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

_ACTION_STRIP = re.compile(r'<{1,2}\s*ACTION\s+.*?>{1,2}', re.DOTALL | re.IGNORECASE)

# ═══════════════ 内置查询类型参考（可被 config 自定义覆盖） ═══════════════
BUILTIN_QUERY_TYPES = {
    "fact": {
        "label": "事实查询",
        "example": '"茅台的价格是多少？"',
        "rules": {
            "entities": "主体/名词。问题涉及的核心事物",
            "attrs": "目的/属性。用户想查询的维度",
            "rel": "留空（不触发两两配对）",
        }
    },
    "compare": {
        "label": "实体对比",
        "example": '"茅台和五粮液酿造工艺异同"',
        "rules": {
            "entities": "被对比的多个实体，逗号分隔",
            "attrs": "对比维度（例如 酿造工艺）",
            "rel": '"对比"',
        }
    },
    "opposition": {
        "label": "二元对立",
        "example": '"AI是顺着倾向回答还是独立思考"',
        "rules": {
            "entities": "只填主体（例如 AI），不要把对立面放进来",
            "attrs": "两个对立面都放进来，逗号分隔（例如 迎合,独立思考）",
            "rel": '"对比"',
        }
    },
    "analysis": {
        "label": "多维度分析",
        "example": '"AI如何模仿人类情感、有什么缺陷、人类的独一无二性体现在哪里"',
        "rules": {
            "entities": "分析主体",
            "attrs": "分析维度A,分析维度B,分析维度C",
            "rel": "对比分析",
        }
    },
}


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
        type_ref = self._build_type_reference()
        prompt = f"""你是 RAG 知识库助手。你可以使用以下动作：

## 动作格式（必须严格遵守，不可变更）
所有动作必须使用以下格式，**大小写、尖括号数量不可修改**：
```
<<ACTION type="xxx" 参数="值">>
```
- 必须使用双尖括号 `<<` 开头和 `>>` 结尾
- 必须大写 `ACTION`，不可写 `action` 或 `Action`
- `<<` 和 `ACTION` 之间不能有空格
- 错误示例（不会被解析）：`<action>`、`<ACTION>`、`<<action>>`、`<< Action>>`

## 知识库查询
<<ACTION type="query" entities="名词1,名词2" attrs="目的" rel="行为" kb="知识库名（可选）">>
- entities：**取主体/名词**。问题中涉及的核心事物、人物、概念，如"茅台"、"五粮液"、"神经网络"。多个用逗号分隔
- attrs：**取目的**。用户想查询的目标/用途/对象，如"酿造工艺"、"价格"、"原理"、"定义"。注意：不要把"异同"、"区别"、"对比"等比较意图词放这里，那些归 rel
- rel：**取行为**。实体间的动作/关系。当存在比较、对比、对立关系时填写，填一个最贴切的词即可（如 rel="对比"）。
- 三者关系：entities=谁/什么，attrs=查什么，rel=怎么查
- evidence：**每个 entity 和 attr 都必须提供原文出处**。格式为 JSON 字典，key 必须与 entities/attrs 中的写法**精确一致**（不可改词、不可增减字），value 是这个词在用户问题中的原文出处。示例：evidence='{{"AI":"AI","迎合":"顺着倾向回答","独立思考":"独立思考"}}' **entity/attr 可以是对原文的提炼凝缩**（如"顺着我的倾向回答"→"迎合"），但 evidence 的 key 必须与 entities/attrs 中实际写出的词完全一样。value 必须使用原文原句，不能自己编造。
Agent 会自动将 entities × attrs 穷举组合后查询。
不要用 question 参数，不会生效。

## 查询类型参考（仅作填写指引，不需要声明类型）
以下不同类型的问题，entities/attrs/rel 的填写方式不同。你不需要声明类型，只需参照最匹配的例子填写参数：

{type_ref}

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
- **闲聊/打招呼/不需要查资料/直接回答** → 使用 `<<ACTION type="chat">>` 显式声明，标记后直接输出回复文本
- **需要查知识库** → 使用 `<<ACTION type="query" entities="..." attrs="..." rel="..." evidence='{...}'>>`
- **需要联网搜索** → 使用 `<<ACTION type="search" query="...">>`
- **入库/导入文件** → 用户明确要求时才用，使用 `<<ACTION type="import">>`

**重要：所有回复都必须使用 `<<ACTION type="xxx">>` 显式声明你要做什么。包括纯聊天、问候、闲聊——都必须用 `<<ACTION type="chat">>` 标记。系统通过这个标记决定如何处理你的输出。**

## 关键：只对最新消息做决策
- 下方消息列表中，最后一条 user 消息是用户的当前提问
- 之前的消息是历史记录，不要重复执行或参考它们的内容来构造新的 <<ACTION>>
- 只根据最新一条 user 消息的内容决定：直接回答 / 查知识库 / 搜网页 / 入库
- **用户说"入库"或"导入"时，表示要导入文件，用 type="import" path="MANIFEST"，不要查知识库**
"""
        return prompt

    def _get_all_query_types(self) -> dict:
        """合并内置+自定义查询类型（自定义覆盖同 key 内置）"""
        types = dict(BUILTIN_QUERY_TYPES)
        try:
            from .engine.config import load_config
            cfg = load_config()
            custom = cfg.get("query_types", {})
            if isinstance(custom, dict):
                types.update(custom)
        except Exception:
            pass
        return types

    def _build_type_reference(self) -> str:
        """构建查询类型参考文本"""
        all_types = self._get_all_query_types()
        lines = []
        for t in all_types.values():
            label = t.get("label", "未知")
            example = t.get("example", "")
            rules = t.get("rules", {})
            lines.append(
                f"【{label}】{example}\n"
                f"  entities → {rules.get('entities','')}\n"
                f"  attrs → {rules.get('attrs','')}\n"
                f"  rel → {rules.get('rel','')}"
            )
        return "\n\n".join(lines)

    def chat(self, message: str, stream: bool = False) -> dict:
        """处理一条用户消息（带 LLM 自修正循环）"""
        self.memory.append_short_term(self.session_id, "user", message)

        # 自修正循环：LLM 输出 → Agent 校验 → 不通过则反馈给 LLM 重试
        decision, action = self._decide_with_retry(message, max_retries=5)

        reply = decision.get("text", "")
        reasoning = decision.get("reasoning", "")

        # 导入动作（独立执行，不需要第二轮 LLM）
        if action and action["type"] == "import":
            result = self._exec_import(action, message)
            self.memory.append_short_term(self.session_id, "assistant", _ACTION_STRIP.sub('', result.get("text", "")).strip())
            imported_kbs = result.get("imported_kbs", {})
            primary_kb = max(imported_kbs, key=imported_kbs.get) if imported_kbs else ""
            self.memory.record_habit(message, is_rag=False, is_chat=False, is_import=True, kb=primary_kb)
            result["success"] = True
            return result

        # 查询/搜索动作（执行后第二轮 LLM 生成回答）
        if action and action["type"] in ("query", "search"):
            context = self._exec_query(action, message)
            result = self._second_pass(message, context, action)
            reply2 = result.get("text", "")
            reas2 = result.get("reasoning", "")
            if reply2:
                self.memory.append_short_term(self.session_id, "assistant", _ACTION_STRIP.sub('', reply2).strip())
            if reas2:
                self.memory.append_short_term(self.session_id, "reasoning", reas2)
            self._compress_if_needed()
            self.memory.record_habit(message, is_rag=action["type"] == "query",
                                     is_chat=action["type"] != "query", is_import=False,
                                     kb=context.get("routed_kb", ""))
            result["success"] = True
            return result

        # 直接回答（无动作）
        if reply:
            self.memory.append_short_term(self.session_id, "assistant", _ACTION_STRIP.sub('', reply).strip())
        if reasoning:
            self.memory.append_short_term(self.session_id, "reasoning", reasoning)
        self._compress_if_needed()
        self.memory.record_habit(message, is_rag=False, is_chat=True, is_import=False, kb="")
        decision["success"] = True
        return decision

    def _decide_with_retry(self, message: str, max_retries: int = 5) -> tuple:
        """LLM 决策 + 自修正循环

        两阶段设计：
        阶段 1（模式判定）：单次 LLM 调用，确定 chat 模式 / action 模式
        阶段 2（仅 action 模式）：小 loop，只在动作校验上循环
            - LLM 一旦进入 action 模式，必须在重试中保持 action 模式
            - 不允许通过"不输出 <<ACTION>>"逃避校验
            - 5 次失败后不允许 LLM 自由回答（防止捏造引用）
        """
        msgs = self._build_first_pass_messages(message)

        # ═══════ 阶段 1：模式判定（单次 LLM 调用，不在 loop 内）═══════
        resp = self.llm.chat(msgs, stream=False)
        reply = resp.get("text", "")
        action, parse_err = self._parse_action(reply)

        # 完全无动作标记 → LLM 显式选择 chat 模式
        if not action and not parse_err:
            # 旧版 LLM 不会用 <<ACTION type="chat">>，但行为语义上"无动作"就是 chat
            return resp, None

        # chat 动作 → chat 模式
        if action and action.get("type") == "chat":
            return resp, action

        # 解析错误或有效 action → 进入阶段 2
        return self._action_validation_loop(
            msgs, message, max_retries,
            initial_resp=resp, initial_action=action, initial_parse_err=parse_err
        )

    def _action_validation_loop(self, msgs: list, message: str, max_retries: int,
                                 initial_resp=None, initial_action=None,
                                 initial_parse_err=None) -> tuple:
        """阶段 2：动作校验小 loop

        LLM 已选择 action 模式（query/search/import），必须保持 action 模式。
        重试中如果 LLM 试图"不输出 <<ACTION>>"逃避，按"逃逸"处理并强制回正。
        5 次都失败 → 返回结构化错误，禁止 LLM 自由回答。
        """
        # 把初始失败的结果作为第一次反馈加入
        if initial_parse_err:
            logger.info(f"LLM 动作解析失败 (attempt 1): {initial_parse_err}")
            msgs.append({"role": "assistant", "content": initial_resp.get("text", "")})
            msgs.append({"role": "user", "content":
                f"【修正提醒】\n"
                f"- 问题：{initial_parse_err}\n"
                f"- 要求：修正后输出有效的 <<ACTION>> 标记\n"
                f"- 注意：你必须输出动作（query/search/import/chat），不能跳出动作模式"})
        elif initial_action:
            rejection = self._validate_action(initial_action, message)
            if rejection:
                logger.info(f"LLM 动作被拒绝 (attempt 1): {rejection}")
                msgs.append({"role": "assistant", "content": initial_resp.get("text", "")})
                msgs.append({"role": "user", "content":
                    f"【修正提醒】\n"
                    f"- 问题：{rejection}\n"
                    f"- 要求：修正后重新输出\n"
                    f"- 注意：你已选择动作模式，必须保持动作模式"})
            else:
                # 初始 action 已经有效，直接返回，不进 loop
                return initial_resp, initial_action

        # 小 loop：从第 2 次 attempt 开始（attempt 1 已处理过）
        for attempt in range(1, max_retries + 1):
            resp = self.llm.chat(msgs, stream=False)
            reply = resp.get("text", "")
            action, parse_err = self._parse_action(reply)

            # LLM 试图逃出 action 模式（不输出 <<ACTION>>）
            if not action and not parse_err:
                logger.info(f"LLM 尝试逃出 action 模式 (attempt {attempt+1})")
                msgs.append({"role": "assistant", "content": reply})
                msgs.append({"role": "user", "content":
                    "【修正提醒】\n"
                    "- 你已选择动作模式（query/search/import），必须输出有效的 <<ACTION>> 标记\n"
                    "- 如要改为纯聊天，请使用 <<ACTION type=\"chat\">> 显式声明\n"
                    "- 不允许通过不输出动作标记来逃避校验"})
                continue

            # 解析错误 → 反馈
            if parse_err:
                logger.info(f"LLM 动作解析失败 (attempt {attempt+1}): {parse_err}")
                msgs.append({"role": "assistant", "content": reply})
                msgs.append({"role": "user", "content":
                    f"【修正提醒】\n"
                    f"- 问题：{parse_err}\n"
                    f"- 要求：修正后输出有效的 <<ACTION>> 标记"})
                continue

            # 校验
            rejection = self._validate_action(action, message)
            if not rejection:
                return resp, action

            logger.info(f"LLM 动作被拒绝 (attempt {attempt+1}): {rejection}")
            msgs.append({"role": "assistant", "content": reply})
            msgs.append({"role": "user", "content":
                f"【修正提醒】\n"
                f"- 问题：{rejection}\n"
                f"- 要求：修正后重新输出\n"
                f"- 注意：你已选择动作模式，必须保持动作模式"})

        # 5 次重试都失败 → 禁止 LLM 自由回答
        logger.warning("LLM 动作校验 5 次失败，拒绝 LLM 自由回答（防止捏造）")
        return {
            "text": "我无法正确解析你的请求为有效的动作（连续校验失败）。请重新表述你的问题。",
            "reasoning": ""
        }, None

    def _validate_action(self, action: dict, original_msg: str) -> Optional[str]:
        """校验动作是否合法，不合法返回明确的拒绝原因"""
        atype = action.get("type", "")

        if atype not in ("query", "search", "import", "chat"):
            return f"type 必须是 query / search / import / chat 之一，收到: {atype}"

        # chat 动作不需要额外校验
        if atype == "chat":
            return None

        if atype == "query":
            if not action.get("entities") and not action.get("attrs"):
                return "query 必须用 entities（主体/名词）和 attrs（目的）参数标注成分，不要用 question"
            if not action.get("entities"):
                return "query 缺少 entities（主体/名词），请标出问题中涉及的核心事物"
            if not action.get("attrs"):
                return "query 缺少 attrs（目的），请标出用户想查询的目标"
            # evidence 校验
            raw_ev = action.get("evidence", "")
            if not raw_ev:
                return "query 缺少 evidence 参数。每个 entity 和 attr 都必须提供原文出处，格式：evidence='{\"词\":\"原文出处\"}'。注意：evidence 的 key 必须与 entities/attrs 中的写法精确一致，不可改词、不可增减字"
            try:
                ev = json.loads(raw_ev)
            except (json.JSONDecodeError, TypeError):
                return "evidence 不是合法 JSON。请检查格式，示例：evidence='{\"AI\":\"AI\"}'"
            if not isinstance(ev, dict):
                return "evidence 必须是一个 JSON 字典"
            all_raw = (action.get("entities", "") + "," + action.get("attrs", ""))
            all_terms = [t.strip() for t in re.split(r'[,，]', all_raw) if t.strip()]
            missing = [t for t in all_terms if t not in ev]
            if missing:
                return f"以下词缺少 evidence key（必须与 entities/attrs 中的写法精确一致，不可改词）: {', '.join(missing)}。请补充 evidence 中的对应条目"
            fakes = [f"「{k}」的出处「{v}」" for k, v in ev.items() if v not in original_msg]
            if fakes:
                return f"以下出处不存在于用户问题中，必须使用原文原句: {'; '.join(fakes)}"
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
        """构建第一轮 LLM 消息：系统提示 → 当前提问（历史以压缩摘要形式传入，不传完整对话）"""
        msgs = [{"role": "system", "content": self._system_prompt()}]

        # 压缩摘要作为 System context（历史脉络，不占轮次位置）
        compressed = self.memory.get_compressed(self.session_id)
        if compressed:
            msgs.append({"role": "system", "content": f"【历史对话，仅作参考】\n{compressed}"})

        # 追加用户画像提示（方案 C：prompt_manager 模块）
        try:
            from prompt_manager import build_persona_prompt
            persona_text = self.memory.build_persona_context()
            persona_prompt = build_persona_prompt(persona_text)
            if persona_prompt:
                msgs.append({"role": "system", "content": persona_prompt})
        except Exception:
            pass

        msgs.append({"role": "user", "content": message})
        return msgs

    # ═══════════════ 第二轮：生成回答 ═══════════════

    def _second_pass(self, message: str, context: dict, action: dict) -> dict:
        """LLM 第二轮：有了检索结果后生成回答（也带历史对话）"""
        ctx_text = context.get("context", "")
        kb = action.get("kb", context.get("kb", ""))
        if ctx_text:
            from prompt_manager import build_second_pass_prompt
            sys_msg = build_second_pass_prompt(context=ctx_text, question=message, kb=kb)
        else:
            sys_msg = f"知识库（{kb}）中没有找到相关信息。请礼貌告知用户。"

        msgs = [{"role": "system", "content": sys_msg}]

        # 带上历史对话，保持上下文连贯（只带 user/assistant，跳过 reasoning 防止连续 role）
        raw = self.memory.get_short_term(self.session_id)
        if raw.strip():
            for line in raw.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                m = re.match(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] (\w+): (.+)', line)
                if m:
                    role_raw = m.group(1)
                    if role_raw == "reasoning":
                        continue
                    role = "user" if role_raw == "user" else "assistant"
                    msgs.append({"role": role, "content": f"[历史对话] {m.group(2)}"})

        msgs.append({"role": "user", "content": message})
        resp = self.llm.chat(msgs, stream=False)
        reply = resp.get("text", "")

        # 引用门禁：校验 LLM 回答中的 [n] 引用是否在资料中真实存在
        if ctx_text and reply:
            cited = set(int(n) for n in re.findall(r'\[(\d+)\]', reply))
            max_para = len(ctx_text.split("\n"))
            fake_cites = [n for n in cited if n < 1 or n > max_para]
            if fake_cites:
                logger.warning(f"LLM 引用了不存在的段落 {fake_cites}，回应注入告警")
                reply += f"\n\n> ⚠️ 以上回答中包含未在资料中出现的引用标记 {fake_cites}，请注意验证。"
            if not cited and ctx_text.strip():
                logger.info(f"LLM 回答未标注引用")
        return resp

    # ═══════════════ 动作解析 ═══════════════

    def _parse_action(self, text: str) -> tuple:
        """解析动作指令。返回 (params_dict, error_msg)
        - (None, None): 没有动作标记，正常聊天
        - (None, "原因"): 有 <<ACTION 但格式错误
        - ({...}, None): 解析成功
        """
        # 精准匹配标准格式 <<ACTION ...>>
        m = re.search(r'<<ACTION\s+(.+?)>>', text, re.DOTALL)
        if m:
            raw_params = m.group(1).strip()
        else:
            # 检查是否有类似动作但格式错误的写法，进入修正循环
            bad = re.search(r'<{1,2}\s*(?:action|Action|query|import|search)\b', text, re.IGNORECASE)
            if bad:
                return None, f"动作格式错误：必须使用 <<ACTION>> 格式（双尖括号、大写ACTION），收到非标准写法「{bad.group()}」。请修正后重试"
            # 完全没有动作标记
            return None, None

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
        if action_type not in ("query", "search", "import", "chat"):
            return None, f"未知动作类型: {action_type}，必须是 query/search/import/chat"

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

        # 穷举组合（支持中英文逗号）
        import re
        entity_list = [e.strip() for e in re.split(r'[,，]', entities) if e.strip()]
        attr_list = [a.strip() for a in re.split(r'[,，]', attrs) if a.strip()]
        # 如果指定的 rel 中包含比较意图关键词，从 attrs 中排除
        if rel:
            _compare_kw = {"异同", "区别", "差别", "对比", "共同点", "不同点", "异同点", "差异"}
            attr_list = [a for a in attr_list if a not in _compare_kw]
        _slices = set()
        # 第一层：entity × attr — 每个实体的各属性切片（事实块检索用）
        for e in entity_list:
            for a in attr_list:
                _slices.add(f"{e} {a}")
        # 第二层：多实体全拼 × attr — 全实体联合检索
        if len(entity_list) >= 2:
            joined = ' '.join(entity_list)
            for a in attr_list:
                _slices.add(f"{joined} {a}")
        # 第三层：rel 语义 — 追加一个关系切片（不是取代前两层）
        #   LLM 拿到 {事实块1, 事实块2, 关系块} 做推理整合
        if rel:
            if len(entity_list) >= 2:
                import itertools
                for e1, e2 in itertools.combinations(entity_list, 2):
                    if attr_list:
                        for a in attr_list:
                            _slices.add(f"{e1} {e2} {a} {rel}")
                    else:
                        _slices.add(f"{e1} {e2} {rel}")
            else:
                # 单实体 + N 属性 + rel → attrs 无重复两两配对 + rel
                #   N=2: "AI 顺着我的倾向回答 独立思考 对比"
                #   N=3: "AI a1 a2 对比", "AI a1 a3 对比", "AI a2 a3 对比"
                import itertools
                e = entity_list[0]
                for a1, a2 in itertools.combinations(attr_list, 2):
                    _slices.add(f"{e} {a1} {a2} {rel}")
        slices = list(_slices)

        logger.info(f"组合查询: entities={entity_list}, attrs={attr_list}, rel={rel}")
        logger.info(f"生成切片: {slices}")

        # 各切片独立走全流程，用技能 SM3 国密哈希去重
        from knowledge_base_manager import sm3
        seen_hashes = set()
        all_docs = []
        routed_kb = ""
        for sq in slices:
            try:
                r = self.rag.query(sq, kb_name=kb if kb else None)
                # 捕获路由实际 KB（取第一个有返回值的）
                if not routed_kb:
                    routed_kb = r.get("kb", "")
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
            return {"context": "", "kb": kb, "routed_kb": routed_kb, "success": False, "has_context": False}

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
        return {"context": context, "kb": kb, "routed_kb": routed_kb, "success": True, "has_context": True}

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
            imported_kbs = {}
            try:
                for item in manifest:
                    pp = item["path"] if isinstance(item, dict) else item
                    if not os.path.exists(pp):
                        failed_all += 1
                        continue
                    result = self._do_import(pp, kb)
                    if result.get("success"):
                        imported_all += 1
                        actual_kb = result.get("kb", kb or "default")
                        imported_kbs[actual_kb] = imported_kbs.get(actual_kb, 0) + 1
                        # 导入成功后清理临时上传目录下的文件
                        imports_dir = os.path.join(self.data_dir, "imports")
                        if pp.startswith(imports_dir):
                            try:
                                os.unlink(pp)
                            except Exception:
                                pass
                    else:
                        failed_all += 1
            finally:
                # 无论循环是否异常，都清空 manifest 防止残留
                if clean == "MANIFEST":
                    try:
                        with open(manifest_path, "w", encoding="utf-8") as f:
                            json.dump([], f)
                    except Exception:
                        pass
            kb_summary = ", ".join(f"{k}({v})" for k, v in sorted(imported_kbs.items())) if imported_kbs else kb or ""
            msg = f"已导入 {imported_all} 个文件"
            if imported_kbs:
                msg += f"\n自动分类路由：{kb_summary}"
            if failed_all:
                msg += f"，{failed_all} 个失败"
            if failed_all == 0 and imported_all > 0:
                return {"text": msg, "success": True, "kb": kb_summary, "imported_kbs": imported_kbs}
            elif imported_all == 0:
                return {"text": "导入失败", "success": False, "imported_kbs": imported_kbs}
            else:
                return {"text": msg, "success": True, "kb": kb_summary, "imported_kbs": imported_kbs}
        return {"text": "指令缺少 path 或 content", "success": False}

    # ═══════════════ 导入实现 ═══════════════

    def _resolve_kb(self, content: str, filename: str = "") -> str:
        try:
            from config import load_config
            cfg = load_config()
            # 只有入库路由开启时才用向量语义分类，否则走默认
            if cfg.get("kb", {}).get("auto_classify", False):
                from knowledge_base_manager import auto_classify
                kb = auto_classify(content, filename=filename, use_semantic=True)
                return kb if kb else "default"
            return "default"
        except Exception:
            return "default"

    def _do_import(self, path: str, kb: str) -> dict:
        path = path.strip('"').strip("'")
        if not kb:
            # 入库路由：受 kb.auto_classify 控制，用向量模型对文档正文×各KB关键词做余弦相似度
            try:
                from config import load_config
                from knowledge_base_manager import _load_rules
                from rag_core import get_embeddings
                cfg = load_config()
                if cfg.get("kb", {}).get("enabled", True) and cfg.get("kb", {}).get("auto_classify", False):
                    ext = os.path.splitext(path)[1].lower()
                    content = ""
                    if ext == ".pdf":
                        from langchain_community.document_loaders import PyPDFLoader
                        pdf_docs = PyPDFLoader(path).load()
                        content = "\n\n".join(d.page_content[:500] for d in pdf_docs[:4])
                    elif ext in (".txt", ".md", ".html"):
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read(6000)
                    if content:
                        import numpy as np
                        emb = get_embeddings()
                        doc_vec = np.array(emb.embed_query(content))
                        rules = _load_rules()
                        best_kb, best_score = "default", -1
                        for kb_name, rule in rules.items():
                            kws = rule.get("keywords", [])
                            if not kws:
                                continue
                            kw_vec = np.array(emb.embed_query(" ".join(kws)))
                            sim = np.dot(doc_vec, kw_vec) / (np.linalg.norm(doc_vec) * np.linalg.norm(kw_vec))
                            if sim > best_score:
                                best_score, best_kb = sim, kb_name
                        if best_kb != "default":
                            kb = best_kb
                if not kb:
                    kb = "default"
            except Exception:
                kb = "default"
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
