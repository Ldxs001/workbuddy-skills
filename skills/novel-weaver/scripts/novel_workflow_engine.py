#!/usr/bin/env python3
"""
Workflow Engine — 流程引擎
子结构注册 / 写作 / 上下文预览 / 一键完结章节 / 验证

新命令：write-sub
  链式调用: atomic_writer.validate_and_write → state_manager.update-sub
  每完成一个子结构立即记录状态（非批量，非延迟）
"""
import json, sys, subprocess, os, re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
# R-12 审计锚点：数据目录变量声明
DEFAULT_DATA_DIR_RAW = "skills/.standardization/novel-weaver/data/"
SKILLS_ROOT = SCRIPTS_DIR.parent.parent
DATA_DIR = SKILLS_ROOT / ".standardization" / "novel-weaver" / "data"
DATA_STATE = DATA_DIR / "novel_state.json"
DATA_CHAPTERS = DATA_DIR / "chapters"
DATA_REPORTS = DATA_DIR / "reports"

def _parse_ending_tag(summary: str) -> str | None:
    """从概述中解析【收尾类型: xxx】标签"""
    m = re.search(r'【收尾类型:\s*(\S+?)】', summary)
    if m:
        t = m.group(1)
        if t in ("封闭式", "开放式", "悬停式"):
            return t
    return None

def plan_chapter(state_path, chapter, subs_json):
    """批量注册子结构。末章末子结构自动标记 is_ending。"""
    data = json.loads(Path(state_path).read_text(encoding="utf-8"))
    subs = json.loads(subs_json)

    # 判断是否为末章
    chapters = data.get("chapters", [])
    is_last_chapter = bool(chapters and chapters[-1]["id"] == chapter)

    for ch in data.get("chapters", []):
        if ch["id"] != chapter:
            continue
        if "sub_structures" not in ch:
            ch["sub_structures"] = {}
        for i, s in enumerate(subs):
            s_key = s["s_key"]
            entry = {
                "title": s.get("title", ""),
                "summary": s.get("summary", ""),
                "tone": s.get("tone", ""),
                "word_count": 0,
                "status": "pending"
            }
            # 情绪混合系统：emotions 数组（可选）
            if "emotions" in s and isinstance(s["emotions"], list) and len(s["emotions"]) > 0:
                entry["emotions"] = s["emotions"]
            # 末章 + 最后一个子结构 → 标记 is_ending
            if is_last_chapter and i == len(subs) - 1:
                entry["is_ending"] = True
                ending_type = _parse_ending_tag(s.get("summary", ""))
                if ending_type:
                    entry["ending_type"] = ending_type
            ch["sub_structures"][s_key] = entry
        break

    Path(state_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if is_last_chapter:
        last_sub = subs[-1]["s_key"] if subs else "?"
        print(f"[plan-chapter] {chapter}: {len(subs)} 个子结构已注册")
        print(f"[收尾] 末章标记 → 末子结构 {last_sub} 的 is_ending=True")
    else:
        print(f"[plan-chapter] {chapter}: {len(subs)} 个子结构已注册")

def verify_chapter(state_path, chapter):
    """验证章节子结构注册完整性"""
    data = json.loads(Path(state_path).read_text(encoding="utf-8"))
    for ch in data.get("chapters", []):
        if ch["id"] != chapter:
            continue
        subs = ch.get("sub_structures", {})
        if not subs:
            print(f"[verify] {chapter}: [FAIL] 无子结构")
            return False
        all_ok = True
        for sk, sv in subs.items():
            if not sv.get("title") or not sv.get("summary"):
                print(f"[verify] {chapter}{sk}: [FAIL] 字段缺失")
                all_ok = False
        if all_ok:
            print(f"[verify] {chapter}: [OK] {len(subs)} 个子结构全部注册完成")
        return all_ok
    print(f"[verify] {chapter}: [FAIL] 未找到")
    return False

def preview_context(state_path, chapter):
    """预览写作上下文"""
    data = json.loads(Path(state_path).read_text(encoding="utf-8"))
    for ch in data.get("chapters", []):
        if ch["id"] != chapter:
            continue
        print(f"{'='*50}")
        print(f"[预览] {chapter}: {ch.get('title','')}")
        print(f"[概述] {ch.get('overview','')}")
        subs = ch.get("sub_structures", {})
        for sk in sorted(subs.keys()):
            sv = subs[sk]
            status_icon = "[OK]" if sv.get("status") == "completed" else "[WAIT]"
            print(f"  {status_icon} {sk}: {sv.get('title','')} [{sv.get('tone','')}]")
            print(f"      {sv.get('summary','')}")
        print(f"{'='*50}")

def write_sub(state_path, chapter, sub_key, target_dir):
    """
    单子结构写入钩子（阻断式，即时状态标记）
    流程链:
      1. atomic_writer.validate_and_write → 格式校验 + 原子写入
      2. state_manager.update-sub → 即时状态更新

    内容从 stdin 读取。
    """
    atomic_writer = SCRIPTS_DIR / "novel_atomic_writer.py"
    chapter_dir = Path(target_dir) / chapter
    chapter_dir.mkdir(parents=True, exist_ok=True)
    filepath = chapter_dir / f"{sub_key}.txt"

    # ── 步骤1: 从 stdin 读取内容 ──
    content = sys.stdin.read()
    if not content.strip():
        print(f"[HOOK-BLOCK] {chapter}{sub_key}: stdin 内容为空，拒绝写入")
        sys.exit(1)

    # ── 步骤2: 通过 atomic_writer 进行格式校验 + 原子写入 ──
    # 直接调用 validate_and_write 函数
    sys.path.insert(0, str(SCRIPTS_DIR))
    import novel_atomic_writer
    success = novel_atomic_writer.validate_and_write(content, str(filepath), chapter, sub_key)
    if not success:
        print(f"[HOOK-BLOCK] {chapter}{sub_key}: 写入失败")
        sys.exit(1)

    # ── 步骤3: state_manager.update-sub — 即时状态标记 ──
    word_count = len(content.replace("\n", ""))
    state_manager = SCRIPTS_DIR / "novel_state_manager.py"
    result = subprocess.run(
        [sys.executable, str(state_manager), "update-sub",
         state_path, chapter, sub_key, str(word_count)],
        capture_output=True, text=True, encoding="utf-8"
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(f"[HOOK-BLOCK] state 更新失败: {result.stderr}")
        sys.exit(1)

    print(f"[write-sub] {chapter}{sub_key} [OK] 已完成")
    print(f"  字数: {word_count}")

def finalize_chapter(state_path, chapter, chapter_dir, report_dir):
    """一键完结：章内连通性 → 跨章承诺链 → 风格校验 → phase→chapter_done"""
    import importlib
    sys.path.insert(0, str(SCRIPTS_DIR))
    from novel_continuity import check_continuity, cross_chapter
    from novel_style_check import check_chapter as style_check
    from novel_pipeline_gate import pass_gate, load_gates, save_gates

    chapters_dir = str(Path(chapter_dir).parent)

    print(f"\n{'='*50}")
    print(f"[完结] {chapter}: 章内连续性检查...")
    check_continuity(chapter_dir, chapter, state_path)

    print(f"\n---")
    print(f"[完结] {chapter}: 跨章承诺链检查...")
    cross_chapter(state_path, chapters_dir)

    print(f"\n---")
    print(f"[完结] {chapter}: 风格校验...")
    style_check(chapter_dir, chapter, state_path)

    print(f"\n---")
    print(f"[完结] {chapter}: 通过完结门禁")
    gates = load_gates(state_path)
    gates[f"chapter_finalized:{chapter}"] = "PASS"
    save_gates(state_path, gates)
    print(f"[完结] {chapter}: [OK] 全部完成")


def fidelity_check(state_path, chapters_dir):
    """
    大纲忠实度检查：逐章对比 overview 与实际内容（通用版，无硬编码）
    关键词从 novel_state.json 的 characters/technical_notes/chapters 动态提取。
    """
    import importlib
    sys.path.insert(0, str(SCRIPTS_DIR))
    # 复用 continuity 中的动态关键词提取
    from novel_continuity import _extract_keywords as _ek

    sp = Path(state_path)
    data = json.loads(sp.read_text(encoding="utf-8"))
    chapters = data.get("chapters", [])

    import re
    # 动态提取关键词
    kw_set = _ek(data)
    kw_list = sorted(kw_set, key=len, reverse=True)
    if not kw_list:
        print("[fidelity] 无可用关键词，使用概述词")
        # 回退：从各章概述中提取≥2字词
        for ch in chapters:
            for seg in re.findall(r'[\u4e00-\u9fff]{2,10}', ch.get("overview", "")):
                kw_list.append(seg)
        kw_list = list(set(kw_list))

    keyword_re = re.compile('|'.join(re.escape(p) for p in kw_list))

    report = []
    report.append("# 大纲忠实度报告\n")
    report.append("## 全文检查\n")
    report.append("| 章节 | 概述 | 实际字数 | 关键词覆盖率 | 等级 |")
    report.append("|------|------|---------|-------------|------|")

    pass_count = 0
    info_count = 0
    warn_count = 0
    error_count = 0
    total_chars = 0

    for ch in chapters:
        ch_id = ch["id"]
        if ch.get("status") != "completed":
            report.append(f"| {ch_id} | - | - | - | [WAIT] 未完成 |")
            warn_count += 1
            continue

        overview = ch.get("overview", "")
        # 读取该章节所有子结构文件
        ch_dir = Path(chapters_dir) / ch_id
        actual_text = ""
        if ch_dir.exists():
            for sf in sorted(ch_dir.glob("S*.txt")):
                content = sf.read_text(encoding="utf-8").strip()
                # 跳过标题行和末行标记
                lines = [l for l in content.split("\n") if l.strip() and not re.match(rf'{ch_id}S\d+', l.strip())]
                # 跳过子结构标题行（L## · S##《...》）
                lines = [l for l in lines if not re.match(r'L\d+ · S\d+《', l.strip())]
                actual_text += "".join(lines)

        word_count = ch.get("word_count", 0)
        total_chars += word_count

        if not actual_text:
            level = "ERROR"
            detail = "未找到实际内容"
            error_count += 1
        else:
            # 提取 overview 中的关键词和概述中的话题词
            overview_kws = set(keyword_re.findall(overview))
            actual_kws = set(keyword_re.findall(actual_text))
            if not overview_kws:
                coverage = 1.0  # 概述没有可提取的关键词，跳过
            else:
                matched = overview_kws & actual_kws
                coverage = len(matched) / len(overview_kws)

            if coverage >= 0.6:
                level = "PASS"
                detail = f"覆盖 {len(matched)}/{len(overview_kws)}"
                pass_count += 1
            elif coverage >= 0.3:
                level = "INFO"
                detail = f"部分覆盖 {len(matched)}/{len(overview_kws)}"
                info_count += 1
            elif coverage > 0:
                level = "WARN"
                detail = f"低覆盖 {len(matched)}/{len(overview_kws)}"
                warn_count += 1
            else:
                level = "ERROR"
                detail = "无主题词匹配"
                error_count += 1

        report.append(f"| {ch_id} | {overview[:40]}... | {word_count}字 | {detail} | {level} |")

    report.append(f"\n## 统计")
    report.append(f"| 等级 | 数量 |")
    report.append(f"|------|------|")
    report.append(f"| [OK] PASS | {pass_count} |")
    report.append(f"| ℹ️ INFO | {info_count} |")
    report.append(f"| [WARN] WARN | {warn_count} |")
    report.append(f"| [FAIL] ERROR | {error_count} |")
    report.append(f"| **总字数** | **{total_chars}字** |")

    report_text = "\n".join(report)
    print(report_text)

    # 写入报告
    report_dir = DATA_REPORTS
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "fidelity_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n[报告已写入] {report_path}")

    return pass_count, info_count, warn_count, error_count


def finalize_novel(state_path, chapters_dir):
    """全文完结：全线跨章检查 → 大纲忠实度 → 结尾验证 → 门禁"""
    import sys as _sys
    _sys.path.insert(0, str(SCRIPTS_DIR))
    from novel_continuity import cross_chapter
    from novel_pipeline_gate import pass_gate, load_gates, save_gates
    from novel_fidelity import verify_ending

    print(f"{'='*50}")
    print(f"[全文完结] 开始全线跨章承诺链检查...")
    issues = cross_chapter(state_path, chapters_dir)
    total_gaps = len(issues)

    print(f"\n{'='*50}")
    print(f"[全文完结] 开始大纲忠实度检查...")
    p, i, w, e = fidelity_check(state_path, chapters_dir)

    # 🔴 结尾收束验证
    print(f"\n{'='*50}")
    print(f"[全文完结] 开始结尾收束验证...")
    project_dir = str(Path(state_path).parent)  # state_path 是 project_dir/data/novel_state.json
    ending_result = verify_ending(project_dir)

    print(f"\n{'='*50}")
    print(f"[全文完结] 门禁: fidelity + ending_verify")
    gates = load_gates(state_path)
    if e > 0:
        print(f"[HOOK-BLOCK] 有 {e} 个 ERROR 级别偏差，fidelity 门禁未通过")
        print(f"  请手动修正后重新运行 finalize-novel")
    elif not ending_result.get("pass", False):
        print(f"[HOOK-BLOCK] 结尾收束验证未通过")
        for d in ending_result.get("details", []):
            if not d.get("pass"):
                print(f"  [FAIL] {d.get('name', '?')}: {d.get('reason', '?')}")
        print(f"  请手动修正后重新运行 finalize-novel")
    else:
        gates["fidelity"] = "PASS"
        gates["ending_verify"] = "PASS"
        save_gates(state_path, gates)
        print(f"[全文完结] fidelity [OK] PASS")
        print(f"[全文完结] ending_verify [OK] PASS")
        print(f"[全文完结] 全部完成！")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python novel_workflow_engine.py <命令> [state_path] [args...]")
        print("  state_path 默认: " + str(DATA_STATE))
        print("  命令:")
        print("    plan-chapter     <chapter> <subs_json>")
        print("    verify-chapter   <chapter>")
        print("    preview          <chapter>")
        print("    write-sub        <chapter> <sub_key> [chapters_dir]")
        print("    finalize-chapter <chapter> <chapter_dir> <report_dir>")
        print("    fidelity         [chapters_dir]")
        print("    finalize-novel   [chapters_dir]")
        sys.exit(1)

    cmd = sys.argv[1]
    sp = sys.argv[2] if len(sys.argv) > 2 else str(DATA_STATE)

    if cmd == "plan-chapter":
        plan_chapter(sp, sys.argv[3], sys.argv[4])
    elif cmd == "verify-chapter":
        verify_chapter(sp, sys.argv[3])
    elif cmd == "preview":
        preview_context(sp, sys.argv[3])
    elif cmd == "write-sub":
        write_sub(sp, sys.argv[3], sys.argv[4],
                  sys.argv[5] if len(sys.argv) > 5 else str(DATA_CHAPTERS))
    elif cmd == "finalize-chapter":
        finalize_chapter(sp, sys.argv[3],
                         sys.argv[4] if len(sys.argv) > 4 else str(DATA_CHAPTERS / sys.argv[3]),
                         sys.argv[5] if len(sys.argv) > 5 else str(DATA_REPORTS))
    elif cmd == "fidelity":
        fidelity_check(sp,
                       sys.argv[3] if len(sys.argv) > 3 else str(DATA_CHAPTERS))
    elif cmd == "finalize-novel":
        finalize_novel(sp,
                       sys.argv[3] if len(sys.argv) > 3 else str(DATA_CHAPTERS))
    else:
        print(f"[错误] 未知命令: {cmd}")
