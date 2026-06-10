#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_skill_frontmatter.py — 原子更新 SKILL.md frontmatter 字段
用法：python update_skill_frontmatter.py <skill_dir> [--set key=value ...] [--version <ver>]
v2.34.8
"""
import re, json, os, sys
from pathlib import Path

def parse_frontmatter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return None, content, "未找到 frontmatter"
    fm = {}
    for line in m.group(1).split('\n'):
        if ':' in line:
            k, _, v = line.partition(':')
            fm[k.strip()] = v.strip()
    return fm, content[m.end():], None

def write_frontmatter(filepath, fm, body):
    body = body.lstrip('\n')
    order = ['name','version','author','license','description',
             'sensitive_access','critical_write','permission_weight',
             'artifact_paths','writing_standards','data_dir']
    lines = ['---']
    for k in order:
        if k in fm:
            lines.append(f'{k}: {fm[k]}')
    # 保留 body 里不在 order 中的字段
    existing = set(fm.keys())
    for k in fm:
        if k not in order:
            lines.append(f'{k}: {fm[k]}')
    lines.append('---')
    new_content = '\n'.join(lines) + '\n' + body
    from scripts.safe_io import safe_write
    safe_write(filepath, new_content, backup=True)

def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print("用法: python update_skill_frontmatter.py <skill_dir> [--set key=value ...] [--version <ver>] [--description <desc>]")
        sys.exit(1)
    
    skill_dir = args[0]
    skill_md = os.path.join(skill_dir, 'SKILL.md')
    
    if not os.path.isfile(skill_md):
        print(f"[ERROR] 未找到 SKILL.md: {skill_md}")
        sys.exit(1)
    
    fm, body, err = parse_frontmatter(skill_md)
    if err:
        print(f"[ERROR] {err}")
        sys.exit(1)
    
    changed = False
    i = 1
    while i < len(args):
        arg = args[i]
        if arg == '--set' and i+1 < len(args):
            kv = args[i+1]
            if '=' in kv:
                k, _, v = kv.partition('=')
                fm[k.strip()] = v.strip()
                changed = True
            i += 2
        elif arg == '--version' and i+1 < len(args):
            fm['version'] = args[i+1]
            changed = True
            i += 2
        elif arg == '--description' and i+1 < len(args):
            fm['description'] = args[i+1]
            changed = True
            i += 2
        else:
            i += 1
    
    if changed:
        write_frontmatter(skill_md, fm, body)
        print(f"[OK] {skill_md} frontmatter 已更新")
    else:
        print(f"[INFO] 无变更，当前版本: {fm.get('version', '?')}")

if __name__ == '__main__':
    main()
