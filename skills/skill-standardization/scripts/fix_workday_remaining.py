#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_workday_remaining.py — 最终修复 R-20/R-23"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from safe_io import safe_write

# 动态计算路径（通用写法）
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR   = os.path.dirname(_SCRIPT_DIR)   # scripts/ → skill-root
_SKILLS_ROOT = os.path.dirname(_SKILL_DIR)
SKILL_NAME    = os.path.basename(_SKILL_DIR)
DATA_DIR       = os.path.join(_SKILLS_ROOT, ".standardization", SKILL_NAME)

# 目标技能（workday-calendar）的数据目录
TARGET_SKILL = "workday-calendar"
TARGET_DIR    = os.path.join(_SKILLS_ROOT, TARGET_SKILL)
SKILL_MD       = os.path.join(TARGET_DIR, "SKILL.md")
FAQ_MD        = os.path.join(TARGET_DIR, "references", "faq.md")


def fix_r20_terminology(content):
    """R-20: 统一术语 — 设置(动词) → 配置"""
    replacements = [
        ("用户可以设置", "用户可以配置"),
        ("请设置", "请配置"),
        ("可设置", "可配置"),
        ("已设置", "已配置"),
    ]
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f"  [R-20] {old} → {new}")
    if not modified:
        print("  [R-20] 未发现需要替换的术语")
    return content


def fix_r23_param_format(content):
    """R-23: 修正示例命令参数格式（空格 → 等号）"""
    lines = content.split("\n")
    modified = False
    for i, line in enumerate(lines):
        orig = line
        line = re.sub(r'(`?--title)\s+(\S+)', r'\1=\2', line)
        line = re.sub(r'(`?--status)\s+(\S+)', r'\1=\2', line)
        line = re.sub(r'(`?--start)\s+(\S+)', r'\1=\2', line)
        line = re.sub(r'(`?--end)\s+(\S+)', r'\1=\2', line)
        line = re.sub(r'(`?--date)\s+(\S+)', r'\1=\2', line)
        line = re.sub(r'(`?--desc)\s+(\S+)', r'\1=\2', line)
        line = re.sub(r'(`?--category)\s+(\S+)', r'\1=\2', line)
        if line != orig:
            lines[i] = line
            modified = True

    if modified:
        print("  [R-23] 修正示例命令参数格式（空格 → =）")
        return "\n".join(lines)
    else:
        print("  [R-23] 示例命令格式已正确")
        return content


def fix_faq_terminology(content):
    """R-20: 统一 faq.md 中的术语"""
    replacements = [
        ("用户可以设置", "用户可以配置"),
        ("请设置", "请配置"),
    ]
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f"  [R-20] faq.md: {old} → {new}")
    return content, modified


def main():
    print("=" * 60)
    print("最终修复 workday-calendar (R-20/R-23)")
    print("=" * 60)

    if not os.path.isfile(SKILL_MD):
        print(f"  ❌ 找不到目标文件：{SKILL_MD}")
        sys.exit(1)

    # 修复 SKILL.md
    print("\n[修复] SKILL.md...")
    with open(SKILL_MD, "r", encoding="utf-8") as f:
        content = f.read()

    content = fix_r20_terminology(content)
    content = fix_r23_param_format(content)

    safe_write(SKILL_MD, content)
    print("  ✅ SKILL.md 已写入")

    # 修复 faq.md
    print("\n[修复] references/faq.md...")
    if os.path.isfile(FAQ_MD):
        with open(FAQ_MD, "r", encoding="utf-8") as f:
            faq_content = f.read()

        faq_content, modified = fix_faq_terminology(faq_content)
        if modified:
            safe_write(FAQ_MD, faq_content)
            print("  ✅ faq.md 已写入")
        else:
            print("  ⏭️  faq.md 无需修改")
    else:
        print("  ⚠️  faq.md 不存在，跳过")

    print("\n完成。请重新运行审计验证。")


if __name__ == "__main__":
    main()
