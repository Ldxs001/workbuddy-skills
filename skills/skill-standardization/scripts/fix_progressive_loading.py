#!/usr/bin/env python3
"""修复 SILL.md 渐进式加载模板句（R-21）"""
import os

skill_md = os.path.join(os.path.dirname(__file__), '..', 'SKILL.md')
skill_md = os.path.abspath(skill_md)

with open(skill_md, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到渐进式加载那一行并修复
target = '> 📚 **渐进式加载**'
fixed = '> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。\n'

new_lines = []
for line in lines:
    if line.startswith(target) and '为入口' in line and '`SKILL.md`' not in line:
        # 缺反引号，修复
        new_lines.append(fixed)
    else:
        new_lines.append(line)

# 原子写入
tmp = skill_md + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
os.replace(tmp, skill_md)
print("OK: 渐进式加载模板句已修复")
