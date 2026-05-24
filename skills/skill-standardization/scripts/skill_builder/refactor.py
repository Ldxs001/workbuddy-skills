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
        "M-04": "数据文件（.csv/.json 数据） → 外部数据目录",
        "M-05": "系统目录（__pycache__/node_modules/） → 排除",
        "M-06": "隐藏文件（.gitignore/.env） → 根目录保留",
    }

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

    # ──────────────────────────────────────────────────────────────────────────
    # 授权系统注入（从 updater.py 同步）
    # ──────────────────────────────────────────────────────────────────────────

    def _render_auth_check_py(self, permissions, skill_name):
        """
        逐行拼接 auth_check.py 的完整源码，避开模板转义问题。
        permissions: list of dict, 每个元素含 serial/name/desc/severity/file/line/authorization_method
        """
        import json

        L = []  # 用 list 收集所有行，最后 join

        def _(s=""):
            L.append(s)

        _("# -*- coding: utf-8 -*-")
        _('"""')
        _("授权检查模块 - 由 skill-standardization 自动生成 - DO NOT EDIT")
        _(f"技能: {skill_name}")
        _('"""')
        _()
        _("import json")
        _("import sys")
        _("from pathlib import Path")
        _()
        _('AUTH_STATE_FILE = Path(__file__).resolve().parent.parent / ".auth_state.json"')
        _()
        _("# 权限列表（自动生成，请勿手动修改）")

        # 把 permissions 格式化为紧凑 JSON 嵌入源码
        perms_json = json.dumps(permissions, ensure_ascii=False)
        _(f"_PERMISSIONS_RAW = {perms_json}")
        _()
        _("PERMISSIONS = _PERMISSIONS_RAW  # list[dict]")
        _()
        _("_initialized = False")
        _()
        _()
        _("def _load_state():")
        _('    """加载授权状态字典。"""')
        _("    if not AUTH_STATE_FILE.exists():")
        _("        return {}")
        _("    try:")
        _('        with open(AUTH_STATE_FILE, "r", encoding="utf-8") as _f:')
        _("            return json.load(_f)")
        _("    except Exception:")
        _("        return {}")
        _()
        _()
        _("def _save_state(state):")
        _('    """保存授权状态字典。"""')
        _('    AUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)')
        _('    with open(AUTH_STATE_FILE, "w", encoding="utf-8") as _f:')
        _("        json.dump(state, _f, indent=2, ensure_ascii=False)")
        _()
        _()
        _("def _all_unauthorized():")
        _('    """返回 True 当且仅当所有权限均未授权。"""')
        _("    st = _load_state()")
        _('    for p in PERMISSIONS:')
        _('        if st.get(p["name"], {}).get("authorized", False):')
        _("            return False")
        _("    return True")
        _()
        _()
        _("def _show_auth_table():")
        _('    """')
        _("    弹出授权表（全部未授权时调用）。")
        _("    用户可选择「全部授权」「输入序号」「拒绝」。")
        _('    """')
        _('    print("=" * 70)')
        _('    print(" 授权表 — 请选择需要授权的操作")')
        _('    print("=" * 70)')
        _('    print(f"{\'序号\':<6}  {\'权限名称\':<38}  简述")')
        _('    print("-" * 70)')
        _("    for p in PERMISSIONS:")
        _('        print(f"{p[\'serial\']:<6}  {p[\'name\']:<38}  {p[\'desc\'][:40]}")')
        _('    print("-" * 70)')
        _('    print(" 选项：")')
        _('    print("   all        — 全部授权")')
        _('    print("   1,3,5      — 输入序号（逗号分隔）")')
        _('    print("   r          — 拒绝所有（退出）")')
        _('    print("=" * 70)')
        _()
        _('    try:')
        _('        choice = input("请选择: ").strip().lower()')
        _('    except EOFError:')
        _('        print("[非交互环境] 默认全部授权")')
        _('        choice = "all"')
        _()
        _("    st = _load_state()")
        _()
        _('    if choice == "all":')
        _("        for p in PERMISSIONS:")
        _('            st[p["name"]] = {"authorized": True, "mode": "unified"}')
        _("        _save_state(st)")
        _('        print("[✓] 已授权全部操作")')
        _('    elif choice == "r":')
        _('        print("[✗] 用户拒绝授权，技能将退出")')
        _("        sys.exit(1)")
        _("    else:")
        _("        try:")
        _('            serials = [int(x.strip()) for x in choice.split(",")]')
        _("        except ValueError:")
        _('            print("[!] 输入格式错误，已跳过")')
        _("            return")
        _("        serial_map = {p['serial']: p['name'] for p in PERMISSIONS}")
        _("        for s in serials:")
        _("            if s in serial_map:")
        _('                st[serial_map[s]] = {"authorized": True, "mode": "unified"}')
        _("        _save_state(st)")
        _('        print(f"[✓] 已授权序号: {serials}")')
        _()
        _()
        _("def _prompt_immediate(perm_name, perm_desc):")
        _('    """')
        _("    对单个未授权权限弹出即时授权对话框。")
        _("    选项：1=永久授权  2=仅本次  3=拒绝")
        _('    返回: "permanent" / "once" / "reject"')
        _('    """')
        _('    print()')
        _('    print("=" * 60)')
        _('    print(f" [授权询问] {perm_desc}")')
        _('    print("=" * 60)')
        _('    print("   1. 永久授权（不再询问）")')
        _('    print("   2. 仅本次（本次执行生效，下次再问）")')
        _('    print("   3. 拒绝授权（跳过此操作）")')
        _('    print("=" * 60)')
        _('    try:')
        _('        choice = input("请选择 (1/2/3): ").strip()')
        _('    except EOFError:')
        _('        print("[非交互环境] 默认：仅本次授权")')
        _('        return "once"')
        _('    if choice == "1":')
        _('        return "permanent"')
        _('    elif choice == "2":')
        _('        return "once"')
        _("    else:")
        _('        return "reject"')
        _()
        _()
        _("def authorize(perm_name, perm_desc=''):")
        _('    """')
        _("    检查并请求授权。在每次高风险操作前调用。")
        _("    返回 True（已授权）/ False（已拒绝，调用方应跳过操作）。")
        _('    """')
        _("    global _initialized")
        _("    if not _initialized:")
        _("        initialize()")
        _("        _initialized = True")
        _()
        _("    st = _load_state()")
        _('    if st.get(perm_name, {}).get("authorized", False):')
        _("        return True")
        _()
        _("    decision = _prompt_immediate(perm_name, perm_desc)")
        _()
        _('    if decision == "permanent":')
        _('        st[perm_name] = {"authorized": True, "mode": "immediate"}')
        _("        _save_state(st)")
        _("        return True")
        _('    elif decision == "once":')
        _("        return True  # 仅本次，不落盘")
        _("    else:")
        _('        print(f"[✗] 权限 {perm_name} 被拒绝，跳过此操作")')
        _("        return False")
        _()
        _()
        _("def initialize():")
        _('    """')
        _("    在技能入口处调用一次。")
        _("    若全部未授权则弹出授权表；否则不干预。")
        _('    """')
        _("    if not _all_unauthorized():")
        _("        return")
        _("    if not PERMISSIONS:")
        _("        return")
        _("    _show_auth_table()")
        _("    # 重新检查：若仍全部未授权说明用户选了 r")
        _("    if _all_unauthorized():")
        _('        print("[✗] 未授权任何操作，技能退出")')
        _("        sys.exit(1)")
        _()
        _()
        _("def reset():")
        _('    """重置授权状态（调试用）。"""')
        _("    if AUTH_STATE_FILE.exists():")
        _("        AUTH_STATE_FILE.unlink()")
        _('    print("[*] 授权状态已重置")')
        _()
        _()
        _("def status():")
        _('    """打印当前授权状态。"""')
        _("    st = _load_state()")
        _('    print("授权状态：")')
        _("    for p in PERMISSIONS:")
        _('        ok = st.get(p["name"], {}).get("authorized", False)')
        _('        marker = "✓" if ok else "✗"')
        _('        auth_str = "已授权" if ok else "未授权"')
        _('        print(f"  [{marker}] {p[\'name\']}: {auth_str}")')
        _()
        _()
        _('if __name__ == "__main__":')
        _("    if len(sys.argv) > 1:")
        _("        cmd = sys.argv[1]")
        _('        if cmd == "status":')
        _("            status()")
        _('        elif cmd == "reset":')
        _("            reset()")
        _('        elif cmd == "init":')
        _("            initialize()")
        _("        else:")
        _('            print("Usage: python auth_check.py [status|reset|init]")')
        _("    else:")
        _("        initialize()")

        return "\n".join(L)

    def _generate_auth_check_py(self, skill_dir, report):
        """
        根据权限检查报告生成 scripts/auth_check.py 并写入磁盘。
        """
        issues = report.get("issues", [])
        if not issues:
            return False

        scripts_dir = Path(skill_dir) / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        auth_py = scripts_dir / "auth_check.py"

        # 构建权限列表（序号从 1 开始）
        permissions = []
        for i, iss in enumerate(issues, 1):
            permissions.append({
                "serial": i,
                "name": iss.get("rule", f"perm_{i}"),
                "desc": iss.get("description", ""),
                "severity": iss.get("severity", "MEDIUM"),
                "file": iss.get("file", ""),
                "line": iss.get("line", 0),
                "authorization_method": iss.get("authorization_method", "immediate"),
            })

        content = self._render_auth_check_py(permissions, Path(skill_dir).name)
        auth_py.write_text(content, encoding="utf-8")
        print(f"[*] 已生成授权模块: {auth_py}")
        return True

    def _inject_auth_imports(self, skill_dir, report):
        """
        在技能 scripts/ 下的所有 .py 文件头部注入
        「from auth_check import authorize, initialize」。
        避免重复注入。
        """
        scripts_dir = Path(skill_dir) / "scripts"
        if not scripts_dir.exists():
            return
        for py_file in scripts_dir.glob("*.py"):
            if py_file.name == "auth_check.py":
                continue   # 自己不注入
            lines = py_file.read_text(encoding="utf-8").splitlines()

            # 检查是否已注入
            has_import = any(
                "from auth_check import" in ln for ln in lines[:30]
            )
            if has_import:
                continue

            # 在第一个有意义的非注释行之前插入
            insert_idx = 0
            for i, ln in enumerate(lines):
                stripped = ln.strip()
                if stripped and not stripped.startswith("#"):
                    insert_idx = i
                    break
            lines.insert(insert_idx, "from auth_check import authorize, initialize")
            lines.insert(insert_idx + 1, "")

            py_file.write_text("\n".join(lines), encoding="utf-8")
            print(f"[*] 已注入 import: {py_file.name}")

    def _inject_initialize_calls(self, skill_dir):
        """
        在所有 scripts/*.py 的  if __name__ == "__main__":  块内
        注入一次  initialize()  调用。
        """
        scripts_dir = Path(skill_dir) / "scripts"
        if not scripts_dir.exists():
            return
        for py_file in scripts_dir.glob("*.py"):
            if py_file.name == "auth_check.py":
                continue
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            new_lines = []
            injected = False
            i = 0
            while i < len(lines):
                ln = lines[i]
                new_lines.append(ln)
                # 找到  if __name__ ... __main__  且下一行是冒号或缩进块
                if not injected and "__name__" in ln and "__main__" in ln:
                    # 找下一个非空行，在其前面插入  initialize()
                    j = i + 1
                    while j < len(lines) and lines[j].strip() == "":
                        new_lines.append(lines[j])
                        j += 1
                    if j < len(lines):
                        # 用下一行的缩进 + 4 空格
                        next_ln = lines[j]
                        indent = " " * (len(next_ln) - len(next_ln.lstrip())) + "    "
                        # 避免重复
                        if not any("initialize()" in l for l in lines):
                            new_lines.append(f"{indent}initialize()")
                    injected = True
                    i = j
                    continue
                i += 1
            if injected:
                py_file.write_text("\n".join(new_lines), encoding="utf-8")
                print(f"[*] 已注入 initialize(): {py_file.name}")

    def _inject_auth_calls(self, skill_dir, report):
        """
        在每个高风险操作所在行之前注入
        「if not authorize("rule_name", "description"): return」调用。
        按文件分组，插入位置按倒序处理以防行号偏移。
        """
        issues = report.get("issues", [])
        if not issues:
            return

        by_file = {}
        for iss in issues:
            fp = iss.get("file", "")
            if not fp:
                continue
            by_file.setdefault(fp, []).append(iss)

        for rel_path, file_issues in by_file.items():
            # 跳过 auth_check.py 自身（它定义了 authorize()，不应被注入）
            if Path(rel_path).name == "auth_check.py":
                continue
            target = Path(skill_dir) / rel_path
            if not target.exists() or target.suffix != ".py":
                continue

            lines = target.read_text(encoding="utf-8").splitlines()

            # 收集插入点 (insert_pos, perm_name, perm_desc)
            insertions = []
            for iss in file_issues:
                ln = iss.get("line", 0)
                if ln <= 0 or ln > len(lines):
                    continue
                # 插入到该行之前（0-indexed: ln-1）
                insert_pos = ln - 1
                pn = iss.get("rule", "unknown")
                pd = iss.get("description", "")
                insertions.append((insert_pos, pn, pd))

            if not insertions:
                continue

            # 按插入位置倒序
            insertions.sort(reverse=True)

            for insert_pos, pn, pd in insertions:
                # 取当前行缩进
                if insert_pos < len(lines):
                    cur = lines[insert_pos]
                    indent = cur[:len(cur) - len(cur.lstrip())]  # 保留原始空白（tab/space 原样）
                else:
                    indent = ""
                call = f"{indent}if not authorize({json.dumps(pn)}, {json.dumps(pd)}): return"
                # 在函数/方法顶部注入时缩进可能不对，统一加 4 空格
                if not call.strip().startswith("if"):
                    call = f"    {call.strip()}"
                lines.insert(insert_pos, call)

            target.write_text("\n".join(lines), encoding="utf-8")
            print(f"[*] 已注入 authorize() 调用: {rel_path}")

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
                return report
            return None
        except Exception as e:
            print(f"[!] 运行 permission_checker.py 失败: {e}")
            return None

    def _inject_auth_section(self, skill_dir, report):
        """
        根据权限检查报告，为 SKILL.md 注入「## 授权要求」章节（文档用途）。
        同时在 scripts/ 下生成可执行的 auth_check.py 并注入 authorize() 调用。
        """
        if not report:
            return
        issues = report.get("issues", [])
        if not issues:
            return

        # ── 1. 生成 scripts/auth_check.py ────────────────────────────────────
        self._generate_auth_check_py(skill_dir, report)

        # ── 2. 注入 import 语句 ─────────────────────────────────────────────
        self._inject_auth_imports(skill_dir, report)

        # ── 3. 注入 initialize() 调用 ────────────────────────────────────────
        self._inject_initialize_calls(skill_dir)

        # ── 4. 注入 authorize() 调用（高风险操作前）────────────────────────
        self._inject_auth_calls(skill_dir, report)

        # ── 5. 注入 SKILL.md 文档章节 ──────────────────────────────────────
        skill_md = Path(skill_dir) / "SKILL.md"
        if not skill_md.exists():
            return

        content = skill_md.read_text(encoding="utf-8")
        if "## 授权要求" in content:
            print("[*] SKILL.md 已包含「授权要求」章节，跳过注入")
        else:
            groups = {"immediate": [], "unified": [], "silent": []}
            for iss in issues:
                method = iss.get("authorization_method", "immediate")
                if method not in groups:
                    method = "immediate"
                groups[method].append(iss)

            lines = ["\n\n---\n\n## 授权要求\n"]
            lines.append("本技能包含以下中高风险操作，使用前需获得用户授权：\n")

            idx = 0
            for method in ("immediate", "unified", "silent"):
                for iss in groups[method]:
                    idx += 1
                    sev_cn = {"HIGH": "高", "ERROR": "高", "MEDIUM": "中"}.get(
                        iss.get("severity", ""), "低"
                    )
                    desc = iss.get("description", "")
                    file = iss.get("file", "")
                    line = iss.get("line", 0)
                    reason = iss.get("reason", "")
                    lines.append(f"{idx}. **[{sev_cn}] {desc}**（`{file}` 第 {line} 行）")

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

            new_content = content.rstrip() + "\n" + "\n".join(lines)
            skill_md.write_text(new_content, encoding="utf-8")
            print(f"[*] 已注入「授权要求」章节（{idx} 项操作）")

    # ──────────────────────────────────────────────────────────────────────────
    # 主入口
    # ──────────────────────────────────────────────────────────────────────────

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

        # ★ 新增：注入授权要求章节
        if getattr(args, "inject_auth", False):
            report = self._run_permission_checker(skill_dir)
            self._inject_auth_section(skill_dir, report)

        print(f"\n✅ refactor 完成！")
        print(f"   备份位置: {backup_dir}")
        print(f"   迁移文件: {len(migration_plan)} 个")
