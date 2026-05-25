#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/structure_checker.py — 正文结构检查函数 (R-06~R-09, R-18~R-20)
v2.17.0: 细化 R-07 触发词质量；新增 R-18 反模式具体性、R-19 FAQ 有意义性、R-20 写作规范
"""

import re
import os


def body_has_h1(filepath, content, fm, body, **kw):
    """R-06: 正文含一级标题检查"""
    m = re.search(r'^# .+', body, re.MULTILINE)
    if m is None:
        name = fm.get("name", "<技能名>") if fm else "<技能名>"
        return {"passed": False,
                "detail": "未找到一级标题 (# )",
                "fix": {"key": "h1", "value": name,
                         "location": f"{filepath} 正文开头",
                         "operation": f"添加一级标题: # {name}",
                         "verification": "重新运行 audit_skill()，确认 R-06 passed"}}
    return {"passed": True,
            "detail": f"发现一级标题: {m.group(0).strip()}"}


def _section_text(body, keywords):
    """
    提取 ## 章节的完整文本（到下个 ## 或文件末尾）。
    返回 (found: bool, title: str, text: str)。
    """
    lines = body.split("\n")
    in_section = False
    section_lines = []
    found_title = ""

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            if any(kw.lower() in title.lower() for kw in keywords):
                in_section = True
                found_title = title
                continue
            elif in_section:
                break
        if in_section:
            section_lines.append(line)

    if not found_title:
        return False, "", ""
    return True, found_title, "\n".join(section_lines)


def body_has_trigger_section(filepath, content, fm, body, **kw):
    """R-07: 触发条件章节质量检查（细化 v2.17.0）"""
    from .utils import TRIGGER_KEYWORDS

    found, title, section_text = _section_text(body, TRIGGER_KEYWORDS)
    if not found:
        return {"passed": False,
                "detail": f"未找到[{', '.join(TRIGGER_KEYWORDS)}]章节",
                "fix": {"key": "section_trigger", "value": True,
                         "location": f"{filepath} 正文",
                         "operation": "添加 ## 触发场景 章节，包含正向触发词≥3个、否定条件≥1个，无「自动执行」等危险表述",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查 1：正向触发词 ≥3 个 ──────────────────
    # 匹配：「当用户...」、「当...时」、列表项（- / 数字编号）
    trigger_patterns = [
        r'当用户.*时',
        r'当.*请求.*时',
        r'当.*要求.*时',
        r'[^。，\n]*触发[^。，\n]*',
        r'[-*]\s*.+[：:].+',   # 列表项格式：- 触发词：说明
    ]
    positive_triggers = set()
    for pat in trigger_patterns:
        for m in re.finditer(pat, section_text):
            t = m.group(0).strip()
            if len(t) > 4:   # 过滤太短的无意义匹配
                positive_triggers.add(t[:50])

    # 也直接取列表项作为触发词
    list_items = re.findall(r'^[-*]\s*.+', section_text, re.MULTILINE)
    for item in list_items:
        t = item.strip()[2:].strip()
        if len(t) > 2:
            positive_triggers.add(t[:50])

    if len(positive_triggers) < 3:
        return {"passed": False,
                "detail": f"触发词数量不足（当前 {len(positive_triggers)} 个，要求 ≥3 个），触发词须具体描述用户意图",
                "fix": {"key": "trigger_quality", "value": "add_triggers",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "添加至少 3 个具体触发词（描述用户会说什么/做什么来触发本技能）",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查 2：否定条件 ≥1 个 ──────────────────────
    negative_keywords = ["不触发", "不", "除非", "排除", "不适用", "not trigger", "won't", "don't"]
    has_negative = any(kw in section_text.lower() for kw in negative_keywords)
    if not has_negative:
        return {"passed": False,
                "detail": "缺少否定条件（须说明什么情况下不触发本技能）",
                "fix": {"key": "trigger_negative", "value": True,
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "添加「不触发」或「排除」段落，说明本技能不应该被触发的情况",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查 3：无危险表述 ────────────────────────────
    dangerous_phrases = ["自动执行", "auto-execute", "automatically execute", "无需询问", "直接执行", "silent execute"]
    found_dangerous = [p for p in dangerous_phrases if p in section_text]
    if found_dangerous:
        return {"passed": False,
                "detail": f"包含危险表述：{', '.join(found_dangerous)}",
                "fix": {"key": "trigger_danger", "value": "remove_dangerous",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": f"移除或改写危险表述：{', '.join(found_dangerous)}",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    return {"passed": True,
            "detail": f"触发条件章节质量合格（{len(positive_triggers)} 个触发词，含否定条件）"}


def body_has_core_section(filepath, content, fm, body, **kw):
    """R-08: 核心能力章节检查"""
    from .utils import CORE_KEYWORDS
    found, title, _ = _section_text(body, CORE_KEYWORDS)
    if not found:
        return {"passed": False,
                "detail": f"未找到[{', '.join(CORE_KEYWORDS)}]章节",
                "fix": {"key": "section_core", "value": True,
                         "location": f"{filepath} 正文",
                         "operation": "添加 ## 核心能力 章节，列出 3-5 条核心功能",
                         "verification": "重新运行 audit_skill()，确认 R-08 passed"}}
    return {"passed": True, "detail": f"发现章节: {title}"}


def body_has_workflow_section(filepath, content, fm, body, **kw):
    """R-09: 工作流程/使用方式章节检查"""
    from .utils import WORKFLOW_KEYWORDS
    found, title, _ = _section_text(body, WORKFLOW_KEYWORDS)
    if not found:
        return {"passed": False,
                "detail": f"未找到[{', '.join(WORKFLOW_KEYWORDS)}]章节",
                "fix": {"key": "section_workflow", "value": True,
                         "location": f"{filepath} 正文",
                         "operation": "添加 ## 工作流程 章节，用步骤列表描述执行流程",
                         "verification": "重新运行 audit_skill()，确认 R-09 passed"}}
    return {"passed": True, "detail": f"发现章节: {title}"}


# ──────────────────────────────────────────────────────────────
# R-18: 反模式具体性检查
# ──────────────────────────────────────────────────────────────

def body_has_antipattern_section(filepath, content, fm, body, **kw):
    """R-18: 反模式/常见错误章节具体性检查"""
    anti_keywords = ["反模式", "常见错误", "注意事项", "坑", "anti-pattern", "common mistake"]

    found, title, section_text = _section_text(body, anti_keywords)
    if not found:
        return {"passed": False,
                "detail": f"未找到[{', '.join(anti_keywords)}]章节（建议添加，帮助用户避坑）",
                "fix": {"key": "section_antipattern", "value": True,
                         "location": f"{filepath} 正文",
                         "operation": "添加 ## 反模式 或 ## 常见错误 章节，列出 2-3 个具体错误示例",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"},
                "skipped": True}   # 非强制，可跳过

    # 检查具体性：每条反模式须包含具体描述（≥20字）或代码示例
    items = re.findall(r'^[-*]\s*.+', section_text, re.MULTILINE)
    if not items:
        # 可能用了数字编号
        items = re.findall(r'^\d+\.\s*.+', section_text, re.MULTILINE)

    if len(items) < 2:
        return {"passed": False,
                "detail": f"反模式条目不足（当前 {len(items)} 条，建议 ≥2 条具体示例）",
                "fix": {"key": "antipattern_count", "value": "add_examples",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "添加至少 2 条具体反模式示例（须含具体错误描述和正确做法）",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}

    # 检查是否包含具体描述（每条至少 20 个非空白字符）
    min_len = 20
    vague_items = []
    for item in items:
        # 去掉列表标记
        text = re.sub(r'^[-*\d\.]\s*', '', item).strip()
        # 跳过水平线（全为 - 字符）
        if set(text) <= {'-', '—', '–'}:
            continue
        if len(text) < min_len:
            vague_items.append(text)

    if vague_items:
        return {"passed": False,
                "detail": f"反模式描述过于宽泛（{len(vague_items)} 条不足 {min_len} 字）：{', '.join(vague_items[:3])}",
                "fix": {"key": "antipattern_vague", "value": "add_detail",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "细化反模式描述，每条须说明具体错误现象和正确做法（≥20字）",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}

    return {"passed": True,
            "detail": f"反模式章节具体性合格（{len(items)} 条具体示例）"}


# ──────────────────────────────────────────────────────────────
# R-19: FAQ 有意义性检查
# ──────────────────────────────────────────────────────────────

def body_has_faq_section(filepath, content, fm, body, **kw):
    """R-19: FAQ/常见问题章节有意义性检查"""
    faq_keywords = ["FAQ", "常见问题", "Q&A", "Questions", "问答"]

    found, title, section_text = _section_text(body, faq_keywords)
    if not found:
        return {"passed": False,
                "detail": f"未找到[{', '.join(faq_keywords)}]章节（建议添加，降低重复提问）",
                "fix": {"key": "section_faq", "value": True,
                         "location": f"{filepath} 正文",
                         "operation": "添加 ## FAQ 或 ## 常见问题 章节，列出 3-5 个真实用户问题",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"},
                "skipped": True}   # 非强制，可跳过

    # 检查 Q&A 格式：须有 Q 和 A（或 ###/#### 子标题）
    has_q = bool(re.search(r'[Qq]\s*[:：]|问\s*[:：]|\*\*Q\b|\d+\.\s*[Qq]', section_text))
    has_a = bool(re.search(r'[Aa]\s*[:：]|答\s*[:：]|\*\*A\b|\d+\.\s*[Aa]', section_text))
    has_subhead = bool(re.search(r'^### |^#### ', section_text, re.MULTILINE))

    if not (has_q and has_a) and not has_subhead:
        return {"passed": False,
                "detail": "FAQ 格式不规范（须含 Q/A 标记或 ### 子标题分隔问题与答案）",
                "fix": {"key": "faq_format", "value": "add_qa_marks",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "用 Q: / A: 或 ### 问题标题 格式组织 FAQ，确保每对有问有答",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    # 检查问题有意义性：问题须具体（≥10字），答案须实质（≥15字）
    # 提取所有 Q/A 对
    qa_pairs = _extract_qa_pairs(section_text)
    if not qa_pairs:
        return {"passed": False,
                "detail": "无法解析 FAQ 内容（请确保使用 Q:/A: 或 ### 子标题格式）",
                "fix": {"key": "faq_unparsable", "value": "reformat",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "用 Q: 问题\n\nA: 答案\n\n 格式重写 FAQ",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    trivial_questions = ["如何工作", "怎么用", "what is", "how to", "帮助"]
    bad_pairs = []
    for q, a in qa_pairs:
        q_trim = q.strip()
        a_trim = a.strip()
        # 问题太短或无意义
        if len(q_trim) < 10 or any(t in q_trim.lower() for t in trivial_questions):
            bad_pairs.append(f"Q: {q_trim[:30]}")
        # 答案太短或无实质
        if len(a_trim) < 15 or a_trim in ("请参考文档", "见上文", "see above"):
            bad_pairs.append(f"A: {a_trim[:30]}")

    if bad_pairs:
        return {"passed": False,
                "detail": f"FAQ 包含低质量条目（{len(bad_pairs)} 条）：{', '.join(bad_pairs[:3])}",
                "fix": {"key": "faq_quality", "value": "improve_qa",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "改进 FAQ 质量：问题须具体（≥10字），答案须有实质内容（≥15字），避免万能回答",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}

    return {"passed": True,
            "detail": f"FAQ 有意义性合格（{len(qa_pairs)} 对 Q&A）"}


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


# ──────────────────────────────────────────────────────────────
# R-20: 写作规范检查
# ──────────────────────────────────────────────────────────────

def body_check_writing_standards(filepath, content, fm, body, **kw):
    """R-20: 写作规范检查（术语一致性、禁止表述、中英文混排）"""
    issues = []

    # ── 检查1：术语一致性 ──────────────────────────────────
    # 同一概念不应混用多种表述
    term_groups = [
        (["创建", "建立", "新建"], "创建"),
        (["更新", "修改", "编辑", "变更"], "更新"),
        (["删除", "移除", "去掉"], "删除"),
        (["配置", "设置", "设定"], "配置"),
    ]
    lines = body.split("\n")
    for group, preferred in term_groups:
        found_terms = {}
        for line in lines:
            for term in group:
                if term in line:
                    found_terms.setdefault(term, []).append(line[:50])
        if len(found_terms) > 1:
            terms_str = ", ".join(found_terms.keys())
            issues.append(f"术语不一致：混用 {terms_str}，建议统一为「{preferred}」")

    # ── 检查2：禁止表述 ────────────────────────────────────
    forbidden = [
        ("可能", "避免模糊表述，改用确定性描述"),
        ("应该", "避免建议性表述，改用确定性描述或明确标注「建议」"),
        ("大概", "避免模糊表述"),
        ("差不多", "避免模糊表述"),
    ]
    for word, suggestion in forbidden:
        # 只在正文中检查（排除代码块）
        cleaned = re.sub(r'```.*?```', '', body, flags=re.DOTALL)
        cleaned = re.sub(r'`[^`]+`', '', cleaned)
        if word in cleaned:
            issues.append(f"含模糊表述「{word}」：{suggestion}")

    # ── 检查3：中英文混排空格 ────────────────────────────
    # 中文与英文/数字之间应有空格（例外：版本号、类名）
    # 简单检查：中文后直接跟英文单词（无空格）
    mingled = re.findall(r'[\u4e00-\u9fff][A-Za-z]{2,}|[A-Za-z]{2,}[\u4e00-\u9fff]', body)
    mingled = [m for m in mingled if not re.match(r'v\d|SKILL|MD|JSON|YAML', m)]
    if mingled:
        issues.append(f"中英文混排缺少空格：{', '.join(mingled[:5])}")

    if issues:
        detail = "；".join(issues[:3])
        return {"passed": False,
                "detail": f"写作规范问题：{detail}",
                "fix": {"key": "writing_standards", "value": "fix_terms",
                         "location": f"{filepath} 正文",
                         "operation": "统一术语表述、移除模糊用词、修正中英文混排空格",
                         "verification": "重新运行 audit_skill()，确认 R-20 passed"}}

    return {"passed": True,
            "detail": "写作规范检查通过（术语一致、无禁止表述、中英文混排规范）"}
