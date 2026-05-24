#!/usr/bin/env python3
"""
SkillCreator — 负责 create 模式（创建新 Skill）
"""

import json
from pathlib import Path


class SkillCreator:
    """Skill 创建器"""

    SKILL_TEMPLATE = """---
name: {name}
version: 0.1.0
author: your-name-here
license: MIT
description: >
  {description}
tags: [{tags}]
---

# {name} — {title}

{description}

## 触发场景

当用户提到以下意图时触发本技能：
- <!-- TODO: 填写触发条件 -->

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | <!-- TODO --> | <!-- TODO --> |

## 快速开始

```bash
# 最简用法示例
```

## 主要流程

<!-- 在此描述主要工作流程 -->

→ 详见 `references/guide.md` 完整教程（按需创建）
"""

    META_TEMPLATE = '{{"name": "{name}", "version": "0.1.0", "description": "{description}", "author": "your-name-here", "tags": [{tags_json}], "data_dir": "skills/.standardization/{name}/data/"}}'

    def create(self, args):
        """创建新的标准 skill 目录结构"""
        name = args.name
        description = args.desc or f"{name} skill"
        tags = args.tags or []
        base_dir = Path(args.dir) if args.dir else Path.cwd()

        skill_dir = base_dir / name

        # 检查是否已存在
        if skill_dir.exists():
            print(f"❌ 目录已存在: {skill_dir}")
            return False

        # 创建目录结构
        skill_dir.mkdir(parents=True)
        (skill_dir / "references").mkdir(exist_ok=True)
        (skill_dir / "scripts").mkdir(exist_ok=True)

        # 写入 SKILL.md
        tags_str = ", ".join(f'"{t}"' for t in tags) if tags else '"todo"'
        tags_simple = ", ".join(tags) if tags else "todo"

        skill_content = self.SKILL_TEMPLATE.format(
            name=name,
            title=name.replace("-", " ").replace("_", " ").title(),
            description=description,
            tags=tags_simple,
        )
        (skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

        # 写入 _meta.json
        meta_content = self.META_TEMPLATE.format(
            name=name,
            description=description,
            tags_json=tags_str,
        )
        (skill_dir / "_meta.json").write_text(meta_content, encoding="utf-8")

        # 创建 .gitkeep 保持空目录
        (skill_dir / "references" / ".gitkeep").write_text("", encoding="utf-8")
        (skill_dir / "scripts" / ".gitkeep").write_text("", encoding="utf-8")

        print(f"✅ Skill 已创建: {skill_dir}")
        print(f"   ├── SKILL.md      (主文件)")
        print(f"   ├── _meta.json    (元数据)")
        print(f"   ├── references/         (渐进式 MD)")
        print(f"   └── scripts/      (脚本目录)")
        print(f"\n下一步:")
        print(f"   1. 编辑 SKILL.md 填写 TODO 占位符")
        print(f"   2. 如需脚本，放入 scripts/")
        print(f"   3. 如需辅助文档，放入 references/")

        return True
