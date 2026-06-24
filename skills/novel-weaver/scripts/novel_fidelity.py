#!/usr/bin/env python3
"""
novel-fidelity — 大纲忠实度报告生成器。

逐条对比大纲标题与实际写作内容，标记偏差位置和等级。

偏差等级：
  - PASS: 实际内容与大纲描述一致
  - INFO: 有偏差但可接受（细节补充/顺序微调）
  - WARN: 实质性偏差（新增场景/删除大纲内容/顺序调换）
  - ERROR: 完全偏离大纲描述

用法：
  python novel_fidelity.py <project_dir>
"""

import os
import sys
import json
import re


def _load_chapters(project_dir: str) -> dict:
    """读取已完成的章节内容"""
    chapters_dir = os.path.join(project_dir, "chapters")
    result = {}
    if not os.path.isdir(chapters_dir):
        return result
    for ch_dir in sorted(os.listdir(chapters_dir)):
        ch_path = os.path.join(chapters_dir, ch_dir)
        if not os.path.isdir(ch_path):
            continue
        ch_text = ""
        sub_files = sorted([f for f in os.listdir(ch_path) if f.endswith(".txt")])
        for sf in sub_files:
            with open(os.path.join(ch_path, sf), "r", encoding="utf-8") as f:
                ch_text += f.read() + "\n"
        result[ch_dir] = ch_text[:500]  # 前500字作为摘要样本
    return result


def generate_report(project_dir: str):
    outline_path = os.path.join(project_dir, "data", "outline.json")
    if not os.path.exists(outline_path):
        print(f"ERROR: novel_state.json 未找到（尝试从 {outline_path} 加载）")
        print(f"  → 阶段1未完成或项目数据目录不完整。")
        sys.exit(1)

    # 阶段门禁：需要 ≥ stage3_ready
    _order = {"none": 0, "init": 10, "stage1_done": 20, "writing": 30, "chapter_done": 40, "stage3_ready": 50, "complete": 60}
    with open(outline_path, "r", encoding="utf-8") as f:
        _state = json.load(f)
    _p = _order.get(_state.get("current_phase", "none"), 0)
    if _p < 50:
        print(f"ERROR: novel_fidelity 需要阶段 ≥ stage3_ready(50)，当前为 {_state.get('current_phase', 'none')}({_p})")
        print(f"  全文写作未完成，不能生成大纲忠实度报告。")
        sys.exit(1)

    with open(outline_path, "r", encoding="utf-8") as f:
        outline = json.load(f)

    chapters = outline.get("chapters", [])
    actual = _load_chapters(project_dir)

    report_lines = []
    report_lines.append(f"# 大纲忠实度报告")
    report_lines.append(f"")
    report_lines.append(f"| 章节 | 大纲概述 | 实际摘要 | 偏差等级 |")
    report_lines.append(f"|------|---------|---------|---------|")

    pass_count = 0
    info_count = 0
    warn_count = 0
    error_count = 0

    for ch in chapters:
        ch_num = ch.get("chapter_number", 0)
        ch_title = ch.get("title", "")
        summary = ch.get("summary", "")
        themes = ch.get("themes", [])

        # 查找对应的实际章节目录
        ch_dir_key = None
        for key in actual:
            if f"{ch_num:02d}" in key or ch_title in key:
                ch_dir_key = key
                break

        actual_sample = actual.get(ch_dir_key, "")
        actual_short = actual_sample[:100].replace("\n", " ") if actual_sample else "(未完成)"

        # 简单偏差检测
        level = "PASS"
        detail = "内容一致"

        if not actual_sample:
            level = "ERROR"
            detail = "章节未完成"
            error_count += 1
        else:
            # 检查主题词是否出现在正文中
            theme_hits = sum(1 for t in themes if t in actual_sample)
            if theme_hits == 0 and themes:
                level = "WARN"
                detail = f"大纲主题词[{', '.join(themes)}]未在正文中出现"
                warn_count += 1
            elif theme_hits < len(themes) / 2:
                level = "INFO"
                detail = f"部分主题词未出现（{theme_hits}/{len(themes)}）"
                info_count += 1
            else:
                level = "PASS"
                pass_count += 1

        ch_label = f"Ch{ch_num} {ch_title}"
        report_lines.append(f"| {ch_label} | {summary[:40]}... | {actual_short[:40]}... | {level} |")

    report_lines.append(f"")
    report_lines.append(f"## 统计")
    report_lines.append(f"- ✅ PASS: {pass_count}")
    report_lines.append(f"- ℹ️ INFO: {info_count}")
    report_lines.append(f"- ⚠️ WARN: {warn_count}")
    report_lines.append(f"- ❌ ERROR: {error_count}")
    report_lines.append(f"")
    report_lines.append(f"---")
    report_lines.append(f"*报告由 novel-fidelity 生成*")

    report_path = os.path.join(project_dir, "data", "fidelity_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        f.flush()
        os.fsync(f.fileno())
    print(f"OK report={report_path} pass={pass_count} info={info_count} warn={warn_count} error={error_count}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: novel_fidelity.py <project_dir>")
        sys.exit(1)
    generate_report(sys.argv[1])
