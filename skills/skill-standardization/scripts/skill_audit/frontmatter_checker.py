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
    return {"passed": passed,
            "detail": "发现 YAML frontmatter" if passed else "缺少 YAML frontmatter"}


def yaml_has_name(filepath, content, fm, body, **kw):
    """R-02: name 字段检查"""
    has_name = fm is not None and "name" in fm
    return {"passed": has_name,
            "detail": f"name = {fm['name']}" if has_name else "缺少 name 字段"}


def yaml_has_semver_version(filepath, content, fm, body, **kw):
    """R-03: version 字段 (SemVer) 检查"""
    has_ver = fm is not None and "version" in fm
    if not has_ver:
        return {"passed": False, "detail": "缺少 version 字段"}
    ver = str(fm["version"])
    semver_ok = bool(re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$', ver))
    return {"passed": semver_ok,
            "detail": f"version = {ver}" + (" ✓" if semver_ok else " ✗ 不符合 SemVer")}


def yaml_has_description(filepath, content, fm, body, **kw):
    """R-04: description 字段检查"""
    has_desc = fm is not None and "description" in fm
    dv = str(fm.get("description", ""))[:60] if has_desc else ""
    return {"passed": has_desc,
            "detail": f"description = \"{dv}\"" if has_desc else "缺少 description 字段"}


def name_matches_dirname(filepath, content, fm, body, dirname=None, **kw):
    """R-05: name 与目录名一致检查"""
    if fm is None or "name" not in fm:
        return {"passed": False, "detail": "无法检查：无 frontmatter/name", "skip": True}
    if not dirname:
        return {"passed": True, "detail": "跳过：未提供目录名", "skip": True}
    matched = fm["name"] == dirname
    return {"passed": matched,
            "detail": f"name({fm['name']}) {'==' if matched else '!='} dirname({dirname})"}


def version_matches_manifest(filepath, content, fm, body, manifest_version=None, **kw):
    """R-10: version 一致性检查（与 manifest 版本比对）"""
    if manifest_version is None:
        return {"passed": True, "detail": "跳过：未提供 manifest 版本号", "skip": True}
    if fm is None or "version" not in fm:
        return {"passed": False, "detail": "无 frontmatter/version，无法比对", "skip": True}
    matched = str(fm["version"]) == str(manifest_version)
    return {"passed": matched,
            "detail": f"SKILL.md({fm['version']}) {'==' if matched else '!='} manifest({manifest_version})"}
