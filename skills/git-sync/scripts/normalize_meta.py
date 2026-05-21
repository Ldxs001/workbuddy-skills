#!/usr/bin/env python3
"""git-sync _meta.json 标准化校验。用法: python normalize_meta.py <_meta.json路径> <skill-name> <version> <description>"""
import json, sys, os

def normalize(meta_file, skill_name, version, description):
    """标准化 _meta.json：只保留 name/version/description/author/tags 5 个标准字段。"""
    standard_fields = {'name', 'version', 'description', 'author', 'tags'}

    if not os.path.exists(meta_file):
        # 创建新文件
        meta = {
            'name': skill_name,
            'version': version,
            'description': description,
            'author': 'wUwproject',
            'tags': []
        }
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f'  ✅ _meta.json 已创建')
        print(f'  📋 name={meta["name"]}, version={meta["version"]}, author={meta["author"]}, tags={len(meta["tags"])}个')
        return

    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    original = json.dumps(meta, ensure_ascii=False, indent=2)

    # 1. slug → name 迁移
    if 'slug' in meta and 'name' not in meta:
        meta['name'] = meta['slug']
    elif 'name' not in meta:
        meta['name'] = skill_name

    # 2. 删除所有非标准字段
    removed = [k for k in list(meta.keys()) if k not in standard_fields]
    for key in removed:
        del meta[key]

    # 3. 补全缺失字段
    added = []
    if 'version' not in meta:
        meta['version'] = version
        added.append('version')
    if 'description' not in meta or not meta.get('description'):
        meta['description'] = description or ''
        added.append('description')
    if 'tags' not in meta or not isinstance(meta.get('tags'), list):
        meta['tags'] = []
        added.append('tags')

    # author 强制统一
    meta['author'] = 'wUwproject'

    modified = json.dumps(meta, ensure_ascii=False, indent=2)

    if original != modified:
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        changes = []
        if removed:
            changes.append(f'删除: {removed}')
        if added:
            changes.append(f'补全: {added}')
        print(f'  ✅ _meta.json 已标准化（{" | ".join(changes)}）')
    else:
        print(f'  ✅ _meta.json 已符合标准，无需修改')

    print(f'  📋 name={meta["name"]}, version={meta["version"]}, author={meta["author"]}, tags={len(meta["tags"])}个')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(f'用法: {sys.argv[0]} <_meta.json路径> <skill-name> <version> [description]')
        sys.exit(1)
    meta_file = sys.argv[1]
    skill_name = sys.argv[2]
    version = sys.argv[3]
    description = sys.argv[4] if len(sys.argv) >= 5 else ''
    normalize(meta_file, skill_name, version, description)
