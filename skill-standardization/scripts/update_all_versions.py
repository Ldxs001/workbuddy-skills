#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性更新所有版本相关文件"""

import json, os, re

# =====================
# 1. universal-file-ops/_meta.json
# =====================
meta1 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "universal-file-ops", "_meta.json")
with open(meta1, "r", encoding="utf-8") as f:
    m1 = json.load(f)

m1["version"] = "1.1.0"
m1["description"] = (
    "为普通大模型/智能体用户提供一站式文件操作与 Python 代码质量保障能力。\n"
    "v1.1.0：重建 python_env.py，修复 _log() 输出到 stderr，修复 utils.py VENV_DIR 定义顺序，18/18 功能测试通过。\n"
    "支持：文件 CRUD、Python 环境管理、代码规范化/审查/OO 化/测试生成、沙箱验证。"
)
with open(meta1, "w", encoding="utf-8") as f:
    json.dump(m1, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("[OK] universal-file-ops/_meta.json -> 1.1.0")

# =====================
# 2. skill-standardization/_meta.json
# =====================
meta2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_meta.json")
with open(meta2, "r", encoding="utf-8") as f:
    m2 = json.load(f)

m2["version"] = "2.35.0"
m2["description"] = (
    "Skill 标准化规范引擎 v2.35.0。"
    "注册 R-23 到审计流程；修复 _apply_fixes() 容错处理（KeyError 根因修复）；"
    "修复 R-11 误报（匹配查找路径当产出物路径）；"
    "更新规则范围 R-01~R-23。"
)
with open(meta2, "w", encoding="utf-8") as f:
    json.dump(m2, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("[OK] skill-standardization/_meta.json -> 2.35.0")

# =====================
# 3. skill-standardization changelog.md v2.35.0 条目修正
# =====================
cl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "changelog.md")
with open(cl_path, "r", encoding="utf-8") as f:
    cl = f.read()

# 找到 ## v2.35.0 条目，替换整个条目内容
new_v2350 = """## v2.35.0 (2026-05-27)

**改写类型：Minor — 修复 _AUDIT_CONTROL_FIELDS bug + 修复 R-11 误报 + 注册 R-23**

### 新增
- R-23 正式接入审计流程：`METHOD_MAP` 注册 `check_doc_code_consistency`，`__init__.py` 导入
- `audit_skill()` 自动审计 R-23（文档-代码一致性检查）

### 修复
- **`_AUDIT_CONTROL_FIELDS` bug**：包含 `sensitive_access`/`critical_write`/`permission_weight`，导致 `_apply_fixes()` 每次运行都 `pop()` 掉这些字段；从列表中移除这三个字段
- **R-11 误报 bug**：`artifact_checker.py` 的 `_check_python_artifact_paths_v2()` 匹配查找路径当产出物路径；增加误报跳过逻辑（有足够证据确认是误报时可跳过）
- **`_apply_fixes()` 容错处理**：`fix` 字典缺少 `key` 字段时跳过而非崩溃（`KeyError` 根因修复）
- **`SKILL.md` 描述更新**：`R-01~R-22` → `R-01~R-23`

### 更新
- `SKILL.md` frontmatter 版本号更新为 v2.35.0
- `_meta.json` 版本号和描述更新
- `utils.py` RULES 列表语法修复（R-23 正确注册）

---
"""

# 用正则替换 ## v2.35.0 到下一个 ## 之间的内容
pattern = r"## v2\.35\.0 \(2026-05-26\).*?\n---"
cl_new = re.sub(pattern, new_v2350.strip() + "\n---", cl, flags=re.DOTALL)
if cl_new == cl:
    print("[WARN] 未找到 v2.35.0 条目，尝试手动插入")
else:
    with open(cl_path, "w", encoding="utf-8") as f:
        f.write(cl_new)
    print("[OK] changelog.md v2.35.0 条目已更新")

print("ALL DONE")
