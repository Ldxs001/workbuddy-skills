#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确修复 safe_io.py 常量定义（按行号）"""
fp = r"C:\Users\sm001\.workbuddy\skills\skill-standardization\scripts\safe_io.py"
with open(fp, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 第25-29行（0-indexed: 24-28）替换为新常量块
new_block = [
    'SKILL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n',
    'SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))\n',
    'SKILL_DIR   = os.path.dirname(SCRIPT_DIR)\n',
    'SKILLS_ROOT = os.path.dirname(SKILL_DIR)\n',
    'SKILL_NAME   = os.path.basename(SKILL_DIR)\n',
    'DATA_DIR     = os.path.join(SKILLS_ROOT, ".standardization", SKILL_NAME)\n',
    'BACKUP_DIR  = os.path.join(DATA_DIR, "backup")\n',
    'OPS_LOG      = os.path.join(DATA_DIR, "logs", "ops.log")\n',
]

# 替换第24-28行（5行 → 8行）
lines[24:29] = new_block

# 第68行（0-indexed 67）：_ensure_data_dirs 中的 _data_dir_abs 引用
if '_data_dir_abs' in lines[67]:
    lines[67] = lines[67].replace('_data_dir_abs', 'DATA_DIR')

with open(fp, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("✅ safe_io.py 已修复")
