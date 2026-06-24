#!/usr/bin/env python3
"""
novel-continuity — 子结构间连通性补充 + 过渡段落合成。

流程：
  1. 读取指定章节目录下所有按编号排序的子结构 .txt 文件
  2. 对每对相邻子结构取前3行+后3行
  3. 读取 outline.json 中该章的模糊概述
  4. 输出 transition 段落 + 写入 continuity_report.md

用法：
  python novel_continuity.py <chapter_dir> <state_path> <report_path>
"""

import os
import sys
import json
import re


_SORTED_SUBSTRUCTURE_FILES_CACHE = {}


def _sorted_substructure_files(chapter_dir: str) -> list:
    """读取按编号排序的子结构文件列表"""
    if not os.path.isdir(chapter_dir):
        return []
    files = [f for f in os.listdir(chapter_dir) if f.endswith(".txt") and not f.startswith(".")]
    files.sort(key=lambda x: int(re.sub(r'\D', '', x.split('_')[0]) or 0))
    return [os.path.join(chapter_dir, f) for f in files]


def _read_head(filepath: str, n: int = 3) -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    # 跳过末尾的编号标记行
    while lines and (lines[-1].startswith("L") and len(lines[-1]) <= 8):
        lines.pop()
    return lines[:n]


def _read_tail(filepath: str, n: int = 3) -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        all_lines = [l.strip() for l in f.readlines() if l.strip()]
    # 跳过末尾的编号标记行
    while all_lines and (all_lines[-1].startswith("L") and len(all_lines[-1]) <= 8):
        all_lines.pop()
    return all_lines[-n:]


def _load_chapter_summary_from_state(state_path: str, ch_key: str) -> str:
    """从 novel_state.json 中读取指定章的模糊概述（chapters 为 dict，keyed by L01..L15）"""
    if not os.path.exists(state_path):
        return ""
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    chapter = data.get("chapters", {}).get(ch_key, {})
    if isinstance(chapter, dict):
        return chapter.get("summary", "")
    return ""


def generate_continuity_report(chapter_dir: str, state_path: str, report_path: str):
    if not os.path.exists(state_path):
        print(f"ERROR: novel_state.json 未找到: {state_path}")
        print(f"  → 必须先运行 novel_state_manager.py init")
        sys.exit(1)

    # 阶段门禁：需要 ≥ writing
    _order = {"none": 0, "init": 10, "stage1_done": 20, "writing": 30, "chapter_done": 40, "stage3_ready": 50, "complete": 60}
    with open(state_path, "r", encoding="utf-8") as f:
        _state = json.load(f)
    _p = _order.get(_state.get("current_phase", "none"), 0)
    if _p < 30:
        print(f"ERROR: novel_continuity 需要阶段 ≥ writing(30)，当前为 {_state.get('current_phase', 'none')}({_p})")
        print(f"  请至少完成一个子结构的写作后再执行连通性检查。")
        sys.exit(1)
    files = _sorted_substructure_files(chapter_dir)
    if len(files) < 2:
        print("SKIP: 子结构不足2个，无需连通性补充")
        return

    # 从目录名推断章节键名（如 "09_法律听证会" → "L09"）
    dir_name = os.path.basename(chapter_dir)
    ch_match = re.search(r'(\d+)', dir_name)
    ch_key = f"L{int(ch_match.group(1)):02d}" if ch_match else ""
    chapter_summary = _load_chapter_summary_from_state(state_path, ch_key)

    report_lines = []
    report_lines.append(f"# 连通性补充报告 — {dir_name}")
    report_lines.append(f"")
    report_lines.append(f"**章节概述**: {chapter_summary}")
    report_lines.append(f"")
    report_lines.append(f"| 过渡段 | 前段末3行 | 后段首3行 | 衔接判定 |")
    report_lines.append(f"|--------|---------|---------|---------|")

    transitions_needed = False

    for i in range(len(files) - 1):
        f_prev = files[i]
        f_next = files[i + 1]
        prev_name = os.path.splitext(os.path.basename(f_prev))[0]
        next_name = os.path.splitext(os.path.basename(f_next))[0]
        prev_tail = _read_tail(f_prev, 3)
        next_head = _read_head(f_next, 3)

        prev_tail_text = " | ".join(prev_tail[-3:]) if prev_tail else "(空)"
        next_head_text = " | ".join(next_head[:3]) if next_head else "(空)"

        report_lines.append(f"| {prev_name} → {next_name} | {prev_tail_text[:40]}... | {next_head_text[:40]}... | 待判断 |")

        # 检查衔接是否自然
        need_transition = False
        if prev_tail and next_head:
            last_prev = prev_tail[-1] if prev_tail else ""
            first_next = next_head[0] if next_head else ""
            if last_prev and first_next:
                # 如果末句和首句的主题不同，需要过渡
                if len(set(last_prev.split()) & set(first_next.split())) < 2:
                    need_transition = True

        if need_transition:
            transitions_needed = True

    report_lines.append(f"")
    report_lines.append(f"## 过渡段落")

    if not transitions_needed:
        report_lines.append(f"")
        report_lines.append(f"各子结构之间逻辑链完整，无需额外过渡段落。")
    else:
        for i in range(len(files) - 1):
            f_prev = files[i]
            f_next = files[i + 1]
            prev_name = os.path.splitext(os.path.basename(f_prev))[0]
            next_name = os.path.splitext(os.path.basename(f_next))[0]
            prev_tail = _read_tail(f_prev, 3)
            next_head = _read_head(f_next, 3)

            report_lines.append(f"")
            report_lines.append(f"### {prev_name} → {next_name}")
            report_lines.append(f"")
            if prev_tail and next_head:
                report_lines.append(f"**前段结尾**: {' '.join(prev_tail[-3:])}")
                report_lines.append(f"**后段开头**: {' '.join(next_head[:3])}")
            report_lines.append(f"*（此处应由 LLM 在现场生成过渡段落）*")

    report_lines.append(f"")
    report_lines.append(f"---")
    report_lines.append(f"*报告由 novel-continuity 生成*")

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        f.flush()
        os.fsync(f.fileno())

    print(f"OK report={report_path} transitions={transitions_needed}")

    return transitions_needed


def write_transitions_json(chapter_dir: str, state_path: str, report_path: str) -> str:
    """
    Auto-fix 模式：生成 _transitions.json（列出所有需要过渡的子结构对）。
    返回 transitions JSON 文件路径，或空字符串表示无需过渡。
    """
    if not os.path.isdir(chapter_dir):
        return ""
    files = _sorted_substructure_files(chapter_dir)
    if len(files) < 2:
        return ""

    transitions = []

    for i in range(len(files) - 1):
        f_prev = files[i]
        f_next = files[i + 1]
        prev_name = os.path.splitext(os.path.basename(f_prev))[0]
        next_name = os.path.splitext(os.path.basename(f_next))[0]
        prev_tail = _read_tail(f_prev, 3)
        next_head = _read_head(f_next, 3)

        # 检查衔接是否需要过渡
        need_transition = False
        if prev_tail and next_head:
            last_prev = prev_tail[-1] if prev_tail else ""
            first_next = next_head[0] if next_head else ""
            if last_prev and first_next:
                if len(set(last_prev.split()) & set(first_next.split())) < 2:
                    need_transition = True

        if need_transition:
            transitions.append({
                "from_file": prev_name,
                "to_file": next_name,
                "from_path": f_prev,
                "to_path": f_next,
                "prev_tail": prev_tail[-3:] if prev_tail else [],
                "next_head": next_head[:3] if next_head else [],
                "transition_text": ""  # 由 LLM 填充
            })

    if not transitions:
        return ""

    # 写入 transitions JSON
    report_dir = os.path.dirname(report_path)
    json_path = os.path.join(report_dir, "_transitions.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transitions, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())

    print(f"OK auto-fix transitions={len(transitions)} json={json_path}")
    print(f"  → 请生成过渡段落文本后，运行本脚本 write-transition 写入")
    print(f"  → 或由 workflow_engine 自动处理")

    return json_path


def cmd_write_transition(chapter_dir: str, from_name: str, to_name: str, text: str):
    """
    将一个过渡段落到指定子结构之间。
    创建 _transition_{from}_{to}.txt 文件。
    """
    filename = f"_transition_{from_name}_{to_name}.txt"
    filepath = os.path.join(chapter_dir, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(f"OK 过渡段落已写入: {filepath}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "generate":
        # novel_continuity.py generate <chapter_dir> <state_path> <report_path> [--auto-fix]
        if len(sys.argv) < 5:
            print("用法: generate <chapter_dir> <state_path> <report_path> [--auto-fix]")
            sys.exit(1)
        transitions_needed = generate_continuity_report(
            chapter_dir=sys.argv[2],
            state_path=sys.argv[3],
            report_path=sys.argv[4]
        )
        if len(sys.argv) >= 6 and sys.argv[5] == "--auto-fix" and transitions_needed:
            write_transitions_json(
                chapter_dir=sys.argv[2],
                state_path=sys.argv[3],
                report_path=sys.argv[4]
            )

    elif command == "write-transition":
        # novel_continuity.py write-transition <chapter_dir> <from_name> <to_name> <text>
        if len(sys.argv) < 6:
            print("用法: write-transition <chapter_dir> <from_name> <to_name> <text>")
            sys.exit(1)
        cmd_write_transition(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)
