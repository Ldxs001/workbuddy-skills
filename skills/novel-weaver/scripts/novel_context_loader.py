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

ATOMIC_WRITER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novel_atomic_writer.py")


def _find_sub_file(state_path: str, ch_key: str, s_key: str) -> str | None:
    """尝试定位子结构文件路径"""
    project_dir = os.path.dirname(os.path.dirname(state_path))
    chapters_dir = os.path.join(project_dir, "chapters")
    ch_num = ch_key.replace("L", "")
    if not os.path.isdir(chapters_dir):
        return None
    for d in sorted(os.listdir(chapters_dir)):
        if d.startswith(ch_num):
            candidate = os.path.join(chapters_dir, d, f"{ch_key}{s_key}.txt")
            if os.path.exists(candidate):
                return candidate
    return None


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

    # 硬检查：子结构必须已通过 add-sub 注册到 state（title 为空表示未注册）
    if not sub.get("title"):
        print(f"ERROR: 子结构 {s_key} 未在 novel_state.json 中注册")
        print(f"  → chapters.{ch_key}.sub_structures.{s_key} 不存在或 title 为空")
        print(f"  → 必须先运行: novel_state_manager.py add-sub <path> {ch_key} {s_key} <title> <summary>")
        print(f"  → 或使用: novel_workflow_engine.py plan-chapter <path> {ch_key} '<subs_json>'")
        sys.exit(1)

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
    s_tone = sub.get("tone", "")

    # 格式化输出 — 命题指令格式
    lines = []
    lines.append("=" * 55)
    lines.append("  📌 命题作文 — 严格按以下要求写作")
    lines.append("=" * 55)
    lines.append(f"  标题：{s_title}")
    lines.append(f"  概述：{s_summary}")
    if s_tone:
        lines.append(f"  情绪基调：{s_tone}")
    lines.append(f"  字数上限：200 行（自然段落结束）")
    lines.append(f"  要求：严格按照标题和概述写作，不可偏离命题")
    lines.append("=" * 55)
    lines.append("")
    lines.append("[背景参考]")
    lines.append(f"  文体风格：{genre}，{perspective}，{narrative}")
    lines.append(f"  出场角色：{'，'.join(char_list)}")
    lines.append(f"  时间线：{start_date}，穿越后第 {current_day} 天")
    lines.append(f"  当前章节：{ch_key}「{ch_title}」— {ch_summary}")
    lines.append(f"  当前子结构：{ch_key}{s_key}「{s_title}」")
    lines.append("")

    # ── 断点续写检测 ──
    sub_file = _find_sub_file(state_path, ch_key, s_key)
    if sub_file:
        # 检查 .progress 文件
        progress_path = sub_file + ".progress"
        written_lines = 0
        if os.path.exists(progress_path):
            with open(progress_path, "r", encoding="utf-8") as pf:
                try:
                    written_lines = int(pf.read().strip())
                except ValueError:
                    written_lines = 0

        if written_lines > 0:
            # 已写内容，断点续写模式
            lines.append("[续写模式 — 已写内容]")
            lines.append(f"  已写 {written_lines} 行（上限 200 行），剩余 {200 - written_lines} 行")
            # 读取末5行作为续写锚点
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, ATOMIC_WRITER_SCRIPT, "tail", sub_file, "5"],
                    capture_output=True, text=True, encoding="utf-8"
                )
                if result.returncode == 0 and result.stdout.strip():
                    tail_lines = json.loads(result.stdout.strip())
                    if tail_lines:
                        lines.append(f"  末5行锚点：")
                        for tl in tail_lines:
                            lines.append(f"    {tl}")
            except Exception:
                pass
            lines.append(f"  → 请从断点继续写作，保持命题风格一致")
            lines.append(f"  → 写完后运行 atomic_writer finalize {sub_file} {ch_key}{s_key}")
        else:
            lines.append("[新写模式]")
            lines.append(f"  → 请开始写作，遵循命题要求")
    else:
        lines.append("[新写模式]")
        lines.append(f"  → 请开始写作，遵循命题要求")

    lines.append("")

    output = "\n".join(lines)
    print(output)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: novel_context_loader.py <state_path> <L##S##>")
        print("示例: novel_context_loader.py ./data/novel_state.json L03S03")
        sys.exit(1)

    load_context(state_path=sys.argv[1], sub_id=sys.argv[2])
