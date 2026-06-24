#!/usr/bin/env python3
"""
novel-timeline — 时间线追踪工具。

每章结束时记录故事内时间进展，维护全局 timeline.json。
支持断电恢复：每次写入后 fsync。

用法：
  python novel_timeline.py init <project_dir> <start_date>      # 初始化时间线
  python novel_timeline.py add <project_dir> <chapter> <days_elapsed> <summary>
  python novel_timeline.py get <project_dir>                    # 查看完整时间线
"""

import os
import sys
import json


def _tl_path(project_dir: str) -> str:
    return os.path.join(project_dir, "data", "timeline.json")


def init_timeline(project_dir: str, start_date: str):
    path = _tl_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "project": os.path.basename(project_dir),
        "start_date": start_date,
        "entries": []
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    print(f"OK timeline initialized at {path}")


def _state_path(project_dir: str) -> str:
    return os.path.join(project_dir, "data", "novel_state.json")


def add_entry(project_dir: str, chapter: str, days_elapsed: int, summary: str):
    path = _tl_path(project_dir)
    state_path = _state_path(project_dir)
    if not os.path.exists(state_path):
        print(f"ERROR: novel_state.json 未初始化（预期路径 {state_path}）")
        print(f"  → 必须在阶段1完成后运行 init")
        sys.exit(1)

    # 阶段门禁：从 novel_state.json 读取 current_phase
    _order = {"none": 0, "init": 10, "stage1_done": 20, "writing": 30, "chapter_done": 40, "stage3_ready": 50, "complete": 60}
    with open(state_path, "r", encoding="utf-8") as f:
        _state = json.load(f)
    _p = _order.get(_state.get("current_phase", "none"), 0)
    if _p < 20:
        print(f"ERROR: novel_timeline 需要阶段 ≥ stage1_done(20)，当前为 {_state.get('current_phase', 'none')}({_p})")
        print(f"  请先完成大纲确认。")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    entries = data.setdefault("entries", [])
    entry_number = len(entries) + 1
    
    entry = {
        "entry": entry_number,
        "chapter": chapter,
        "days_since_start": days_elapsed,
        "summary": summary
    }
    entries.append(entry)
    data["entries"] = entries
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    print(f"OK entry added: {chapter} @ day {days_elapsed}")


def get_timeline(project_dir: str):
    path = _tl_path(project_dir)
    if not os.path.exists(path):
        print("ERROR: timeline not initialized")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: novel_timeline.py <init|add|get> <project_dir> [args...]")
        sys.exit(1)

    command = sys.argv[1]
    project_dir = sys.argv[2]

    if command == "init":
        start_date = sys.argv[3] if len(sys.argv) >= 4 else "未知"
        init_timeline(project_dir, start_date)

    elif command == "add":
        chapter = sys.argv[3] if len(sys.argv) >= 4 else ""
        days = int(sys.argv[4]) if len(sys.argv) >= 5 else 0
        summary = sys.argv[5] if len(sys.argv) >= 6 else ""
        add_entry(project_dir, chapter, days, summary)

    elif command == "get":
        get_timeline(project_dir)

    else:
        print(f"未知命令: {command}")
        sys.exit(1)
