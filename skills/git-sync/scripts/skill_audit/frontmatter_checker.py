#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/frontmatter_checker.py — Frontmatter 检查函数 (R-01~R-05, R-10)
"""

import re
import os


def regex_frontmatter_exists(filepath, content, fm, body, **kw):
    """R-01: Frontmatter 存在性检查"""
    passed = fm is not None
    if not passed:
        return {"passed": False,
                "detail": "缺少 YAML frontmatter",
                "fix": {"key": "frontmatter", "value": True,
                         "location": f"{filepath} (文件头部)",
                         "operation": "自动插入 --- 包裹的 frontmatter 块，含 name/version/description/sensitive_access/critical_write/permission_weight",
                         "verification": "重新运行 audit_skill()，确认 R-01 passed"}}
    return {"passed": True,
            "detail": "发现 YAML frontmatter"}


def yaml_has_name(filepath, content, fm, body, **kw):
    """R-02: name 字段检查"""
    has_name = fm is not None and "name" in fm
    if not has_name:
        return {"passed": False,
                "detail": "缺少 name 字段",
                "fix": {"key": "name", "value": None,
                         "location": f"{filepath} frontmatter",
                         "operation": "添加 name: <技能名，与目录名一致>",
                         "verification": "重新运行 audit_skill()，确认 R-02 passed"}}
    return {"passed": True,
            "detail": f"name = {fm['name']}"}


def yaml_has_semver_version(filepath, content, fm, body, **kw):
    """R-03: version 字段 (SemVer) 检查"""
    has_ver = fm is not None and "version" in fm
    if not has_ver:
        return {"passed": False,
                "detail": "缺少 version 字段",
                "fix": {"key": "version", "value": "1.0.0",
                         "location": f"{filepath} frontmatter",
                         "operation": "添加 version: 1.0.0 (必须符合 SemVer x.y.z 格式)",
                         "verification": "重新运行 audit_skill()，确认 R-03 passed"}}
    ver = str(fm["version"])
    semver_ok = bool(re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$', ver))
    if not semver_ok:
        return {"passed": False,
                "detail": f"version = {ver} ✗ 不符合 SemVer",
                "fix": {"key": "version", "value": "符合 SemVer 的值",
                         "location": f"{filepath} frontmatter",
                         "operation": f"修改 version: {ver} → 符合 SemVer 格式 (x.y.z)",
                         "verification": "重新运行 audit_skill()，确认 R-03 passed"}}
    return {"passed": True,
            "detail": f"version = {ver} ✓"}


def yaml_has_description(filepath, content, fm, body, **kw):
    """R-04: description 字段检查"""
    has_desc = fm is not None and "description" in fm
    if not has_desc:
        return {"passed": False,
                "detail": "缺少 description 字段",
                "fix": {"key": "description", "value": "<技能的简要描述>",
                         "location": f"{filepath} frontmatter",
                         "operation": "添加 description: <技能的简要描述，一行概括技能用途>",
                         "verification": "重新运行 audit_skill()，确认 R-04 passed"}}
    dv = str(fm.get("description", ""))[:60]
    return {"passed": True,
            "detail": f"description = \"{dv}\""}


def name_matches_dirname(filepath, content, fm, body, dirname=None, **kw):
    """R-05: name 与目录名一致检查"""
    if fm is None or "name" not in fm:
        return {"passed": False, "detail": "无法检查：无 frontmatter/name", "skip": True}
    if not dirname:
        return {"passed": True, "detail": "跳过：未提供目录名", "skip": True}
    matched = fm["name"] == dirname
    if not matched:
        return {"passed": False,
                "detail": f"name({fm['name']}) != dirname({dirname})",
                "fix": {"key": "name", "value": dirname,
                         "location": f"{filepath} frontmatter",
                         "operation": f"修改 name: {fm['name']} → {dirname} (与目录名一致)",
                         "verification": "重新运行 audit_skill()，确认 R-05 passed"}}
    return {"passed": True,
            "detail": f"name({fm['name']}) == dirname({dirname})"}


def version_matches_manifest(filepath, content, fm, body, manifest_version=None, **kw):
    """R-10: version 一致性检查（与 manifest 版本比对）"""
    if manifest_version is None:
        return {"passed": True, "detail": "跳过：未提供 manifest 版本号", "skip": True}
    if fm is None or "version" not in fm:
        return {"passed": False, "detail": "无 frontmatter/version，无法比对", "skip": True}
    matched = str(fm["version"]) == str(manifest_version)
    if not matched:
        return {"passed": False,
                "detail": f"SKILL.md({fm['version']}) != manifest({manifest_version})",
                "fix": {"key": "version", "value": manifest_version,
                         "location": f"{filepath} frontmatter",
                         "operation": f"修改 version: {fm['version']} → {manifest_version} (与 manifest.json 一致)",
                         "verification": "重新运行 audit_skill()，确认 R-10 passed"}}
    return {"passed": True,
            "detail": f"SKILL.md({fm['version']}) == manifest({manifest_version})"}
