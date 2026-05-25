#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit package — SKILL.md 规范化审查工具 v2.25.0

支持 R-01~R-21 规则审查，集成到 git-sync 流程。

用法:
    python -m skill_audit audit <skill_dir> [--json] [--manifest-version VER]
    python -m skill_audit audit-all <skills_dir> [--manifest FILE] [--json]
    python -m skill_audit rules
"""

import os
import sys
import json
import argparse
from pathlib import Path

# ── 导入子模块 ─────────────────────────────────────────────
from .utils import (
    RULES, TRIGGER_KEYWORDS, CORE_KEYWORDS, WORKFLOW_KEYWORDS,
    ARTIFACT_DIR_NAMES, _KNOWN_STANDARD_DIRS, _ARTIFACT_DIR_CLASSIFY,
    _ARTIFACT_EXTS_COMPREHENSIVE, _ARTIFACT_DIR_PATTERN,
    _ARTIFACT_WRITE_PATTERNS, _HARDCODED_PATH_RE, _PATH_EXCLUDE_RE,
    _is_hardcoded_path, parse_simple_yaml_frontmatter,
    _find_skills_dir,
)
from .frontmatter_checker import (
    regex_frontmatter_exists, yaml_has_name, yaml_has_semver_version,
    yaml_has_description, name_matches_dirname, version_matches_manifest,
)
from .structure_checker import (
    body_has_h1, body_has_trigger_section, body_has_core_section,
    body_has_workflow_section,
    body_has_antipattern_section, body_has_faq_section,
    body_check_writing_standards,
    body_has_progressive_loading_explicit,
)
from .artifact_checker import (
    check_artifact_paths, check_external_data_dir,
)
from .permission_checks import (
    check_sensitive_access_declaration, check_critical_write_declaration,
    check_authorization_present, check_permission_weight_explained,
    check_progressive_loading_forced,
)

# ── 方法分派表 ─────────────────────────────────────────────
METHOD_MAP = {
    "check_external_data_dir": check_external_data_dir,
    "regex_frontmatter_exists": regex_frontmatter_exists,
    "yaml_has_name": yaml_has_name,
    "yaml_has_semver_version": yaml_has_semver_version,
    "yaml_has_description": yaml_has_description,
    "name_matches_dirname": name_matches_dirname,
    "body_has_h1": body_has_h1,
    "body_has_trigger_section": body_has_trigger_section,
    "body_has_core_section": body_has_core_section,
    "body_has_workflow_section": body_has_workflow_section,
    "version_matches_manifest": version_matches_manifest,
    "check_artifact_paths": check_artifact_paths,
    "check_sensitive_access_declaration": check_sensitive_access_declaration,
    "check_critical_write_declaration": check_critical_write_declaration,
    "check_authorization_present": check_authorization_present,
    "check_permission_weight_explained": check_permission_weight_explained,
    "check_progressive_loading_forced": check_progressive_loading_forced,
    "body_has_antipattern_section": body_has_antipattern_section,
    "body_has_faq_section": body_has_faq_section,
    "body_check_writing_standards": body_check_writing_standards,
    "body_has_progressive_loading_explicit": body_has_progressive_loading_explicit,
}


def _apply_fixes(skill_md, fixes):
    """
    将 fixes 列表应用到 SKILL.md 的 frontmatter。
    fixes: [{"key": "sensitive_access", "value": True, "reason": "..."}, ...]
    """
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return []  # 无 frontmatter，无法修正

    applied = []
    for fix in fixes:
        key = fix["key"]
        val = fix["value"]
        fm[key] = val
        applied.append(f"{key}: {val} ({fix.get('reason', '')})")

    # 重新组装 frontmatter + body
    import io
    buf = io.StringIO()
    buf.write("---\n")
    for k, v in fm.items():
        if isinstance(v, bool):
            buf.write(f"{k}: {'true' if v else 'false'}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {v}\n")
        else:
            buf.write(f"{k}: {v}\n")
    buf.write("---\n")
    buf.write(body)

    with open(skill_md, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())

    return applied


def audit_skill(skill_dir, manifest_version=None, _fix_applied=False, progress_file=None):
    """
    审查单个 skill 目录中的 SKILL.md。_fix_applied 防止无限递归。

    如果传了 _progress_file，审计结束后自动更新 .progress.md。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    dirname = os.path.basename(os.path.normpath(skill_dir))

    if not os.path.isfile(skill_md):
        return {
            "skill": dirname,
            "path": skill_dir,
            "error": "SKILL.md 文件不存在",
            "results": [],
            "summary": {"total": 0, "pass": 0, "fail": 0, "skip": 0, "errors": 0, "warns": 0},
            "verdict": "ERROR — SKILL.md 不存在",
        }

    with open(skill_md, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    fm, body = parse_simple_yaml_frontmatter(content)

    results = []
    error_count = 0
    warn_count = 0
    pass_count = 0
    skip_count = 0
    fixes = []

    for rule in RULES:
        method_fn = METHOD_MAP.get(rule["method"])
        if not method_fn:
            continue

        result = method_fn(
            filepath=skill_md,
            content=content,
            fm=fm,
            body=body,
            dirname=dirname,
            skill_dir=skill_dir,
            manifest_version=manifest_version,
        )
        passed = result.get("passed", False)
        skipped = result.get("skip", False)

        entry = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "severity": rule["severity"],
            "passed": passed,
            "skipped": skipped,
            "detail": result.get("detail", ""),
        }
        results.append(entry)

        # 收集 fix 建议
        if not passed and not skipped and result.get("fix"):
            fixes.append(result["fix"])

        if skipped:
            skip_count += 1
        elif passed:
            pass_count += 1
        elif rule["severity"] == "ERROR":
            error_count += 1
        else:
            warn_count += 1

    # 自动修正：有不一致的声明，且还没修正过，且不是 dry-run 模式
    fixed = []
    dry_run = os.environ.get("SKILL_AUDIT_DRY_RUN", "0") == "1"
    if fixes and not _fix_applied and not dry_run:
        applied = _apply_fixes(skill_md, fixes)
        if applied:
            fixed = applied
            # 重新审计一次，确保修正后通过
            re_result = audit_skill(skill_dir, manifest_version=manifest_version, _fix_applied=True)
            re_result["fixed"] = fixed
            re_result["re_audit"] = True
            return re_result

    fail_count = error_count + warn_count
    total = len(results)

    if error_count > 0:
        verdict = f"FAIL ({error_count} ERROR{', ' + str(warn_count) + ' WARN' if warn_count > 0 else ''})"
    elif warn_count > 0:
        verdict = f"WARN ({warn_count} WARN)"
    else:
        verdict = "PASS"

    r = {
        "skill": dirname,
        "path": skill_dir,
        "results": results,
        "summary": {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "skip": skip_count,
            "errors": error_count,
            "warns": warn_count,
        },
        "verdict": verdict,
    }
    if fixed:
        r["fixed"] = fixed
    # 更新 .progress.md（如果传了 _progress_file）
    if progress_file:
        try:
            from .progress_manager import update_progress_from_audit, finalize_progress
            update_progress_from_audit(progress_file, r)
            finalize_progress(progress_file, r)
        except Exception as e:
            print(f"[!] 更新 .progress.md 失败: {e}", file=sys.stderr)
    return r


def format_report(audit_result, verbose=True):
    """格式化人类可读的审查报告"""
    lines = []
    r = audit_result

    if "error" in r:
        lines.append(f"❌ {r['skill']}: {r['error']}")
        return "\n".join(lines)

    lines.append(f"{'='*55}")
    lines.append(f"  审查结果: {r['skill']} — {r['verdict']}")
    lines.append(f"{'='*55}")

    s = r["summary"]
    lines.append(f"  总计: {s['total']} | 通过: {s['pass']} | 失败: {s['fail']} | 跳过: {s['skip']}")

    # 显示自动修正信息
    if r.get("fixed"):
        lines.append(f"\n{'─'*55}")
        lines.append("  ⚠️  已自动修正以下 frontmatter 字段：")
        for fix_desc in r["fixed"]:
            lines.append(f"    • {fix_desc}")
        if r.get("re_audit"):
            lines.append("  （已重新审计，确保修正后通过）")
        lines.append(f"{'─'*55}")

    if verbose:
        lines.append("")
        lines.append(f"{'规则ID':<8} {'严重度':<7} {'状态':<6} 详情")
        lines.append(f"{'-'*8}-{'-'*7}-{'-'*6}-{'-'*30}")
        for res in r["results"]:
            status = "✅" if res["passed"] else ("⏭️" if res["skipped"] else ("🔴" if res["severity"]=="ERROR" else "🟡"))
            sev = res["severity"][0] if res["severity"] else "?"
            lines.append(f"{res['rule_id']:<8} {sev:<7} {status:<6} {res['detail']}")

    return "\n".join(lines)


def cmd_rules():
    """列出所有审查规则"""
    print(f"\n{'ID':<8} {'严重度':<8} 名称  检查内容")
    print("-" * 65)
    for rule in RULES:
        sev_mark = "🔴" if rule["severity"] == "ERROR" else "🟡"
        print(f"  {rule['id']:<6} {sev_mark} {rule['severity']:<6} {rule['name']: <20} {rule['check']}")
    print(f"\n共 {len(RULES)} 条规则")


def cmd_audit(args):
    """审查单个 skill 目录"""
    skill_dir = args.skill_dir
    if not os.path.isdir(skill_dir):
        print(f"❌ 目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    result = audit_skill(skill_dir, manifest_version=args.manifest_version,
                        progress_file=args.progress_file)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))


def cmd_audit_all(args):
    """批量审查 skills 目录下所有 skill"""
    skills_dir = args.skills_dir
    manifest_file = args.manifest

    # 读取 manifest 获取版本号映射
    version_map = {}
    if manifest_file and os.path.isfile(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
            items = mdata.get("repos", {}).get("workbuddy-skills", {}).get("items", {})
            for name, info in items.items():
                if isinstance(info, dict) and "version" in info:
                    version_map[name] = info["version"]
        except Exception as e:
            print(f"⚠️  读取 manifest 失败: {e}", file=sys.stderr)

    # 发现所有 skill 目录
    entries = []
    for entry in sorted(os.listdir(skills_dir)):
        full_path = os.path.join(skills_dir, entry)
        if os.path.isdir(full_path) and os.path.isfile(os.path.join(full_path, "SKILL.md")):
            entries.append((entry, full_path))

    all_results = []
    total_errors = 0
    total_warns = 0

    for dirname, dirpath in entries:
        mv = version_map.get(dirname)
        result = audit_skill(dirpath, manifest_version=mv)
        all_results.append(result)
        total_errors += result["summary"]["errors"]
        total_warns += result["summary"]["warns"]

    if args.json:
        print(json.dumps({
            "audited_count": len(all_results),
            "total_errors": total_errors,
            "total_warns": total_warns,
            "results": all_results,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  批量审查报告 — 共 {len(entries)} 个 skill")
        print(f"  汇总: {sum(r['summary']['pass'] for r in all_results)} PASS / "
              f"{total_errors} ERROR / {total_warns} WARN")
        print(f"{'='*60}")

        for r in all_results:
            print(format_report(r, verbose=False))
            print()

        print(f"\n{'='*60}")
        print("  详细逐项结果:")
        print(f"{'='*60}")
        for r in all_results:
            if "error" not in r:
                print(format_report(r, verbose=True))
                print()


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SKILL.md 规范化审查工具 (R-01~R-17)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m skill_audit audit ~/.workbuddy/skills/git-sync
  python -m skill_audit audit ~/.workbuddy/skills/svg-composer --json
  python -m skill_audit audit-all ~/.workbuddy/skills --manifest manifest.json
  python -m skill_audit rules
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # audit 子命令
    p_audit = subparsers.add_parser("audit", help="审查单个 skill")
    p_audit.add_argument("skill_dir", help="skill 目录路径")
    p_audit.add_argument("--json", action="store_true", help="JSON 格式输出")
    p_audit.add_argument("--manifest-version", metavar="VER", help="manifest 中记录的版本号（用于 R-10）")
    p_audit.add_argument("--progress-file", metavar="FILE", help=".progress.md 文件路径（用于过程管理）")

    # audit-all 子命令
    p_all = subparsers.add_parser("audit-all", help="批量审查所有 skill")
    p_all.add_argument("skills_dir", help="skills 根目录")
    p_all.add_argument("--manifest", metavar="FILE", help="manifest.json 路径（用于 R-10 版本比对）")
    p_all.add_argument("--json", action="store_true", help="JSON 格式输出")

    # rules 子命令
    subparsers.add_parser("rules", help="列出所有审查规则")

    args = parser.parse_args()

    if args.command == "audit":
        cmd_audit(args)
    elif args.command == "audit-all":
        cmd_audit_all(args)
    elif args.command == "rules":
        cmd_rules()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
