#!/usr/bin/env python3
"""
novel-context-loader — 写作前上下文加载器。

从 novel_state.json 读取当前子结构所属的上下文并格式化输出。

用法：
  python novel_context_loader.py <state_path> <L##S##>

输出：
  [写作前上下文]
  风格：...
  出场角色：...
  时间线：...
  当前子结构 <L##S##> <标题> 概述：
    <模糊概述>
"""

import os
import sys
import json


def load_context(state_path: str, sub_id: str) -> None:
    if not os.path.exists(state_path):
        print(f"ERROR: novel_state.json not found at {state_path}")
        print(f"  → 必须先运行 novel_state_manager.py init 初始化项目状态文件")
        sys.exit(1)

    # 阶段门禁：需要 ≥ stage1_done
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    _phase = state.get("current_phase", "none")
    _min = "stage1_done"
    _order = {"none": 0, "init": 10, "stage1_done": 20, "writing": 30, "chapter_done": 40, "stage3_ready": 50, "complete": 60}
    if _order.get(_phase, 0) < _order[_min]:
        print(f"ERROR: novel_context_loader 需要阶段 ≥ {_min}({_order[_min]})，当前为 {_phase}({_order.get(_phase, 0)})")
        print(f"  → 请先完成阶段1（大纲确认），执行 set-phase stage1_done")
        sys.exit(1)

    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    # 解析 L##S##
    parts = sub_id.split("S")
    if len(parts) != 2 or not parts[0].startswith("L"):
        print(f"ERROR: invalid sub_id format: {sub_id} (expected e.g. L03S04)")
        sys.exit(1)
    ch_key = parts[0]  # L03
    s_key = sub_id     # L03S04

    # 获取章节和子结构
    chapter = state.get("chapters", {}).get(ch_key, {})
    sub = chapter.get("sub_structures", {}).get(s_key, {})

    # 风格指南
    style = state.get("style_guide", {})
    genre = style.get("genre", "未设定")
    perspective = style.get("perspective", "未设定")
    narrative = style.get("narrative_mode", "未设定")

    # 角色
    characters = state.get("characters", {})
    char_list = []
    for name, info in characters.items():
        role = info.get("role", "")
        char_list.append(f"{name}({role})")

    # 时间线
    timeline = state.get("timeline", {})
    current_day = timeline.get("current_day", "未知")
    start_date = timeline.get("start_date", "未知")

    # 章节/子结构信息
    ch_title = chapter.get("title", "未知")
    ch_summary = chapter.get("summary", "")
    s_title = sub.get("title", "未知")
    s_summary = sub.get("summary", "")

    # 格式化输出
    lines = []
    lines.append("[写作前上下文]")
    lines.append(f"风格：{genre}，{perspective}，{narrative}")
    lines.append(f"出场角色：{'，'.join(char_list)}")
    lines.append(f"时间线：{start_date}，穿越后第 {current_day} 天")
    lines.append(f"当前章节 {ch_key}「{ch_title}」概述：{ch_summary}")
    lines.append(f"当前子结构 {s_key}「{s_title}」概述：{s_summary}")
    lines.append("")

    output = "\n".join(lines)
    print(output)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: novel_context_loader.py <state_path> <L##S##>")
        print("示例: novel_context_loader.py ./data/novel_state.json L03S03")
        sys.exit(1)

    load_context(state_path=sys.argv[1], sub_id=sys.argv[2])
