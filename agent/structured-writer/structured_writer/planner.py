"""大纲规划器 — 调用 LLM 生成结构化文章大纲"""
import json
import re
from typing import Optional
from .llm_client import LLMClient, LLMClientError


def _build_planner_prompt(meta: list, content: list, user_meta: dict,
                          plan_hints: str = "") -> str:
    """
    根据 meta+content 结构和用户已填信息动态构建 planner system prompt。

    meta 字段 → 进入 meta{} 对象（短数据，不拆子结构）
    content 字段 → 进入 sections[] 数组（长文本，leaf/section）
    plan_hints → 用户对规划的额外要求（章节数、子结构数、字数等）
    """
    parts = [
        "你是结构化写作规划助手。严格执行以下命令：",
        "",
        "【输出规则】",
        "- 只输出 JSON，禁止任何其他文字、解释、礼貌用语。",
        "- 禁止 markdown 代码块标记（不要 ```json）。",
        "- 直接以 { 开头，以 } 结尾。",
        "",
        "【优先级规则】",
        "- 用户明确指定的结构要求（章节数、子结构数、字数等）优先于默认值",
        "- 2-4 个子结构、200-800 字/子结构 这些只是默认值，用户说了就不遵守",
        "- 每个内容树字段的 desc 字段中可能包含字数要求（如200-300字），以此为准设置 word_count",
        "",
        "【层级边界规则】",
        "- 内容树只支持 2 级结构：## 章节(section) 和 ### 子节(sub_section)",
        "- ####/##### 及更深的层次不作为独立结构条目",
        "- 深层次内容（####+）直接在 ### 子节的正文中作为 Markdown 标题输出",
        "",
        "【数据分类】",
        "- 元数据（短数据：标题、作者、关键词等）→ 放入 meta 对象",
        "- 内容树（长文本：摘要、引言、正文、结论等）→ 放入 sections 数组",
        "",
    ]

    # 用户规划要求
    if plan_hints:
        parts.append("【用户对本次规划的明确要求】")
        parts.append(plan_hints)
        parts.append("——以上要求优先于所有默认值，必须严格遵守。")
        parts.append("")

    # meta 字段
    if meta:
        parts.append(f"【元数据字段（共 {len(meta)} 个）】")
        parts.append(json.dumps(meta, ensure_ascii=False, indent=2))
        parts.append("")
        # 分类展示
        user_filled = [f for f in meta if f.get("source") == "user"]
        auto_filled = [f for f in meta if f.get("source") == "auto" and user_meta.get(f["name"])]
        llm_fields = [f for f in meta if f.get("source") == "llm"]
        auto_empty = [f for f in meta if f.get("source") == "auto" and not user_meta.get(f["name"])]
        if user_filled:
            parts.append("source=user 字段（用户填写，直接抄入 meta，不要修改）：" + json.dumps([f["name"] for f in user_filled], ensure_ascii=False))
        if auto_filled:
            parts.append("source=auto 已填（用户提供了值，直接抄入 meta）：" + json.dumps([f["name"] for f in auto_filled], ensure_ascii=False))
        if auto_empty:
            parts.append("source=auto 未填（用户未提供，由你生成）：" + json.dumps([f["name"] for f in auto_empty], ensure_ascii=False))
        if llm_fields:
            parts.append("source=llm 元数据（必须由你生成）：" + json.dumps([f["name"] for f in llm_fields], ensure_ascii=False))
        parts.append("")
        if user_meta:
            parts.append("用户已提供的值：")
            parts.append(json.dumps(user_meta, ensure_ascii=False, indent=2))
            parts.append("")

    # content 字段
    if content:
        parts.append(f"【内容树字段（共 {len(content)} 个）】")
        parts.append(json.dumps(content, ensure_ascii=False, indent=2))
        parts.append("")
        parts.append("类型规则：")
        parts.append('- type="leaf"：无子结构 sub_sections=[]，直接写全部内容')
        parts.append('- type="section"：默认拆 2-4 个子结构，用户明确指定数量时按用户要求')
        parts.append('- 每子结构默认 200-800 字，用户指定则按用户要求')
        parts.append("")
        parts.append("- is_key: true = 该节为重点节，写作字数可上浮 50%；false = 普通节")

        parts.append("【硬性要求】所有内容树字段**必须全部**在 sections 数组中输出，一条对应一个 sections 元素。")
        parts.append(f"内容树字段清单（共 {len(content)} 个，不准少）：{', '.join(cf['name'] for cf in content)}")
        parts.append("少输出任何一条，系统解析失败，文章将缺失该章节。")
        parts.append("")

    parts.extend([
        "【JSON 格式】",
        '{',
        '  "title": "标题值",',
        '  "meta": {"作者": "（待填写）", "文号": "〔2026〕12号"},',
        '  "sections": [',
        '    {"title": "关键词", "sub_sections": [], "type": "leaf", "is_key": false},',
        '    {"title": "摘要", "sub_sections": [], "type": "leaf", "is_key": false},',
        '    {"title": "引言", "sub_sections": [{"title":"子1","summary":"要点","word_count":400}], "type": "section", "is_key": true},',
        '  ]',
        '}',
        "",
        "【后果】如果输出包含 JSON 以外的任何文字，系统将无法解析，整个流程会失败。",
    ])

    return "\n".join(parts)


def parse_outline(text: str) -> Optional[dict]:
    """尝试从 LLM 输出中解析大纲 JSON"""
    text = text.strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start) if "```" in text[start:] else len(text)
        try:
            return json.loads(text[start:end].strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # 尝试提取 ``` ... ``` 代码块（无 json 标记）
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start) if "```" in text[start:] else len(text)
        content = text[start:end].strip()
        if content.startswith("json\n"):
            content = content[5:]
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            pass

    # 尝试找到第一个 { 或 [ 提取 JSON
    for ch, quote in [("{", "}"), ("[", "]")]:
        pos = text.find(ch)
        if pos >= 0:
            candidate = text[pos:]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                lines = candidate.split("\n")
                for cut in range(len(lines), 0, -1):
                    try:
                        return json.loads("\n".join(lines[:cut]))
                    except json.JSONDecodeError:
                        continue
            break

    return None


def _parse_word_count(cf: dict) -> int:
    """从模板 content 字段解析字数要求：
    desc 含 "200-300字" → 取中值；含 "300字" → 取该值；
    无数字时 leaf=0（字数不限，由 desc 指令约束）、section=800（默认）。
    leaf 拒绝 800 兜底——关键词这类输出列表的节不能被"约800字"诱导成长文。
    """
    _wc = 0 if cf.get("type") == "leaf" else 800
    _desc = cf.get("desc", "")
    _m = re.search(r"(\d+)\s*[-~至到]\s*(\d+)\s*字", _desc)
    if _m:
        return (int(_m.group(1)) + int(_m.group(2))) // 2
    _m = re.search(r"(\d+)\s*字", _desc)
    if _m:
        return int(_m.group(1))
    return _wc


def _normalize_outline(outline: dict, content_fields: list) -> dict:
    """
    规范化大纲：补默认值、填充 meta。
    """
    # 确保 title 存在
    if not outline.get("title"):
        meta = outline.get("meta", {})
        # 从 meta 或 content 字段中找标题
        outline["title"] = meta.get("标题", meta.get("文章标题", "未命名文章"))

    # 确保 sections 存在
    sections = outline.get("sections", [])
    if not sections:
        sections = []
    # 补充缺失的 content 字段（LLM 可能跳过某些字段）
    existing_titles = {s.get("title", "") for s in sections}
    for cf in content_fields:
        if cf["name"] not in existing_titles:
            sections.append({
                "id": f"s{len(sections)+1}",
                "title": cf["name"],
                "subtitle": "",
                "summary": cf.get("desc", ""),
                "word_count": _parse_word_count(cf),
                "is_key": False,
                "status": "pending",
                "actual_word_count": 0,
                "rag": {"enabled": False, "kb": ""},
                "_checked": True,
                "type": cf.get("type", "section"),
                "show_label": cf["show_label"],
                "sub_sections": []
            })
    outline["sections"] = sections

    for i, s in enumerate(sections):
        if "id" not in s:
            s["id"] = f"s{i+1}"
        s.setdefault("subtitle", "")
        s.setdefault("summary", "")
        s.setdefault("word_count", 800)
        s.setdefault("is_key", False)
        s.setdefault("status", "pending")
        s.setdefault("actual_word_count", 0)
        s.setdefault("rag", {"enabled": False, "kb": ""})
        s.setdefault("_checked", True)
        s.setdefault("type", "section")

        # ── 逻辑顺序（从模板 content[].logical_order 读取，不设/0 表示按 content[] 顺序） ──
        stitle = s.get("title", "")
        matched = [cf for cf in content_fields if cf.get("name") == stitle]
        lo = matched[0].get("logical_order") if matched else None
        s["_logical_order"] = lo if lo is not None else None

        # 从模板 content_fields 补充 show_label
        if matched:
            s["show_label"] = matched[0]["show_label"]
            # 引用校验节：字数强制为 0（不走 LLM 写作，由后处理接管）
            if matched[0].get("citation_check"):
                s["word_count"] = 0
            # leaf 节：字数按 desc 解析，拒绝 800 兜底
            # （规划器输出的大纲可能给关键词这类节兜底 800 字，
            #   导致写作提示变成"约800字"，诱导长文输出）
            elif matched[0].get("type") == "leaf":
                s["word_count"] = _parse_word_count(matched[0])

        subs = s.get("sub_sections", [])
        s_type = s.get("type", "section")

        if not subs and s_type == "section":
            subs = [{
                "id": f"{s['id']}_1",
                "title": s.get("subtitle") or s["title"],
                "summary": s.get("summary", ""),
                "word_count": s.get("word_count", 800),
            }]
            s["sub_sections"] = subs

        for j, ss in enumerate(subs):
            if "id" not in ss:
                ss["id"] = f"{s['id']}_{j+1}"
            ss.setdefault("summary", "")
            ss.setdefault("word_count", max(200, s.get("word_count", 800) // max(len(subs), 1)))
            ss.setdefault("status", "pending")
            ss.setdefault("actual_word_count", 0)
            ss.setdefault("_checked", True)
            ss.setdefault("aux_knowledge", None)

        if not subs:
            s.setdefault("word_count", 800)
        else:
            s["word_count"] = sum(ss["word_count"] for ss in subs)

    return outline


def plan_outline(topic: str, template: dict = None,
                 user_meta: dict = None, llm_client: LLMClient = None,
                 prompt: str = "", plan_hints: str = "") -> dict:
    """
    生成结构化大纲。

    参数:
        topic: 写作主题
        template: {meta: [...], content: [...], style: "...", logic: "..."}
        user_meta: 用户已填的字段值 {"标题": "xxx", "作者": "（待填写）"}
        llm_client: LLM 客户端
        prompt: 旧兼容参数 — 作为风格提示词覆盖
        plan_hints: 用户对规划的额外要求（章节数、子结构数、字数等）

    返回:
        dict: 大纲 JSON {title, meta, sections}
    """
    if llm_client is None:
        raise ValueError("需要提供 llm_client")

    # 旧接口兼容
    if isinstance(template, str) or template is None:
        style = template or prompt or ""
        template = {
            "meta": [{"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto"}],
            "content": [{"name": "正文", "show_label": False, "desc": "文章主体", "type": "section"}],
            "style": style,
            "logic": ""
        }
        if not user_meta:
            user_meta = {"标题": topic} if topic else {}

    if user_meta is None:
        user_meta = {}

    meta_fields = template.get("meta", [])
    content_fields = template.get("content", [])
    style = template.get("style", prompt or "")

    # 构建 system prompt（含 plan_hints）
    system_prompt = _build_planner_prompt(meta_fields, content_fields, user_meta, plan_hints)

    # 构建 user message
    user_msg_lines = [f"主题：{topic}"]
    if style:
        user_msg_lines.append(f"写作风格：{style}")
    user_msg_lines.append("\n请生成文章大纲。")
    user_msg = "\n".join(user_msg_lines)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg}
    ]

    # 最多重试 3 次（格式错误重试）
    outline = None
    last_raw = ""
    for attempt in range(3):
        # 下限 2048：保证推理模型能完成推理并输出大纲主体；
        # 仍被截断时由续接循环补全。低于 2048 推理吃光 token
        # 输出为空，续接无法挽救（空内容直接断）。
        plan_max_tokens = max(2048, llm_client.max_tokens)
        # 续接循环：检测 finish_reason=length 时追加"继续输出"，
        # 拼装完整 JSON 后再解析（与写作引擎机制一致）
        raw = ""
        cont_messages = messages.copy()
        for _cont in range(4):
            result = llm_client.chat_detailed(cont_messages, max_tokens=plan_max_tokens, temperature=None)
            chunk = result.get("content", "")
            finish_reason = result.get("finish_reason", "stop")
            raw += chunk
            if finish_reason != "length":
                break
            if not chunk.strip():
                break
            cont_messages.append({"role": "assistant", "content": chunk})
            cont_messages.append({
                "role": "user",
                "content": "大纲 JSON 输出被截断，请直接从截断处继续输出 JSON 内容，"
                           "不要重复已输出的内容，不要任何解释文字。"
            })
        last_raw = raw
        outline = parse_outline(raw)

        if outline is not None:
            break

        error_feedback = (
            f"【格式错误】你的输出包含 JSON 以外的文字，或 JSON 格式不正确。\n"
            f"只输出 JSON，以 {{ 开头，以 }} 结尾，不要任何其他文字。\n"
            f"重新生成："
        )
        messages.append({"role": "assistant", "content": raw[:800]})
        messages.append({"role": "user", "content": error_feedback})

    if outline is None:
        raise ValueError(
            f"LLM 连续 3 次无法输出正确格式的大纲。最后一次输出：\n{last_raw[:500]}"
        )

    # 规范化
    outline = _normalize_outline(outline, content_fields)

    return outline
