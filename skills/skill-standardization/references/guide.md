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

1. **更新 SKILL.md**：将 TODO 占位符替换为实际内容
2. **补充脚本**：在 `scripts/` 中添加实际功能代码
3. **补充文档**：按需在 `references/` 中创建渐进式 MD
4. **运行 update**：`python scripts/skill_builder.py update <skill-dir>` 验证合规性

### 示例：从头创建一个完整 skill

```bash
# 1. 创建骨架
python scripts/skill_builder.py create color-toolkit --desc "颜色工具集" --tags color,design,ui

# 2. 进入目录更新
cd color-toolkit
# 更新 SKILL.md 填写触发场景、核心能力等章节

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
| author | string | ✅ | `[username-redacted]` |
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

dry-run 输出完整的迁移计划但不做任何更新：

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

### R-18~R-20 审查规则（v2.17.0 新增）

#### R-18: 反模式具体性（WARN）

检查正文是否包含 `## 反模式` / `## 常见错误` 章节，且每条反模式含具体描述（≥20字）或代码示例。

| 检查项 | 通过条件 | 失败建议 |
|--------|----------|----------|
| 章节存在 | 正文含 `## 反模式` 或 `## 常见错误` | 添加章节，列出 2-3 个具体错误示例 |
| 条目数量 | 至少 2 条具体反模式 | 补充更多反模式示例 |
| 描述具体性 | 每条 ≥20 字，含错误现象和正确做法 | 细化描述，避免模糊表述 |

**示例（通过）：**
```markdown
## 反模式

- **在 SKILL.md 正文中写大量详细教程** — 正确做法：教程类内容拆分到 `references/guide.md`，主文件只留摘要 + 引用。详细教程超过50行时必须拆分，避免主文件超过200行限制。
- **触发词过于宽泛导致误触发** — 正确做法：触发词须含具体动作或对象（如"生成峰图"而非"画图"），并加否定条件缩小范围。

→ 更多反模式详见 `references/antipatterns.md`
```

#### R-19: FAQ 有意义性（WARN）

检查正文是否包含 `## FAQ` / `## 常见问题` 章节，且 Q&A 对有意义（Q≥10字，A≥15字）。

| 检查项 | 通过条件 | 失败建议 |
|--------|----------|----------|
| 章节存在 | 正文含 `## FAQ` 或 `## 常见问题` | 添加章节，列出 3-5 个真实用户问题 |
| Q/A 格式 | 含 Q:/A: 或 ### 子标题分隔 | 用 Q: / A: 或 ### 问题标题格式组织 FAQ |
| 问题有意义性 | 问题 ≥10 字，且非 trivial（如"如何工作"） | 改进问题，使其具体、有实质内容 |
| 答案有实质 | 答案 ≥15 字，且非万能回答（如"请参考文档"） | 改进答案，提供具体解决步骤或说明 |

**示例（通过）：**
```markdown
## FAQ

Q: 什么时候用 create，什么时候用 update？
A: 目标 skill 尚未存在或需要完全重建时用 create；已存在但需增量检查/修复时用 update。不确定时先跑 update 看报告再决定。

→ 更多常见问题详见 `references/faq.md`
```

#### R-20: 写作规范（术语一致/无模糊表述/中英文混排）（WARN）

检查正文写作规范：术语一致性、禁止模糊表述、中英文混排空格。

| 检查项 | 通过条件 | 失败建议 |
|--------|----------|----------|
| 术语一致性 | 同一概念不混用多种表述（如 `创建/创建`、`更新/更新/更新`） | 统一为首选术语（`创建`、`更新`、`删除`、`配置`） |
| 禁止模糊表述 | 不含 `可能`、`应该`、`大概`、`差不多` 等 | 改用确定性描述，或明确标注「建议」 |
| 中英文混排空格 | 中文与英文/数字之间应有空格（例外：版本号、类名） | 在中文与英文/数字之间加空格 |

**示例（通过）：**
```markdown
## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | **三种执行模式** | create / update / refactor |
| 2 | **17 条审查规则** | R-01~R-17（含安全规则） |
```

（避免 `可能 `~`、`应该 `~` 等模糊表述；中英文之间加空格，如 `Python 脚本` 而非 `Python脚本`。）

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

---

## 7. 安全增强功能（v2.13.0）

> 本 skill 在创建/更新/改造其他 skill 时，会自动进行权限检查和授权管理。

### 权限检查流程

`skill-standardization` 在 `update` 模式下会自动调用 `permission_checker.py` 扫描目标 skill 的脚本，计算权限权重，生成风险报告。

```
skill_builder.py update <skill-dir>
  ↓
调用 permission_checker.py 扫描脚本
  ↓
计算权限权重（敏感信息 40% + 关键位置 30% + 网络 20% + 删除 10%）
  ↓
生成 JSON 报告 → 打印到终端
  ↓
如发现中高风险操作，提示用户审批
```

### 授权管理流程

当目标 skill 包含高权限操作（文件删除、网络请求、subprocess 调用）时，`authorization_manager.py` 会介入：

- **统一审批**：累积多个风险操作，一次性列出，由用户统一审批
- **即时审批**：高风险操作执行前，立即请求用户授权

### R-13~R-17 规则说明

| 规则 | 严重度 | 检查内容 |
|------|---------|----------|
| R-13 | ERROR | 敏感信息访问声明（读取 memory/credentials/token 等须声明 `sensitive_access: true`） |
| R-14 | ERROR | 关键位置写入声明（写入 skills/.workbuddy/系统目录须声明 `critical_write: true`） |
| R-15 | ERROR | 高权限操作风险说明（脚本含高/严重风险操作时，`references/permissions.md` 须包含对应操作的风险说明、权限作用、执行步骤） |
| R-16 | WARN | 权限权重说明（建议在 SKILL.md 或 references/ 中说明各操作的权限权重） |
| R-17 | ERROR | 渐进加载引用（SKILL.md > 200 行时必须拆分到 references/ 并通过引用链接） |


---

## 注意事项

1. **refactor 前务必先 `--dry-run`**
2. **备份是 refactor 默认行为**：不要用 `--no-backup` 除非明确知道风险
3. **本文件控制在 200 行以内**：超过部分已拆分到 `references/`
4. **审查是纯警告模式**：不会阻止 git-sync 同步
5. **版本号三方一致**：更新后按上表同步
