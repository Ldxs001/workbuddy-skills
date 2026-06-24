#!/usr/bin/env python3
"""
Atomic Writer — 原子写入器（v2，格式硬约束版）

格式规范（钩子强制执行，阻断式）：
  第1行: L## · S##《标题》
  第2..N-1行: 正文（纯叙事，不得含子结构标记行）
  末行: L##S##（由本脚本自动追加）

流程门禁：
  1. title_line 正则校验（阻断）
  2. body 标记行检测（阻断）
  3. 正文非空检测（阻断）
  4. 原子写入 → fsync → 追加编号标记 → 再次 fsync
"""
import sys, os, re
from pathlib import Path

TITLE_PATTERN = re.compile(r'^L\d+ · S\d+《.+》$')
MARKER_PATTERN = re.compile(r'^L\d+S\d+$')

def validate_and_write(content, filepath, chapter, sub_key):
    fp = Path(filepath)
    fp.parent.mkdir(parents=True, exist_ok=True)

    sub_marker = f"{chapter}{sub_key}"
    lines = content.split("\n")

    # ── 钩子1: 第1行标题格式校验（阻断） ──
    first_line = lines[0].strip() if lines else ""
    if not TITLE_PATTERN.match(first_line):
        print(f"[HOOK-BLOCK] 第1行不是合法标题格式")
        print(f"  期望: L{chapter} · {sub_key}《标题》")
        print(f"  实际: {first_line}")
        return False

    # ── 钩子2: 正文非空检测（阻断） ──
    body_lines = lines[1:]
    body_text = "\n".join(body_lines).strip()
    if not body_text:
        print(f"[HOOK-BLOCK] 正文为空，拒绝写入")
        return False

    # ── 钩子3: 正文标记行检测（阻断） ──
    for i, line in enumerate(body_lines, 2):  # 行号从2开始计数（第1行是标题）
        stripped = line.strip()
        if MARKER_PATTERN.match(stripped):
            print(f"[HOOK-BLOCK] 正文第{i}行含非法子结构标记: {line.strip()}")
            return False

    # ── 写入前确认: 最终内容不含元注释污染 ──
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # 禁止助手元注释（**S01 完成（字数： 之类的模式）
        if re.match(r'^\*\*(S\d+|L\d+)\s*(完成|全章完成)', stripped):
            print(f"[HOOK-BLOCK] 正文第{i}行含元注释污染: {line.strip()}")
            print(f"  禁止将助手工作记录写入作品文件")
            return False

    # ── 原子写入 ──
    # 写入正文（不含末行标记）
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    # 追加子结构编号标记
    with open(fp, "a", encoding="utf-8") as f:
        f.write(f"\n{sub_marker}\n")
        f.flush()
        os.fsync(f.fileno())

    print(f"[WRITE-OK] {filepath}")
    print(f"  标题: {first_line}")
    print(f"  正文: {len(body_lines)} 行")
    print(f"  标记: {sub_marker}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("用法: python novel_atomic_writer.py <content_file|-> <filepath> <chapter> <sub_key>")
        print("  - 表示从 stdin 读取内容")
        print("  示例: echo '内容' | python novel_atomic_writer.py - /path/to/L01/S01.txt L01 S01")
        sys.exit(1)

    content_src = sys.argv[1]
    filepath = sys.argv[2]
    chapter = sys.argv[3]
    sub_key = sys.argv[4]

    if content_src == "-":
        content = sys.stdin.read()
    else:
        content = Path(content_src).read_text(encoding="utf-8")

    success = validate_and_write(content, filepath, chapter, sub_key)
    if not success:
        sys.exit(1)
