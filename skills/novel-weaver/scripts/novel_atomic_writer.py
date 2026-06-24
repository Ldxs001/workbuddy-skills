#!/usr/bin/env python3
"""
novel-atomic-writer — 行级别原子写入器。

用途：
  - 按行写入正文文件，每行后 os.fsync()，防止断电丢失整篇
  - 维护 .progress 标记文件，记录已写入的行数，支持断点续写
  - 读取上一个子结构的末 N 行作为连接锚点（自动跳过末尾编号标记行）
  - 写入末尾编号标记行（如 L10S04）

用法：
  python novel_atomic_writer.py write <filepath> <line>          # 写入单行（追加）
  python novel_atomic_writer.py write-batch <filepath> <lines>   # 写入多行（追加）
  python novel_atomic_writer.py finalize <filepath> <marker>     # 写入末尾编号标记行（如 L10S04）
  python novel_atomic_writer.py tail <filepath> <n>              # 读取末 N 行（跳过编号标记行）
  python novel_atomic_writer.py head <filepath> <n>              # 读取首 N 行
  python novel_atomic_writer.py progress <filepath>              # 获取已写入行数
"""

import os
import sys
import json
import re

# 标记行模式：L##S##（如 L10S04），禁止出现在正文中
_MARKER_PATTERN = re.compile(r'^L\d{1,2}S\d{1,3}$')


def _validate_body_line(line: str):
    """检查一行是否看起来像子结构标记行，若是则阻断（标记行只能用 finalize 写入）"""
    stripped = line.strip()
    if _MARKER_PATTERN.match(stripped):
        print(f"ERROR: 正文中不能包含子结构标记行 '{stripped}'")
        print(f"  → 标记行只能通过 finalize 命令写入文件末尾")
        print(f"  → 如果需要引用子结构编号，请使用其他格式（如“第5小节”或“S05”）")
        sys.exit(1)


def _progress_path(filepath: str) -> str:
    return filepath + ".progress"


def write_line(filepath: str, line: str) -> int:
    """写入单行并 fsync，返回当前行数"""
    _validate_body_line(line)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())
    # 更新 progress
    count = _update_progress(filepath, 1)
    return count


def write_batch(filepath: str, lines: list) -> int:
    """写入多行（每行独立 fsync），返回总行数"""
    for line in lines:
        _validate_body_line(line)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    count = 0
    with open(filepath, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
            count += 1
    _update_progress(filepath, count)
    # 读取 progress 文件中的累计值
    prog_path = _progress_path(filepath)
    if os.path.exists(prog_path):
        with open(prog_path, "r", encoding="utf-8") as pf:
            return int(pf.read().strip())
    return count


def _update_progress(filepath: str, added: int):
    """累加进度"""
    prog_path = _progress_path(filepath)
    current = 0
    if os.path.exists(prog_path):
        with open(prog_path, "r", encoding="utf-8") as pf:
            try:
                current = int(pf.read().strip())
            except ValueError:
                current = 0
    current += added
    with open(prog_path, "w", encoding="utf-8") as pf:
        pf.write(str(current))
        pf.flush()
        os.fsync(pf.fileno())
    return current


def finalize(filepath: str, marker: str) -> str:
    """写入末尾编号标记行（如 L10S04）"""
    write_line(filepath, marker)
    return marker


def read_tail(filepath: str, n: int = 3) -> list:
    """读取文件末 N 行（跳过末尾编号标记行，如 L10S04）"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n\r") for l in f.readlines()]

    # 跳过末尾的空行和编号标记行
    while lines and (not lines[-1] or lines[-1].startswith("L") and len(lines[-1]) <= 8):
        lines.pop()

    return [l for l in lines[-n:] if l]


def read_head(filepath: str, n: int = 3) -> list:
    """读取文件首 N 行"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i >= n:
                break
            stripped = line.rstrip("\n\r")
            if stripped:
                lines.append(stripped)
    return lines


def get_progress(filepath: str) -> int:
    """获取已写入行数"""
    prog_path = _progress_path(filepath)
    if not os.path.exists(prog_path):
        return 0
    with open(prog_path, "r", encoding="utf-8") as pf:
        try:
            return int(pf.read().strip())
        except ValueError:
            return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: atomic_writer.py <write|write-batch|tail|head|progress> <filepath> [args...]")
        sys.exit(1)

    command = sys.argv[1]
    filepath = sys.argv[2]

    if command == "write" and len(sys.argv) >= 4:
        line = sys.argv[3]
        count = write_line(filepath, line)
        print(f"OK line={count}")

    elif command == "write-batch" and len(sys.argv) >= 4:
        lines_raw = sys.argv[3]
        lines = lines_raw.split("\\n")
        count = write_batch(filepath, lines)
        print(f"OK lines={count}")

    elif command == "finalize" and len(sys.argv) >= 4:
        marker = sys.argv[3]
        result = finalize(filepath, marker)
        print(f"OK marker={result}")

    elif command == "tail":
        n = int(sys.argv[3]) if len(sys.argv) >= 4 else 3
        result = read_tail(filepath, n)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "head":
        n = int(sys.argv[3]) if len(sys.argv) >= 4 else 3
        result = read_head(filepath, n)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "progress":
        count = get_progress(filepath)
        print(count)

    else:
        print(f"未知命令: {command}")
        sys.exit(1)
