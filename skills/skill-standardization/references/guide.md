# 使用指南 — skill-standardization v2

本指南提供 skill-standardization v2 三种执行模式的详细操作教程。

---

## 目录

1. [模式 A：create — 创建新 Skill](#模式-acreate--创建新-skill)
2. [模式 B：update — 更新已有 Skill](#模式-bupdate--更新已有-skill)
3. [模式 C：refactor — 改造非标 Skill](#模式-crefactor--改造非标-skill)
4. [审查模式 — 独立审计](#审查模式--独立审计)
5. [规范加载 — 渐进式 JSON 查询](#规范加载--渐进式-json-查询)

---


> **⚠️ 文件更新约束**：更新 `SKILL.md` 或 `references/*.md` 时，**严禁使用 Write/Edit 工具**（会损坏 UTF-8 编码）。必须使用 `scripts/` 下的 Python 脚本原子写入（`open(tmp)+os.replace()`）。更新后必须自审 0 ERROR 0 WARN。

| 文件 | 更新方式 | 脚本 |
|------|----------|------|
| `SKILL.md` frontmatter | Python 原子写入 | `scripts/update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 正则替换 | `scripts/safe_io.py` 的 `safe_write()` |
| `references/*.md` | `scripts/safe_io.py` 的 `safe_write()` | 随技能自带 |
| 更新日志 | Python 合并脚本 | 每次发版统一维护 `references/changelog.md` |

## 模式 A：create — 创建新 Skill

### 基础用法

```bash
python -m scripts.skill_builder create <skill-name> --desc "技能描述"
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
├── references/.gitkeep     # 渐进式 MD 目录占位
└── scripts/.gitkeep  # 脚本目录占位
```

### create 后的后续步骤

1. **更新 SKILL.md**：将 TODO 占位符替换为实际内容
2. **补充脚本**：在 `scripts/` 中添加实际功能代码
3. **补充文档**：按需在 `references/` 中创建渐进式 MD
4. **运行 update**：`python -m scripts.skill_builder update <skill-dir>` 验证合规性

### 示例：从头创建一个完整 skill

```bash
# 1. 创建骨架
python -m scripts.skill_builder create color-toolkit --desc "颜色工具集" --tags color,design,ui

# 2. 进入目录更新
cd color-toolkit
# 更新 SKILL.md 填写触发场景、核心能力等章节

# 3. 添加脚本
# 在 scripts/ 下放入实际 .py 文件

# 4. 验证
python ../skill-standardization/scripts/-m scripts.skill_builder update .
```

---

## 模式 B：update — 更新已有 Skill

### 基础用法（仅检查）

```bash
python -m scripts.skill_builder update <skill-dir>
```

### 工作流程（含临时/备份管理 + 强制 inspect 前置扫描）

1. **操作前整体备份**（默认执行）
   ```bash
   # 备份：cp -r <skill-dir> <skill-dir>_bak_update_$(date +%Y%m%d_%H%M%S)
   ```
2. **★ 强制 inspect 结构扫描**（v2.44.0 新增，备份后自动执行）
   工具自动输出技能蓝皮书（元信息、目录树、章节、函数清单、安全数据），
   确保 AI/开发者了解技能全貌后再动手，避免遗漏文件或功能。
   也可独立运行：
   ```bash
   python -m scripts.skill_inspector <skill-dir>
   ```
3. **执行审查/修复**
   ```bash
   python -m scripts.skill_builder update <skill-dir> --fix
   ```
4. **操作中记录**：所有临时文件（`*.tmp`、`temp_*`）和备份文件记录到 `op_logger` 日志
5. **操作后清理**：审查通过 + 版本号更新 + 更新日志完毕后，执行：
   ```bash
   # 清理备份：skill_rollback 暂不支持 cleanup，手动删除旧备份即可
   ```

### 自动修复模式

```bash
python -m scripts.skill_builder update <skill-dir> --fix --backup
```

### update 检查项详解

#### B-01: _meta.json 完整性

> 完整字段定义以 `scripts/spec/structure.json` 为准，此处仅作摘要。

检查 `_meta.json` 是否存在且包含全部七个标准字段：

| 字段 | 类型 | 必填 | 默认值 |
|------|------|------|--------|
| name | string | ✅ | 取目录名 |
| version | string (SemVer) | ✅ | `0.1.0` |
| description | string | ✅ | 从 SKILL.md 提取或空 |
| author | string | ✅ | `[username-redacted]` |
| tags | string[] | ✅ | `[]` |
| data_dir | string | ❌ | 无（需要持久化数据时必填） |
| triggers | string[] | ❌ | `[]` |

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

### 工作流程（含临时/备份管理 + 强制 inspect 前置扫描）

1. **操作前整体备份**（默认执行，`--no-backup` 跳过）
   ```bash
   # 备份：cp -r <skill-dir> <skill-dir>_bak_refactor_$(date +%Y%m%d_%H%M%S)
   ```
2. **★ 强制 inspect 结构扫描**（v2.44.0 新增，备份后自动执行）
   工具自动输出技能蓝皮书，确保了解全貌后再迁移。
3. **dry-run 预览**
   ```bash
   python -m scripts.skill_builder refactor <skill-dir> --dry-run
   ```
4. **执行改造**：`-m scripts.skill_builder refactor` 自动备份 + 迁移 + 验证
5. **操作中记录**：临时文件、备份文件记录到 `op_logger` 日志
6. **操作后清理**：审查通过 + 版本号更新 + 更新日志完毕后，执行：
   ```bash
   # 清理备份：skill_rollback 暂不支持 cleanup，手动删除旧备份即可
   ```

### dry-run（推荐首选）

```bash
python -m scripts.skill_builder refactor <skill-dir> --dry-run
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
python -m scripts.skill_builder refactor <skill-dir>
```

执行流程：
1. **R-22 数据目录规范检查** — 检查安装目录是否包含应归属数据目录的文件
2. 自动创建备份（带时间戳）
3. 按迁移规则 M-01~M-06 移动文件
4. 验证总字节一致性（±1% 容差）
5. 输出迁移映射表
6. 更新 SKILL.md frontmatter（加入 `data_dir:` 声明）

### 跳过备份（不推荐）

```bash
python -m scripts.skill_builder refactor <skill-dir> --no-backup
```

### 回滚方法

```bash
# 删除当前目录，用备份恢复
rm -rf <skill-dir>
mv <skill-dir>_bak_refactor_YYYYMMDD_HHMMSS <skill-dir>
```

---


---

## 临时文件与备份管理规范

> 本技能在创建、更新、改造目标技能的过程中，对临时文件和备份文件进行全生命周期管理。

### 管理流程

```
操作前                              操作中                    操作后
  │                                   │                        │
  ▼                                   ▼                        ▼
整体备份目标技能                    记录临时/备份文件        清理临时文件
（timestamp 命名）                （op_logger 日志）      （保留最新 10 个备份）
  │                                   │                        │
  └───────────────────────────────────┴───────────────────────┘
```

### 操作前：整体备份

- 更新/改造前，对目标技能目录执行整体备份
- 备份命名格式：`skills/.standardization/<skill-name>/backup/<skill-dir>_bak_<operation>_<YYYYMMDD_HHMMSS>`
- 备份路径记录在 `op_logger` 日志的 `rollback_id` 字段

### 操作中：临时/备份文件记录

- 所有临时文件（`*.tmp`、`temp_*`、`draft_*`）的产生路径、时间记录到 `op_logger` 日志的 `temp_files` 字段
- 所有备份文件（`data/backup/*`、`_bak_*` 目录）记录到 `op_logger` 日志的 `backup_files` 字段
- 日志格式（JSON Lines）：

```json
{
  ts: 2026-05-27T08:31:47,
  operation: update,
  file: skills/.standardization/skill-standardization/,
  success: true,
  rollback_id: 20260527_083147_...,
  temp_files: [skills/.standardization/skill-standardization/data/temp/xxx.tmp],
  backup_files: [skills/.standardization/skill-standardization/data/backup/20260527_...bak],
  detail: ...
}
```

### 操作后：清理规范

| 文件类型 | 路径模式 | 保留数量/时长 | 清理时机 |
|-----------|-----------|----------------|------------|
| 临时文件 | `data/temp/*`、`*.tmp`、`draft_*` | 0（会话级） | 每次操作完成后立即清除 |
| 操作备份 | `data/backup/*` | 最近 10 个 | 每次操作完成后保留最新 10 个，其余清除 |
| 整体备份 | `<skill-dir>_bak_*<timestamp>` | 操作完成确认后 | 操作完成并确认无异常后，提示用户是否清除 |
| 日志文件 | `data/logs/ops.log` | 最近 200 条 | 超过 200 条时截断，保留最新 |

### py 工具兜底能力

`scripts/safe_io.py` 所有写操作（`safe_write`、`safe_patch_by_line`、`safe_patch_regex`、`safe_insert_after`）均内置 `backup_file()` 临时备份，返回 `rollback_id`，确保删/改动作可回滚。

`scripts/skill_rollback.py` 提供：
- `backup_file()` — 单文件备份（safe_io 内置）
- `op_logger` — 记录操作日志（含临时/备份文件追踪）

- `rollback(rollback_id)` — 单文件回滚
- `rollback_latest(N)` — 回滚最近 N 次操作

---

## 审查模式 — 独立审计

审查由 `-m scripts.skill_audit` 提供，独立于 skill_builder：

```bash
# 基本审查
python -m scripts.skill_audit audit <skill-dir>

# JSON 输出（供程序解析）
python -m scripts.skill_audit audit <skill-dir> --json

# 指定 manifest 版本进行 R-10 对比
python -m scripts.skill_audit audit <skill-dir> --manifest-version 2.0.0
```

### 审查结果判定

| 结果 | 含义 | 后续行为 |
|------|------|----------|
| **PASS** | 全部通过 | 继续后续流程 |
| **WARN** | 仅 WARN 级失败 | 🟡 继续同步（纯警告） |
| **FAIL** | 含 ERROR 级失败 | 🟡 继续同步（纯警告，v2起不阻断） |

### R-18~R-21 审查规则（v2.17.0~v2.24.0）

#### R-18: 反模式具体性（WARN）

检查正文是否包含 `## 反模式` / `## 常见错误` 章节，且每条反模式含具体描述（≥20字）或代码示例。

| 检查项 | 通过条件 | 失败建议 |
|--------|----------|----------|
| 章节存在 | 正文含 `## 反模式` 或 `## 常见错误` | 添加章节，列出 2-3 个具体错误示例 |
| 条目数量 | 至少 2 条具体反模式 | 补充更多反模式示例 |
| 描述具体性 | 每条 ≥20 字，含错误现象和正确做法 | 细化描述，避免模糊表述 |

**示例（通过）：**
```markdown

### 审计输出示例

对一个技能执行 `audit` 后的实际输出效果：

```
$ python -m scripts.skill_audit audit /path/to/skill
════════════════════════════════════════════════════
  技能标准化审计报告
════════════════════════════════════════════════════

 ┌─────────────────────────────────────────────┐
 │ 进度                                        │
 ├─────────────────────────────────────────────┤
 │ PASS(24)  WARN(4)  ERROR(1)                 │
 └─────────────────────────────────────────────┘

审查结果逐规则详情：

[R-01] frontmatter 字段完整性 ......... ✅ PASS (字段完整)
[R-06] H1 标题格式 .................. ✅ PASS
[R-07] 触发条件章节存在性 ............ ✅ PASS
[R-10] description 一致性 ........... ❌ ERROR
    → SKILL.md 的 description 与 _meta.json 不一致
    → 使用 --fix 自动同步：description 已更新
  
[R-17] 渐进加载检查 ................. ⓘ Phase 1 粗筛
    → 发现 1 个疑似非标章节（WARN，待 LLM Phase 2 确认）
[R-25] 文档写作格式 ................. 🟡 WARN(4)
    → C-11: 章节「工作流程」应在「快速开始」之后（逆序）
    → C-13: references/ 目录有 6 个 .md 文件但核心能力缺少渐进式索引表
    → C-14: 工作流程共 4 步，需 LLM Phase 2 确认是否完整

════════════════════════════════════════════════════
```

每条规则输出都包含精确行号和上下文片段，LLM 一眼可知问题所在，无需翻文件确认。

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

#### R-20: 写作规范（术语一致/无模糊表述/中英文混排/脚本调用验证）（WARN）

检查正文写作规范：术语一致性、禁止模糊表述、中英文混排空格、脚本调用验证。

| 检查项 | 通过条件 | 失败建议 |
|--------|----------|----------|
| 术语一致性 | 同一概念不混用多种表述（如 `创建/创建`、`更新/更新`、`删除/删除`、`配置/配置`） | 统一为首选术语（`创建`、`更新`、`删除`、`配置`） |
| 禁止模糊表述 | 不含 `可能`、`大概`、`差不多` 等模糊词 | 改用确定性描述，或明确标注「建议」 |
| 中英文混排空格 | 中文与英文/数字之间应有空格（例外：版本号、类名） | 在中文与英文/数字之间加空格 |
| 脚本调用验证 | `SKILL.md` 提到的脚本文件真实存在，且能正常运行 `--help` | 检查脚本路径是否正确、参数定义是否有误 |

**v2.24.4 新增：脚本调用验证**：
- 解析 `SKILL.md` 里的代码块（```bash ... ```）和行内代码（`...` ）
- 提取脚本路径（如 `python scripts/xxx.py --list`）
- 检查脚本文件是否存在
- 尝试运行 `--help` 验证脚本可调用（超时 5 秒）

**示例（通过）：**
```markdown
## 参数

| 脚本 | 参数 | 说明 |
|---|------|------|
| `scripts/chain_manager.py` | `--list`, `--create` | 调用链管理 |

> 💡 可直接 `python scripts/chain_manager.py --list` 查看所有调用链。
```

**示例（通过）：**
```markdown
## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | **三种执行模式** | create / update / refactor |
| 2 | **17 条审查规则** | R-01~R-17（含安全规则） |
```

（避免 `可能 `~` 等模糊表述；中英文之间加空格，如 `Python 脚本` 而非 Python脚本（缺空格）。）

#### R-21: 渐进式加载显式说明（WARN）

检查 `SKILL.md` 是否在显眼位置（核心能力/工作流程章节）包含**固定模板句**。

**v2.24.2 固定模板**：所有技能必须原封不动包含以下句子（可在后面接其他说明）：
```
> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。
```

**为什么用固定模板？**
- 搜索友好：直接搜固定句子，不用猜关键词
- 检查简单：判断是否以模板句开头即可
- 避免歧义：不会出现"代码块内偶然提及导致误判"的问题

| 检查项 | 通过条件 | 失败建议 |
|--------|----------|----------|
| 显眼位置 | `## 核心能力` 或 `## 工作流程` 章节存在 | 添加对应章节 |
| 固定模板句 | 章节内某行以固定模板句开头（可接其他说明） | 添加固定模板句 |

**检测逻辑（v2.24.2）**：
1. 在 `## 核心能力` 或 `## 工作流程` 章节内查找
2. 逐行检查是否以固定模板句开头（允许后面接其他内容）
3. 找到即通过，找不到则 FAIL

**示例（通过）：**
```markdown
## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 功能 | 说明 |
|---|------|------|
| 1 | **三种执行模式** | create / update / refactor |
```

**示例（通过，接其他说明）：**
```markdown
## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。用本技能创建/更新/改造的技能均遵循此规范。
```

（固定模板句必须原封不动，后面可以接其他说明。）

---

### R-12: 外部数据目录路径规范（v2.25.0）【新增】

R-12 检查 `scripts/*.py` 中定义的外部数据目录路径是否符合 `skills/.standardization/<skill-name>/data/` 规范。

**审计原理**：R-12 对源码做**静态字符串匹配**，检查 `DEFAULT_DATA_DIR = ` 赋值右侧是否出现 `skills/.standardization/<skill>/data/` 字面量。

**推荐写法（同时满足审计+运行时正确性）**：

```python
# R-12 审计锚点：变量名含 DATA，值含合规字面量，审计可匹配
DEFAULT_DATA_DIR_RAW = "skills/.standardization/<skill-name>/data/"

SKILL_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 运行时绝对路径（变量名不含 DATA/STORAGE/DB/CACHE/CONFIG，避免被审计二次匹配）
_data_dir_abs  = os.path.normpath(os.path.join(SKILL_ROOT, "..", DEFAULT_DATA_DIR_RAW))
BACKUP_DIR      = os.path.join(_data_dir_abs, "backup")
LOGS_DIR        = os.path.join(_data_dir_abs, "logs")
```

**要点**：
1. 第一行变量名必须含 `DATA|STORAGE|DB|CACHE|CONFIG` 之一才会被审计匹配
2. 值必须是 `skills/.standardization/<skill>/data/` 字面量（审计只检查赋值右侧的字符串）
3. 运行时用另一个不含上述关键词的变量（如 `_data_dir_abs`）存放绝对路径，避免被审计二次匹配
4. `backup/` 和 `logs/` 子目录基于绝对路径变量拼接

**常见错误写法（审计会失败）**：

```python
# ❌ 错误：运行时计算路径，审计匹配不到合规字面量
DEFAULT_DATA_DIR = os.path.normpath(os.path.join(...))

# ❌ 错误：注释里写合规路径，审计不认注释
# skills/.standardization/xxx/data/
DEFAULT_DATA_DIR = os.path.normpath(...)

# ❌ 错误：两次赋值，审计匹配到第二行（不合规）
DEFAULT_DATA_DIR = "skills/.standardization/xxx/data/"
DEFAULT_DATA_DIR = os.path.normpath(...)  # 审计匹配这行 → 失败
```

---


---

## 审查后自动更新（fix.py）

审计输出 WARN/ERROR 后，可直接调用 `scripts/skill_audit/fix.py` 中的修复函数自动修复，无需手写修复脚本。

### 用法

```bash
# 方式一：在 skill-standardization 目录下调用
cd "C:/Users/sm001/.workbuddy/skills/skill-standardization"
python -c "
from scripts.skill_audit.fix import apply_fix
# 修复单条规则
apply_fix('C:/Users/sm001/.workbuddy/skills/<skill-dir>', 'R-07')
# 修复多条规则
apply_fix('C:/Users/sm001/.workbuddy/skills/<skill-dir>', 'R-07', 'R-18', 'R-19')
"

# 方式二：直接调用修复函数
python -c "
import sys; sys.path.insert(0, 'scripts')
from skill_audit.fix import fix_progressive_loading, fix_antipattern_progressive, fix_faq_progressive
skill = 'C:/Users/sm001/.workbuddy/skills/<skill-dir>'
fix_progressive_loading(skill)
fix_antipattern_progressive(skill)
fix_faq_progressive(skill)
"
```

### 全部修复函数一览

| 函数名 | 对应规则 | 说明 |
|---------|---------|------|
| `fix_name(skill_dir, value)` | R-01 | 修复 name 字段 |
| `fix_description(skill_dir, value)` | R-04 | 修复 description 字段 |
| `fix_version(skill_dir, value)` | R-03 | 修复 version 字段 |
| `fix_author(skill_dir, value)` | R-02 | 修复 author 字段 |
| `fix_h1(skill_dir)` | R-06 | 删除正文一级标题 |
| `fix_section_trigger(skill_dir)` | R-07 | 添加触发条件章节 |
| `fix_section_core(skill_dir)` | R-08 | 添加核心能力章节 |
| `fix_section_workflow(skill_dir)` | R-09 | 添加工作流程章节 |
| `fix_progressive_loading(skill_dir)` | R-21 | 添加渐进式加载模板句 |
| `fix_antipattern_progressive(skill_dir)` | R-18 | 创建/更新 references/antipatterns.md |
| `fix_faq_progressive(skill_dir)` | R-19 | 创建/更新 references/faq.md |
| `fix_writing_standards(skill_dir)` | R-20 | 统一术语（配置/更新/删除） |
| `fix_data_dir_compliance(skill_dir)` | R-22 | 添加 data_dir 声明 |
| `fix_doc_code_consistency(skill_dir)` | R-23 | 修复文档-代码一致性 |
| `fix_artifact_paths(skill_dir)` | R-11 | 修复产出物路径 |
| `fix_external_data_dir(skill_dir)` | R-12 | 修复外部数据目录 |
| `fix_sensitive_access(skill_dir)` | R-13 | 添加敏感信息访问声明 |
| `fix_critical_write(skill_dir)` | R-14 | 添加关键位置写入声明 |
| `fix_create_permissions_md(skill_dir)` | R-15 | 创建 references/permissions.md |
| `fix_permission_weight(skill_dir)` | R-16 | 添加权限权重说明 |

> **推荐工作流**：先运行审计 → 查看报告 → 调用 `apply_fix()` 批量修复 → 再次审计验证。


## 规范加载 — 渐进式 JSON 查询

```bash
# 列出所有可用模块
python scripts/json_loader.py list

# 加载指定模块
python scripts/json_loader.py load frontmatter    # Frontmatter 字段规范
python scripts/json_loader.py load body           # 正文章节规范
python scripts/json_loader.py load rules          # 审查规则 R-01~R-10
python scripts/json_loader.py load structure      # 目录结构规范 [v2]
python scripts/json_loader.py load progressive_md # 渐进式 MD 体系 [v2]

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


## 7. 安全增强功能（v2.13.0）

> 本 skill 在创建/更新/改造其他 skill 时，会自动进行权限检查和授权管理。

### 权限检查流程

`skill-standardization` 在 `update` 模式下会自动调用 `permission_checker.py` 扫描目标 skill 的脚本，计算权限权重，生成风险报告。

```
-m scripts.skill_builder update <skill-dir>
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
| R-14 | ERROR | 关键位置写入声明（写入 skills/技能数据目录/系统目录须声明 `critical_write: true`） |
| R-15 | ERROR | 高权限操作风险说明（脚本含高/严重风险操作时，`references/permissions.md` 须包含对应操作的风险说明、权限作用、执行步骤） |
| R-16 | WARN | 权限权重说明（建议在 SKILL.md 或 references/ 中说明各操作的权限权重） |
| R-17 | ERROR | 渐进加载引用（SKILL.md > 200 行时必须拆分到 references/ 并通过引用链接） |


---

## 注意事项

1. **refactor 前务必先 `--dry-run`**
2. **备份是 refactor 默认行为**：不要用 `--no-backup` 除非明确知道风险
3. **本文件控制在 200 行以内**：超过部分已拆分到 `references/`
4. **审查是纯警告模式**：审计结果仅作参考，不阻断操作
5. **版本号三方一致**：更新后按上表同步
