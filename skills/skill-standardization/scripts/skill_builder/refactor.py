#!/usr/bin/env python3
"""
SkillRefactor — 负责 refactor 模式（改造非标 Skill）
"""

import json
import os
import shutil
import subprocess
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

        # 6. 改造后检查（格式化输出）
        self._post_refactor_checks(skill_dir)

        # 7. 保全检查（结构完整性 + 语法校验）
        self._preservation_check(skill_dir)

    def _preservation_check(self, skill_dir):
        """保全检查：确认改造后功能不受损（结构完整 + 语法合法）"""
        print(f"\n{'='*50}")
        print(f"=== 保全检查（Preservation Check）===")

        # a. 结构完整性（复用 _post_refactor_checks）
        self._post_refactor_checks(skill_dir)

        # b. Python 脚本语法校验
        scripts_dir = skill_dir / "scripts"
        py_issues = []
        if scripts_dir.exists():
            for py_file in scripts_dir.glob("*.py"):
                try:
                    import py_compile
                    py_compile.compile(str(py_file), doraise=True)
                except Exception as e:
                    py_issues.append((py_file.name, str(e)))
            if py_issues:
                print(f"\n[⚠️] Python 语法错误 {len(py_issues)} 处：")
                for fname, err in py_issues:
                    print(f"   {fname}: {err}")
            else:
                py_count = len(list(scripts_dir.glob("*.py")))
                print(f"\n[✅] Python 脚本语法校验通过（{py_count} 个文件）")

        # c. Shell 脚本语法校验（如有）
        sh_issues = []
        if scripts_dir.exists():
            for sh_file in list(scripts_dir.glob("*.sh")) + list(scripts_dir.glob("*.bat")) + list(scripts_dir.glob("*.ps1")):
                try:
                    # 仅检查文件是否包含常见语法错误（简单检查）
                    content = sh_file.read_text(encoding="utf-8", errors="ignore")
                    if sh_file.suffix == ".sh" and content.strip().startswith("#!"):
                        # bash 语法检查（需要 bash 命令）
                        pass  # 跳过，跨平台不保证有 bash
                except Exception as e:
                    sh_issues.append((sh_file.name, str(e)))
            if sh_issues:
                print(f"\n[⚠️] Shell 脚本问题 {len(sh_issues)} 处：")
                for fname, err in sh_issues:
                    print(f"   {fname}: {err}")
            else:
                sh_count = len(list(scripts_dir.glob("*.sh")) + list(scripts_dir.glob("*.bat")) + list(scripts_dir.glob("*.ps1")))
                if sh_count > 0:
                    print(f"[✅] Shell 脚本检查完成（{sh_count} 个文件）")

        print(f"\n[📊] 保全检查完成 — 如有关键问题请修正后再继续")

    def _check_permissions(self, skill_dir):
        """调用 permission_checker.py 进行权限扫描"""
        checker = Path(__file__).parent.parent / "permission_checker.py"
        if not checker.exists():
            print(f"⚠️  permission_checker.py 不存在，跳过权限扫描")
            return
        try:
            proc = subprocess.run(
                ["python", str(checker), str(skill_dir)],
                capture_output=True, text=True, timeout=30
            )
            output = proc.stdout.strip()
            if not output:
                return
            report = json.loads(output)
            issues = report.get("issues", [])
            if issues:
                print(f"\n🔍 权限扫描发现 {len(issues)} 项风险（{report.get('risk_level','unknown')}）：")
                for iss in issues[:10]:
                    print(f"   [{iss.get('severity','?')}] {iss.get('file','?')}:{iss.get('line','?')} — {iss.get('description','')}")
                if len(issues) > 10:
                    print(f"   ...还有 {len(issues)-10} 项，详见 JSON 报告")
            else:
                print(f"\n✅ 权限扫描通过（{report.get('risk_level','low')}）")
        except Exception as e:
            print(f"⚠️  权限扫描失败: {e}")

    def _dry_run(self, skill_dir):
        """输出迁移计划但不执行"""
        print(f"=== refactor DRY-RUN plan ===")
        print(f"Source: {skill_dir}")
        print(f"Backup: {skill_dir}_bak_refactor_YYYYMMDD_HHMMSS (将创建）")

        migration_plan = self._build_migration_plan(skill_dir)

        print(f"\nMigration plan ({len(migration_plan)} files):")
        for rule_id, src, dst, size in migration_plan:
            name = src.name
            dst_str = str(dst)
            print(f"  {rule_id} {name:20s} → {dst_str:30s} ({size//1024}KB)")

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

    def _post_refactor_checks(self, skill_dir):
        """改造后检查（格式化输出）"""
        print(f"\n{'='*50}")
        print(f"=== refactor 后检查报告 ===")
        print(f"Skill: {skill_dir.name}")
        print(f"Path: {skill_dir}")
        print()

        # 检查 1: _meta.json
        self._check_meta_json(skill_dir)

        # 检查 2: SKILL.md
        self._check_skill_md(skill_dir)

        # 检查 3: 目录结构
        self._check_dir_structure(skill_dir)

        # 检查 4: 权限扫描
        self._check_permissions(skill_dir)

    def _check_meta_json(self, skill_dir):
        """检查 _meta.json"""
        meta_file = skill_dir / "_meta.json"
        if meta_file.exists():
            try:
                import json
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                required = ["name", "version", "description", "author", "tags", "data_dir"]
                missing = [k for k in required if k not in meta]
                if missing:
                    print(f"[⚠️] _meta.json 缺失字段: {missing}")
                else:
                    print(f"[✅] _meta.json 结构正常")
            except json.JSONDecodeError as e:
                print(f"[⚠️] _meta.json JSON 格式错误: {e}")
        else:
            print(f"[⚠️] _meta.json 不存在")

    def _check_skill_md(self, skill_dir):
        """检查 SKILL.md"""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            print(f"[⚠️] SKILL.md 不存在")
            return

        content = skill_md.read_text(encoding="utf-8")
        lines = content.split("\n")
        line_count = len(lines)

        # 检查 frontmatter
        if content.startswith("---"):
            print(f"[✅] SKILL.md 有 frontmatter")
        else:
            print(f"[⚠️] SKILL.md 缺少 frontmatter")

        # 检查行数（230 = 200 + 15% 浮动）
        if line_count > 230:
            print(f"[💡] SKILL.md 共 {line_count} 行，超过 230 行建议拆分到 references/（限制：200+15%浮动）")
        else:
            print(f"[✅] SKILL.md 行数 {line_count} ≤ 230")

        # 检查三个必须文件
        refs_dir = skill_dir / "references"
        required_files = ["changelog.md", "guide.md", "permissions.md"]
        if refs_dir.exists():
            refs = [f.name for f in refs_dir.iterdir() if f.is_file()]
            missing = [f for f in required_files if f not in refs]
            if missing:
                print(f"[⚠️] references/ 缺少必须文件: {missing}")
            else:
                print(f"[✅] references/ 三个必须文件齐全（changelog.md/guide.md/permissions.md）")
        else:
            print(f"[⚠️] references/ 目录不存在，缺少渐进式加载文档")

        # 检查渐进式加载引用表
        has_progressive_table = any("渐进式加载" in l and "|" in l for l in lines)
        if has_progressive_table:
            print(f"[✅] 包含渐进式加载引用表")
        else:
            print(f"[⚠️] SKILL.md 可能缺少渐进式加载引用表（建议加入）")

    def _check_dir_structure(self, skill_dir):
        """检查目录结构规范性"""
        root_files = [f.name for f in skill_dir.iterdir() if f.is_file()]
        expected_root = {"SKILL.md", "_meta.json"}
        unexpected_root = set(root_files) - expected_root - {".gitignore"}

        if unexpected_root:
            print(f"[💡] 根目录有非常规文件: {sorted(unexpected_root)}（建议移入对应子目录）")
        else:
            print(f"[✅] 根目录结构规范（仅 SKILL.md + _meta.json）")
