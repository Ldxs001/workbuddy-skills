#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_data_dir.py — 修复 skill-standardization 所有脚本的数据目录路径计算

修复内容：
1. 去掉硬编码的 "skills/" 前缀和 "data/" 后缀
2. 动态计算 SKILLS_ROOT（安装根目录），通用不依赖安装结构
3. DATA_DIR = os.path.join(SKILLS_ROOT, ".standardization", SKILL_NAME)
4. 子目录（backup/、logs/ 等）由 DATA_DIR 拼接
"""
import os
import re

SKILL_NAME = "skill-standardization"

def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 计算正确的替换内容
    # 替换常量定义块
    # 针对 safe_io.py
    content = re.sub(
        r'(SKILL_ROOT\s*=\s*os\.path\.dirname\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\))\s*\n'
        r'(DATA_DIR_RAW\s*=\s*")[^"]*("\s*\n)'
        r'(_data_dir_abs\s*=\s*os\.path\.normpath\(os\.path\.join\(SKILL_ROOT,\s*"[^"]*"\)\))\s*\n'
        r'(BACKUP_DIR\s*=\s*os\.path\.join\(_data_dir_abs,\s*"[^"]*"\))\s*\n'
        r'(OPS_LOG\s*=\s*os\.path\.join\(_data_dir_abs,\s*"[^"]*",\s*"[^"]*"\))',
        lambda m: (
            'SKILL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
            'SKILLS_ROOT  = os.path.dirname(SKILL_ROOT)\n'
            'DATA_DIR      = os.path.join(SKILLS_ROOT, ".standardization", "' + SKILL_NAME + '")\n'
            'BACKUP_DIR   = os.path.join(DATA_DIR, "backup")\n'
            'OPS_LOG      = os.path.join(DATA_DIR, "logs", "ops.log")'
        ),
        content
    )

    # 针对 op_logger.py
    content = re.sub(
        r'(DEFAULT_DATA_DIR_RAW\s*=\s*")[^"]*("\s*\n)'
        r'(SKILL_ROOT\s*=\s*os\.path\.dirname\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\))\s*\n'
        r'(_data_dir_abs\s*=\s*os\.path\.normpath\(os\.path\.join\(SKILL_ROOT,\s*"[^"]*"\)\))\s*\n'
        r'(LOGS_DIR\s*=\s*os\.path\.join\(_data_dir_abs,\s*"[^"]*"\))\s*\n'
        r'(OPS_LOG\s*=\s*os\.path\.join\(LOGS_DIR,\s*"[^"]*"\))',
        lambda m: (
            'DEFAULT_DATA_DIR_RAW = "../.standardization/' + SKILL_NAME + '/"\n'
            'SKILL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
            'SKILLS_ROOT  = os.path.dirname(SKILL_ROOT)\n'
            'DATA_DIR      = os.path.join(SKILLS_ROOT, ".standardization", "' + SKILL_NAME + '")\n'
            'LOGS_DIR     = os.path.join(DATA_DIR, "logs")\n'
            'OPS_LOG      = os.path.join(LOGS_DIR, "ops.log")'
        ),
        content
    )

    # 针对 skill_rollback.py
    content = re.sub(
        r'(DEFAULT_DATA_DIR_RAW\s*=\s*")[^"]*("\s*\n)'
        r'(SKILL_ROOT\s*=\s*os\.path\.dirname\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\))\s*\n'
        r'(_data_dir_abs\s*=\s*os\.path\.normpath\(os\.path\.join\(SKILL_ROOT,\s*"[^"]*"\)\))\s*\n'
        r'(BACKUP_DIR\s*=\s*os\.path\.join\(_data_dir_abs,\s*"[^"]*"\))\s*\n'
        r'(MANIFEST_FILE\s*=\s*os\.path\.join\(BACKUP_DIR,\s*"[^"]*"\))',
        lambda m: (
            'DEFAULT_DATA_DIR_RAW = "../.standardization/' + SKILL_NAME + '/"\n'
            'SKILL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
            'SKILLS_ROOT  = os.path.dirname(SKILL_ROOT)\n'
            'DATA_DIR      = os.path.join(SKILLS_ROOT, ".standardization", "' + SKILL_NAME + '")\n'
            'BACKUP_DIR   = os.path.join(DATA_DIR, "backup")\n'
            'MANIFEST_FILE = os.path.join(BACKUP_DIR, "manifest.txt")'
        ),
        content
    )

    if content == original:
        print(f"  ⚠  {filepath}: 未匹配到需要替换的内容（可能已修复或格式不同）")
        return False
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ {filepath}: 已修复")
        return True

print("=" * 60)
print("修复 skill-standardization 数据目录路径")
print("=" * 60)

base = r"C:\Users\sm001\.workbuddy\skills\skill-standardization\scripts"
files = ["safe_io.py", "op_logger.py", "skill_rollback.py"]
ok = 0
for f in files:
    fp = os.path.join(base, f)
    print(f"\n处理: {f}")
    if fix_file(fp):
        ok += 1

print(f"\n{'=' * 60}")
print(f"完成: {ok}/{len(files)} 个文件已修复")
print(f"{'=' * 60}")
