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

# ── 路径常量（通用写法，适用于任何安装结构）───────────────────
_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR   = os.path.dirname(_SCRIPT_DIR)
_SKILLS_ROOT = os.path.dirname(_SKILL_DIR)
SKILL_NAME    = os.path.basename(_SKILL_DIR)
DATA_DIR      = os.path.join(_SKILLS_ROOT, ".standardization", SKILL_NAME)
LOGS_DIR      = os.path.join(DATA_DIR, "logs")
OPS_LOG       = os.path.join(LOGS_DIR, "ops.log")


# ── 初始化 ────────────────────────────────────────────────────────

def _ensure_logs_dir():
    os.makedirs(LOGS_DIR, exist_ok=True)


# ── 核心接口 ──────────────────────────────────────────────────────

def log_op(operation, file_path, success, rollback_id=None, detail=None):
    """记录一条操作日志到 ops.log"""
    _ensure_logs_dir()
    entry = {
        "ts": datetime.datetime.now().isoformat(),
        "operation": operation,
        "file": file_path,
        "success": bool(success),
    }
    if rollback_id:
        entry["rollback_id"] = rollback_id
    if detail:
        entry["detail"] = detail
    with open(OPS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_audit_result(result_dict):
    """将审计结果字典追加写入 ops.log"""
    _ensure_logs_dir()
    entry = {
        "ts": datetime.datetime.now().isoformat(),
        "operation": "audit_result",
        "result": result_dict,
    }
    with open(OPS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_logs(n=50):
    """读取最近 n 条日志记录，返回 list[dict]"""
    if not os.path.exists(OPS_LOG):
        return []
    entries = []
    with open(OPS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-n:]


if __name__ == "__main__":
    # 简单自测
    log_op("test", "SKILL.md", True, detail="self-test")
    print("_ops.log written:", OPS_LOG)
    for e in read_logs(5):
        print(e)
