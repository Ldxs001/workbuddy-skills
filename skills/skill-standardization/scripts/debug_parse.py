#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from skill_audit.utils import parse_simple_yaml_frontmatter

with open(os.path.join(os.path.dirname(__file__), '..', 'SKILL.md'), 'r', encoding='utf-8') as f:
    content = f.read()

fm, body = parse_simple_yaml_frontmatter(content)

out = []
out.append(f'parse_simple_yaml_frontmatter 返回类型: {type(fm).__name__}')
if isinstance(fm, dict):
    out.append(f'解析到 {len(fm)} 个字段:')
    for k, v in fm.items():
        out.append(f'  [{k}] = {v!r} (type: {type(v).__name__})')
else:
    out.append(f'返回值类型异常: {type(fm)}')
    out.append(f'fm = {fm!r}')

with open('C:\Users\sm001\workbuddy\skills\skill-standardization\scripts\debug_parse_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print('OK: 结果已写入 debug_parse_output.txt')
