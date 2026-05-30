# 示例集合 — skill-standardization v2

本文件包含 skill-standardization v2 各种使用场景的完整示例。

---

## 目录

1. [Create 模式示例](#create-模式示例)
2. [Update 模式示例](#update-模式示例)
3. [Refactor 模式示例](#refactor-模式示例)
4. [审查报告示例](#审查报告示例)
5. [规范加载输出示例](#规范加载输出示例)
6. [SKILL.md 完整模板示例](#skillmd-完整模板示例)

---

## Create 模式示例

### 示例 1：最小化创建

```bash
$ python -m scripts.skill_builder create hello-world --desc "问候技能"

[CREATE] Skill: hello-world
[CREATE] Directory: ./hello-world
[CREATE] SKILL.md   → ./hello-world/SKILL.md
[CREATE] _meta.json → ./hello-world/_meta.json
[CREATE] references/      → ./hello-world/references/.gitkeep
[CREATE] scripts/   → ./hello-world/scripts/.gitkeep

Done! Next steps:
1. Edit hello-world/SKILL.md (replace TODOs with real content)
2. Add scripts to hello-world/scripts/
3. Run update to verify: python -m scripts.skill_builder update ./hello-world
```

### 示例 2：带完整参数创建

```bash
python -m scripts.skill_builder create \
  data-processor \
  --desc "数据处理流水线" \
  --tags data,pipeline,etl \
  --dir ~/workbuddy/skills/
```

产出 `_meta.json`：
```json
{
  "name": "data-processor",
  "version": "0.1.0",
  "description": "数据处理流水线",
  "author": "[username-redacted]",
  "tags": ["data", "pipeline", "etl"]
}
```

### 示例 3：create 生成的 SKILL.md 模板

```markdown
---
name: hello-world
version: 0.1.0
author: [username-redacted]
license: MIT
description: >
  问候技能
tags: []
---

# hello-world — 问候技能

一句话概述技能的核心价值。（TODO: 替换为实际描述）

## 触发场景

当用户提到以下意图时触发本技能：
- TODO: 触发条件 1
- TODO: 触发条件 2

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | TODO: 能力1 | TODO: 描述 |
| 2 | TODO: 能力2 | TODO: 描述 |

## 快速开始

```bash
# TODO: 最简用法示例（1-3 行即可上手）
```

→ 详见 `references/guide.md` 完整教程
```

---

## Update 模式示例

### 示例 4：检查一个合规的 skill

```bash
$ python -m scripts.skill_builder update ./color-toolkit

=== UPDATE REPORT ===
Skill: color-toolkit
Path: ./color-toolkit

[B-01] _meta.json:     ✅ EXISTS, all 5 fields present
[B-02] Frontmatter:     ✅ VALID YAML block found
[B-03] Required sections:
       - Trigger section: ✅ found "触发条件"
       - Core section:    ✅ found "核心能力"
       - Quick start:     ✅ found "快速开始"
[B-04] File size:        ✅ 89 lines (< 200 limit)
[B-05] Root directory:   ✅ clean (only SKILL.md + _meta.json)

Summary: 5/5 passed, 0 errors, 0 warnings
Verdict: ✅ PASS — skill is well-standardized
```

### 示例 5：检查有问题的 skill（不使用 --fix）

```bash
$ python -m scripts.skill_builder update ./old-skill

=== UPDATE REPORT ===
Skill: old-skill
Path: ./old-skill

[B-01] _meta.json:     ❌ MISSING (file not found)
[B-02] Frontmatter:     ✅ VALID YAML block found
[B-03] Required sections:
       - Trigger section: ❌ MISSING
       - Core section:    ✅ found "功能列表"
       - Quick start:     ❌ MISSING
[B-04] File size:        ⚠️ 312 lines (> 200 limit, consider splitting)
[B-05] Root directory:   ⚠️ stray files: tool.py, README.md, notes.txt

Summary: 2/5 passed, 0 errors, 3 warnings
Suggestion: Run with --fix to auto-fix B-01; use refactor for B-05
```

### 示例 6：--fix 自动修复

```bash
$ python -m scripts.skill_builder update ./old-skill --fix --backup

=== UPDATE REPORT ===
Skill: old-skill
Path: ./old-skill

[B-01] _meta.json:     🔧 FIXED → created ./old-skill/_meta.json (backup: _meta.json.bak)
[B-02] Frontmatter:     ✅ VALID
[B-03] Required sections:
       - Trigger section: ❌ MANUAL FIX NEEDED
         Suggested heading: ## 触发场景
       - Core section:    ✅ found "功能列表"
       - Quick start:     ❌ MANUAL FIX NEEDED
         Suggested heading: ## 快速开始
[B-04] File size:        ⚠️ 312 lines (> 200, suggest references/ split)
[B-05] Root directory:   ⚠️ stray files (refactor recommended)

Backup saved: ./old-skill_bak_update_20260522_190000/
Summary: Auto-fixed 1 item, 3 manual items remaining
```

---

## Refactor 模式示例

### 示例 7：dry-run 查看迁移计划

```bash
$ python -m scripts.skill_builder refactor ./legacy-tool --dry-run

=== REFACTOR DRY-RUN ===
Target: ./legacy-tool
Mode: DRY-RUN (no changes will be made)

Scanning files...
Found 8 files (total: 45,230 bytes)

Migration plan:
┌──────┬───────────────────┬────────────────────────┬────────┐
│ Rule │ Source             │ Destination            │ Size   │
├──────┼───────────────────┼────────────────────────┼────────┤
│ M-01 │ tool.py            │ scripts/tool.py        │ 18.2KB │
│ M-01 │ utils.py           │ scripts/utils.py       │ 4.1KB  │
│ M-02 │ README.md          │ references/README.md         │ 2.3KB  │
│ M-02 │ NOTES.md           │ references/NOTES.md          │ 1.8KB  │
│ M-03 │ requirements.txt   │scripts/requirements.txt│ 0.1KB  │
└──────┴───────────────────┴────────────────────────┴────────┘

Excluded (M-05): __pycache__/ (3 files)

Root after migration: SKILL.md + _meta.json only ✅
Total size verification: 45,230 bytes (±1% = 44,778~45,683 bytes)

⚠️ This is a dry-run. No files were changed.
To execute: remove --dry-run flag
```

### 示例 8：实际执行 refactor

```bash
$ python -m scripts.skill_builder refactor ./legacy-tool

=== REFACTOR EXECUTE ===
Target: ./legacy-tool
Backup: ./legacy-tool_bak_refactor_20260522_191000/

[1/5] Creating backup... ✅
[2/5] Scanning files... ✅ 8 files found
[3/5] Applying migrations:
      M-01 tool.py      → scripts/tool.py      ✅
      M-01 utils.py     → scripts/utils.py     ✅
      M-02 README.md    → references/README.md       ✅
      M-02 NOTES.md     → references/NOTES.md        ✅
      M-03 requirements.txt → scripts/requirements.txt ✅
[4/5] Verifying integrity... ✅ 45,230 bytes match
[5/5] Writing migration log... ✅

Refactor complete! Migration log: .refactor_log.json
Rollback: mv ./legacy-tool_bak_refactor_* ./legacy-tool
```

---

## 审查报告示例

### 示例 9：完整通过

```bash
$ python -m scripts.skill_audit audit ./my-skill --json

{
  "skill_dir": "./my-skill",
  "verdict": "PASS",
  "summary": {"total": 10, "passed": 10, "errors": 0, "warns": 0},
  "rules": [
    {"id": "R-01", "status": "PASS", "msg": "Frontmatter exists"},
    {"id": "R-02", "status": "PASS", "msg": "name field present"},
    ...
  ]
}
```

### 示例 10：含 WARN 的结果（纯警告模式）

```bash
$ python -m scripts.skill_audit audit ./another-skill

=== AUDIT REPORT ===
Skill: another-skill

[R-01] Frontmatter 存在性 ............ ✅ PASS
[R-02] name 字段 ..................... ✅ PASS
[R-03] version SemVer ................ ✅ PASS
[R-04] description 字段 .............. ✅ PASS
[R-05] name 与目录名一致 .............. ⚠️ WARN  (frontmatter name="MySkill", dir="another-skill")
[R-06] 正文含一级标题 ................ ✅ PASS
[R-07] 触发条件章节 .................. ⚠️ WARN  (not found)
[R-08] 核心能力章节 .................. ✅ PASS
[R-09] 工作流程章节 .................. ⚠️ WARN  (not found)
[R-10] version 一致性 ................. ✅ PASS

Verdict: ⚠️ WARN (6/10 PASS, 0 ERROR, 4 WARN)
Exit code: 0 (pure warning mode — will NOT block subsequent steps)
```

---

## 规范加载输出示例

### 示例 11：加载 structure 模块

```bash
$ python scripts/json_loader.py load structure

═══ SKILL.md 标准化规范 v2.0.0 ═══

📦 Module: structure
📄 Source: spec/structure.json
📐 Dependencies: (none)

Root mandatory files (must exist):
  • SKILL.md   — 主文件（≤200行，含核心章节）
  • _meta.json — 元数据（5字段）

Subdirectories (create as needed):
  • references/     — 渐进式 MD 辅助文档
  • scripts/  — 可执行脚本和工具 + spec/
  • assets/   — 静态资源（可选）
  • tests/    — 测试（可选）

Layout levels:
  minimal  — SKILL.md + _meta.json
  standard — + scripts/ + references/
  full     — + assets/ + tests/

Migration rules: M-01 ~ M-06 defined
```

---

## SKILL.md 完整模板示例

### 示例 12：standard 级别的标准 SKILL.md

这是一个完全符合 v2 规范的标准 SKILL.md 示例：

```markdown
---
name: example-skill
version: 1.0.0
author: [username-redacted]
license: MIT
description: >
  一个示例技能，演示标准的 SKILL.md 写法。
tags: ["example", "demo", "template"]
---

# example-skill — 示例技能

基于 XX 框架的 YY 功能实现。

## 触发场景

当用户提到以下意图时触发：
- "需要 XX 功能"
- "帮我做 YY"
- "XX 怎么用"

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | 核心功能 A | 做什么 |
| 2 | 核心功能 B | 做什么 |
| 3 | 辅助功能 C | 做什么 |

## 快速开始

```bash
python scripts/main.py --help
```

## 主要流程

### 流程 A：常用操作

1. 准备输入数据
2. 执行处理
3. 获取结果

→ 详见 `references/guide.md` 完整教程
→ [API 参考](references/reference.md) 查看全部选项

## 注意事项

1. 约束一
2. 约束二
3. 约束三
```
