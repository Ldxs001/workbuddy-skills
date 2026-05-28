#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 utils.py 第227行多余的 }, + 验证 R-24 在 RULES 列表内"""
import os

UTILS = r"C:\Users\sm001\.workbuddy\skills\skill-standardization\scripts\skill_audit\utils.py"

with open(UTILS, "r", encoding="utf-8") as f:
    content = f.read()

# 验证：R-24 条目必须在 ] 之前（即在 RULES 列表内部）
lines = content.split("\n")
in_rules = False
r24_found = False
r24_inside = False
closing_bracket_idx = None

for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == "RULES = [":
        in_rules = True
    if in_rules:
        if stripped.startswith('"id": "R-24"'):
            r24_found = True
            # 检查这一行是否在 ] 之前
            for j in range(i, len(lines)):
                if lines[j].strip() == "]":
                    closing_bracket_idx = j
                    break
            # R-24 行号 < ] 行号 → 在列表内部
            r24_inside = (i < closing_bracket_idx)
            break

print(f"  R-24 条目存在: {r24_found}")
print(f"  R-24 在 ] 之前（列表内部）: {r24_inside}")

# 修复：删除多余的 },
# 当前结构：R-23 的 }, 之后多了一个 }, 然后才是 R-24 的 {
# 正确结构：R-23 的 }, 之后直接是 R-24 的 {，然后是 ]
old_pattern = '    },\n    },\n    # ── 新增规则 R-24 (v2.38.6)'
new_pattern = '    },\n    # ── 新增规则 R-24 (v2.38.6)'

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern, 1)
    tmp = UTILS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, UTILS)
    print("[OK] utils.py — 删除多余的 },（第227行）")
else:
    print("[WARN] 未找到预期的旧模式，尝试按行号修复...")
    # 按行号修复：找到 R-23 的 }，然后删除紧随其后的独立 }, 行
    lines = content.split("\n")
    new_lines = []
    skip_next = False
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        # 如果这一行是 R-23 的 closing }，下一行是独立的 },，则跳过下一行
        if line.strip() == "}," and i + 1 < len(lines) and lines[i+1].strip() == "},":
            # 这一行是 R-23 的正常关闭，保留
            new_lines.append(line)
            skip_next = True  # 跳过下一个 },（多余的那个）
            print(f"  [fix] 跳过第 {i+2} 行的多余 }},")
        else:
            new_lines.append(line)
    content = "\n".join(new_lines)
    tmp = UTILS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, UTILS)
    print("[OK] utils.py — 按行号删除多余的 },")

# 验证修复结果
with open(UTILS, "r", encoding="utf-8") as f:
   验证内容 = f.read()

try:
    compile(验证内容, UTILS, "exec")
    print("[PASS] utils.py 语法检查通过")
except SyntaxError as e:
    print(f"[FAIL] utils.py 仍有语法错误: {e}")
    exit(1)

print("[DONE] utils.py 修复完成")
