"""大纲规划器 — 调用 LLM ��成结构化文章大纲"""
import json
from typing import Optional
from .llm_client import LLMClient, LLMClientError


def _build_planner_prompt(structure: list, user_meta: dict) -> str:
    """
    根据五元组结构和用户已填信息动态构建 planner system prompt。
    """
    # 按 source 分组
    user_fields = [f for f in structure if f["source"] == "user"]
    auto_filled = [f for f in structure
                   if f["source"] == "auto" and user_meta.get(f["name"])]
    llm_fields = [f for f in structure
                  if f["source"] == "llm" or
                  (f["source"] == "auto" and not user_meta.get(f["name"]))]

    parts = [
        "你是结构化写作规划助手。严格执行以下命令：",
        "",
        "【输出规则】",
        "- 只输出 JSON，禁止任何其他文字、解释、礼貌用语。",
        "- 禁止 markdown 代码块标记（不要 ```json）。",
        "- 直接以 { 开头，以 } 结尾。",
        "",
        "【字段列表】（共 {} 个）：".format(len(structure)),
        "",
    ]

    # 按填写对象分类展示
    if llm_fields:
        parts.append("以下字段**必须由你生成**（llm/auto未填）：")
        parts.append(json.dumps(llm_fields, ensure_ascii=False, indent=2))
        parts.append("")
    if auto_filled:
        parts.append("以下 auto 字段用户已提供，直接抄入 meta（无需生成）：")
        parts.append(json.dumps(auto_filled, ensure_ascii=False, indent=2))
        parts.append("")
    if user_fields:
        parts.append("以下 user 字段由用户填写，有值则抄入 meta，没值则 meta 中不出现（切勿生成）：")
        parts.append(json.dumps(user_fields, ensure_ascii=False, indent=2))
        parts.append("")

    # user_meta 展示
    if user_meta:
        parts.append("用户已提供的值：")
        parts.append(json.dumps(user_meta, ensure_ascii=False, indent=2))
        parts.append("")

    parts.extend([
        "【类型规则】",
        '- type:"leaf"：无子结构 sub_sections=[]，直接写全部内容在该节下',
        '- type:"section"：拆 2-4 个子结构，每子结构 200-800 字',
        "",
        "【元数据规则】",
        "- 短数据（标题、关键词等）放入 meta 对象",
        "- 段落内容（摘要、参考文献等）放入 sections 数组",
        "- user 字段：有值就原样抄入 meta，没值不出现",
        "- 第一个 leaf 字段自动作为文章标题，同时在 title 字段和 meta 中各放一份",
        "",
        "【后果】如果输出包含 JSON 以外的任何文字，系统将无法解析，整个流程会失败。",
        "",
        "【JSON 格式】",
        '{',
        '  "title": "标题值",',
        '  "meta": {"关键词": "xxx; yyy"},',
        '  "sections": [',
        '    {"title": "摘要", "sub_sections": [], "type": "leaf"},',
        '    {"title": "正文", "sub_sections": [{"title":"子1","summary":"要点","word_count":400}, {...}], "type": "section"}',
        '  ]',
        '}',
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


def _normalize_outline(outline: dict, structure: list, user_meta: dict) -> dict:
    """
    规范化大纲：补默认值、填充 user_meta、标记 type。
    """
    # 填充 user 字段到 meta
    meta = outline.get("meta", {})
    for f in structure:
        if f["source"] == "user" and user_meta.get(f["name"]):
            meta[f["name"]] = user_meta[f["name"]]
    outline["meta"] = meta

    # 确保 title 存在
    if not outline.get("title"):
        # 从 meta 中取第一个 leaf
        for f in structure:
            if f["type"] == "leaf" and meta.get(f["name"]):
                outline["title"] = meta[f["name"]]
                break
        if not outline.get("title"):
            outline["title"] = "未命名文章"

    # 确保 sections 存在
    if not outline.get("sections"):
        outline["sections"] = []

    # 为每个 section 补 type 和默认值
    for i, s in enumerate(outline["sections"]):
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

        # 子结构规范化
        subs = s.get("sub_sections", [])
        s_type = s.get("type", "section")

        if not subs and s_type == "section":
            # section 类型但 LLM 没给子结构时，自动补一个
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

        # 纠正 section 级 word_count（叶子节用自己的 word_count，section 节用子结构求和）
        if not subs:
            s.setdefault("word_count", 800)
        else:
            s["word_count"] = sum(ss["word_count"] for ss in subs)

    return outline


def plan_outline(topic: str, template: dict = None,
                 user_meta: dict = None, llm_client: LLMClient = None,
                 prompt: str = "") -> dict:
    """
    生成结构化大纲。

    参数:
        topic: 写作主题
        template: {structure: [五元组], style: "..."}
        user_meta: 用户已填的字段值 {"标题": "xxx", "作者": "吴王思淼"}
        llm_client: LLM 客户端
        prompt: 旧兼容参数 — 作为风格提示词覆盖

    返回:
        dict: 大纲 JSON {title, meta, sections}
    """
    if llm_client is None:
        raise ValueError("需要提供 llm_client")

    # 处理旧接口兼容：如果 template 是字符串，当作旧 style prompt
    if isinstance(template, str) or template is None:
        # 老式调用 plan_outline(topic, prompt="xxx", llm_client=cli)
        # 构建一个最小 fallback 模板
        style = template or prompt or ""
        template = {
            "structure": [
                {"name": "标题", "show_label": False, "desc": "文章标题",
                 "source": "auto" if not topic else "user", "type": "leaf"},
                {"name": "正文", "show_label": False, "desc": "文章主体按逻辑拆子节",
                 "source": "llm", "type": "section"},
            ],
            "style": style
        }
        if not user_meta:
            user_meta = {"标题": topic} if topic else {}

    if user_meta is None:
        user_meta = {}

    structure = template.get("structure", [])
    style = template.get("style", prompt or "")

    # 构建 system prompt
    system_prompt = _build_planner_prompt(structure, user_meta)

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

    # 最多重试 3 次
    outline = None
    last_raw = ""
    for attempt in range(3):
        plan_max_tokens = max(4096, llm_client.max_tokens)
        raw = llm_client.chat(messages, max_tokens=plan_max_tokens, temperature=None)
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
    outline = _normalize_outline(outline, structure, user_meta)

    return outline
