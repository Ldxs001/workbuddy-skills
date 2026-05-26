#!/usr/bin/env python3
"""强制修复 chain_manager.py 中所有 f-string 语法错误（稳健版）"""
p = r"C:\Users\sm001\.workbuddy\skills\skill-sub\scripts\chain_manager.py"

with open(p, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"总行数: {len(lines)}")

# 找所有有问题的行：以 print(f" 开头，但没有匹配的 )
fixed = 0
i = 0
new_lines = []
while i < len(lines):
    line = lines[i]
    # 检查这一行是否有未关闭的 f-string
    if 'print(f"' in line or "print(f'" in line:
        # 数这一行中（除了转义的）双引号的数量
        # 简化：如果这一行以 print(f" 开头，且 ) 不在这一行
        if ')' not in line or line.count('"') % 2 == 1:
            # 需要合并下一行
            if i + 1 < len(lines):
                merged = line.rstrip('\n') + lines[i+1]
                new_lines.append(merged)
                i += 2
                fixed += 1
                continue
    new_lines.append(line)
    i += 1

if fixed > 0:
    print(f"修复了 {fixed} 处 f-string 问题")
    with open(p, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"✅ 已写入，新行数: {len(new_lines)}")
else:
    print("未找到需要修复的 f-string 问题")

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
        if 0 <= line_no < len(new_lines):
            print(f"错误行内容: {repr(new_lines[line_no][:200])}")
        else:
            # 用原始文件
            with open(p, "r", encoding="utf-8") as f:
                orig_lines = f.readlines()
            if 0 <= line_no < len(orig_lines):
                print(f"错误行内容（原始）: {repr(orig_lines[line_no][:200])}")
