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

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python novel_context_loader.py <state_path> <chapter> <sub_key>")
        sys.exit(1)
    load_context(sys.argv[1], sys.argv[2], sys.argv[3])
