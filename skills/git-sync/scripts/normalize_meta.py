#!/usr/bin/env python3
"""git-sync _meta.json 标准化校验。用法: python normalize_meta.py <_meta.json路径> <skill-name> <version> <description>"""

import json, sys, os
from pathlib import Path

# R-12 审计锚点：数据目录字面量声明
DEFAULT_DATA_DIR_RAW = "skills/.standardization/git-sync/data/"

SKILL_DIR = Path(__file__).resolve().parent.parent
# 运行时绝对路径
_data_dir_abs = SKILL_DIR.parent / ".standardization" / "git-sync" / "data"




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
    """_meta.json 版本同步：只更新 version/description，不删除任何字段。"""
    config = load_config()
    default_author = config.get('author', 'unknown')

    if not os.path.exists(meta_file):
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

    updated = []

    # 补 name（如果缺失）
    if 'name' not in meta:
        meta['name'] = skill_name
        updated.append('name')

    # 只同步 version
    if 'version' not in meta:
        meta['version'] = version
        updated.append('version')
    elif meta['version'] != version:
        old_ver = meta['version']
        meta['version'] = version
        updated.append(f'version: {old_ver} → {version}')

    # 只同步 description（如果缺失）
    if 'description' not in meta or not meta.get('description'):
        meta['description'] = description or ''
        updated.append('description')

    # author（non-destructive）
    if 'author' not in meta or not meta.get('author'):
        meta['author'] = default_author

    # 不删除任何字段
    modified = json.dumps(meta, ensure_ascii=False, indent=2)

    if original != modified:
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f'  ✅ _meta.json 已同步（{", ".join(updated)}）')
    else:
        print(f'  ✅ _meta.json 已符合标准，无需修改')

    print(f'  📋 name={meta["name"]}, version={meta["version"]}, author={meta.get("author","?")}, tags={len(meta.get("tags",[]))}个')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(f'用法: {sys.argv[0]} <_meta.json路径> <skill-name> <version> [description]')
        sys.exit(1)
    meta_file = sys.argv[1]
    skill_name = sys.argv[2]
    version = sys.argv[3]
    description = sys.argv[4] if len(sys.argv) >= 5 else ''
    normalize(meta_file, skill_name, version, description)
