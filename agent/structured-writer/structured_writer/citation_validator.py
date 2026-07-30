"""引用验证器 — 对生成的文章做格式/一致性/来源三项验证

支持双格式映射：如 "[x]=1." 表示正文用 [x]，参考文献条目用 1.
"""

import re
from typing import Optional


def _parse_citation_format(fmt: str) -> str:
    """将单格式转为带捕获组的正则。

    有 x 占位符: [x] / (x)
    无占位符: 数字即占位 (1. / [1])
    """
    pattern = re.escape(fmt)
    if "x" in pattern or "X" in pattern or "n" in pattern or "N" in pattern:
        pattern = pattern.replace("x", r"(\d+)").replace("X", r"(\d+)").replace("n", r"(\d+)").replace("N", r"(\d+)")
    else:
        # 无显式占位符：格式中所有数字视为编号占位符
        pattern = re.sub(r"\d+", r"(\\d+)", pattern)
    return pattern


def _parse_citation_format_plain(fmt: str) -> str:
    """返回纯文本格式描述。 [x] → [数字]  1. → 数字. """
    if "x" in fmt or "X" in fmt or "n" in fmt or "N" in fmt:
        return fmt.replace("x", "数字").replace("X", "数字").replace("N", "数字")
    else:
        return re.sub(r"\d+", "数字", fmt)


def _parse_citation_mapping(mapping: str) -> tuple:
    """解析双格式映射 "[x]=1." → ("[x]", "1.")

    仅输入 "[x]" 时 → ("[x]", "[x]")  （旧格式兼容）
    """
    parts = mapping.split("=", 1)
    if len(parts) == 2:
        inline_fmt = parts[0].strip()
        ref_fmt = parts[1].strip()
    else:
        inline_fmt = ref_fmt = parts[0].strip()
    return inline_fmt, ref_fmt


def _extract_section_ranges(md_text: str):
    """解析 markdown，返回所有 ## 节的范围。"""
    sections = []
    pattern = re.compile(r"^(#{2,})\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(md_text))
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        sections.append((title, start, end))
    return sections


def _get_section_content(md_text: str, start: int, end: int) -> str:
    """提取节的实际内容（去掉标题行）"""
    content = md_text[start:end]
    lines = content.split("\n", 1)
    return lines[1].strip() if len(lines) > 1 else ""


def _extract_all_citations(md_text: str, pattern: str) -> list:
    """从全文提取所有引用编号，保持出现顺序"""
    nums = []
    for m in re.finditer(pattern, md_text):
        nums.append(int(m.group(1)))
    return nums


def _extract_reference_entries(md_text: str, pattern: str) -> list:
    """从全文提取每条引用条目及其编号。"""
    entries = []
    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\s*" + pattern + r"\s*(.*)", line)
        if m:
            num = int(m.group(1))
            text = m.group(2).strip()
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if re.match(r"^\s*" + pattern, next_line):
                    break
                if not next_line.strip():
                    i += 1
                    continue
                text += " " + next_line.strip()
                i += 1
            entries.append((num, text))
        else:
            i += 1
    return entries


def _split_ref_entry_for_matching(entry_text: str) -> list:
    """把参考文献条目切成候选匹配片段，取最长片段做子串匹配。"""
    clean = re.sub(r"\[[A-Za-z]+\]", "", entry_text)
    segments = re.split(r"[，。．,\.；;：:、\s]{2,}", clean)
    segments = [s.strip() for s in segments if len(s.strip()) >= 4]
    segments.sort(key=len, reverse=True)
    return segments


def _match_entry_with_headers(entry_text: str, segments: list,
                               all_rag_headers: dict) -> Optional[str]:
    """尝试将条目与 headers 匹配，返回来源文件名或 None。"""
    for src_name, header_texts in all_rag_headers.items():
        combined = " ".join(header_texts)
        for seg in segments:
            if seg in combined:
                return src_name
        if segments and segments[0] in src_name:
            return src_name
    return None


def validate(md_text: str, all_rag_headers: Optional[dict] = None,
             citation_config: Optional[dict] = None) -> dict:
    """执行引用验证。

    参数:
        md_text: 完整文章 markdown
        all_rag_headers: RAG 查询累积的文档元数据 {文件名: [文本块]}
        citation_config: {section_title: {"enabled": bool, "format": str}}
                         format 支持 "[x]=1." 双格式映射

    返回:
        {
            "format_check": [...],
            "consistency_check": {...},
            "source_check": [...],
            "summary": str
        }
    """
    if not citation_config:
        citation_config = {}

    has_citation = any(c.get("enabled") for c in citation_config.values())
    if not has_citation:
        return {
            "format_check": [],
            "consistency_check": {"status": "skip", "message": "未启用引用检测"},
            "source_check": [],
            "summary": "跳过（引用检测未开启）"
        }

    report = {"format_check": [], "consistency_check": {}, "source_check": []}

    # ── 收集所有格式映射 ──
    # inline_patterns: 用于扫正文引用 [x]
    # ref_patterns: 用于扫参考文献条目 x.
    inline_patterns = []
    ref_patterns = []
    format_descs = set()

    for sec_title, config in citation_config.items():
        if not config.get("enabled"):
            continue
        mapping = config.get("format", "[x]")
        inline_fmt, ref_fmt = _parse_citation_mapping(mapping)
        inline_patterns.append(_parse_citation_format(inline_fmt))
        ref_patterns.append(_parse_citation_format(ref_fmt))
        format_descs.add(f"{_parse_citation_format_plain(inline_fmt)}↔{_parse_citation_format_plain(ref_fmt)}")

    fmt_desc = "、".join(sorted(format_descs)) if format_descs else "[数字]"

    section_ranges = _extract_section_ranges(md_text)

    # ── 1. 格式检查 ──
    format_errors = []
    for sec_title, config in citation_config.items():
        if not config.get("enabled"):
            continue
        mapping = config.get("format", "[x]")
        inline_fmt, ref_fmt = _parse_citation_mapping(mapping)
        inline_pat = _parse_citation_format(inline_fmt)
        ref_pat = _parse_citation_format(ref_fmt)
        inline_plain = _parse_citation_format_plain(inline_fmt)
        ref_plain = _parse_citation_format_plain(ref_fmt)

        matched_range = False
        for title, start, end in section_ranges:
            if title == sec_title:
                matched_range = True
                content = _get_section_content(md_text, start, end)
                if not content:
                    report["format_check"].append({
                        "section": sec_title,
                        "status": "skip",
                        "message": f"节「{sec_title}」内容为空，跳过格式检查"
                    })
                    break
                # 检查正文格式或参考文献格式（任一种命中即可）
                has_inline = bool(re.search(inline_pat, content))
                has_ref = bool(re.search(ref_pat, content))
                if has_inline or has_ref:
                    found_fmt = f"{inline_plain}" if has_inline else f"{ref_plain}"
                    report["format_check"].append({
                        "section": sec_title,
                        "status": "ok",
                        "message": f"节「{sec_title}」含 {found_fmt} 格式引用"
                    })
                else:
                    msg = f"节「{sec_title}」有内容但无匹配格式（{inline_plain} 或 {ref_plain}）"
                    format_errors.append(msg)
                    report["format_check"].append({
                        "section": sec_title,
                        "status": "error",
                        "message": msg
                    })
                break
        if not matched_range:
            report["format_check"].append({
                "section": sec_title,
                "status": "skip",
                "message": f"节「{sec_title}」未在最终文章中找到，跳过检查"
            })

    # ── 2. 一致性检查 ──
    # 用 inline 格式扫描正文，ref 格式扫描条目，对比编号集
    all_inline_nums = []
    all_ref_nums = []

    for ip in inline_patterns:
        nums = _extract_all_citations(md_text, ip)
        if nums:
            all_inline_nums = nums
            break

    for rp in ref_patterns:
        # ref 格式只扫行首（条目格式），避免匹配正文中非引用的数字标点
        entries = _extract_reference_entries(md_text, rp)
        if entries:
            all_ref_nums = [e[0] for e in entries]
            break

    # 如果没有专门区分，就用同一份
    if not all_inline_nums and not all_ref_nums:
        for ip in inline_patterns:
            nums = _extract_all_citations(md_text, ip)
            if nums:
                all_inline_nums = all_ref_nums = nums
                break

    if all_inline_nums or all_ref_nums:
        # 用更大的集合做基数校验
        combined_nums = set(all_inline_nums + all_ref_nums)
        min_n, max_n = min(combined_nums), max(combined_nums)
        expected = set(range(1, max_n + 1))

        consistency_issues = []
        if combined_nums != expected:
            missing = expected - combined_nums
            extra = combined_nums - expected
            if missing:
                consistency_issues.append(f"缺少编号: {sorted(missing)}")
            if extra:
                consistency_issues.append(f"多余编号: {sorted(extra)}")

        # 交叉验证：正文编号 vs 条目编号
        inline_set = set(all_inline_nums) if all_inline_nums else set()
        ref_entry_nums = set(e[0] for e in entries) if entries else set()

        if inline_set and ref_entry_nums and inline_set != ref_entry_nums:
            consistency_issues.append(
                f"正文引用 {sorted(inline_set)} 与参考文献条目编号 {sorted(ref_entry_nums)} 不匹配"
            )

        if consistency_issues:
            report["consistency_check"] = {
                "status": "error",
                "body_refs": sorted(inline_set),
                "ref_section_refs": sorted(ref_entry_nums) if ref_entry_nums else [],
                "message": "；".join(consistency_issues)
            }
        else:
            report["consistency_check"] = {
                "status": "ok",
                "body_refs": sorted(combined_nums),
                "ref_section_refs": sorted(ref_entry_nums) if ref_entry_nums else [],
                "message": f"全文引用编号一致，共 {len(combined_nums)} 个"
            }
    else:
        report["consistency_check"] = {
            "status": "skip",
            "body_refs": [],
            "ref_section_refs": [],
            "message": "全文未发现引用编号"
        }

    # ── 3. 来源验证 ──
    if all_rag_headers and entries:
        for num, entry_text in entries:
            segments = _split_ref_entry_for_matching(entry_text)
            if not segments:
                report["source_check"].append({
                    "ref_num": num,
                    "entry": entry_text,
                    "status": "unverified",
                    "matched_source": None,
                    "message": "条目过短，无法匹配"
                })
                continue
            matched_src = _match_entry_with_headers(entry_text, segments,
                                                     all_rag_headers)
            if matched_src:
                report["source_check"].append({
                    "ref_num": num,
                    "entry": entry_text[:60] + ("..." if len(entry_text) > 60 else ""),
                    "status": "verified",
                    "matched_source": matched_src,
                    "message": f"在 {matched_src} 中找到匹配内容"
                })
            else:
                report["source_check"].append({
                    "ref_num": num,
                    "entry": entry_text[:60] + ("..." if len(entry_text) > 60 else ""),
                    "status": "unverified",
                    "matched_source": None,
                    "message": "未在 RAG 返回的文档元信息中找到匹配"
                })
    elif not all_rag_headers:
        report["source_check"] = [{
            "ref_num": 0, "entry": "",
            "status": "skip",
            "matched_source": None,
            "message": "RAG 未返回文档元信息（include_header=False 或无检索结果）"
        }]

    # ── 综合总结 ──
    f_errors = [c for c in report["format_check"] if c["status"] == "error"]
    c_error = report["consistency_check"]["status"] == "error"
    s_unverified = [c for c in report["source_check"] if c["status"] == "unverified"]

    if f_errors or c_error:
        report["summary"] = "有错误"
    elif s_unverified:
        report["summary"] = "有警告（来源未验证，建议人工复核）"
    else:
        report["summary"] = "通过"

    return report


def format_report(report: dict) -> str:
    """将验证报告格式化为追加到文末的文本"""
    lines = []

    if report.get("summary") == "跳过（引用检测未开启）":
        return ""

    lines.append("\n\n---\n\n## 引用验证报告\n")

    if report["summary"] == "通过":
        lines.append("✅ 所有引用验证通过\n")
    elif report["summary"] == "有警告（来源未验证，建议人工复核）":
        lines.append("⚠️ 引用验证通过，但部分来源未经 RAG 确认，建议人工复核\n")
    else:
        lines.append("❌ 引用验证发现问题，请修正\n")

    fc = report.get("format_check", [])
    errors = [c for c in fc if c["status"] == "error"]
    if errors:
        lines.append("\n### 格式错误\n")
        for c in errors:
            lines.append(f"- ⚠️ {c['message']}")
    ok_fc = [c for c in fc if c["status"] == "ok"]
    if ok_fc:
        lines.append(f"\n### 格式检查\n")
        for c in ok_fc:
            lines.append(f"- ✅ {c['message']}")

    cc = report.get("consistency_check", {})
    if cc.get("status") == "ok":
        lines.append(f"\n### 一致性检查 ✅\n{cc['message']}\n")
    elif cc.get("status") == "error":
        lines.append(f"\n### 一致性检查 ❌\n{cc['message']}\n")

    sc = report.get("source_check", [])
    verified = [c for c in sc if c["status"] == "verified"]
    unverified = [c for c in sc if c["status"] == "unverified"]
    skipped = [c for c in sc if c["status"] == "skip"]

    if verified:
        lines.append(f"\n### 来源验证 ✅（{len(verified)} 条已确认）\n")
        for c in verified:
            lines.append(f"- [{c['ref_num']}] {c['entry']} — ✅ {c['message']}")

    if unverified:
        lines.append(f"\n### 建议人工复核 ⚠️（{len(unverified)} 条来源无法自动确认）\n")
        for c in unverified:
            lines.append(f"- [{c['ref_num']}] {c['entry']}")
            lines.append(f"  → {c['message']}")

    if skipped:
        for c in skipped:
            lines.append(f"\n{c['message']}")

    return "\n".join(lines)
