#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 references/changelog.md 的 --- 之后、## v2.34.9 之前插入 v2.34.10 条目。"""
import os

entry = """---
## v2.34.10 (2026-05-26)

**改写类型：Patch — 修复 frontmatter 字段残留 bug（5字段 → 11字段完整写入）**

### 根因分析
- **根因1**：Python -c 脚本字段列表括号语法错误（`(` 和 `)` 用了中文全角括号），导致脚本执行失败，文件内容未变
- **根因2**：`update_skill_frontmatter.py` 的 `parse_frontmatter()` 按行解析，若 SKILL.md 只有5个字段，重建后仍为5字段
- **根因3**：`git-sync.py` 第477/491行 push 前先 `_pull_with_cred_url()` → 远程旧版本（5字段）覆盖本地新版本（11字段）→ 反复出现"5字段残留"

### 修复
- 改用 Python 脚本直接重建 frontmatter（11字段完整写入，不经过 `parse_frontmatter()`）
- 移除 `_KNOWN_ROOT_FILES` 中的 `"CHANGELOG.md"`（白名单 bug）
- 移除 `git-sync.py` push 前的 `_pull_with_cred_url()` 调用，改为 push 失败时再 pull --rebase 重试
- 删除根目录错误 `CHANGELOG.md`（正确位置为 `references/changelog.md`）

### 新增
- （无）

### 更新
- `SKILL.md` frontmatter 值更新为 v2.34.10（sensitive_access: false / permission_weight: LOW）
- `_meta.json` description 更新

### 删除
- 根目录 `CHANGELOG.md`（错误位置）
- `scripts/update_skill_frontmatter.py`（功能已由直接重建替代，不再使用）

---
"""

fpath = os.path.join(os.path.dirname(__file__), "references", "changelog.md")
with open(fpath, "r", encoding="utf-8") as f:
    content = f.read()

# 找到第一个 --- 之后、第一个 ## 之前插入
idx = content.find("---")
if idx == -1:
    print("[X] 找不到 ---")
    raise SystemExit(1)

# 在第一个 --- 之后插入
new_content = content[:idx + 3] + "\n" + entry + content[idx + 3:]

tmp = fpath + ".tmp"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(new_content)
os.replace(tmp, fpath)
print("[OK] CHANGELOG.md 已插入 v2.34.10 条目")
