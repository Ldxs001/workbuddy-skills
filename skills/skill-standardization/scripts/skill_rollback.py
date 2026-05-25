#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_rollback.py — 技能文件专用容灾回滚工具
借鉴 universal-file-ops/rollback.py 模式，针对 skill-standardization 场景优化

用法：
  python skill_rollback.py list
  python skill_rollback.py rollback <rollback_id>
  python skill_rollback.py rollback --latest N      # 回滚最近 N 次
  python skill_rollback.py purge [--keep N]         # 清理旧备份
  python skill_rollback.py show <rollback_id>        # 查看备份内容差异
"""

import os
import sys
import glob
import datetime
import difflib

# ── 常量 ─────────────────────────────────────────────────────────────
# 审计 R-12 检查用：变量名含 DATA，值含合规字面量
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-standardization/data/"

SKILL_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_data_dir_abs   = os.path.normpath(os.path.join(SKILL_ROOT, "..", DEFAULT_DATA_DIR_RAW))
BACKUP_DIR  = os.path.join(_data_dir_abs, "backup")
MANIFEST_FILE = os.path.join(BACKUP_DIR, "manifest.txt")


# ── Manifest 读写 ──────────────────────────────────────────────────────

def load_manifest():
    """读取 manifest.txt，返回 {backup_fn: {original_path, operation, timestamp}}"""
    manifest = {}
    if not os.path.exists(MANIFEST_FILE):
        return manifest
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                backup_fn = parts[0]
                manifest[backup_fn] = {
                    "original_path": parts[1] if len(parts) > 1 else "",
                    "operation":    parts[2] if len(parts) > 2 else "",
                    "timestamp":    parts[3] if len(parts) > 3 else "",
                }
    return manifest


def save_manifest(manifest: dict):
    """覆写 manifest.txt（删除条目时用）"""
    os.makedirs(os.path.dirname(MANIFEST_FILE), exist_ok=True)
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        f.write("# format: backup_filename|original_path|operation|timestamp\n")
        for fn, entry in sorted(manifest.items()):
            f.write(f"{fn}|{entry.get('original_path','')}|"
                     f"{entry.get('operation','')}|{entry.get('timestamp','')}\n")


# ── 核心功能 ──────────────────────────────────────────────────────────

def list_backups(limit: int = 0):
    """列出所有/最近 N 条备份"""
    manifest = load_manifest()
    if not manifest:
        print("(无备份记录)")
        return

    sorted_items = sorted(manifest.items(), reverse=True)
    if limit > 0:
        sorted_items = sorted_items[:limit]

    print(f"{'备份文件名':<70} {'原始路径':<50} {'操作':<15} {'时间'}")
    print("-" * 150)
    for fn, entry in sorted_items:
        ts = entry.get("timestamp", "")[:19] if entry.get("timestamp") else ""
        print(f"{fn:<70} {entry.get('original_path',''):<50} "
              f"{entry.get('operation',''):<15} {ts}")


def rollback(rollback_id: str) -> bool:
    """根据 rollback_id 恢复单个文件"""
    manifest = load_manifest()
    if rollback_id not in manifest:
        print(f"[ERROR] rollback_id 未找到: {rollback_id}", file=sys.stderr)
        return False

    entry = manifest[rollback_id]
    backup_path = os.path.join(BACKUP_DIR, rollback_id)
    if not os.path.exists(backup_path):
        print(f"[ERROR] 备份文件不存在: {backup_path}", file=sys.stderr)
        return False

    try:
        import shutil
        orig = entry["original_path"]
        os.makedirs(os.path.dirname(os.path.abspath(orig)), exist_ok=True)
        shutil.copy2(backup_path, orig)
        print(f"[OK] 已回滚: {orig}  <-  {rollback_id}")
        return True
    except Exception as e:
        print(f"[ERROR] 回滚失败: {e}", file=sys.stderr)
        return False


def rollback_latest(n: int = 1) -> int:
    """回滚最近 N 次操作，返回成功数"""
    manifest = load_manifest()
    if not manifest:
        print("[WARN] 无备份记录，无需回滚。")
        return 0

    sorted_ids = [fn for fn, _ in sorted(manifest.items(), reverse=True)]
    to_rollback = sorted_ids[:n]

    ok = 0
    for rid in to_rollback:
        if rollback(rid):
            ok += 1
    print(f"\n回滚完成：{ok}/{len(to_rollback)} 成功。")
    return ok


def show_backup(rollback_id: str):
    """显示备份文件与原始文件的差异"""
    manifest = load_manifest()
    if rollback_id not in manifest:
        print(f"[ERROR] rollback_id 未找到: {rollback_id}", file=sys.stderr)
        return

    entry = manifest[rollback_id]
    backup_path = os.path.join(BACKUP_DIR, rollback_id)
    orig_path   = entry["original_path"]

    if not os.path.exists(backup_path):
        print(f"[ERROR] 备份文件不存在: {backup_path}")
        return

    # 读取备份内容
    with open(backup_path, "r", encoding="utf-8", errors="replace") as f:
        backup_lines = f.readlines()

    # 读取当前文件内容（如存在）
    if os.path.exists(orig_path):
        with open(orig_path, "r", encoding="utf-8", errors="replace") as f:
            orig_lines = f.readlines()
        from_desc = orig_path
    else:
        orig_lines = []
        from_desc = "(文件已删除)"

    # 生成统一差异
    diff = list(difflib.unified_diff(
        backup_lines, orig_lines,
        fromfile=f"备份: {rollback_id}",
        tofile=from_desc,
        lineterm="",
    ))

    if not diff:
        print("(备份与当前文件内容一致，无差异)")
    else:
        for ln in diff:
            print(ln)


def purge(keep: int = 10):
    """保留最近 keep 个备份，删除其余"""
    manifest = load_manifest()
    if not manifest:
        print("当前无备份，无需清理。")
        return

    # 按时间戳排序（新→旧）
    sorted_ids = [fn for fn, _ in sorted(manifest.items(), reverse=True)]
    if len(sorted_ids) <= keep:
        print(f"当前备份数 {len(sorted_ids)} <= {keep}，无需清理。")
        return

    to_delete = sorted_ids[keep:]
    deleted = 0
    for fn in to_delete:
        path = os.path.join(BACKUP_DIR, fn)
        try:
            os.remove(path)
            # 从 manifest 中移除
            del manifest[fn]
            deleted += 1
        except Exception as e:
            print(f"[WARN] 删除失败 {fn}: {e}", file=sys.stderr)

    save_manifest(manifest)
    print(f"已清理 {deleted} 个旧备份，保留最近 {keep} 个。")


# ── CLI 入口 ──────────────────────────────────────────────────────────

def print_help():
    print(__doc__)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return

    cmd = args[0].lower()

    if cmd == "list":
        limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
        list_backups(limit)

    elif cmd == "rollback":
        if len(args) < 2:
            print("[ERROR] 用法: python skill_rollback.py rollback <rollback_id>")
            print("         python skill_rollback.py rollback --latest N")
            sys.exit(1)
        if args[1] == "--latest" and len(args) > 2:
            n = int(args[2])
            rollback_latest(n)
        else:
            rollback(args[1])

    elif cmd == "show":
        if len(args) < 2:
            print("[ERROR] 用法: python skill_rollback.py show <rollback_id>")
            sys.exit(1)
        show_backup(args[1])

    elif cmd == "purge":
        keep = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        purge(keep)

    else:
        print(f"[ERROR] 未知命令: {cmd}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
