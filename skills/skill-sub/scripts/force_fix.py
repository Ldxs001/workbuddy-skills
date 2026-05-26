#!/usr/bin/env python3
"""强制修复 chain_manager.py 第 900 行（0-based 899）的 f-string 语法错误"""
p = r"C:\Users\sm001\.workbuddy\skills\skill-sub\scripts\chain_manager.py"

with open(p, "rb") as f:
    raw = f.read()

# 按 \r\n 分割
lines = raw.split(b"\r\n")
print(f"总行数: {len(lines)}")
print(f"第 900 行（0-based 899）内容: {repr(lines[899][:200])}")
print(f"包含 print 次数: {lines[899].count(b'print(')}")

# 检查是否有未关闭的 f-string
line = lines[899]
if b'print(f"' in line and line.count(b'"') % 2 == 1:
    print("⚠️  检测到未关闭的 f-string")
    # 需要拆分这一行
    # 找第二个 print 的位置
    second_start = line.find(b'print(f"', line.find(b')') + 1)
    if second_start != -1:
        part1 = line[:second_start]
        part2 = line[second_start:]
        print(f"拆分后第一部分: {repr(part1)}")
        print(f"拆分后第二部分: {repr(part2)}")
        lines[899] = part1
        lines.insert(900, part2)
        print(f"✅ 已拆分成两行")
    else:
        print("❌ 未找到第二个 print，尝试通用修复...")
        # 通用修复：在 f-string 未关闭的地方插入 "
        # 找最后一个 " 的位置
        last_quote = line.rfind(b'"')
        if last_quote != -1 and line[last_quote+1:last_quote+2] != b')':
            # 在最后一个 " 后面插入 )
            line = line[:last_quote+1] + b')' + line[last_quote+1:]
            lines[899] = line
            print(f"✅ 已修复（插入 )）")
else:
    print("✅ 未检测到未关闭的 f-string，可能已修复")

# 写入文件
with open(p, "wb") as f:
    f.write(b"\r\n".join(lines))

print(f"\n✅ 文件已写入，新的总行数: {len(lines)}")

# 验证语法
import py_compile
try:
    py_compile.compile(p, doraise=True)
    print("✅ 语法正确！")
except py_compile.PyCompileError as e:
    print(f"❌ 还有语法错误: {e}")
    # 找错误行
    import re
    m = re.search(r"line (\d+)", str(e))
    if m:
        line_no = int(m.group(1)) - 1  # 0-based
        if 0 <= line_no < len(lines):
            print(f"错误行内容: {repr(lines[line_no])}")
