#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 safe_io.py 的数据目录路径计算"""
import re

fp = r"C:\Users\sm001\.workbuddy\skills\skill-standardization\scripts\safe_io.py"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

old = (
    'SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
    'DATA_DIR_RAW = "skills/.standardization/skill-standardization/data/"\n'
    '_data_dir_abs = os.path.normpath(os.path.join(SKILL_ROOT, "..", DATA_DIR_RAW))\n'
    'BACKUP_DIR  = os.path.join(_data_dir_abs, "backup")\n'
    'OPS_LOG     = os.path.join(_data_dir_abs, "logs", "ops.log")'
)
new = (
    'SKILL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
    'SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))\n'
    'SKILL_DIR   = os.path.dirname(SCRIPT_DIR)\n'
    'SKILLS_ROOT  = os.path.dirname(SKILL_DIR)\n'
    'SKILL_NAME   = os.path.basename(SKILL_DIR)\n'
    'DATA_DIR      = os.path.join(SKILLS_ROOT, ".standardization", SKILL_NAME)\n'
    'BACKUP_DIR   = os.path.join(DATA_DIR, "backup")\n'
    'OPS_LOG      = os.path.join(DATA_DIR, "logs", "ops.log")'
)

if old in c:
    c = c.replace(old, new)
    # 同时修复 _ensure_data_dirs 中的 _data_dir_abs 引用
    c = c.replace("os.path.join(_data_dir_abs, \"logs\")",
                     "os.path.join(DATA_DIR, \"logs\")")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(c)
    print("✅ safe_io.py 已修复")
else:
    print("❌ 未找到匹配内容，手动检查")
    # debug: show the actual lines
    for i, line in enumerate(c.splitlines(), 1):
        if "DATA_DIR" in line or "SKILL_ROOT" in line or "_data_dir" in line:
            print(f"  L{i}: {repr(line)}")
