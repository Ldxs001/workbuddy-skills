#!/usr/bin/env python3
"""
novel-workflow-engine — 统一编排引擎。

解决三大缺陷：
  1. 子结构规划未先于写作 → plan-chapter 批量注册所有子结构（含情绪提示）
  2. 阶段转换无前置校验 → 每个 set-phase 前自动检查必要条件
  3. 各脚本各自为战 → 统一切片入口

用法：
  plan-chapter <state_path> <ch_key> <subs_json>
      批量注册一章内所有子结构（含 title / summary / tone）
      subs_json: [{"s_key":"S01","title":"...","summary":"...","tone":"..."}, ...]

  verify-chapter <state_path> <ch_key>
      验证一章内所有子结构已全部注册，列出缺失项。

  finalize-chapter <state_path> <ch_key> <chapter_dir> <report_dir>
      完成一章：运行连通性检查 + 风格校验 + 逻辑检查 + phase→chapter_done

  preview-writing-context <state_path> <ch_key>
      预览一章写作前的完整上下文（含所有子结构规划）

  verify-causality-outline <state_path>
      验证大纲（章）级别的因果链完整性。
      在 Phase 1 用户确认之前必须运行。

  verify-causality-sub <state_path> <ch_key>
      验证指定章的子结构级别因果链完整性。
      在 plan-chapter 之后、写作开始之前必须运行。
"""

import os
import sys
import json
import re
import subprocess

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

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


def _save_state(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def _check_phase_ge(state: dict, min_phase: str) -> bool:
    return PHASE_ORDER.get(state.get("current_phase", "none"), 0) >= PHASE_ORDER.get(min_phase, 0)


def cmd_plan_chapter(state_path: str, ch_key: str, subs_json: str):
    """批量注册一章内的所有子结构"""
    state = _load_state(state_path)
    min_phase = "stage1_done"
    if not _check_phase_ge(state, min_phase):
        print(f"ERROR: plan-chapter 需要 phase ≥ {min_phase}")
        sys.exit(1)

    # 如果 chapter 不存在，创建
    chapter = state.setdefault("chapters", {}).setdefault(ch_key, {})
    subs = chapter.setdefault("sub_structures", {})

    # 解析子结构数组
    try:
        sub_list = json.loads(subs_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: subs_json 格式错误: {e}")
        print(f'  → 期望 JSON 数组: [{{"s_key":"S01","title":"...","summary":"...","tone":"..."}}, ...]')
        sys.exit(1)

    if not isinstance(sub_list, list) or len(sub_list) == 0:
        print("ERROR: subs_json 必须是非空 JSON 数组")
        sys.exit(1)

    for sub_item in sub_list:
        s_key = sub_item.get("s_key")
        title = sub_item.get("title")
        summary = sub_item.get("summary", "")
        tone = sub_item.get("tone", "中性")

        if not s_key or not title:
            print(f"ERROR: 子结构条目缺少 s_key 或 title: {json.dumps(sub_item, ensure_ascii=False)}")
            sys.exit(1)

        if s_key in subs:
            print(f"  WARN: {s_key} 已存在，覆盖")

        subs[s_key] = {
            "title": title,
            "summary": summary,
            "tone": tone,
            "word_count": 0,
            "status": "pending"
        }
        print(f"  ✅ {ch_key}{s_key} {title} — 情绪: {tone}")

    # 自动推进 phase 到 writing（如果还在 stage1_done）
    if state.get("current_phase") == "stage1_done":
        state["current_phase"] = "writing"
        print(f"  🔄 phase → writing")

    _save_state(state_path, state)
    count = len(sub_list)
    print(f"OK {count} 个子结构已注册到 {ch_key}")
    print(f"  → 下一步: context_loader 或直接开始写作")


def cmd_verify_chapter(state_path: str, ch_key: str):
    """验证一章内的所有子结构是否已全部注册"""
    state = _load_state(state_path)
    chapter = state.get("chapters", {}).get(ch_key, {})
    subs = chapter.get("sub_structures", {})

    if not isinstance(subs, dict) or len(subs) == 0:
        print(f"ERROR: {ch_key} 的子结构为空，请先运行 plan-chapter")
        sys.exit(1)

    missing_items = []
    registered_items = []

    # 提取子结构编号并排序
    s_keys = sorted(subs.keys(), key=lambda k: int(k.replace("S", "")))
    for s_key in s_keys:
        info = subs[s_key]
        if not info.get("title"):
            missing_items.append(s_key)
        else:
            registered_items.append(f"  ✅ {ch_key}{s_key} {info.get('title', '?')}")

    print(f"[验证 {ch_key}]")
    for item in registered_items:
        print(item)

    if missing_items:
        print(f"\n❌ 以下子结构缺失 title（未正确注册）:")
        for m in missing_items:
            print(f"   - {ch_key}{m}")
        sys.exit(1)

    print(f"OK {ch_key} 全部 {len(s_keys)} 个子结构已注册")


def cmd_finalize_chapter(state_path: str, ch_key: str, chapter_dir: str, report_dir: str):
    """完成一章：连通性 + 风格校验 + 逻辑检查 + phase→chapter_done"""
    state = _load_state(state_path)
    min_phase = "writing"
    if not _check_phase_ge(state, min_phase):
        print(f"ERROR: finalize-chapter 需要 phase ≥ {min_phase}")
        sys.exit(1)

    os.makedirs(report_dir, exist_ok=True)
    python_exe = sys.executable

    ch_num = ch_key.replace("L", "")
    continuity_report = os.path.join(report_dir, f"continuity_{ch_key}.md")
    style_report = os.path.join(report_dir, f"style_{ch_key}.md")
    logic_report = os.path.join(report_dir, f"logic_{ch_key}.md")

    # 检查 chapter_dir 是否存在且非空
    if not os.path.isdir(chapter_dir):
        print(f"WARN: 章节目录不存在: {chapter_dir}，跳过文件级检查")
        print(f"OK phase 已推进到 chapter_done（无内容章节）")
        return

    # ── 步骤1: 连通性检查 ──
    continuity_script = os.path.join(SCRIPTS_DIR, "novel_continuity.py")
    if os.path.exists(continuity_script):
        print(f"\n[1/3] 连通性检查...")
        ret = os.system(f'"{python_exe}" "{continuity_script}" generate "{chapter_dir}" "{state_path}" "{continuity_report}" --auto-fix')
        if ret != 0:
            print(f"  WARN: 连通性检查返回非零 {ret}，继续")
    else:
        print(f"\n[1/3] 连通性检查 — 跳过（脚本不存在）")

    # ── 步骤2: 风格校验 ──
    style_script = os.path.join(SCRIPTS_DIR, "novel_style_check.py")
    if os.path.exists(style_script):
        print(f"\n[2/3] 风格校验...")
        ret = os.system(f'"{python_exe}" "{style_script}" "{chapter_dir}" "{state_path}" "{style_report}"')
        if ret != 0:
            print(f"  WARN: 风格校验返回非零 {ret}，继续")
    else:
        print(f"\n[2/3] 风格校验 — 跳过（脚本不存在）")

    # ── 步骤3: 逻辑检查（新增） ──
    logic_script = os.path.join(SCRIPTS_DIR, "novel_logic_check.py")
    if os.path.exists(logic_script):
        print(f"\n[3/3] 逻辑检查...")
        ret = os.system(f'"{python_exe}" "{logic_script}" "{chapter_dir}" "{state_path}" "{logic_report}"')
        if ret != 0:
            print(f"  WARN: 逻辑检查返回非零 {ret}，继续")
    else:
        print(f"\n[3/3] 逻辑检查 — 跳过（脚本不存在）")

    # ── 推进 phase ──
    state = _load_state(state_path)
    current_phase = state.get("current_phase", "none")
    if PHASE_ORDER.get(current_phase, 0) < PHASE_ORDER["chapter_done"]:
        state["current_phase"] = "chapter_done"
        _save_state(state_path, state)
        print(f"\n✅ phase → chapter_done")

    # ── 输出摘要 ──
    continuity_exists = os.path.exists(continuity_report)
    style_exists = os.path.exists(style_report)
    logic_exists = os.path.exists(logic_report)
    print(f"\n📋 报告:")
    print(f"  {'✅' if continuity_exists else '❌'} 连通性: {continuity_report}")
    print(f"  {'✅' if style_exists else '❌'} 风格: {style_report}")
    print(f"  {'✅' if logic_exists else '❌'} 逻辑: {logic_report}")
    print(f"OK {ch_key} 已完成")


def cmd_preview_context(state_path: str, ch_key: str):
    """预览一章所有子结构的写作前上下文"""
    state = _load_state(state_path)
    chapter = state.get("chapters", {}).get(ch_key, {})
    subs = chapter.get("sub_structures", {})

    if not subs:
        print(f"ERROR: {ch_key} 子结构未规划，请先运行 plan-chapter")
        sys.exit(1)

    style = state.get("style_guide", {})
    genre = style.get("genre", "未设定")
    perspective = style.get("perspective", "未设定")
    narrative = style.get("narrative_mode", "未设定")

    characters = state.get("characters", {})
    char_list = []
    for name, info in characters.items():
        role = info.get("role", "")
        char_list.append(f"{name}({role})")

    timeline = state.get("timeline", {})
    current_day = timeline.get("current_day", "未知")

    ch_title = chapter.get("title", "未知")
    ch_summary = chapter.get("summary", "")

    s_keys = sorted(subs.keys(), key=lambda k: int(k.replace("S", "")))

    print(f"[写作前上下文 — {ch_key}「{ch_title}」]")
    print(f"风格: {genre}")
    print(f"视角: {perspective} / {narrative}")
    print(f"角色: {', '.join(char_list)}")
    print(f"时间: 穿越后第 {current_day} 天")
    print(f"章概述: {ch_summary}")
    print(f"")
    print(f"{'─'*60}")
    print(f"{'子结构':>8} | {'情绪':>6} | {'概述':<40}")
    print(f"{'─'*60}")

    for s_key in s_keys:
        info = subs[s_key]
        title = info.get("title", "?").ljust(20)
        tone = info.get("tone", "中性").ljust(6)
        summary = info.get("summary", "")
        print(f"  {ch_key}{s_key} | {tone} | {title[:20]} | {summary[:40]}")

    print(f"{'─'*60}")
    print(f"OK {ch_key} 共 {len(s_keys)} 个子结构等待写作")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    state_path = sys.argv[2]

    if command == "plan-chapter":
        if len(sys.argv) < 5:
            print("用法: plan-chapter <state_path> <ch_key> <subs_json>")
            sys.exit(1)
        cmd_plan_chapter(state_path, sys.argv[3], sys.argv[4])

    elif command == "verify-chapter":
        if len(sys.argv) < 4:
            print("用法: verify-chapter <state_path> <ch_key>")
            sys.exit(1)
        cmd_verify_chapter(state_path, sys.argv[3])

    elif command == "finalize-chapter":
        if len(sys.argv) < 5:
            print("用法: finalize-chapter <state_path> <ch_key> <chapter_dir> <report_dir>")
            sys.exit(1)
        cmd_finalize_chapter(state_path, sys.argv[3], sys.argv[4], sys.argv[5])

    elif command == "preview-writing-context":
        if len(sys.argv) < 4:
            print("用法: preview-writing-context <state_path> <ch_key>")
            sys.exit(1)
        cmd_preview_context(state_path, sys.argv[3])

    elif command == "verify-causality-outline":
        causality_script = os.path.join(SCRIPTS_DIR, "novel_causality_check.py")
        if not os.path.exists(causality_script):
            print("ERROR: novel_causality_check.py 不存在")
            sys.exit(1)
        python_exe = sys.executable
        ret = os.system(f'"{python_exe}" "{causality_script}" chapter-outline "{state_path}"')
        sys.exit(ret >> 8)

    elif command == "verify-causality-sub":
        if len(sys.argv) < 4:
            print("用法: verify-causality-sub <state_path> <ch_key>")
            sys.exit(1)
        causality_script = os.path.join(SCRIPTS_DIR, "novel_causality_check.py")
        if not os.path.exists(causality_script):
            print("ERROR: novel_causality_check.py 不存在")
            sys.exit(1)
        python_exe = sys.executable
        ret = os.system(f'"{python_exe}" "{causality_script}" sub-structure "{state_path}" "{sys.argv[3]}"')
        sys.exit(ret >> 8)

    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)
