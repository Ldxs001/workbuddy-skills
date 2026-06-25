#!/usr/bin/env python3
"""
State Manager — 状态文件管理
角色登记 / 子结构进度更新 / 章节完成 / 时间线记录

update-sub 命令特点（即时标记）：
  - 每次调用立即更新 novel_state.json 中的子结构状态
  - 不接受批量/延迟模式调用
  - 记录实际字数和完成时间
"""
import json, sys
from pathlib import Path
from datetime import datetime

def load_state(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def save_state(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def add_char(path, name, role_attr, first_appearance, traits="", mbti="", archetype=""):
    data = load_state(path)
    chars = data.get("characters", [])
    for c in chars:
        if c.get("name") == name:
            if role_attr: c["role"] = role_attr
            if first_appearance: c["first_appearance"] = first_appearance
            if traits: c["traits"] = [t.strip() for t in traits.split(",")]
            if mbti: c["mbti"] = mbti
            if archetype: c["archetype"] = archetype
            save_state(path, data)
            print(f"[角色更新] {name} (MBTI={mbti or '无'}, 原型={archetype or '无'})")
            return
    entry = {"name": name, "role": role_attr, "first_appearance": first_appearance}
    if traits:
        entry["traits"] = [t.strip() for t in traits.split(",")]
    if mbti:
        entry["mbti"] = mbti
    if archetype:
        entry["archetype"] = archetype
    chars.append(entry)
    data["characters"] = chars
    save_state(path, data)
    print(f"[角色新增] {name} (出场: {first_appearance}, MBTI={mbti or '无'}, 原型={archetype or '无'})")

def update_sub(path, chapter, sub_key, word_count):
    """
    即时标记子结构完成（非批量，非延迟）
    每次调用立即写入 novel_state.json
    """
    data = load_state(path)
    for ch in data.get("chapters", []):
        if ch["id"] != chapter:
            continue
        if "sub_structures" not in ch:
            ch["sub_structures"] = {}
        prev_wc = ch["sub_structures"].get(sub_key, {}).get("word_count", 0)
        prev = ch["sub_structures"].get(sub_key, {})
        prev["word_count"] = int(word_count)
        prev["status"] = "completed"
        ch["sub_structures"][sub_key] = prev
        # 更新章总字数（减去旧字数+新字数）
        ch["word_count"] = ch.get("word_count", 0) - prev_wc + int(word_count)
        break
    save_state(path, data)
    print(f"[SUB-COMPLETE] {chapter}{sub_key}: {word_count}字, status=completed")

def finalize_chapter(path, chapter):
    data = load_state(path)
    for ch in data.get("chapters", []):
        if ch["id"] == chapter:
            ch["status"] = "completed"
            break
    save_state(path, data)
    print(f"[章节] {chapter} [OK] 完成")

def add_timeline(path, time_point, event):
    data = load_state(path)
    tl = data.get("timeline", [])
    tl.append({"event": event, "time_point": time_point})
    data["timeline"] = tl
    save_state(path, data)
    print(f"[时间线] {time_point}: {event}")

def set_signature(path, enabled, text=""):
    """设置署名开关和文本。代码级强制，LLM 不可自行添加。"""
    data = load_state(path)
    enabled_bool = enabled.lower() in ("true", "1", "yes")
    data["signature"] = {"enabled": enabled_bool, "text": text}
    save_state(path, data)
    status = "开" if enabled_bool else "关"
    print(f"[署名] signature.enabled={enabled_bool} ({status})")
    if enabled_bool and text:
        print(f"[署名] signature.text=\"{text}\"")
    elif enabled_bool:
        print(f"[署名] signature.text 为空（默认不显示署名行）")
    if not enabled_bool:
        print(f"[署名] 已关闭，LLM 不得在正文中写入任何署名/代名内容（atomic_writer 代码级阻断）")

def init_project(path, project_name, num_chapters=10):
    """
    初始化 novel_state.json 骨架。
    涵盖所有标准字段，确保格式正确。
    """
    if Path(path).exists():
        print(f"[HOOK-BLOCK] {path} 已存在，禁止重复初始化")
        sys.exit(1)
    today = datetime.now().strftime("%Y-%m-%d")
    chapters = []
    for i in range(1, num_chapters + 1):
        chapters.append({
            "id": f"L{i:02d}",
            "title": f"第{i}章",
            "overview": "",
            "word_count": 0,
            "status": "pending",
            "sub_structures": {}
        })
    # 末章标记
    if chapters:
        chapters[-1]["is_final"] = True
    data = {
        "project": project_name,
        "created": today,
        "meta": {
            "current_phase": "stage1_init",
            "version": "1.12.5"
        },
        "writing_style": {
            "narrative_voice": "",
            "tense": "",
            "sentence_preference": "",
            "vocabulary_register": "",
            "description_depth": "",
            "custom_rules": ""
        },
        "characters": [],
        "chapters": chapters,
        "timeline": [],
        "signature": {"enabled": False, "text": ""}
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[初始化] {project_name} → {path}")
    print(f"[初始化] {num_chapters} 章骨架已创建")
    print(f"[初始化] 当前阶段: stage1_init")
    print(f"[下一步] 设置场景配置和大纲后:")
    print(f"  python novel_causality_check.py outline <state_path>")
    print(f"  python novel_pipeline_gate.py set-phase <state_path> stage1_done")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python novel_state_manager.py <命令> <state_path> [args...]")
        print("  命令:")
        print("    init       <project_name> [num_chapters]  初始化新人小说")
        print("    add-char   <name> <role> <first_appearance> [traits] [mbti] [archetype]")
        print("    update-sub <chapter> <sub_key> <word_count>")
        print("    finalize   <chapter>")
        print("    add-timeline <time_point> <event>")
        print("    set-signature <true|false> [text]")
        print("")
        print("  示例:")
        print("    python novel_state_manager.py init <path> 我的小说 12")
        sys.exit(1)
    cmd = sys.argv[1]
    sp = sys.argv[2]
    if cmd == "add-char":
        add_char(sp, sys.argv[3], sys.argv[4], sys.argv[5],
                 sys.argv[6] if len(sys.argv) > 6 else "",
                 sys.argv[7] if len(sys.argv) > 7 else "",
                 sys.argv[8] if len(sys.argv) > 8 else "")
    elif cmd == "update-sub":
        update_sub(sp, sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "finalize":
        finalize_chapter(sp, sys.argv[3])
    elif cmd == "add-timeline":
        add_timeline(sp, sys.argv[3], sys.argv[4])
    elif cmd == "set-signature":
        text = sys.argv[4] if len(sys.argv) > 4 else ""
        set_signature(sp, sys.argv[3], text)
    elif cmd == "init":
        num = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        init_project(sp, sys.argv[3], num)
    else:
        print(f"[错误] 未知命令: {cmd}")
