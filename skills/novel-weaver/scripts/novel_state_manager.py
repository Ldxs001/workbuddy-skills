#!/usr/bin/env python3
"""
novel-state-manager — novel_state.json 统一管理器 + 阶段门禁系统。

管理 novel_state.json 的初始化、章节/子结构追加、进度更新、阶段门禁。

阶段定义（不可逆递增）：
  00 none        → 未初始化
  10 init        → init 完成
  20 stage1_done → 大纲确认完成
  30 writing     → 子结构写作中
  40 chapter_done→ 某章全部完成（连+风格通过）
  50 stage3_ready→ 所有章节完成
  60 complete    → 全文整合完成
"""

import os
import sys
import json

PHASE_ORDER = {
    "none": 0, "init": 10, "stage1_done": 20,
    "writing": 30, "chapter_done": 40,
    "stage3_ready": 50, "complete": 60
}

# 命令 → 最低所需阶段
PHASE_REQUIREMENTS = {
    "init":           ("none",     "项目已初始化，禁止重复 init"),
    "add-sub":        ("stage1_done", "大纲未确认，不能创建子结构"),
    "update-sub":     ("stage1_done", "大纲未确认，不能写入子结构"),
    "add-char":       ("stage1_done", "大纲未确认，不能添加角色"),
    "set-timeline":   ("stage1_done", "大纲未确认，不能记录时间线"),
    "update-chapter": ("stage1_done", "大纲未确认，不能更新章节"),
    "set-phase":      ("init",   "初始化后才能设置阶段"),
    "get":            ("init",   "初始化后才能读取"),
}


def _load(path: str) -> dict:
    if not os.path.exists(path):
        print(f"ERROR: novel_state.json not found at {path}")
        print(f"  → 必须先运行：novel_state_manager.py init ...")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def _current_phase_int(data: dict) -> int:
    return PHASE_ORDER.get(data.get("current_phase", "none"), 0)


def _require_phase(path: str, command: str) -> dict:
    """加载文件并检查阶段门禁，返回 data。失败则 sys.exit(1)。"""
    req = PHASE_REQUIREMENTS.get(command)
    if not req:
        # 无阶段要求的命令直接放行
        return _load(path)

    min_phase_str, block_msg = req
    min_phase_int = PHASE_ORDER.get(min_phase_str, 0)

    data = _load(path)
    current_int = _current_phase_int(data)

    if current_int < min_phase_int:
        print(f"ERROR: 命令 '{command}' 被阶段门禁阻挡")
        print(f"  → 需要阶段 ≥ {min_phase_str}({min_phase_int})，当前为 {data.get('current_phase', 'none')}({current_int})")
        print(f"  → 原因：{block_msg}")
        print(f"  请按阶段顺序推进：none → init → stage1_done → writing → chapter_done → stage3_ready → complete")
        sys.exit(1)

    return data


def _set_phase_and_save(data: dict, path: str, new_phase: str):
    new_int = PHASE_ORDER.get(new_phase, 0)
    current_int = _current_phase_int(data)
    if new_int < current_int:
        print(f"ERROR: 阶段不可回退。当前 {data.get('current_phase', 'none')}({current_int})，试图设 {new_phase}({new_int})")
        sys.exit(1)
    data["current_phase"] = new_phase
    _save(path, data)
    print(f"OK phase → {new_phase}")


# ===== 命令函数 =====

def cmd_init(path: str, project_name: str, style_json: str, chapters_json: str):
    # 如果文件已存在且阶段 ≥ init，阻断
    if os.path.exists(path):
        existing = _load(path)
        if _current_phase_int(existing) >= PHASE_ORDER["init"]:
            print(f"ERROR: 项目已初始化 (phase={existing.get('current_phase', 'none')})，禁止重复 init")
            sys.exit(1)

    style = json.loads(style_json) if isinstance(style_json, str) else style_json
    chapters = json.loads(chapters_json) if isinstance(chapters_json, str) else chapters_json

    data = {
        "project": project_name,
        "current_phase": "init",
        "style_guide": style,
        "characters": [],
        "timeline": {"start_date": "未知", "current_day": 1, "entries": []},
        "chapters": chapters
    }
    _save(path, data)
    print(f"OK novel_state.json initialized at {path} (phase=init)")


def cmd_set_phase(path: str, new_phase: str):
    if new_phase not in PHASE_ORDER:
        print(f"ERROR: 无效阶段 '{new_phase}'。可选：{', '.join(PHASE_ORDER.keys())}")
        sys.exit(1)
    data = _require_phase(path, "set-phase")

    # ── phase→chapter_done 前置检查 ──
    if new_phase == "chapter_done":
        data_dir = os.path.dirname(path)
        ch_key = data.get("current_chapter", "")
        continuity_path = os.path.join(data_dir, f"continuity_{ch_key}.md" if ch_key else "continuity_report.md")
        style_path = os.path.join(data_dir, f"style_{ch_key}.md" if ch_key else "style_report.md")
        logic_path = os.path.join(data_dir, f"logic_{ch_key}.md" if ch_key else "logic_report.md")
        missing = []
        if not os.path.exists(continuity_path):
            missing.append(continuity_path)
        if not os.path.exists(style_path):
            missing.append(style_path)
        if missing:
            print(f"WARN: 以下报告不存在，建议先运行 finalize-chapter 生成:")
            for m in missing:
                print(f"  - {m}")
            print(f"  → 继续执行 set-phase（如需强制检查请运行 novel_workflow_engine.py finalize-chapter）")

    _set_phase_and_save(data, path, new_phase)


def cmd_add_sub(path: str, ch_key: str, s_key: str, title: str, summary: str, tone: str = "中性"):
    data = _require_phase(path, "add-sub")
    chapter = data.setdefault("chapters", {}).setdefault(ch_key, {})
    subs = chapter.setdefault("sub_structures", {})
    if s_key in subs:
        print(f"WARN: {s_key} already exists, overwriting")
    subs[s_key] = {
        "title": title,
        "summary": summary,
        "tone": tone,
        "word_count": 0,
        "status": "pending"
    }
    _save(path, data)
    print(f"OK {s_key} added: {title} (tone: {tone})")


def cmd_update_sub(path: str, sub_id: str, *kv_pairs):
    data = _require_phase(path, "update-sub")
    parts = sub_id.split("S")
    if len(parts) != 2:
        print(f"ERROR: invalid {sub_id}")
        sys.exit(1)
    ch_key = parts[0]

    sub = data.get("chapters", {}).get(ch_key, {}).get("sub_structures", {}).get(sub_id, {})
    if not sub:
        print(f"ERROR: {sub_id} not found")
        sys.exit(1)

    for kv in kv_pairs:
        if "=" not in kv:
            continue
        key, val = kv.split("=", 1)
        try:
            val = int(val)
        except ValueError:
            try:
                val = float(val)
            except ValueError:
                pass
        sub[key] = val

    _save(path, data)
    print(f"OK {sub_id} updated")


def cmd_add_char(path: str, name: str, role: str, first_appearance: str):
    data = _require_phase(path, "add-char")
    chars = data.setdefault("characters", [])
    for c in chars:
        if isinstance(c, dict) and c.get("name") == name:
            print(f"WARN: character '{name}' already exists")
            return
    chars.append({
        "name": name,
        "role": role,
        "first_appearance": first_appearance,
        "attributes": {}
    })
    _save(path, data)
    print(f"OK character '{name}' added")


def cmd_set_timeline(path: str, day: str, summary: str):
    data = _require_phase(path, "set-timeline")
    tl = data.setdefault("timeline", {})
    tl["current_day"] = int(day)
    entries = tl.setdefault("entries", [])
    entries.append({"day": int(day), "summary": summary})
    _save(path, data)
    print(f"OK timeline → day {day}")


def cmd_update_chapter(path: str, ch_key: str, *kv_pairs):
    data = _require_phase(path, "update-chapter")
    chapter = data.get("chapters", {}).get(ch_key, {})
    if not chapter:
        print(f"ERROR: {ch_key} not found")
        sys.exit(1)
    for kv in kv_pairs:
        if "=" not in kv:
            continue
        key, val = kv.split("=", 1)
        try:
            val = int(val)
        except ValueError:
            try:
                val = float(val)
            except ValueError:
                pass
        chapter[key] = val
    _save(path, data)
    print(f"OK {ch_key} updated")


def cmd_get(path: str):
    data = _require_phase(path, "get")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_get_phase(path: str):
    data = _require_phase(path, "get")
    print(data.get("current_phase", "none"))


# ===== CLI 调度 =====

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    path = sys.argv[2]

    if command == "init":
        if len(sys.argv) < 6:
            print("用法: init <path> <project_name> <style_json> <chapters_json>")
            sys.exit(1)
        cmd_init(path, sys.argv[3], sys.argv[4], sys.argv[5])

    elif command == "set-phase":
        if len(sys.argv) < 4:
            print("用法: set-phase <path> <phase_name>")
            sys.exit(1)
        cmd_set_phase(path, sys.argv[3])

    elif command == "get-phase":
        cmd_get_phase(path)

    elif command == "add-sub":
        if len(sys.argv) < 7:
            print("用法: add-sub <path> <L##> <S##> <title> <summary> [tone]")
            sys.exit(1)
        summary = sys.argv[6]
        tone = sys.argv[7] if len(sys.argv) >= 8 else "中性"
        cmd_add_sub(path, sys.argv[3], sys.argv[4], sys.argv[5], summary, tone)

    elif command == "update-sub":
        if len(sys.argv) < 4:
            print("用法: update-sub <path> <L##S##> <key=value> ...")
            sys.exit(1)
        cmd_update_sub(path, sys.argv[3], *sys.argv[4:])

    elif command == "add-char":
        if len(sys.argv) < 6:
            print("用法: add-char <path> <name> <role> <first_appearance>")
            sys.exit(1)
        cmd_add_char(path, sys.argv[3], sys.argv[4], sys.argv[5])

    elif command == "set-timeline":
        if len(sys.argv) < 5:
            print("用法: set-timeline <path> <day> <summary>")
            sys.exit(1)
        cmd_set_timeline(path, sys.argv[3], sys.argv[4])

    elif command == "update-chapter":
        if len(sys.argv) < 4:
            print("用法: update-chapter <path> <L##> <key=value> ...")
            sys.exit(1)
        cmd_update_chapter(path, sys.argv[3], *sys.argv[4:])

    elif command == "get":
        cmd_get(path)

    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)
