"""串行写作器 — 逐节写作 + context_loader + .md 输出"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from .llm_client import LLMClient, LLMClientError
from .state_manager import StateManager, OUTPUTS_DIR
from .citation_validator import post_process as citation_post_process

# 写入异常日志到 writer_error.log
_logger = logging.getLogger("writer")
_logger.setLevel(logging.ERROR)
_fh = logging.FileHandler("writer_error.log", mode="a", encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [ERROR] %(message)s"))
_logger.addHandler(_fh)

WRITER_SYSTEM_PROMPT = """你是一个结构化文章写作助手。
请根据提供的主题、大纲、前文上下文和参考资料，写出指定节的内容。

要求：
- 只输出正文（Markdown 格式），不要额外说明、不要元数据
- 语言风格：客观、专业、逻辑清晰
- 字数要求：尽量接近指定的字数
- 与前文保持逻辑连贯
"""


# ── 引用元数据开关（自然语言驱动） ──

def _needs_metadata(style_text: str) -> bool:
    """从模板 style 字段检测是否需要 RAG 文档元数据。
    
    检测关键词：引用、参考文献、citation、引用规则、参考文献格式。
    纯自然语言驱动，不依赖配置字段。
    """
    keywords = ["引用", "参考文献", "citation", "引用规则", "参考文献格式"]
    return any(kw in style_text for kw in keywords)


def _build_headers_text(all_rag_headers: dict) -> Optional[str]:
    """将累积的文档元数据格式化为 prompt 中可注入的文本"""
    if not all_rag_headers:
        return None
    lines = []
    for i, (src, header_texts) in enumerate(all_rag_headers.items(), 1):
        # 取前几个 header 块拼接（标题+作者就够了）
        meta_info = " / ".join(t.strip() for t in header_texts[:3] if t.strip())
        lines.append(f"来源{i}: {meta_info}")
    return "\n".join(lines) if lines else None


def _build_context_section_prompt(
    topic: str,
    section_title: str,
    section_subtitle: str,
    section_summary: str,
    word_count: int,
    is_key: bool,
    context_buffer: str,
    rag_context: Optional[str],
    aux_text: Optional[str] = None,
    logic_hint: str = "",
    style_hint: str = "",
    headers_text: Optional[str] = None,
    section_desc: str = ""
) -> str:
    """构建单节写作 prompt，各区域标识明确，LLM 能区分用途"""
    blocks = []

    blocks.append(f"# 文章主题\n\n{topic}")

    if logic_hint:
        blocks.append(f"写作阶段提示：{logic_hint}")

    if style_hint:
        blocks.append(f"【全文风格背景，所有章节通用】（仅作为整体行文风格参考，当前节的写作要求以「当前章节要求」为准）\n{style_hint}")

    # ── 前文回顾 ──
    if context_buffer:
        blocks.append(f"【前文回顾】（已完成的内容，用于了解文章逻辑走向，不要重复书写）\n\n{context_buffer}")

    # ── 当前章节要求 ──
    sec_reqs = []
    if word_count > 0:
        wn = f"字数要求：约 {word_count} 字"
        if is_key:
            wn += "（重点节，可上浮 50%）"
        sec_reqs.append(wn)
    else:
        sec_reqs.append("字数不限：根据写作要点自由发挥，该节必须输出有效内容，不得留空")
    sec_reqs.append(f"写作要点：\n{section_summary}")
    # 模板 desc 权威指令：确定性注入，不依赖规划器转述
    if section_desc:
        sec_reqs.append(f"本节要求：\n{section_desc}")
    blocks.append(f"【当前章节要求】\n" + "\n".join(sec_reqs))

    # ── 引用来源 ──
    if headers_text:
        blocks.append("【引用来源】（正文引用时使用「引用自来源N」或「引自来源N」格式标注，如「引用自来源1」，不要直接使用编号格式）：\n\n" + headers_text)

    if rag_context:
        blocks.append(f"【RAG 参考资料】（来自知识库检索，结合主题选择性参考）：\n\n{rag_context}")

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
    fact_check_enabled: bool = False,
    context_review_length: int = 0,
    stop_check=None,
    template: Optional[dict] = None,
    citation_config: Optional[dict] = None
) -> tuple[str, str]:
    """
    逐节串行写作，返回 (md_content, output_filepath)

    参数:
        outline: 大纲字典 {title, meta, sections: [...]}
        user_orders: {section_id: order_number}
        rag_options: {section_id: {enabled: bool, kb: str}}
        llm_client: LLM 写作客户端
        state_mgr: 状态管理器
        rag_client: 可选的 RAG 客户端
        template: {meta: [...], content: [...], style: "...", logic: "..."}
        citation_config: {section_title: {"enabled": bool, "format": str}}
    """
    sections = outline.get("sections", [])
    title = outline.get("title", "未命名文章")
    meta_fields = (template or {}).get("meta", [])
    content_fields = (template or {}).get("content", [])
    logic_prompt = (template or {}).get("logic", "")
    style_prompt = (template or {}).get("style", "")
    # 模板 desc 权威指令查找表：写作时按节名确定性注入【当前章节要求】
    desc_by_title = {cf.get("name"): cf.get("desc", "") for cf in content_fields}

    # ── 提示词开关：根据 style + content desc 判断是否需要 RAG 文档元数据 ──
    needs_metadata = _needs_metadata(style_prompt)
    # 引用规则可能在 content 项的 desc 中（如参考文献）
    if not needs_metadata and content_fields:
        needs_metadata = any(
            "引用" in (cf.get("desc") or "") or "参考文献" in (cf.get("desc") or "")
            for cf in content_fields
        )

    # ── 写作顺序 vs 输出顺序 ──
    # 写作按逻辑顺序，不设_logical_order 的节按 content[] 顺序
    # 输出按 content[]/用户调整后的顺序重排
    if user_orders:
        output_order = sorted(sections, key=lambda s: user_orders.get(s["id"], 999))
    else:
        content_order = {cf["name"]: i for i, cf in enumerate(content_fields)}
        output_order = sorted(sections, key=lambda s: content_order.get(s.get("title", ""), 999))

    # 只有模板设置了 logical_order 时才重排写入顺序
    has_logic = any(s.get("_logical_order") is not None for s in sections)
    if has_logic:
        sections = sorted(sections, key=lambda s: s.get("_logical_order") or 0)
    else:
        # 按输出顺序写（没设逻辑顺序时写=输出）
        sections = list(output_order)

    state_mgr.set_phase("writing")

    context_buffer = ""
    parts_by_sid = {}
    sub_fact_notes = []
    all_rag_headers = {}  # 累积所有 RAG 查询的文档元数据

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
        sub_rag_contexts = {}

        if rag_enabled:
            state_mgr.set_status_text(f"RAG查询: {kb or '自动'} → {section['title']}（整节背景）")
            try:
                q = f"{title} {section['title']} {section['summary']}"
                r = rag_client.query(kb, q, include_header=needs_metadata)
                ctx = r.get("context", "").strip()
                if ctx:
                    section_rag_context = ctx
                    cnt = len(r.get("sources", []))
                    state_mgr.set_status_text(f"RAG完成: {kb or '自动'} → {section['title']}（{cnt}条）")
                else:
                    state_mgr.set_status_text(f"RAG无结果: {kb or '自动'} → {section['title']}")
                # 累积文档元数据
                if needs_metadata and r.get("headers"):
                    all_rag_headers.update(r["headers"])
            except Exception as e:
                state_mgr.set_status_text(f"RAG超时: {kb or '自动'} → {section['title']}")

            for sub in subs:
                ssid = sub["id"]
                state_mgr.set_status_text(f"RAG查询: {kb or '自动'} → {sub['title']}")
                try:
                    q = f"{section['title']} {sub['title']} {sub.get('summary', '')}"
                    r = rag_client.query(kb, q, include_header=needs_metadata)
                    ctx = r.get("context", "").strip()
                    if ctx:
                        sub_rag_contexts[ssid] = ctx
                        cnt = len(r.get("sources", []))
                        state_mgr.set_status_text(f"RAG完成: {kb or '自动'} → {sub['title']}（{cnt}条）")
                    else:
                        state_mgr.set_status_text(f"RAG无结果: {kb or '自动'} → {sub['title']}")
                    if needs_metadata and r.get("headers"):
                        all_rag_headers.update(r["headers"])
                except Exception as e:
                    state_mgr.set_status_text(f"RAG超时: {kb or '自动'} → {sub['title']}")

        # 写入节标题
        # 所有内容树节统一用 ## 级别（# 已用于文章标题）
        # show_label 控制是否显示标题行，false 且有内容时纯内容，false 且空时跳过
        sec_show_label = section["show_label"]
        wrote_any = False

        if sec_show_label:
            section_md = f"\n\n## {section['title']}\n\n"
            if section.get("subtitle"):
                section_md += f"*{section['subtitle']}*\n\n"
        else:
            section_md = ""

        if s_type == "leaf":
            # 如果节启用了引用校验，完全跳过 LLM 写作，由后处理接管
            if citation_config and section["title"] in citation_config:
                _cc = citation_config[section["title"]]
                if _cc.get("enabled"):
                    # 只留标题行，内容由 citation_post_process 填充
                    parts_by_sid[sid] = f"\n\n## {section['title']}\n\n" if section.get("show_label", True) else ""
                    state_mgr.update_section(sid, {"status": "done", "actual_word_count": 0})
                    continue
            leaf_headers_text = _build_headers_text(all_rag_headers)
            prompt = _build_context_section_prompt(
                topic=title,
                section_title=section["title"],
                section_subtitle=section.get("subtitle", ""),
                section_summary=section.get("summary", ""),
                word_count=section.get("word_count", 800),
                is_key=section.get("is_key", False),
                context_buffer=(context_buffer or "") if section.get("_logical_order") == 2 else (context_buffer[-context_review_length:] if context_buffer and context_review_length else (context_buffer or "")),
                rag_context=section_rag_context,
                aux_text=None,
                logic_hint=logic_prompt,
                style_hint=style_prompt,
                headers_text=leaf_headers_text,
                section_desc=desc_by_title.get(section["title"], "")
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
            # 同步设置 parts_by_sid：leaf 走特殊路径，必须在这里处理
            if wrote_any:
                parts_by_sid[sid] = section_md
            elif section["show_label"]:
                parts_by_sid[sid] = f"\n\n## {section['title']}\n\n"
            # show_label=false + 空 → 不写入
            state_mgr.update_section(sid, {
                "status": "done" if wrote_any else "pending",
                "actual_word_count": len(section_md.replace(" ", "").replace("\n", "")) if wrote_any else 0
            })
            continue

        for j, sub in enumerate(subs):
            if stop_check:
                st = stop_check()
                if st == "immediate":
                    state_mgr.set_status_text(f"已停止: {sub['title']}（立即停止）")
                    break
                elif st == "delay":
                    state_mgr.set_status_text(f"当前子结构完成后停止: {sub['title']}")
            ssid = sub["id"]
            state_mgr.update_section(ssid, {"status": "in_progress"})
            state_mgr.set_status_text(f"写作中: {sub['title']}")

            ctx_buffer = context_buffer[-context_review_length:] if context_buffer and context_review_length > 0 else (context_buffer or "")

            sub_rag = sub_rag_contexts.get(ssid, section_rag_context)
            if sub_rag and section_rag_context and sub_rag != section_rag_context:
                combined_rag = (
                    f"【背景资料】（本节整体相关）\n{section_rag_context}\n\n"
                    f"---\n\n"
                    f"【针对性资料】（针对当前子结构）\n{sub_rag}"
                )
            elif sub_rag:
                combined_rag = sub_rag
            else:
                combined_rag = section_rag_context

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

            sub_headers_text = _build_headers_text(all_rag_headers)

            # 将 RAG 参考资料中的 【文档: filename】 替换为 【来源N】
            if combined_rag and all_rag_headers:
                _rag_keys = list(all_rag_headers.keys())
                for _ri, _rk in enumerate(_rag_keys, 1):
                    combined_rag = combined_rag.replace(f"【文档: {_rk}】", f"【来源{_ri}】")

            prompt = _build_context_section_prompt(
                topic=title,
                section_title=sub["title"],
                section_subtitle="",
                section_summary=sub.get("summary", ""),
                word_count=sub.get("word_count", 400),
                is_key=section.get("is_key", False),
                context_buffer=ctx_buffer,
                rag_context=combined_rag,
                aux_text=sub_aux,
                logic_hint=logic_prompt,
                style_hint=style_prompt,
                headers_text=sub_headers_text,
                section_desc=desc_by_title.get(section["title"], "")
            )

            messages = [
                {"role": "system", "content": WRITER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            if fact_check_enabled:
                messages[1]["content"] += (
                    "\n\n写完后，在末尾另起一行用「【事实待核查】」标注本节中你"
                    "不确定准确性的数据、前沿信息或案例。"
                    "如果没有需标注的内容，写「【事实待核查】无」。"
                )

            try:
                accumulated = ""
                cont_messages = messages.copy()
                for attempt in range(6):
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
                        break
                    if not chunk.strip():
                        break
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

            if not content:
                continue

            if fact_check_enabled and "【事实待核查】" in content:
                parts = content.split("【事实待核查】", 1)
                content = parts[0].strip()
                marker = parts[1].strip()
                if marker and marker != "无":
                    sub_fact_notes.append(f"{sub['title']}: {marker[:200]}")

            wrote_any = True
            sub_md = f"### {sub['title']}\n\n{content}\n"

            section_md += sub_md
            context_buffer += sub_md

            actual_chars = len(content.replace(" ", "").replace("\n", ""))
            state_mgr.update_section(ssid, {
                "status": "done",
                "actual_word_count": actual_chars
            })

        # show_label 控制空节处理：true=保留标题，false=彻底跳过
        if wrote_any:
            parts_by_sid[sid] = section_md
        elif sec_show_label:
            parts_by_sid[sid] = f"\n\n## {section['title']}\n\n"
        # show_label=false + 空 → 不加入 parts_by_sid，输出时跳过

        actual_chars = len(section_md.replace(" ", "").replace("\n", "")) if wrote_any else 0
        state_mgr.update_section(sid, {
            "status": "done" if wrote_any else "pending",
            "actual_word_count": actual_chars
        })

    # ── meta 块渲染 ──
    # show_label=true → 显示标签（无论是否有值）
    # show_label=false → 无标签，有值才渲染，没值跳过
    meta_lines = []
    for field in meta_fields:
        fname = field["name"]
        v = outline.get("meta", {}).get(fname, "")
        show = field.get("show_label", True)
        if show:
            meta_lines.append(f"> {fname}：{v}" if v else f"> {fname}：")
        elif v:
            meta_lines.append(f"> {v}")
    meta_block = "\n".join(meta_lines) + "\n\n" if meta_lines else ""

    # 按输出顺序重排（逻辑写完了，按 content[]/用户顺序输出）
    article_md = f"# {title}\n{meta_block}" + "".join(parts_by_sid[s["id"]] for s in output_order if s["id"] in parts_by_sid)

    # 去掉开头的多余空行
    article_md = article_md.strip()

    # ── 引用后处理：打勾时才执行 ──
    article_md = citation_post_process(article_md, citation_config, all_rag_headers, llm_client)

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
