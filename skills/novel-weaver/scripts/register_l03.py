#!/usr/bin/env python3
"""Register L03 substructures for 赛博搏杀记"""

import json, sys
sys.path.insert(0, 'scripts')

from pathlib import Path
from novel_workflow_engine import plan_chapter

PROJECT = '赛博搏杀记'
CHAPTER = 'L03'

# 从文件读取 JSON（避免 shell 转义问题）
with open('scripts/l03_subs.json', 'r', encoding='utf-8') as f:
    subs_json = f.read()

print(f"计划注册：{PROJECT}/{CHAPTER}")
print("子结构列表:")

data = json.loads(subs_json)
for s in data:
    print(f'  {s["s_key"]}: {s["title"]} [{s["tone"]}]')

# 调用函数
plan_chapter(f"projects/{PROJECT}/data/novel_state.json", CHAPTER, subs_json)
