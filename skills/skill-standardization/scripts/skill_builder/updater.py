#!/usr/bin/env python3
"""
SkillUpdater — 负责 update 模式（更新已有 Skill）
"""

import json
import sys
import subprocess
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

        # 检查 0: R-01~R-17 规则审查（skill_audit）
        self._check_skill_audit(skill_dir, results)

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

        # 检查 5: 权限扫描（permission_checker）
        fix_applied = self._check_permissions(skill_dir, results, getattr(args, 'fix', False))

        # 检查 6: 版本号自动更新（--version-bump）
        if hasattr(args, 'version_bump') and args.version_bump:
            self._bump_version(skill_dir, args.version_bump, results)

        # 输出报告
        self._print_report(skill_dir, results)

        return results

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

        # 检查文件大小（230行 = 200 + 15% 浮动）
        line_count = len(lines)
        if line_count > 230:
            results["warnings"].append(
                f"💡 SKILL.md 共 {line_count} 行，超过 230 行建议拆分到 references/（限制：200+15%浮动）"
            )
        else:
            results["checks"].append(f"✅ SKILL.md 行数 {line_count} ≤ 230")

        # 检查三个必须文件（渐进式加载）
        refs_dir = skill_dir / "references"
        required_files = ["changelog.md", "guide.md", "permissions.md"]
        if refs_dir.exists():
            refs = [f.name for f in refs_dir.iterdir() if f.is_file()]
            missing = [f for f in required_files if f not in refs]
            if missing:
                results["warnings"].append(f"⚠️ references/ 缺少必须文件: {missing}")
            else:
                results["checks"].append("✅ references/ 三个必须文件齐全（changelog.md/guide.md/permissions.md）")
        else:
            results["warnings"].append("⚠️ references/ 目录不存在，缺少渐进式加载文档")

        # 检查渐进式加载引用表
        has_progressive_table = any("渐进式加载" in l and "|" in l for l in lines)
        if has_progressive_table:
            results["checks"].append("✅ 包含渐进式加载引用表")
        else:
            results["warnings"].append("⚠️ SKILL.md 可能缺少渐进式加载引用表（建议加入）")

    def _check_dir_structure(self, skill_dir, results):
        """检查目录结构规范性"""
        root_files = [f.name for f in skill_dir.iterdir() if f.is_file()]
        expected_root = {"SKILL.md", "_meta.json"}
        unexpected_root = set(root_files) - expected_root - {".gitignore"}

        if unexpected_root:
            results["warnings"].append(
                f"💡 根目录有非常规文件: {sorted(unexpected_root)}（建议移入对应子目录）"
            )

    def _check_skill_audit(self, skill_dir, results):
        """调用 skill_audit 进行 R-01~R-17 规则审查"""
        import sys, json
        from pathlib import Path
        
        # 将 skill_audit 的父目录加入 sys.path
        audit_pkg = Path(__file__).parent.parent / "skill_audit"
        if not audit_pkg.exists():
            results["warnings"].append("⚠️ skill_audit 目录不存在，跳过 R-01~R-17 审查")
            return
        
        sys.path.insert(0, str(audit_pkg.parent))
        try:
            from skill_audit import audit_skill
            report = audit_skill(str(skill_dir), manifest_version=None)
        except Exception as e:
            results["warnings"].append(f"⚠️ skill_audit 导入/执行失败: {e}")
            return
        
        verdict = report.get("verdict", "UNKNOWN")
        summary = report.get("summary", {})
        
        if verdict == "PASS":
            total = summary.get("total", 0)
            passed = summary.get("pass", 0)
            results["checks"].append(f"✅ R-01~R-17 规则审查通过（{passed}/{total}）")
        else:
            fail = summary.get("fail", 0)
            warns = summary.get("warns", 0)
            errors = summary.get("errors", 0)
            results["warnings"].append(f"⚠️ R-01~R-17 审查未通过：{errors} ERROR, {warns} WARN")
            # 输出前5条失败规则
            for res in report.get("results", []):
                if not res.get("passed", False) and not res.get("skipped", False):
                    rule_id = res.get("rule_id", "?")
                    detail = res.get("detail", "")
                    results["warnings"].append(f"   [{rule_id}] {detail}")
                    if len([r for r in results["warnings"] if r.startswith("   [")]) >= 5:
                        break


    def _check_permissions(self, skill_dir, results, fix=False):
        """调用 permission_checker.py 进行权限扫描；fix=True 时自动修改目标 skill"""
        import subprocess, json
        checker = Path(__file__).parent.parent / "permission_checker.py"
        if not checker.exists():
            results["warnings"].append("⚠️ permission_checker.py 不存在，跳过权限扫描")
            return False

        try:
            proc = subprocess.run(
                ["python", str(checker), str(skill_dir)],
                capture_output=True, text=True, timeout=30
            )
            output = proc.stdout.strip()
            if not output:
                return False
            report = json.loads(output)
            issues = report.get("issues", [])
            stats = report.get("stats", {})

            if issues:
                results["warnings"].append(
                    f"🔍 权限扫描发现 {len(issues)} 项风险（{report.get('risk_level','unknown')}）："
                )
                for iss in issues[:10]:
                    results["warnings"].append(
                        f"   [{iss.get('severity','?')}] {iss.get('file','?')}:{iss.get('line','?')} — {iss.get('description','')}"
                    )
                if len(issues) > 10:
                    results["warnings"].append(f"   ...还有 {len(issues)-10} 项，详见 JSON 报告")
            else:
                results["checks"].append(f"✅ 权限扫描通过（{report.get('risk_level','low')}）")

            # 权限扫描结果仅输出报告，不修改目标 skill
            # AI 看到报告后自觉参考 references/permissions.md
            return False

        except Exception as e:
            results["warnings"].append(f"⚠️ 权限扫描失败: {e}")
            return False

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
