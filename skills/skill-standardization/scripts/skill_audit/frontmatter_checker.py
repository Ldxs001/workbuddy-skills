#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/frontmatter_checker.py — Frontmatter 检查函数 (R-01~R-05, R-10)

[v2.36.0] 所有检查返回 filename:line 格式，方便直接定位。
"""

import re

def _find_fm_line(content, field_name=None):
    """
    返回 frontmatter 内的行号（1-indexed，相对于文件开头）。
    - 如果 field_name 非空：找到该字段所在行号。
    - 如果 field_name 为 None：返回 frontmatter 结束行号（第二个 --- 所在行），
      用于提示「应在哪一行之前插入缺失字段」。
    如果找不到 frontmatter，返回 1。
    """
    lines = content.split("\n")
    # 找第一个 ---
    fm_start = None
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            fm_start = i
            break
    if fm_start is None:
        return 1
    # 找第二个 ---
    fm_end = None
    for i in range(fm_start + 1, len(lines)):
        if lines[i].strip() == "---":
            fm_end = i
            break
    if fm_end is None:
        return fm_start + 2  # 保守估计

    if field_name is None:
        return fm_end + 1  # 1-indexed

    # 在 frontmatter 区间内搜索 field_name:
    pattern = re.compile(r'^' + re.escape(field_name) + r'\s*:')
    for i in range(fm_start + 1, fm_end):
        if pattern.match(lines[i]):
            return i + 1  # 1-indexed
    # 没找到字段：返回 fm_end（提示应插在 --- 前）
    return fm_end  # 1-indexed，即第二个 --- 所在行


def regex_frontmatter_exists(filepath, content, fm, body, **kw):
    """R-01: Frontmatter 存在性 + 字段完整性检查（required/conditional/optional 分层）"""
    # ── 存在性检查 ──
    if fm is None:
        line = 1
        return {"passed": False,
                "detail": f"{filepath}:{line} - 缺少 YAML frontmatter（期望：文件以 --- 开头）",
                "fix": {"key": "frontmatter", "value": True,
                         "location": f"{filepath}:{line}",
                         "operation": "在文件头部插入 --- 包裹的 frontmatter 块，含 name/version/description/sensitive_access/critical_write/permission_weight",
                         "verification": "重新运行 audit_skill()，确认 R-01 passed"}}

    line = 1  # frontmatter 从第一行开始

    # ── 分层字段定义 ──
    FM_REQUIRED = {'name','version','description','author','license','tags',
                   'data_dir','external_data_dir',
                   'sensitive_access','critical_write','permission_weight'}
    FM_CONDITIONAL = {'trigger','trigger_negative'}
    FM_OPTIONAL = {'references','category','priority','deprecated'}
    FM_STANDARD = FM_REQUIRED | FM_CONDITIONAL | FM_OPTIONAL

    existing = set(fm.keys()) if fm else set()
    missing_required = FM_REQUIRED - existing
    missing_conditional = FM_CONDITIONAL - existing
    extra = existing - FM_STANDARD

    issues = []
    if missing_required:
        issues.append(f"缺失必填字段({len(missing_required)}): {', '.join(sorted(missing_required))}")
    if missing_conditional:
        issues.append(f"缺失条件字段(正文有触发词/否定条件时必填，否则 WARN): {', '.join(sorted(missing_conditional))}")
    if extra:
        issues.append(f"非标字段(仅提醒，不阻断): {', '.join(sorted(extra))}")

    if not issues:
        return {"passed": True,
                "detail": f"发现 YAML frontmatter，11 required + 2 conditional 字段完整"}

    issues_str = '；'.join(issues)
    # 仅 extra（非标字段）时不阻断通过，报 WARN
    passed = not bool(missing_required) and not bool(missing_conditional)
    return {"passed": passed,
            "detail": f"{filepath}:{line} - {issues_str}",
            "fix": {"key": "frontmatter_fields", "value": "+".join(sorted(missing_required | missing_conditional)) if missing_required or missing_conditional else 'clean',
                     "operation": f"补全缺失字段{'；非标字段仅提醒' if extra else ''}"}}


def yaml_has_name(filepath, content, fm, body, **kw):
    """R-02: name 字段检查"""
    has_name = fm is not None and "name" in fm
    line = _find_fm_line(content, "name") if has_name else _find_fm_line(content)
    if not has_name:
        return {"passed": False,
                "detail": f"{filepath}:{line} - 缺少 name 字段（期望：name: <技能名，与目录名一致>）",
                "fix": {"key": "name", "value": None,
                         "location": f"{filepath}:{line}",
                         "operation": f"添加 name: <技能名，与目录名一致>",
                         "verification": "重新运行 audit_skill()，确认 R-02 passed"}}
    return {"passed": True,
            "detail": f"{filepath}:{line} - name = {fm['name']}"}


def yaml_has_semver_version(filepath, content, fm, body, **kw):
    """R-03: version 字段 (SemVer) 检查"""
    has_ver = fm is not None and "version" in fm
    line = _find_fm_line(content, "version") if has_ver else _find_fm_line(content)
    if not has_ver:
        return {"passed": False,
                "detail": f"{filepath}:{line} - 缺少 version 字段（期望：SemVer x.y.z 格式）",
                "fix": {"key": "version", "value": "1.0.0",
                         "location": f"{filepath}:{line}",
                         "operation": "添加 version: 1.0.0 (必须符合 SemVer x.y.z 格式)",
                         "verification": "重新运行 audit_skill()，确认 R-03 passed"}}
    ver = str(fm["version"])
    semver_ok = bool(re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$', ver))
    if not semver_ok:
        return {"passed": False,
                "detail": f"{filepath}:{line} - version = {ver} ✗ 不符合 SemVer（期望：x.y.z）",
                "fix": {"key": "version", "value": "符合 SemVer 的值",
                         "location": f"{filepath}:{line}",
                         "operation": f"修改 version: {ver} → 符合 SemVer 格式 (x.y.z)",
                         "verification": "重新运行 audit_skill()，确认 R-03 passed"}}
    return {"passed": True,
            "detail": f"{filepath}:{line} - version = {ver} ✓"}


def yaml_has_description(filepath, content, fm, body, **kw):
    """R-04: description 字段检查（功能描述，不应含版本号）"""
    has_desc = fm is not None and "description" in fm
    line = _find_fm_line(content, "description") if has_desc else _find_fm_line(content)
    if not has_desc:
        return {"passed": False,
                "detail": f"{filepath}:{line} - 缺少 description 字段（期望：≤120 字符的简要描述）",
                "fix": {"key": "description", "value": "<技能的简要描述>",
                         "location": f"{filepath}:{line}",
                         "operation": "添加 description: <技能的简要描述，一行概括技能用途，不含版本号>",
                         "verification": "重新运行 audit_skill()，确认 R-04 passed"}}
    dv = str(fm.get("description", ""))[:60]
    desc_raw = str(fm.get("description", ""))
    # 检测 description 中是否含版本号（如 v2.40.0、v1.0 等模式）
    version_in_desc = re.search(r'v?\d+\.\d+\.\d+', desc_raw)
    if version_in_desc:
        line = _find_fm_line(content, "description")
        return {"passed": False,
                "detail": f'{filepath}:{line} - description 含版本号 "{version_in_desc.group()}"，description 是功能摘要不应含版本号（版本号由 version 字段管理）',
                "fix": {"key": "description", "value": desc_raw,
                         "location": f"{filepath}:{line}",
                         "operation": f"从 description 中移除版本号 {version_in_desc.group()}",
                         "verification": "重新运行 audit_skill()，确认 R-04 passed"}}
    return {"passed": True,
            "detail": f'{filepath}:{line} - description = "{dv}"'}


def name_matches_dirname(filepath, content, fm, body, dirname=None, **kw):
    """R-05: name 与目录名一致检查"""
    if fm is None or "name" not in fm:
        return {"passed": False, "detail": "无法检查：无 frontmatter/name", "skip": True}
    if not dirname:
        return {"passed": True, "detail": "跳过：未提供目录名", "skip": True}
    line = _find_fm_line(content, "name")
    matched = fm["name"] == dirname
    if not matched:
        return {"passed": False,
                "detail": f"{filepath}:{line} - name({fm['name']}) != dirname({dirname})",
                "fix": {"key": "name", "value": dirname,
                         "location": f"{filepath}:{line}",
                         "operation": f"修改 name: {fm['name']} → {dirname} (与目录名一致)",
                         "verification": "重新运行 audit_skill()，确认 R-05 passed"}}
    return {"passed": True,
            "detail": f"{filepath}:{line} - name({fm['name']}) == dirname({dirname})"}


def version_matches_manifest(filepath, content, fm, body, manifest_version=None, **kw):
    """R-10: 版本三端一致性检查（v2.38.15 增强：自动读取 _meta.json + changelog + mtime 时序检查）"""
    import os, json, re
    skill_dir = kw.get('skill_dir') or os.path.dirname(filepath) if filepath else None

    if fm is None or "version" not in fm:
        return {"passed": False, "detail": "无 frontmatter/version，无法比对", "skip": True}
    line = _find_fm_line(content, "version")
    skill_version = str(fm["version"])

    # ── 1. 比对 _meta.json ──
    meta_path = os.path.join(skill_dir, '_meta.json') if skill_dir else None
    meta_version = None
    if meta_path and os.path.isfile(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as _f:
                meta_version = str(json.load(_f).get('version', ''))
        except Exception:
            pass

    # 优先使用 manifest_version（CLI --manifest-version），否则从 _meta.json 获取
    expected_version = str(manifest_version) if manifest_version is not None else meta_version

    # ── 2. 比对 references/changelog.md ──
    cl_path = os.path.join(skill_dir, 'references', 'changelog.md') if skill_dir else None
    cl_version = None
    if cl_path and os.path.isfile(cl_path):
        try:
            with open(cl_path, 'r', encoding='utf-8') as _f:
                cl_content = _f.read()
            _m = re.search(r'^##\s*v?(\d+\.\d+\.\d+)', cl_content, re.MULTILINE)
            if _m:
                cl_version = _m.group(1)
        except Exception:
            pass

    # ── 3. 版本值一致性检查 ──
    issues = []
    if expected_version and skill_version != expected_version:
        issues.append(f"SKILL.md({skill_version}) != _meta.json({expected_version})")
    if cl_version and skill_version != cl_version:
        issues.append(f"SKILL.md({skill_version}) != changelog({cl_version})")
    if expected_version and cl_version and expected_version != cl_version:
        issues.append(f"_meta.json({expected_version}) != changelog({cl_version})")

    if issues:
        detail = f"{filepath}:{line} - 版本不一致：{'；'.join(issues)}"
        return {"passed": False, "detail": detail,
                "fix": {"key": "version", "value": expected_version or skill_version,
                         "location": f"{filepath}:{line}",
                         "operation": f"同步 version 为 {expected_version or skill_version}，确保三端一致"}
                }

    # ── 4. mtime 时序检查（检测"改了文件但忘了更新版本号"） ──
    mtime_warnings = []
    try:
        skill_md_mtime = os.path.getmtime(filepath) if filepath and os.path.isfile(filepath) else 0
        cl_mtime = os.path.getmtime(cl_path) if cl_path and os.path.isfile(cl_path) else 0
        # 检查 scripts/ 下所有 .py 文件的最新 mtime
        scripts_dir = os.path.join(skill_dir, 'scripts') if skill_dir else None
        scripts_max_mtime = 0
        if scripts_dir and os.path.isdir(scripts_dir):
            for root, dirs, files in os.walk(scripts_dir):
                for f in files:
                    if f.endswith('.py'):
                        fp = os.path.join(root, f)
                        scripts_max_mtime = max(scripts_max_mtime, os.path.getmtime(fp))

        # SKILL.md 比 changelog 新
        if skill_md_mtime > cl_mtime + 60:  # 60秒容差
            mtime_warnings.append("SKILL.md 修改时间比 changelog 更新，可能忘了更新版本号/changelog")
        # scripts/ 比 changelog 新
        if scripts_max_mtime > cl_mtime + 60:
            mtime_warnings.append("scripts/ 下有文件修改时间比 changelog 更新，可能忘了更新版本号/changelog")
    except Exception:
        pass

    sources = []
    if skill_version: sources.append(f"SKILL.md({skill_version})")
    if meta_version: sources.append(f"_meta.json({meta_version})")
    if cl_version: sources.append(f"changelog({cl_version})")
    detail = f"{filepath}:{line} - 版本一致（{' == '.join(sources)}）"
    if mtime_warnings:
        detail += ' ⚠️ ' + '；'.join(mtime_warnings)
    return {"passed": True,  # 版本值一致即 passed，mtime 仅做提示
            "detail": detail}


def check_meta_json_completeness(filepath, content, fm, body, **kw):
    """R-25: _meta.json 字段规范性检查（7 标准字段 + 非标字段标记）"""
    import os, json, re
    skill_dir = kw.get('skill_dir') or (os.path.dirname(filepath) if filepath else None)
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "R-25: 无法访问技能目录，跳过"}
    meta_path = os.path.join(skill_dir, '_meta.json')
    if not os.path.isfile(meta_path):
        return {"passed": False, "detail": "R-25: _meta.json 文件不存在",
                "fix": {"key": "meta_json", "value": "missing",
                         "operation": "创建 _meta.json（含 7 标准字段）"}}

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    META_STANDARD_FIELDS = {'name', 'version', 'description', 'author', 'tags',
                            'data_dir', 'triggers'}
    existing = set(meta.keys())
    missing = META_STANDARD_FIELDS - existing
    extra = existing - META_STANDARD_FIELDS

    issues = []
    if missing:
        issues.append(f"缺失字段: {', '.join(sorted(missing))}")
    if extra:
        issues.append(f"非标字段(需人工判断删/迁移): {', '.join(sorted(extra))}")

    if not issues:
        return {"passed": True, "detail": f"R-25: _meta.json 字段完整（{len(existing)}字段）"}

    issues_str = '；'.join(issues)
    return {"passed": False,
            "detail": f"R-25: {meta_path} - {issues_str}",
            "fix": {"key": "meta_json", "value": "+".join(sorted(missing)) if missing else 'clean',
                     "operation": f"补全缺失字段{'、标记非标字段供判断' if extra else ''}"}}
