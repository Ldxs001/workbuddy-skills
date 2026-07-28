"""串行写作器 — 逐节写作 + context_loader + .md 输出"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from .llm_client import LLMClient, LLMClientError
from .state_manager import StateManager, OUTPUTS_DIR

WRITER_SYSTEM_PROMPT = """你是一个结构化文章写作助手。
请根据提供的主题、大纲、前文上下文和参考资料，写出指定节的内容。

要求：
- 只输出正文（Markdown 格式），不要额外说明、不要元数据
- 语言风格：客观、专业、逻辑清晰
- 字数要求：尽量接近指定的字数
- 与前文保持逻辑连贯
"""


def _build_context_section_prompt(
    topic: str,
    section_title: str,
    section_subtitle: str,
    section_summary: str,
    word_count: int,
    is_key: bool,
    context_buffer: str,
    rag_context: Optional[str],
    aux_text: Optional[str] = None
) -> str:
    """构建单节写作 prompt"""
    blocks = []

    blocks.append(f"# 文章主题\n\n{topic}")
    blocks.append(f"# 正写作的子结构\n\n### {section_title}\n{subtitle if (subtitle := section_subtitle) else ''}")

    word_note = f"字数要求：约 {word_count} 字"
    if is_key:
        word_note += "（重点节，可上浮 50%）"
    blocks.append(word_note)

    blocks.append(f"写作要点：\n{section_summary}")

    if context_buffer:
        blocks.append(f"前文回顾（保持连贯性）：\n\n{context_buffer}")

    if rag_context:
        blocks.append(f"【RAG 参考资料】（来自知识库检索，请结合文章主题选择性引用）：\n\n{rag_context}")

    if aux_text:
        blocks.append(f"【辅助知识】（用户指定参考内容，请优先采用）：\n\n{aux_text}")

    blocks.append("请写出该节正文（Markdown 格式）。只输出正文，不输出标题行。")

    return "\n\n---\n\n".join(blocks)


def generate_article(
    outline: dict,
    user_orders: dict,
    rag_options: Optional[dict],
    llm_client: LLMClient,
    state_mgr: StateManager,
    rag_client=None,
    aux_knowledge: Optional[dict] = None,
    context_review_length: int = 800,
    fact_check_enabled: bool = False,
    stop_check=None,
    template: Optional[dict] = None
) -> tuple[str, str]:
    """
    逐节串行写作，返回 (md_content, output_filepath)

    参数:
        outline: 大纲字典 {title, sections: [...]}
        user_orders: {section_id: order_number}
        rag_options: {section_id: {enabled: bool, kb: str}}
        llm_client: LLM 写作客户端
        state_mgr: 状态管理器
        rag_client: 可选的 RAG 客户端
        template: {structure: [五元组], style: "..."} 用于 meta 渲染
    """
    sections = outline.get("sections", [])
    title = outline.get("title", "未命名文章")
    structure = (template or {}).get("structure", [])

    # 按用户排序排列
    if user_orders:
        def sort_key(s):
            return user_orders.get(s["id"], 999)
        sections = sorted(sections, key=sort_key)

    state_mgr.set_phase("writing")

    context_buffer = ""
    all_parts = []
    sub_fact_notes = []  # 每个子结构的自检记录

    # 标记是否已找到第一个 leaf（用于 # 标题渲染）
    _first_leaf_rendered = False

    for i, section in enumerate(sections):
        sid = section["id"]
        state_mgr.update_section(sid, {"status": "in_progress"})

        s_type = section.get("type", "section")
        subs = section.get("sub_sections", [])

        # leaf 类型不自动补子结构；section 类型 LLM 漏了则补一个
        if not subs and s_type == "section":
            subs = [{
                "id": f"{sid}_1",
                "title": section.get("subtitle") or section["title"],
                "summary": section.get("summary", ""),
                "word_count": section.get("word_count", 800),
            }]

        # ── 两级 RAG 查询 ──
        rag_opt = (rag_options or {}).get(sid, {})
        rag_enabled = rag_opt.get("enabled") and rag_client is not None
        kb = rag_opt.get("kb", "")

        section_rag_context = None
        sub_rag_contexts = {}  # {sub_id: context_text}

        if rag_enabled:
            # 节级别 RAG（背景资料）
            state_mgr.set_status_text(f"RAG查询: {kb or '自动'} → {section['title']}（整节背景）")
            try:
                q = f"{title} {section['title']} {section['summary']}"
                r = rag_client.query(kb, q)
                ctx = r.get("context", "").strip()
                if ctx:
                    section_rag_context = ctx
                    cnt = len(r.get("sources", []))
                    state_mgr.set_status_text(f"RAG完成: {kb or '自动'} → {section['title']}（{cnt}条）")
                else:
                    state_mgr.set_status_text(f"RAG无结果: {kb or '自动'} → {section['title']}")
            except Exception as e:
                state_mgr.set_status_text(f"RAG超时: {kb or '自动'} → {section['title']}")

            # 子结构级别 RAG（针对性资料）
            for sub in subs:
                ssid = sub["id"]
                state_mgr.set_status_text(f"RAG查询: {kb or '自动'} → {sub['title']}")
                try:
                    q = f"{section['title']} {sub['title']} {sub.get('summary', '')}"
                    r = rag_client.query(kb, q)
                    ctx = r.get("context", "").strip()
                    if ctx:
                        sub_rag_contexts[ssid] = ctx
                        cnt = len(r.get("sources", []))
                        state_mgr.set_status_text(f"RAG完成: {kb or '自动'} → {sub['title']}（{cnt}条）")
                    else:
                        state_mgr.set_status_text(f"RAG无结果: {kb or '自动'} → {sub['title']}")
                except Exception as e:
                    state_mgr.set_status_text(f"RAG超时: {kb or '自动'} → {sub['title']}")

        # 写入节标题（第一个 leaf → #，其他 → ##）
        wrote_any = False

        if s_type == "leaf" and not _first_leaf_rendered:
            _first_leaf_rendered = True
            section_md = f"\n\n# {section['title']}\n\n"
        else:
            section_md = f"\n\n## {section['title']}\n\n"
        if section.get("subtitle"):
            section_md += f"*{section['subtitle']}*\n\n"

        if s_type == "leaf":
            # leaf 类型：无子结构，一个调用写全部内容
            # 构建一个单次写作调用
            prompt = _build_context_section_prompt(
                topic=title,
                section_title=section["title"],
                section_subtitle=section.get("subtitle", ""),
                section_summary=section.get("summary", ""),
                word_count=section.get("word_count", 800),
                is_key=section.get("is_key", False),
                context_buffer=context_buffer[-context_review_length:] if context_buffer else "",
                rag_context=None,
                aux_text=None
            )
            messages = [
                {"role": "system", "content": WRITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            try:
                accumulated = ""
                cont_messages = messages.copy()
                for attempt in range(6):
                    if stop_check and stop_check() == "immediate":
                        break
                    result = llm_client.chat_detailed(cont_messages, max_tokens=None, temperature=None)
                    chunk = result.get("content", "")
                    finish_reason = result.get("finish_reason", "stop")
                    accumulated += chunk
                    if finish_reason != "length":
                        break
                    if not chunk.strip():
                        break
                    cont_messages.append({"role": "assistant", "content": chunk})
                    cont_messages.append({"role": "user", "content": "请继续写，紧接着上一段的结尾，不要重复已写过的内容。"})
            except LLMClientError as e:
                accumulated = f"\n\n> **写作失败**: {e}\n\n"
            content = accumulated.strip()
            if content:
                wrote_any = True
                section_md += f"\n{content}\n\n"
                context_buffer += content
                actual_chars = len(content.replace(" ", "").replace("\n", ""))
                state_mgr.update_section(sid, {"status": "done", "actual_word_count": actual_chars})
            continue  # 跳过子结构循环

        for j, sub in enumerate(subs):
            # 停止检测：延时停止检查点（子结构边界）
            if stop_check:
                st = stop_check()
                if st == "immediate":
                    # 立即停止：跳过当前及后续子结构
                    state_mgr.set_status_text(f"已停止: {sub['title']}（立即停止）")
                    break
                elif st == "delay":
                    state_mgr.set_status_text(f"当前子结构完成后停止: {sub['title']}")
            ssid = sub["id"]
            state_mgr.update_section(ssid, {"status": "in_progress"})
            state_mgr.set_status_text(f"写作中: {sub['title']}")

            # 构建 context prompt（两级 RAG 上下文）
            ctx_buffer = context_buffer[-context_review_length:] if context_buffer else ""

            # 拼装本子结构的 RAG 上下文
            sub_rag = sub_rag_contexts.get(ssid, section_rag_context)
            if sub_rag and section_rag_context and sub_rag != section_rag_context:
                # 两个都有且不同 → 分背景+针对性
                combined_rag = (
                    f"【背景资料】（本节整体相关）\n{section_rag_context}\n\n"
                    f"---\n\n"
                    f"【针对性资料】（针对当前子结构）\n{sub_rag}"
                )
            elif sub_rag:
                combined_rag = sub_rag
            else:
                combined_rag = section_rag_context  # 可能 None

            # 提取当前子结构的辅助知识文本
            sub_aux = None
            if aux_knowledge:
                ak = aux_knowledge.get(ssid, {}) or {}
                aux_parts = []
                if ak.get("text"):
                    aux_parts.append(ak["text"])
                if ak.get("files"):
                    for f in ak["files"]:
                        if f.get("content"):
                            aux_parts.append(f"[{f.get('name', 'file')}]\n{f['content']}")
                if aux_parts:
                    sub_aux = "\n\n---\n\n".join(aux_parts)

            prompt = _build_context_section_prompt(
                topic=title,
                section_title=sub["title"],
                section_subtitle="",
                section_summary=sub.get("summary", ""),
                word_count=sub.get("word_count", 400),
                is_key=section.get("is_key", False),
                context_buffer=ctx_buffer,
                rag_context=combined_rag,
                aux_text=sub_aux
            )

            messages = [
                {"role": "system", "content": WRITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            # 启用自检时，在写作指令末尾追加标记要求
            if fact_check_enabled:
                messages[1]["content"] += (
                    "\n\n写完后，在末尾另起一行用「【事实待核查】」标注本节中你"
                    "不确定准确性的数据、前沿信息或案例。"
                    "如果没有需标注的内容，写「【事实待核查】无」。"
                )

            try:
                accumulated = ""
                cont_messages = messages.copy()
                for attempt in range(6):  # 首次 + 最多 5 次续写
                    # 停止检测：立即停止检查点（续写边界）
                    if stop_check and stop_check() == "immediate":
                        state_mgr.set_status_text("已停止（立即停止）")
                        break
                    result = llm_client.chat_detailed(
                        cont_messages,
                        max_tokens=None,
                        temperature=None
                    )
                    chunk = result.get("content", "")
                    finish_reason = result.get("finish_reason", "stop")
                    accumulated += chunk

                    if finish_reason != "length":
                        break  # 写完了

                    # content 为空却被截断 → 推理吃光了 token，没有可续的内容
                    # 续写也救不了，直接放弃
                    if not chunk.strip():
                        break

                    # token 用完被截断 → 追加续写指令
                    cont_messages.append({
                        "role": "assistant",
                        "content": chunk
                    })
                    cont_messages.append({
                        "role": "user",
                        "content": "请继续写，紧接着上一段的结尾，不要重复已写过的内容。"
                    })
            except LLMClientError as e:
                accumulated = f"\n\n> **写作失败**: {e}\n\n"

            content = accumulated.strip()

            # 跳过空内容（推理模型吃光 token 导致 content=""）
            if not content:
                continue

            # 解析自检标记：将「【事实待核查】」后的内容提取到 sub_fact_notes
            if fact_check_enabled and "【事实待核查】" in content:
                parts = content.split("【事实待核查】", 1)
                content = parts[0].strip()
                marker = parts[1].strip()
                if marker and marker != "无":
                    sub_fact_notes.append(f"{sub['title']}: {marker[:200]}")

            wrote_any = True

            # 子结构标题
            sub_md = f"### {sub['title']}\n\n{content}\n"

            section_md += sub_md
            context_buffer += sub_md

            actual_chars = len(content.replace(" ", "").replace("\n", ""))
            state_mgr.update_section(ssid, {
                "status": "done",
                "actual_word_count": actual_chars
            })

        if wrote_any:
            all_parts.append(section_md)

        actual_chars = len(section_md.replace(" ", "").replace("\n", "")) if wrote_any else 0
        state_mgr.update_section(sid, {
            "status": "done" if wrote_any else "pending",
            "actual_word_count": actual_chars
        })

    # 合并全文
    # ── meta 块渲染（根据 structure 五元组的 show_label） ──
    meta_lines = []
    for field in structure:
        fname = field["name"]
        v = outline.get("meta", {}).get(fname)
        if not v:
            continue
        if field.get("show_label", True):
            meta_lines.append(f"> {fname}：{v}")
        else:
            meta_lines.append(f"> {v}")
    meta_block = "\n".join(meta_lines) + "\n\n" if meta_lines else ""

    article_md = f"# {title}\n{meta_block}" + "".join(all_parts)

    # 去掉开头的多余空行
    article_md = article_md.strip()

    # ── 事实自检汇总 ──
    if fact_check_enabled:
        review_lines = [
            "## 建议人工复审（事实捏造风险较高）",
            "",
            f"以下由AI写作模型在写作过程中自动标记，请人工核实（共检查 {len(sub_fact_notes)} 项）：",
            "",
        ]
        if sub_fact_notes:
            for i, note in enumerate(sub_fact_notes):
                review_lines.append(f"{i+1}. {note}")
        else:
            review_lines.append("未发现需标记的问题。")
        article_md += "\n\n---\n\n" + "\n".join(review_lines)

    # 写入文件
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-")
    safe_title = safe_title.strip() or "untitled"
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{now}.md"
    output_path = OUTPUTS_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(article_md)

    state_mgr.set_output_file(str(output_path))
    state_mgr.set_phase("done")

    return article_md, str(output_path)
