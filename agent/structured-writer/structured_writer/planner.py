"""大纲规划器 — 调用 LLM 生成结构化文章大纲"""
import json
from typing import Optional
from .llm_client import LLMClient, LLMClientError

OUTLINE_SYSTEM_PROMPT = """你是结构化写作规划助手。严格执行以下命令：

【输出规则】
- 只输出 JSON，禁止任何其他文字、解释、礼貌用语。
- 禁止 markdown 代码块标记（不要 ```json）。
- 直接以 { 开头，以 } 结尾。
- JSON 结构（字段名、层级）严格按下方【JSON 格式】执行，不可增减字段。仅 sections 数量和 sub_sections 数量可依据用户指令或默认值调整。

【JSON 格式】
{
  "title": "文章标题",
  "sections": [
    {
      "id": "s1",
      "title": "一级标题",
      "subtitle": "二级标题或简述",
      "summary": "本节总览和写作目标，50-100字",
      "word_count": 1200,
      "is_key": false,
      "sub_sections": [
        {
          "id": "s1_1",
          "title": "子标题1",
          "summary": "本节的写作要点，30-50字",
          "word_count": 400
        },
        {
          "id": "s1_2",
          "title": "子标题2",
          "summary": "本节的写作要点，30-50字",
          "word_count": 400
        },
        {
          "id": "s1_3",
          "title": "子标题3",
          "summary": "本节的写作要点，30-50字",
          "word_count": 400
        }
      ]
    }
  ]
}

【约束】
- 优先遵循用户明确指定的结构要求（章节数、子结构数、字数等），以下为默认建议值
- 如用户未指定，sections 数量：4-10 个
- 每节 sub_sections 数量：2-4 个
- 每节 word_count = 各 sub_section word_count 之和
- sub_section word_count 范围：200-800 字
- is_key: true = 重点节，字数可上浮 50%
- summary 必须包含本节要论证的核心观点或要回答的问题
- 各节之间要逻辑递进、前后连贯
- subtitle 可以为空字符串

【后果】如果输出包含 JSON 以外的任何文字，系统将无法解析，整个流程会失败。
"""


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
        # 跳过可能在第一行的语言标识
        content = text[start:end].strip()
        if content.startswith("json\n"):
            content = content[5:]
        try:
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            pass

    # 尝试找到第一个 { 或 [ 提取 JSON
    brace_start = -1
    for ch, quote in [("{", "}"), ("[", "]")]:
        pos = text.find(ch)
        if pos >= 0:
            brace_start = pos
            # 从该位置截取并尝试解析
            candidate = text[pos:]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # 可能尾部有多余文字，逐行截断重试
                lines = candidate.split("\n")
                for cut in range(len(lines), 0, -1):
                    try:
                        return json.loads("\n".join(lines[:cut]))
                    except json.JSONDecodeError:
                        continue
            break

    return None


def plan_outline(topic: str, prompt: str = "",
                 llm_client: LLMClient = None) -> dict:
    """
    生成结构化大纲

    参数:
        topic: 写作主题
        prompt: 额外写作要求/风格说明
        llm_client: LLM 客户端实例

    返回:
        dict: 大纲 JSON {title, sections: [...]}

    异常:
        LLMClientError: LLM 调用失败
        ValueError: 解析失败
    """
    if llm_client is None:
        raise ValueError("需要提供 llm_client")

    user_msg = f"主题：{topic}\n"
    if prompt:
        user_msg += f"写作要求：\n{prompt}\n"
    user_msg += "\n请生成文章大纲。"

    messages = [
        {"role": "system", "content": OUTLINE_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg}
    ]

    # 最多重试 2 次（含首次）
    outline = None
    last_raw = ""
    for attempt in range(3):
        # 推理模型需要为 thinking 预留 token，最低保底 4096
        plan_max_tokens = max(4096, llm_client.max_tokens)
        raw = llm_client.chat(messages, max_tokens=plan_max_tokens, temperature=None)
        last_raw = raw
        outline = parse_outline(raw)

        if outline is not None:
            break  # 解析成功

        # 解析失败 → 追加纠正指令重试
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

    # 校验
    if not outline.get("title"):
        outline["title"] = topic
    if not outline.get("sections"):
        raise ValueError("大纲中必须包含 sections 列表")

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

        # 子结构规范化
        subs = s.get("sub_sections", [])
        if not subs:
            # LLM 没生成子结构时，用整节作为单个子结构
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
            ss.setdefault("word_count", max(200, s.get("word_count", 800) // len(subs)))
            ss.setdefault("status", "pending")
            ss.setdefault("actual_word_count", 0)
            ss.setdefault("_checked", True)
            ss.setdefault("aux_knowledge", None)
        # 纠正 section 级 word_count 为子结构之和
        s["word_count"] = sum(ss["word_count"] for ss in subs)

    return outline
