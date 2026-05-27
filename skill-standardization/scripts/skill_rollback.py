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


# ── 新增：整体备份 / 临时文件记录 / 事后清理 ─────────────────────────────

def backup_skill(skill_dir: str, operation: str) -> str | None:
    """
    更新/改造前对目标技能目录执行整体备份。
    命名格式：<skill-dir>_bak_<operation>_<YYYYMMDD_HHMMSS>
    备份记录在 op_logger 日志（rollback_id 字段）。
    """
    if not os.path.isdir(skill_dir):
        print(f"[ERROR] 目标技能目录不存在: {skill_dir}", file=sys.stderr)
        return None

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    skill_name = os.path.basename(os.path.normpath(skill_dir))
    backup_name = f"{skill_name}_bak_{operation}_{ts}"
    # 正确计算：skill_dir → skills_root → .standardization/<skill-name>/backup/
    # skill_dir = skills/<skill-name>/
    # skills_root = skills/
    skill_abs = os.path.abspath(skill_dir)
    skills_root = os.path.dirname(skill_abs)
    std_dir = os.path.join(skills_root, ".standardization", skill_name, "backup")
    os.makedirs(std_dir, exist_ok=True)
    backup_path = os.path.join(std_dir, backup_name)

    try:
        import shutil
        shutil.copytree(skill_dir, backup_path)
        print(f"[OK] 整体备份已创建: {backup_path}")

        # 记录到 op_logger
        try:
            from op_logger import log_op
            log_op(
                operation=f"backup_skill_{operation}",
                file_path=skill_dir,
                success=True,
                rollback_id=backup_path,
                detail=f"整体备份: {backup_path}",
            )
        except Exception as log_err:
            print(f"[WARN] op_logger 记录失败（非致命）: {log_err}", file=sys.stderr)

        return backup_path
    except Exception as e:
        print(f"[ERROR] 整体备份失败: {e}", file=sys.stderr)
        return None


def record_temp_file(temp_path: str, operation: str) -> None:
    """
    记录操作过程中产生的临时文件到 op_logger 日志（temp_files 字段）。
    临时文件在操作完成后由 cleanup() 统一清除。
    """
    try:
        from op_logger import log_op
        log_op(
            operation=f"temp_file_{operation}",
            file_path=temp_path,
            success=True,
            detail=f"临时文件: {temp_path}",
        )
        print(f"[OK] 临时文件已记录: {temp_path}")
    except Exception as e:
        print(f"[WARN] 临时文件记录失败: {e}", file=sys.stderr)


def cleanup(operation_id: str = "", keep_backups: int = 10) -> int:
    """
    操作后清理：
      1. 清除 data/temp/ 下所有临时文件（会话级，立即清除）
      2. 保留最新 keep_backups 个备份，其余清除
      3. 如指定 operation_id，仅清理该操作的临时文件（将来扩展）

    返回清除的文件总数。
    """
    removed = 0

    # 1. 清理临时文件目录
    temp_dir = os.path.join(_data_dir_abs, "temp")
    if os.path.exists(temp_dir):
        import shutil
        try:
            for fname in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, fname)
                if os.path.isfile(fpath):
                    os.remove(fpath)
                    removed += 1
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                    removed += 1
            print(f"[OK] 临时文件已清理: {temp_dir}（{removed} 项）")
        except Exception as e:
            print(f"[WARN] 临时文件清理失败: {e}", file=sys.stderr)
    else:
        print(f"[INFO] 临时文件目录不存在，跳过: {temp_dir}")

    # 2. 清理过期备份（保留最新 keep_backups 个）
    try:
        removed += purge(keep=keep_backups)
    except Exception as e:
        print(f"[WARN] 过期备份清理失败: {e}", file=sys.stderr)

    print(f"[OK] 清理完成，共清除 {removed} 项（保留最新 {keep_backups} 个备份）")
    return removed


# ── CLI 入口 ──────────────────────────────────────────────────────────

def print_help():
    print(__doc__)
    print("\n新增命令（v2.36.0）：")
    print("  python skill_rollback.py backup-skill <skill-dir> <operation>")
    print("                          → 整体备份目标技能目录")
    print("  python skill_rollback.py record-temp <temp-path> <operation>")
    print("                          → 记录临时文件到 op_logger")
    print("  python skill_rollback.py cleanup [--keep N] [--op <operation_id>]")
    print("                          → 清理临时文件和过期备份（默认保留 10 个备份）")
    print("\n原有命令：")
    print("  python skill_rollback.py list [N]")
    print("  python skill_rollback.py rollback <rollback_id>")
    print("  python skill_rollback.py rollback --latest N")
    print("  python skill_rollback.py show <rollback_id>")
    print("  python skill_rollback.py purge [--keep N]")


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

    elif cmd == "backup-skill":
        if len(args) < 3:
            print("[ERROR] 用法: python skill_rollback.py backup-skill <skill-dir> <operation>")
            sys.exit(1)
        backup_skill(args[1], args[2])
        print(f"[OK] 整体备份完成: {args[1]}")

    elif cmd == "record-temp":
        if len(args) < 3:
            print("[ERROR] 用法: python skill_rollback.py record-temp <temp-path> <operation>")
            sys.exit(1)
        record_temp_file(args[1], args[2])
        print(f"[OK] 临时文件已记录: {args[1]}")

    elif cmd == "cleanup":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--keep", type=int, default=10)
        ap.add_argument("--op", default="")
        parsed = ap.parse_args(args[1:])
        cleanup(parsed.op, parsed.keep)

    else:
        print(f"[ERROR] 未知命令: {cmd}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
