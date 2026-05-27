#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_workday_remaining.py — 最终修复 R-20/R-23"""

import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from safe_io import safe_write

SKILL_MD = "C:/Users/sm001/.workbuddy/skills/workday-calendar/SKILL.md"
FAQ_MD = "C:/Users/sm001/.workbuddy/skills/workday-calendar/references/faq.md"


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
    # 脚本用 startswith("--title=") 解析，示例必须用 --title=xxx 格式
    # 先找到所有 CLI 示例行，修正参数格式
    lines = content.split("\n")
    modified = False
    for i, line in enumerate(lines):
        orig = line
        # 修正 --title xxx → --title=xxx
        line = re.sub(r'(`?--title)\s+(\S+)', r'\1=\2', line)
        # 修正 --status xxx → --status=xxx
        line = re.sub(r'(`?--status)\s+(\S+)', r'\1=\2', line)
        # 修正 --start xxx → --start=xxx（脚本用 --start=）
        line = re.sub(r'(`?--start)\s+(\S+)', r'\1=\2', line)
        # 修正 --end xxx → --end=xxx
        line = re.sub(r'(`?--end)\s+(\S+)', r'\1=\2', line)
        # 修正 --date xxx → --date=xxx
        line = re.sub(r'(`?--date)\s+(\S+)', r'\1=\2', line)
        # 修正 --desc xxx → --desc=xxx
        line = re.sub(r'(`?--desc)\s+(\S+)', r'\1=\2', line)
        # 修正 --category xxx → --category=xxx
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
    with open(FAQ_MD, "r", encoding="utf-8") as f:
        faq_content = f.read()

    faq_content, modified = fix_faq_terminology(faq_content)
    if modified:
        safe_write(FAQ_MD, faq_content)
        print("  ✅ faq.md 已写入")
    else:
        print("  ⏭️  faq.md 无需修改")

    print("\n完成。请重新运行审计验证。")


if __name__ == "__main__":
    main()
