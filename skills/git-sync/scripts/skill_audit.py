#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit.py — SKILL.md 规范化审查工具 (v1.0.0)
集成到 git-sync 流程，在同步前自动检查 SKILL.md 合规性。

基于 SKILL.md 标准化规范草案 v0.1 的 R-01~R-10 规则。
支持独立运行（CLI）和被 git-sync.sh 调用（--json 模式）。

用法:
    python skill_audit.py audit <skill_dir> [--json] [--manifest-version VER]
    python skill_audit.py audit-all <skills_dir> [--manifest FILE] [--json]
    python skill_audit.py rules                          # 列出所有规则
"""

import sys
import os
import re
import json
import argparse

# ── 规则定义 (R-01 ~ R-10) ──────────────────────────────────────

RULES = [
    {
        "id": "R-01",
        "name": "Frontmatter 存在性",
        "severity": "ERROR",
        "check": "存在 YAML frontmatter（--- 包裹）",
        "method": "regex_frontmatter_exists",
    },
    {
        "id": "R-02",
        "name": "name 字段",
        "severity": "ERROR",
        "check": "frontmatter 含 name 字段",
        "method": "yaml_has_name",
    },
    {
        "id": "R-03",
        "name": "version 字段 (SemVer)",
        "severity": "ERROR",
        "check": "frontmatter 含 version 字段且符合 SemVer",
        "method": "yaml_has_semver_version",
    },
    {
        "id": "R-04",
        "name": "description 字段",
        "severity": "ERROR",
        "check": "frontmatter 含 description 字段",
        "method": "yaml_has_description",
    },
    {
        "id": "R-05",
        "name": "name 与目录名一致",
        "severity": "WARN",
        "check": "frontmatter name 与目录名一致",
        "method": "name_matches_dirname",
    },
    {
        "id": "R-06",
        "name": "正文含一级标题",
        "severity": "WARN",
        "check": "正文含 # 开头的一级标题",
        "method": "body_has_h1",
    },
    {
        "id": "R-07",
        "name": "触发条件章节",
        "severity": "WARN",
        "check": "正文含 ## 触发条件 或同义章节标题",
        "method": "body_has_trigger_section",
    },
    {
        "id": "R-08",
        "name": "核心能力章节",
        "severity": "WARN",
        "check": "正文含核心功能/能力/概述章节",
        "method": "body_has_core_section",
    },
    {
        "id": "R-09",
        "name": "工作流程/使用方式章节",
        "severity": "WARN",
        "check": "正文含工作流/使用方式/Workflow 章节",
        "method": "body_has_workflow_section",
    },
    {
        "id": "R-10",
        "name": "version 与 manifest 一致",
        "severity": "WARN",
        "check": "SKILL.md 中 version 与 manifest.json 记录一致",
        "method": "version_matches_manifest",
    },
]

# 同义章节关键词映射
TRIGGER_KEYWORDS = ["触发条件", "触发场景", "适用场景", "触发"]
CORE_KEYWORDS = ["核心功能", "核心能力", "概述", "核心概念", "Overview", "技能概述"]
WORKFLOW_KEYWORDS = ["工作流程", "使用方式", "Workflow", "完整执行流程", "核心指令"]


# ── 轻量 YAML 解析器（零依赖） ──────────────────────────────────

def parse_simple_yaml_frontmatter(text):
    """从 Markdown 文本中提取并解析 YAML frontmatter。
    返回 (dict, body_text) 或 (None, text) 如果没有 frontmatter。"""
    if not text.startswith("---"):
        return None, text

    lines = text.split("\n", 1)
    rest = lines[1] if len(lines) > 1 else ""

    end_idx = rest.find("\n---")
    if end_idx == -1:
        return None, text

    fm_text = rest[:end_idx]
    body = rest[end_idx + 4:]

    result = {}
    current_key = None

    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if stripped.startswith("- ") and current_key:
            arr_key = current_key
            if arr_key not in result or not isinstance(result.get(arr_key), list):
                existing = result.get(arr_key, "")
                if isinstance(existing, str) and existing:
                    result[arr_key] = [existing]
                else:
                    result[arr_key] = []
            result[arr_key].append(stripped[2:].strip().strip("'\""))
            continue

        colon_idx = stripped.find(":")
        if colon_idx > 0:
            key = stripped[:colon_idx].strip()
            val = stripped[colon_idx + 1:].strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if inner:
                    result[key] = [item.strip().strip("'\"") for item in inner.split(",")]
                else:
                    result[key] = []
            elif val:
                result[key] = val
            current_key = key

    return result, body


# ── 审查方法实现 ────────────────────────────────────────────────

def regex_frontmatter_exists(filepath, content, fm, body, **kw):
    passed = fm is not None
    return {"passed": passed,
            "detail": "发现 YAML frontmatter" if passed else "缺少 YAML frontmatter"}


def yaml_has_name(filepath, content, fm, body, **kw):
    has_name = fm is not None and "name" in fm
    return {"passed": has_name,
            "detail": f"name = {fm['name']}" if has_name else "缺少 name 字段"}


def yaml_has_semver_version(filepath, content, fm, body, **kw):
    has_ver = fm is not None and "version" in fm
    if not has_ver:
        return {"passed": False, "detail": "缺少 version 字段"}
    ver = str(fm["version"])
    semver_ok = bool(re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$', ver))
    return {"passed": semver_ok,
            "detail": f"version = {ver}" + (" ✓" if semver_ok else " ✗ 不符合 SemVer")}


def yaml_has_description(filepath, content, fm, body, **kw):
    has_desc = fm is not None and "description" in fm
    dv = str(fm.get("description", ""))[:60]
    return {"passed": has_desc,
            "detail": f"description = \"{dv}\"" if has_desc else "缺少 description 字段"}


def name_matches_dirname(filepath, content, fm, body, dirname=None, **kw):
    if fm is None or "name" not in fm:
        return {"passed": False, "detail": "无法检查：无 frontmatter/name", "skip": True}
    if not dirname:
        return {"passed": True, "detail": "跳过：未提供目录名", "skip": True}
    matched = fm["name"] == dirname
    return {"passed": matched,
            "detail": f"name({fm['name']}) {'==' if matched else '!='} dirname({dirname})"}


def body_has_h1(filepath, content, fm, body, **kw):
    m = re.search(r'^# ', body, re.MULTILINE)
    return {"passed": m is not None,
            "detail": f"发现一级标题: {m.group(0).strip()}" if m else "未找到一级标题 (# )"}


def _section_exists(body, keywords, label):
    """通用：检查是否包含任一关键词的 ## 级标题"""
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("## "):
            title = s[3:].strip()
            for kw in keywords:
                if kw.lower() in title.lower():
                    return True, f"发现章节: {title}"
    return False, f"未找到 [{label}] 章节（同义词: {', '.join(keywords)}）"


def body_has_trigger_section(filepath, content, fm, body, **kw):
    ok, detail = _section_exists(body, TRIGGER_KEYWORDS, "触发条件")
    return {"passed": ok, "detail": detail}


def body_has_core_section(filepath, content, fm, body, **kw):
    ok, detail = _section_exists(body, CORE_KEYWORDS, "核心能力")
    return {"passed": ok, "detail": detail}


def body_has_workflow_section(filepath, content, fm, body, **kw):
    ok, detail = _section_exists(body, WORKFLOW_KEYWORDS, "工作流程")
    return {"passed": ok, "detail": detail}


def version_matches_manifest(filepath, content, fm, body, manifest_version=None, **kw):
    if manifest_version is None:
        return {"passed": True, "detail": "跳过：未提供 manifest 版本号", "skip": True}
    if fm is None or "version" not in fm:
        return {"passed": False, "detail": "无 frontmatter/version，无法比对", "skip": True}
    matched = str(fm["version"]) == str(manifest_version)
    return {"passed": matched,
            "detail": f"SKILL.md({fm['version']}) {'==' if matched else '!='} manifest({manifest_version})"}


# 方法分派表
METHOD_MAP = {
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
}


def audit_skill(skill_dir, manifest_version=None):
    """审查单个 skill 目录中的 SKILL.md。

    Args:
        skill_dir: skill 目录路径
        manifest_version: manifest.json 中记录的版本号（用于 R-10）

    Returns:
        dict: 完整审查结果
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    dirname = os.path.basename(os.path.normpath(skill_dir))

    # 检查文件是否存在
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

        if skipped:
            skip_count += 1
        elif passed:
            pass_count += 1
        elif rule["severity"] == "ERROR":
            error_count += 1
        else:
            warn_count += 1

    fail_count = error_count + warn_count
    total = len(results)

    # 综合判定
    if error_count > 0:
        verdict = f"FAIL ({error_count} ERROR{', ' + str(warn_count) + ' WARN' if warn_count > 0 else ''})"
    elif warn_count > 0:
        verdict = f"WARN ({warn_count} WARN)"
    else:
        verdict = "PASS"

    return {
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

    if verbose:
        lines.append("")
        lines.append(f"{'规则ID':<8} {'严重度':<7} {'状态':<6} 详情")
        lines.append(f"{'-'*8}-{'-'*7}-{'-'*6}-{'-'*30}")
        for res in r["results"]:
            status = "✅" if res["passed"] else ("⏭️" if res["skipped"] else ("🔴" if res["severity"]=="ERROR" else "🟡"))
            sev = res["severity"][0] if res["severity"] else "?"
            lines.append(f"{res['rule_id']:<8} {sev:<7} {status:<6} {res['detail']}")

    return "\n".join(lines)


# ── CLI 命令处理 ─────────────────────────────────────────────────

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

    result = audit_skill(skill_dir, manifest_version=args.manifest_version)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))

    # 退出码：纯警告模式 — 始终返回 0，不阻断调用方流程
    # ERROR 和 WARN 仅在报告中体现严重度差异，不影响退出码
    # 调用方（如 git-sync.sh）可根据 summary.errors/summary.warns 自行决定行为
    # sys.exit(0)  # 显式注释：默认退出码即为 0，无需显式调用


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
            print(format_result := format_report(r, verbose=False))
            print()

        # 仅汇总行
        print(f"\n{'='*60}")
        print("  详细逐项结果:")
        print(f"{'='*60}")
        for r in all_results:
            if "error" not in r:
                print(format_report(r, verbose=True))
                print()


def main():
    parser = argparse.ArgumentParser(
        description="SKILL.md 规范化审查工具 (R-01~R-10)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python skill_audit.py audit ~/.workbuddy/skills/git-sync
  python skill_audit.py audit ~/.workbuddy/skills/svg-composer --json
  python skill_audit.py audit-all ~/.workbuddy/skills --manifest manifest.json
  python skill_audit.py rules
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # audit 子命令
    p_audit = subparsers.add_parser("audit", help="审查单个 skill")
    p_audit.add_argument("skill_dir", help="skill 目录路径")
    p_audit.add_argument("--json", action="store_true", help="JSON 格式输出")
    p_audit.add_argument("--manifest-version", metavar="VER", help="manifest 中记录的版本号（用于 R-10）")

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
