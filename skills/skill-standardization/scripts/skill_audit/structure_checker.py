#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/structure_checker.py — 正文结构检查函数 (R-06~R-09, R-18~R-25)
v2.44.0: 新增 R-25 文档写作格式规范（9项子检查）
v2.38.6: R-18/R-19/R-20 新增渐进式文件（references/*.md）审查支持
v2.37.0: 所有 detail/location 添加绝对行号（filepath:line# 格式）
v2.5.0: R-25 C-11 章节顺位/C-12 章节格式合规
"""

import re
import os
import json
import warnings


# ── C-11/C-12 辅助函数：从 body.json 加载章节顺位/格式定义 ──────────
_BODY_SPEC_CACHE = None

def _load_body_spec():
    """加载 body.json 并缓存结果。"""
    global _BODY_SPEC_CACHE
    if _BODY_SPEC_CACHE is not None:
        return _BODY_SPEC_CACHE
    spec_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'spec', 'body.json'
    )
    if not os.path.isfile(spec_path):
        _BODY_SPEC_CACHE = {}
        return {}
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            _BODY_SPEC_CACHE = json.load(f)
        return _BODY_SPEC_CACHE
    except Exception:
        _BODY_SPEC_CACHE = {}
        return {}


def _load_section_order():
    """返回 section_order 列表。"""
    spec = _load_body_spec()
    return spec.get("section_order", [])


def _section_order_synonyms():
    """返回 section_synonyms 字典。"""
    spec = _load_body_spec()
    return spec.get("section_synonyms", {})


def _load_section_formats():
    """
    构建 章节名(小写) → content_format 的查找表。
    合并 required_sections + recommended_sections + optional_sections 的 content_format。
    """
    spec = _load_body_spec()
    fmt_map = {}
    for group_key in ("required_sections", "recommended_sections", "optional_sections"):
        for sec in spec.get(group_key, []):
            fmt = sec.get("content_format")
            if fmt:
                # 章节名取 keywords[0] 或 description
                name = (sec.get("keywords") or [""])[0]
                if name:
                    fmt_map[name.lower()] = fmt
                else:
                    # 用 description 的前 10 个字
                    desc = sec.get("description", "")
                    fmt_map[desc[:10].lower()] = fmt
    return fmt_map


def _abs_line(body, content, m_or_pos):
    """
    计算 body 中匹配位置在 content（全文）中的绝对行号（1-indexed）。
    m_or_pos: re.Match 对象（在 body 中匹配），或 int 位置（body 内字符偏移）。
    body: 正文（不含 frontmatter）
    content: 全文（含 frontmatter）
    """
    if hasattr(m_or_pos, 'start'):
        pos_in_body = m_or_pos.start()
    else:
        pos_in_body = m_or_pos
    fm_text = content[:len(content) - len(body)] if body else ""
    fm_lines = fm_text.count('\n')
    line_in_body = body[:pos_in_body].count('\n') if body else 0
    return fm_lines + line_in_body + 1


def body_has_h1(filepath, content, fm, body, **kw):
    """R-06: 正文含一级标题检查（H1 不得含版本号，版本号由 version 字段管理）"""
    # v2.44.1: 排除代码块内容，避免 bash/json 中的 # 注释被误判为 H1
    body_no_code = re.compile(r'```.*?```', re.DOTALL).sub('', body)
    m = re.search(r'^# .+', body_no_code, re.MULTILINE)
    if m is None:
        name = fm.get("name", "<技能名>") if fm else "<技能名>"
        line = _abs_line(body, content, 0)
        return {"passed": False,
                "detail": f"{filepath}:{line} - 未找到一级标题 (# )",
                "fix": {"key": "h1", "value": name,
                         "location": f"{filepath}:{line}",
                         "operation": f"添加一级标题: # {name}",
                         "verification": "重新运行 audit_skill()，确认 R-06 passed"}}
    line = _abs_line(body, content, m)
    h1_text = m.group(0).strip()
    # 检查 H1 是否含版本号（如 '# skill-name v2.38.7' 或 '# skill-name v2.6.27 — 描述'）
    ver_in_h1 = re.search(r'v?\d+\.\d+\.\d+', h1_text)
    if ver_in_h1:
        return {"passed": False,
                "detail": f"{filepath}:{line} - H1 含版本号 \"{ver_in_h1.group().strip()}\"，H1 不应含版本号（版本号由 version 字段管理）",
                "fix": {"key": "h1_version", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "移除 H1 标题中的版本号",
                         "verification": "重新运行 audit_skill()，确认 R-06 passed"}}
    # 检查 H1 是否包含技能名（v2.44.3 新增）
    name = (fm or {}).get("name", "")
    if name and name not in h1_text and name.replace('-', ' ') not in h1_text.lower():
        return {"passed": False,
                "detail": f"{filepath}:{line} - H1 \"{h1_text}\" 不含技能名 \"{name}\"，建议 H1 与技能名一致",
                "fix": {"key": "h1", "value": name,
                         "location": f"{filepath}:{line}",
                         "operation": f"添加一级标题: # {name}",
                         "verification": "重新运行 audit_skill()，确认 R-06 passed"}}
    # 检查 H1 位置——应紧跟在 frontmatter 后（v2.44.4 新增）
    h1_body_line = body[:m.start()].count('\n') + 1
    if h1_body_line > 2:
        return {"passed": False,
                "detail": f"{filepath}:{line} - H1 在第 {line} 行（距 frontmatter 闭合后有 {h1_body_line-1} 行空白），H1 应紧跟在 frontmatter 后",
                "fix": {"key": "h1_position", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "将 H1 移到 frontmatter 闭合 --- 后的下一行",
                         "verification": "重新运行 audit_skill()，确认 R-06 passed"}}
    return {"passed": True,
            "detail": f"{filepath}:{line} - 发现一级标题: {h1_text}"}


def _section_text(body, keywords):
    """
    提取 ## 章节的完整文本（到下个 ## 或文件末尾）。
    返回 (found: bool, title: str, text: str, line_no: int)。
    line_no: 章节标题在 body 中的 1-indexed 行号（用于计算绝对行号）。
    """
    lines = body.split("\n")
    in_section = False
    section_lines = []
    found_title = ""
    found_line_no = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            if any(kw.lower() in title.lower() for kw in keywords):
                in_section = True
                found_title = title
                found_line_no = i + 1
                continue
            elif in_section:
                break
        if in_section:
            section_lines.append(line)

    if not found_title:
        return False, "", "", 0
    return True, found_title, "\n".join(section_lines), found_line_no


def body_has_trigger_section(filepath, content, fm, body, **kw):
    """R-07: 触发条件章节质量检查（细化 v2.17.0）"""
    from .utils import TRIGGER_KEYWORDS

    found, title, section_text, line_no = _section_text(body, TRIGGER_KEYWORDS)
    if not found:
        line = _abs_line(body, content, 0)
        return {"passed": False,
                "detail": f"{filepath}:{line} - 未找到[{', '.join(TRIGGER_KEYWORDS)}]章节",
                "fix": {"key": "section_trigger", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "添加 ## 触发场景 章节，包含正向触发词≥3个、否定条件≥1个，无「自动执行」等危险表述",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # 章节起始绝对行号
    base_line = _abs_line(body, content, line_no - 1)  # line_no 是 1-indexed

    # ── 质量检查1：正向触发词 ≥3 个 ──────────────────
    trigger_patterns = [
        r'当用户.*时',
        r'当.*请求.*时',
        r'当.*要求.*时',
        r'[^。，\n]*触发[^。，\n]*',
        r'[-*]\s*.+[：:].+',
    ]
    positive_triggers = set()
    for pat in trigger_patterns:
        for m in re.finditer(pat, section_text):
            t = m.group(0).strip()
            if len(t) > 4:
                positive_triggers.add(t[:50])

    list_items = re.findall(r'^[-*]\s*.+', section_text, re.MULTILINE)
    for item in list_items:
        t = item.strip()[2:].strip()
        if len(t) > 2:
            positive_triggers.add(t[:50])

    if len(positive_triggers) < 3:
        return {"passed": False,
                "detail": f"{filepath}:{base_line} - 触发词数量不足（当前 {len(positive_triggers)} 个，要求 ≥3 个）",
                "fix": {"key": "trigger_quality", "value": "add_triggers",
                         "location": f"{filepath}:{base_line}",
                         "operation": "添加至少 3 个具体触发词（描述用户会说什么/做什么来触发本技能）",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查2：否定条件 ≥1 个 ──────────────────────
    negative_keywords = ["不触发", "不", "除非", "排除", "不适用", "not trigger", "won't", "don't"]
    has_negative = any(kw in section_text.lower() for kw in negative_keywords)
    if not has_negative:
        return {"passed": False,
                "detail": f"{filepath}:{base_line} - 缺少否定条件（须说明什么情况下不触发本技能）",
                "fix": {"key": "trigger_negative", "value": True,
                         "location": f"{filepath}:{base_line}",
                         "operation": "添加「不触发」或「排除」段落，说明本技能不应该被触发的情况",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查3：无危险表述 ────────────────────────────
    dangerous_phrases = ["自动执行", "auto-execute", "automatically execute", "无需询问", "直接执行", "silent execute"]
    found_dangerous = [p for p in dangerous_phrases if p in section_text]
    if found_dangerous:
        return {"passed": False,
                "detail": f"{filepath}:{base_line} - 包含危险表述：{', '.join(found_dangerous)}",
                "fix": {"key": "trigger_danger", "value": "remove_dangerous",
                         "location": f"{filepath}:{base_line}",
                         "operation": f"移除或改写危险表述：{', '.join(found_dangerous)}",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查4：frontmatter trigger/trigger_negative 一致性 ──
    fm_trigger = str(fm.get('trigger', '')).strip() if fm else ''
    fm_trigger_neg = str(fm.get('trigger_negative', '')).strip() if fm else ''
    consistency_warnings = []

    # 正文有正向触发词但 frontmatter 没有 trigger 字段
    if len(positive_triggers) >= 3 and not fm_trigger:
        consistency_warnings.append("正文有 ⩾3 个触发词但 frontmatter 缺 trigger 字段")
    # 正文有否定条件但 frontmatter 没有 trigger_negative 字段
    if has_negative and not fm_trigger_neg:
        consistency_warnings.append("正文有否定条件但 frontmatter 缺 trigger_negative 字段")

    detail = f"{filepath}:{base_line} - 触发条件章节质量合格（{len(positive_triggers)} 个触发词，含否定条件）"
    if consistency_warnings:
        detail += ' ⚠️ ' + '；'.join(consistency_warnings)

    return {"passed": len(consistency_warnings) == 0,
            "detail": detail}


def body_has_core_section(filepath, content, fm, body, **kw):
    """R-08: 核心能力章节检查"""
    from .utils import CORE_KEYWORDS
    found, title, _, line_no = _section_text(body, CORE_KEYWORDS)
    if not found:
        line = _abs_line(body, content, 0)
        return {"passed": False,
                "detail": f"{filepath}:{line} - 未找到[{', '.join(CORE_KEYWORDS)}]章节",
                "fix": {"key": "section_core", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "添加 ## 核心能力 章节，列出 3-5 条核心功能",
                         "verification": "重新运行 audit_skill()，确认 R-08 passed"}}
    abs_line = _abs_line(body, content, line_no - 1)
    return {"passed": True, "detail": f"{filepath}:{abs_line} - 发现章节: {title}"}


def body_has_workflow_section(filepath, content, fm, body, **kw):
    """R-09: 工作流程/使用方式章节检查"""
    from .utils import WORKFLOW_KEYWORDS
    found, title, _, line_no = _section_text(body, WORKFLOW_KEYWORDS)
    if not found:
        line = _abs_line(body, content, 0)
        return {"passed": False,
                "detail": f"{filepath}:{line} - 未找到[{', '.join(WORKFLOW_KEYWORDS)}]章节",
                "fix": {"key": "section_workflow", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "添加 ## 工作流程 章节，用步骤列表描述执行流程",
                         "verification": "重新运行 audit_skill()，确认 R-09 passed"}}
    abs_line = _abs_line(body, content, line_no - 1)
    return {"passed": True, "detail": f"{filepath}:{abs_line} - 发现章节: {title}"}


# ────────────────────────────────────────────────────────
# R-18: 反模式具体性检查
# ────────────────────────────────────────────────────────

def body_has_antipattern_section(filepath, content, fm, body, **kw):
    """R-18: 反模式/常见错误章节具体性检查（必须渐进式，v2.24.7 重构）"""
    antipattern_keywords = ["反模式", "常见错误", "注意事项", "坑", "anti-pattern", "common mistake"]

    # 1. 检查 SKILL.md 是否直接包含反模式章节（这是错的，必须用渐进式）
    found, title, section_text, line_no = _section_text(body, antipattern_keywords)

    if found:
        abs_line = _abs_line(body, content, line_no - 1)
        return {"passed": False,
                "detail": f"{filepath}:{abs_line} - 反模式不应直接写在 SKILL.md 的 ## {title} 章节里，须改用渐进式（移到 references/antipatterns.md）",
                "fix": {"key": "antipattern_progressive", "value": True,
                         "location": f"{filepath}:{abs_line}",
                         "operation": "将反模式内容移到 references/antipatterns.md，在 SKILL.md 中添加引用 `→ 详见 references/antipatterns.md`",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}

    # 2. 检查 SKILL.md 是否有引用 references/antipatterns.md
    has_ref = bool(re.search(r'references/antipatterns\.md', body))
    if not has_ref:
        line = _abs_line(body, content, 0)
        return {"passed": False,
                "detail": f"{filepath}:{line} - 未找到对 references/antipatterns.md 的引用（反模式须用渐进式）",
                "fix": {"key": "antipattern_reference", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "创建 references/antipatterns.md，并在 SKILL.md 中添加引用 `→ 详见 references/antipatterns.md`",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}

    # 3. 检查 references/antipatterns.md 是否存在
    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    antipattern_file = os.path.join(skill_dir, 'references', 'antipatterns.md')

    if not os.path.isfile(antipattern_file):
        return {"passed": False,
                "detail": f"{antipattern_file}:1 - SKILL.md 引用了 references/antipatterns.md 但该文件不存在",
                "fix": {"key": "antipattern_file_missing", "value": True,
                         "location": f"{antipattern_file}:1",
                         "operation": "创建 references/antipatterns.md，包含至少 2 条具体反模式示例（含 **错误做法：**、**正确做法：** 标记）",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}

    # 4. 检查 references/antipatterns.md 内容质量
    with open(antipattern_file, 'r', encoding='utf-8') as f:
        ap_content = f.read()

    # 匹配反模式条目（支持 ### AP-01 格式、列表项、表格）
    ap_items = re.findall(r'^###\s*AP-\d+[:\uff1a]', ap_content, re.MULTILINE)
    if not ap_items:
        ap_items = re.findall(r'^[-*]\s*.+', ap_content, re.MULTILINE)
    if not ap_items:
        ap_items = re.findall(r'^\d+\.\s*.+', ap_content, re.MULTILINE)
    # 表格格式支持
    if not ap_items:
        table_rows = re.findall(r'^\|.*\|$', ap_content, re.MULTILINE)
        data_rows = [r for r in table_rows if not re.match(r'^\|[\s\-:|]+\|$', r)]
        if len(data_rows) >= 2:
            ap_items = data_rows[1:]

    if len(ap_items) < 2:
        return {"passed": False,
                "detail": f"{antipattern_file}:1 - references/antipatterns.md 反模式条目不足（当前 {len(ap_items)} 条，要求 ≥2 条）",
                "fix": {"key": "antipattern_count", "value": "add_examples",
                         "location": f"{antipattern_file}:1",
                         "operation": "添加至少 2 条具体反模式示例（须含 **错误做法：**、**正确做法：** 标记），支持列表/表格/### 标题格式",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}

    # 检查是否有具体描述（错误做法/正确做法标记）
    # 修复 v2.38.1：放宽匹配，允许冒号在加粗符内或外，允许后面有空格/文本
    has_detail = bool(re.search(r'\*\*错误做法\s*[:：\uff1a]?\s*\*\*?', ap_content) or
                      re.search(r'\*\*正确做法\s*[:：\uff1a]?\s*\*\*?', ap_content) or
                      re.search(r'\*\*深层原因\s*[:：\uff1a]?\s*\*\*?', ap_content))

    if not has_detail:
        return {"passed": False,
                "detail": f"{antipattern_file}:1 - references/antipatterns.md 缺少具体描述（须含 **错误做法：**、**正确做法：** 标记）",
                "fix": {"key": "antipattern_detail", "value": "add_detail",
                         "location": f"{antipattern_file}:1",
                         "operation": "为每个反模式添加 **错误做法：**、**正确做法：** 和 **深层原因：** 标记",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}

    return {"passed": True,
            "detail": f"{antipattern_file}:1 - 反模式在 references/antipatterns.md 中（{len(ap_items)} 条具体示例，含错误做法/正确做法标记）"}


def body_has_faq_section(filepath, content, fm, body, **kw):
    """R-19: FAQ/常见问题章节有意义性检查（必须渐进式，v2.24.7 重构）"""
    faq_keywords = ["FAQ", "常见问题", "Q&A", "Questions", "问答"]

    # 1. 检查 SKILL.md 是否直接包含 FAQ 章节（这是错的，必须用渐进式）
    found, title, section_text, line_no = _section_text(body, faq_keywords)

    if found:
        abs_line = _abs_line(body, content, line_no - 1)
        return {"passed": False,
                "detail": f"{filepath}:{abs_line} - FAQ 不应直接写在 SKILL.md 的 ## {title} 章节里，须改用渐进式（移到 references/faq.md）",
                "fix": {"key": "faq_progressive", "value": True,
                         "location": f"{filepath}:{abs_line}",
                         "operation": "将 FAQ 内容移到 references/faq.md，在 SKILL.md 中添加引用 `→ 详见 references/faq.md`",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    # 2. 检查 SKILL.md 是否有引用 references/faq.md
    has_ref = bool(re.search(r'references/faq\.md', body))
    if not has_ref:
        line = _abs_line(body, content, 0)
        return {"passed": False,
                "detail": f"{filepath}:{line} - 未找到对 references/faq.md 的引用（FAQ 须用渐进式）",
                "fix": {"key": "faq_reference", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "创建 references/faq.md，并在 SKILL.md 中添加引用 `→ 详见 references/faq.md`",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    # 3. 检查 references/faq.md 是否存在
    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    faq_file = os.path.join(skill_dir, 'references', 'faq.md')

    if not os.path.isfile(faq_file):
        return {"passed": False,
                "detail": f"{faq_file}:1 - SKILL.md 引用了 references/faq.md 但该文件不存在",
                "fix": {"key": "faq_file_missing", "value": True,
                         "location": f"{faq_file}:1",
                         "operation": "创建 references/faq.md，包含至少 3 对 Q&A（问题 ≥10 字，答案 ≥15 字）",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    # 4. 检查 references/faq.md 内容质量
    with open(faq_file, 'r', encoding='utf-8') as f:
        faq_content = f.read()

    # 提取 Q&A 对
    faq_qa = _extract_qa_pairs(faq_content)

    if not faq_qa:
        return {"passed": False,
                "detail": f"{faq_file}:1 - references/faq.md 无法解析 Q&A 内容（请确保使用 Q:/A: 或 ### 子标题格式）",
                "fix": {"key": "faq_unparsable", "value": "reformat",
                         "location": f"{faq_file}:1",
                         "operation": "用 Q: 问题\n\nA: 答案\n\n 格式重写 FAQ",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    # 检查 Q&A 质量
    trivial_questions = ["如何工作", "怎么用", "what is", "how to", "帮助"]
    bad_pairs = []
    for q, a in faq_qa:
        q_trim = q.strip()
        a_trim = a.strip()
        if len(q_trim) < 10 or any(t in q_trim.lower() for t in trivial_questions):
            bad_pairs.append(f"Q: {q_trim[:30]}")
        if len(a_trim) < 15 or a_trim in ("请参考文档", "见上文", "see above"):
            bad_pairs.append(f"A: {a_trim[:30]}")
        if bad_pairs:
            return {"passed": False,
                    "detail": f"{faq_file}:1 - FAQ 包含低质量条目（{len(bad_pairs)} 条）：{', '.join(bad_pairs[:3])}",
                    "fix": {"key": "faq_quality", "value": "improve_qa",
                             "location": f"{faq_file}:1",
                             "operation": "改进 FAQ 质量：问题须具体（≥10字），答案须有实质内容（≥15字），避免万能回答",
                             "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    return {"passed": True,
            "detail": f"{faq_file}:1 - FAQ 在 references/faq.md 中（{len(faq_qa)} 对 Q&A）"}


def _extract_qa_pairs(section_text):
    """
    从 FAQ 章节提取 Q/A 对。
    支持格式：
      Q: 问题\n\nA: 答案
      ### 问题标题\n答案...
      **Q:** 问题\n**A:** 答案
    返回 [(q_text, a_text), ...]
    """
    pairs = []

    # 方法1：Q:/A: 格式
    qa_blocks = re.split(r'\n\s*(?:Q\s*[:：]|\*\*Q\b)', section_text)
    for block in qa_blocks[1:]:
        q_end = block.find("\nA") if "\nA" in block else block.find("\nA:")
        if q_end == -1:
            q_end = len(block)
        q = block[:q_end].strip()
        a_start = block.find("A:")
        if a_start == -1:
            a_start = block.find("A：")
        a = block[a_start+2:].strip() if a_start != -1 else ""
        if q and a:
            pairs.append((q, a))

    if pairs:
        return pairs

    # 方法2：### 子标题格式
    subheads = list(re.finditer(r'^### (.+)$', section_text, re.MULTILINE))
    for i, m in enumerate(subheads):
        q = m.group(1).strip()
        start = m.end()
        end = subheads[i+1].start() if i+1 < len(subheads) else len(section_text)
        a = section_text[start:end].strip()
        if q and a:
            pairs.append((q, a))

    return pairs


# ────────────────────────────────────────────────────────
# R-20: 写作规范检查
# ────────────────────────────────────────────────────────

def _check_writing_standards_text(text, filename="", self_audit=False):
    """
    检查文本的写作规范，返回分级 issues 字典。
    供 body_check_writing_standards() 和渐进式文件检查复用。

    self_audit=True 时跳过术语一致性检查（尺子不能量自己）。
    注意：self_audit 只在直接检查审计代码文件自身（如 structure_checker.py）
    时启用。body_check_writing_standards 检查的是文档文件（SKILL.md/references/*.md），
    不检查审计代码，所以不应传 self_audit=True。

    返回格式：
    {
        "must": [],    # 🔴 必须修：术语不一致、事实错误
        "suggest": [], # 🟡 建议修：模糊表述、缺少空格
        "optional": []  # ⚪ 可选择修：风格偏好
    }
    """
    issues = {"must": [], "suggest": [], "optional": []}

    # ── 预清理：剔除代码块、行内代码、文件名、目录路径（供所有检查复用）──
    cleaned = re.sub(r"```.*?```", '', text, flags=re.DOTALL)
    # v2.29.0 修复：用 Unicode 转义代替反引号，避免正则失效
    tick = '\u0060'
    cleaned = re.sub(f'{tick}[^{tick}]+?{tick}', '', cleaned)
    # v2.29.1 修复：剔除文件名（如 SKILL.md、reference.md），避免中英文混排误报
    cleaned = re.sub(r'[A-Za-z]+\.[a-zA-Z]+', ' ', cleaned)
    # v2.29.1 新增：剔除目录路径（如 scripts/、references/），避免中英文混排误报
    cleaned = re.sub(r'[A-Za-z]+/', ' ', cleaned)
    # v2.38.1 新增：剔除大写变量名（如 CANVAS_W、MARGIN_X），避免中英文混排误报
    cleaned = re.sub(r'[A-Z_]{2,}\s*=', ' ', cleaned)
    cleaned = re.sub(r'[A-Z][A-Z_0-9]*', ' ', cleaned)
    # v2.38.1 新增：剔除 camelCase/PascalCase 标识符（如 exitX、entryY、Header），避免误报
    cleaned = re.sub(r'[a-z]+[A-Z][a-zA-Z0-9]*', ' ', cleaned)
    # v2.38.1 新增：剔除英文代码术语紧跟中文的情况（如 id指、XML输、容器header），白名单常见术语
    # 不用 \b 单词边界（中文+英文之间没有 \b），用 ASCII 边界
    code_terms_pattern = r'(?<![a-zA-Z0-9_])(id|header|exit|entry|xml|json|url|http|https|api|ui|ux|db|io)(?![a-zA-Z0-9_])'
    cleaned = re.sub(code_terms_pattern + r'[一-鿿]', ' ', cleaned, flags=re.IGNORECASE)
    # v2.38.2 新增：剔除 snake_case 标识符（如 parent_id、my_variable），避免中英文混排误报
    cleaned = re.sub(r"[a-zA-Z][a-zA-Z0-9]*_[a-zA-Z0-9_]+", " ", cleaned)
    cleaned = re.sub(r'[一-鿿]' + code_terms_pattern, ' ', cleaned, flags=re.IGNORECASE)

    # ── 检查1：术语一致性（🔴 必须修）───────────────────
    # self_audit=True 时跳过（审计标准不审计自身，尺子不能量自己）
    if not self_audit:
        term_groups = [
            (["创建", "建立", "新建"], "创建"),
            (["更新", "修改", "变更"], "更新"),
            (["删除", "移除", "去掉"], "删除"),
            (["配置", "设置", "设定"], "配置"),
        ]
        lines = cleaned.split("\n")
        for group, preferred in term_groups:
            found_terms = {}
            for line in lines:
                for term in group:
                    if term in line:
                        found_terms.setdefault(term, []).append(line[:50])
            if len(found_terms) > 1:
                terms_str = ", ".join(found_terms.keys())
                prefix = f"{filename}：" if filename else ""
                issues["must"].append(f"{prefix}术语不一致：混用 {terms_str}，建议统一为「{preferred}」")

    # ── 检查2：禁止表述（🟡 建议修）────────────────────
    forbidden = [
        ("可能", "避免模糊表述，改用确定性描述"),
        ("应该", "避免建议性表述，改用确定性描述或明确标注「建议」"),
        ("大概", "避免模糊表述"),
        ("差不多", "避免模糊表述"),
    ]
    for word, suggestion in forbidden:
        if word in cleaned:
            # v2.24.2 误判排除：如果模糊词出现在"修复"、"删除"等动词后面，说明是在描述修复动作，不是实际模糊表述
            # v2.24.5 新增：被动语态排除（"可能被"、"应该被" 等），描述可能性而非模糊表述
            lines = cleaned.splitlines()
            is_false_positive = False
            for line in lines:
                if word in line:
                    # 排除1：修复动作（修复、删除、统一、修改、更新、移除、去掉）
                    if any(verb in line for verb in ["修复", "删除", "统一", "修改", "更新", "移除", "去掉"]):
                        is_false_positive = True
                        break
                    # 排除2：被动语态（可能被、应该被、可以被 等）
                    if re.search(r'(可能|应该|可以)被', line):
                        is_false_positive = True
                        break
                    # 排除3：条件句式（如果可能、若可能 等）
                    if re.search(r'(如果|若|假如|假设).*?(可能|应该)', line):
                        is_false_positive = True
                        break
                    # v2.24.6 新增：疑问句排除（"应该" 在疑问句里是询问建议，不是模糊表述）
                    if word == "应该" and ('？' in line or '？' in line):
                        is_false_positive = True
                        break
            if not is_false_positive:
                prefix = f"{filename}：" if filename else ""
                issues["suggest"].append(f"{prefix}含模糊表述「{word}」：{suggestion}")

    # ── 检查3：中英文混排空格（🟡 建议修）───────────────────
    mingled = re.findall(r'[一-鿿][A-Za-z]{2,}|[A-Za-z]{2,}[一-鿿]', cleaned)
    mingled = [m for m in mingled if not re.match(r'v\d|SKILL|MD|JSON|YAML', m)]
    if mingled:
        prefix = f"{filename}：" if filename else ""
        issues["suggest"].append(f"{prefix}中英文混排缺少空格：{', '.join(mingled[:5])}")

    return issues


def body_check_writing_standards(filepath, content, fm, body, **kw):
    """R-20: 写作规范检查（术语一致性、禁止表述、中英文混排）
    ✅ v2.22.0：同时检查 references/*.md 渐进式文件
    ✅ v2.23.0：分级输出（必须修/建议修/可选择修）
    """
    all_issues = {"must": [], "suggest": [], "optional": []}

    # ── R-23: 文档-代码一致性检查 (v2.34.8) ──────────────────────
    r23_result = check_doc_code_consistency(filepath, content, fm, body, **kw)
    if not r23_result.get("passed", True):
        for k in ["must", "suggest", "optional"]:
            if f"R-23" in r23_result.get("detail", ""):
                all_issues["suggest"].append(r23_result["detail"])
    elif "ⓘ" in r23_result.get("detail", ""):
        # R-23 通过但有 optional 提示，放在 optional 供参考
        all_issues["optional"].append(r23_result["detail"])

    # ── 检查 SKILL.md 正文 ────────────────────────
    # 注意：body_check_writing_standards 检查的是 SKILL.md 和 references/*.md，
    # 不是审计代码文件（structure_checker.py）自身，所以 self_audit=False。
    # 尺子不能量自己，但这里量的不是尺子本身，而是被审计技能的文档文件。
    issues = _check_writing_standards_text(body, "SKILL.md")
    for k in all_issues:
        all_issues[k] += issues[k]

    # ── 新增：脚本调用验证检查（v2.24.4）─────────────────────
    # 检查 SKILL.md 里提到的脚本是否真实存在、能否正常运行（--help 验证）
    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    if skill_dir and os.path.isdir(skill_dir):
        import re, py_compile, sys

        # 1. 解析 SKILL.md 里的代码块（```bash ... ```）和行内代码（`...`）
        code_blocks = re.findall(r'```(?:bash|sh|python)?\s*\n(.*?)```', body, re.DOTALL)
        inline_codes = re.findall(r'`([^`]+?)`', body)

        all_commands = []
        for block in code_blocks:
            for line in block.splitlines():
                line = line.strip()
                if line.startswith('#'):
                    continue
                all_commands.append(line)
        all_commands.extend(inline_codes)

        # 2. 提取脚本路径（如 python scripts/xxx.py --list）
        script_paths = set()
        for cmd in all_commands:
            match = re.search(r'(?:python3?)\s+([^\s]+\.py)', cmd)
            if match:
                script_path = match.group(1)
                # v2.29.0 修复：脚本路径不应包含中文/全角字符（排除误报）
                if re.search(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', script_path):
                    continue
                # v2.24.4 修复：跳过包含变量的路径（如 {SKILL_DIR}/scripts/...）
                if '{' in script_path or '}' in script_path:
                    continue
                script_paths.add(script_path)

        # 3. 检查脚本文件是否存在、能否运行 --help
        for script_path in script_paths:
            full_path = os.path.join(skill_dir, script_path)
            if not os.path.isfile(full_path):
                all_issues["suggest"].append(f"SKILL.md 提到脚本 `{script_path}` 但文件不存在（应使用相对路径如 `scripts/foo.py`）")
            else:
                # 静态分析：检查 Python 语法（不执行脚本，避免间接执行风险）
                try:
                    with open(full_path, 'r', encoding='utf-8') as _f:
                        import ast
                        ast.parse(_f.read())
                except SyntaxError as _e:
                    all_issues["suggest"].append(f"脚本 `{script_path}` 语法错误（第 {_e.lineno} 行）：{_e.msg}")
                except Exception as _e:
                    all_issues["suggest"].append(f"脚本 `{script_path}` 读取/编译失败：{str(_e)[:100]}")

    # ── 检查渐进式文件 references/*.md ────────────────
    # skill_dir 已在上面定义
    refs_dir = os.path.join(skill_dir, 'references')
    if os.path.isdir(refs_dir):
        for fname in sorted(os.listdir(refs_dir)):
            if not fname.endswith('.md'):
                continue
            # changelog.md 也检查写作规范（审计标准不可绕过，问题应改文件而非改审计）
            fpath = os.path.join(refs_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    ref_content = f.read()
            except Exception:
                continue
            # 渐进式文件也是文档文件，不是审计代码自身，不传 self_audit（保持默认 False）
            issues = _check_writing_standards_text(ref_content, fname)
            for k in all_issues:
                all_issues[k] += issues[k]

    # ── 分级格式化输出 ──────────────────────────────
    must_count = len(all_issues["must"])
    suggest_count = len(all_issues["suggest"])
    optional_count = len(all_issues["optional"])

    if must_count == 0 and suggest_count == 0 and optional_count == 0:
        return {"passed": True,
                "detail": "写作规范检查通过（SKILL.md + references/*.md 术语一致、无禁止表述、中英文混排规范）"}

    # 仅 optional（如两阶段粗筛产物）→ 通过，detail 带 NOTE
    if must_count == 0 and suggest_count == 0 and optional_count > 0:
        return {"passed": True,
                "detail": f"写作规范检查通过 ⓘ 仅可选问题（{optional_count} 条，不阻断通过）：{all_issues['optional'][0]}" +
                          (f" 等（共 {optional_count} 条）" if optional_count > 1 else "")}

    # 格式化输出
    parts = []
    parts = []
    if must_count > 0:
        parts.append(f"🔴 必须修（{must_count} 条）：{all_issues['must'][0]}")
        if must_count > 1:
            parts[0] += f" 等（共 {must_count} 条）"
    if suggest_count > 0:
        parts.append(f"🟡 建议修（{suggest_count} 条）：{all_issues['suggest'][0]}")
        if suggest_count > 1:
            parts[-1] += f" 等（共 {suggest_count} 条）"
    if optional_count > 0:
        parts.append(f"⚪ 可选择修（{optional_count} 条）：{all_issues['optional'][0]}")
        if optional_count > 1:
            parts[-1] += f" 等（共 {optional_count} 条）"

    detail = "；".join(parts)
    return {"passed": False,
            "detail": f"写作规范问题：{detail}",
            "fix": {"key": "writing_standards", "value": "fix_terms",
                     "location": f"{filepath} 正文 + references/*.md",
                     "operation": "优先修复🔴必须修问题，建议修复🟡建议修问题（含渐进式文件）",
                     "verification": "重新运行 audit_skill()，确认 R-20 passed"}}


def body_has_progressive_loading_explicit(filepath, content, fm, body, **kw):
    """
    R-21: 渐进式加载显式说明检查 (v2.24.2 固定模板)
    检查 SKILL.md 是否在显眼位置（核心能力/工作流程章节）包含固定模板句。
    ✅ v2.24.2：固定模板句必须原封不动包含，可后面接其他说明。
    """
    from .utils import CORE_KEYWORDS, WORKFLOW_KEYWORDS

    # v2.24.2 固定模板句子（所有技能必须原封不动包含此句，可在后面接其他说明）
    FIXED_TEMPLATE = "> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。"

    # v2.24.2 硬编码章节名：只检查 ## 核心能力 和 ## 工作流程（不用 CORE_KEYWORDS，避免匹配到 ## 核心概念）
    prominent_texts = []
    # 硬编码检查 ## 核心能力
    found, title, section_text, line_no = _section_text(body, ["核心能力", "核心功能", "概述", "Overview", "技能概述"])
    if found:
        prominent_texts.append(("核心能力", title, section_text, line_no))
    # 硬编码检查 ## 工作流程
    found, title, section_text, line_no = _section_text(body, ["工作流程", "使用方式", "Workflow", "完整执行流程", "核心指令", "完整工作流"])
    if found:
        prominent_texts.append(("工作流程", title, section_text, line_no))

    if not prominent_texts:
        line = _abs_line(body, content, 0)
        return {"passed": False,
                "detail": f"{filepath}:{line} - 未找到核心能力/工作流程章节，无法检查渐进式加载显式说明",
                "fix": {"key": "progressive_loading_explicit", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": f"在 ## 核心能力 章节添加固定模板句：{FIXED_TEMPLATE}",
                         "verification": "重新运行 audit_skill()，确认 R-21 passed"}}

    # v2.24.2：直接搜固定模板句子（原封不动，可后面接其他内容）
    for section_name, title, section_text, line_no in prominent_texts:
        abs_line = _abs_line(body, content, line_no - 1)
        for line in section_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(FIXED_TEMPLATE) or stripped == FIXED_TEMPLATE:
                return {"passed": True,
                        "detail": f"{filepath}:{abs_line} - 在 ## {title} 章节发现渐进式加载固定模板句"}

    # 未找到固定模板句
    first_section, first_title, _, first_line_no = prominent_texts[0]
    first_abs_line = _abs_line(body, content, first_line_no - 1)
    return {"passed": False,
            "detail": f"{filepath}:{first_abs_line} - 在 ## {first_title} 等显眼章节未找到渐进式加载固定模板句",
            "fix": {"key": "progressive_loading_explicit", "value": True,
                     "location": f"{filepath}:{first_abs_line}",
                     "operation": f"在 ## {first_section} 章节添加固定模板句：{FIXED_TEMPLATE}（必须原封不动，可在后面接其他说明）",
                     "verification": "重新运行 audit_skill()，确认 R-21 passed"}}


def check_doc_code_consistency(
    filepath, content, fm, body, **kw):
    """
    # R-23: filter Python builtins falsely matched as skill-defined names
    _BUILTINS = {
        "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",
        "ImportError", "FileNotFoundError", "KeyError", "IndexError",
        "RuntimeError", "AttributeError", "NameError",
    }

    # R-23: filter Python builtins falsely matched as skill-defined names
    _BUILTINS = {
        "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",
        "ImportError", "FileNotFoundError", "KeyError", "IndexError",
        "RuntimeError", "AttributeError", "NameError",
    }

    # R-23: filter Python builtins falsely matched as skill-defined names
    _BUILTINS = {
        "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",
        "ImportError", "FileNotFoundError", "KeyError", "IndexError",
        "RuntimeError", "AttributeError", "NameError",
    }
    R-23: 文档-代码一致性检查 (v2.34.8)
    验证 SKILL.md 中引用的脚本/文件/函数名真实存在。
    """
    # R-23: filter out Python builtins falsely matched as "functions/classes defined in skill"
    _BUILTINS = {
        "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",
        "ImportError", "FileNotFoundError", "KeyError", "IndexError",
        "RuntimeError", "AttributeError", "NameError",
    }

    import re, ast, os
    from pathlib import Path

    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    issues = {"must": [], "suggest": [], "optional": []}

    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "R-23: 无法访问技能目录，跳过检查"}

    # 1. 解析 SKILL.md 里的代码块和行内代码
    code_blocks = re.findall(r'```(?:bash|sh|python)?\s*\n(.*?)```', body, re.DOTALL)
    inline_codes = re.findall(r'`([^`]+?)`', body)

    all_commands = []
    for block in code_blocks:
        for line in block.splitlines():
            line = line.strip()
            if line.startswith('#'):
                continue
            all_commands.append(line)
    all_commands.extend(inline_codes)

    # 2. 提取脚本路径（如 python scripts/xxx.py --list）
    script_paths = set()
    py_file_refs = set()  # 所有 .py 文件引用

    for cmd in all_commands:
        # 匹配 python scripts/xxx.py 或 `scripts/xxx.py`
        match = re.search(r'(?:python3?\s+)?([^\s`]+\.py)', cmd)
        if match:
            script_path = match.group(1).strip()
            # 排除含变量/中文的路径
            if re.search(r'[{\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', script_path):
                continue
            if '{' in script_path or '}' in script_path:
                continue
            script_paths.add(script_path)
        # 也匹配行内代码中的 .py 引用
        for m2 in re.finditer(r'([^\s`]*\.py)', cmd):
            py_file_refs.add(m2.group(1))

    script_paths.update(py_file_refs)

    # 3. 检查脚本文件是否存在
    for script_path in script_paths:
        full_path = os.path.join(skill_dir, script_path)
        if not os.path.isfile(full_path):
            # 尝试在 scripts/ 子目录找
            alt_path = os.path.join(skill_dir, 'scripts', os.path.basename(script_path))
            if os.path.isfile(alt_path):
                continue
            issues["suggest"].append(
                f"R-23: {filepath}:1 - SKILL.md 提到脚本 `{script_path}` 但文件不存在（期望相对路径如 `scripts/foo.py`）"
            )
        else:
            # 静态语法检查
            try:
                with open(full_path, 'r', encoding='utf-8') as _f:
                    ast.parse(_f.read())
            except SyntaxError as _e:
                issues["suggest"].append(
                    f"R-23: {script_path}:{_e.lineno} - 脚本 `{script_path}` 语法错误（第 {_e.lineno} 行）：{_e.msg}"
                )
            except Exception as _e:
                issues["suggest"].append(
                    f"R-23: {script_path}:1 - 脚本 `{script_path}` 读取失败：{str(_e)[:80]}"
                )

            # 4. 检查 SKILL.md 中【调用此脚本的命令】的参数是否与实际代码一致
            # 只检查调用了当前 script_path 的命令，不检查全部 all_commands
            script_basename = os.path.basename(script_path)  # e.g. "template_generator.py"
            relevant_cmds = []
            for cmd in all_commands:
                # 命令中提及此脚本名（含路径）才检查
                if script_basename in cmd or script_path.replace('\\', '/') in cmd or script_path.replace('/', '\\') in cmd:
                    # 按行拆分，只保留真正调用此脚本的命令行（避免整个代码块被当作一条命令）
                    for _line in cmd.splitlines():
                        _line = _line.strip()
                        if _line.startswith('#'): continue
                        if script_basename in _line or script_path.replace('\\', '/') in _line or script_path.replace('/', '\\') in _line:
                            relevant_cmds.append(_line)
                        if _line.startswith('#'):
                            continue
                        if script_basename in _line or script_path.replace('\\', '/') in _line or script_path.replace('/', '\\') in _line:
                            relevant_cmds.append(_line)
            if relevant_cmds and '--' in ' '.join(relevant_cmds):
                # 提取这些相关命令中提到的 --flags
                doc_flags = set(re.findall(r'--([a-z][-a-z]*)', ' '.join(relevant_cmds)))
                if doc_flags and script_path.endswith('.py'):
                    # 尝试从脚本源码中提取实际的 argparse flags
                    try:
                        with open(full_path, 'r', encoding='utf-8') as _f:
                            src = _f.read()
                        # 简单匹配 add_argument('--xxx') 模式
                        actual_flags = set(re.findall(r"add_argument\(\s*['\"]--([a-z][-a-z]*)['\"]", src))
                        for flag in doc_flags:
                            if flag not in actual_flags and flag not in ('help', 'version'):
                                issues["optional"].append(
                                    f"R-23: {filepath}:1 - SKILL.md 示例中含 `--{flag}` 但 `{script_path}` 未定义此参数（实际定义：{', '.join(sorted(actual_flags)[:5])}）"
                                )
                    except Exception:
                        pass

    # 5. 检查 SKILL.md 正文提到的函数/类名是否在实际代码中存
    # 匹配中文描述后的代码引用，如 "调用 XXXFunction" 或 "`XXXClass`"
    func_refs = re.findall(r'`([A-Z][a-zA-Z0-9_]*)`', body)
    func_refs += re.findall(r'调用\s+([a-zA-Z_][a-zA-Z0-9_]*)', body)
    func_refs += re.findall(r'函数\s+([a-zA-Z_][a-zA-Z0-9_]*)', body)

    if func_refs and skill_dir:
        # 收集技能目录中所有 .py 文件定义的函数/类名
        all_defs = set()
        for py_file in Path(skill_dir).rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as _f:
                    src = _f.read()
                for m in re.finditer(r'^(?:def |class )([a-zA-Z_][a-zA-Z0-9_]*)', src, re.MULTILINE):
                    all_defs.add(m.group(1))
            except Exception:
                continue

        for ref in set(func_refs):
            if ref in _BUILTINS:  # R-23: skip Python builtins
                continue
            if ref not in all_defs:
                # 模糊匹配（前缀匹配）
                matched = [d for d in all_defs if d.startswith(ref) or ref.startswith(d)]
                if not matched:
                    issues["suggest"].append(
                        f"R-23: {filepath}:1 - SKILL.md 提到函数/类名 `{ref}` 但在技能代码中未找到（已有定义：{', '.join(sorted(all_defs)[:5])}）"
                    )

    # 6. (新增 v2.38.8) 检查 SKILL.md 正文中的路径描述是否与 frontmatter data_dir 一致
    if fm and fm.get('data_dir'):
        data_dir_val = str(fm['data_dir']).replace('\\', '/')
        if '.standardization' in data_dir_val:
            # 从 data_dir 提取技能目录名（最后一级目录）
            _dd_parts = data_dir_val.rstrip('/').split('/')
            skill_name_in_dir = _dd_parts[-2] if len(_dd_parts) >= 2 else ''
            if skill_name_in_dir:
                # 在正文中搜索 skills/<skill>/data/ 模式（缺少 .standardization 前缀）
                # 使用负向先行断言 (?:(?!\.standardization/)[^/]+)* 确保路径中不含 .standardization/
                _old_path_re = re.compile(
                    r'skills/(?:(?!\.standardization/)[^/]+/)*' + re.escape(skill_name_in_dir) + r'/data/'
                )
                for _m in _old_path_re.finditer(body):
                    _line = body[:_m.start()].count('\n') + 1
                    issues["must"].append(
                        f"R-23: {filepath}:{_line} - SKILL.md 正文路径 `{_m.group()}` 缺少 `.standardization/` 层级"
                        f"（frontmatter data_dir 为 `{data_dir_val}`，路径应包含 `.standardization/` 前缀）"
                    )

    # 7. (v2.39.0) 两阶段：R-23 第 7 项 — MD 引用的外部技能是否存在
    # 第一阶段（正则粗筛）：收集所有 skills/<name>/ 候选，不设白名单，不阻断 PASS
    # 第二阶段（LLM 精筛）：AI 对粗筛结果逐条判断语境，过滤误报后才是最终结果
    if skill_dir and os.path.isdir(skill_dir):
        _skills_root = os.path.normpath(os.path.join(skill_dir, '..'))
        _current_skill = os.path.basename(os.path.normpath(skill_dir))
        _all_md = [('SKILL.md', body)]
        _refs_dir = os.path.join(skill_dir, 'references')
        if os.path.isdir(_refs_dir):
            for _rf in sorted(os.listdir(_refs_dir)):
                if _rf.endswith('.md') and _rf != 'changelog.md':
                    _rp = os.path.join(_refs_dir, _rf)
                    try:
                        with open(_rp, 'r', encoding='utf-8') as _f:
                            _all_md.append((f'references/{_rf}', _f.read()))
                    except Exception:
                        pass
        # 正则粗筛：skills/<name>/ 或 ~/.workbuddy/skills/<name>/
        # 不设白名单，不排除 URL — 第二阶段 LLM 精筛处理
        _ref_skill_re = re.compile(r'(?:skills|\.workbuddy/skills)/([a-zA-Z0-9_-]+)/')
        _candidates = []
        for _src_name, _src_body in _all_md:
            for _m in _ref_skill_re.finditer(_src_body):
                _sn = _m.group(1)
                if _sn == _current_skill:
                    continue
                _sd = os.path.join(_skills_root, _sn)
                if not os.path.isdir(_sd):
                    _src_line = _src_body[:_m.start()].count('\n') + 1
                    _ctx_start = max(0, _m.start() - 40)
                    _ctx_end = min(len(_src_body), _m.end() + 40)
                    _context = _src_body[_ctx_start:_ctx_end].replace('\n', ' ')
                    _candidates.append({
                        'skill': _sn,
                        'source': _src_name,
                        'line': _src_line,
                        'context': _context.strip()
                    })
        if _candidates:
            _lines = [f"  {c['source']}:{c['line']} - `{c['skill']}` (上下文: ...{c['context']}...)" for c in _candidates]
            issues["optional"].append(
                f"R-23: {filepath}:1 - 【两阶段】粗筛发现 {len(_candidates)} 个 MD 引用的技能目录不存在"
                f"，需 LLM 第二阶段精筛判断是否为真实过时描述（正则仅做粗筛，不阻断通过）：\n" + '\n'.join(_lines)
            )

    # 汇总
    must_n = len(issues["must"])
    suggest_n = len(issues["suggest"])
    optional_n = len(issues["optional"])
    total = must_n + suggest_n + optional_n

    if total == 0:
        return {"passed": True, "detail": f"{filepath}:1 - R-23: 文档-代码一致性检查通过（引用文件/函数均存在，调用方式一致）"}

    # 仅 optional（如两阶段粗筛产物）→ 通过，detail 带 NOTE
    if must_n == 0 and suggest_n == 0 and optional_n > 0:
        opt_msgs = "\n".join(issues["optional"])
        return {"passed": True,
                "detail": f"{filepath}:1 - R-23: ⓘ 两阶段粗筛 {optional_n} 条待 LLM 精筛确认（不阻断通过）：\n{opt_msgs}",
                "fix": None}

    # ── 检查 4: SKILL.md 中引用的规则编号范围是否与 rules.json 一致 ──
    _rules_spec_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'spec', 'rules.json'
    )
    if os.path.isfile(_rules_spec_path):
        try:
            with open(_rules_spec_path, 'r', encoding='utf-8') as f:
                _rules_data = json.load(f)
            _actual_max = _rules_data.get('_total_rules', 0)
            for m in re.finditer(r'R-(\d+)~R-(\d+)', content):
                claimed_max = int(m.group(2))
                if claimed_max != _actual_max:
                    line_no = content[:m.start()].count('\n') + 1
                    issues["must"].append(
                        f"{filepath}:{line_no} - SKILL.md 声称最大规则编号为 R-{claimed_max}，"
                        f"但 rules.json 实际为 R-{_actual_max}，描述可能过时"
                    )
        except Exception:
            pass

    msgs = []
    for k in ["must", "suggest", "optional"]:
        msgs.extend(issues[k])
    return {"passed": False,
            "detail": f"{filepath}:1 - R-23: 文档-代码一致性问题（{total} 条）：{msgs[0]}",
            # R-23 只检查，不自动修复——需要人工判断
            "fix": None}

def check_changelog_progressive(filepath, content, fm, body, **kw):
    """
    R-24: 更新日志（changelog）禁止直接在 SKILL.md。
    必须在 references/changelog.md 中，SKILL.md 只保留引用。
    """
    import os
    skill_dir = kw.get("skill_dir", "")
    skill_md_dir = os.path.dirname(filepath) if filepath else ""

    # 检查 SKILL.md 正文是否含有"更新日志" / "changelog" / "变更记录"章节
    changelog_pattern = re.compile(
        r'^##\s*(更新日志|changelog|变更记录|更新记录|版本历史)',
        re.MULTILINE | re.IGNORECASE
    )
    m = changelog_pattern.search(body)
    if m:
        line_no = body[:m.start()].count('\n') + 1
        # 找到绝对行号
        fm_lines = content[:len(content) - len(body)].count('\n') if body else 0
        abs_line = fm_lines + line_no
        return {
            "passed": False,
            "detail": f"{filepath}:{abs_line} - R-24: 更新日志章节直接在 SKILL.md 中，必须移至 references/changelog.md",
            "fix": {
                "key": "changelog_progressive",
                "location": f"{filepath}:{abs_line}",
                "operation": "将更新日志章节移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
                "verification": "重新运行 audit_skill()，确认 R-24 passed"
            }
        }

    # 检查 SKILL.md 正文是否含有版本号+更新描述的混合段落（松散检测）
    # 匹配如 "v2.3.0\n- 更新..." 或 "## v2.3.0" 等模式
    loose_pattern = re.compile(
        r'^(#\s+v\d+\.\d+\.\d+|[·•]\s*v\d+\.\d+\.\d+|-.+v\d+\.\d+\.\d+)',
        re.MULTILINE
    )
    # 只检测 H2 及以上的版本号标题
    h2_version = re.compile(r'^##\s+v?\d+\.\d+\.\d+', re.MULTILINE)
    m2 = h2_version.search(body)
    if m2:
        line_no = body[:m2.start()].count('\n') + 1
        fm_lines = content[:len(content) - len(body)].count('\n') if body else 0
        abs_line = fm_lines + line_no
        return {
            "passed": False,
            "detail": f"{filepath}:{abs_line} - R-24: SKILL.md 中含版本号标题（疑似更新日志），必须移至 references/changelog.md",
            "fix": {
                "key": "changelog_progressive",
                "location": f"{filepath}:{abs_line}",
                "operation": "将版本更新记录移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
                "verification": "重新运行 audit_skill()，确认 R-24 passed"
            }
        }

    # 检查 references/changelog.md 是否存在（推荐但不强制）
    changelog_path = os.path.join(skill_md_dir, "references", "changelog.md")
    if skill_dir:
        changelog_path2 = os.path.join(skill_dir, "references", "changelog.md")
        if os.path.isfile(changelog_path2):
            changelog_path = changelog_path2

    if not os.path.isfile(changelog_path):
        return {
            "passed": True,   # SKILL.md 中没有更新日志，通过
            "detail": f"{filepath}:1 - R-24: SKILL.md 无更新日志章节（references/changelog.md 不存在，但 SKILL.md 也未含日志，通过）",
        }

    return {"passed": True,
            "detail": f"{filepath}:1 - R-24: 更新日志在 references/changelog.md 中（SKILL.md 无内嵌日志，通过）"}


def body_check_document_format(filepath, content, fm, body, **kw):
    """
    R-25: 文档写作格式规范 (v2.44.0, v2.5.0 C-11/C-12, v2.6.0 C-13)
    10 项子检查：C-01 (ERROR) + C-02~C-10 (WARN 建议) + C-11 章节顺位 + C-12 格式合规 + C-13 渐进式索引表 + C-14 工作流步骤完整性。
    冲突排除：R-06 H1 存在性、R-21 渐进式加载固定模板句、R-24 更新日志位置、R-18/R-19 渐进式引用。
    全部子检查仅作建议标准统一，不强制改造。
    """
    issues = {"error": [], "warn": []}

    # ── 预清理：提取正文中非代码块的内容（代码块内的格式化模式不计入检查）──
    # 先替换所有 ```code``` 块为占位符，避免代码里匹配到伪格式化模式
    cleaned_body = re.sub(r'```[\s\S]*?```', '\n', body)
    # 排除行内代码
    tick = '\u0060'
    cleaned_body = re.sub(f'{tick}[^{tick}]+?{tick}', '', cleaned_body)

    # ════════════════════════════════════════════════════════════
    # C-01 (ERROR): H1 标题格式正确
    # 检查 H1 仅含技能名，可加 — 简短副标题，不含版本号
    # ════════════════════════════════════════════════════════════
    h1_match = re.search(r'^# (.+)', cleaned_body, re.MULTILINE)
    if h1_match:
        h1_text = h1_match.group(1).strip()
        # 检查是否含版本号
        if re.search(r'v?\d+\.\d+\.\d+', h1_text):
            line_no = body[:h1_match.start()].count('\n') + 1
            issues["error"].append(f"{filepath}:{line_no} - C-01: H1 标题含版本号「{h1_text}」，版本号应由 frontmatter version 字段管理")
        # 检查是否过于复杂（含 ## 或更深的标题内容混入）
        elif re.search(r'#{2,}', h1_text):
            line_no = body[:h1_match.start()].count('\n') + 1
            issues["error"].append(f"{filepath}:{line_no} - C-01: H1 标题格式异常「{h1_text}」，应为 # <技能名>")
        else:
            # 通过 — 不报 ERROR
            pass

    # ════════════════════════════════════════════════════════════
    # C-02 (WARN): 标题层级限制在 ## 和 ###
    # 不报 ####+ 的出现在允许范围内
    # 冲突排除：跳过 R-21 渐进式加载模板句中的引用格式
    # 冲突排除：跳过 R-24 更新日志可能提到的版本号标题
    # ════════════════════════════════════════════════════════════
    # 检查 H4+（#### 及更深）
    deep_heads = []
    for m in re.finditer(r'^#{4,}\s+', cleaned_body, re.MULTILINE):
        line_text = cleaned_body[m.start():m.start()+80].split('\n')[0]
        line_no = body[:m.start()].count('\n') + 1
        deep_heads.append(f"第{line_no}行「{line_text.strip()[:40]}」")
    if deep_heads:
        issues["warn"].append(f"C-02: 发现 {len(deep_heads)} 处 ####+ 深层标题（建议改用 ## 或 ###）：{'; '.join(deep_heads[:3])}")

    # ════════════════════════════════════════════════════════════
    # C-03 (WARN): 表格用于结构化信息展示
    # 检查正文中是否有表格（| 分隔行），如有则标记使用合理
    # 仅当完全没有表格但有结构化数据时提示
    # ════════════════════════════════════════════════════════════
    table_rows = re.findall(r'^\|.+\|$', cleaned_body, re.MULTILINE)
    # 检查是否有至少 3 行表格内容（表头+分隔+数据）
    has_substantial_table = False
    seen_tables = 0
    for line in table_rows:
        if re.match(r'^\|[\s\-:|]+\|$', line):
            continue  # 分隔行
        seen_tables += 1
        if seen_tables >= 3:
            has_substantial_table = True
            break
    if not has_substantial_table:
        # 检查是否有明显的键值对比数据（如文件映射、参数列表）但没有用表格
        structured_lines = [l for l in cleaned_body.split('\n') if '→' in l or '—' in l]
        if structured_lines and len(structured_lines) >= 5:
            issues["warn"].append("C-03: 正文包含较多键值对应关系（→ 或 — 分隔），建议用表格结构化展示")

    # ════════════════════════════════════════════════════════════
    # C-04 (WARN): 引用块 > 用于提示/注意/警告
    # 检查是否使用了 > 引用块
    # 冲突排除：R-21 的固定模板句也是引用块，不应计为"未使用"
    # ════════════════════════════════════════════════════════════
    blockquote_lines = [l for l in cleaned_body.split('\n') if l.strip().startswith('>')]
    if len(blockquote_lines) == 0:
        # 检查正文中是否有警告性提示（加粗的"注意"/"警告"/"注"）但没有用 > 包装
        warning_keywords = re.findall(r'\*\*(?:注意|警告|提示|注)\*\*', cleaned_body)
        if warning_keywords:
            issues["warn"].append("C-04: 正文含「注意/警告/提示」类关键词但未使用 > 引用块包装，建议统一使用 > 块")

    # ════════════════════════════════════════════════════════════
    # C-05 (WARN): 有序列表用于步骤，无序列表用于选项
    # 检查混合使用情况：同一章节内是否混用
    # ════════════════════════════════════════════════════════════
    sections = re.split(r'^##\s+', cleaned_body, flags=re.MULTILINE)
    for i, sec in enumerate(sections):
        if i == 0:
            continue
        has_ordered = bool(re.search(r'^\d+\.\s+', sec, re.MULTILINE))
        has_unordered = bool(re.search(r'^[-*]\s+', sec, re.MULTILINE))
        # 如果同时有有序和无序列表在同一章节内，且数量都不少，可能混用不当
        if has_ordered and has_unordered:
            ordered_count = len(re.findall(r'^\d+\.\s+', sec, re.MULTILINE))
            unordered_count = len(re.findall(r'^[-*]\s+', sec, re.MULTILINE))
            if ordered_count >= 3 and unordered_count >= 3:
                sec_title = sec.split('\n')[0].strip()
                issues["warn"].append(f"C-05: 章节「{sec_title[:20]}」同时包含有序列表({ordered_count}条)和无序列表({unordered_count}条)，建议区分：有序→步骤流程，无序→选项列举")

    # ════════════════════════════════════════════════════════════
    # C-06 (WARN): 加粗用于关键术语/约束
    # 检查正文是否使用了 **加粗** 标记
    # ════════════════════════════════════════════════════════════
    bold_markers = re.findall(r'\*\*[^*]+\*\*', cleaned_body)
    # 排除引用块内的加粗（C-04 已处理）和表格内的加粗（C-03 已处理）
    # 如果正文完全没有加粗，且正文较长（>100行），建议使用加粗
    if not bold_markers and len(body) > 500:
        issues["warn"].append("C-06: 正文未使用 **加粗** 标记，建议对关键术语/约束/规则名使用加粗强调")

    # ════════════════════════════════════════════════════════════
    # C-07 (WARN): 代码块使用语言标识
    # 检查所有的 ``` 代码块是否都有语言标识
    # ════════════════════════════════════════════════════════════
    code_fence_count = 0
    no_lang_count = 0
    no_lang_lines = []
    all_fences = list(re.finditer(r'^```', body, re.MULTILINE))
    code_fence_count = len(all_fences) // 2  # 仅统计起始 ```（成对的一半）
    for i, m in enumerate(all_fences):
        if i % 2 == 0:  # 起始 ```（i为偶数）
            line_text = body[m.start():body.find('\n', m.start())]
            if not re.search(r'```\w+', line_text):
                no_lang_count += 1
                line_no = body[:m.start()].count('\n') + 1
                no_lang_lines.append(str(line_no))
    if code_fence_count > 0 and no_lang_count > 0:
        lines_str = ", ".join(no_lang_lines[:5])
        issues["warn"].append(f"C-07: {no_lang_count}/{code_fence_count} 个代码块缺少语言标识（如 ```bash、```python、```json），位于第 {lines_str} 行，建议补充")

    # ════════════════════════════════════════════════════════════
    # C-08 (WARN): Checklist [ ] 用于操作前自检
    # 检查是否使用了 - [ ] checklist 格式
    # ════════════════════════════════════════════════════════════
    checklist_items = re.findall(r'^[-*]\s+\[\s*[ xX]?\s*\]', cleaned_body, re.MULTILINE)
    # 如果完全没有 checklist，但正文中包含"检查"/"确认"/"清单"等关键词，建议使用
    if not checklist_items:
        checklist_matches = list(re.finditer(r'(检查清单|自检|确认是否)', cleaned_body))
        if checklist_matches:
            details = "; ".join(
                f"L{body[:m.start()].count(chr(10)) + 1}「{m.group()[:30]}」"
                for m in checklist_matches[:3]
            )
            if len(checklist_matches) > 3:
                details += f" 等（共 {len(checklist_matches)} 处）"
            issues["warn"].append(f"C-08: 正文含「检查/确认/清单」类关键词但未使用 checklist 格式，触发位置：{details}")

    # ════════════════════════════════════════════════════════════
    # C-09 (WARN): → 详见 用于渐进式文件引用
    # 检查是否使用了 → 详见 references/xxx.md 格式
    # 冲突排除：R-18 反模式引用、R-19 FAQ 引用已有规则约束
    # ════════════════════════════════════════════════════════════
    arrow_refs = re.findall(r'→\s*详见?\s*`?references/', cleaned_body)
    simple_refs = re.findall(r'→\s*`?references/', cleaned_body)
    if not arrow_refs and not simple_refs:
        # 只检查 references/ 目录中是否有 .md 文件但 SKILL.md 没有引用的情况
        # 这个会在其他 R-18/R-19/R-24 中检查，这里不做交叉检查
        pass

    # ════════════════════════════════════════════════════════════
    # C-10 (WARN): 空行规范 — frontmatter 后及正文中过多的连续空白行
    # 代码块内的空行不计入（使用 body 原文而非 cleaned_body 时需排除代码块）
    # ════════════════════════════════════════════════════════════
    # 检查 frontmatter 闭合 --- 后的连续空行
    # 使用 content（全文）定位 frontmatter 结束位置
    fm_end = content.find('\n---')
    if fm_end >= 0:
        after_fm = content[fm_end + 4:]  # 跳过 \n---
        trailing_newlines = len(re.match(r'\n*', after_fm).group())
        if trailing_newlines > 2:
            issues["warn"].append(f"C-10: frontmatter 闭合 --- 后有 {trailing_newlines} 个连续空行（建议仅保留 1 个）")
    # 检查正文（排除代码块后）是否有连续 4+ 换行
    excess_blank = re.findall(r'\n{5,}', cleaned_body)
    if excess_blank:
        max_blank = max(len(b) for b in excess_blank)
        spots = len(excess_blank)
        issues["warn"].append(f"C-10: 正文中发现 {spots} 处连续 5+ 换行（最大 {max_blank} 行），建议精简到 1~2 个空行")

    # ════════════════════════════════════════════════════════════
    # C-11 (WARN): 章节顺位 — 检查 H2 出现顺序是否与 body.json section_order 一致
    # ════════════════════════════════════════════════════════════
    _section_order = _load_section_order()
    if _section_order:
        # 从 body（原始）提取 H2 标题（按出现顺序）
        h2_titles = []
        for m in re.finditer(r'^##\s+(.+)$', body, re.MULTILINE):
            h2_titles.append(m.group(1).strip())
        if h2_titles:
            # 构建 section_order 的别名查找表（canonical -> position）
            order_position = {}
            for pos, name in enumerate(_section_order):
                order_position[name.lower()] = pos

            # 将实际 H2 标题映射到顺序位置
            actual_positions = []
            unmapped = []
            for t in h2_titles:
                tl = t.lower()
                if tl in order_position:
                    actual_positions.append(order_position[tl])
                else:
                    # 尝试匹配 synonyms
                    found = False
                    for canon, syns in _section_order_synonyms().items():
                        if tl in [s.lower() for s in syns]:
                            actual_positions.append(order_position[canon.lower()])
                            found = True
                            break
                    if not found:
                        unmapped.append(t)
                        actual_positions.append(-1)

            # 检查逆序（相邻两个章节位置递减即为逆序）
            inversions = []
            for i in range(1, len(actual_positions)):
                if actual_positions[i] >= 0 and actual_positions[i-1] >= 0:
                    if actual_positions[i] < actual_positions[i-1]:
                        inversions.append((h2_titles[i-1], h2_titles[i]))
            if inversions:
                inv_details = "; ".join(f"「{a}」应在「{b}」之后" for a, b in inversions[:3])
                if len(inversions) > 3:
                    inv_details += f" 等（共 {len(inversions)} 处逆序）"
                issues["warn"].append(f"C-11: 章节顺位异常——{inv_details}（建议按 body.json section_order 调整顺序：H1→触发条件→核心能力→快速开始→工作流程→...）")
            elif unmapped:
                issues["warn"].append(f"C-11: 以下章节不在 section_order 白名单中：{'; '.join(unmapped[:3])}（建议按 body.json section_order 调整顺序或拆分到 references/）")
            else:
                pass  # 顺序正确，不报
    # 若无 section_order 数据，静默跳过 C-11

    # ════════════════════════════════════════════════════════════
    # C-12 (WARN): 章节格式合规 — 检查核心章节是否使用了 content_format 指定的格式
    # ════════════════════════════════════════════════════════════
    _sec_formats = _load_section_formats()
    if _sec_formats:
        # 提取每个 ## 章节的正文内容
        sections_raw = re.split(r'^(?=##\s+)', body, flags=re.MULTILINE)
        for sec_text in sections_raw:
            if not sec_text.strip() or not sec_text.startswith('## '):
                continue
            first_line = sec_text.split('\n')[0].strip()
            sec_title = re.sub(r'^##\s+', '', first_line).strip()
            sec_title_lower = sec_title.lower()

            # 查找此章节的 content_format 定义
            fmt = _sec_formats.get(sec_title_lower)
            if not fmt:
                # 尝试 synonyms
                for canon, syns in _section_order_synonyms().items():
                    if sec_title_lower in [s.lower() for s in syns]:
                        fmt = _sec_formats.get(canon.lower())
                        break

            if not fmt:
                continue

            fmt_type = fmt.get("type", "")
            sec_body = sec_text[len(first_line):].strip()
            sec_body_no_code = re.sub(r'```[\s\S]*?```', '', sec_body)

            # 检查表格类型章节是否真的有表格
            if fmt_type == "table":
                table_lines = [l for l in sec_body_no_code.split('\n') if l.strip().startswith('|') and '|' in l[1:]]
                if len(table_lines) < 3:
                    col_info = fmt.get("table_columns", [])
                    col_hint = f"（期望列：{', '.join(col_info)}）" if col_info else ""
                    issues["warn"].append(f"C-12: 章节「{sec_title[:20]}」的 content_format 要求用表格{col_hint}，但未检测到有效表格（至少 3 行）")

            # 检查列表类型章节是否真的有列表
            elif fmt_type in ("unordered_list", "ordered_list"):
                has_list_items = bool(re.search(r'^[-*]\s+', sec_body_no_code, re.MULTILINE))
                has_ordered = bool(re.search(r'^\d+\.\s+', sec_body_no_code, re.MULTILINE))
                if not has_list_items and not has_ordered:
                    issues["warn"].append(f"C-12: 章节「{sec_title[:20]}」的 content_format 要求用{'无序' if fmt_type=='unordered_list' else '有序'}列表，但未检测到列表项")

            # 检查代码块类型章节是否真的有代码块
            elif fmt_type == "code":
                has_code = bool(re.search(r'```\w*', sec_body))
                if not has_code:
                    issues["warn"].append(f"C-12: 章节「{sec_title[:20]}」的 content_format 要求用代码块，但未检测到 ``` 代码块")

            # ── 内容完整性检查：使用 classification_hints.format_clues 验证 ──
            hints = fmt.get("classification_hints", {})
            clues = hints.get("format_clues", [])
            if clues:
                missing_clues = []
                for clue in clues:
                    found = False
                    if clue == "正向触发":
                        found = "**正向触发**" in sec_body
                    elif clue == "否定条件":
                        found = "**否定条件**" in sec_body
                    elif clue == "表格":
                        found = bool(re.search(r'^\|.+\|$', sec_body_no_code, re.MULTILINE))
                    elif clue == "加粗":
                        found = bool(re.search(r'\*\*[^*]+\*\*', sec_body))
                    elif clue in ("编号列表", "序号"):
                        found = bool(re.search(r'^\d+\.\s+', sec_body_no_code, re.MULTILINE))
                    elif clue == "简短列表":
                        found = bool(re.search(r'^[-*]\s+', sec_body, re.MULTILINE))
                    elif clue == "流程图":
                        found = bool(re.search(r'[\u2193\u2192\u2191\u2193]', sec_body))
                    elif clue == "代码块":
                        found = bool(re.search(r'```', sec_body))
                    elif clue == "命令":
                        found = bool(re.search(r'`[^`]+`', sec_body))
                    elif clue in ("Q/A 对",):
                        found = bool(re.search(r'^Q:|^A:', sec_body_no_code, re.MULTILINE))
                    elif clue == "目录树":
                        found = bool(re.search(r'^[\u2502\u251c\u2514\u2500]|^[a-zA-Z]/', sec_body, re.MULTILINE))
                    elif clue in ("版本号",):
                        found = bool(re.search(r'\d+\.\d+\.\d+', sec_body))
                    elif clue == "日期":
                        found = bool(re.search(r'\d{4}-\d{2}-\d{2}', sec_body))
                    elif clue == "路径结构":
                        found = bool(re.search(r'[\\/]', sec_body))
                    elif clue == "一行一条":
                        items_c = len(re.findall(r'^[-*]\s+', sec_body, re.MULTILINE))
                        found = items_c > 0
                    else:
                        found = clue in sec_body
                    if not found:
                        missing_clues.append(clue)
                if missing_clues:
                    extra = ""
                    if "正向触发" in missing_clues and "正向触发" in clues:
                        extra = "（应分「**正向触发**」和「**否定条件**」两段）"
                    if "Q/A 对" in missing_clues:
                        extra = "（应使用 Q: / A: 格式）"
                    issues["warn"].append(
                        "C-12: 章节「" + sec_title[:20] + "」内容不完整——缺少格式要素：" + ", ".join(missing_clues) + extra
                    )
            if "约束" in sec_title:
                items_c = len(re.findall(r'^[-*]\s+', sec_body, re.MULTILINE))
                if items_c > 5:
                    issues["warn"].append("C-12: 章节「约束」共 " + str(items_c) + " 条，超过建议上限 5 条，建议精简或部分移到 references/")

            guidelines_str = fmt.get("guidelines", "")
            if guidelines_str:
                semantic_rules = []
                for sentence in re.split(r'[。；;]', guidelines_str):
                    s = sentence.strip()
                    if not s:
                        continue
                    if re.search(r'[应必][该须]?|[不得][能]?', s):
                        skip = all(clue in s for clue in clues if clue)
                        if not skip and len(s) > 6:
                            semantic_rules.append(s)
                if semantic_rules:
                    for rule in semantic_rules[:3]:
                        detail_preview = rule[:80].replace('\n', ' ')
                        issues["warn"].append(
                            "C-12: 章节「" + sec_title[:16] + "」" + detail_preview + "（需 LLM Phase 2 确认是否满足）"
                        )
    # C-13 (WARN): 渐进式索引表完整性 — 检查 ## 核心能力 末尾是否包含索引表
    # ════════════════════════════════════════════════════════════
    _c13_sd = kw.get("skill_dir", "")
    core_section_match = re.search(r'^##\s+(?:核心能力|核心功能|概述).*?(?=^##\s|\Z)', body, re.MULTILINE | re.DOTALL)
    if core_section_match:
        core_text = core_section_match.group(0)
        has_index_table = "### 渐进式文件索引" in core_text
        if has_index_table and _c13_sd:
            refs_dir = os.path.join(_c13_sd, "references")
            if os.path.isdir(refs_dir):
                actual_refs = sorted(f for f in os.listdir(refs_dir) if f.endswith('.md'))
                listed_refs = set()
                table_rows = re.findall(r'^\|.*?`(references/[^`]+)`.*?\|', core_text, re.MULTILINE)
                for r in table_rows:
                    fn = r.split('/')[-1] if '/' in r else r
                    listed_refs.add(fn)
                missing_from_table = [f for f in actual_refs if f not in listed_refs]
                if missing_from_table:
                    issues["warn"].append(f"C-13: references/ 中存在但渐进式索引表未列出的文件：{', '.join(missing_from_table[:5])}")
        elif not has_index_table and _c13_sd:
            refs_dir = os.path.join(_c13_sd, "references")
            if os.path.isdir(refs_dir):
                ref_count = len([f for f in os.listdir(refs_dir) if f.endswith('.md')])
                if ref_count > 0:
                    issues["warn"].append(f"C-13: references/ 目录有 {ref_count} 个 .md 文件，但 ## 核心能力 章节末尾缺少渐进式索引表（### 渐进式文件索引）")

    # ════════════════════════════════════════════════════════════
    # C-14 (WARN): 工作流程步骤完整性 — Phase 1 正则粗筛步骤数，Phase 2 LLM 确认
    # ════════════════════════════════════════════════════════════
    # 提取 ## 工作流程 章节中的编号步骤
    wf_section = re.search(r'^## 工作流程\n\n.*?(?=^## |\Z)', body, re.MULTILINE | re.DOTALL)
    if wf_section:
        wf_text = wf_section.group(0)
        steps = re.findall(r'^\d+\.\s+(.+)$', wf_text, re.MULTILINE)
        if steps:
            # Phase 1: 输出步骤列表供 LLM 精筛
            step_details = "; ".join(s[:40] for s in steps[:6])
            if len(steps) > 6:
                step_details += f" 等（共 {len(steps)} 步）"
            issues["warn"].append(
                f"C-14: ⓘ 工作流程共 {len(steps)} 步，需 LLM Phase 2 确认步骤是否完整覆盖实际代码功能（当前步骤：{step_details}）"
            )

        # ── C-14b: 检测工作流程中混入 changelog 风格内容（版本号+更新类关键词） ──
        # 检查 blockquote 行中是否含版本号标记
        versioned_lines = []
        for line in wf_text.split('\n'):
            if re.search(r'v\d+\.\d+\.\d+.*(?:新增|修复|修改|变更|优化)', line):
                versioned_lines.append(line.strip()[:60])
        if versioned_lines:
            issues["warn"].append(
                f"C-14: ⓘ 工作流程中含有 {len(versioned_lines)} 条版本标记内容（类似更新日志），"
                f"应移至 references/changelog.md，工作流程只保留步骤描述。"
                f"触发行：{' / '.join(versioned_lines[:3])}"
            )

    # ════════════════════════════════════════════════════════════
    # 汇总输出
    # ════════════════════════════════════════════════════════════
    error_count = len(issues["error"])
    warn_count = len(issues["warn"])
    total = error_count + warn_count

    if total == 0:
        return {"passed": True,
                "detail": f"{filepath}:1 - R-25: 文档写作格式规范检查通过（13项子检查均符合建议标准）"}

    detail_parts = []
    if error_count > 0:
        detail_parts.append(f"🔴 ERROR({error_count}): {'; '.join(issues['error'])}")
    if warn_count > 0:
        detail_parts.append(f"🟡 WARN({warn_count}): {'; '.join(issues['warn'][:20])}")
        if warn_count > 20:
            detail_parts[-1] += f" 等（共 {warn_count} 条建议）"

    return {"passed": error_count == 0,
            "detail": f"{filepath}:1 - R-25: {'; '.join(detail_parts)}"}
