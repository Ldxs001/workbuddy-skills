#!/usr/bin/env python3
"""修复 R-06（缺一级标题）和 R-20（术语不一致）"""
import os, re

skill_md = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'SKILL.md'))

with open(skill_md, 'r', encoding='utf-8') as f:
    content = f.read()

# === R-06 修复：在 --- 之后插入一级标题 ===
# 找到 frontmatter 结束位置
fm_end = content.find('\n---')
if fm_end == -1:
    print("ERROR: 找不到 frontmatter 结束标记")
    exit(1)

# 在 ---\n 之后、第一个非空行之前插入一级标题
insert_pos = fm_end + len('\n---\n')
# 检查是否已经有 # skill-standardization
if '# skill-standardization' not in content:
    content = content[:insert_pos] + '\n# skill-standardization v2.33.0\n' + content[insert_pos:]

# === R-20 修复：统一术语「修改」→「更新」（约束章节除外，保留原文语义）===
# 只改 SILL.md 正文中的版本/内容更新描述，不改约束章节的「修改」一词
# 具体：把「变更记录」→「更新记录」，「改写类型」→「更新类型」（如 references/changelog.md 引用）
# 这里修 SILL.md 里的「变更」→「更新」
replacements = [
    ('变更记录', '更新记录'),
    ('变更日志', '更新日志'),
]
for old, new in replacements:
    content = content.replace(old, new)

# 原子写入
tmp = skill_md + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(content)
os.replace(tmp, skill_md)
print("OK: R-06 一级标题已补回，R-20 术语已统一")
