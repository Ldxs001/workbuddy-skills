#!/usr/bin/env python3
from auth_check import authorize, initialize

"""git-sync _meta.json 标准化校验。用法: python normalize_meta.py <_meta.json路径> <skill-name> <version> <description>"""

import json, sys, os
from pathlib import Path

def _find_skills_dir():
    """从 scripts/ 往上 2 级确定 skills 目录: skills/<name>/scripts/ → skills/"""
    return str(Path(__file__).resolve().parent.parent.parent)

def load_config():
    """读取 skills/.standardization/git-sync/data/config.json，返回配置字典"""
    skills_dir = _find_skills_dir()
    config_path = os.path.join(skills_dir, ".standardization", "git-sync", "data", "config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def normalize(meta_file, skill_name, version, description):
    """标准化 _meta.json：只保留 name/version/description/author/tags 5 个标准字段。"""
    standard_fields = {'name', 'version', 'description', 'author', 'tags'}

    # 读取默认 author
    config = load_config()
    default_author = config.get('author', 'unknown')

    if not os.path.exists(meta_file):
        # 创建新文件
        meta = {
            'name': skill_name,
            'version': version,
            'description': description,
            'author': default_author,
            'tags': []
        }
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f'  ✅ _meta.json 已创建（author={default_author}）')
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

    # 3. 补全/更新缺失或过期字段
    added = []
    if 'version' not in meta:
        meta['version'] = version
        added.append('version')
    elif meta['version'] != version:
        old_ver = meta['version']
        meta['version'] = version
        added.append(f'version: {old_ver} → {version}')
    if 'description' not in meta or not meta.get('description'):
        meta['description'] = description or ''
        added.append('description')
    if 'tags' not in meta or not isinstance(meta.get('tags'), list):
        meta['tags'] = []
        added.append('tags')

    # author：如果已有值且非空，保留；否则用 config 的默认值
    if 'author' not in meta or not meta.get('author'):
        meta['author'] = default_author

    modified = json.dumps(meta, ensure_ascii=False, indent=2)

    if original != modified:
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        changes = []
        if removed:
            changes.append(f'删除: {removed}')
        if added:
            changes.append(f'补全: {added}')
        if meta.get('author') == default_author:
            changes.append(f'author: {default_author}')
        print(f'  ✅ _meta.json 已标准化（{" | ".join(changes)}）')
    else:
        print(f'  ✅ _meta.json 已符合标准，无需修改')

    print(f'  📋 name={meta["name"]}, version={meta["version"]}, author={meta["author"]}, tags={len(meta["tags"])}个')

if __name__ == '__main__':
        initialize()
    if len(sys.argv) < 4:
        print(f'用法: {sys.argv[0]} <_meta.json路径> <skill-name> <version> [description]')
        sys.exit(1)
    meta_file = sys.argv[1]
    skill_name = sys.argv[2]
    version = sys.argv[3]
    description = sys.argv[4] if len(sys.argv) >= 5 else ''
    normalize(meta_file, skill_name, version, description)