#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/structure_checker.py — 正文结构检查函数 (R-06~R-09, R-18~R-20)
v2.22.0: R-18/R-19/R-20 新增渐进式文件（references/*.md）审查支持
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
                "detail": f"触发词数量不足（当前 {len(positive_triggers)} 个，要求 ≥3 个）",
                "fix": {"key": "trigger_quality", "value": "add_triggers",
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "添加至少 3 个具体触发词（描述用户会说什么/做什么来触发本技能）",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查2：否定条件 ≥1 个 ──────────────────────
    negative_keywords = ["不触发", "不", "除非", "排除", "不适用", "not trigger", "won't", "don't"]
    has_negative = any(kw in section_text.lower() for kw in negative_keywords)
    if not has_negative:
        return {"passed": False,
                "detail": "缺少否定条件（须说明什么情况下不触发本技能）",
                "fix": {"key": "trigger_negative", "value": True,
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "添加「不触发」或「排除」段落，说明本技能不应该被触发的情况",
                         "verification": "重新运行 audit_skill()，确认 R-07 passed"}}

    # ── 质量检查3：无危险表述 ────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# R-18: 反模式具体性检查
# ─────────────────────────────────────────────────────────────

def body_has_antipattern_section(filepath, content, fm, body, **kw):
    """R-18: 反模式/常见错误章节具体性检查（必须渐进式，v2.24.7 重构）"""
    antipattern_keywords = ["反模式", "常见错误", "注意事项", "坑", "anti-pattern", "common mistake"]
    
    # 1. 检查 SKILL.md 是否直接包含反模式章节（这是错的，必须用渐进式）
    found, title, section_text = _section_text(body, antipattern_keywords)
    
    if found:
        return {"passed": False,
                "detail": f"反模式不应直接写在 SKILL.md 的 ## {title} 章节里，须改用渐进式（移到 references/antipatterns.md）",
                "fix": {"key": "antipattern_progressive", "value": True,
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "将反模式内容移到 references/antipatterns.md，在 SKILL.md 中添加引用 `→ 详见 references/antipatterns.md`",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}
    
    # 2. 检查 SKILL.md 是否有引用 references/antipatterns.md
    has_ref = bool(re.search(r'references/antipatterns\.md', body))
    if not has_ref:
        return {"passed": False,
                "detail": "未找到对 references/antipatterns.md 的引用（反模式须用渐进式）",
                "fix": {"key": "antipattern_reference", "value": True,
                         "location": f"{filepath} 正文",
                         "operation": "创建 references/antipatterns.md，并在 SKILL.md 中添加引用 `→ 详见 references/antipatterns.md`",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}
    
    # 3. 检查 references/antipatterns.md 是否存在
    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    antipattern_file = os.path.join(skill_dir, 'references', 'antipatterns.md')
    
    if not os.path.isfile(antipattern_file):
        return {"passed": False,
                "detail": "SKILL.md 引用了 references/antipatterns.md 但该文件不存在",
                "fix": {"key": "antipattern_file_missing", "value": True,
                         "location": f"{antipattern_file}",
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
                "detail": f"references/antipatterns.md 反模式条目不足（当前 {len(ap_items)} 条，要求 ≥2 条）",
                "fix": {"key": "antipattern_count", "value": "add_examples",
                         "location": f"{antipattern_file}",
                         "operation": "添加至少 2 条具体反模式示例（须含 **错误做法：**、**正确做法：** 标记），支持列表/表格/### 标题格式",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}
    
    # 检查是否有具体描述（错误做法/正确做法标记）
    has_detail = bool(re.search(r'\*\*错误做法[:\uff1a]\*\*|\*\*正确做法[:\uff1a]\*\*|\*\*深层原因[:\uff1a]\*\*', ap_content))
    
    if not has_detail:
        return {"passed": False,
                "detail": "references/antipatterns.md 缺少具体描述（须含 **错误做法：**、**正确做法：** 标记）",
                "fix": {"key": "antipattern_detail", "value": "add_detail",
                         "location": f"{antipattern_file}",
                         "operation": "为每个反模式添加 **错误做法：**、**正确做法：** 和 **深层原因：** 标记",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}
    
    return {"passed": True,
            "detail": f"反模式在 references/antipatterns.md 中（{len(ap_items)} 条具体示例，含错误做法/正确做法标记）"}

def body_has_faq_section(filepath, content, fm, body, **kw):
    """R-19: FAQ/常见问题章节有意义性检查（必须渐进式，v2.24.7 重构）"""
    faq_keywords = ["FAQ", "常见问题", "Q&A", "Questions", "问答"]
    
    # 1. 检查 SKILL.md 是否直接包含 FAQ 章节（这是错的，必须用渐进式）
    found, title, section_text = _section_text(body, faq_keywords)
    
    if found:
        return {"passed": False,
                "detail": f"FAQ 不应直接写在 SKILL.md 的 ## {title} 章节里，须改用渐进式（移到 references/faq.md）",
                "fix": {"key": "faq_progressive", "value": True,
                         "location": f"{filepath} ## {title} 章节",
                         "operation": "将 FAQ 内容移到 references/faq.md，在 SKILL.md 中添加引用 `→ 详见 references/faq.md`",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}
    
    # 2. 检查 SKILL.md 是否有引用 references/faq.md
    has_ref = bool(re.search(r'references/faq\.md', body))
    if not has_ref:
        return {"passed": False,
                "detail": "未找到对 references/faq.md 的引用（FAQ 须用渐进式）",
                "fix": {"key": "faq_reference", "value": True,
                         "location": f"{filepath} 正文",
                         "operation": "创建 references/faq.md，并在 SKILL.md 中添加引用 `→ 详见 references/faq.md`",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}
    
    # 3. 检查 references/faq.md 是否存在
    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    faq_file = os.path.join(skill_dir, 'references', 'faq.md')
    
    if not os.path.isfile(faq_file):
        return {"passed": False,
                "detail": "SKILL.md 引用了 references/faq.md 但该文件不存在",
                "fix": {"key": "faq_file_missing", "value": True,
                         "location": f"{faq_file}",
                         "operation": "创建 references/faq.md，包含至少 3 对 Q&A（问题 ≥10 字，答案 ≥15 字）",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}
    
    # 4. 检查 references/faq.md 内容质量
    with open(faq_file, 'r', encoding='utf-8') as f:
        faq_content = f.read()
    
    # 提取 Q&A 对
    faq_qa = _extract_qa_pairs(faq_content)
    
    if not faq_qa:
        return {"passed": False,
                "detail": "references/faq.md 无法解析 Q&A 内容（请确保使用 Q:/A: 或 ### 子标题格式）",
                "fix": {"key": "faq_unparsable", "value": "reformat",
                         "location": f"{faq_file}",
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
                "detail": f"FAQ 包含低质量条目（{len(bad_pairs)} 条）：{', '.join(bad_pairs[:3])}",
                "fix": {"key": "faq_quality", "value": "improve_qa",
                         "location": f"{faq_file}",
                         "operation": "改进 FAQ 质量：问题须具体（≥10字），答案须有实质内容（≥15字），避免万能回答",
                         "verification": "重新运行 audit_skill()，确认 R-19 passed"}}
    
    return {"passed": True,
            "detail": f"FAQ 在 references/faq.md 中（{len(faq_qa)} 对 Q&A）"}


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


# ─────────────────────────────────────────────────────────────
# R-20: 写作规范检查
# ─────────────────────────────────────────────────────────────

def _check_writing_standards_text(text, filename=""):
    """
    检查文本的写作规范，返回分级 issues 字典。
    供 body_check_writing_standards() 和渐进式文件检查复用。

    返回格式：
    {
        "must": [],    # 🔴 必须修：术语不一致、事实错误
        "suggest": [], # 🟡 建议修：模糊表述、缺少空格
        "optional": []  # ⚪ 可选择修：风格偏好
    }
    """
    issues = {"must": [], "suggest": [], "optional": []}

    # ── 检查1：术语一致性（🔴 必须修）───────────────────
    term_groups = [
        (["创建", "建立", "新建"], "创建"),
        (["更新", "修改", "变更"], "更新"),
        (["删除", "移除", "去掉"], "删除"),
        (["配置", "设置", "设定"], "配置"),
    ]
    lines = text.split("\n")
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
    cleaned = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'`[^`]+?`', '', cleaned)
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
    mingled = re.findall(r'[一-鿿][A-Za-z]{2,}|[A-Za-z]{2,}[一-鿿]', text)
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

    # ── 检查 SKILL.md 正文 ─────────────────────────
    issues = _check_writing_standards_text(body, "SKILL.md")
    for k in all_issues:
        all_issues[k] += issues[k]

    # ── 新增：脚本调用验证检查（v2.24.4）────────────────────
    # 检查 SKILL.md 里提到的脚本是否真实存在、能否正常运行（--help 验证）
    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    if skill_dir and os.path.isdir(skill_dir):
        import re, subprocess
        
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
                # v2.24.4 修复：跳过包含变量的路径（如 {SKILL_DIR}/scripts/...）
                if '{' in script_path or '}' in script_path:
                    continue
                script_paths.add(script_path)
        
        # 3. 检查脚本文件是否存在、能否运行 --help
        for script_path in script_paths:
            full_path = os.path.join(skill_dir, script_path)
            if not os.path.isfile(full_path):
                all_issues["suggest"].append(f"SKILL.md 提到脚本 `{script_path}` 但文件不存在（期望路径：{full_path}）")
            else:
                # 尝试运行 --help 验证脚本可调用
                try:
                    result = subprocess.run(
                        ['python', full_path, '--help'],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode != 0:
                        all_issues["suggest"].append(f"脚本 `{script_path}` --help 返回非零退出码（{result.returncode}），可能参数定义有误")
                except subprocess.TimeoutExpired:
                    all_issues["suggest"].append(f"脚本 `{script_path}` --help 超时（>5秒），可能有问题")
                except FileNotFoundError:
                    all_issues["suggest"].append(f"脚本 `{script_path}` 无法运行（python 命令不存在？）")
                except Exception as e:
                    all_issues["suggest"].append(f"脚本 `{script_path}` 运行出错：{str(e)[:100]}")
    
        # ── 检查渐进式文件 references/*.md ────────────────
    skill_dir = kw.get('skill_dir', os.path.dirname(filepath))
    refs_dir = os.path.join(skill_dir, 'references')
    if os.path.isdir(refs_dir):
        for fname in sorted(os.listdir(refs_dir)):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(refs_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    ref_content = f.read()
            except Exception:
                continue
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

    # 格式化输出
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
    found, title, section_text = _section_text(body, ["核心能力", "核心功能", "概述", "Overview", "技能概述"])
    if found:
        prominent_texts.append(("核心能力", title, section_text))
    # 硬编码检查 ## 工作流程
    found, title, section_text = _section_text(body, ["工作流程", "使用方式", "Workflow", "完整执行流程", "核心指令", "完整工作流"])
    if found:
        prominent_texts.append(("工作流程", title, section_text))
    
    if not prominent_texts:
        return {"passed": False,
                "detail": "未找到核心能力/工作流程章节，无法检查渐进式加载显式说明",
                "fix": {"key": "progressive_loading_explicit", "value": True,
                         "location": f"{filepath} ## 核心能力 或 ## 工作流程 章节",
                         "operation": f"在 ## 核心能力 章节添加固定模板句：{FIXED_TEMPLATE}",
                         "verification": "重新运行 audit_skill()，确认 R-21 passed"}}
    
    # v2.24.2：直接搜固定模板句子（原封不动，可后面接其他内容）
    for section_name, title, section_text in prominent_texts:
        for line in section_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(FIXED_TEMPLATE) or stripped == FIXED_TEMPLATE:
                return {"passed": True,
                        "detail": f"在 ## {title} 章节发现渐进式加载固定模板句"}
    
    # 未找到固定模板句
    first_section = prominent_texts[0][0]
    first_title   = prominent_texts[0][1]
    return {"passed": False,
            "detail": f"在 ## {first_title} 等显眼章节未找到渐进式加载固定模板句",
            "fix": {"key": "progressive_loading_explicit", "value": True,
                     "location": f"{filepath} ## {first_section} 章节",
                     "operation": f"在 ## {first_section} 章节添加固定模板句：{FIXED_TEMPLATE}（必须原封不动，可在后面接其他说明）",
                     "verification": "重新运行 audit_skill()，确认 R-21 passed"}}


