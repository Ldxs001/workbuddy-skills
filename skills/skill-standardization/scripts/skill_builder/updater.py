#!/usr/bin/env python3
"""
SkillUpdater — 负责 update 模式（更新已有 Skill）
"""

import json
import os

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
        """自动升级版本号（SemVer），同步更新 changelog"""
        from pathlib import Path
        import re, json
        from datetime import datetime

        skill_md = skill_dir / "SKILL.md"
        meta_file = skill_dir / "_meta.json"
        if not skill_md.exists():
            results["warnings"].append("⚠️ SKILL.md 不存在，无法升级版本号")
            return

        # 读取当前版本
        content = skill_md.read_text(encoding="utf-8")
        m = re.search(r"^version:\s*([\d\.]+)", content, re.MULTILINE)
        if not m:
            results["warnings"].append("⚠️ SKILL.md frontmatter 中未找到 version 字段")
            return

        old_ver = m.group(1)
        parts = list(map(int, old_ver.split(".")))
        while len(parts) < 3:
            parts.append(0)

        # 升级
        bt = (bump_type or "patch").lower()
        if bt == "major":
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif bt == "minor":
            parts[1] += 1
            parts[2] = 0
        else:  # patch
            parts[2] += 1

        new_ver = ".".join(map(str, parts))
        today = datetime.now().strftime("%Y-%m-%d")

        # 写入 SKILL.md
        new_content = content[:m.start(1)] + new_ver + content[m.end(1):]
        skill_md.write_text(new_content, encoding="utf-8")

        # 写入 _meta.json
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                meta["version"] = new_ver
                meta_file.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8"
                )
            except Exception as e:
                results["warnings"].append(f"⚠️ 更新 _meta.json 版本号失败: {e}")

        # ★ 同步更新 references/changelog.md 或 CHANGELOG.md
        changelog_candidates = [
            skill_dir / "references" / "changelog.md",
            skill_dir / "references" / "CHANGELOG.md",
            skill_dir / "CHANGELOG.md",
            skill_dir / "changelog.md",
        ]
        changelog_path = None
        for p in changelog_candidates:
            if p.exists():
                changelog_path = p
                break

        if changelog_path:
            try:
                today_str = datetime.now().strftime("%Y-%m-%d")
                old_content = changelog_path.read_text(encoding="utf-8")
                # 如果已有前缀 title（# Changelog），在其后插入新条目
                insert_pos = 0
                title_match = re.search(r"^#\s+.+", old_content, re.MULTILINE)
                if title_match:
                    # 找第一个版本条目位置
                    ver_match = re.search(r"\n##\s+v?[\d\.]+", old_content)
                    if ver_match:
                        insert_pos = ver_match.start() + 1
                    else:
                        insert_pos = len(old_content)  # append
                entry = (
                    f"\n## v{new_ver} ({today}) — 自动版本升级\n\n"
                    f"### Changed\n"
                    f"- 版本号 {old_ver} → {new_ver}（`update --fix` 自动 bump）\n"
                )
                new_cl = old_content[:insert_pos] + entry + old_content[insert_pos:]
                changelog_path.write_text(new_cl, encoding="utf-8")
                results["fixes"].append(f"✅ 更新日志已追加: {changelog_path.relative_to(skill_dir)}")
            except Exception as e:
                results["warnings"].append(f"⚠️ 更新 changelog 失败: {e}")
        else:
            results["warnings"].append(
                "⚠️ 未找到 changelog 文件（checked: references/changelog.md, CHANGELOG.md），"
                "版本号已升级但日志未记录"
            )

        results["fixes"].append(f"✅ 版本号升级: {old_ver} → {new_ver} ({bt})")

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

    # ── 授权要求注入（--inject-auth）────────────────────────────────────────

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
                # 自动写入权限说明到 references/permissions.md
                self._write_permissions_md(skill_dir, report)
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

        # 注入到文件末尾
        new_content = content.rstrip() + "\n" + "\n".join(lines)
        skill_md.write_text(new_content, encoding="utf-8")
        print(f"[*] 已注入「授权要求」章节（{idx} 项操作）")

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

        # ★ 新增：注入授权要求章节
        if getattr(args, "inject_auth", False):
            report = self._run_permission_checker(skill_dir)
            self._inject_auth_section(skill_dir, report)

        # 输出报告
        self._print_report(skill_dir, results)

        return results

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

        # 按类别分组（使用 type 字段，而非 category）
        categories = {}
        for iss in issues:
            cat = iss.get("type", "other")
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
                lines.append(f"| {i} | {desc} | {sev_cn} | `{iss.get('match', '')[:50]}` | {location} | {method_cn} |")
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

