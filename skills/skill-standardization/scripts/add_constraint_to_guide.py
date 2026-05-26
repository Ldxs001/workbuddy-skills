#!/usr/bin/env python3
"""在 guide.md 的 TOC 之后插入文件修改约束章节"""
import os, re

guide_md = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'references', 'guide.md'))

with open(guide_md, 'r', encoding='utf-8') as f:
    content = f.read()

constraint = """
> **⚠️ 文件修改约束**：修改 `SKILL.md` 或 `references/*.md` 时，**严禁使用 Write/Edit 工具**（会损坏 UTF-8 编码）。必须使用 `scripts/` 下的 Python 脚本原子写入（`open(tmp)+os.replace()`）。修改后必须自审 0 ERROR 0 WARN。

| 文件 | 修改方式 | 脚本 |
|------|----------|------|
| `SKILL.md` frontmatter | Python 原子写入 | `scripts/update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 正则替换 | `scripts/fix_progressive_loading.py` |
| `references/*.md` | `scripts/safe_io.py` 的 `safe_write()` | 随技能自带 |
| 变更日志 | Python 合并脚本 | 每次发版统一维护 `references/changelog.md` |
"""

# 在 TOC 之后的第一个 --- 分隔线后面插入（即 ## 模式 A 之前）
# 找到 "---" + 换行 + "## 模式 A" 的位置
pattern = r'(-\n## 模式 A)'
replacement = r'---\n' + constraint + '\n## 模式 A'

new_content = re.sub(pattern, replacement, content, count=1)

if new_content == content:
    print("WARN: 找不到插入位置，尝试其他方式")
    # 备用：在 ## 模式 A 之前插入
    new_content = re.sub(r'(\n## 模式 A)', '\n' + constraint + r'\1', content, count=1)

# 原子写入
tmp = guide_md + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(new_content)
os.replace(tmp, guide_md)
print("OK: guide.md 已加入文件修改约束章节")
