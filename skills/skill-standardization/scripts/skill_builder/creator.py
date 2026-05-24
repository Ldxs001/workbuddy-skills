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

---

## 渐进式加载引用表

| 状态 | 内容 | 引用 |
|------|------|------|
| ✅ 核心触发 | 触发场景 + 核心能力 + 快速开始 + 主要流程 | 本文件（SKILL.md） |
| ✅ 版本记录 | 版本更新历史 | 📄 `references/changelog.md` |
| ✅ 详细指南 | 规则详解、FAQ、注意事项 | 📄 `references/guide.md` |
| ✅ 权限说明 | 权限类型、风险等级、行为对照表 | 📄 `references/permissions.md` |

→ 详见 `references/guide.md`（按需加载）

---

## 注意事项

→ 详见 `references/guide.md`（按需加载）
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

        # 自动创建三个必须文件（渐进式加载）
        refs = skill_dir / "references"
        (refs / "changelog.md").write_text(
            f"# {name} — 版本更新日志\n\n"
            f"> 本文档记录 {name} 的版本更新历史，按需加载。\n\n"
            f"## v0.1.0 (创建)\n\n"
            f"- 初始版本\n",
            encoding="utf-8"
        )
        (refs / "guide.md").write_text(
            f"# {name} — 详细指南\n\n"
            f"> 本文档提供 {name} 的详细使用指南、规则详解和注意事项，按需加载。\n\n"
            f"<!-- TODO: 填写详细指南内容 -->\n",
            encoding="utf-8"
        )
        # permissions.md 复用 skill-standardization 的模板（如存在）
        src_perm = Path(__file__).parent.parent / "references" / "permissions.md"
        if src_perm.exists():
            import shutil
            shutil.copy(str(src_perm), str(refs / "permissions.md"))
        else:
            (refs / "permissions.md").write_text(
                f"# {name} — 权限说明\n\n"
                f"> 本文档说明 {name} 的权限需求和风险等级，按需加载。\n\n"
                f"<!-- TODO: 按需填写权限说明 -->\n",
                encoding="utf-8"
            )

        print(f"✅ Skill 已创建: {skill_dir}")
        print(f"   ├── SKILL.md         (主文件，≤230行)")
        print(f"   ├── _meta.json       (元数据)")
        print(f"   ├── references/")
        print(f"   │   ├── changelog.md   (✅ 必须：版本记录)")
        print(f"   │   ├── guide.md       (✅ 必须：详细指南)")
        print(f"   │   └── permissions.md (✅ 必须：权限说明)")
        print(f"   └── scripts/         (脚本目录)")
        # === 创建后流程（由 AI 在填充内容后执行）===
        # 步骤：填充内容 → 权限扫描 → 写权限声明 → 审计循环 ≥95%
        print(f"\n📋 创建后规范流程（填充内容后执行）:")
        print(f"   ① 填充 SKILL.md / references/ 内容")
        print(f"   ② 运行权限扫描: python {Path(__file__).parent.parent}/permission_checker.py {skill_dir}")
        print(f"   ③ 根据扫描结果更新 references/permissions.md 和 SKILL.md frontmatter")
        print(f"   ④ 运行审计循环直到通过率 ≥95%: python -m skills.skill_audit {skill_dir}")
        print(f"   ⑤ 更新 references/changelog.md")

        print(f"\n下一步（按规范执行）:")
        print(f"   1. 填充 SKILL.md 内容（保持 ≤230 行，必须有渐进式加载引用表）")
        print(f"   2. 填充 references/guide.md（详细指南）")
        print(f"   3. 确认/修改 references/permissions.md（权限说明）")
        print(f"   4. 运行审计: python -m skills.skill_audit {skill_dir}")
        print(f"   5. 如通过率 <95%，修正后回到步骤4，直到 ≥95%")
        print(f"   6. 确认 references/permissions.md 与扫描结果一致")
        print(f"   7. 更新 changelog.md 记录版本")

        return True

    def _check_permissions(self, skill_dir):
        """调用 permission_checker.py 进行权限扫描（供 AI 在填充内容后调用）"""
        import subprocess, json
        from pathlib import Path
        checker = Path(__file__).parent.parent / "permission_checker.py"
        if not checker.exists():
            print(f"[⚠️] permission_checker.py 不存在，跳过权限扫描")
            return
        try:
            proc = subprocess.run(
                ["python", str(checker), str(skill_dir)],
                capture_output=True, text=True, timeout=30
            )
            output = proc.stdout.strip()
            if not output:
                print(f"[💡] 权限扫描无输出（可能 SKILL.md 无实质内容）")
                return
            report = json.loads(output)
            issues = report.get("issues", [])
            if issues:
                print(f"\n[🔍] 权限扫描发现 {len(issues)} 项风险（{report.get('risk_level','unknown')}）：")
                for iss in issues[:10]:
                    print(f"   [{iss.get('severity','?')}] {iss.get('file','?')}:{iss.get('line','?')} — {iss.get('description','')}")
                if len(issues) > 10:
                    print(f"   ...还有 {len(issues)-10} 项，详见 JSON 报告")
            else:
                print(f"\n[✅] 权限扫描通过（{report.get('risk_level','low')}）")
        except Exception as e:
            print(f"[⚠️] 权限扫描失败: {e}")

    def _check_skill_audit(self, skill_dir):
        """调用 skill_audit 进行 R-01~R-17 规则审查（供 AI 在填充内容后调用）"""
        import sys, json
        from pathlib import Path
        audit_pkg = Path(__file__).parent.parent / "skill_audit"
        if not audit_pkg.exists():
            print(f"[⚠️] skill_audit 目录不存在，跳过 R-01~R-17 审查")
            return
        sys.path.insert(0, str(audit_pkg.parent))
        try:
            from skill_audit import audit_skill
            report = audit_skill(str(skill_dir), manifest_version=None)
        except Exception as e:
            print(f"[⚠️] skill_audit 导入/执行失败: {e}")
            return
        verdict = report.get("verdict", "UNKNOWN")
        summary = report.get("summary", {})
        print(f"\n[📊] R-01~R-17 审查结果: {verdict}")
        print(f"   总计: {summary.get('total',0)}, 通过: {summary.get('pass',0)}, 失败: {summary.get('fail',0)}, 警告: {summary.get('warns',0)}")
        if verdict == "PASS":
            print(f"[✅] 审查通过（通过率 ≥95%）")
        else:
            print(f"[⚠️] 审查未通过，以下为失败项：")
            for res in report.get("results", []):
                if not res.get("passed", False) and not res.get("skipped", False):
                    print(f"   [{res.get('rule_id','?')}] {res.get('detail','')}")
        return report
