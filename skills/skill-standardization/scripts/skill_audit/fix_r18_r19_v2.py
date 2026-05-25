#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正确修复 R-18 和 R-19 函数（强制渐进式逻辑）
"""
import re, os

filepath = 'structure_checker.py'

# 读取备份（原始状态）
with open(filepath + '.bak', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 R-18 函数位置
r18_start = content.find('def body_has_antipattern_section(')
if r18_start == -1:
    print('ERROR: 找不到 R-18 函数')
    exit(1)

r18_end = content.find('\ndef ', r18_start + 1)
if r18_end == -1:
    r18_end = len(content)

# 找到 R-19 函数位置
r19_start = content.find('def body_has_faq_section(')
if r19_start == -1:
    print('ERROR: 找不到 R-19 函数')
    exit(1)

r19_end = content.find('\ndef ', r19_start + 1)
if r19_end == -1:
    r19_end = content.find('\n# ', r19_start + 1)
    if r19_end == -1:
        r19_end = len(content)

print(f'R-18: {r18_start} ~ {r18_end}')
print(f'R-19: {r19_start} ~ {r19_end}')

# 构造新的 R-18 函数（强制渐进式逻辑）
new_r18 = '''def body_has_antipattern_section(filepath, content, fm, body, **kw):
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
    has_ref = bool(re.search(r'references/antipatterns\\.md', body))
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
    ap_items = re.findall(r'^###\\s*AP-\\d+[:\\uff1a]', ap_content, re.MULTILINE)
    if not ap_items:
        ap_items = re.findall(r'^[-*]\\s*.+', ap_content, re.MULTILINE)
    if not ap_items:
        ap_items = re.findall(r'^\\d+\\.\\s*.+', ap_content, re.MULTILINE)
    # 表格格式支持
    if not ap_items:
        table_rows = re.findall(r'^\\|.*\\|$', ap_content, re.MULTILINE)
        data_rows = [r for r in table_rows if not re.match(r'^\\|[\\s\\-:|]+\\|$', r)]
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
    has_detail = bool(re.search(r'\\*\\*错误做法[:\\uff1a]\\*\\*|\\*\\*正确做法[:\\uff1a]\\*\\*|\\*\\*深层原因[:\\uff1a]\\*\\*', ap_content))
    
    if not has_detail:
        return {"passed": False,
                "detail": "references/antipatterns.md 缺少具体描述（须含 **错误做法：**、**正确做法：** 标记）",
                "fix": {"key": "antipattern_detail", "value": "add_detail",
                         "location": f"{antipattern_file}",
                         "operation": "为每个反模式添加 **错误做法：**、**正确做法：** 和 **深层原因：** 标记",
                         "verification": "重新运行 audit_skill()，确认 R-18 passed"}}
    
    return {"passed": True,
            "detail": f"反模式在 references/antipatterns.md 中（{len(ap_items)} 条具体示例，含错误做法/正确做法标记）"}

'''

# 构造新的 R-19 函数（强制渐进式逻辑）
new_r19 = '''def body_has_faq_section(filepath, content, fm, body, **kw):
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
    has_ref = bool(re.search(r'references/faq\\.md', body))
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
                         "operation": "用 Q: 问题\\n\\nA: 答案\\n\\n 格式重写 FAQ",
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

'''

# 替换：content[:r18_start] + new_r18 + new_r19 + content[r19_end:]
new_content = content[:r18_start] + new_r18 + new_r19 + content[r19_end:]

# 写回文件
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f'✅ R-18 和 R-19 函数已替换')
print(f'新文件长度: {len(new_content)} 字符')

# 语法检查
import py_compile
try:
    py_compile.compile(filepath, doraise=True)
    print('✅ 语法检查通过')
except py_compile.PyCompileError as e:
    print(f'❌ 语法错误: {e}')
    exit(1)
