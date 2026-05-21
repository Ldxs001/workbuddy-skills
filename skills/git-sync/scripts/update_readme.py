#!/usr/bin/env python3
"""
update_readme.py - 安全地更新 README.md 中的技能列表和目录结构
避免 heredoc 中变量展开导致重复写入的问题

用法: python update_readme.py <readme_path> <skill_name> <skill_desc>
"""
import re
import sys
import os

def update_readme(readme_path, skill_name, skill_desc):
    with open(readme_path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")

    modified = False

    # --- 1. 更新技能列表表格 ---
    # 在 |------|------| 分隔行后插入新行（如果不存在）
    table_entry = f"| `{skill_name}` | {skill_desc} |"

    if table_entry in "\n".join(lines):
        print(f"  ℹ️  表格中已存在 `{skill_name}`，跳过表格插入")
    else:
        # 找到表格分隔行 |------|------| 的行号
        sep_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            # 匹配表格分隔行：以 | 开头，主要内容是 - 和 |
            if re.match(r"^\|[\s\-:|]+\|$", stripped) and "---" in stripped:
                sep_idx = i
                break

        if sep_idx >= 0:
            # 在分隔行后插入新行
            lines.insert(sep_idx + 1, table_entry)
            modified = True
            print(f"  ✅ 已添加到技能列表表格")
        else:
            print(f"  ⚠️  未找到表格分隔行，跳过表格更新")

    # --- 2. 更新目录结构树 ---
    content_now = "\n".join(lines)
    tree_branch = f"│   ├── {skill_name}/"
    tree_last = f"│   └── {skill_name}/"

    if tree_branch in content_now or tree_last in content_now:
        print(f"  ℹ️  目录树中已存在 `{skill_name}`，跳过")
    else:
        # 找到 skills/ 块中最后一个条目
        last_entry_idx = -1
        in_skills_block = False

        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if "├── skills/" in stripped or "└── skills/" in stripped:
                in_skills_block = True
            if in_skills_block:
                if re.match(r"│   ├── .+/$", stripped) or re.match(r"│   └── .+/$", stripped):
                    last_entry_idx = i

        if last_entry_idx >= 0:
            last_line = lines[last_entry_idx]
            if "└──" in last_line:
                # 最后一条是 └──，改成 ├──，然后追加新的 └──
                lines[last_entry_idx] = last_line.replace("└──", "├──", 1)
                lines.insert(last_entry_idx + 1, "│   └── " + skill_name + "/")
            else:
                # 最后一条是 ├──，直接追加 └──
                lines.insert(last_entry_idx + 1, "│   └── " + skill_name + "/")
            modified = True
            print(f"  ✅ 已更新目录结构")
        else:
            print(f"  ⚠️  未找到skills目录树，请手动添加")

    # 写回文件
    if modified:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  ✅ README.md 已更新")
    else:
        print(f"  ℹ️  README.md 无需修改")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python update_readme.py <readme_path> <skill_name> <skill_desc>")
        sys.exit(1)

    readme_path = sys.argv[1]
    skill_name = sys.argv[2]
    skill_desc = sys.argv[3]

    if not os.path.exists(readme_path):
        print(f"  ⚠️  README.md 不存在: {readme_path}")
        sys.exit(0)

    update_readme(readme_path, skill_name, skill_desc)
