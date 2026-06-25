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

LENGTH_RANGES = {"short": (3, 6), "medium": (8, 10), "long": (11, 99)}
LENGTH_LABELS = {"short": "短篇(3-6章)", "medium": "中篇(8-10章)", "long": "长篇(11章+)"}

def init_project(name, project_name, length="medium", num_chapters=None):
    """
    初始化 novel_state.json 骨架。
    name: 项目名（自动创建在 projects/<name>/data/）或完整路径
    length: short/medium/long（默认 medium）
    num_chapters: 不传则按 length 范围取中值
    """
    p = Path(name)
    # 如果名字不含路径分隔符，视为项目名，自动创建标准化子目录
    if "/" not in name and "\\" not in name:
        SCRIPTS_DIR = Path(__file__).parent
        base = SCRIPTS_DIR.parent.parent / ".standardization" / "novel-weaver" / "projects"
        p = base / name / "data" / "novel_state.json"
        print(f"[初始化] 项目目录: {p.parent}")
    if p.exists():
        print(f"[HOOK-BLOCK] {p} 已存在，禁止重复初始化")
        sys.exit(1)
    if length not in LENGTH_RANGES:
        print(f"[HOOK-BLOCK] 无效篇幅: {length}，可选: short/medium/long")
        sys.exit(1)
    if num_chapters is None:
        lo, hi = LENGTH_RANGES[length]
        num_chapters = (lo + hi) // 2
    else:
        num_chapters = int(num_chapters)
        lo, hi = LENGTH_RANGES[length]
        if num_chapters < lo or num_chapters > hi:
            print(f"[HOOK-BLOCK] {LENGTH_LABELS[length]} 章数应在 {lo}-{hi} 之间，收到 {num_chapters}")
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
            "version": "1.12.6",
            "length": length
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
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[初始化] {project_name} → {p}")
    print(f"[初始化] 篇幅: {LENGTH_LABELS.get(length, length)}（{num_chapters} 章）")
    print(f"[初始化] 当前阶段: stage1_init")
    print(f"[下一步] 设置场景配置和大纲后:")
    print(f"  python novel_causality_check.py outline <state_path>")
    print(f"  python novel_pipeline_gate.py set-phase <state_path> stage1_done")

if __name__ == "__main__":
    # list-projects 不需要 state_path，优先处理
    if len(sys.argv) >= 2 and sys.argv[1] == "list-projects":
        cmd = "list-projects"
    elif len(sys.argv) < 3:
        print("用法: python novel_state_manager.py <命令> <state_path> [args...]")
        print("  命令:")
        print("    init       <项目名> [length] [num_chapters]  初始化新小说")
        print("                   length: short(3-6章), medium(8-10章,默认), long(11章+)")
        print("                   也可传入完整路径: init ./my/path/data/novel_state.json 小说名")
        print("    add-char   <name> <role> <first_appearance> [traits] [mbti] [archetype]")
        print("    add-char   <name> <role> <first_appearance> [traits] [mbti] [archetype]")
        print("    update-sub <chapter> <sub_key> <word_count>")
        print("    finalize   <chapter>")
        print("    add-timeline <time_point> <event>")
        print("    set-signature <true|false> [text]")
        print("    set-length    <short|medium|long>")
        print("    list-projects                     列出所有已创建的项目")
        print("    list-projects                     列出所有已创建的项目")
        print("")
        print("  示例:")
        print("    python novel_state_manager.py init my-novel 我的小说   # 自动创建")
        print("    python novel_state_manager.py init ./path/state.json 小说名  # 指定路径")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list-projects":
        SCRIPTS_DIR = Path(__file__).parent
        scan_base = SCRIPTS_DIR.parent.parent / ".standardization" / "novel-weaver" / "projects"
        found = []
        if scan_base.exists():
            for proj_dir in scan_base.iterdir():
                state_file = proj_dir / "data" / "novel_state.json"
                try:
                    d = json.loads(state_file.read_text(encoding="utf-8-sig"))
                    name = d.get("project", "?")
                    length = d.get("meta", {}).get("length", "?")
                    phase = d.get("meta", {}).get("current_phase", "?")
                    ch_count = len(d.get("chapters", []))
                    done = sum(1 for c in d.get("chapters", []) if c.get("status") == "completed")
                    found.append((str(state_file), name, length, phase, ch_count, done))
                except Exception:
                    continue
        if not found:
            print("没有找到已创建的项目。")
        else:
            print(f"\n{'='*55}")
            print(f"  已创建的项目 ({len(found)}):")
            print(f"{'='*55}")
            for path, name, length, phase, total, done in found:
                print(f"  📖 {name}")
                print(f"    路径: {path}")
                print(f"    篇幅: {length} | 阶段: {phase}")
                print(f"    章节: {done}/{total}")
                print()
        sys.exit(0)
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
    elif cmd == "set-length":
        length = sys.argv[3]
        data = load_state(sp)
        if length not in LENGTH_RANGES:
            print(f"[HOOK-BLOCK] 无效篇幅: {length}，可选: short/medium/long")
            sys.exit(1)
        data.setdefault("meta", {})["length"] = length
        save_state(sp, data)
        print(f"[篇幅] 已设为 {LENGTH_LABELS[length]}")
    elif cmd == "init":
        # sys.argv[2] = 项目名（可含路径）; sys.argv[3] = 显示名; [4]=length; [5]=num
        display_name = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2]
        length = sys.argv[4] if len(sys.argv) > 4 else "medium"
        num = sys.argv[5] if len(sys.argv) > 5 else None
        init_project(sys.argv[2], display_name, length, num)
    else:
        print(f"[错误] 未知命令: {cmd}")
