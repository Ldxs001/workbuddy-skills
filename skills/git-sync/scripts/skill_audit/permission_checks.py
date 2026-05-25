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
    """R-13: 敏感信息访问声明检查。不一致时返回 fix 建议。"""
    # 修复：先检查 frontmatter 是否缺少字段
    if fm is None:
        return {"passed": False, "detail": "SKILL.md 缺少 frontmatter（--- 包裹的元数据区）"}
    
    if "sensitive_access" not in fm:
        # 获取实际扫描结果，返回 fix 建议
        if not skill_dir or not os.path.isdir(skill_dir):
            return {"passed": False, "detail": "frontmatter 缺少 sensitive_access 字段（必须声明，值为 true 或 false）"}
        report = _get_report(skill_dir)
        if report is None:
            return {"passed": False, "detail": "frontmatter 缺少 sensitive_access 字段（必须声明，值为 true 或 false）"}
        stats = report.get("stats", {})
        has_sensitive = stats.get("sensitive_access", 0) > 0
        return {
            "passed": False,
            "detail": "frontmatter 缺少 sensitive_access 字段（必须声明，值为 true 或 false）",
            "fix": {"key": "sensitive_access", "value": has_sensitive,
                     "location": "<skill-dir>/SKILL.md frontmatter",
                     "operation": f"设置 sensitive_access: {has_sensitive}",
                     "verification": "重新运行 audit_skill()，确认 R-13 passed",
                     "reason": f"缺少 sensitive_access 字段，根据实际扫描结果（{has_sensitive} 处敏感信息访问）自动添加"}
        }
    
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
            "detail": "脚本含敏感信息访问（memory/credentials/token），但 frontmatter 声明 sensitive_access: false",
            "fix": {"key": "sensitive_access", "value": True,
                     "reason": f"实际扫描发现 {stats.get('sensitive_access', 0)} 处敏感信息访问，与声明不一致"}
        }

    if not has_sensitive_access and fm_sensitive:
        return {
            "passed": False,
            "detail": "frontmatter 声明 sensitive_access: true，但脚本未检测到敏感信息访问",
            "fix": {"key": "sensitive_access", "value": False,
                     "reason": "实际扫描未发现敏感信息访问，与声明不一致"}
        }

    return {
        "passed": True,
        "detail": "敏感信息访问声明检查通过" + (f"（检测到 {stats.get('sensitive_access', 0)} 处访问）" if has_sensitive_access else "")
    }


def check_critical_write_declaration(filepath, content, fm, body, skill_dir=None, **kw):
    """R-14: 关键位置写入声明检查。不一致时返回 fix 建议。"""
    # 修复：先检查 frontmatter 是否缺少字段
    if fm is None:
        return {"passed": False, "detail": "SKILL.md 缺少 frontmatter（--- 包裹的元数据区）"}
    
    if "critical_write" not in fm:
        # 获取实际扫描结果，返回 fix 建议
        if not skill_dir or not os.path.isdir(skill_dir):
            return {"passed": False, "detail": "frontmatter 缺少 critical_write 字段（必须声明，值为 true 或 false）"}
        report = _get_report(skill_dir)
        if report is None:
            return {"passed": False, "detail": "frontmatter 缺少 critical_write 字段（必须声明，值为 true 或 false）"}
        stats = report.get("stats", {})
        has_critical = stats.get("critical_write", 0) > 0
        return {
            "passed": False,
            "detail": "frontmatter 缺少 critical_write 字段（必须声明，值为 true 或 false）",
            "fix": {"key": "critical_write", "value": has_critical,
                     "location": "<skill-dir>/SKILL.md frontmatter",
                     "operation": f"设置 critical_write: {has_critical}",
                     "verification": "重新运行 audit_skill()，确认 R-14 passed",
                     "reason": f"缺少 critical_write 字段，根据实际扫描结果（{has_critical} 处关键位置写入）自动添加"}
        }
    
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
            "detail": "脚本含关键位置写入（skills/.workbuddy/系统目录），但 frontmatter 声明 critical_write: false",
            "fix": {"key": "critical_write", "value": True,
                     "reason": f"实际扫描发现 {stats.get('critical_write', 0)} 处关键位置写入，与声明不一致"}
        }

    if not has_critical_write and fm_critical:
        return {
            "passed": False,
            "detail": "frontmatter 声明 critical_write: true，但脚本未检测到关键位置写入",
            "fix": {"key": "critical_write", "value": False,
                     "reason": "实际扫描未发现关键位置写入，与声明不一致"}
        }

    return {
        "passed": True,
        "detail": "关键位置写入声明检查通过" + (f"（检测到 {stats.get('critical_write', 0)} 处写入）" if has_critical_write else "")
    }


def check_authorization_present(filepath, content, fm, body, skill_dir=None, **kw):
    """R-15: 高权限操作风险说明检查。检查 references/permissions.md 是否包含高权限操作风险说明。"""
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}

    # 用 PermissionChecker 获取风险等级
    report = _get_report(skill_dir)
    risk_level = report.get("risk_level", "low").upper() if report else "LOW"

    # 低风险/中风险：无需在 references/permissions.md 中说明风险
    if risk_level in ("LOW", "MEDIUM"):
        return {"passed": True, "detail": f"风险等级 {risk_level}，无需在 references/permissions.md 中说明高风险操作"}

    # 高风险/严重风险：必须在 references/permissions.md 中说明
    if risk_level in ("HIGH", "CRITICAL"):
        refs_dir = os.path.join(skill_dir, "references")
        if not os.path.isdir(refs_dir):
            return {
                "passed": False,
                "detail": f"风险等级 {risk_level}，但 references/ 目录不存在，无法检查风险说明",
                "fix": {"key": "create_references_permissions_md", "value": True,
                         "location": f"{skill_dir}/references/permissions.md",
                         "operation": "创建 references/ 目录和 permissions.md，并在其中说明高权限操作风险",
                         "verification": "重新运行 audit_skill()，确认 R-15 passed"}
            }

        permissions_md = os.path.join(refs_dir, "permissions.md")
        if not os.path.isfile(permissions_md):
            return {
                "passed": False,
                "detail": f"风险等级 {risk_level}，但 references/permissions.md 不存在",
                "fix": {"key": "create_permissions_md", "value": True,
                         "location": permissions_md,
                         "operation": "创建 permissions.md 并在其中说明高权限操作风险（风险等级、具体操作、为什么需要）",
                         "verification": "重新运行 audit_skill()，确认 R-15 passed"}
            }

        # 读取 permissions.md 内容
        try:
            with open(permissions_md, "r", encoding="utf-8", errors="replace") as f:
                pm_content = f.read()
        except Exception as e:
            return {
                "passed": False,
                "detail": f"风险等级 {risk_level}，但无法读取 references/permissions.md: {e}",
                "fix": {"key": "fix_permissions_md_readable", "value": True,
                         "location": permissions_md,
                         "operation": "确保 permissions.md 可读，并包含高权限操作风险说明",
                         "verification": "重新运行 audit_skill()，确认 R-15 passed"}
            }

        # 检查是否包含风险说明关键词
        risk_keywords = ["风险", "risk", "高权限", "high risk", "critical", "授权", "authorization", "权限"]
        found_risk = False
        for kw in risk_keywords:
            if kw.lower() in pm_content.lower():
                found_risk = True
                break

        if not found_risk:
            return {
                "passed": False,
                "detail": f"风险等级 {risk_level}，但 references/permissions.md 未包含高风险操作风险说明",
                "fix": {"key": "add_risk_description", "value": True,
                         "location": permissions_md,
                         "operation": "在 permissions.md 中添加高风险操作风险说明（风险等级、具体操作、为什么需要、如何降低风险）",
                         "verification": "重新运行 audit_skill()，确认 R-15 passed"}
            }

        return {
            "passed": True,
            "detail": f"高权限操作风险说明检查通过（风险等级 {risk_level}，references/permissions.md 包含风险说明）"
        }

    # 未知风险等级
    return {"passed": True, "detail": f"风险等级 {risk_level}（未知），跳过检查", "skip": True}


def check_permission_weight_explained(filepath, content, fm, body, skill_dir=None, **kw):
    """R-16: 权限权重说明检查。不一致时返回 fix 建议。"""
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}

    # 1. 检查 frontmatter 中是否有 permission_weight 字段
    fm_weight = fm.get("permission_weight", None)
    if fm_weight is None:
        # 获取实际扫描的风险等级，用于 fix 建议
        if not skill_dir or not os.path.isdir(skill_dir):
            return {"passed": False, "detail": "frontmatter 缺少 permission_weight 字段（必须声明风险等级：LOW/MEDIUM/HIGH/CRITICAL）"}
        report = _get_report(skill_dir)
        actual_weight = report.get("risk_level", "low").upper() if report else "LOW"
        return {
            "passed": False,
            "detail": "frontmatter 缺少 permission_weight 字段（必须声明风险等级：LOW/MEDIUM/HIGH/CRITICAL）",
            "fix": {"key": "permission_weight", "value": actual_weight,
                     "location": "<skill-dir>/SKILL.md frontmatter",
                     "operation": f"设置 permission_weight: {actual_weight}",
                     "verification": "重新运行 audit_skill()，确认 R-16 passed",
                     "reason": f"缺少 permission_weight 字段，根据实际扫描风险等级 {actual_weight} 自动添加"}
        }

    # 2. 获取实际扫描的风险等级
    report = _get_report(skill_dir)
    actual_weight = report.get("risk_level", "low").upper() if report else "LOW"
    fm_weight_upper = fm_weight.upper() if isinstance(fm_weight, str) else "LOW"

    # 3. 对比声明和实际是否一致
    if fm_weight_upper != actual_weight:
        return {
            "passed": False,
            "detail": f"frontmatter permission_weight: {fm_weight}，但实际扫描风险等级: {actual_weight}",
            "fix": {"key": "permission_weight", "value": actual_weight,
                     "reason": f"实际扫描风险等级为 {actual_weight}，与声明 {fm_weight} 不一致"}
        }

    # 4. 检查 references/ 里有没有权重说明文档（保留原有检查）
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
            "detail": "建议在 references/ 中说明各操作的权限权重，便于审查时评估风险"
        }

    return {"passed": True, "detail": f"权限权重说明检查通过（声明: {fm_weight}，实际风险: {actual_weight}）"}


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
            "detail": f"SKILL.md 共 {line_count} 行，超过 200 行限制，但未拆分到 references/ 或通过「→ 详见 references/xxx.md」引用",
            "fix": {"key": "progressive_loading", "value": True,
                     "location": f"{filepath} (SKILL.md 超过 200 行部分)",
                     "operation": "将 SKILL.md 中详细内容拆分到 references/ 目录下的独立 .md 文件，并在 SKILL.md 中用「→ 详见 references/xxx.md」引用",
                     "verification": "重新运行 audit_skill()，确认 R-17 passed"}
        }

    return {
        "passed": True,
        "detail": f"SKILL.md 共 {line_count} 行，已超过 200 行，但已拆分到 references/（符合渐进加载要求）"
    }
