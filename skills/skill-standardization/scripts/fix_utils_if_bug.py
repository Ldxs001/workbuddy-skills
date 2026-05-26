#!/usr/bin/env python3
"""修复 utils.py 中 parse_simple_yaml_frontmatter() 的 if/if bug
   
   原代码（错误）：
    1. if val.startswith("[") and val.endswith("]"):
           ...  # 处理 list
       if val:    # <-- 并列 if，list 值会被这里覆盖！
           ...  # 处理 bool/string
    
   修复后：
    1. if val.startswith("[") and val.endswith("]"):
           ...  # 处理 list
       elif val:  # <-- 改为 elif，list 和 非list 互斥
           ...  # 处理 bool/string
"""
import os, re

utils_py = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'skill_audit', 'utils.py'))

with open(utils_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 定位并修复：找到 "if val.startswith("" 后面的独立 "if val:" -> "elif val:"
# 关键特征：在一个 for 循环内，有两处 if val: 后面紧跟 current_key = key
# 修复策略：把处理 val 的第二个 if 改成 elif

old_pattern = r'(if val\.startswith\(\[") and val\.endswith\("\]"\):\s*\n\s*# 处理 list.*?\n\s*)(if val:)'
new_pattern = r'\1elif val:'

fixed_content = re.sub(old_pattern, new_pattern, content, flags=re.DOTALL)

if fixed_content == content:
    print("WARN: 没找到预期模式，尝试直接搜索 'if val:' 在合适位置改为 'elif val:'")
    # 备用：直接在 parse_simple_yaml_frontmatter 函数里把第二个 if val: 改成 elif val:
    # 找到函数定义，然后在函数体内把第二个 if val: 改成 elif
    lines = content.split('\n')
    in_func = False
    if_val_count = 0
    for i, line in enumerate(lines):
        if 'def parse_simple_yaml_frontmatter' in line:
            in_func = True
        if in_func:
            # 检查是否离开了函数（取消缩进到 def 级别）
            if i > 0 and lines[i].strip() and not lines[i].startswith('    ') and not lines[i].startswith('\t'):
                in_func = False
            if in_func and re.match(r'\s*if val:', line) and 'startswith' not in line:
                if_val_count += 1
                if if_val_count == 1:
                    # 第二个 if val: 改成 elif val:
                    lines[i] = line.replace('if val:', 'elif val:', 1)
                    print(f'  L{i+1}: 已修复 if val: -> elif val:')
    fixed_content = '\n'.join(lines)
else:
    print("OK: 主模式匹配成功，已修复 if -> elif")

# 原子写入
tmp = utils_py + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(fixed_content)
os.replace(tmp, utils_py)
print(f'OK: {utils_py} 已修复（if/if -> if/elif）')

# 验证：导入并测试
import sys
sys.path.insert(0, os.path.join(os.path.dirname(utils_py), '..', '..'))
from skill_audit.utils import parse_simple_yaml_frontmatter

test_fm = """---
name: test
version: 1.0.0
sensitive_access: True
critical_write: False
permission_weight: HIGH
artifact_paths: []
writing_standards: []
---"""
result, body = parse_simple_yaml_frontmatter(test_fm)
print(f'\n验证测试结果（7 个字段应全部解析）：')
for k in ['name','version','sensitive_access','critical_write','permission_weight','artifact_paths','writing_standards']:
    v = result.get(k, '!!!缺失!!!')
    print(f'  {k} = {v!r}')
print(f'解析到 {len(result)} 个字段')
