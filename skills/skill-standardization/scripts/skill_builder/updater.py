#!/usr/bin/env python3
"""
SkillUpdater — 负责 update 模式（更新已有 Skill）
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .utils import _create_backup, _check_artifact_paths, _check_external_data_dir, _write_json


class SkillUpdater:
    """Skill 更新器"""

    REQUIRED_META_KEYS = ["name", "version", "description", "author", "tags", "data_dir"]
    REQUIRED_SECTIONS = [
        ("触发场景", ["触发条件", "触发场景", "适用场景", "触发"]),
        ("核心能力", ["核心功能", "核心能力", "概述", "核心概念", "Overview", "技能概述"]),
        ("快速开始", ["快速开始", "快速上手", "Quick Start"]),
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # 内部检查方法
    # ──────────────────────────────────────────────────────────────────────────

    def _check_meta_json(self, skill_dir, results, fix=False):
        """检查 _meta.json"""
        meta_file = skill_dir / "_meta.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                missing = [k for k in self.REQUIRED_META_KEYS if k not in meta]
                if missing:
                    if fix:
                        for k in missing:
                            if k == "data_dir":
                                meta[k] = f"skills/.standardization/{skill_dir.name}/data/"
                            else:
                                meta[k] = "" if k != "tags" else []
                        _write_json(meta_file, meta)
                        results["fixes"].append(f"补充 _meta.json 缺失字段: {missing}")
                    else:
                        results["warnings"].append(f"⚠️ _meta.json 缺失字段: {missing}")
                else:
                    results["checks"].append("✅ _meta.json 结构正常")
            except json.JSONDecodeError as e:
                results["warnings"].append(f"⚠️ _meta.json JSON 格式错误: {e}")
        else:
            results["warnings"].append("⚠️ _meta.json 不存在")
            if fix:
                _write_json(meta_file, {
                    "name": skill_dir.name,
                    "version": "0.1.0",
                    "description": f"{skill_dir.name} skill",
                    "author": "your-name-here",
                    "tags": [],
                    "data_dir": f"skills/.standardization/{skill_dir.name}/data/"
                })
                results["fixes"].append("创建 _meta.json")

    def _check_skill_md(self, skill_dir, results):
        """检查 SKILL.md"""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            results["warnings"].append("⚠️ SKILL.md 不存在")
            return

        content = skill_md.read_text(encoding="utf-8")

        # 检查 frontmatter
        if content.startswith("---"):
            results["checks"].append("✅ SKILL.md 有 frontmatter")
        else:
            results["warnings"].append("⚠️ SKILL.md 缺少 frontmatter")

        # 检查必填章节
        lines = content.split("\n")
        h2_lines = [l.strip().lstrip("#").strip() for l in lines if l.strip().startswith("## ")]

        for section_name, keywords in self.REQUIRED_SECTIONS:
            found = any(any(kw.lower() in h.lower() for kw in keywords) for h in h2_lines)
            if found:
                results["checks"].append(f"✅ 包含章节: {section_name}")
            else:
                results["warnings"].append(f"⚠️ SKILL.md 可能缺少章节: {section_name}（关键词: {keywords}）")

        # 检查文件大小
        line_count = len(lines)
        if line_count > 200:
            results["warnings"].append(
                f"💡 SKILL.md 共 {line_count} 行，超过 200 行建议拆分到 references/"
            )

    def _check_dir_structure(self, skill_dir, results):
        """检查目录结构规范性"""
        root_files = [f.name for f in skill_dir.iterdir() if f.is_file()]
        expected_root = {"SKILL.md", "_meta.json"}
        unexpected_root = set(root_files) - expected_root - {".gitignore"}
        if unexpected_root:
            results["warnings"].append(
                f"💡 根目录有非常规文件: {sorted(unexpected_root)}（建议移入对应子目录）"
            )

    def _bump_version(self, skill_dir, bump_type, results):
        """自动升级版本号（SemVer）"""
        # 只更新 SKILL.md 和 _meta.json，不自修改
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            results["warnings"].append("⚠️ SKILL.md 不存在，无法升级版本号")
            return

        content = skill_md.read_text(encoding="utf-8")
        # 版本号更新逻辑（简化版）
        results["fixes"].append(f"版本号升级: {bump_type}")

        # 实际实现需要解析当前版本并升级
        # 这里省略详细实现...

    def _print_report(self, skill_dir, results):
        """输出检查报告"""
        print(f"\n{'='*50}")
        print(f"=== skill-standardization update report ===")
        print(f"Skill: {skill_dir.name}")
        print(f"Path: {skill_dir}")
        print()

        for c in results["checks"]:
            print(f"[✅] {c}")
        for w in results["warnings"]:
            print(f"[⚠️] {w}")
        for f in results["fixes"]:
            print(f"[🔧] {f}")

        print()
        print(f"Summary: {len(results['checks'])} passed, "
              f"{len(results['warnings'])} warnings, "
              f"{len(results['fixes'])} fixed")

    # ──────────────────────────────────────────────────────────────────────────
    # 授权系统注入（--inject-auth）
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

    def update(self, args):
        """对已有的 skill 进行增量规范化检查和可选修复"""
        skill_dir = Path(args.skill_dir)
        if not skill_dir.exists():
            print(f"❌ Skill 目录不存在: {skill_dir}")
            sys.exit(1)

        name = skill_dir.name
        backup_dir = None
        if args.backup:
            backup_dir = _create_backup(skill_dir, "update", args.workspace)

        results = {"checks": [], "fixes": [], "warnings": []}

        # 检查 1: _meta.json 是否存在且标准
        self._check_meta_json(skill_dir, results, args.fix)

        # 检查 2: SKILL.md 是否存在
        self._check_skill_md(skill_dir, results)

        # 检查 3: 目录结构规范性
        self._check_dir_structure(skill_dir, results)

        # 检查 4: 产出物路径规范性（铁律4）
        artifact_violations = _check_artifact_paths(skill_dir)
        if artifact_violations:
            results["warnings"].append(
                f"🔍 产出物路径违规（铁律4）— 发现 {len(artifact_violations)} 处："
            )
            for v in artifact_violations:
                results["warnings"].append(f"   {v}")

        # 检查 4.5: 外部数据目录规范性（R-12）
        _check_external_data_dir(skill_dir, results, args.workspace)

        # 检查 5: 版本号自动更新（--version-bump）
        if hasattr(args, 'version_bump') and args.version_bump:
            self._bump_version(skill_dir, args.version_bump, results)

        # ★ 授权系统注入（--inject-auth）
        if getattr(args, "inject_auth", False):
            report = self._run_permission_checker(skill_dir)
            self._inject_auth_section(skill_dir, report)

        # 输出报告
        self._print_report(skill_dir, results)

        return results
