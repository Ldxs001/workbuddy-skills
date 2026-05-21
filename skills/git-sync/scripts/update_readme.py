#!/usr/bin/env python3
"""
update_readme.py - 全量重新生成 README.md（从仓库实际文件）

不再手动维护 README.md，而是从 WORK_REPO/skills/ 实际目录扫描，
全量生成技能列表表格和目录结构，确保 README = 仓库实际内容。

用法: python update_readme.py <repo_name> <readme_path>
示例: python update_readme.py workbuddy-skills /path/to/README.md
"""

import json
import os
import re
import sys
from datetime import date


def extract_desc(skill_dir):
    """从 _meta.json 或 SKILL.md 提取描述"""
    # 优先 _meta.json
    meta_path = os.path.join(skill_dir, "_meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                desc = d.get("description", "")
                if desc:
                    return desc.strip()
        except Exception:
            pass

    # 降级：从 SKILL.md YAML frontmatter 提取
    skill_path = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(skill_path):
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if m:
                fm = m.group(1)
                for line in fm.split("\n"):
                    if line.strip().startswith("description:"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass

    return "技能描述"


def generate_readme(repo_path, readme_path):
    """全量生成 README.md"""
    skills_dir = os.path.join(repo_path, "skills")
    today = date.today().isoformat()

    if not os.path.isdir(skills_dir):
        print(f"❌ skills/ 目录不存在: {skills_dir}")
        sys.exit(1)

    # 扫描实际技能目录
    actual_skills = []
    for entry in sorted(os.listdir(skills_dir)):
        full = os.path.join(skills_dir, entry)
        if os.path.isdir(full):
            desc = extract_desc(full)
            actual_skills.append((entry, desc))

    print(f"扫描到 {len(actual_skills)} 个技能目录:")
    for name, desc in actual_skills:
        print(f"  - {name}: {desc[:60]}")

    # 生成技能列表表格
    table_lines = []
    for name, desc in actual_skills:
        table_lines.append(f"| `{name}` | {desc} |")
    table = "\n".join(table_lines)

    # 生成目录树
    tree_lines = []
    if len(actual_skills) == 1:
        tree_lines = [f"└── {actual_skills[0][0]}/"]
    elif len(actual_skills) > 1:
        tree_lines = [f"├── {name}/" for name, _ in actual_skills[:-1]]
        tree_lines.append(f"└── {actual_skills[-1][0]}/")
    tree = "\n".join(tree_lines)

    # 读取原 README.md，替换技能列表和目录结构区域
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""

    # 构建新的 README.md
    new_readme = f"""# WorkBuddy Skills Repository

> **用户技能仓库** — 由 git-sync 自动同步维护。
> 最后更新：{today}

本仓库存放 WorkBuddy 用户技能，支持码云（Gitee）和 GitHub 双平台同步。

---

## 技能列表

以下为仓库中实际存在的技能（由 `manifest.py sync-readme` 全量生成，请勿手动修改此表格）：

| 技能名 | 描述 |
|--------|------|
{table}

---

## 目录结构

```
workbuddy-skills/
├── README.md
├── LICENSE
└── skills/
{tree}
```

---

## 如何使用

### 方式一：从工蜂（Gitee）安装
```bash
cd ~/.workbuddy/skills
git clone https://gitee.com/wUwproject/workbuddy-skills.git temp-skills
cp -r temp-skills/skills/* .
rm -rf temp-skills
```

### 方式二：从 GitHub 安装
```bash
cd ~/.workbuddy/skills/
git clone https://github.com/Ldxs001/workbuddy-skills.git temp-skills
cp -r temp-skills/skills/* .
rm -rf temp-skills
```

### 方式三：ZIP 包安装
从 Releases 下载对应技能的 ZIP 包，解压到 `~/.workbuddy/skills/` 目录。

---

## 维护说明

- 本仓库由 **git-sync** 技能自动维护
- README.md 由 `manifest.py sync-readme` **从仓库实际文件全量生成**，不手动编辑
- 维护清单：`git-sync/manifest.json`（记录计划管理的技能全集）
- 三单一致原则：**清单 ⊇ 仓库 = README.md**（清单是计划全集，仓库是实际上传的子集，README.md 由仓库自动生成）

---

## 许可证

MIT License
"""

    # 写回文件
    backup_path = readme_path + ".bak"
    if os.path.exists(readme_path):
        import shutil
        shutil.copy2(readme_path, backup_path)
        print(f"  ℹ️  已备份原 README.md → README.md.bak")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_readme)
    print(f"  ✅ README.md 已全量重新生成: {readme_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python update_readme.py <repo_name> <readme_path>")
        print("示例: python update_readme.py workbuddy-skills /path/to/README.md")
        sys.exit(1)

    repo_name = sys.argv[1]
    readme_path = sys.argv[2]

    # 从 manifest.json 获取仓库路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(script_dir, "..", "manifest.json")
    manifest_path = os.path.normpath(manifest_path)

    if not os.path.exists(manifest_path):
        print(f"❌ manifest.json 不存在: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    repos = data.get("repos", {})
    if repo_name not in repos:
        print(f"❌ 仓库 '{repo_name}' 不存在于 manifest.json")
        sys.exit(1)

    repo_path = os.path.expanduser(repos[repo_name].get("path", ""))
    if not repo_path or not os.path.isdir(repo_path):
        print(f"❌ 仓库路径不存在: {repo_path}")
        sys.exit(1)

    generate_readme(repo_path, readme_path)
