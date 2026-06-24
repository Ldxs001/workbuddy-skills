#!/usr/bin/env python3
"""
novel-causality-check — 因果链验证钩子。

不做因果正确性判断（纯统计做不到），而是：
  1. 从 novel_state.json 中提取大纲/子结构，格式化为因果链矩阵
  2. 输出每两相邻项之间是否缺失显式因果描述
  3. 返回 PASS（每链都OK）/ WARN（有链节需要补充因果描述）/ ERROR（有链节完全空白）

两个模式：
  chapter-outline  <state_path>                     — 检查大纲（章）级别因果链
  sub-structure    <state_path> <ch_key>             — 检查指定章的子结构级别因果链

用法：
  python novel_causality_check.py chapter-outline <state_path>
  python novel_causality_check.py sub-structure <state_path> <ch_key>
"""

import os
import sys
import json

PHASE_ORDER = {
    "none": 0, "init": 10, "stage1_done": 20,
    "writing": 30, "chapter_done": 40,
    "stage3_ready": 50, "complete": 60
}


def _load_state(path: str) -> dict:
    if not os.path.exists(path):
        print(f"ERROR: novel_state.json not found at {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _tag(level: str) -> str:
    return {"PASS": "✅", "WARN": "⚠️", "ERROR": "❌"}.get(level, "❓")


def cmd_chapter_outline(state_path: str):
    """检查大纲（章）级别的因果链完整性"""
    state = _load_state(state_path)

    chapters_raw = state.get("chapters", {})
    if isinstance(chapters_raw, list):
        # 兼容 list 格式 → 转 dict
        chapters = {}
        for ch in chapters_raw:
            n = ch.get("chapter_number", 0)
            key = f"L{n:02d}"
            chapters[key] = ch
    else:
        chapters = chapters_raw

    if not chapters:
        print("ERROR: chapters 为空，请先完成 Phase 1 大纲生成")
        sys.exit(1)

    # 排序
    ch_keys = sorted(chapters.keys(), key=lambda k: int(k.replace("L", "")))

    if len(ch_keys) < 2:
        print("SKIP: 仅 1 章，无需因果链检查")
        return

    print(f"{'='*60}")
    print(f"  因果链验证 — 大纲（章）级别")
    print(f"{'='*60}")
    print(f"")
    print(f"{'链节':>8} | {'因果关联':<50} | {'状态':>6}")
    print(f"{'-'*70}")

    total = 0
    warn_count = 0
    error_count = 0
    chains = []

    for i in range(len(ch_keys) - 1):
        k_prev = ch_keys[i]
        k_next = ch_keys[i + 1]
        ch_prev = chapters[k_prev]
        ch_next = chapters[k_next]

        title_prev = ch_prev.get("title", "?")
        title_next = ch_next.get("title", "?")
        summary_prev = ch_prev.get("summary", "")
        summary_next = ch_next.get("summary", "")

        total += 1

        # 判断因果链状态
        if not summary_prev or not summary_next:
            level = "ERROR"
            reason = f"{k_prev} 或 {k_next} 概述为空，无法建立因果链"
        elif summary_prev == summary_next:
            level = "WARN"
            reason = f"{k_prev} 和 {k_next} 概述相同，因果无递进"
        else:
            # 简单关键词重叠检测（仅供提示，非最终判断）
            words_prev = set(summary_prev.replace("，", ",").replace("。", "").split())
            words_next = set(summary_next.replace("，", ",").replace("。", "").split())
            common = words_prev & words_next
            if len(common) < 1 and len(words_prev) >= 2 and len(words_next) >= 2:
                level = "WARN"
                reason = f"关键词无交集，可能因果断裂（重叠词: {', '.join(common) if common else '无'})"
            else:
                level = "PASS"
                reason = f"关键词重叠 {len(common)} 个，因果链正常"

        chains.append({
            "from": k_prev,
            "to": k_next,
            "from_title": title_prev,
            "to_title": title_next,
            "summary_prev": summary_prev[:60],
            "summary_next": summary_next[:60],
            "level": level,
            "reason": reason
        })

        if level == "ERROR":
            error_count += 1
        elif level == "WARN":
            warn_count += 1

    for ch in chains:
        print(f"  {ch['from']} → {ch['to']:>5} | {ch['reason']:<50} | {_tag(ch['level'])} {ch['level']:>6}")

    print(f"{'-'*70}")
    print(f"")
    print(f"## 因果链明细")
    print(f"")
    for ch in chains:
        print(f"### {ch['from']}「{ch['from_title']}」→ {ch['to']}「{ch['to_title']}」")
        print(f"")
        print(f"**前章概述**: {ch['summary_prev']}")
        print(f"**后章概述**: {ch['summary_next']}")
        print(f"**状态**: {_tag(ch['level'])} {ch['level']}")
        print(f"**说明**: {ch['reason']}")
        if ch['level'] != 'PASS':
            print(f"**操作**: 请补充或修正概述，确保 {ch['from']} 的果能导向 {ch['to']} 的因")
        print(f"")

    print(f"---")
    print(f"## 统计")
    print(f"- ✅ PASS: {total - warn_count - error_count}")
    print(f"- ⚠️ WARN: {warn_count}")
    print(f"- ❌ ERROR: {error_count}")
    print(f"")
    if error_count > 0 or warn_count > 0:
        print(f"❌ 检测到 {error_count + warn_count} 个链节问题，请修复后重新运行")
        sys.exit(1)
    else:
        print(f"✅ 大纲因果链完整，可进入下一阶段")


def cmd_substructure(state_path: str, ch_key: str):
    """检查指定章内子结构级别的因果链完整性"""
    state = _load_state(state_path)

    chapter = state.get("chapters", {}).get(ch_key, {})
    subs = chapter.get("sub_structures", {})

    if not isinstance(subs, dict) or not subs:
        print(f"ERROR: {ch_key} 子结构未规划，请先运行 plan-chapter")
        sys.exit(1)

    ch_title = chapter.get("title", "?")
    s_keys = sorted(subs.keys(), key=lambda k: int(k.replace("S", "")))

    if len(s_keys) < 2:
        print(f"SKIP: {ch_key} 仅 1 个子结构，无需因果链检查")
        return

    print(f"{'='*60}")
    print(f"  因果链验证 — 子结构级别 — {ch_key}「{ch_title}」")
    print(f"{'='*60}")
    print(f"")
    print(f"{'链节':>10} | {'因果关联':<50} | {'状态':>6}")
    print(f"{'-'*72}")

    total = 0
    warn_count = 0
    error_count = 0
    chains = []

    for i in range(len(s_keys) - 1):
        k_prev = s_keys[i]
        k_next = s_keys[i + 1]
        sub_prev = subs[k_prev]
        sub_next = subs[k_next]

        title_prev = sub_prev.get("title", "?")
        title_next = sub_next.get("title", "?")
        summary_prev = sub_prev.get("summary", "")
        summary_next = sub_next.get("summary", "")
        tone_prev = sub_prev.get("tone", "")
        tone_next = sub_next.get("tone", "")

        total += 1

        # 判断因果链状态
        if not summary_prev or not summary_next:
            level = "ERROR"
            reason = f"{ch_key}{k_prev} 或 {ch_key}{k_next} 概述为空"
        elif summary_prev == summary_next:
            level = "WARN"
            reason = "概述相同，因果无递进"
        else:
            words_prev = set(summary_prev.replace("，", ",").replace("。", "").split())
            words_next = set(summary_next.replace("，", ",").replace("。", "").split())
            common = words_prev & words_next
            if len(common) < 1 and len(words_prev) >= 2 and len(words_next) >= 2:
                level = "WARN"
                reason = f"关键词无交集，可能因果断裂"
            else:
                level = "PASS"
                reason = f"关键词重叠 {len(common)} 个，因果链正常"

        # 检查情绪递进是否合理
        tone_note = ""
        if tone_prev and tone_next and tone_prev != tone_next:
            tone_note = f"（情绪: {tone_prev} → {tone_next}）"

        chains.append({
            "from": k_prev,
            "to": k_next,
            "from_title": title_prev,
            "to_title": title_next,
            "summary_prev": summary_prev[:50],
            "summary_next": summary_next[:50],
            "tone_prev": tone_prev,
            "tone_next": tone_next,
            "level": level,
            "reason": reason + " " + tone_note
        })

        if level == "ERROR":
            error_count += 1
        elif level == "WARN":
            warn_count += 1

    for ch in chains:
        tag = _tag(ch['level'])
        print(f"  {ch['from']} → {ch['to']:>5} | {ch['reason']:<50} | {tag} {ch['level']:>6}")

    print(f"{'-'*72}")
    print(f"")
    print(f"## 因果链明细")
    print(f"")
    for ch in chains:
        prev_title_full = f"{ch['from']}「{ch['from_title']}」"
        next_title_full = f"{ch['to']}「{ch['to_title']}」"
        print(f"### {prev_title_full} → {next_title_full}")
        print(f"")
        print(f"**前段概述**: {ch['summary_prev']}  (情绪: {ch['tone_prev'] or '未设'})")
        print(f"**后段概述**: {ch['summary_next']}  (情绪: {ch['tone_next'] or '未设'})")
        print(f"**状态**: {_tag(ch['level'])} {ch['level']}")
        print(f"**说明**: {ch['reason']}")
        if ch['level'] != 'PASS':
            print(f"**操作**: 调整 {ch['to']} 的概述，使其与 {ch['from']} 形成因果递进")
        print(f"")

    print(f"---")
    print(f"## 统计")
    print(f"- ✅ PASS: {total - warn_count - error_count}")
    print(f"- ⚠️ WARN: {warn_count}")
    print(f"- ❌ ERROR: {error_count}")
    print(f"")
    if error_count > 0 or warn_count > 0:
        print(f"❌ 检测到 {error_count + warn_count} 个链节问题，请修复子结构概述后重新运行")
        sys.exit(1)
    else:
        print(f"✅ {ch_key} 子结构因果链完整，可开始写作")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    state_path = sys.argv[2]

    if mode == "chapter-outline":
        cmd_chapter_outline(state_path)

    elif mode == "sub-structure":
        if len(sys.argv) < 4:
            print("用法: sub-structure <state_path> <ch_key>")
            sys.exit(1)
        cmd_substructure(state_path, sys.argv[3])

    else:
        print(f"未知模式: {mode}")
        print(__doc__)
        sys.exit(1)
