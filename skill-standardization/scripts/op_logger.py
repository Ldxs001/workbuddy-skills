#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
op_logger.py — skill-standardization 操作日志
借鉴 universal-file-ops/utils.py::log_operation 模式

日志记录到 data/logs/ops.log（JSON Lines 格式，每行一个 JSON）
每条日志包含：ts / operation / file / success / rollback_id / detail

用法（供其他脚本调用）：
  from op_logger import log_op, log_audit_result
  log_op("audit", "path/to/SKILL.md", True, rollback_id="...", detail="...")
  log_audit_result(audit_result_dict)
"""

import os
import sys
import json
import datetime

# ── 常量 ─────────────────────────────────────────────────────────
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-standardization/data/"

SKILL_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_data_dir_abs = os.path.normpath(os.path.join(SKILL_ROOT, "..", DEFAULT_DATA_DIR_RAW))
LOGS_DIR = os.path.join(_data_dir_abs, "logs")
OPS_LOG  = os.path.join(LOGS_DIR, "ops.log")


# ── 初始化 ────────────────────────────────────────────────────────

def _ensure_logs_dir():
    os.makedirs(LOGS_DIR, exist_ok=True)


# ── 核心接口 ──────────────────────────────────────────────────────

def log_op(operation: str, file_path: str, success: bool,
            rollback_id: str = "", detail: str = "",
            temp_files: list = None, backup_files: list = None) -> None:
    """
    记录一条操作日志到 ops.log（JSON Lines 格式）。
    temp_files: 本次操作产生的临时文件路径列表
    backup_files: 本次操作产生的备份文件路径列表
    """
    _ensure_logs_dir()
    entry = {
        "ts":            datetime.datetime.now().isoformat(),
        "operation":     operation,
        "file":          os.path.abspath(file_path) if file_path else "",
        "success":       success,
        "rollback_id":   rollback_id or "",
        "temp_files":    temp_files or [],
        "backup_files":  backup_files or [],
        "detail":         detail or "",
    }
    try:
        with open(OPS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[WARN] 日志写入失败: {e}", file=sys.stderr)


def log_audit_result(audit_result: dict) -> None:
    """
    从 audit_skill() 返回结果中提取信息，记录审计日志。
    audit_result: {"rule_id", "rule_name", "severity", "passed", "skipped", "detail", ...}
    """
    rule_id      = audit_result.get("rule_id", "unknown")
    rule_name    = audit_result.get("rule_name", "")
    passed       = audit_result.get("passed", False)
    skipped      = audit_result.get("skipped", False)
    detail       = audit_result.get("detail", "")
    rollback_id  = audit_result.get("rollback_id", "")
    fix          = audit_result.get("fix", {})

    status_str = "PASS" if passed else ("SKIP" if skipped else "FAIL")
    detail_short = (detail or "")[:200]   # 截断过长 detail

    log_op(
        operation=f"audit_{rule_id}",
        file_path="",
        success=passed or skipped,
        rollback_id=rollback_id,
        detail=f"{rule_id} {status_str} — {rule_name} | {detail_short}",
    )


def read_recent_logs(n: int = 20) -> list:
    """读取最近 N 条日志，返回 list[dict]"""
    if not os.path.exists(OPS_LOG):
        return []
    with open(OPS_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entries = []
    for ln in lines[-n:]:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        try:
            entries.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return entries


def print_recent_logs(n: int = 20) -> None:
    """格式化打印最近 N 条日志"""
    entries = read_recent_logs(n)
    if not entries:
        print("(无日志记录)")
        return

    print(f"{'时间':<22} {'操作':<25} {'文件':<40} {'结果':<8} {'详情'}")
    print("-" * 150)
    for e in entries:
        ts     = (e.get("ts") or "")[:19]
        op      = (e.get("operation") or "")[:24]
        fp      = (e.get("file") or "")[:39]
        success = e.get("success")
        status  = "✅" if success else "❌"
        detail  = (e.get("detail") or "")[:60]
        print(f"{ts:<22} {op:<25} {fp:<40} {status:<8} {detail}")


# ── CLI 入口 ──────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        print("\n用法:")
        print("  python op_logger.py recent [N]     # 查看最近 N 条日志（默认 20）")
        print("  python op_logger.py log <op> <file> <success> [detail]  # 手动记录")
        return

    cmd = args[0].lower()
    if cmd == "recent":
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
        print_recent_logs(n)
    elif cmd == "log" and len(args) >= 4:
        operation = args[1]
        file_path = args[2]
        success   = args[3].lower() in ("true", "1", "yes")
        detail    = args[4] if len(args) > 4 else ""
        log_op(operation, file_path, success, detail=detail)
        print(f"[OK] 已记录日志: {operation} {'成功' if success else '失败'}")
    else:
        print(f"[ERROR] 未知命令或参数不足: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
