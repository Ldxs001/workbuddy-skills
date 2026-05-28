#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 SKILL.md 三处问题"""
fp = r"C:\Users\sm001\.workbuddy\skills\skill-standardization\SKILL.md"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

# ① description 字段
old_desc = (
    'description: Skill 标准化规范引擎 v2.38.4。'
    'fix.py 增加文件性质分辨+引用修正；'
    'artifact_checker.py 根目录白名单修复；run_audit.py 移入 scripts/。'
)
new_desc = (
    'description: '
    'Skill 标准化规范引擎 v2.38.4。'
    '支持 R-01~R-23 规范审查（audit/create/refactor 三模式），'
    '含权限扫描、数据目录合规检查、渐进式加载。'
)
if old_desc in c:
    c = c.replace(old_desc, new_desc)
    print("  ✅ description 已修复")
else:
    print("  ⚠️  description 未匹配（可能已改）")

# ② H1 标题版本号
c = c.replace("# skill-standardization v2.38.3", "# skill-standardization v2.38.4")
print("  ✅ H1 标题版本号已修复")

# ③ 第71行 R-01~R-24 → R-01~R-23
c = c.replace("执行 R-01~R-24 规范审查", "执行 R-01~R-23 规范审查")
print("  ✅ 规则范围 R-24 → R-23")

with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
print("✅ SKILL.md 全部修复完成")
