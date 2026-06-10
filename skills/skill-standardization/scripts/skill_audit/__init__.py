#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
"""
skill_audit package — SKILL.md 规范化审查工具 v2.25.0

支持 R-01~R-25 规则审查，独立审计工具。

用法:
    python -m skill_audit audit <skill_dir> [--json] [--manifest-version VER]
    python -m skill_audit audit-all <skills_dir> [--manifest FILE] [--json]
    python -m skill_audit rules
"""

import warnings
# 临时移除过滤，捕获 SyntaxWarning 来源
# warnings.filterwarnings("ignore", category=SyntaxWarning, message=r'.*invalid escape sequence.*')

import os
import re
import sys
import json
import argparse
from pathlib import Path

# ── [GBK 兼容] 强制 stdout 使用 UTF-8，防止 Windows 终端 emoji print 崩溃 ──
if sys.stdout.encoding and sys.stdout.encoding.upper() not in ('UTF-8', 'UTF8'):
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.upper() not in ('UTF-8', 'UTF8'):
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1, errors='replace')

# ── 导入子模块 ─────────────────────────────────────────────
from .utils import (
    _fmt_frontmatter_value, RULES, TRIGGER_KEYWORDS, CORE_KEYWORDS, WORKFLOW_KEYWORDS,
    ARTIFACT_DIR_NAMES, _KNOWN_STANDARD_DIRS, _ARTIFACT_DIR_CLASSIFY,
    _ARTIFACT_EXTS_COMPREHENSIVE, _ARTIFACT_DIR_PATTERN,
    _ARTIFACT_WRITE_PATTERNS, _HARDCODED_PATH_RE, _PATH_EXCLUDE_RE,
    _is_hardcoded_path, parse_simple_yaml_frontmatter,
    _find_skills_dir,
)
from .frontmatter_checker import (
    regex_frontmatter_exists, yaml_has_name, yaml_has_semver_version,
    yaml_has_description, name_matches_dirname, version_matches_manifest,
    check_meta_json_completeness,
    regex_frontmatter_and_meta,
)
from .structure_checker import (
    body_has_h1, body_has_trigger_section, body_has_core_section,
    body_has_workflow_section,
    body_has_antipattern_section, body_has_faq_section,
    body_check_writing_standards,
    body_has_progressive_loading_explicit,
    check_doc_code_consistency,
    check_changelog_progressive,
    body_check_document_format,
)
from .artifact_checker import (
    check_artifact_paths, check_external_data_dir,
    fix_external_data_dir,
)
from .permission_checks import (
    check_sensitive_access_declaration, check_critical_write_declaration,
    check_authorization_present, check_permission_weight_explained,
    check_progressive_loading_forced,
)
from .data_dir_checker import (
    check_data_dir_compliance, fix_data_dir_compliance,
)
from .fix import apply_fix, list_fixable

# ── 方法分派表 ─────────────────────────────────────────────
METHOD_MAP = {
    "check_external_data_dir": check_external_data_dir,
    "regex_frontmatter_exists": regex_frontmatter_exists,
    "regex_frontmatter_and_meta": regex_frontmatter_and_meta,
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
    "check_data_dir_compliance": check_data_dir_compliance,
    "check_doc_code_consistency": check_doc_code_consistency,
    "check_changelog_progressive": check_changelog_progressive,
    "check_meta_json_completeness": check_meta_json_completeness,
    "body_check_document_format": body_check_document_format,
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
    _AUDIT_CONTROL_FIELDS = {
        "writing_standards", "artifact_paths",
        "antipattern_progressive", "faq_progressive",
        "progressive_loading_explicit",
        "h1", "section_trigger", "section_core", "section_workflow",
        "antipattern_reference", "faq_reference",
        "frontmatter_fields", "meta_json",
    }
    for fix in fixes:
        if "key" not in fix:
            continue
        key = fix["key"]
        if key in _AUDIT_CONTROL_FIELDS:
            continue
        if "value" not in fix:
            continue  # 结构性修复（如删除/创建文件），不走 frontmatter 合并
        val = fix["value"]
        fm[key] = val
        applied.append(f"{key}: {val} ({fix.get('reason', '')})")

    # 重新组装 frontmatter + body（过滤审计控制字段）
    import io
    buf = io.StringIO()
    buf.write("---\n")
    for k in _AUDIT_CONTROL_FIELDS:
        fm.pop(k, None)
    for k, v in fm.items():
        if isinstance(v, bool):
            val_str = 'true' if v else 'false'
            buf.write(f"{k}: {val_str}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {_fmt_frontmatter_value(v)}\n")
        else:
            buf.write(f"{k}: {_fmt_frontmatter_value(v)}\n")
    buf.write("---\n")
    buf.write(body.lstrip("\n"))

    # 使用 safe_io 原子写入 + 自动备份
    from ..safe_io import safe_write
    safe_write(skill_md, buf.getvalue(), backup=True)

    return applied


def audit_skill(skill_dir, manifest_version=None, _fix_applied=False, progress_file=None):
    """
    审查单个 skill 目录中的 SKILL.md。_fix_applied 防止无限递归。

    如果传了 _progress_file，审计结束后自动更新 .progress.md。
    """
    # 先把 skill_dir 转成绝对路径，防止 '.' 等相对路径导致 dirname 异常
    skill_dir = os.path.abspath(skill_dir)
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

        try:
            result = method_fn(
                filepath=skill_md,
                content=content,
                fm=fm,
                body=body,
                dirname=dirname,
                skill_dir=skill_dir,
                manifest_version=manifest_version,
            )
        except Exception as _e:
            import traceback
            traceback.print_exc()
            result = {"passed": False, "detail": f"规则 {rule['id']} 执行异常: {_e}"}
        # 兼容 dict 和 tuple 两种返回格式
        if isinstance(result, dict):
            passed = result.get("passed", False)
            skipped = result.get("skip", False)
        elif isinstance(result, (tuple, list)) and len(result) >= 1:
            # 旧格式: (passed, details, fixable)
            passed = bool(result[0]) if len(result) > 0 else False
            skipped = result[2].get("skip", False) if len(result) > 2 and isinstance(result[2], dict) else False
            # 将 tuple 转为 dict 以便后续处理
            detail = result[1] if len(result) > 1 else ""
            fix = result[2] if len(result) > 2 and isinstance(result[2], dict) else None
            # data_dir_checker 返回 (passed, details, fixable_list)，fixable 为 list
            if fix is None and len(result) > 2 and isinstance(result[2], list) and len(result[2]) > 0:
                fix = {"key": "data_dir_compliance", "fixable_list": result[2], "value": True}
            result = {"passed": passed, "detail": detail, "fix": fix}
        else:
            passed = False
            skipped = False

        entry = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "severity": rule["severity"],
            "passed": passed,
            "skipped": skipped,
            "detail": result.get("detail", ""),
        }
        if result.get("ctx_lines"):
            entry["ctx_lines"] = result["ctx_lines"][:8]  # 最多8行上下文
        # 新增：附带修正建议（供 LLM 参考）
        if not passed and not skipped:
            if result.get("fix"):
                entry["fix"] = result["fix"]
            if result.get("suggestion"):
                entry["suggestion"] = result["suggestion"]
        results.append(entry)

        # 收集 fix 建议
        if not passed and not skipped and result.get("fix"):
            fixes.append(result["fix"])

        # 误报不计入 WARN/ERROR 统计
        is_false_positive = not passed and not skipped and _reclassify_false_positive(entry)
        if is_false_positive:
            pass_count += 1
        elif skipped:
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


def _expand_fail_entries(remaining):
    """
    将 FAIL 项展开为颗粒度一致的可编号条目。
    每条包含独立 ID、规则 ID、严重度、问题描述、修复指引、上下文行。

    特别处理 R-25：将 WARN(N) 中的 C-XX 子项展开为独立条目，
    每个子项带有自己的问题描述和对应的 → LLM执行：修复指引。
    非 R-25 规则保持原样输出。
    """
    entries = []
    eid = 0
    # 匹配 C-XX 子项：C-07, C-10, C-11... 及其内容和修复指引
    # 子项之间以 ; 分隔。部分子项有 C-XX 前缀，部分无前缀（续前项）
    # 格式示例：C-10: xxx; C-17: yyy → LLM执行：zzz; 【续】www → LLM执行：vvv
    sub_pattern = re.compile(
        r'(?:'
        r'(C-\d+):\s*(.*?)(?:\s*→\s*LLM执行[：:]([^;]*))?'
        r'|'
        r';\s*(【[^】]+】.*?)(?:\s*→\s*LLM执行[：:]([^;]*))?'
        r')'
        r'(?=;\s*(?:C-\d|【)|\s*C-\d|$)'
    )

    for res in remaining:
        rid = res.get('rule_id', '')
        detail = res.get('detail', '')
        sev = res.get('severity', 'WARN')
        ctx = res.get('ctx_lines', [])

        if rid == 'R-25':
            # 从 detail 中提取 WARN(N) 块
            warn_match = re.search(r'🟡\s*WARN\(\d+\):\s*(.+)', detail)
            if warn_match:
                sub_text = warn_match.group(1)
                # 逐个匹配子项（含 C-XX 前缀项和无前缀续项）
                last_cid = None  # 记录最近 C-XX，给续项用
                for sm in sub_pattern.finditer(sub_text):
                    eid += 1
                    c_id = sm.group(1)       # 如 "C-17"，续项为 None
                    if c_id:
                        last_cid = c_id
                        problem = sm.group(2).strip()
                        fix = sm.group(3)
                    else:
                        # 续项：无 C-XX 前缀，使用最近一个 C-XX + 序号
                        suffix = chr(ord('a') + [m.group(1) for m in sub_pattern.finditer(sub_text[:sm.start()])].count(None))
                        c_id = f'{last_cid}{suffix}'
                        problem = sm.group(4).strip()
                        fix = sm.group(5)
                    if fix:
                        fix = fix.strip()
                    else:
                        fix = ''
                    entries.append({
                        'id': str(eid),
                        'rule_id': f'R-25 ({c_id})',
                        'severity': sev,
                        'problem': f'{c_id}: {problem}',
                        'fix': f'R-25 ({c_id}): {problem} → LLM执行：{fix}' if fix else '',
                        'ctx_lines': ctx,
                    })
            else:
                # fallback: 无法解析 WARN 格式，整条输出
                eid += 1
                detail_clean = re.sub(r'\s*→\s*LLM执行[：:][^;]*', '', detail)
                entries.append({
                    'id': str(eid),
                    'rule_id': rid,
                    'severity': sev,
                    'problem': detail_clean,
                    'fix': detail,
                    'ctx_lines': ctx,
                })
        else:
            # 非 R-25：整条规则作为一个条目
            eid += 1
            # 分离问题描述和修复指引
            detail_clean = re.sub(r'\s*→\s*LLM执行[：:][^;]*', '', detail)
            detail_clean = re.sub(r'\s*💡\s*建议修正[：:].*', '', detail_clean)
            # 提取修复指引（💡 建议修正 或 → LLM执行：）
            fix = detail
            entries.append({
                'id': str(eid),
                'rule_id': rid,
                'severity': sev,
                'problem': detail_clean.strip(),
                'fix': fix,
                'ctx_lines': ctx,
            })

    return entries


def _reclassify_false_positive(res):
    """检测已知误报模式，仅用于报告格式化时标记 ⓘ 排除标记。
    
    注意：--verify 模式已关闭白名单预筛，LLM 需要逐条审查所有 FAIL 项。
    此函数仅用于报告显示时的视觉标记（ⓘ），不影响 exit code 和 LLM 决策。
    """
    detail = str(res.get("detail", ""))
    rule = res.get("rule_id", "")
    # 系统工具名被误判为函数引用
    if "lualatex" in detail and "函数/类名" in detail:
        return True
    # examples.md 中的示例输出路径（[CREATE] SKILL.md → ./hello-world/SKILL.md）
    if "examples.md" in detail and ("→" in detail or "[CREATE]" in detail or "[B-0" in detail):
        return True
    # architecture.md 中的分类说明（.py/.sh/.bat → move → scripts/）
    if "architecture.md" in detail and "→ move →" in detail:
        return True
    # R-23 step 3 示例脚本引用（SKILL.md 中的用法示例路径，非真实文件）
    if rule == "R-23" and "但文件不存在（期望相对路径如" in detail:
        return True
    # R-23 中文语境下的文件引用（如 "（参见 search-integration.md）" 是文档引用标记，非真实文件路径）
    # TODO: 根因已修（_tree_scanner.py 加了中文文字/括号过滤），此规则保留作为双保险
    if rule == "R-23" and "目录树显示" in detail and "（" in detail and "但文件不存在" in detail:
        return True
    # R-20 如果仅包含 R-23 问题则同步标记
    if rule == "R-20" and "R-23" in detail and "但文件不存在" in detail:
        return True
    # R-20 写作规范 WARN：术语偏好（"设置" vs "配置"）、模糊表述（"可能"等）属于风格建议，
    # 不影响功能且无法穷举修复，标记为已知误报
    if rule == "R-20" and ("术语不一致" in detail or "模糊表述" in detail):
        return True
    # JSON 示例中的文件路径（如 component-spec.md 的 manifest.json schema 展示）
    if '"file": "' in detail:
        return True
    # 使用示例中的占位符路径（如 my_package 等通用占位符名）
    if 'my_package' in detail:
        return True
    return False


def format_report(audit_result, verbose=True):
    """格式化人类可读的审查报告"""
    lines = []
    r = audit_result

    if "error" in r:
        lines.append(f"[X] {r['skill']}: {r['error']}")
        return "\n".join(lines)

    lines.append(f"{'='*55}")
    lines.append(f"  审查结果: {r['skill']} — {r['verdict']}")
    lines.append(f"{'='*55}")

    s = r["summary"]
    lines.append(f"  总计: {s['total']} | 通过: {s['pass']} | 失败: {s['fail']} | 跳过: {s['skip']}")

    # 显示自动修正信息
    if r.get("fixed"):
        lines.append(f"\n{'─'*55}")
        lines.append("  [!]  已自动修正以下 frontmatter 字段：")
        for fix_desc in r["fixed"]:
            lines.append(f"    • {fix_desc}")
        if r.get("re_audit"):
            lines.append("  （已重新审计，确保修正后通过）")
        lines.append(f"{'─'*55}")

    if verbose:
        # 预读技能目录文件内容，用于自动上下文提取
        _skill_dir = r.get("path", "")
        _file_cache = {}

        def _get_file_lines(filepath):
            if filepath in _file_cache:
                return _file_cache[filepath]
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        _file_cache[filepath] = f.read().split('\n')
                except Exception:
                    _file_cache[filepath] = []
            else:
                _file_cache[filepath] = []
            return _file_cache[filepath]

        lines.append("")
        lines.append(f"{'规则ID':<8} {'严重度':<7} {'状态':<6} 详情")
        lines.append(f"{'-'*8}-{'-'*7}-{'-'*6}-{'-'*30}")
        for res in r["results"]:
            # 已知误报检测：LLM 可确定的 false positive 降级为 ⓘ
            if _reclassify_false_positive(res):
                status = "ⓘ"
                sev = "排除"
            else:
                status = "[OK]" if res["passed"] else ("⏭️" if res["skipped"] else ("[ERROR]" if res["severity"]=="ERROR" else "[WARN]"))
                sev = res["severity"][0] if res["severity"] else "?"
            lines.append(f"{res['rule_id']:<8} {sev:<7} {status:<6} {res['detail']}")
            # 详细上下文行：优先使用检查器返回的 ctx_lines，否则自动从 detail 中的路径提取
            ctx = res.get("ctx_lines") or []
            if not ctx and _skill_dir:
                _detail_str = res.get("detail", "")
                if isinstance(_detail_str, str):
                    for _m in re.finditer(r'([^\s]+\.(?:md|py|tex|txt|json|yaml|yml|cfg|ini|toml)):(\d+)', _detail_str):
                        _fp = _m.group(1)
                        _ln = int(_m.group(2))
                        for _base in ('', _skill_dir):
                            _full = os.path.join(_base, _fp) if _base else _fp
                            _ls = _get_file_lines(_full)
                            if _ls:
                                _start = max(0, _ln - 3)
                                _end = min(len(_ls), _ln + 2)
                                _ctx = '\n'.join(f"    {_fp}:{i} {_ls[i-1]}" for i in range(_start + 1, _end + 1))
                                ctx.append(f"  {_fp}:{_ln} 附近:\n{_ctx}")
                                break
            if ctx:
                for cl in ctx[:8]:
                    lines.append(f"       {cl}")
            # 修正建议（供 LLM 参考）
            if not res["passed"] and not res["skipped"] and res.get("fix"):
                fix = res["fix"]
                if fix.get("operation"):
                    lines.append(f"    💡 建议修正：{fix['operation']}")
                if fix.get("location"):
                    lines.append(f"    [search] 位置：{fix['location']}")
                if fix.get("reason"):
                    lines.append(f"    💬 原因：{fix['reason']}")

    # 固定输出：提示可用 --fix 自动修复
    lines.append("")
    lines.append(f"{"─"*55}")
    lines.append("  🛠️ 提示：发现可修复问题时，优先运行以下命令自动修复：")
    lines.append("    python -m skill_audit audit <skill_dir> --fix")
    lines.append("  （模型请勿手动修改，优先使用 --fix 自动修复）")
    lines.append(f"{"─"*55}")

    return "\n".join(lines)


def cmd_create_template():
    """
    输出所有规则的创建模板（供 LLM 创建技能时参考）。
    包含：规则 ID、严重度、检查内容、是否可自动修正、创建模板。
    """
    print(f"\n{'='*70}")
    print("  skill-standardization 创建模板（供 LLM 参考）")
    print(f"{'='*70}\n")

    for rule in RULES:
        sev_mark = "[ERROR]" if rule["severity"] == "ERROR" else "[WARN]"
        fixable_mark = "[OK] 可自动修正" if rule.get("fixable") else "[X] 需手动修正"
        print(f"{'─'*70}")
        print(f"  {rule['id']} {sev_mark} [{rule['severity']}] {rule['name']}")
        print(f"  检查：{rule['check']}")
        print(f"  修正：{fixable_mark}")
        tmpl = rule.get("create_template", "")
        if tmpl:
            # 把 \n 转换成实际换行，并缩进
            tmpl_lines = tmpl.split("\\n")
            print(f"  创建模板：")
            for ln in tmpl_lines:
                print(f"    {ln}")
        print()

    print(f"{'='*70}")
    print(f"  共 {len(RULES)} 条规则")
    print(f"{'='*70}\n")
    print("用法：")
    print("  python -m skill_audit create-template")
    print("  python -m skill_audit create-template --json  （JSON 格式）")
    print()


def cmd_rules():
    """列出所有审查规则"""
    print(f"\n{'ID':<8} {'严重度':<8} 名称  检查内容")
    print("-" * 65)
    for rule in RULES:
        sev_mark = "[ERROR]" if rule["severity"] == "ERROR" else "[WARN]"
        print(f"  {rule['id']:<6} {sev_mark} {rule['severity']:<6} {rule['name']: <20} {rule['check']}")
    print(f"\n共 {len(RULES)} 条规则")


def _do_bump(skill_dir, bump_type='fix', desc='自动升级', skip_changelog=False):
    """版本号三端更新核心逻辑 — 供 --fix 和 bump 子命令复用
    参数 skip_changelog=True 时，仅更新 SKILL.md 和 _meta.json 的版本号，不写 changelog。
    changelog 由 LLM 根据 fix 详情和审计报告动态翻译生成。
    """
    import os, sys, json, re, datetime

    # 映射 fix/feature/breaking → patch/minor/major
    type_map = {'fix': 'patch', 'feature': 'minor', 'breaking': 'major'}
    vm_bump_type = type_map.get(bump_type, 'patch')

    meta_path = os.path.join(skill_dir, '_meta.json')
    if not os.path.isfile(meta_path):
        raise FileNotFoundError(
            f"未找到 `_meta.json`（位置：{meta_path}）。\n"
            f"  原因：目标目录可能不是标准 skill 结构，缺少技能元数据文件。\n"
            f"  解决：确认目标路径是一个完整的 skill 目录（含 SKILL.md 和 _meta.json），\n"
            f"        或使用 `python -m scripts.skill_builder create <name>` 创建新 skill。"
        )

    with open(meta_path, 'r', encoding='utf-8') as f:
        current_version = str(json.load(f).get('version', '0.0.0'))

    parts = current_version.split('.')
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if bump_type == 'fix':
        new_version = f"{major}.{minor}.{patch + 1}"
    elif bump_type == 'feature':
        new_version = f"{major}.{minor + 1}.0"
    else:
        new_version = f"{major + 1}.0.0"

    today = datetime.date.today().isoformat()

    # 用已有 VersionManager 更新 SKILL.md + _meta.json
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from skill_builder.version_manager import VersionManager
        VersionManager.bump_version(skill_dir, vm_bump_type)
    except Exception:
        # 兜底：直接写
        meta_path = os.path.join(skill_dir, '_meta.json')
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        meta['version'] = new_version
        from ..safe_io import safe_write
        safe_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2) + '\n', backup=True)
        skill_md = os.path.join(skill_dir, 'SKILL.md')
        with open(skill_md, 'r', encoding='utf-8') as f:
            md_content = f.read()
        md_content = re.sub(
            r'^(version:\s*)\d+\.\d+\.\d+',
            rf'\g<1>{new_version}',
            md_content, count=1, flags=re.MULTILINE
        )
        safe_write(skill_md, md_content, backup=True)

    # 更新 changelog（--fix 模式跳过，由 LLM 根据审计结果动态翻译生成）
    if not skip_changelog:
        cl_entry = f"## [{new_version}] - {today}\n\n### 修复\n- {desc}\n"
        cl_path = os.path.join(skill_dir, 'references', 'changelog.md')
        if os.path.isfile(cl_path):
            with open(cl_path, 'r', encoding='utf-8') as f:
                cl_old = f.read()
        else:
            cl_old = ''
            os.makedirs(os.path.dirname(cl_path), exist_ok=True)
        new_cl = cl_entry + '\n---\n\n' + cl_old if cl_old else cl_entry
        os.makedirs(os.path.dirname(cl_path), exist_ok=True)
        from ..safe_io import safe_write
        safe_write(cl_path, new_cl, backup=True)


def cmd_audit(args):
    """审查单个 skill 目录"""
    # 强制 UTF-8 输出（Windows 终端兼容）
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    skill_dir = args.skill_dir
    if not os.path.isdir(skill_dir):
        print(f"[X] 目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    # 纯 --show-fix 模式：跳过审计，直接读取 fix_map 输出修复指引
    if getattr(args, 'show_fix', None) and not getattr(args, 'verify', False):
        fix_map_path = os.path.join(
            os.path.dirname(skill_dir), '.standardization',
            os.path.basename(skill_dir), 'data', '.verify_fix_map.json')
        if not os.path.isfile(fix_map_path):
            print(f"[ERROR] 未找到 fix_map 文件（{fix_map_path}），请先运行 --verify")
            sys.exit(1)
        with open(fix_map_path, 'r', encoding='utf-8') as f:
            fix_map = json.load(f)
        ids = [s.strip() for s in args.show_fix.split(',')]
        print(f"\n{'='*55}")
        print(f"  [SHOW-FIX v1] 展示 {len(ids)} 条修复指引")
        print(f"{'─'*55}")
        found_any = False
        for rid in ids:
            fix_text = fix_map.get(rid)
            if fix_text:
                print(f"  [#{rid}] {fix_text}")
                found_any = True
            else:
                print(f"  [#{rid}] (未找到对应修复指引)")
        if not found_any:
            print(f"  (无有效修复指引，请确认 ID 正确或重新运行 --verify)")
        print(f"{'='*55}")
        sys.exit(0)

    # ═══════════════════════════════════════════════════════
    # [强制钩子 1] 蓝皮书前置扫描 — audit 执行前输出技能全貌
    # ═══════════════════════════════════════════════════════
    try:
        from ..skill_inspector import inspect_skill
        print(f"\n{'='*55}")
        print(f"  前置扫描：Skill 蓝皮书")
        print(f"{'='*55}")
        inspect_skill(skill_dir)
        print()
    except ImportError:
        try:
            from scripts.skill_inspector import inspect_skill
            inspect_skill(skill_dir)
            print()
        except ImportError:
            pass

    result = audit_skill(skill_dir, manifest_version=args.manifest_version,
                        progress_file=args.progress_file)

    # 出完整报告（LLM 读取报告中的 FAIL 项，分类：ERROR=真问题保留，其他=误报类）
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))

    # ── 问题分类与真问题强制修复 ──
    # 分类体系：0 ERROR 0 WARN 铁律
    #   ERROR → 未排除则必须 --fix
    #   WARN  → 未排除则必须 --fix
    #   排除  → 已知误报（_reclassify_false_positive），不阻断通过
    #   PASS/SKIP → 通过
    remaining_pre = [res for res in result.get("results", [])
                     if not res.get("passed") and not res.get("skipped")
                     and not _reclassify_false_positive(res)]
    has_fixable = any(r.get("fix") for r in remaining_pre)
    if has_fixable and not args.fix:
        print(f"\n  ⛔ 存在可自动修复的 FAIL — 必须执行 audit --fix 修复后重新验证")
        sys.exit(1)

    # --fix 模式：自动修正所有失败规则的违规
    if args.fix:
        print(f"\n=== 自动修正模式 ===")
        # 收集所有失败规则的 fix key
        fixes_applied = 0
        fix_details = []
        for res in result.get("results", []):
            if not res.get("passed") and res.get("fix"):
                fix_key = res["fix"].get("key")
                if fix_key:
                    try:
                        n = apply_fix(skill_dir, fix_key, **res["fix"])
                        fixes_applied += n
                        fix_details.append(fix_key)
                        print(f"[OK] R-{fix_key}：修正 {n} 处")
                    except Exception as e:
                        print(f"[ERROR] R-{fix_key} 修正失败: {e}")
        if fixes_applied > 0:
            print(f"[OK] 共修正 {fix_details} 处")
            # 版本号 bump（仅更新 SKILL.md + _meta.json，不写 changelog）
            # changelog 由 LLM 根据下方输出的 fix 详情和审计报告动态翻译写入
            try:
                _do_bump(skill_dir, 'fix', '由 LLM 补充实际内容', skip_changelog=True)
                print(f"[OK] 版本号已自动升级（R-03 规则: audit --fix 默认为 PATCH）")
            except Exception as e:
                print(f"[WARN] 版本号自动更新失败（可手动执行 bump 子命令）: {e}")
            # 重新审计
            result = audit_skill(skill_dir, manifest_version=args.manifest_version,
                                progress_file=args.progress_file, _fix_applied=True)
        else:
            # ★ v2.63.0: --fix 执行了但 0 处修正 → 这些 FAIL 不是真可修复
            #   清除其 fix 属性，使其进入 LLM 二段筛查的「误判→放过」流程
            #   而不是无限循环 "存在可自动修复的 FAIL — 必须再跑 --fix"
            for res in result.get("results", []):
                if not res.get("passed") and not res.get("skipped") and res.get("fix"):
                    fix_key = res["fix"].get("key")
                    if fix_key in fix_details:
                        del res["fix"]

        # 出二次审计报告
        if fixes_applied > 0:
            if not args.json:
                print(format_report(result))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))

        # ── 问题分类与真问题强制修复：--fix 后仍有可修复 FAIL 则阻止通过
        remaining = [res for res in result.get("results", [])
                     if not res.get("passed") and not res.get("skipped")
                     and not _reclassify_false_positive(res)]
        has_fixable_after = any(r.get("fix") for r in remaining)
        if has_fixable_after:
            print(f"\n  ⛔ --fix 后仍有可自动修复的 FAIL — 必须再执行 --fix")
            sys.exit(1)

    # --verify 模式：展示所有 FAIL 项（不做白名单预筛），LLM 自行判断误报
    # 铁律 8 分两阶段：(1) 筛选看到的问题 → (2) 凭ID获取对应修复指引
    if getattr(args, 'verify', False):
        remaining = []
        for res in result.get("results", []):
            if not res.get("passed") and not res.get("skipped"):
                remaining.append(res)
        if remaining:
            print(f"\n{'='*55}")
            print(f"  [VERIFY v1] {len(remaining)} 项 FAIL 待筛选，逐条判断真问题/误判")
            print(f"  确认真问题后记下 #ID，运行 --show-fix ID1,ID2 获取修复指引")
            print(f"{'─'*55}")

            # 展开为带 ID 的条目，每条有问题描述 + 对应修复指引
            entries = _expand_fail_entries(remaining)
            fix_map = {}  # id → fix_suggestion

            for e in entries:
                eid = e['id']
                sev = "[ERROR]" if e['severity'] == 'ERROR' else "[WARN]"
                # 输出 [ID] 规则 + 问题描述（不带修复指引）
                print(f"  [#{eid}] {e['rule_id']} {sev} {e['problem']}")
                if e.get('ctx_lines'):
                    for cl in e['ctx_lines'][:6]:
                        print(f"         {cl[:160]}")
                fix_map[eid] = e['fix']

            # 将 fix_map 写入标准化数据目录供 --show-fix 读取
            try:
                fix_map_dir = os.path.join(
                    os.path.dirname(skill_dir), '.standardization',
                    os.path.basename(skill_dir), 'data')
                os.makedirs(fix_map_dir, exist_ok=True)
                fix_map_path = os.path.join(fix_map_dir, '.verify_fix_map.json')
                with open(fix_map_path, 'w', encoding='utf-8') as f:
                    json.dump(fix_map, f, ensure_ascii=False, indent=2)
            except Exception:
                pass  # 写不进去不影响主流程

            print(f"{'─'*55}")
            print(f"  确认真问题后运行： audit <skill_dir> --show-fix ID1,ID2,ID3")
            print(f"{'='*55}")
        else:
            print(f"\n{'='*55}")
            print(f"  [VERIFY] 验证通过：所有未通过项均为误报，达到铁律 0 ERROR 0 WARN 要求")
            print(f"{'='*55}")
        # --verify 和 --show-fix 互斥
        if getattr(args, 'show_fix', None):
            return  # --show-fix 单独处理
        sys.exit(1 if remaining else 0)

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
            print(f"[!]  读取 manifest 失败: {e}", file=sys.stderr)

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


def cmd_fix(args):
    """针对性修复工具（按 fix key 分发）"""
    skill_dir = args.skill_dir
    if not os.path.isdir(skill_dir):
        print(f"[X] 目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    keys = args.key if args.key else None
    dry_run = args.dry_run

    if not keys:
        # 列出所有可用的 fix key
        print("可用修复 key（对应审计规则 R-01~R-23）:")
        for k in list_fixable():
            print(f"  {k}")
        print("\n用法: python -m skill_audit fix <skill_dir> --key <key> [--dry-run]")
        print("      python -m skill_audit fix <skill_dir> --key <key1> <key2> ...")
        return

    total_fixed = 0
    for key in keys:
        try:
            params = {}
            if hasattr(args, 'value') and args.value:
                # 尝试解析 value 为 JSON 或字符串
                try:
                    params["value"] = json.loads(args.value)
                except json.JSONDecodeError:
                    params["value"] = args.value
            if dry_run:
                print(f"[DRY-RUN] R-{key}: 模拟修复...")
                n = apply_fix(skill_dir, key, dry_run=True, **params)
            else:
                n = apply_fix(skill_dir, key, **params)
            total_fixed += n
            print(f"[OK] R-{key}: 修复 {n} 处")
        except Exception as e:
            print(f"[ERROR] R-{key}: {e}")

    if not dry_run and total_fixed > 0:
        # 重新审计
        print(f"\n=== 重新审计 ===")
        result = audit_skill(skill_dir)
        print(format_report(result))


def cmd_bump(args):
    """bump 子命令：一键升级技能版本号三端（遵循 R-03 语义规则）"""
    import os, json, datetime

    skill_dir = os.path.abspath(args.skill_dir)
    dry_run = getattr(args, 'dry_run', False)
    bump_type = getattr(args, 'type', None)
    desc = getattr(args, 'desc', '')

    # 未指定 --type 时显示规则并提示
    if bump_type is None:
        print("R-03 版本号变更语义规则：")
        print("  breaking (MAJOR.0.0) = 架构级重构/破坏性变更/核心引擎重写")
        print("  feature  (x.MINOR.0) = 新增功能/已有功能重构/大面积描述修正/bug修复")
        print("  fix      (x.y.PATCH) = 单处描述修正/参数拼写/路径修正/错别字")
        print()
        bump_type = input("请选择变更类型 [fix/feature/breaking] (默认 feature): ").strip().lower()
        if bump_type not in ('fix', 'feature', 'breaking'):
            bump_type = 'feature'

    meta_path = os.path.join(skill_dir, '_meta.json')
    if not os.path.isfile(meta_path):
        print(f"[ERROR] 未找到 _meta.json: {meta_path}")
        return
    with open(meta_path, 'r', encoding='utf-8') as f:
        current_version = str(json.load(f).get('version', '0.0.0'))

    parts = current_version.split('.')
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        print(f"[ERROR] 无法解析版本号「{current_version}」—— 期望格式如「1.2.3」（三位数字以点分隔）")
        print(f"       请检查 `_meta.json` 和 `SKILL.md` 中的 version 字段是否正确")
        return
    if bump_type == 'fix':
        new_version = f"{major}.{minor}.{patch + 1}"
        rule_note = "PATCH: 单处bug修复/文档错别字/参数拼写(不含新功能,多变更不得打包为PATCH)"
    elif bump_type == 'feature':
        new_version = f"{major}.{minor + 1}.0"
        rule_note = "MINOR: 新增功能/已有功能重构/大面积描述修正"
    else:
        new_version = f"{major + 1}.0.0"
        rule_note = "MAJOR: 架构级重构/破坏性变更/核心引擎重写"

    if dry_run:
        print(f"[DRY-RUN] skill: {os.path.basename(skill_dir)}")
        print(f"  {current_version} → {new_version} ({bump_type}) — {rule_note}")
        return

    _do_bump(skill_dir, bump_type, desc)
    print(f"\n=== 版本号三端更新完成 ===")
    print(f"  skill:          {os.path.basename(skill_dir)}")
    print(f"  版本:           {current_version} → {new_version}")
    print(f"  类型:           {bump_type} — {rule_note}")
    print(f"  规则:           R-03（SemVer + 变更语义）")
    print(f"  SKILL.md:       ✅ version={new_version}")
    print(f"  _meta.json:     ✅ version={new_version}")
    print(f"  changelog.md:   ✅ 已插入 v{new_version} 条目")


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
    description="SKILL.md 规范化审查工具 (R-01~R-23)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m skill_audit audit ~/.workbuddy/skills/<skill-name>
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
    p_audit.add_argument("--fix", action="store_true", help="自动修正 R-11/R-12 违规（修改脚本和 _meta.json）")
    p_audit.add_argument("--verify", action="store_true", help="强制验证：有非误报未通过项则 exit(1)，确保铁律 0 ERROR 0 WARN 强制执行")
    p_audit.add_argument("--show-fix", metavar="IDS", help="仅展示指定 #ID 的修复指引（先运行 --verify 获取 ID 列表）")

    # audit-all 子命令
    p_all = subparsers.add_parser("audit-all", help="批量审查所有 skill")
    p_all.add_argument("skills_dir", help="skills 根目录")
    p_all.add_argument("--manifest", metavar="FILE", help="manifest.json 路径（用于 R-10 版本比对）")
    p_all.add_argument("--json", action="store_true", help="JSON 格式输出")

    # rules 子命令
    subparsers.add_parser("rules", help="列出所有审查规则")

    # create-template 子命令（v2.29.0 新增）
    p_template = subparsers.add_parser("create-template", aliases=["template"],
                                      help="输出所有规则的创建模板（供 LLM 创建技能时参考）")
    p_template.add_argument("--json", action="store_true", help="JSON 格式输出")

    # fix 子命令（v2.37.0 新增）
    p_fix = subparsers.add_parser("fix", help="针对性修复工具（按 fix key 分发）")
    p_fix.add_argument("skill_dir", help="skill 目录路径")
    p_fix.add_argument("--key", help="修复 key（如 name、section_trigger 等，可多次指定或留空列出所有可用 key）", nargs="*")
    p_fix.add_argument("--value", help="修复参数值（如 value=true）")
    p_fix.add_argument("--dry-run", action="store_true", help="仅模拟，不实际修改")

    # bump 子命令（v2.38.15 新增）
    p_bump = subparsers.add_parser("bump", help="自动升级技能版本号三端（SKILL.md + _meta.json + changelog）",
        epilog="""版本号变更规则（R-03）：
  breaking (MAJOR.0.0) = 架构级重构/破坏性变更/核心引擎重写    例: 2.3.4 → 3.0.0
  feature  (x.MINOR.0) = 新增功能/已有功能重构/大面积描述修正   例: 2.3.4 → 2.4.0
  fix      (x.y.PATCH) = 单处描述修正/参数拼写/路径修正/错别字  例: 2.3.4 → 2.3.5
不确认时选 feature（MINOR），严禁随意使用 MAJOR。
架构级重构（如模块系统替换、核心引擎重写）才使用 breaking。""")
    p_bump.add_argument("skill_dir", help="skill 目录路径")
    p_bump.add_argument("--type", choices=["fix", "feature", "breaking"], default=None,
                        help="变更类型（默认交互选择）")
    p_bump.add_argument("--desc", required=True, help="本次变更描述（将写入 changelog）")
    p_bump.add_argument("--dry-run", action="store_true", help="仅预览，不实际修改")

    args = parser.parse_args()

    if args.command == "audit":
        cmd_audit(args)
    elif args.command == "audit-all":
        cmd_audit_all(args)
    elif args.command == "rules":
        cmd_rules()
    elif args.command == "fix":
        cmd_fix(args)
    elif args.command == "bump":
        cmd_bump(args)
    elif args.command in ("create-template", "template"):
        if hasattr(args, "json") and args.json:
            import json
            output = []
            for rule in RULES:
                output.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "check": rule["check"],
                    "fixable": rule.get("fixable", False),
                    "create_template": rule.get("create_template", ""),
                })
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            cmd_create_template()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
