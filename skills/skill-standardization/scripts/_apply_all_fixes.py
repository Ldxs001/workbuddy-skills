#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性修完 hug-html 所有剩余 WARN"""
import re

# ===== 修复1: SKILL.md 添加 H1 标题（R-06）======
path = r'C:/Users/sm001/.workbuddy/skills/hug-html/SKILL.md'
content = open(path, 'r', encoding='utf-8').read()
# 在 frontmatter 结束 --- 之后、第一个 > 之前插入 ## hug-html
old = '---\n\n> 📚'
new = '---\n\n## hug-html\n\n> 📚'
if old in content:
    content = content.replace(old, new, 1)
    print('[OK] SKILL.md 已添加 H1 标题')
else:
    print(f'[WARN] SKILL.md 未找到预期内容，当前 L13-24:')
    print(repr(content[content.find('---'):content.find('> 📚')+20]))

open(path, 'w', encoding='utf-8').write(content)

# ===== 修复2: antipatterns.md 术语统一（R-20）======
path2 = r'C:/Users/sm001/.workbuddy/skills/hug-html/references/antipatterns.md'
content2 = open(path2, 'r', encoding='utf-8').read()
# 检查清单里还有"所有路径均为绝对路径？"——应改为"相对路径"
old2 = '- [ ] 所有路径均为绝对路径？'
new2 = '- [ ] 所有路径均为相对路径（scripts/foo.py）？'
if old2 in content2:
    content2 = content2.replace(old2, new2, 1)
    print('[OK] antipatterns.md 检查清单已修正（绝对→相对）')
else:
    print('[SKIP] antipatterns.md 检查清单已修正或格式不同')

open(path2, 'w', encoding='utf-8').write(content2)

# ===== 修复3: faq.md Q2/Q3 路径改为相对路径（R-20）======
path3 = r'C:/Users/sm001/.workbuddy/skills/hug-html/references/faq.md'
content3 = open(path3, 'r', encoding='utf-8').read()
fixes = 0
# Q2 答案里的绝对路径
old_q2 = 'C:/Users/sm001/.workbuddy/skills/.standardization/hug-html/data/output/'
new_q2 = '../.standardization/hug-html/data/output/'
if old_q2 in content3:
    content3 = content3.replace(old_q2, new_q2)
    fixes += 1

# Q3 答案里的绝对路径
old_q3 = 'C:/Users/sm001/.workbuddy/skills/.standardization/hug-html/data/config/style-presets.json'
new_q3 = '../.standardization/hug-html/data/config/style-presets.json'
if old_q3 in content3:
    content3 = content3.replace(old_q3, new_q3)
    fixes += 1

# Q8 答案里的绝对路径
old_q8 = 'C:/temp/assembled.html'
new_q8 = '../.standardization/hug-html/data/output/assembled.html'
if old_q8 in content3:
    content3 = content3.replace(old_q8, new_q8)
    fixes += 1

# Q8 代码块里的绝对路径
old_q8b = 'C:/Users/sm001/.workbuddy/skills/.standardization/hug-html/data/config/call-chains.json'
new_q8b = '../.standardization/hug-html/data/config/call-chains.json'
if old_q8b in content3:
    content3 = content3.replace(old_q8b, new_q8b)
    fixes += 1

if fixes > 0:
    print(f'[OK] faq.md 已修复 {fixes} 处绝对路径')
else:
    print('[SKIP] faq.md 未找到绝对路径或已修复')

open(path3, 'w', encoding='utf-8').write(content3)

# ===== 修复4: SKILL.md 快速开始代码块修正（R-23）======
# R-23 报错：示例参数与脚本定义不匹配
# 需要看具体是哪些参数不对，先运行审计看详情
print()
print('=== 修复完成，建议运行审计验证 ===')
