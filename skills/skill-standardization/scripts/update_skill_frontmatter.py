#!/usr/bin/env python3
"""原子方式更新 SKILL.md 的 frontmatter，补全缺失字段"""

import os, re

skill_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
skill_md = os.path.join(skill_dir, 'SKILL.md')

with open(skill_md, 'r', encoding='utf-8') as f:
    content = f.read()

# 解析现有 frontmatter
fm_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
if not fm_match:
    print("ERROR: 找不到 frontmatter")
    exit(1)

fm_text = fm_match.group(1)
rest = content[fm_match.end():]

# 解析现有字段
fields = {}
for line in fm_text.splitlines():
    line = line.rstrip()
    if not line or line.startswith('#'):
        continue
    if ':' in line:
        k, _, v = line.partition(':')
        k = k.strip()
        v = v.strip()
        # 去掉引号
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        fields[k] = v

# 需要补全的字段（按规范顺序）
required = [
    ('name', fields.get('name', 'skill-standardization')),
    ('version', fields.get('version', '2.33.0')),
    ('author', fields.get('author', '[username-redacted]')),
    ('license', fields.get('license', 'MIT')),
    ('description', fields.get('description', '')),
    ('data_dir', fields.get('data_dir', '../.standardization/skill-standardization/')),
    ('sensitive_access', 'True'),
    ('critical_write', 'False'),
    ('permission_weight', 'HIGH'),
    ('artifact_paths', '[]'),
    ('writing_standards', '[]'),
]

# 重新生成 frontmatter（保持顺序）
lines = []
for k, v in required:
    if k == 'description':
        lines.append(f'{k}: {v}')
    elif k in ('sensitive_access', 'critical_write'):
        lines.append(f'{k}: {v}')
    elif k == 'permission_weight':
        lines.append(f'{k}: {v}')
    elif k in ('artifact_paths', 'writing_standards'):
        lines.append(f'{k}: {v}')
    else:
        lines.append(f'{k}: {v}')

new_fm = '---\n' + '\n'.join(lines) + '\n---\n' + rest

# 原子写入
tmp = skill_md + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(new_fm)
os.replace(tmp, skill_md)

print(f"OK: {skill_md}")
print("写入字段:")
for k, v in required:
    print(f"  {k}: {v}")
