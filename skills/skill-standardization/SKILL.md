---
name: skill-standardization
version: 2.0.0
author: wUwproject
license: MIT
description: >
  Skill 标准化规范引擎 v2 — 集规范定义、创建器、更新器、
  改造器于一体的全生命周期工具。基于草案 v0.1，
  支持 R-01~R-10 审查、渐进式 JSON 加载、标准目录结构、
  渐进式 MD 文件体系。
tags: [standardization, skill-builder, skill-audit, validation, json-loader, refactor]
---

# skill-standardization — Skill 标准化规范引擎 v2

基于 **SKILL.md 标准化规范草案 v0.1**，提供 Skill 全生命周期的标准化管理：

| 能力 | 说明 | 工具 |
|------|------|------|
| **创建 (create)** | 从模板初始化标准 skill | `skill_builder.py create` |
| **更新 (update)** | 增量规范化检查与修复 | `skill_builder.py update` |
| **改造 (refactor)** | 非标 skill 整体优化（信息零遗漏） | `skill_builder.py refactor` |
| **审查 (audit)** | R-01~R-10 自动审查 | `skill_audit.py audit` |
| **规范加载** | 渐进式 JSON 规范按需加载 | `json_loader.py load` |

---

## 触发场景

当用户提到以下任一意图时触发本技能：
- "创建/新建一个 skill"、"标准化创建 skill"
- "检查/审查/审计 SKILL.md"
- "更新/规范化已有 skill"
- "改造/重构/优化 skill 结构"
- "skill 是否符合标准/规范"
- "SKILL.md 标准化"、"skill 标准验证"

---

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | **三种执行模式** | create / update / refactor 覆盖 skill 全生命周期 |
| 2 | **10 条自动审查规则** | R-01~R-04 (ERROR) + R-05~R-10 (WARN)，纯警告不阻断 |
| 3 | **标准目录结构规范** | 根目录仅 SKILL.md + _meta.json，三级复杂度布局 |
| 4 | **渐进式 MD 文件体系** | 主文件 ≤200 行核心，辅助内容拆分到 references/ 按需加载 |
| 5 | **零依赖 Python 工具** | 所有脚本仅使用标准库，跨平台兼容 |
| 6 | **信息完整性保障** | refactor 模式强制备份 + 全量扫描 + 仅移动不删除 + 映射报告 |

---

## 快速开始

```bash
# 1. 创建新 skill（从模板）
python scripts/skill_builder.py create my-skill --desc "我的技能" --tags tag1,tag2

# 2. 检查已有 skill 的规范化状态
python scripts/skill_builder.py update ~/.workbuddy/skills/my-skill

# 3. 改造非标 skill 到标准结构（先 dry-run 看计划！）
python scripts/skill_builder.py refactor ~/.workbuddy/skills/old-skill --dry-run

# 4. 执行审查
python scripts/skill_audit.py audit ~/.workbuddy/skills/my-skill

# 5. 加载规范定义
python scripts/json_loader.py load structure          # 目录结构规范
python scripts/json_loader.py load progressive_md     # 渐进式MD体系
python scripts/json_loader.py load all                 # 全部规范
```

---

## 三种执行模式详解

### 模式 A：create（创建）

从模板初始化一个新的**完全符合标准**的 skill。

**何时使用：**
- 用户要新建一个 skill
- 需要一个标准的 skill 骨架作为起点

**执行流程：**
```
输入: name + description(可选) + tags(可选)
  ↓
生成标准目录:
  <name>/
  ├── SKILL.md          (含 frontmatter + TODO 占位符模板)
  ├── _meta.json        (五字段元数据)
  ├── references/.gitkeep     (渐进式MD目录)
  └── scripts/.gitkeep  (脚本目录)
  ↓
输出: 创建结果 + 后续指引
```

**关键设计：**
- SKILL.md 模板包含所有必填章节的占位符（TODO 标记清晰）
- 版本号从 0.1.0 开始，遵循 SemVer
- author 默认为 `your-name-here` 占位符（铁律1：不可擅自替换为具体人名）

→ 详见 `references/guide.md` 完整创建教程（按需编写）

### 模式 B：update（更新）

对已有的 skill 进行增量规范化**检查和修复**。

**何时使用：**
- 已有 skill 需要检查是否符合最新规范
- 需要补充缺失的字段或章节

**检查项：**
| 检查项 | 说明 | 可自动修复？ |
|--------|------|-------------|
| _meta.json 存在性和字段完整性 | 五字段齐全 | ✅ --fix |
| SKILL.md frontmatter 存在性 | 以 --- 开头 | ❌ 需手动 |
| 必填章节完整性 | 触发场景/核心能力/快速开始 | ❌ 需手动提示 |
| 文件大小合理性 | SKILL.md ≤ 200 行 | 💡 建议拆分 |
| 根目录规范性 | 无散落文件 | 💡 建议 |

**执行示例：**
```bash
# 仅查看检查报告
python scripts/skill_builder.py update ./my-skill

# 自动修复可修复的问题 + 备份原文件
python scripts/skill_builder.py update ./my-skill --fix --backup
```

### 模式 C：refactor（改造）

对**不符合标准**的 skill 进行整体结构改造。

**⚠️ 核心约束：信息零遗漏**

**安全保障机制：**
```
1. 强制备份（除非显式 --no-backup）
2. 全量扫描 → 文件清单（路径+大小+时间）
3. 仅执行 move 操作（绝不 delete）
4. 移动后验证总字节一致性（允许 1% 容差）
5. 输出完整迁移映射表
6. 失败时可从备份完整回滚
```

**迁移规则（M-01 ~ M-06）：**
| ID | 规则 | 示例 |
|----|------|------|
| M-01 | 根目录 .py/.sh → `scripts/` | `tool.py` → `scripts/tool.py` |
| M-02 | 根目录 .md（非 SKILL.md）→ `references/` | `NOTES.md` → `references/NOTES.md` |
| M-03 | requirements.txt → `scripts/` | `requirements.txt` → `scripts/requirements.txt` |
| M-04 | config.json 等 → `scripts/` 或保留根目录 | 取决于是否被外部引用 |
| M-05 | __pycache__/ 始终排除 | 不参与迁移 |
| M-06 | 迁移时内容不变（仅移动位置） | 保持原始内容和编码 |

**执行示例：**
```bash
# ★ 推荐：先 dry-run 查看计划
python scripts/skill_builder.py refactor ./old-skill --dry-run

# 确认无误后执行（自动备份）
python scripts/skill_builder.py refactor ./old-skill

# 回滚（用备份覆盖）
mv ./old-skill_bak_refactor_YYYYMMDD_HHMMSS ./old-skill
```

→ 详见 `references/guide.md` refactor 详细指南（按需编写）

---

## 标准目录结构

> 📖 加载命令：`python scripts/json_loader.py load structure`

### 根目录（必须且仅包含）

| 文件 | 必填 | 说明 |
|------|------|------|
| `SKILL.md` | ✅ | 技能主文件（≤200 行，含核心章节） |
| `_meta.json` | ✅ | 元数据（name/version/description/author/tags） |

**约定：根目录不应放置其他文件。**

### 子目录（按需创建）

```
<skill-name>/
├── SKILL.md                  # [必填] 主文件
├── _meta.json                # [必填] 元数据
│
├── references/                     # 渐进式 MD 辅助文档
│   ├── guide.md              #     使用指南（详细教程）
│   ├── examples.md           #     示例集合
│   ├── reference.md          #     API/命令参考
│   ├── faq.md                #     常见问题
│   └── ...                   #     其他 .md 文件
│
├── scripts/                  # 可执行脚本和工具
│   ├── *.py / *.sh           #     脚本文件
│   └── spec/                 #     JSON 规格定义
│
├── assets/                   # [可选] 静态资源
│   └── images/ / templates/
│
└── tests/                    # [可选] 测试
    └── test_*.py
```

### 三级复杂度

| 级别 | 适用场景 | 包含目录 | 示例 |
|------|---------|---------|------|
| **minimal** | 纯提示型 skill | SKILL.md + _meta.json | color-toolkit |
| **standard** | 有脚本或文档的 skill | + scripts/ + references/ | git-sync, triphasic-execution |
| **full** | 复杂工具型 skill | + assets/ + tests/ | — |

---

## 渐进式 MD 文件体系

> 📖 加载命令：`python scripts/json_loader.py load progressive_md`

### 核心原则

> **主 SKILL.md 必须可独立理解核心功能和使用方法。** references/ 下的渐进式 .md 是按需加载的补充材料，缺失不影响基本使用。

### 拆分边界

| 主文件 SKILL.md 必须包含 | 拆分到 references/ 的渐进式 MD |
|--------------------------|------------------------|
| ✅ frontmatter 元数据 | 📄 详细教程 (`guide.md`) |
| ✅ 技能名称/一级标题 | 📄 完整示例 (`examples.md`) |
| ✅ 触发条件/适用场景 | 📄 参考/API文档 (`reference.md`) |
| ✅ 核心功能概述 | 📄 FAQ常见问题 (`faq.md`) |
| ✅ 快速开始（最简用法） | 📄 更新日志 (`changelog.md`) |
| | 📄 架构设计 (`architecture.md`) |

### 加载协议

```
用户任务 → AI 加载 SKILL.md（始终发生）
         ↓
    任务简单？ → 直接用 SKILL.md 执行
         ↓ 否
    任务复杂？ → 检查 SKILL.md 中的 references/ 引用
         ↓
    按需读取 references/*.md 补充决策
```

### 引用语法（在 SKILL.md 中指向渐进式 MD）

```markdown
→ 详见 `references/guide.md` 完整教程
→ [API 参考](references/reference.md) 查看全部选项
→ `references/examples.md` 包含更多使用示例
```

---

## 审查规则（R-01 ~ R-10）

### ERROR 级（纯警告，不阻断）

> ⚠️ 自 v2.0 起，ERROR 级问题在 git-sync 中**仅为警告**，不会阻止同步。

| ID | 名称 | 检查逻辑 |
|----|------|----------|
| R-01 | Frontmatter 存在性 | 文件以 `---` 开头且包含闭合 `---` |
| R-02 | name 字段 | frontmatter 中存在 `name` 键 |
| R-03 | version SemVer | `version` 匹配 `\d+\.\d+\.\d+(-\w+)?` |
| R-04 | description 字段 | frontmatter 中存在 `description` 键 |

### WARN 级（建议改进）

| ID | 名称 | 检查逻辑 |
|----|------|----------|
| R-05 | name 与目录名一致 | `name` 值等于父目录名 |
| R-06 | 正文含一级标题 | 正文中存在 `# ` 开头的行 |
| R-07 | 触发条件章节 | 含关键词匹配的 `## ` 标题 |
| R-08 | 核心能力章节 | 含关键词匹配的 `## ` 标题 |
| R-09 | 工作流程章节 | 含关键词匹配的 `## ` 标题 |
| R-10 | version 一致性 | SKILL.md version == manifest.json version |

### 同义关键词

| 规范章节 | 匹配关键词 |
|----------|-----------|
| 触发条件 | `触发条件`, `触发场景`, `适用场景`, `触发` |
| 核心能力 | `核心功能`, `核心能力`, `概述`, `核心概念`, `Overview` |
| 工作流程 | `工作流程`, `使用方式`, `Workflow`, `完整执行流程` |

---

## 与 git-sync 的集成

git-sync 在同步步骤 3.5 自动调用 `skill_audit.py` 进行审查：

```
同步前审查（git-sync.sh 步骤 3.5）
  ↓
skill_audit.py audit <skill_dir> --json
  ↓
解析 ERROR/WARN 数量 → 终端输出人类可读报告
  ↓
🟡 纯警告模式：不阻断、不中止、不强制修复
  ↓
继续同步后续步骤
```

**关键变更（v1.8.0+）：**
- ~~ERROR → exit(1) 阻断~~ → **始终 exit(0)**
- ~~🔴 ERROR 级问题~~ → **🟡 纯警告提示**

---

## 规范文件结构（渐进式加载模型）

```
skill-standardization/
├── SKILL.md                          # 本文件（v2）
├── _meta.json                        # 元数据
├── scripts/
│   ├── skill_builder.py              # [v2新增] 构建器（create/update/refactor）
│   ├── skill_audit.py                # 审查工具（与 git-sync 共享）
│   ├── json_loader.py               # 渐进式 JSON 加载器
│   └── spec/                         # 规范定义
│       ├── _index.json              # [v2] 模块索引（6模块）
│       ├── frontmatter.json          # Frontmatter 字段规范
│       ├── body.json                 # 正文章节规范
│       ├── rules.json                # 审查规则 R-01~R-10
│       ├── structure.json            # [v2新增] 目录结构规范
│       └── progressive_md.json      # [v2新增] 渐进式MD体系规范
```

### 可加载模块

| 命令 | 加载内容 | 大小 | 使用场景 |
|------|---------|------|---------|
| `load frontmatter` | 字段定义（3必须+7可选） | ~1KB | 编写 frontmatter 时 |
| `load body` | 章节结构（5必须+4推荐+N可选） | ~2KB | 编写正文时 |
| `load rules` | R-01~R-10 规则定义 | ~3KB | 执行审查时 |
| `load structure` | 目录结构规范 | ~3KB | 创建/改造 skill 时 |
| `load progressive_md` | 渐进式MD拆分方案 | ~4KB | 设计文档结构时 |
| `load all` | 全部规范 | ~16KB | 全量操作时 |

---

## 注意事项

1. **refactor 前务必先 `--dry-run`**：查看完整的迁移计划后再确认执行
2. **备份是 refactor 默认行为**：不要用 `--no-backup` 除非明确知道风险
3. **SKILL.md 控制在 200 行以内**：超过的部分考虑拆到 `references/`
4. **审查是纯警告模式**：不会阻止 git-sync 同步，但建议逐步优化
5. **版本号统一管理**：SKILL.md version + _meta.json version + manifest.json version 三方保持一致

---

## ⚙️ 改写/更新铁律（AI 执行前必须遵守）

以下规则适用于所有 AI 在改写或更新 skill 时的行为约束，**不限于本技能本身，而是对所有 skill 操作生效**：

### 铁律 1：author 字段不可擅自替换

- 技能是**通用工具**（所有人可安装使用），不是个人专用
- author 的默认值必须为 **`your-name-here`** 占位符
- 如果目标 skill 已有 author 值（如 `"由 config.json 的 author 字段决定"`），**保留原值不变**
- 只有用户明确指定时才写入真实署名

> ❌ 错误：将已有 `your-name-here` 或动态引用擅自改为具体人名
> ✅ 正确：保持原值 / 使用占位符 / 询问用户后再填写

### 铁律 2：版本号不确定时必须询问

- **SKILL.md 和 _meta.json 的 version**：技能自身元数据，改写后是否升级需**确认**
- **manifest.json 中的版本号**（version / gitee_version / github_version）：
  - 这是维护清单运行数据，由 **git-sync 上传同步流程**负责更新
  - **本地不应擅改**——提前修改会破坏三方对比逻辑（清单 vs 本地 vs 远程仓库）
  - 如不确定当前是否应升级，**先问用户**

> ❌ 错误：本地提前把 manifest.json 版本号从 1.8.0 改为 1.9.0
> ✅ 正确：只改 SKILL.md + _meta.json（确认后），manifest 留给上传流程

### 铁律 3：改写前必须理解每个文件的作用

- 在修改任何文件前，**先用 Read 工具阅读完整内容**
- 理解每个字段的含义、引用关系、被哪些脚本使用
- 特别注意：
  - `config.json`：运行时配置，可能被多个脚本通过相对路径引用
  - `manifest.json`：维护清单状态数据，有特定的读写时机
  - `_meta.json`：标准化元数据，其 author 可能来自 config.json 动态注入
  - 脚本中的硬编码路径/字段名：改动可能级联影响其他功能

> ❌ 错误：看到 author 字段就按自己理解改成常量，不考虑原始设计意图
> ✅ 正确：追踪字段的来源（config.json？模板？脚本生成？），再决定如何处理

---

## 版本更新日志

### v2.0.0（重大升级）

- **新增** skill_builder.py 构建器（create/update/refactor 三模式）
- **新增** 标准目录结构规范（structure.json）— 三级复杂度 + 6条迁移规则
- **新增** 渐进式 MD 文件体系（progressive_md.json）— 拆分边界 + 加载协议 + 文件映射
- **升级** git-sync 审查策略为纯警告模式（ERROR 不再退出非零码）
- **扩展** spec/_index.json 注册 structure 和 progressive_md 两个新模块
- **新增** 信息完整性保障机制（refactor 强制备份+全量扫描+零丢失验证）

### v1.0.0（初始版本）

- 基于 SKILL.md 标准化规范草案 v0.1 创建
- 实现 R-01~R-10 审查规则
- 实现渐进式 JSON 加载器（json_loader.py）
- 提供独立 CLI 和 git-sync 集成双模式
