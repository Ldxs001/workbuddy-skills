#!/usr/bin/env python3
"""
SkillRefactor — 负责 refactor 模式（改造非标 Skill）
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from .utils import _create_backup, _write_json, SPLITTABLE_KEYWORDS


class SkillRefactor:
    """Skill 改造器"""

    MIGRATION_RULES = {
        "M-01": "脚本文件（.py/.sh/.bat/.ps1）→ scripts/",
        "M-02": "文档文件（.md > 50行） → references/",
        "M-03": "配置文件（.json/.yaml/.toml） → 根目录保留或 scripts/",
        "M-04": "数据文件（.csv/.json 数据） → 外部数据目录",
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
            print(f"  {rule_id} {Path(src).name:20s} → {dst:30s} ({size//1024}KB)")

        print(f"\nExcluded:")
        print(f"  __pycache__/        (M-05: always excluded)")
        print(f"\nTotal size: {sum(s for _,_,_,s in migration_plan)//1024}KB")
        print(f"Verification will check ±1% tolerance")

    def _build_migration_plan(self, skill_dir):
        """构建迁移计划"""
        plan = []
        excluded_dirs = {"__pycache__", "node_modules", ".git", "venv", ".venv"}

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

        return plan

    def _execute_migration(self, skill_dir, plan):
        """执行文件迁移"""
        # 确保目标目录存在
        (skill_dir / "scripts").mkdir(exist_ok=True)
        (skill_dir / "references").mkdir(exist_ok=True)

        for rule_id, src, dst, size in plan:
            print(f"  {rule_id} {src.name:20s} → {dst}")
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
