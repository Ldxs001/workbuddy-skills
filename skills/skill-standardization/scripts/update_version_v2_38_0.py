#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原子更新 SKILL.md / _meta.json / changelog.md 到 v2.38.0"""
import re, json, os, sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD   = os.path.join(SKILL_ROOT, "SKILL.md")
META_JSON   = os.path.join(SKILL_ROOT, "_meta.json")
CHANGELOG   = os.path.join(SKILL_ROOT, "references", "changelog.md")

# 1. 更新 SKILL.md（原子写入，保护 UTF-8 中文）
with open(SKILL_MD, "r", encoding="utf-8") as f:
    content = f.read()

old = content
# frontmatter: version
content = re.sub(r'^(version\s*:\s*).*$', r'\g<1>2.38.0', content, flags=re.MULTILINE)
# frontmatter: description
content = re.sub(
    r'^(description\s*:\s*).*$',
    r'\g<1>Skill 标准化规范引擎 v2.38.0。审计输出含 filepath:line#；fix.py 统一修复工具；git-sync 后根目录 .py 清理。',
    content, flags=re.MULTILINE
)
# 标题行
content = re.sub(r'^# skill-standardization v[\d.]+', '# skill-standardization v2.38.0', content, flags=re.MULTILINE)

if content == old:
    print("[WARN] SKILL.md 内容未变化，请检查正则是否匹配", file=sys.stderr)
else:
    tmp = SKILL_MD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, SKILL_MD)
    print(f"[OK] SKILL.md -> v2.38.0 ({SKILL_MD})")

# 2. 更新 _meta.json
with open(META_JSON, "r", encoding="utf-8") as f:
    meta = json.load(f)
meta["version"] = "2.38.0"
meta["description"] = "Skill 标准化规范引擎 v2.38.0。审计输出含 filepath:line#；fix.py 统一修复工具；git-sync 后根目录 .py 清理。"
with open(META_JSON, "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"[OK] _meta.json -> v2.38.0")

# 3. 更新 changelog.md（在 ## 最新版本 后面插入新条目）
with open(CHANGELOG, "r", encoding="utf-8") as f:
    cl = f.read()

new_entry = (
    "## v2.38.0（2026-05-27）\n"
    "- 修复：git-sync 打包后根目录残留 .py 文件（违反 R-11），迁移至 scripts/ 并修正路径计算\n"
    "- 修复：update_version.py / update_all_versions.py 路径计算错误（SKILL_ROOT 计算少一级）\n"
    "- 优化：insert_v2_34_10.py 过期脚本清理\n"
    "- 修复：fix.py 移除未使用的 write_frontmatter import\n"
    "- 修复：cmd_fix() --key 参数 nargs=? 导致字符串迭代 bug，改为 nargs=*\n\n"
)
# 在 ## 最新版本 后面插入
cl_new, n = re.subn(
    r'(## 最新版本\n)',
    r'\g<1>' + new_entry,
    cl,
    count=1
)
if n == 0:
    # 找不到标记，直接插到文件开头
    cl_new = new_entry + cl
    print("[WARN] 未找到 '## 最新版本'，已追加到文件开头")
else:
    print("[OK] changelog.md 插入 v2.38.0 条目")

tmp = CHANGELOG + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(cl_new)
os.replace(tmp, CHANGELOG)

print("[DONE] 所有版本号已更新到 v2.38.0")
