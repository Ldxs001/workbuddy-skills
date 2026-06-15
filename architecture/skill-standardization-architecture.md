# skill-standardization 架构与规范体系文档

> 完整解读 v2.80.0 版的架构设计、审查规则体系、标准化执行流程与修复体系  
> 更新：2026-06-15（v2.73.2 → v2.80.0，含 11 个版本迭代的变更同步）

---

## 一、系统概览

skill-standardization 是一个 **Skill 全生命周期标准化管理工具集**，围绕以下闭环运行：

```
规范定义（spec/*.json）
  → 构建器（skill_builder: create / update / refactor）
    → 审查器（skill_audit: R-01 ~ R-26）
      → 修复器（fix.py: 30+ 自动修复函数）
        → 验证（--verify 铁律阻断）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI | 人类可读的文档和命令行交互 |
| **业务层** | skill_builder / skill_audit / fix.py / safe_io | 创建/更新/改造/审查/修复/安全写入的核心逻辑 |
| **数据层** | json_loader + spec/*.json | 按需加载的标准化规范定义；数据存储在 `skills/.standardization/<skill>/` |

### 1.2 目录结构

```
skill-standardization/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据（name/version/description/author/tags/data_dir/triggers）
├── references/                 # 渐进式文档
│   ├── guide.md                # 完整使用教程
│   ├── architecture.md         # 架构设计（本文件）
│   ├── reference.md            # API/命令参考手册
│   ├── rules.md                # 铁律 1~9 与完整规则说明
│   ├── blueprint_flow.md       # 蓝皮书扫描流程定义
│   ├── antipatterns.md         # 反模式速查
│   ├── data_dir_map.md         # 数据目录路径引用对照表
│   ├── examples.md             # 使用示例
│   ├── faq.md                  # 常见问题
│   ├── changelog.md            # 版本更新日志
│   ├── permissions.md          # 权限声明
│   ├── LICENSE.md              # MIT 许可证（R-26 要求）
│   └── scan_patterns.json      # 扫描模式定义
└── scripts/                    # 核心脚本
    ├── skill_builder/          # 构建器包（OO 重构）
    │   ├── __init__.py         # 主入口 + argparse
    │   ├── __main__.py         # python -m 支持
    │   ├── creator.py          # SkillCreator（create 模式）
    │   ├── updater.py          # SkillUpdater（update 模式）
    │   ├── refactor.py         # SkillRefactor（refactor 模式）
    │   ├── migrator.py         # SkillMigrator（migrate-data 命令）
    │   ├── version_manager.py  # VersionManager（版本号管理）
    │   └── utils.py            # 工具函数（备份、模板等）
    ├── skill_audit/            # 审查器包（OO 重构）
    │   ├── __init__.py         # 主入口 + audit_skill() + cmd_refactor/create/update/bump
    │   ├── __main__.py         # python -m 支持
    │   ├── frontmatter_checker.py  # R-01~R-05（frontmatter + _meta.json）
    │   ├── structure_checker.py    # R-06~R-09, R-18~R-25 正文结构 + 质量 + R-26
    │   ├── artifact_checker.py     # R-11~R-12 产出物 + 数据目录
    │   ├── permission_checks.py    # R-13~R-17 安全权限
    │   ├── data_dir_checker.py     # R-22 数据目录合规
    │   ├── consistency_checker.py  # 一致性审查（outdated_rule_ref 等）
    │   ├── _tree_scanner.py        # 目录树扫描器（R-23 辅助）
    │   ├── progress_manager.py     # 进度管理器
    │   ├── fix.py              # 自动修复函数（30+ 规则）
    │   └── utils.py            # 常量定义（RULES 列表、关键词映射等）
    ├── json_loader.py          # 渐进式 JSON 加载器
    ├── safe_io.py              # 安全文件写入（原子写入 + 备份 + Windows 重试）
    ├── log.py                  # 共享日志模块（统一日志配置，v2.73.3 新增）
    ├── op_logger.py            # 操作日志记录
    ├── op_logger_patch.py      # 操作日志补丁
    ├── run_audit.py            # 独立审计入口
    ├── cleanup_manager.py      # Manifest 驱动清理（备份注册 + 收尾清理）
    ├── authorization_manager.py # 授权管理器
    ├── permission_checker.py   # 权限检查器（AST 扫描风险操作）
    ├── skill_inspector.py      # 结构扫描器（输出技能蓝皮书）
    ├── skill_rollback.py       # 回滚工具
    ├── patch_utils.py          # 补丁工具
    ├── update_all_versions.py  # 全版本更新
    ├── update_skill_frontmatter.py # frontmatter 更新脚本
    └── spec/                   # 规范定义（JSON Schema）
        ├── _index.json         # 模块注册索引
        ├── frontmatter.json    # Frontmatter 字段规范 v2.6.0（11 required + 2 conditional + 4 optional）
        ├── body.json           # 正文章节结构规范 v2.6.0（三层章节体系 + classification_hints）
        ├── rules.json          # 审查规则完整定义（R-01~R-26，12 ERROR + 9 WARN）
        ├── structure.json      # 目录结构规范
        └── progressive_md.json # 渐进式 MD 体系规范
```

**变化说明（v2.73.2 → v2.80.0）**：
- ✅ **新增** `scripts/log.py` — 共享日志模块（v2.73.3）
- ✅ **新增** `skill_audit/consistency_checker.py` — 一致性审查闭环
- ✅ **新增** `skill_audit/_tree_scanner.py` — 目录树扫描器
- ✅ **新增** `references/LICENSE.md`、`references/permissions.md`、`references/scan_patterns.json`
- ❌ **已删除** `scripts/_dead_code_backup/` — 50+ 死文件已清理（v2.73.3）
- ❌ **已删除** blueprint 参数体系（v2.75.0）

### 1.3 三层章节体系（section_tiers）

SKILL.md 的 `##` 章节分为三个层级，决定其存留行为和拆分优先级：

| 层级 | 包含章节 | 行为 |
|------|---------|------|
| **① must_have** | H1 / 约束 / 触发条件 / 核心能力 / 工作流程 | 永远留在 SKILL.md，不拆分 |
| **② whitelist.optional_progressive** | 快速开始 / 强制约束 / 铁律 / 规范 / 反模式 / FAQ / 配置 / API / 示例 / 限制 / 数据目录说明 / 权限说明 / 临时文件与备份管理 / 注意事项 | 可留，超230行时优先拆到 references/ |
| **②' whitelist.always_progressive** | 版本日志 / 更新日志 / Changelog | 强制在 references/，SKILL.md 只能有引用（R-24） |
| **③ nonstandard** | 不在①②的所有H2 | Phase 1 粗筛 → Phase 2 精筛：合并 or 拆分 |

**渐进式索引表**：所有标准技能的 `## 核心能力` 末尾应包含 `### 渐进式文件索引` 表格（文件名/位置/说明），集中列出所有 references/*.md。C-13 审计完整性，C-15 审计正文重复引用。

### 1.4 能力与限制章节

SKILL.md 新增 `## 能力与限制` 章节（v2.62.2），明确列出每项核心能力的适用范围和限制条件：

| 能力 | 说明 | 限制 |
|------|------|------|
| **审计现有 skill** | R-01~R-26 全量检查，输出 PASS/WARN/FAIL 逐条明细及上下文行 | 仅检查 SKILL.md + _meta.json + scripts/ 文件结构和代码静态分析，不检查 Python 运行时行为 |
| **创建新 skill** | 从模板生成标准骨架（含目录结构预览 v2.63.0） | 只生成结构模板和占位符，功能代码需要手动填充 |
| **改造非标 skill** | 自动迁移文件到正确位置 | 不处理跨技能依赖、不自动生成功能代码 |
| **批量审计** | `--audit-all` 参数扫描多个 skill | 仅支持一级子目录（不支持嵌套） |
| **自动修复** | `--fix` 自动修正格式/结构/路径/生成类问题，覆盖 R-01~R-26 共 20+ 条规则 | 仅修格式/结构/路径/生成类问题，**不修复代码逻辑错误**。<br>修复后需运行 `--verify` + `--show-fix` 两阶段验证确认 |
| **权限安全扫描** | 自动检测脚本中的删除/网络/subprocess 调用 | 基于 AST 静态分析，无法检测动态执行 |

**触发后立即可见**：读取目标 SKILL.md 中的 frontmatter/正文/references/scripts → 执行 R-01~R-26 规则审查 → 输出审查报告（含每条规则的 PASS/WARN/FAIL 状态 + 详细原因 + 附近代码上下文）。

### 1.5 四种执行模式

| 模式 | 命令 | 作用 | 风险等级 |
|------|------|------|---------|
| **audit** | `python -m scripts.skill_audit audit <dir> --confirmed` | 独立全量审计 | 🟢 只读 |
| **create** | `python -m scripts.skill_audit create <name> --confirmed` | 从模板创建标准的 skill 骨架 | 🟢 无害 |
| **update** | `python -m scripts.skill_audit update <dir> [--fix] --confirmed` | 增量检查 + 可选修复 | 🟡 轻度修改 |
| **refactor** | `python -m scripts.skill_audit refactor <dir> --confirmed` | 全流程改造（蓝皮书→备份→审计→修复→验证→bump→清理） | 🟡 有备份保障 |

> **语义门禁**（v2.73.0+）：所有模式入口必须传 `--confirmed` 参数，否则 exit(0) 阻断。脚本级强制，不再靠 LLM 自觉。

---

## 二、完整审查规则体系（R-01 ~ R-26）

26 条规则按用途分为 7 大类别，严重度分为 **ERROR**（必须修）和 **WARN**（建议修）两级。  
**代码定义**：`scripts/skill_audit/utils.py` 中 `RULES` 列表 + `scripts/spec/rules.json`（`_total_rules: 26`, `_error_count: 12`, `_warn_count: 9`）。

### 2.1 类别 A：Frontmatter 结构（R-01 ~ R-05）

**目的**：确保每个 skill 有完整可解析的 YAML frontmatter，字段齐全、命名规范。R-01 合并了 _meta.json 字段检查。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-01** | ERROR | YAML frontmatter 存在性 + 11 required + 2 conditional 字段 + _meta.json 7 字段完整性 | 文件以 `---` 开头并包含闭合 `---`；11 required + 2 conditional 字段分层检查；_meta.json 含 7 标准字段（name/version/description/author/tags/data_dir/triggers） |
| **R-02** | ERROR | `name` 字段 | frontmatter 含 `name:`，值非空，且与目录名一致 |
| **R-03** | ERROR | `version` 字段（SemVer + 变更语义规则） | 值符合纯数字 x.y.z 格式（禁止 v 前缀）；附带 MAJOR/MINOR/PATCH 变更语义规则 |
| **R-04** | ERROR | `description` 字段 | 含 `description:`，值非空且 ≤120 字符 |
| **R-05** | WARN | name = 目录名 | frontmatter 的 name 与所在目录名一致 |

**Frontmatter 字段分层体系**（`scripts/spec/frontmatter.json` v2.6.0）：
- **11 required**：name / version / description / author / license / tags / data_dir / external_data_dir / sensitive_access / critical_write / permission_weight
- **2 conditional**：trigger / trigger_negative（正文有触发词/否定条件时必填）
- **4 optional**：references / category / priority / deprecated

**非标字段处理策略**：
- **_meta.json 非标字段**：审计阶段标记并提示"需人工判断删/迁移"（WARN）；`--fix` 自动修复时直接删除（_meta.json 是机器元数据，应保持严格一致）
- **frontmatter 非标字段**：仅 WARN 提醒，不移除（frontmatter 允许自定义字段如 home_url、category）

### 2.2 类别 B：正文结构（R-06 ~ R-10）

**目的**：规范 SKILL.md 正文的结构和内容质量，确保可读性。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-06** | WARN | 一级标题 | 正文包含 `# ` 开头的 H1 标题（排除代码块内 `#` 注释）；H1 不得含版本号；H1 应紧跟在 frontmatter 后；H1 内容应含技能名 |
| **R-07** | **ERROR** | 触发条件章节 | 含触发场景章节，≥3 个触发词，≥1 个否定条件，无「自动执行」等危险表述，且与 frontmatter 的 trigger/trigger_negative 字段一致性 |
| **R-08** | WARN | 核心能力章节 | 含核心能力/功能章节 |
| **R-09** | WARN | 工作流程章节 | 含工作流程/步骤章节 |
| **R-10** | **ERROR** | 版本三端一致性 + 时序检查 | SKILL.md version == _meta.json version == changelog 最新版本号；mtime 时序检查检测修改后未更新版本号；版本号必须为纯数字 x.y.z（禁止 v 前缀） |

**R-07 质量子检查**：正向触发词数量 ≥3 个（每条约 4 字以上，含具体动作）；否定条件 ≥1 个；无自动执行类危险表述；frontmatter trigger/trigger_negative 与正文一致性。

**R-10 共享字段一致性**：_meta.json 与 frontmatter 的 name/description/tags/trigger/data_dir 交叉比对，路径自动归一化（`skills/` ≈ `../`），`--fix` 按权威方向自动同步（tags 以 _meta 为准、description/trigger 以 frontmatter 为准、data_dir 统一为 `../` 相对路径）。

### 2.3 类别 C：产出物与数据目录（R-11 ~ R-12）

**目的**：防止数据/产出物污染技能安装目录，规范数据目录路径。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-11** | ERROR | 产出物路径 + 风险检测 | 产出物符合 `skills/.standardization/<skill>/` 规范，且无路径遍历/跨目录写入/敏感信息泄露风险；根目录下的 `.standardization/` 现在会被报违规（v2.80.0） |
| **R-12** | ERROR | 外部数据目录 + 风险检测 | 路径符合 `skills/.standardization/<skill-name>/` 约定，_meta.json 含 data_dir 字段且一致，无数据泄露风险。`DEFAULT_DATA_DIR_RAW` 变量所在行必须直接赋值合规字面量（不得通过中间变量间接赋值） |

**R-12 三源证据链**：审计器对源码做三源证据链判断。推荐双变量模式：
```python
DEFAULT_DATA_DIR_RAW = "skills/.standardization/<skill>/data/"  # R-12 审计锚点
_data_dir_abs = os.path.normpath(os.path.join(SKILL_ROOT, "..", DEFAULT_DATA_DIR_RAW))  # 运行时路径
```

### 2.4 类别 D：安全与权限（R-13 ~ R-17）

**目的**：确保 skill 声明的权限与实际行为一致，防止未经授权的敏感操作。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-13** | WARN | 敏感信息访问声明 | 脚本含敏感信息访问（memory/credentials/token）时，frontmatter 须声明 `sensitive_access: true` 并在 references/permissions.md 中说明用途 |
| **R-14** | WARN | 关键位置写入声明 | 脚本含关键位置写入（skills/.workbuddy/系统目录）时，须声明 `critical_write: true` |
| **R-15** | ERROR | 高权限操作风险说明 | 脚本含高权限操作（风险等级 high/critical）时，references/permissions.md 须包含对应操作的风险说明（v2.73.9：改为调用 PermissionChecker.scan() 获取实际风险等级和发现项，自动生成完整内容） |
| **R-16** | WARN | 权限权重说明 | frontmatter 须声明 permission_weight（LOW/MEDIUM/HIGH/CRITICAL），且 references/permissions.md 须包含权限权重说明表格 |
| **R-17** | ERROR | 渐进加载引用（强制） | SKILL.md > 200 行时必须拆分到 references/，并通过「→ 详见 references/xxx.md」引用。非标准 H2 章节 Phase 1 正则粗筛 → Phase 2 LLM 精筛 |

**R-15 增强**（v2.73.9）：`fix_create_permissions_md()` 不再生成含"（请填写）"的模板，改为调用 `PermissionChecker.scan()` 获取实际风险等级和发现项，自动生成完整内容。同时新增占位符检测，避免"文件存在但内容是模板"的虚假 PASS。

### 2.5 类别 E：质量规范（R-18 ~ R-21）

**目的**：提升技能文档的内容质量，避免模糊、空洞的表述。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-18** | WARN | 反模式具体性 | 强制渐进式，检查 references/antipatterns.md 引用、文件存在性、内容质量（≥2 条具体示例 + 错误做法/正确做法标记） |
| **R-19** | WARN | FAQ 有意义性 | 强制渐进式，检查 references/faq.md 引用、文件存在性、Q&A 质量（≥3 对 + 问题≥10字 + 答案≥15字） |
| **R-20** | WARN | 写作规范 | 术语统一、无模糊词（可能/大概）、中英文混排空格、脚本调用验证 |
| **R-21** | WARN | 渐进式加载说明 | 核心能力/工作流程章节中包含固定模板句 |

**R-21 固定模板句**：
```
> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。
```

### 2.6 类别 F：合规与维护（R-22 ~ R-24）

**目的**：确保技能符合数据目录规范、文档与代码一致、更新日志规范。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-22** | WARN | 数据目录合规 | 检查安装目录是否混入应属数据目录的文件（如 cache/temp/backup）；`.standardization/` 目录被 os.walk 跳过（不会误报标准化数据目录） |
| **R-23** | WARN | 文档-代码一致性 | SKILL.md 引用的脚本/文件/函数名真实存在，代码示例中的调用方式与实际代码一致（含目录树扫描器 `_tree_scanner.py` 辅助检测） |
| **R-24** | WARN | 更新日志渐进加载 | 更新日志必须放在 references/changelog.md，SKILL.md 只能有引用 |

### 2.7 类别 G：文档写作格式（R-25，含 C-01~C-12 十二项子检查）

**目的**：统一 SKILL.md 的写作格式，提供标准化的排版建议。R-25 整体为 WARN 级，C-01 为 ERROR 级。

| 编号 | 级别 | 检查项 | 说明 |
|:----:|:----:|--------|------|
| C-01 | ERROR | H1 标题格式 | 必须为 `# <技能名>`，不得含版本号 |
| C-02 | WARN | 标题层级 | 限制在 `##` 和 `###`，不应出现 `####+` |
| C-03 | WARN | 表格使用 | 结构化信息应使用表格展示 |
| C-04 | WARN | 引用块使用 | 提示/注意/警告应使用 `>` 引用块包装 |
| C-05 | WARN | 列表区分 | 有序列表用于步骤流程，无序列表用于选项列举 |
| C-06 | WARN | 加粗使用 | 关键术语/约束/规则名使用 `**加粗**` 强调 |
| C-07 | WARN | 语言标识 | 代码块应带语言标识（` ```bash `、` ```python `） |
| C-08 | WARN | Checklist | 操作前自检使用 `- [ ]` checklist 格式（带行号+触发词） |
| C-09 | WARN | 渐进引用 | 引用渐进式文件统一使用 `→ 详见 references/xxx.md` |
| C-10 | WARN | 空行规范 | frontmatter 闭合后 ≤2 个连续空行；正文 ≤4 个连续换行 |
| C-11 | WARN | 章节顺位 | H2 章节出现顺序应与 body.json section_order 一致 |
| C-12 | WARN | 格式合规 | 每个 H2 章节使用的格式应与 body.json content_format 定义一致 |

**冲突排除矩阵**：

| 现有规则 | 冲突点 | 处理方式 |
|---------|--------|---------|
| R-06 | 均检查 H1 | R-06 查存在性（WARN），C-01 查格式（ERROR），互补不冲突 |
| R-21 | 渐进式加载模板句含 `>` 引用 | C-02/C-04 不检查该模板句的格式 |
| R-24 | 更新日志章节可能在 references/ | C-02 不约束更新日志位置 |
| R-18/R-19 | 反模式/FAQ 须渐进式引用 | C-09 不约束已有强制规范的引用 |

### 2.8 类别 H：文档声明规范（R-26，含 C-01~C-08 八项子检查）

**新增于 v2.75.0**。目的：确保 LICENSE 和 README 声明符合规范，遵循渐进式加载体系。

| 编号 | 级别 | 检查项 | 说明 |
|:----:|:----:|--------|------|
| C-01 | ERROR | references/LICENSE.md 存在 | 文件必须存在 |
| C-02 | ERROR | SKILL.md 正文无独立 license 章节 | frontmatter 的 license 字段保留，正文不得有独立 license/License 章节或声明 |
| C-03 | ERROR | 根目录无 LICENSE 文件 | 根目录不得存在 LICENSE.txt/LICENSE.md 等 license 文件 |
| C-04 | WARN | scripts/ 下无 LICENSE 文件 | scripts/ 下不得存在 LICENSE 文件 |
| C-05 | WARN | 渐进式索引表含 LICENSE.md 引用 | SKILL.md 的渐进式文件索引表应包含 LICENSE.md |
| C-06 | ERROR | references/LICENSE.md 非空 | 内容不应为空 |
| C-07 | ERROR | 根目录无 README.md | 根目录不得存在 README.md（应放在 references/） |
| C-08 | ERROR | SKILL.md 正文 README 章节拆分 | SKILL.md 正文含 README/说明章节应拆分至 references/README.md |

**冲突排除**：R-01 保留 frontmatter 的 license 字段，R-26 仅检查正文和文件系统。

### 2.9 规则汇总统计

| 类别 | 包含规则 | ERROR | WARN | 目的 |
|------|---------|:-----:|:----:|------|
| A. Frontmatter | R-01~R-05 | 4 | 1 | 技能身份标识 + _meta.json 字段完整性 |
| B. 正文结构 | R-06~R-10 | 3 | 2 | 文档结构和质量（R-06/R-08/R-09 为 WARN；R-07/R-10 为 ERROR） |
| C. 产出物与目录 | R-11~R-12 | 2 | 0 | 目录隔离和数据安全 |
| D. 安全与权限 | R-13~R-17 | 2 | 3 | 权限声明和风险控制（R-15/R-17 为 ERROR） |
| E. 质量规范 | R-18~R-21 | 0 | 4 | 内容质量和可读性 |
| F. 合规与维护 | R-22~R-24 | 0 | 3 | 长期维护一致性 |
| G. 写作格式 | R-25 | 0 | 1 | 文档排版统一建议（12 项子检查仅 C-01 为 ERROR 级） |
| H. 文档声明 | R-26 | 0 | 1 | LICENSE + README 声明规范（8 项子检查中 C-01/C-02/C-03/C-06/C-07/C-08 为 ERROR 级） |
| **合计** | **R-01~R-26** | **11** | **15** | |

---

## 三、核心设计原则

### D1: 零外部依赖
所有脚本仅使用 Python 标准库（pathlib, json, re, argparse 等），零 pip install。
**目的**：降低安装门槛，提高跨平台兼容性，减少供应链风险。

### D2: 铁律验证阻断模式
审查发现 ERROR/WARN 时，refactor/update/bump 流程使用 `--verify` + exit(1) 阻断，要求 LLM 逐条排查修复。非误判项必须修复才能继续。
**目的**：0 ERROR 0 WARN 铁律强制，确保推送前所有真实问题已消除。

### D3: 信息零遗漏
refactor 模式绝不删除任何文件——只执行 `move` 操作，执行前强制备份，执行后验证字节一致性。
**目的**：Skill 包含用户自定义的有价值文件，即使不符合规范也不应丢失。

### D4: 渐进式加载
SKILL.md 是轻量入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。规范定义也遵循此原则——json_loader 只在请求时才读取对应的 spec JSON 文件。
**目的**：减少一次性加载的上下文开销，让 AI 和人类都能快速理解 skill 的核心信息。

### D5: 模板驱动
create 使用硬编码字符串模板（当前），未来可能支持外部模板文件。
**目的**：简单直接，无额外抽象，易于理解和自定义。

### D6: 备份优先 + Inspect 先读全
任何修改性操作（update --fix, refactor）在执行前均强制备份，带时间戳命名。备份后、改造前**强制运行 skill_inspector** 结构扫描，输出技能蓝皮书。
**目的**：备份确保可回滚；inspect 确保不遗漏文件或功能，避免"AI 读哪算哪导致的改造遗漏"。

### D7: Manifest 驱动清理
所有修改性操作通过 `cleanup_manager.py` 注册备份到 manifest，`end_session()` 按清单删除。不再是"靠 AI 自觉清理"。
**目的**：确保临时文件和备份被可靠清理，不留残余。

### D8: 脚本级强制（非 AI 自觉）
语义门禁（`--confirmed`）、铁律阻断（exit(1)）、流程钩子全部在代码层强制，不再依赖 LLM 自觉遵守流程。
**目的**：消除 AI 不按流程走导致的问题。

---

## 四、强制约束与编程规范

### 4.1 版本号三端一致规则

版本号变更时必须同步更新以下 **3 处**：

| # | 文件 | 字段/位置 |
|---|------|-----------|
| 1 | `SKILL.md` frontmatter | `version:` 字段 |
| 2 | `_meta.json` | `"version"` 字段 |
| 3 | `references/changelog.md` | 版本条目 |

`bump` 子命令可一键升级版本号三端。`update --fix` 和 `refactor` 流程末尾自动执行三端验证钩子。

### 4.2 文件更新约束

所有 `.md` 文件**禁止使用 Write/Edit 工具更新**（会损坏 UTF-8 中文编码），必须用 Python 脚本原子写入：

| 文件 | 更新方式 | 使用脚本 |
|------|----------|---------|
| `SKILL.md` frontmatter | Python 原子写入 | `update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 原子重写 | `safe_io.py` 的 `safe_write()` |
| `references/*.md` | safe_io.py 的 `safe_write()` | 随技能自带 |
| 更新日志 | Python 合并脚本 | 每次发版统一维护 `references/changelog.md` |

**CRLF 编码约束**：`SKILL.md` 必须使用 CRLF 换行符（Windows 风格）。

### 4.3 工具自动保障

| 事项 | 保障方式 |
|------|---------|
| .md 文件写入 | `safe_io.py` 原子写入（`tmp + os.replace()` + Windows 3次重试 + `shutil.move` 降级） |
| 更新日志维护 | `bump` 子命令自动插入 references/changelog.md 条目 |
| CRLF 编码 | git-sync 推送前自动验证换行符 |
| 自审状态 | bump 后自动触发审计；推送前再次验证 |
| 版本号三端一致 | bump 子命令自动同步 SKILL.md / _meta.json / changelog |
| 临时文件清理 | `cleanup_manager` manifest 驱动，builder 收尾强制清理 |
| 非标章节检测 | R-17 Phase 1 正则粗筛 → Phase 2 LLM 精筛 |
| 章节格式合规 | R-25 C-12 自动比对 body.json content_format |
| 渐进式索引表 | C-13 审计自动检查完整性 |

### 4.4 排错止损规则

1. **区分警告来源**：审计 WARNING/ERROR 可能是审计工具自身的问题。先判断是被审计技能的真实问题还是审计工具的问题，再动手。
2. **同一操作失败 ≥2 次 → 强制停止换思路**：重复同样的失败操作不会得到不同结果。
3. **5 轮无实质进展 → 主动求助**：超过 5 轮没有向前推进，必须承认困境并请求指引。

### 4.5 R-12 数据目录字面量规则

```python
DEFAULT_DATA_DIR_RAW = "skills/.standardization/<skill-name>/data/"  # R-12 审计锚点
```

变量名必须含 `DATA|STORAGE|DB|CACHE|CONFIG` 之一才能被审计匹配。推荐使用 `DEFAULT_DATA_DIR_RAW` + `_data_dir_abs` 双变量模式。

---

## 五、反模式速查表

| ID | 反模式 | 级别 | 正确做法 |
|----|--------|:----:|---------|
| AP-01 | SKILL.md 写大量教程 | 🔴 | 拆分到 references/guide.md |
| AP-02 | 根目录散落文件 | 🔴 | scripts/ + references/ + assets/ |
| AP-03 | Frontmatter 字段缺失 | 🔴 | 补全 required 字段 |
| AP-04 | 触发词过于宽泛 | 🟡 | 含具体动作或对象 |
| AP-05 | 缺少否定条件 | 🟡 | 防误触发 |
| AP-06 | SKILL.md 超过 230 行 | 🔴 | 拆分到 references/ |
| AP-07 | 渐进式文件存在但无引用 | 🟡 | SKILL.md 添加引用 |
| AP-08 | R-07 只检查章节存在性 | 🟡 | 还需检查触发词质量 |
| AP-09 | 审查 FAIL 无修复建议 | 🟢 | 每条 FAIL 附带修复方案 |
| AP-10 | 版本号不一致 | 🔴 | 三端同步 |
| AP-11 | 不遵循 SemVer | 🟡 | patch/minor/major 规范 |
| AP-12 | 混淆审计工具警告和技能 bug | 🔴 | 先定位来源再动手 |
| AP-13 | 同一失败重复尝试不换思路 | 🔴 | 2 次失败后强制换方案 |

---

## 六、审计后自动修复体系（fix.py）

审计输出的 WARN/ERROR 可以直接通过 `scripts/skill_audit/fix.py` 自动修复：

| 函数 | 对应规则 | 修复内容 |
|------|---------|---------|
| `fix_name(skill_dir, value)` | R-01 | 修复 name 字段 |
| `fix_description(skill_dir, value)` | R-04 | 修复 description 字段 |
| `fix_version(skill_dir, value)` | R-03 | 修复 version 字段 |
| `fix_author(skill_dir, value)` | R-02 | 修复 author 字段 |
| `fix_h1(skill_dir)` | R-06 | 添加正文一级标题 |
| `fix_h1_version(skill_dir)` | R-06 | 移除 H1 中的版本号 |
| `fix_h1_position(skill_dir)` | R-06 | 将 H1 移到 frontmatter 后首行 |
| `fix_section_trigger(skill_dir)` | R-07 | 添加触发条件章节 |
| `fix_section_core(skill_dir)` | R-08 | 添加核心能力章节 |
| `fix_section_workflow(skill_dir)` | R-09 | 添加工作流程章节 |
| `fix_progressive_loading(skill_dir)` | R-21 | 添加渐进式加载模板句 |
| `fix_antipattern_progressive(skill_dir)` | R-18 | 创建/更新 antipatterns.md |
| `fix_faq_progressive(skill_dir)` | R-19 | 创建/更新 faq.md |
| `fix_writing_standards(skill_dir)` | R-20 + R-18 | 统一术语 + 反模式格式修正 |
| `fix_data_dir_compliance(skill_dir)` | R-22 | 添加 data_dir 声明 |
| `fix_doc_code_consistency(skill_dir)` | R-23 | 修复文档-代码一致性 |
| `fix_split_nonstandard(skill_dir)` | R-17 | 非标章节拆分到 references/ |
| `fix_section_order(skill_dir)` | R-25 C-11 | 按 body.json section_order 重排章节 |
| `fix_section_constraint(skill_dir)` | must_have | 从目标技能脚本采集约束词生成 ## 约束 |
| `fix_progressive_index_table(skill_dir)` | C-13 | 从 references/ 扫描文件名+H1 生成索引表 |
| `fix_reclassify_section(skill_dir, action, section_title, target_section)` | R-17 Phase 3 | 通用非标归类：merge/split/delete, 参数驱动 |
| `fix_artifact_paths(skill_dir)` | R-11 | 修复产出物路径 |
| `fix_external_data_dir(skill_dir)` | R-12 | 修复外部数据目录 |
| `fix_sensitive_access(skill_dir)` | R-13 | 添加敏感信息访问声明 |
| `fix_critical_write(skill_dir)` | R-14 | 添加关键位置写入声明 |
| `fix_create_permissions_md(skill_dir)` | R-15 | 创建 permissions.md（PermissionChecker.scan() 驱动，v2.73.9） |
| `fix_permission_weight(skill_dir)` | R-16 | 添加权限权重说明 |
| `fix_frontmatter_fields(skill_dir)` | R-01 | 补全 frontmatter 字段（required→conditional 分层补全） |
| `fix_meta_field_sync(skill_dir)` | R-10 | 同步 _meta.json 与 frontmatter 共享字段 |
| `fix_meta_json_completeness(skill_dir)` | R-01（合并） | 补全 _meta.json 7 标准字段，标记非标字段 |
| `fix_missing_data_dir(skill_dir)` | R-12 | 为引用 .standardization 但缺少 DATA_DIR 的脚本补上声明 |
| `fix_license_compliance(skill_dir)` | R-26 | 创建/修正 references/LICENSE.md + 清理根目录 LICENSE 文件 |
| `apply_consistency_fix(skill_dir)` | 一致性审查 | 修复 outdated_rule_ref 等一致性问题（v2.78.0） |

统一修复入口：
```python
from scripts.skill_audit.fix import apply_fix
apply_fix(skill_dir, 'R-07', 'R-18', 'R-19')  # 批量修复
```

**内容采集原则**（v2.46.0+）：所有 fix 函数生成章节内容时优先从目标技能自身采集，不照抄 skill-standardization 的模板：
- `fix_section_constraint`：扫描 `scripts/*.py` 中 必须/不得/禁止/MUST → 生成 ≤5 条约束
- `fix_progressive_index_table`：扫描 `references/*.md` 的 H1 和首段 → 生成 3 列索引表
- `fix_section_trigger`：扫描 docstring + frontmatter trigger 字段 → 生成触发表
- `fix_section_core`：扫描模块级 docstring + def 函数名 → 生成能力表格
- `fix_section_workflow`：扫描 `def main()` 和 CLI 入口 → 生成步骤列表

`audit --fix` 执行完毕后，终端输出 fix_details 机器名列表，并强制提示 AI 将其转化为可读 changelog 描述用 safe_io 写入 references/changelog.md。

---

## 七、与 git-sync 的协作（已解耦）

> **注意**：`skill-standardization` 与 `git-sync` 已完全解耦，本技能不依赖也不包含 git-sync 的任何功能。以下仅为历史集成关系说明。

```
git-sync 执行时（可选集成）
  └─ 步骤 3.5: skill_audit.py audit ← 可选调用（非强制，已从 git-sync 核心流程中移除）
```

**本技能的工作流在 bump + cleanup 后即终止**，不涉及 git 推送、commit、CRLF 验证等操作。如果用户需要在推送前自动审计，应由 git-sync 技能独立调用审计功能。

---

## 八、规范定义体系（spec/*.json）

| 文件 | 版本 | 职责 | 不包含 |
|------|------|------|-------|
| `frontmatter.json` | v2.6.0 | 定义 11 required + 2 conditional + 4 optional 字段，含非标字段处理策略 | 不含验证逻辑 |
| `body.json` | v2.6.0 | 三层章节体系 + section_order + content_format + classification_hints | 不含写作指导 |
| `rules.json` | v2.38.6 | 完整规则定义（R-01~R-26，12 ERROR + 9 WARN） | 不含执行引擎 |
| `structure.json` | — | 目录结构规范 + _meta.json 严格 7 字段 | 不含移动逻辑 |
| `progressive_md.json` | — | MD 拆分方案 + 加载协议 | 不含文件操作 |
| `_index.json` | — | 模块注册表 + 依赖关系 | 不含具体规范 |

**模块依赖关系**：
```
_index.json → frontmatter.json → rules.json
           → body.json
           → structure.json → progressive_md.json
```

---

## 九、关键流程总结

### 9.1 标准化工作流（按模式分述）

> **⚠️ 本技能无 git-sync 依赖**。标准化工作流到 bump + cleanup 即终止，不涉及 git 推送/CRLF 验证。git-sync 是独立技能，与本技能已解耦。

#### audit 模式（仅审查，只读）

```
用户请求："检查/审计/评估这个 skill"
  ↓
Step 0 模式识别 → 匹配 audit 关键词
  ↓
读取目标 skill 的 SKILL.md
  ↓
执行 R-01~R-26 全量审计
  ↓
输出审查报告（PASS/WARN/FAIL），逐条列出通过/失败/跳过
  ↓
[--fix 时] 自动修正可修复项（frontmatter/版本号/数据目录/反模式/FAQ 等 20+ 条规则）
  ↓
[--verify 时] 输出编号 FAIL 条目 [#ID]，每条含独立问题描述
  ↓
[--show-fix ID1,ID2] 获取真问题修复指引
```

#### update 模式（轻量更新，含细碎审计循环）

```
用户请求："更新/修复/升级这个 skill"
  ↓
Step 0 模式识别 → 匹配 update 关键词 → 语义确认
  ↓
[步骤 1] 蓝皮书扫描 — inspect_skill(skill_dir) 输出结构快照
  ↓
[步骤 2] 更新声明（流程钩子 — 强制）
  LLM 必须输出：{"changed_files": [...], "description": "..."}
  ↓
[步骤 3] 针对性审计 — 只跑跟 changed_files 相关的规则
  ↓
[步骤 4] ★★★ 修复 + 细碎审计循环 ★★★
  ┌─────────────────────────────────────────────┐
  │ LLM 修一批/一类/一个问题                      │
  │   ↓                                          │
  │ ★ 细碎钩子触发 ★                              │
  │ LLM 声明 fixed_rules：{"fixed_rules": [...]} │
  │   ↓                                          │
  │ 代码自动跑针对性审计（filter_rules=...）       │
  │   ↓                                          │
  │ 还有 FAIL？→ 继续修                           │
  │ 全部 PASS？→ 退出循环                         │
  └─────────────────────────────────────────────┘
  ↓
[步骤 5] 全量审计确认 — 还有 FAIL？→ 回到步骤 4
  ↓
[步骤 6] 针对性一致性审查 + 修复（只审 changed_files）
  ↓
[步骤 7] 输出报告 → bump (PATCH) → cleanup
```

#### refactor 模式（全量改造，含细碎审计循环）

```
用户请求："改造/重构/标准化这个 skill"
  ↓
Step 0 模式识别 → 匹配 refactor 关键词 → 语义确认
  ↓
[步骤 1] 蓝皮书扫描 — inspect_skill(skill_dir) 输出结构快照
  ↓
[步骤 2] 备份 — zip 到 .standardization/<skill>/backup/pre_refactor_<timestamp>.zip
  ↓
[步骤 3] 全量审计 — R-01~R-26 全量跑 + LLM 二次筛除
  ↓
[步骤 4] ★★★ 修复 + 细碎审计循环 ★★★
  ┌─────────────────────────────────────────────┐
  │ LLM 修一批/一类/一个问题                      │
  │   ↓                                          │
  │ ★ 细碎钩子触发 ★                              │
  │ LLM 声明 fixed_rules：{"fixed_rules": [...]} │
  │   ↓                                          │
  │ 代码自动跑针对性审计（filter_rules=...）       │
  │   ↓                                          │
  │ 还有 FAIL？→ 继续修                           │
  │ 全部 PASS？→ 退出循环                         │
  └─────────────────────────────────────────────┘
  ↓
[步骤 5] 全量审计确认 — 双 0 验证（全量跑，还有 FAIL → 回到步骤 4）
  ↓
[步骤 6] 全量一致性审查 + 修复（全量检查文档-代码一致性）
  ↓
[步骤 7] 输出报告 → bump (FEATURE) → cleanup（end_session 驱动）
```

### 9.2 update 模式完整步骤

1. `start_session(skill_dir, "update")` — 创建 manifest（v2.80.0 修复）
2. `_create_backup(skill_dir, "update", workspace)` — 时间戳完整备份
3. `skill_inspector.inspect_skill(skill_dir)` — **强制**输出结构蓝皮书
4. **更新声明（流程钩子）** — LLM 输出 `{"changed_files": [...], "description": "..."}`
5. **针对性审计** — `audit_skill(skill_dir, filter_files=changed_files)`，只跑相关规则
6. **★★★ 细碎审计循环 ★★★** — `_run_audit_loop()`：
   - LLM 修一批 → 声明 `fixed_rules`
   - 代码自动跑 `audit_skill(skill_dir, filter_rules=fixed_rules)`
   - 还有 FAIL → 继续修；全部 PASS → 退出循环
7. **全量审计确认** — `audit_skill(skill_dir)` 全量跑，双 0 验证
8. **针对性一致性审查** — 只审 changed_files 涉及的文档-代码一致性
9. `_bump_version()` — 版本号自动更新（patch）
10. `end_session()` — Manifest 驱动清理

### 9.3 refactor 模式完整步骤

1. `start_session(skill_dir, "refactor")` — 创建 manifest，注册备份 zip 路径（v2.80.0 修复）
2. `_create_backup(skill_dir, "refactor", workspace)` — 强制备份
3. `skill_inspector.inspect_skill(skill_dir)` — **强制**输出结构蓝皮书
4. **全量审计** — `audit_skill(skill_dir)` 全量跑 + LLM 二次筛除
5. **★★★ 细碎审计循环 ★★★** — `_run_audit_loop()`：
   - LLM 修一批 → 声明 `fixed_rules`
   - 代码自动跑 `audit_skill(skill_dir, filter_rules=fixed_rules)`
   - 还有 FAIL → 继续修；全部 PASS → 退出循环
6. **全量审计确认** — 双 0 验证（全量跑，还有 FAIL → 回到步骤 5）
7. **全量一致性审查 + 修复** — 全量检查文档-代码一致性（最多3轮重试）
8. `bump` — 版本号自动升级（feature）
9. `end_session()` — Manifest 驱动清理

### 9.4 审计结果判定

| 结果 | 含义 |
|:----:|------|
| **PASS** | 全部规则通过 |
| **WARN** | 仅 WARN 级未通过 |
| **FAIL** | 含 ERROR 级未通过 |

**审计报告格式**：
```
=======================================================
  审查结果: <skill-name> — PASS / WARN / FAIL
=======================================================
  总计: 26 | 通过: N | 失败: N | 跳过: N

规则ID     严重度     状态     详情
------------------------------------------------------
R-01     E       [OK]   发现 YAML frontmatter...
R-26     W       [OK]   文档声明规范检查通过...

───────────────────────────────────────────────────────
  🛠️ 提示：发现可修复问题时...
```

**误报分类机制**：`_reclassify_false_positive()` 在审计运行时自动过滤已知误报模式（如系统工具名被误检为函数名），过滤后的项显示为 `ⓘ 已排除`，不计入 WARN/ERROR 统计。

### 9.5 bump 子命令

一键升级技能版本号三端：

```bash
python -m scripts.skill_audit bump <skill-dir> --type fix       # patch 升级
python -m scripts.skill_audit bump <skill-dir> --type feature   # minor 升级
python -m scripts.skill_audit bump <skill-dir> --type breaking  # major 升级
```

`audit --fix` 模式修复文件后自动执行 patch bump，changelog 写入实际修复规则名而非空话。

### 9.6 inspect 子命令

结构无关的全量扫描工具，输出技能蓝皮书：

```bash
python -m scripts.skill_inspector <skill-dir>
python -m scripts.skill_inspector <skill-dir> --json   # JSON 格式
```

**inspect 扫描产出明细**：
- 结构标准化判定：标准（scripts/ + references/）/ 半标准 / 非标准
- 元信息：SKILL.md 行数、## 章节数量及标题列表、_meta.json 字段清单
- 文件清单：按扩展名分组计数
- 非标位置标记：每个不在 scripts/ 下的 .py 文件、不在 references/ 下的 .md 文件均标注
- 功能清单：每个 .py 文件的 def 函数名和 class 类名列表
- 引用概览：每个 .md 文件的行数和 ## 章节标题
- 安全数据：sensitive_access / critical_write / permission_weight / data_dir 声明值

---

## 十、铁律8：全报告 LLM 细筛

审计报告（`run_audit audit`）输出后，LLM **必须**逐条阅读每条结果。

审计输出已包含行号、上下文、问题描述，信息完整。`_reclassify_false_positive()` 已在 Python 侧自动过滤已知误报模式，过滤后的剩余项由 LLM 终审判断：

- **真问题** → 立即修复
- **新误报模式** → LLM 直接放过，后续由开发者按需补充

LLM **禁止**跳过终审步骤，也**禁止**将应修复的真问题解释为误报放任不管。全报告处理完毕后，才能进入铁律9验证。

**v2.62.0 变更**：`_reclassify_false_positive()` 仅用于报告显示标记（ⓘ），**不影响 exit code**。所有 FAIL 项全量输出给 LLM。

---

## 十一、铁律9：0 ERROR 0 WARN 强制验证

`audit --verify` 在 LLM 细筛完成后执行：

1. 运行完整审计 R-01~R-26
2. 不设白名单预筛——所有 FAIL 项全量输出
3. LLM **必须**逐条审查所有 FAIL 项（含上下文），语义判断即误报依据
4. 有非误报的未通过项 → exit(1)，输出每项 rule_id + detail
5. 全部通过或仅误报 → exit(0)

exit code 是 LLM 无法忽略的信号。非零退出码意味着验证绝对失败，LLM **不得**声称"审计通过"。

**v2.62.0 设计理由**：
- 之前：白名单匹配的误报提前过滤，LLM 只看"剩余项"——可能漏看边界误报
- 之后：LLM 逐条审查所有 FAIL 项，语义判断即误报依据，无需匹配白名单

---

## 十二、关键版本变更摘要（v2.73.2 → v2.80.0）

| 版本 | 核心变更 |
|------|---------|
| 2.73.3 | 清理 `_dead_code_backup/`（50+死文件）；新增 `scripts/log.py` 共享日志模块；print→logging；异常处理 |
| 2.73.4 | R-11 动态路径检测增强（`os.path.join` 跨技能污染） |
| 2.73.8 | R-12 log.py 路径违规修复；safe_io.py Windows 写入权限 3次重试；changelog 方括号格式统一 |
| 2.73.9 | R-15 permissions.md 自动填充（PermissionChecker.scan() 驱动）；新增占位符检测 |
| 2.75.0 | 删除 blueprint 参数/废弃别名/清理 creator.py blueprint 注入 |
| 2.76.0 | 流程钩子代码级强制+更新声明+一致性审查增强+规则编号迁移+修复循环（P0-3 P1-5 P2-8）。**细碎审计循环代码级实现**：`_run_audit_loop()` 通用修复循环、`_validate_changed_files()` 更新声明校验、`--fixed-rules` CLI 参数 |
| 2.77.0 | 自改造验证：修复 R-10 changelog 正则 + R-15 占位符检测 bug + _filter_false_positives 遗漏 |
| 2.78.0 | 一致性审查闭环重构：误判过滤+自动修复+细碎钩子，流程调整为 bump→报告 |
| 2.79.0 | 修复 outdated_rule_ref 方向（以实际技能为准而非 rules.json），修复误改 R-26→R-25 |
| 2.80.0 | log.py 数据目录路径修复；R-11 .standardization 白名单移除；cmd_refactor cleanup 修复（start_session/end_session 驱动） |

---

> 本文档基于 skill-standardization v2.80.0 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
