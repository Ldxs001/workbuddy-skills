#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_dir_checker.py — R-22 数据目录规范检查
v2.33.0

检查技能安装目录是否包含应归属数据目录的文件，
并在 --fix 模式下自动迁移到 skills/.standardization/<skill>/

参考 universal-file-ops 设计：
- 操作前自动备份
- 操作日志记录
- 支持回滚
"""

import os
import shutil
import json
import datetime
from pathlib import Path


# ── 备份目录 ─────────────────────────────────────────────────────
_BACKUP_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    ".standardization", "skill-standardization", "data", "backup"
)

# ── 日志目录 ─────────────────────────────────────────────────────
_LOG_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    ".standardization", "skill-standardization", "data", "logs"
)

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


def _log_operation(log_path, operation, detail):
    """记录操作日志（参考 universal-file-ops 设计）"""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {operation}: {detail}\n")


# ── 应留在安装目录的目录（标准目录）────────────────────────────
_KEEP_DIRS_IN_INSTALL = {
    "scripts",
    "references",
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
        # 标准目录（scripts/, references/）→ 允许留在安装目录
        if os.path.isdir(full) and entry in _KEEP_DIRS_IN_INSTALL:
            ok.append(entry)
            continue
        # 明确应留在安装目录（文件）
        if os.path.isfile(full) and entry in _KEEP_IN_INSTALL:
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
        # 默认：未知文件/目录 → 违规
        kind = "dir" if os.path.isdir(full) else "file"
        to_migrate.append((kind, entry, "未知项，不应出现在安装目录"))

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
            "detail": f"{filepath}:1 - R-22 跳过：无法确定技能目录",
        }

    # 读取 data_dir 声明
    data_dir_declared = fm.get("data_dir", "") if fm else ""
    if not data_dir_declared:
        # 尝试从 SHELL.md 推断
        return {
            "passed": False, "skipped": False,
            "detail": f"{filepath}:1 - R-22 FAIL — 未在 frontmatter 中声明 data_dir: "
                      "(应声明数据目录，如 data_dir: ../.standardization/git-sync/)",
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
    }


def fix_data_dir_compliance(skill_dir: str, dry_run: bool = False) -> int:
    """
    自动修复 R-22 违规（参考 universal-file-ops 设计）：
    1. 如果缺少 data_dir: 声明，添加到 SKILL.md frontmatter
    2. 如果有文件需要迁移，自动迁移到数据目录
    3. 操作前自动备份，记录日志，支持回滚

    返回: 修复的文件数
    """
    fixed = 0
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0

    # 日志路径
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(_LOG_ROOT, f"r22_fix_{ts}.log")
    backup_root = os.path.join(_BACKUP_ROOT, f"r22_{ts}")
    os.makedirs(backup_root, exist_ok=True)
    os.makedirs(_LOG_ROOT, exist_ok=True)

    _log_operation(log_file, "START", f"skill_dir={skill_dir}, dry_run={dry_run}")

    # 读取 frontmatter
    from .utils import parse_simple_yaml_frontmatter
    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()
    fm, body = parse_simple_yaml_frontmatter(content)

    if fm is None:
        _log_operation(log_file, "ERROR", "无法解析 SKILL.md frontmatter")
        return 0

    install_path = Path(skill_dir).resolve()
    dirname = os.path.basename(install_path)

    # 修复 1: 添加 data_dir: 声明
    if "data_dir" not in fm:
        new_val = f"../.standardization/{dirname}/"
        if not dry_run:
            fm["data_dir"] = new_val
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
            _log_operation(log_file, "FIX", f"添加 data_dir: {new_val} 到 {skill_md}")
        else:
            _log_operation(log_file, "DRY-RUN", f"将添加 data_dir: {new_val} 到 SKILL.md")
        print(f"  [OK] R-22 fix: 已{'计划' if dry_run else '实际'}添加 data_dir: {new_val}")
        fixed += 1

    # 修复 2: 迁移文件
    data_dir_declared = fm.get("data_dir", "")
    if not data_dir_declared:
        _log_operation(log_file, "SKIP", "data_dir 未声明，跳过文件迁移")
        _log_operation(log_file, "END", f"共修复 {fixed} 项")
        return fixed

    data_dir_path = (install_path / data_dir_declared).resolve()
    os.makedirs(data_dir_path, exist_ok=True)

    classification = _classify_files(skill_dir, str(data_dir_path))

    migrated = []  # 记录成功迁移的文件，用于回滚

    for kind, entry, reason in classification["to_migrate"]:
        src = os.path.join(skill_dir, entry)
        dst = os.path.join(data_dir_path, entry)
        backup_path = os.path.join(backup_root, entry)

        if os.path.exists(dst):
            _log_operation(log_file, "SKIP", f"目标已存在: {dst}")
            if not dry_run:
                print(f"  [skip] 目标已存在: {dst}")
            continue

        if dry_run:
            _log_operation(log_file, "DRY-RUN", f"将迁移: {src} → {dst} ({reason})")
            print(f"  [plan] 将迁移: {entry} → {data_dir_path} ({reason})")
            fixed += 1
            continue

        # 备份（复制）
        try:
            if kind == "dir":
                shutil.copytree(src, backup_path)
            else:
                shutil.copy2(src, backup_path)
            _log_operation(log_file, "BACKUP", f"{src} → {backup_path}")
        except Exception as e:
            _log_operation(log_file, "ERROR", f"备份失败 {src}: {e}")
            print(f"  [X] 备份失败 {entry}: {e}，跳过")
            continue

        # 迁移（移动）
        try:
            if kind == "dir":
                shutil.move(src, dst)
            else:
                shutil.move(src, dst)
            _log_operation(log_file, "MIGRATE", f"{src} → {dst} ({reason})")
            print(f"  [OK] 已迁移: {entry} → {data_dir_path}")
            migrated.append((src, dst, backup_path, kind))
            fixed += 1
        except Exception as e:
            _log_operation(log_file, "ERROR", f"迁移失败 {src}: {e}，正在回滚...")
            print(f"  [X] 迁移失败 {entry}: {e}，正在回滚...")
            # 回滚：从备份恢复
            try:
                if kind == "dir":
                    if os.path.exists(src):
                        shutil.rmtree(src)
                    shutil.copytree(backup_path, src)
                else:
                    if os.path.exists(src):
                        os.remove(src)
                    shutil.copy2(backup_path, src)
                _log_operation(log_file, "ROLLBACK", f"已从备份恢复: {src}")
                print(f"  [OK] 已回滚: {entry}")
            except Exception as re:
                _log_operation(log_file, "ERROR", f"回滚失败 {src}: {re}")
                print(f"  [X] 回滚失败 {entry}: {re}")

    _log_operation(log_file, "END", f"共修复 {fixed} 项，日志: {log_file}")
    return fixed
