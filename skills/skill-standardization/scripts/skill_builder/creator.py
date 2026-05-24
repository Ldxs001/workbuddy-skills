#!/usr/bin/env python3
"""
SkillCreator — 负责 create 模式（创建新 Skill）
"""

import json
import sys
import subprocess
import tempfile
import os
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

        # 权限扫描（自动写入 references/permissions.md）
        self._check_permissions(skill_dir)

        return True

    # ── 权限扫描结果自动写入 references/permissions.md ──────────────────

    def _write_permissions_md(self, skill_dir, report):
        """将权限扫描报告自动写入 references/permissions.md"""
        from pathlib import Path
        import json

        skill_dir = Path(skill_dir)
        pm = skill_dir / "references" / "permissions.md"
        issues = report.get("issues", [])
        risk_level = report.get("risk_level", "unknown")

        if not issues:
            print("[💡] 权限扫描无风险项，跳过 permissions.md 写入")
            return

        lines = []
        lines.append("# 权限说明\n")
        lines.append(f"权限扫描风险等级：**{risk_level}**\n")
        lines.append("## 权限总览\n")
        lines.append(f"共 {len(issues)} 项权限风险，按类别分组如下：\n")

        # 按类别分组
        categories = {}
        for iss in issues:
            cat = iss.get("category", "other")
            categories.setdefault(cat, []).append(iss)

        for cat, items in categories.items():
            lines.append(f"### {cat}（{len(items)} 项）\n")
            lines.append("| # | 权限名称 | 风险等级 | 功能解释 | 具体位置 | 授权方式 |")
            lines.append("|---|----------|----------|----------|----------|----------|")
            for i, iss in enumerate(items, 1):
                sev = iss.get("severity", "?")
                sev_cn = {"HIGH": "高", "MEDIUM": "中", "LOW": "低", "ERROR": "高"}.get(sev, sev)
                desc = iss.get("description", "")
                file = iss.get("file", "")
                line = iss.get("line", "")
                method = iss.get("authorization_method", "immediate")
                method_cn = {"immediate": "即时授权", "unified": "统一授权", "silent": "静默授权"}.get(method, method)
                location = f"`{file}` 第 {line} 行" if file else "未知"
                lines.append(f"| {i} | {desc} | {sev_cn} | {desc} | {location} | {method_cn} |")
            lines.append("")

        lines.append("## 授权方式说明\n")
        lines.append("- **即时授权**：每次执行前需获得用户批准")
        lines.append("- **统一授权**：首次执行前获得用户批准，后续不再询问")
        lines.append("- **静默授权**：无需用户交互，自动执行并记录")
        lines.append("")
        lines.append("## 详细风险列表\n")
        for i, iss in enumerate(issues, 1):
            sev = iss.get("severity", "?")
            sev_cn = {"HIGH": "高", "MEDIUM": "中", "LOW": "低", "ERROR": "高"}.get(sev, sev)
            desc = iss.get("description", "")
            file = iss.get("file", "")
            line = iss.get("line", "")
            reason = iss.get("reason", "")
            lines.append(f"{i}. **[{sev_cn}] {desc}**")
            lines.append(f"   - 位置：`{file}` 第 {line} 行")
            if reason:
                lines.append(f"   - 原因：{reason}")
            lines.append("")

        pm.parent.mkdir(parents=True, exist_ok=True)
        pm.write_text("\n".join(lines), encoding="utf-8")
        print(f"[✅] 权限扫描结果已自动写入 {pm}")

    def _get_category_description(self, category):
        """返回权限类别的中文描述"""
        descs = {
            "file_write": "写入文件（可能覆盖或破坏现有文件）",
            "file_read": "读取文件（可能访问敏感信息）",
            "network": "网络通信（可能传输数据到外部）",
            "subprocess": "执行外部命令（可能执行恶意代码）",
            "env_var": "读取环境变量（可能泄露系统信息）",
            "user_interaction": "用户交互（需要用户授权）",
            "other": "其他权限",
        }
        return descs.get(category, "未知权限类别")

    def _get_item_explanation(self, item):
        """返回权限项的详细解释"""
        return item.get("description", "无详细描述")

    def _get_auth_method(self, method):
        """返回授权方式的中文说明"""
        methods = {
            "immediate": "即时授权（每次执行前需获得用户批准）",
            "unified": "统一授权（首次执行前获得用户批准，后续不再询问）",
            "silent": "静默授权（无需用户交互，自动执行并记录）",
        }
        return methods.get(method, "未知授权方式")

