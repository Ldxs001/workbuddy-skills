#!/usr/bin/env python3
"""强制修复 chain_manager.py 中所有 f-string 语法错误"""
p = r"C:\Users\sm001\.workbuddy\skills\skill-sub\scripts\chain_manager.py"

with open(p, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"总行数: {len(lines)}")

# 找所有有问题的行：print(f" 开头但没有匹配的 ")
fixed = 0
i = 0
while i < len(lines):
    line = lines[i]
    # 检查这一行是否有未关闭的 f-string
    if 'print(f"' in line or "print(f'" in line:
        # 数双引号（排除转义的）
        # 简化：如果这一行以 print(f" 开头，且 " 的数量是奇数
        if line.count('"') % 2 == 1:
            # 需要合并下一行
            if i + 1 < len(lines):
                merged = line.rstrip('\n') + lines[i+1]
                lines[i] = merged
                del lines[i+1]
                fixed += 1
                continue
    i += 1

print(f"修复了 {fixed} 处")

with open(p, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"✅ 已写入，新行数: {len(lines)}")

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
            print(f"错误行内容: {repr(lines[line_no][:200])}")
