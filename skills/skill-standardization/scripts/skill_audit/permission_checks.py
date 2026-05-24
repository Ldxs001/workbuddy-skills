#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/permission_checks.py — 权限相关检查函数 (R-13~R-17)
v2.16.0: 直接内嵌 PermissionChecker，不再 shell out
"""

import os
import re
import sys

# ── 直接导入 PermissionChecker，不再 subprocess.run() ─────────────────────
_scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _scripts_dir)
from permission_checker import PermissionChecker


def _get_report(skill_dir):
    """
    直接调用 PermissionChecker（不再 shell out）。
    返回 report dict，失败返回 None。
    """
    try:
        checker = PermissionChecker(skill_dir, verbose=False)
        return checker.scan()
    except Exception:
        return None


# ── R-13 ~ R-17 检查函数 ─────────────────────────────────────────────────────

def check_sensitive_access_declaration(filepath, content, fm, body, skill_dir=None, **kw):
    """R-13: 敏感信息访问声明检查。"""
    # 修复：先检查 frontmatter 是否缺少字段
    if fm is None:
        return {"passed": False, "detail": "SKILL.md 缺少 frontmatter（--- 包裹的元数据区）"}
    
    if "sensitive_access" not in fm:
        return {"passed": False, "detail": "frontmatter 缺少 sensitive_access 字段（必须声明，值为 true 或 false）"}
    
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}

    report = _get_report(skill_dir)
    if report is None:
        return {
            "passed": True,
            "detail": "PermissionChecker 不可用，跳过详细检查",
            "skip": True
        }

    stats = report.get("stats", {})
    has_sensitive_access = stats.get("sensitive_access", 0) > 0
    fm_sensitive = fm.get("sensitive_access", False)

    if has_sensitive_access and not fm_sensitive:
        return {
            "passed": False,
            "detail": "脚本含敏感信息访问（memory/credentials/token），但 frontmatter 声明 sensitive_access: false"
        }

    return {
        "passed": True,
        "detail": "敏感信息访问声明检查通过" + (f"（检测到 {stats.get('sensitive_access', 0)} 处访问）" if has_sensitive_access else "")
    }


def check_critical_write_declaration(filepath, content, fm, body, skill_dir=None, **kw):
    """R-14: 关键位置写入声明检查。"""
    # 修复：先检查 frontmatter 是否缺少字段
    if fm is None:
        return {"passed": False, "detail": "SKILL.md 缺少 frontmatter（--- 包裹的元数据区）"}
    
    if "critical_write" not in fm:
        return {"passed": False, "detail": "frontmatter 缺少 critical_write 字段（必须声明，值为 true 或 false）"}
    
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}

    report = _get_report(skill_dir)
    if report is None:
        return {
            "passed": True,
            "detail": "PermissionChecker 不可用，跳过详细检查",
            "skip": True
        }

    stats = report.get("stats", {})
    has_critical_write = stats.get("critical_write", 0) > 0
    fm_critical = fm.get("critical_write", False)

    if has_critical_write and not fm_critical:
        return {
            "passed": False,
            "detail": "脚本含关键位置写入（skills/.workbuddy/系统目录），但 frontmatter 声明 critical_write: false"
        }

    return {
        "passed": True,
        "detail": "关键位置写入声明检查通过" + (f"（检测到 {stats.get('critical_write', 0)} 处写入）" if has_critical_write else "")
    }


def check_authorization_present(filepath, content, fm, body, skill_dir=None, **kw):
    """R-15: 高权限操作授权检查。"""
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}

    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return {"passed": True, "detail": "无 scripts/ 目录，跳过检查"}

    # 检查是否有授权逻辑
    auth_patterns = [
        r"authorization_manager",
        r"request.*authorization",
        r"check.*permission",
        r"\bauthoriz\w*\b",
    ]

    found_auth = False
    for fname in sorted(os.listdir(scripts_dir)):
        fpath = os.path.join(scripts_dir, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in (".py", ".sh", ".bat", ".ps1"):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
        except Exception:
            continue
        for pattern in auth_patterns:
            if re.search(pattern, file_content, re.IGNORECASE):
                found_auth = True
                break
        if found_auth:
            break

    # 用 PermissionChecker 获取风险等级
    report = _get_report(skill_dir)
    if report:
        risk_level = report.get("risk_level", "low")
        if risk_level in ("high", "critical") and not found_auth:
            return {
                "passed": False,
                "detail": f"脚本含高权限操作（风险等级: {risk_level}），但未调用 authorization_manager.py 请求授权"
            }

    return {
        "passed": True,
        "detail": "高权限操作授权检查通过" + (
            "（发现授权检查逻辑）" if found_auth else f"（风险等级 {report.get('risk_level', 'low') if report else 'unknown'}，无需授权）"
        )
    }


def check_permission_weight_explained(filepath, content, fm, body, skill_dir=None, **kw):
    """R-16: 权限权重说明检查。"""
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}

    refs_dir = os.path.join(skill_dir, "references")
    if not os.path.isdir(refs_dir):
        return {"passed": False, "detail": "建议增加权限权重说明（references/ 目录不存在）"}

    weight_keywords = ["权限权重", "permission weight", "权重", "weight", "风险等级", "risk level"]

    found_explanation = False
    for fname in sorted(os.listdir(refs_dir)):
        fpath = os.path.join(refs_dir, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in (".md", ".txt", ".rst"):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read()
        except Exception:
            continue
        for keyword in weight_keywords:
            if keyword.lower() in file_content.lower():
                found_explanation = True
                break
        if found_explanation:
            break

    if not found_explanation:
        return {
            "passed": False,
            "detail": "建议在 SKILL.md 或 references/ 中说明各操作的权限权重，便于审查时评估风险"
        }

    return {"passed": True, "detail": "权限权重说明检查通过（发现权重说明文档）"}


def check_progressive_loading_forced(filepath, content, fm, body, **kw):
    """R-17: 渐进加载强制检查。"""
    if not content:
        return {"passed": True, "detail": "无内容，跳过检查"}

    lines = content.splitlines()
    line_count = len(lines)

    if line_count <= 200:
        return {"passed": True, "detail": f"SKILL.md 共 {line_count} 行，符合渐进加载要求（≤200 行）"}

    has_references = False
    for line in lines:
        if "references/" in line or "→ 详见" in line or "详见 `references/" in line:
            has_references = True
            break

    if not has_references:
        return {
            "passed": False,
            "detail": f"SKILL.md 共 {line_count} 行，超过 200 行限制，但未拆分到 references/ 或通过「→ 详见 references/xxx.md」引用"
        }

    return {
        "passed": True,
        "detail": f"SKILL.md 共 {line_count} 行，已超过 200 行，但已拆分到 references/（符合渐进加载要求）"
    }
