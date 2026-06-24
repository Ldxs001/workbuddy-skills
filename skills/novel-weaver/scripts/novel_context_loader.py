#!/usr/bin/env python3
"""
Context Loader — 上下文加载器
验证子结构是否已注册，加载写作上下文
"""
import json, sys
from pathlib import Path

def load_context(state_path, chapter, sub_key):
    """加载写作上下文：上一子结构的末3行+当前子结构规划"""
    sp = Path(state_path)
    if not sp.exists():
        print(f"[错误] state 文件不存在: {state_path}")
        sys.exit(1)

    data = json.loads(sp.read_text(encoding="utf-8"))

    # 查找当前章节
    ch_info = None
    ch_dir = None
    for ch in data.get("chapters", []):
        if ch["id"] == chapter:
            ch_info = ch
            break

    if not ch_info:
        print(f"[错误] 章节 {chapter} 未找到")
        sys.exit(1)

    # 验证子结构已注册
    subs = ch_info.get("sub_structures", {})
    if sub_key not in subs:
        print(f"[阻断] {chapter}{sub_key} 未注册，拒绝加载上下文")
        print(f"[提示] 先运行 plan-chapter 注册子结构")
        sys.exit(1)

    # 查找上一个已完成的子结构
    sub_keys = sorted(subs.keys())
    current_idx = sub_keys.index(sub_key) if sub_key in sub_keys else -1
    prev_lines = []
    if current_idx > 0:
        prev_key = sub_keys[current_idx - 1]
        prev_file = Path(sp.parent) / "chapters" / chapter / f"{prev_key}.txt"
        if prev_file.exists():
            lines = prev_file.read_text(encoding="utf-8").strip().split("\n")
            # 跳过末行标记行，取末3行正文
            prev_text = [l for l in lines if not l.strip().startswith(f"{chapter}")]
            prev_lines = prev_text[-3:] if len(prev_text) >= 3 else prev_text

    # 输出上下文
    print(f"{'='*50}")
    print(f"[上下文] {chapter}{sub_key}")
    print(f"[章节概述] {ch_info.get('overview', '')}")
    print(f"[子结构规划] title={subs[sub_key].get('title','')}")
    print(f"[子结构概述] {subs[sub_key].get('summary','')}")
    print(f"[情绪提示] {subs[sub_key].get('tone','')}")
    if prev_lines:
        print(f"[上一子结构末3行]:")
        for l in prev_lines:
            print(f"  | {l}")
    print(f"{'='*50}")

    # 🔴 收尾命题框（is_ending=true 时追加）
    if subs[sub_key].get("is_ending"):
        ending_type = subs[sub_key].get("ending_type", "未指定")
        project = data.get("project", "未知项目")
        core_conflict = data.get("core_conflict", "未知冲突")
        protagonist = data.get("protagonist", "未知主角")
        theme = data.get("theme", "未知主题")

        print(f"\n{'='*50}")
        print(f"🔴 收尾约束（硬性）")
        print(f"{'='*50}")
        print(f"  收尾类型: {ending_type}")
        print(f"  {'─'*40}")
        if ending_type == "封闭式":
            print(f"  □ 核心冲突必须落地（起始于: {core_conflict}）")
            print(f"  □ 主角弧必须闭合（起始于: {protagonist}）")
            print(f"  □ 主题必须回扣（{theme}）")
            print(f"  □ 末句用动作收束（推门。/关灯。/转身。）")
        elif ending_type == "开放式":
            print(f"  □ 核心冲突必须有明确结果（起始于: {core_conflict}）")
            print(f"  □ 留白必须服务于主题（{theme}）")
            print(f"  □ 情绪基调必须收敛")
            print(f"  □ 禁止: 未完待续/预知后事如何/一切才刚刚开始")
        elif ending_type == "悬停式":
            print(f"  □ 留下一个具体悬念（必须可命名）")
            print(f"  □ 悬停点必须是节奏最高处")
            print(f"  □ 主角必须有阶段性成长（起始于: {protagonist}）")
            print(f"  □ 情绪必须有明确指向（焦虑/希望/恐惧/期待）")
            print(f"  □ 禁止: 未完待续/一切才刚刚开始")
        else:
            print(f"  ⚠️ 末子结构概述缺少【收尾类型】标签（应为封闭式/开放式/悬停式）")
            print(f"  □ 请修正概述后重新 plan-chapter")
        print(f"  {'─'*40}")
        print(f"  提示: 以上为命题约束，不可偏离")
        print(f"{'='*50}\n")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python novel_context_loader.py <state_path> <chapter> <sub_key>")
        sys.exit(1)
    load_context(sys.argv[1], sys.argv[2], sys.argv[3])
