#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_dir_checker.py — R-22 数据目录规范检查
v2.31.0

检查技能安装目录是否包含应归属数据目录的文件，
并在 --fix 模式下自动迁移到 skills/.standardization/<skill>/
"""

import os
import shutil
from pathlib import Path

# ── 应留在安装目录的文件（代码/配置/文档）──────────────────────────
_KEEP_IN_INSTALL = {
    "SKILL.md", "_meta.json",
    "README.md", "LICENSE", "CHANGELOG.md",
}

# ── 应迁移到数据目录的文件/目录模式 ────────────────────────────────
_MOVE_TO_DATA = {
    # 构建产物
    ".dist",
    # 数据/缓存/日志
    "data", "cache", "logs", "tmp", "temp",
    # 特定文件名
    "manifest.json", "progress.json",
}

# ── 应迁移到数据目录的文件扩展名 ────────────────────────────────────
_MOVE_EXTS = {
    ".zip", ".tar", ".gz", ".tgz",  # 构建产物
    ".log", ".cache", ".tmp",           # 日志/缓存
    ".db", ".sqlite", ".json",          # 数据文件（非配置）
}


def _classify_files(install_dir: str, data_dir: str) -> dict:
    """
    分类安装目录中的文件：
      - to_migrate: 需要迁移到数据目录的
      - ok: 可以留在安装目录的
    """
    to_migrate = []
    ok = []

    for entry in sorted(os.listdir(install_dir)):
        full = os.path.join(install_dir, entry)
        # 跳过数据目录本身
        if os.path.isdir(full) and entry == ".standardization":
            ok.append(entry)
            continue
        # 明确应留在安装目录
        if entry in _KEEP_IN_INSTALL:
            ok.append(entry)
            continue
        # .dist/ 构建产物 → 迁移
        if entry == ".dist":
            to_migrate.append(("dir", entry, "构建产物应放在数据目录"))
            continue
        # data/ cache/ logs/ tmp/ → 迁移
        if entry.lower() in _MOVE_TO_DATA:
            kind = "dir" if os.path.isdir(full) else "file"
            to_migrate.append((kind, entry, "数据/缓存文件应放在数据目录"))
            continue
        # 扩展名匹配 → 迁移
        _, ext = os.path.splitext(entry)
        if ext.lower() in _MOVE_EXTS:
            to_migrate.append(("file", entry, f"扩展名 {ext} 属于构建产物/缓存"))
            continue
        # 默认：留在安装目录
        ok.append(entry)

    return {"to_migrate": to_migrate, "ok": ok}


def check_data_dir_compliance(filepath=None, content=None, fm=None,
                            body=None, dirname=None, skill_dir=None,
                            manifest_version=None):
    """
    R-22: 数据目录规范检查。
    检查技能安装目录是否包含应归属数据目录的文件。

    返回: {"passed": bool, "skipped": bool, "detail": str, "fix": dict or None}
    """
    if not skill_dir or not os.path.isdir(skill_dir):
        return {
            "passed": True, "skipped": True,
            "detail": "R-22 跳过：无法确定技能目录",
        }

    # 读取 data_dir 声明
    data_dir_declared = fm.get("data_dir", "") if fm else ""
    if not data_dir_declared:
        # 尝试从 SHELL.md 推断
        return {
            "passed": False, "skipped": False,
            "detail": "R-22 FAIL — 未在 frontmatter 中声明 data_dir: "
                      "(应声明数据目录，如 data_dir: ../.standardization/git-sync/)",
            "fix": {
                "operation": "add_frontmatter_field",
                "field": "data_dir",
                "value": "../.standardization/" + dirname + "/",
                "location": "SKILL.md frontmatter",
                "reason": "R-22 要求声明数据目录",
            },
        }

    # 解析 data_dir 的实际路径
    install_path = Path(skill_dir).resolve()
    # data_dir 是相对于安装目录的路径
    data_dir_path = (install_path / data_dir_declared).resolve()

    if not data_dir_path.is_dir():
        # 数据目录不存在，提示创建
        return {
            "passed": False, "skipped": False,
            "detail": f"R-22 WARN — 声明的数据目录不存在: {data_dir_path}",
            "fix": {
                "operation": "create_data_dir",
                "path": str(data_dir_path),
                "reason": "R-22 要求数据目录存在",
            },
        }

    # 分类文件
    classification = _classify_files(skill_dir, str(data_dir_path))

    if not classification["to_migrate"]:
        return {
            "passed": True, "skipped": False,
            "detail": f"R-22 PASS — 安装目录无越位数据文件 (data_dir: {data_dir_declared})",
        }

    # 有需要迁移的文件
    migrate_desc = ", ".join([f"{kind}:{name}" for kind, name, _ in classification["to_migrate"][:5]])
    return {
        "passed": False, "skipped": False,
        "detail": f"R-22 FAIL — 安装目录存在应迁移文件: {migrate_desc} (共 {len(classification['to_migrate'])} 项)",
        "fix": {
            "operation": "migrate_data_files",
            "skill_dir": skill_dir,
            "data_dir": str(data_dir_path),
            "files": classification["to_migrate"],
            "reason": "R-22 要求数据文件放在数据目录",
        },
    }


def fix_data_dir_compliance(skill_dir: str) -> int:
    """
    自动修复 R-22 违规：
    1. 如果缺少 data_dir: 声明，添加到 SKILL.md frontmatter
    2. 如果有文件需要迁移，自动迁移到数据目录

    返回: 修复的文件数
    """
    fixed = 0
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0

    # 读取 frontmatter
    from .utils import parse_simple_yaml_frontmatter
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()
    fm, body = parse_simple_yaml_frontmatter(content)

    if fm is None:
        return 0

    install_path = Path(skill_dir).resolve()
    dirname = os.path.basename(install_path)

    # 修复 1: 添加 data_dir: 声明
    if "data_dir" not in fm:
        fm["data_dir"] = f"../.standardization/{dirname}/"
        # 重写文件
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
        fixed += 1

    # 修复 2: 迁移文件
    data_dir_declared = fm.get("data_dir", "")
    if not data_dir_declared:
        return fixed

    data_dir_path = (install_path / data_dir_declared).resolve()
    os.makedirs(data_dir_path, exist_ok=True)

    classification = _classify_files(skill_dir, str(data_dir_path))

    for kind, entry, reason in classification["to_migrate"]:
        src = os.path.join(skill_dir, entry)
        dst = os.path.join(data_dir_path, entry)
        if os.path.exists(dst):
            # 目标已存在，跳过
            print(f"  [skip] 目标已存在: {dst}")
            continue
        try:
            if kind == "dir":
                shutil.move(src, dst)
            else:
                shutil.move(src, dst)
            print(f"  [OK] 已迁移: {entry} → {data_dir_path}")
            fixed += 1
        except Exception as e:
            print(f"  [X] 迁移失败 {entry}: {e}")

    return fixed
