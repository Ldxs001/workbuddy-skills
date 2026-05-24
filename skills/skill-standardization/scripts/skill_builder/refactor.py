"""
refactor.py — 对非标 skill 进行整体改造（标准化）

正确逻辑：
- 技能安装目录：skills/<skill-name>/（不搬迁）
- 数据/产出物路径：应指向 skills/.standardization/<skill-name>/
- refactor 只整理技能内部文件结构，不搬迁整个目录
"""

import sys
import os
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


class Refactor:
    def __init__(self, console=None):
        self.console = console

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

        # 1. dry-run 模式：只输出计划，不创建备份
        if args.dry_run:
            self._dry_run(skill_dir)
            return

        # 2. 备份（除非 --no-backup）
        backup_dir = None
        if not args.no_backup:
            backup_dir = _create_backup(skill_dir, "refactor", args.workspace)
            print(f"📦 备份已创建: {backup_dir}")

        # 3. 执行迁移（整理技能内部文件结构）
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
            report = self._run_permissionchecker(skill_dir)
            self._inject_auth_section(skill_dir, report)

        print(f"\n✅ refactor 完成！")
        print(f"   备份位置: {backup_dir}")
        print(f"   迁移文件: {len(migration_plan)} 个")

    def _dry_run(self, skill_dir):
        """输出迁移计划但不执行"""
        print(f"=== refactor DRY-RUN plan ===")
        print(f"Source: {skill_dir}")
        print(f"Backup: {skill_dir}_bak_refactor_YYYYMMDD_HHMMSS (将创建）")

        migration_plan = self._build_migration_plan(skill_dir)

        print(f"\nMigration plan ({len(migration_plan)} files):")
        for rule_id, src, dst, size in migration_plan:
            print(f"  {rule_id} {Path(src).name:20s} → {dst:30s} ({size // 1024}KB)")

        print(f"\nExcluded:")
        print(f"  __pycache__/        (M-05: always excluded)")
        print(f"\nTotal size: {sum(s for _, _, _, s in migration_plan) // 1024}KB")
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
                # 处理子目录：递归收集文件，判断是否需要迁移
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
        """执行迁移计划"""
        # 确保目标目录存在
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)

        for rule_id, src, dst, size in plan:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.move(str(src), str(dst))
                print(f"  {rule_id} {Path(src).name} → {dst}")

    def _verify_migration(self, skill_dir, backup_dir, plan):
        """验证迁移前后总字节一致"""
        if not backup_dir:
            return
        orig_size = sum(p.stat().st_size for p in backup_dir.rglob("*") if p.is_file())
        new_size = sum(p.stat().st_size for p in skill_dir.rglob("*") if p.is_file())
        diff = abs(orig_size - new_size)
        if diff > orig_size * 0.01:  # >1% 差异
            print(f"⚠️  警告：迁移前后大小差异 {diff} bytes ({diff / orig_size:.1%})")
        else:
            print(f"✅ 验证通过：大小差异 <1% ({diff} bytes)")

    def _run_permission_checker(self, skill_dir):
        """运行 permission_checker.py 扫描权限"""
        checker = Path(__file__).parent.parent / "scripts" / "permission_checker.py"
        if not checker.exists():
            print(f"[!] permission_checker.py 不存在: {checker}")
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
            print(f"[!] 运行 permissionchecker.py 失败: {e}")
            return None

    def _write_permission_md(self, skill_dir, report):
        """将权限扫描报告写入 references/permission.md"""
        if not report:
            return
        issues = report.get("issues", [])
        if not issues:
            return

        refs_dir = skill_dir / "references"
        refs_dir.mkdir(exist_ok=True)
        perm_file = refs_dir / "permission.md"

        lines = ["# 权限说明\n", "\n", "> 由 permissionchecker.py 自动扫描生成，请勿手动编辑。\n", "\n"]
        lines.append("| 文件 | 行号 | 操作 | 风险 | 建议授权 |\n")
        lines.append("|------|------|------|------|------------|\n")
        for iss in issues:
            lines.append(f"| {iss.get('file', '')} | {iss.get('line', '')} | {iss.get('operation', '')} | {iss.get('risk', '')} | {iss.get('suggested_auth', '')} |\n")
        perm_file.write_text("".join(lines), encoding="utf-8")
        print(f"[*] 已生成权限说明: {perm_file}")

    def _inject_auth_section(self, skill_dir, report):
        """
        根据权限检查报告，为 SKILL.md 注入「## 授权要求」章节。

        授权方式直接读取 report 中每项的 authorization_method 字段
        （由 permissionchecker.py 的 suggest_authorization_methods() 生成，
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
                groups[method] = []
            groups[method].append(iss)

        # 构建章节内容
        auth_section = ["\n", "\n", "## 授权要求\n", "\n"]
        for method, items in groups.items():
            if not items:
                continue
            if method == "immediate":
                auth_section.append("### 立即授权（操作前询问）\n")
            elif method == "unified":
                auth_section.append("### 统一授权（首次确认，后续信任）\n")
            elif method == "silent":
                auth_section.append("### 静默授权（无需询问）\n")
            for iss in items:
                auth_section.append(f"- `{iss.get('file', '')}:{iss.get('line', '')}` — {iss.get('operation', '')} → **{iss.get('suggested_auth', '')}**\n")
            auth_section.append("\n")

        # 注入到 SKILL.md 末尾
        skill_md.write_text(content + "".join(auth_section), encoding="utf-8")
        print(f"[*] 已注入「授权要求」章节（{sum(len(v) for v in groups.values())} 项操作）")


def _create_backup(skill_dir, operation, workspace):
    """创建备份目录"""
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = skill_dir.parent / f"{skill_dir.name}_bak_{operation}_{ts}"
    shutil.copytree(skill_dir, backup_dir)
    return backup_dir
