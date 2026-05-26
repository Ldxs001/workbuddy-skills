#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bump skill-standardization to 2.35.1 and sync."""

import os, json, subprocess, sys

SKILL_DIR = r"C:\Users\sm001\.workbuddy\skills\skill-standardization"

def read(p):
    with open(os.path.join(SKILL_DIR, p), 'r', encoding='utf-8') as f:
        return f.read()

def write(p, c):
    with open(os.path.join(SKILL_DIR, p), 'w', encoding='utf-8') as f:
        f.write(c)

# 1. SKILL.md
c = read('SKILL.md')
lines = c.split('\n')
for i, ln in enumerate(lines):
    if ln.startswith('version:'):
        lines[i] = 'version: "2.35.1"'
        print(f'SKILL.md version -> 2.35.1 (line {i+1})')
        break
write('SKILL.md', '\n'.join(lines))

# 2. changelog.md - insert v2.35.1 entry after first ## heading
c = read('references/changelog.md')
lines = c.split('\n')
insert_at = None
for i, ln in enumerate(lines):
    if ln.startswith('## ') and 'v2.35' in ln:
        insert_at = i
        break
if insert_at is None:
    for i, ln in enumerate(lines):
        if ln.strip():
            insert_at = i + 1
            break
entry = [
    '',
    '## v2.35.1',
    '',
    '- **修复**：`changelog.md` 术语不一致（`移除`/`删除` 混用），R-20 审查触发 WARN，统一为 `删除`（1 处）',
    '- **流程**：版本 bump 触发强制同步，确保码云/GitHub 文件内容一致',
    '',
]
lines = lines[:insert_at] + entry + lines[insert_at:]
write('references/changelog.md', '\n'.join(lines))
print('changelog.md -> added v2.35.1')

# 3. _meta.json
meta = json.loads(read('_meta.json'))
meta['version'] = '2.35.1'
meta['description'] = 'Skill 标准化规范引擎 v2.35.1。修复 _AUDIT_CONTROL_FIELDS bug、R-11 误报、R-20 术语不一致（changelog.md 移除→删除）。支持 R-01~R-23 审查，create/update/refactor 三模式。'
write('_meta.json', json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
print('_meta.json -> 2.35.1')

print('\nAll version files updated.')
