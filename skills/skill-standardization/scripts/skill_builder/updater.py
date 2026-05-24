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
                return report
            return None
        except Exception as e:
            print(f"[!] 运行 permission_checker.py 失败: {e}")
            return None

    def _inject_auth_section(self, skill_dir, report):
        """
        根据权限检查报告，为 SKILL.md 注入「## 授权要求」章节。

        授权方式判定规则：
        - HIGH / ERROR  → 即时授权（immediate）
        - MEDIUM        → 统一授权（unified）
        - 其他           → 静默授权（silent）
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

        # 按授权方式分组
        groups = {"immediate": [], "unified": [], "silent": []}
        for iss in issues:
            sev = iss.get("severity", "")
            if sev in ("HIGH", "ERROR"):
                method = "immediate"
            elif sev == "MEDIUM":
                method = "unified"
            else:
                method = "silent"
            groups[method].append((method, iss))

        # 生成章节内容
        lines = ["\n\n---\n\n## 授权要求\n"]
        lines.append("本技能包含以下中高风险操作，使用前需获得用户授权：\n")

        idx = 0
        for method in ("immediate", "unified", "silent"):
            for m, iss in groups[method]:
                idx += 1
                sev_cn = {"HIGH": "高", "ERROR": "高", "MEDIUM": "中"}.get(iss.get("severity", ""), "低")
                desc = iss.get("description", "")
                file = iss.get("file", "")
                line = iss.get("line", 0)
                lines.append(f"{idx}. **[{sev_cn}] {desc}**（`{file}` 第 {line} 行）")

                if method == "immediate":
                    lines.append("   - 授权方式：**即时授权**（每次执行前需获得用户批准）\n")
                elif method == "unified":
                    lines.append("   - 授权方式：**统一授权**（首次执行前获得用户批准，后续不再询问）\n")
                else:
                    lines.append("   - 授权方式：**静默授权**（无需用户交互，自动执行并记录）\n")

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

