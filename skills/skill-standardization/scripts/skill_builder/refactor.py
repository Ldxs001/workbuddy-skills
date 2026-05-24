#!/usr/bin/env python3
"""
SkillRefactor — 负责 refactor 模式（改造非标 Skill）
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from .utils import _create_backup, _write_json, SPLITTABLE_KEYWORDS


class SkillRefactor:
    """Skill 改造器"""

    MIGRATION_RULES = {
        "M-01": "脚本文件（.py/.sh/.bat/.ps1）→ scripts/",
        "M-02": "文档文件（.md > 50行） → references/",
        "M-03": "配置文件（.json/.yaml/.toml） → 根目录保留或 scripts/",
        "M-04": "数据/产出物目录（data/outputs/cache/temp） → 递归收集文件迁移",
        "M-05": "系统目录（__pycache__/node_modules/） → 排除",
        "M-06": "隐藏文件（.gitignore/.env） → 根目录保留",
    }

    def refactor(self, args):
        """对非标 skill 进行整体改造"""
        # 兼容文件路径和目录路径
        input_path = Path(args.skill_dir)
        if input_path.is_file():
            skill_dir = input_path.parent
        else:
            skill_dir = input_path

        if not skill_dir.exists():
            print(f"❌ Skill 目录不存在: {skill_dir}")
            sys.exit(1)

        # 0. 检查是否在 .standardization/ 下，如果不在则先搬迁整个 skill
        skill_dir = self._ensure_standardization_location(skill_dir, args)

        # 1. dry-run 模式：只输出计划，不创建备份
        if args.dry_run:
            self._dry_run(skill_dir)
            return

        # 2. 备份（除非 --no-backup）
        backup_dir = None
        if not args.no_backup:
            backup_dir = _create_backup(skill_dir, "refactor", args.workspace)
            print(f"📦 备份已创建: {backup_dir}")

        # 3. 执行迁移
        migration_plan = self._build_migration_plan(skill_dir)

        print(f"\n=== refactor 执行计划 ===")
        print(f"Source: {skill_dir}")
        if backup_dir:
            print(f"Backup: {backup_dir}")

        # 4. 执行文件移动
        self._execute_migration(skill_dir, migration_plan)

        # 5. 验证总字节一致性
        self._verify_migration(skill_dir, backup_dir, migration_plan)

        # ★ 新增：注入授权要求章节
        if getattr(args, "inject_auth", False):
            report = self._run_permission_checker(skill_dir)
            self._inject_auth_section(skill_dir, report)

        print(f"\n✅ refactor 完成！")
        print(f"   备份位置: {backup_dir}")
        print(f"   迁移文件: {len(migration_plan)} 个")

    def _ensure_standardization_location(self, skill_dir, args):
        """
        检查 skill 是否在 skills/.standardization/<name>/ 下。
        如果不在，提示用户并搬迁整个目录到正确位置。
        """
        skill_dir = Path(skill_dir).resolve()
        parts = skill_dir.parts

        # 检查是否已在 .standardization/<name>/ 下
        for i, part in enumerate(parts):
            if part == ".standardization":
                # 已在正确位置
                return skill_dir

        # 不在 .standardization/ 下，需要搬迁
        # 找到 skills/ 目录
        skills_dir = None
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] == "skills":
                skills_dir = Path(*parts[:i+1])
                break

        if skills_dir is None:
            # 找不到 skills/ 目录，使用默认位置
            skills_dir = skill_dir.parent

        std_dir = skills_dir / ".standardization" / skill_dir.name

        if std_dir.exists():
            print(f"⚠️  目标目录已存在: {std_dir}")
            print(f"   继续使用现有目录: {std_dir}")
            return std_dir

        if not args.dry_run:
            print(f"\n⚠️  检测到 skill 不在 .standardization/ 下！")
            print(f"   当前位置: {skill_dir}")
            print(f"   目标位置: {std_dir}")
            # 执行搬迁
            print(f"   🫆 正在搬迁整个 skill 目录...")
            shutil.move(str(skill_dir), str(std_dir))
            print(f"   ✅ 已搬迁到: {std_dir}")
            return std_dir
        else:
            print(f"\n[i] 计划搬迁整个 skill 到 .standardization/ 下:")
            print(f"   当前: {skill_dir}")
            print(f"   目标: {std_dir}")
            return skill_dir  # dry-run 不实际搬迁

    def _dry_run(self, skill_dir):
        """输出迁移计划但不执行"""
        print(f"=== refactor DRY-RUN plan ===")
        print(f"Source: {skill_dir}")
        print(f"Backup: {skill_dir}_bak_refactor_YYYYMMDD_HHMMSS (将创建）")

        migration_plan = self._build_migration_plan(skill_dir)

        print(f"\nMigration plan ({len(migration_plan)} files):")
        for rule_id, src, dst, size in migration_plan:
            print(f"  {rule_id} {Path(src).name:20s} → {dst:30s} ({size//1024}KB)")

        print(f"\nExcluded:")
        print(f"  __pycache__/        (M-05: always excluded)")
        print(f"\nTotal size: {sum(s for _,_,_,s in migration_plan)//1024}KB")
        print(f"Verification will check ±1% tolerance")

    def _build_migration_plan(self, skill_dir):
        """构建迁移计划 — 处理文件和子目录"""
        plan = []
        excluded_dirs = {"__pycache__", "node_modules", ".git", "venv", ".venv"}
        # 已知标准目录（不迁移整个目录，但会扫描其下文件）
        known_std_dirs = {"scripts", "references", "assets"}

        for item in skill_dir.iterdir():
            if item.name in {"SKILL.md", "_meta.json", "scripts", "references"}:
                continue  # 标准文件/目录，跳过
            if item.name.startswith(".") and item.name != ".gitignore":
                continue  # 隐藏文件，跳过
            if item.is_dir() and item.name in excluded_dirs:
                continue  # 排除目录

            if item.is_file():
                # 判断迁移目标
                ext = item.suffix.lower()
                size = item.stat().st_size

                if ext in (".py", ".sh", ".bat", ".ps1"):
                    dst = skill_dir / "scripts" / item.name
                    rule_id = "M-01"
                elif ext == ".md" and size > 50 * 1024:  # > 50KB
                    dst = skill_dir / "references" / item.name
                    rule_id = "M-02"
                elif ext in (".json", ".yaml", ".toml") and item.name != "_meta.json":
                    dst = skill_dir / "scripts" / item.name
                    rule_id = "M-03"
                else:
                    continue  # 不迁移

                if dst.exists():
                    print(f"⚠️  目标已存在，跳过: {dst}")
                    continue

                plan.append((rule_id, item, dst, size))

            elif item.is_dir():
                # M-04: 处理子目录：递归收集文件，判断是否需要迁移
                for sub_item in item.rglob("*"):
                    if not sub_item.is_file():
                        continue
                    # 跳过已知标准目录里的文件（已在正确位置）
                    if item.name in known_std_dirs:
                        continue
                    # 跳过排除目录里的文件
                    if any(part in excluded_dirs for part in sub_item.parts):
                        continue

                    ext = sub_item.suffix.lower()
                    size = sub_item.stat().st_size

                    # 判断目标位置：保持原目录结构
                    rel_path = sub_item.relative_to(skill_dir)
                    dst = skill_dir / rel_path
                    rule_id = "M-04"  # 数据文件迁移

                    if dst.exists():
                        continue  # 目标已存在，跳过

                    plan.append((rule_id, sub_item, dst, size))

        return plan

    def _execute_migration(self, skill_dir, plan):
        """执行文件迁移"""
        # 确保目标目录存在
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)

        for rule_id, src, dst, size in plan:
            print(f"  {rule_id} {src.name:20s} → {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    def _verify_migration(self, skill_dir, backup_dir, plan):
        """验证迁移前后总字节一致性（±1% 容差）"""
        if not backup_dir:
            return

        # 计算备份总大小
        backup_size = sum(
            f.stat().st_size
            for f in backup_dir.rglob("*") if f.is_file()
        )

        # 计算当前总大小
        current_size = sum(
            f.stat().st_size
            for f in skill_dir.rglob("*") if f.is_file()
        )

        diff = abs(backup_size - current_size)
        tolerance = backup_size * 0.01  # 1% 容差

        if diff > tolerance:
            print(f"⚠️  字节数差异较大: 备份 {backup_size}, 当前 {current_size}, 差异 {diff}")
        else:
            print(f"✅ 字节数验证通过: {current_size} bytes (±1% tol)")

    def _print_migration_rules(self):
        """打印迁移规则"""
        print(f"\n迁移规则:")
        for rule_id, description in self.MIGRATION_RULES.items():
            print(f"  {rule_id}: {description}")

    # ── 授权要求注入（--inject-auth）────────────────────────────────

    def _run_permission_checker(self, skill_dir):
        """运行 permission_checker.py，返回报告字典或 None。"""
        script_dir = Path(__file__).resolve().parent.parent
        checker = script_dir / "permission_checker.py"
        if not checker.exists():
            print("[!] permission_checker.py 不存在，跳过授权检查")
            return None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                out = f.name
            result = subprocess.run(
                [sys.executable, str(checker), str(skill_dir), "--output", out],
                capture_output=True, text=True, timeout=30
            )
            if os.path.exists(out):
                with open(out, "r", encoding="utf-8") as f:
                    report = json.load(f)
                os.unlink(out)
                # 自动写入权限说明到 references/permission.md
                self._write_permission_md(skill_dir, report)
                return report
            return None
        except Exception as e:
            print(f"[!] 运行 permission_checker.py 失败: {e}")
            return None

    def _inject_auth_section(self, skill_dir, report):
        """
        根据权限检查报告，为 SKILL.md 注入「## 授权要求」章节。

        授权方式直接读取 report 中每项的 authorization_method 字段
        （由 permission_checker.py 的 suggest_authorization_methods() 生成，
         已根据技能工作性质（自动化/交互式）智能判断）。
        """
        if not report:
            return
        issues = report.get("issues", [])
        if not issues:
            return

        skill_md = Path(skill_dir) / "SKILL.md"
        if not skill_md.exists():
            return

        content = skill_md.read_text(encoding="utf-8")

        # 已存在则跳过
        if "## 授权要求" in content:
            print("[*] SKILL.md 已包含「授权要求」章节，跳过注入")
            return

        # 按 authorization_method 分组（来自 suggest_authorization_methods() 的智能判断）
        groups = {"immediate": [], "unified": [], "silent": []}
        for iss in issues:
            method = iss.get("authorization_method", "immediate")
            if method not in groups:
                method = "immediate"
            groups[method].append(iss)

        # 生成章节内容
        lines = ["\n\n---\n\n## 授权要求\n"]
        lines.append("本技能包含以下中高风险操作，使用前需获得用户授权：\n")

        idx = 0
        for method in ("immediate", "unified", "silent"):
            for iss in groups[method]:
                idx += 1
                sev_cn = {"HIGH": "高", "ERROR": "高", "MEDIUM": "中"}.get(iss.get("severity", ""), "低")
                desc = iss.get("description", "")
                file = iss.get("file", "")
                line = iss.get("line", 0)
                reason = iss.get("reason", "")
                lines.append(f"{idx}. **[{sev_cn}] {desc}** (`{file}` 第 {line} 行）")
                if method == "immediate":
                    lines.append("   - 授权方式：**即时授权**（每次执行前需获得用户批准）")
                elif method == "unified":
                    lines.append("   - 授权方式：**统一授权**（首次执行前获得用户批准，后续不再询问）")
                else:
                    lines.append("   - 授权方式：**静默授权**（无需用户交互，自动执行并记录）")
                if reason:
                    lines.append(f"   - 原因：{reason}")

        lines.append("**授权方式说明：**")
        lines.append("- 静默授权：无需用户交互，自动执行并记录")
        lines.append("- 统一授权：首次执行前获得用户批准，后续不再询问")
        lines.append("- 即时授权：每次执行前需获得用户批准")
        lines.append("")

        # 注入到文件末尾
        new_content = content.rstrip() + "\n" + "\n".join(lines)
        skill_md.write_text(new_content, encoding="utf-8")
        print(f"[*] 已注入「授权要求」章节（{idx} 项操作）")

    # ── 权限扫描结果自动写入 references/permission.md ─────────────────

    def _write_permission_md(self, skill_dir, report):
        """将权限扫描报告自动写入 references/permission.md"""
        from pathlib import Path
        import json

        skill_dir = Path(skill_dir)
        pm = skill_dir / "references" / "permission.md"
        issues = report.get("issues", [])
        risk_level = report.get("risk_level", "unknown")

        if not issues:
            print("[💡] 权限扫描无风险项，跳过 permission.md 写入")
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
