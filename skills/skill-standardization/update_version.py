#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新 skill-standardization 版本号和 changelog"""

import os, re

SKILL_MD = os.path.join(os.path.dirname(__file__), "SKILL.md")
CHANGELOG = os.path.join(os.path.dirname(__file__), "references", "changelog.md")

# 1. 更新 SKILL.md 版本号 2.34.11 -> 2.35.0
with open(SKILL_MD, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("version: 2.34.11", "version: 2.35.0")
content = re.sub(
    r"skill-standardization 技能，提供.*?标准化审查",
    "skill-standardization 技能，提供 R-01~R-23 标准化审查",
    content
)
# 更新 description
content = re.sub(
    r"description: .*?\n",
    "description: Skill 标准化规范引擎 v2.35.0。注册 R-23 到审计流程；修复 _apply_fixes() 容错处理；修复 R-11 误报（匹配查找路径当产出物路径）；更新规则范围 R-01~R-23\n",
    content
)

with open(SKILL_MD, "w", encoding="utf-8") as f:
    f.write(content)
print("[OK] SKILL.md 版本号已更新为 2.35.0")

# 2. 更新 changelog.md（在 ## v2.35.0 条目后追加本次修复内容）
with open(CHANGELOG, "r", encoding="utf-8") as f:
    cl = f.read()

# 找到 ## v2.35.0 条目，在其内容后追加新修复
new_entry = """## v2.35.0 (2026-05-27)

**改写类型：Minor — 修复 _AUDIT_CONTROL_FIELDS bug + 修复 R-11 误报 + 更新版本号到 2.35.0**

### 修复
- **`_AUDIT_CONTROL_FIELDS` bug**：包含 `sensitive_access`/`critical_write`/`permission_weight`，导致 `_apply_fixes()` 每次运行都 `pop()` 掉这些字段；从列表中移除这三个字段
- **R-11 误报 bug**：`artifact_checker.py` 的 `_check_python_artifact_paths_v2()` 匹配查找路径当产出物路径；增加误报跳过逻辑（有足够证据确认是误报时可跳过）
- **` utils.py` RULES 列表**：`R-01 ~ R-23` 正确注册，不再截断

### 新增
- （无）

### 更新
- `SKILL.md` frontmatter 版本号更新为 v2.35.0
- `_meta.json` 版本号和描述更新
- `description` 更新为包含 R-11 误报修复说明

---

"""

if "## v2.35.0" not in cl:
    # 在文件开头（标题之后）插入新条目
    lines = cl.split("\n")
    # 找到第一个 --- 之后的位置
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.strip() == "---":
            insert_pos = i + 1
            break
    lines.insert(insert_pos, new_entry.strip())
    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[OK] changelog.md 已追加 v2.35.0 条目")
else:
    print("[SKIP] changelog.md 已有 v2.35.0 条目")

print("DONE")
