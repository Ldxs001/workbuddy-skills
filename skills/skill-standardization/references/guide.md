# 使用指南 — skill-standardization v2

本指南提供 skill-standardization v2 三种执行模式的详细操作教程。

---

## 目录

1. [模式 A：create — 创建新 Skill](#模式-acreate--创建新-skill)
2. [模式 B：update — 更新已有 Skill](#模式-bupdate--更新已有-skill)
3. [模式 C：refactor — 改造非标 Skill](#模式-crefactor--改造非标-skill)
4. [审查模式 — 独立审计](#审查模式--独立审计)
5. [规范加载 — 渐进式 JSON 查询](#规范加载--渐进式-json-查询)
6. [与 git-sync 集成工作流](#与-git-sync-集成工作流)

---

## 模式 A：create — 创建新 Skill

### 基础用法

```bash
python scripts/skill_builder.py create <skill-name> --desc "技能描述"
```

### 完整参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `name` (位置参数) | ✅ | 技能名称（目录名） | `my-skill` |
| `--desc` | ❌ | 一句话描述 | `"文件搜索工具"` |
| `--dir` | ❌ | 输出目录（默认当前目录） | `~/skills/` |
| `--tags` | ❌ | 逗号分隔标签 | `search,tool,files` |

### create 产出物结构

```
<skill-name>/
├── SKILL.md          # 主文件（含 TODO 占位符模板）
├── _meta.json        # 元数据（五字段）
├── references/.gitkeep     # 渐进式MD目录占位
└── scripts/.gitkeep  # 脚本目录占位
```

### create 后的后续步骤

1. **编辑 SKILL.md**：将 TODO 占位符替换为实际内容
2. **补充脚本**：在 `scripts/` 中添加实际功能代码
3. **补充文档**：按需在 `references/` 中创建渐进式 MD
4. **运行 update**：`python scripts/skill_builder.py update <skill-dir>` 验证合规性

### 示例：从头创建一个完整 skill

```bash
# 1. 创建骨架
python scripts/skill_builder.py create color-toolkit --desc "颜色工具集" --tags color,design,ui

# 2. 进入目录编辑
cd color-toolkit
# 编辑 SKILL.md 填写触发场景、核心能力等章节

# 3. 添加脚本
# 在 scripts/ 下放入实际 .py 文件

# 4. 验证
python ../skill-standardization/scripts/skill_builder.py update .
```

---

## 模式 B：update — 更新已有 Skill

### 基础用法（仅检查）

```bash
python scripts/skill_builder.py update <skill-dir>
```

### 自动修复模式

```bash
python scripts/skill_builder.py update <skill-dir> --fix --backup
```

### update 检查项详解

#### B-01: _meta.json 完整性

检查 `_meta.json` 是否存在且包含全部五个必填字段：

| 字段 | 类型 | 必填 | 默认值 |
|------|------|------|--------|
| name | string | ✅ | 取目录名 |
| version | string (SemVer) | ✅ | `0.1.0` |
| description | string | ✅ | 从 SKILL.md 提取或空 |
| author | string | ✅ | `wUwproject` |
| tags | string[] | ✅ | `[]` |

**--fix 行为**：自动补充缺失字段，使用上述默认值。

#### B-02: SKILL.md Frontmatter 存在性

检查文件是否以 `---` 开头并包含闭合 `---`。

**注意：此项无法自动修复**（需手动创建 frontmatter），仅输出警告。

#### B-03: 必填章节完整性

检查以下章节是否存在于正文中（支持同义词匹配）：
- 触发条件 / 触发场景 / 适用场景
- 核心功能 / 核心能力 / 概述 / Overview
- 快速开始 / Quick Start

**--fix 行为**：无法自动修复，输出具体缺失项和建议模板。

#### B-04: 文件大小合理性

检查 SKILL.md 行数是否超过 200 行。

建议：超过时考虑拆分到 `references/`。

#### B-05: 根目录规范性

检查根目录是否存在散落文件（SKILL.md 和 _meta.json 之外的文件）。

建议：用 refactor 模式自动迁移。

### update 输出示例

```
=== skill-standardization update report ===
Skill: my-skill
Path: ./my-skill

[✅] _meta.json: 存在且字段完整
[✅] SKILL.md frontmatter: 正常
[⚠️] SKILL.md 章节: 缺少"快速开始"(recommended)
[✅] 文件大小: 156 行 (< 200)
[⚠️] 根目录规范: 发现散落文件 tool.py, README.md

Summary: 2 passed, 0 errors, 2 warnings
Suggestion: 运行 refactor 清理根目录散落文件
```

---

## 模式 C：refactor — 改造非标 Skill

> ⚠️ refactor 会移动文件！务必先 `--dry-run`！

### dry-run（推荐首选）

```bash
python scripts/skill_builder.py refactor <skill-dir> --dry-run
```

dry-run 输出完整的迁移计划但不做任何修改：

```
=== refactor DRY-RUN plan ===
Source: ./old-skill
Backup: ./old-skill_bak_refactor_20260522_190000

Migration plan (4 files):
  M-01 tool.py        → scripts/tool.py       (12KB)
  M-02 NOTES.md       → references/NOTES.md         (3KB)
  M-03 helper.sh      → scripts/helper.sh      (1KB)
  M-02 README.md      → references/README.md         (2KB)

Excluded:
  __pycache__/        (M-05: always excluded)

Total size: 18KB → verification will check ±1% tolerance
```

### 实际执行

```bash
python scripts/skill_builder.py refactor <skill-dir>
```

执行流程：
1. 自动创建备份（带时间戳）
2. 按迁移规则 M-01~M-06 移动文件
3. 验证总字节一致性（±1% 容差）
4. 输出迁移映射表

### 跳过备份（不推荐）

```bash
python scripts/skill_builder.py refactor <skill-dir> --no-backup
```

### 回滚方法

```bash
# 删除当前目录，用备份恢复
rm -rf <skill-dir>
mv <skill-dir>_bak_refactor_YYYYMMDD_HHMMSS <skill-dir>
```

---

## 审查模式 — 独立审计

审查由 `skill_audit.py` 提供（与 git-sync 共享），独立于 skill_builder：

```bash
# 基本审查
python scripts/skill_audit.py audit <skill-dir>

# JSON 输出（供程序解析）
python scripts/skill_audit.py audit <skill-dir> --json

# 指定 manifest 版本进行 R-10 对比
python scripts/skill_audit.py audit <skill-dir> --manifest-version 2.0.0
```

### 审查结果判定

| 结果 | 含义 | git-sync 行为 |
|------|------|---------------|
| **PASS** | 全部通过 | 继续同步 |
| **WARN** | 仅 WARN 级失败 | 🟡 继续同步（纯警告） |
| **FAIL** | 含 ERROR 级失败 | 🟡 继续同步（纯警告，v2起不阻断） |

---

## 规范加载 — 渐进式 JSON 查询

```bash
# 列出所有可用模块
python scripts/json_loader.py list

# 加载指定模块
python scripts/json_loader.py load frontmatter    # Frontmatter 字段规范
python scripts/json_loader.py load body           # 正文章节规范
python scripts/json_loader.py load rules          # 审查规则 R-01~R-10
python scripts/json_loader.py load structure      # 目录结构规范 [v2]
python scripts/json_loader.py load progressive_md # 渐进式MD体系 [v2]

# 全量加载
python scripts/json_loader.py load all

# 显示模块原始 JSON
python scripts/json_loader.py show structure

# 查看依赖关系
python scripts/json_loader.py refs progressive_md
```

### 模块依赖图

```
frontmatter ─────┬──→ rules ──┐
body ────────────┘            │
                              ├──→ all
structure ──→ progressive_md ─┘
```

---

## 与 git-sync 集成工作流

### 同步时的自动审查流程

```
git sync 执行
  │
  ├─ 步骤 1~3: 收集/检查/提交
  │
  ├─ 步骤 3.5: 审查每个 skill ← skill_audit.py 自动调用
  │   ├─ PASS → 继续推送
  │   ├─ WARN → 🟡 打印警告，继续推送
  │   └─ FAIL(含ERROR) → 🟡 打印警告，继续推送（纯警告模式）
  │
  └─ 步骤 4~6: 推送/生成ZIP/更新manifest
```

### 版本号三方一致

skill-standardization 要求以下三处版本号保持一致：

| 位置 | 文件 | 字段 |
|------|------|------|
| 技能声明 | `SKILL.md` | frontmatter `version:` |
| 元数据 | `_meta.json` | `version` |
| 注册清单 | git-sync 的 `manifest.json` | 对应条目的 `version` |

**update/refactor 模式会自动检测和提示不一致。**
