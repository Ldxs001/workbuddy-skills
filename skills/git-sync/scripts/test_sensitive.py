#!/usr/bin/env python3
"""测试 sensitive_scan.py 完整流程"""
import json, os, sys, shutil

sys.path.insert(0, "C:/Users/sm001/.workbuddy/skills/git-sync/scripts")
from sensitive_scan import scan_skill, sanitize_content, build_replacements

# 1. 扫描
print("[测试1] 扫描敏感信息...")
results = scan_skill("/tmp/git-sync-test", config=None)
print(f"  → 发现 {len(results)} 个文件有敏感信息")
for e in results:
    print(f"    · {e['file']}（{len(e['findings'])} 项）")
    for f in e["findings"][:3]:
        print(f"      - {f['label']}：「{f['match'][:30]}」")

# 2. 构建替换表
print("\n[测试2] 构建替换表并脱敏...")
for entry in results:
    replacements = build_replacements(entry["findings"])
    fpath = os.path.join("/tmp/git-sync-test", entry["file"])
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        new_content = sanitize_content(content, replacements)
        # 验证 Python 语法
        if fpath.endswith(".py"):
            try:
                compile(new_content, fpath, "exec")
                print(f"  ✅ {entry['file']} 脱敏后语法正常")
            except SyntaxError as ex:
                print(f"  ❌ {entry['file']} 语法错误: {ex}")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  ✅ {entry['file']} 已脱敏")

# 3. 显示脱敏后内容
print("\n[测试3] 脱敏后内容预览...")
for entry in results:
    fpath = os.path.join("/tmp/git-sync-test", entry["file"])
    if fpath.endswith(".py"):
        with open(fpath, "r", encoding="utf-8") as f:
            print(f"  --- {entry['file']} ---")
            print("  " + f.read()[:300].replace("\n", "\n  "))

print("\n✅ 全部测试完成")
