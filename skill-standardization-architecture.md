# skill-standardization 架构与规范体系文档

> 完整解读 v2.58.1 版的架构设计、审查规则体系、标准化执行流程与修复体系  
> 生成时间：2026-06-02（v2.58.1 最新更新）

---

## 一、系统概览

skill-standardization 是一个 **Skill 全生命周期标准化管理工具集**，围绕以下闭环运行：

```
规范定义（spec/*.json）
  → 构建器（skill_builder: create / update / refactor）
    → 审查器（skill_audit: R-01 ~ R-25）
      → 修复器（fix.py: 自动修复各规则问题）
        → git-sync 集成（推送前自动审查）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI | 人类可读的文档和命令行交互 |
| **业务层** | skill_builder / skill_audit / fix.py | 创建/更新/改造/审查/修复的核心逻辑 |
| **数据层** | json_loader + spec/*.json | 按需加载的标准化规范定义 |

### 1.2 目录结构

```
skill-standardization/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据（name/version/description/author/tags/data_dir/triggers）
├── references/                 # 渐进式文档
│   ├── guide.md                # 完整使用教程
│   ├── architecture.md         # 架构设计
│   ├── reference.md            # API/命令参考手册
│   ├── antipatterns.md         # 13 条反模式
│   ├── data_dir_map.md         # 数据目录路径引用对照表
│   ├── faq.md                  # 常见问题
│   └── changelog.md            # 版本更新日志
└── scripts/                    # 核心脚本
    ├── skill_builder/          # 构建器包（OO 重构）
    │   ├── __init__.py         # 主入口 + argparse
    │   ├── creator.py          # SkillCreator（create 模式）
    │   ├── updater.py          # SkillUpdater（update 模式）
    │   ├── refactor.py         # Refactor（refactor 模式）
    │   ├── version_manager.py  # VersionManager
    │   ├── migrator.py         # SkillMigrator（migrate-data 命令）
    │   └── utils.py            # 工具函数
    ├── skill_audit/            # 审查器包（OO 重构）
    │   ├── __init__.py         # 主入口 + audit_skill()
    │   ├── frontmatter_checker.py  # R-01~R-05（含 _meta.json 字段检查）
    │   ├── structure_checker.py    # R-06~R-09, R-18~R-25 正文结构检查
    │   ├── artifact_checker.py     # R-11~R-12
    │   ├── permission_checks.py    # R-13~R-17
    │   ├── data_dir_checker.py     # R-22 数据目录合规检查
    │   ├── progress_manager.py     # 进度管理器
    │   ├── fix.py              # 自动修复函数（30+ 规则）
    │   └── utils.py            # 工具函数
    ├── json_loader.py          # 渐进式 JSON 加载器
    ├── skill_inspector.py      # 技能结构蓝皮书生成器
    ├── permission_checker.py   # 权限检查器
    ├── authorization_manager.py# 授权管理器
    ├── cleanup_manager.py      # manifest 驱动临时文件清理
    └── safe_io.py              # 安全文件写入（原子写入+备份）
    ├── op_logger.py            # 操作日志记录
    ├── op_logger_patch.py      # 操作日志补丁
    ├── run_audit.py            # 独立审计入口
    ├── update_all_versions.py  # 全版本更新
    ├── update_skill_frontmatter.py # frontmatter 更新脚本
    ├── restore_from_gitee.py   # 从码云恢复
    └── spec/                   # 规范定义（JSON Schema）
        ├── _index.json         # 模块注册索引
        ├── frontmatter.json    # Frontmatter 字段规范 v2.5.0
        ├── body.json           # 正文章节结构规范
        ├── rules.json          # 审查规则完整定义
        ├── structure.json      # 目录结构规范 v2.5.0
        └── progressive_md.json # 渐进式 MD 体系规范
```

### 1.3 三层章节体系（section_tiers）

SKILL.md 的 ## 章节分为三个层级，决定其存留行为和拆分优先级：

| 层级 | 包含章节 | 行为 |
|------|---------|------|
| **① must_have** | H1/约束/触发条件/核心能力/工作流程 | 永远留在 SKILL.md，不拆分 |
| **② whitelist.optional_progressive** | 快速开始/配置/反模式/FAQ/API/示例/限制/铁律 | 可留，超230行时优先拆到 references/ |
| **②' whitelist.always_progressive** | 版本日志/更新日志/Changelog | 强制在 references/，SKILL.md 只能有引用（R-24） |
| **③ nonstandard** | 不在①②的所有H2 | Phase 1 粗筛 rarr; Phase 2 精筛：合并 or 拆分 |

**渐进式索引表**：所有标准技能的 ## 核心能力 末尾应包含 ### 渐进式文件索引 表格（文件名/位置/说明），集中列出所有 references/*.md。C-13 审计完整性，C-15 审计正文重复引用。

### 1.4 三种执行模式

| 模式 | 命令 | 作用 | 风险等级 |
|------|------|------|---------|
| **create** | `skill_builder create <name>` | 从模板创建标准的 skill 骨架 | 🟢 无害 |
| **update** | `skill_builder update <dir> [--fix]` | 增量检查 + 可选修复 | 🟡 轻度修改 |
| **refactor** | `skill_builder refactor <dir> [--dry-run]` | 整体结构改造（移动文件） | 🔴 必须先 dry-run |

此外，审计模式可通过 `python -m scripts.skill_audit audit <dir>` 独立运行。

---

## 二、完整审查规则体系（R-01 ~ R-25）

25 条规则按用途分为 7 大类别，严重度分为 **ERROR**（必须修）和 **WARN**（建议修）两级。

### 2.1 类别 A：Frontmatter 结构（R-01 ~ R-05）

**目的**：确保每个 skill 有完整可解析的 YAML frontmatter，字段齐全、命名规范。R-01 合并了 _meta.json 7 字段检查。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-01** | ERROR | YAML frontmatter 存在性 + 字段完整性 + **_meta.json 7 字段检查**（合并） | 文件以 `---` 开头并包含闭合 `---`；11 required + 2 conditional 字段分层检查；_meta.json 7 标准字段完整 |
| **R-02** | ERROR | `name` 字段 | frontmatter 含 `name:`，值非空字符串 |
| **R-03** | ERROR | `version` 字段 | 值符合 SemVer 格式（x.y.z） |
| **R-04** | ERROR | `description` 字段 | 含 `description:`，值非空 |
| **R-05** | WARN | name = 目录名 | frontmatter 的 name 与所在目录名一致 |

**Frontmatter 字段分层体系**：
- **11 required**：name/version/description/author/license/tags/data_dir/external_data_dir/sensitive_access/critical_write/permission_weight
- **2 conditional**：trigger/trigger_negative（正文有触发词/否定条件时必填）
- **4 optional**：references/category/priority/deprecated

**非标字段处理策略**：
- **_meta.json 非标字段**：审计阶段标记并提示"需人工判断删/迁移"（WARN）；`--fix` 自动修复时直接删除（_meta.json 是机器元数据，应保持严格一致）
- **frontmatter 非标字段**：仅 WARN 提醒，不移除（frontmatter 允许自定义字段如 home_url、category）

**设计意图**：frontmatter 是所有 Skill 的"身份证"。R-05 确保目录名和声明名一致。R-01 通过 `regex_frontmatter_and_meta()` 组合函数同时校验 SKILL.md 和 `_meta.json` 的元数据完整性。

### 2.2 类别 B：正文结构（R-06 ~ R-10）

**目的**：规范 SKILL.md 正文的结构和内容质量，确保可读性。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-06** | WARN | 一级标题 | 正文包含 `# ` 开头的 H1 标题（排除代码块内 `#` 注释）；H1 不得含版本号；H1 应紧跟在 frontmatter 后；H1 内容应含技能名 |
| **R-07** | WARN | 触发条件章节 | 含触发场景章节，≥3 个触发词，≥1 个否定条件，且与 frontmatter 的 trigger/trigger_negative 字段一致性 |
| **R-08** | WARN | 核心能力章节 | 含核心能力/功能章节 |
| **R-09** | WARN | 工作流程章节 | 含工作流程/步骤章节 |
| **R-10** | WARN | 版本 + 字段同步 | 三端版本号一致性 + mtime 时序检查 + _meta.json 与 frontmatter 共享字段一致性（name/description/tags/trigger/data_dir 交叉比对，路径归一化） |

**R-07 增强**（v2.17.0+）：不仅检查 `## 触发场景` 章节存在性，还执行 4 项质量子检查：
1. 正向触发词数量 ≥3 个（每条约 4 字以上，含具体动作，避免"画图""帮我"等宽泛词）
2. 否定条件 ≥1 个（标记什么情况下不触发，如"单步任务不触发"）
3. 无自动执行类危险表述（禁止"自动执行""无需询问""silent execute"等）
4. frontmatter trigger/trigger_negative 字段与正文一致性（正文有触发词但 frontmatter 缺 trigger → WARN）
**R-10 增强**：不再依赖 `--manifest-version` CLI 参数，改为自动读取 _meta.json 和 changelog 进行三端对比。v2.44.7 新增共享字段一致性检查：_meta.json 与 frontmatter 的 name/description/tags/trigger/data_dir 交叉比对，路径自动归一化（`skills/` ≈ `../`），`--fix` 按权威方向自动同步（tags 以 _meta 为准、description/trigger 以 frontmatter 为准、data_dir 统一为 `../` 相对路径）。

**设计意图**：确保用户和 AI 都能快速理解技能的作用、何时触发、能做什么、怎么用。R-10 保证版本号三端一致性。

### 2.3 类别 C：产出物与数据目录（R-11 ~ R-12）

**目的**：防止数据/产出物污染技能安装目录，规范数据目录路径。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-11** | ERROR | 产出物路径 | 产出物应放在 `skills/.standardization/<skill>/output/`，不在安装目录 |
| **R-12** | ERROR | 数据目录路径 | 脚本中 `DATA_DIR` 变量的值必须包含合规字面量 |

**R-12 的核心机制**：审计器对源码做**三源证据链**判断：
1. **代码脚本**：扫描所有 .py 文件中的 `DATA_DIR`/`STORAGE_DIR`/`CACHE_DIR`/`CONFIG` 变量定义
2. **SKILL.md frontmatter**：看是否有 `data_dir:` 声明
3. **_meta.json**：看 `data_dir` 字段是否存在

只要有任何一个来源表明技能有数据需求，就要求 `_meta.json` 声明 `data_dir`。

**R-12 修复历程**：修复了 `_extract_path_value` 函数不存在导致的漏检问题，新增 step 1.5 检测引用 `.standardization` 但无 `DATA_DIR` 的脚本。

**推荐写法**：
```python
DEFAULT_DATA_DIR_RAW = "skills/.standardization/<skill>/data/"  # R-12 审计锚点
_data_dir_abs = os.path.normpath(os.path.join(SKILL_ROOT, "..", DEFAULT_DATA_DIR_RAW))  # 运行时路径
```

**设计意图**：隔离安装目录和数据目录。安装目录只保留 SKILL.md + scripts/，所有运行时产生的数据（缓存、日志、输出文件）放在 `.standardization/` 下。升级 skill 时只会覆盖安装目录，数据不丢失。

### 2.4 类别 D：安全与权限（R-13 ~ R-17）

**目的**：确保 skill 声明的权限与实际行为一致，防止未经授权的敏感操作。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-13** | WARN | 敏感信息访问 | 若脚本读取 memory/credentials/token → frontmatter 须声明 `sensitive_access: true` |
| **R-14** | WARN | 关键位置写入 | 若写入 skills/系统目录 → 须声明 `critical_write: true` |
| **R-15** | ERROR | 高权限风险说明 | 脚本含高/严重风险操作时，`references/permissions.md` 须有风险说明 |
| **R-16** | WARN | 权限权重说明 | 建议在 SKILL.md 或 references/ 中说明各操作的权限权重 |
| **R-17** | ERROR | 渐进加载引用 | SKILL.md > 230 行时必须拆分 whitelist 章节到 references/；非标准 H2 章节 Phase 1 正则粗筛 → Phase 2 LLM 精筛 |

**设计意图**：让用户在安装技能前就能了解其风险。R-15 要求高风险操作必须附带说明文档，R-17 强制大文件必须分解以保持加载效率。v2.45.0 扩展为非标章节两阶段检测（正则粗筛+LLM精筛），阈值放宽至 230 行。

### 2.5 类别 E：质量规范（R-18 ~ R-21）

**目的**：提升技能文档的内容质量，避免模糊、空洞的表述。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-18** | WARN | 反模式具体性 | 强制渐进式，检查 `references/antipatterns.md` 引用、文件存在性、内容质量（≥2 条具体示例 + 错误做法/正确做法标记） |
| **R-19** | WARN | FAQ 有意义性 | 强制渐进式，检查 `references/faq.md` 引用、文件存在性、Q&A 质量（≥3 对 + 问题≥10字 + 答案≥15字） |
| **R-20** | WARN | 写作规范 | 术语统一、无模糊词（可能/大概）、中英文混排空格、脚本调用验证 |
| **R-21** | WARN | 渐进式加载说明 | 核心能力/工作流程章节中包含固定模板句 |

**R-20 两阶段检查协议**：
1. **第一阶段**（正则粗筛）：扫描所有 `.md` 文件，找出疑似中英文混排间距问题
2. **第二阶段**（LLM 精筛）：AI 对正则匹配结果逐条判断，过滤代码标识符误报

**R-21 固定模板句**：
```
> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。
```

**设计意图**：这四个规则解决"这个技能不好用"的根本原因——文档质量。R-18 教用户避免常见坑，R-19 确保 FAQ 真正有用，R-20 统一可读性标准，R-21 让 AI 知道文档是渐进式加载的。

### 2.6 类别 F：合规与维护（R-22 ~ R-24）

**目的**：确保技能符合数据目录规范、文档与代码一致、更新日志规范。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-22** | WARN | 数据目录合规 | 检查安装目录是否混入应属数据目录的文件（如 cache/temp/backup），R-12 审计锚点变量 + 数据目录迁移 |
| **R-23** | WARN | 文档-代码一致性 | SKILL.md 引用的脚本/文件真实存在，调用方式一致；新增第 6 项路径一致性检查（正文路径与 data_dir 一致）、第 7 项外部技能引用检查 |
| **R-24** | WARN | 更新日志规范 | changelog 在 `references/changelog.md`，根目录无 `CHANGELOG.md` |

**R-23 七项检查内容**：
1. SKILL.md 引用的脚本/文件真实存在
2. 代码示例中的调用方式与实际代码一致
3. 引用的函数名/类名真实存在
4. 脚本路径引用正确
5. 命令行示例可运行
6. **正文路径与 frontmatter data_dir 一致性**：当 data_dir 包含 `.standardization/` 时，检测正文中缺少 `.standardization/` 层级的路径
7. **外部技能引用检查**：扫描 MD 中引用的技能路径，引用不存在的技能时 WARN

### 2.7 类别 G：文档写作格式（R-25 v2.58.1 含 C-01~C-15 十五项子检查）

**目的**：统一 SKILL.md 的写作格式，提供标准化的排版建议。R-25 整体为 WARN 级，其 14 项子检查中 C-01 为 ERROR 级（仅作内部参考，不提升规则总体级别），其余均为 WARN 建议级。

| 编号 | 级别 | 检查项 | 说明 |
|:----:|:----:|--------|------|
| C-01 | ERROR | H1 标题格式 | 必须为 `# <技能名>`，不得含版本号（版本号由 version 字段管理） |
| C-02 | WARN | 标题层级 | 限制在 `##` 和 `###`，不应出现 `####+` |
| C-03 | WARN | 表格使用 | 结构化信息应使用表格展示 |
| C-04 | WARN | 引用块使用 | 提示/注意/警告应使用 `>` 引用块包装 |
| C-05 | WARN | 列表区分 | 有序列表用于步骤流程，无序列表用于选项列举 |
| C-06 | WARN | 加粗使用 | 关键术语/约束/规则名使用 `**加粗**` 强调 |
| C-07 | WARN | 语言标识 | 代码块应带语言标识（` ```bash `、` ```python `） |
| C-08 | WARN | Checklist | 操作前自检使用 `- [ ]` checklist 格式（带行号+触发词） |
| C-09 | WARN | 渐进引用 | 引用渐进式文件统一使用 `→ 详见 references/xxx.md` |
| C-10 | WARN | 空行规范 | frontmatter 闭合后 ≤2 个连续空行；正文 ≤4 个连续换行 |
| C-11 | WARN | 章节顺位 | H2 章节出现顺序应与 body.json section_order 一致（v2.45.0） |
| C-12 | WARN | 格式合规 | 每个 H2 章节使用的格式应与 body.json content_format 定义一致；从 guidelines 提取语义要求转 LLM Phase 2（v2.45.0） |
| C-13 | WARN | 渐进式索引表 | 核心能力章节末尾应包含 渐进式文件索引 表（列：文件名/位置/说明），references/ 文件未列出时报 WARN（v2.45.0） |
| C-14 | WARN | 工作流程完整性 | 工作流程步骤数 + 混入版本标记检测 → LLM Phase 2 确认覆盖率（v2.45.0） |
| C-15 | WARN | 内容冗余检测 | 索引表引用重复(15a) + H1后独立引用(15c) + 章节标题近似重叠(15d), rarr; LLM Phase 2（v2.58.1） |

**冲突排除矩阵**：

| 现有规则 | 冲突点 | 处理方式 |
|---------|--------|---------|
| R-06 | 均检查 H1 | R-06 查存在性（WARN），C-01 查格式（ERROR），互补不冲突 |
| R-21 | 渐进式加载模板句含 `>` 引用 | C-02/C-04 不检查该模板句的格式 |
| R-24 | 更新日志章节可能在 references/ | C-02 不约束更新日志位置 |
| R-18/R-19 | 反模式/FAQ 须渐进式引用 | C-09 不约束已有强制规范的引用 |

### 2.8 规则汇总统计

| 类别 | 包含规则 | ERROR | WARN | 目的 |
|------|---------|:-----:|:----:|------|
| A. Frontmatter | R-01~R-05 | 4 | 1 | 技能身份标识 + _meta.json 字段完整性（R-01 合并） |
| B. 正文结构 | R-06~R-10 | 2 | 3 | 文档结构和质量（R-07、R-10 为 ERROR） |
| C. 产出物与目录 | R-11~R-12 | 2 | 0 | 目录隔离和数据安全 |
| D. 安全与权限 | R-13~R-17 | 2 | 3 | 权限声明和风险控制（R-15、R-17 为 ERROR） |
| E. 质量规范 | R-18~R-21 | 0 | 4 | 内容质量和可读性 |
| F. 合规与维护 | R-22~R-24 | 0 | 3 | 长期维护一致性 |
| G. 写作格式 | **R-25** | 0 | 1 | 文档排版统一建议（16 项子检查仅 C-01 为 ERROR 级，其余均 WARN） |
| **合计** | **R-01~R-25** | **10** | **15** | |

---

## 三、核心设计原则

### D1: 零外部依赖
所有脚本仅使用 Python 标准库（pathlib, json, re, argparse 等），零 pip install。
**目的**：降低安装门槛，提高跨平台兼容性，减少供应链风险。

### D2: 纯警告模式
审查结果不阻断工作流——即使 ERROR 也始终 exit(0)，git-sync 不会因此停止。
**目的**：Skill 开发是迭代过程，初期不规范是正常的。阻断会导致开发者关闭审查。

### D3: 信息零遗漏
refactor 模式绝不删除任何文件——只执行 `move` 操作，执行前强制备份，执行后验证字节一致性。
**目的**：Skill 包含用户自定义的有价值文件，即使不符合规范也不应丢失。

### D4: 渐进式加载
SKILL.md 是轻量入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。
规范定义也遵循此原则——json_loader 只在请求时才读取对应的 spec JSON 文件。
**目的**：减少一次性加载的上下文开销，让 AI 和人类都能快速理解 skill 的核心信息。

### D5: 模板驱动
create 使用硬编码字符串模板（当前），未来可能支持外部模板文件。
**目的**：简单直接，无额外抽象，易于理解和自定义。

### D6: 备份优先 + Inspect 先读全
任何修改性操作（update --fix, refactor）在执行前均强制备份，带时间戳命名。
备份后、改造前**强制运行 skill_inspector** 结构扫描，输出技能蓝皮书（元信息、目录树、章节、函数清单、引用概览、安全数据），确保 AI/开发者了解全貌后再动手。
**目的**：备份确保可回滚；inspect 确保不遗漏文件或功能，避免"AI 读哪算哪导致的改造遗漏"。

---

## 四、强制约束与编程规范

### 4.1 版本号三端一致规则

版本号变更时必须同步更新以下 **3 处**，缺一不可：

| # | 文件 | 字段/位置 |
|---|------|-----------|
| 1 | `SKILL.md` frontmatter | `version:` 字段 |
| 2 | `_meta.json` | `"version"` 字段 |
| 3 | `references/changelog.md` | 版本条目 |

`update --fix` 已自动执行上述三端同步。`bump` 子命令可一键升级版本号三端。

### 4.2 文件更新约束

所有 `.md` 文件**禁止使用 Write/Edit 工具更新**（会损坏 UTF-8 中文编码），必须用 Python 脚本原子写入（`tmp + os.replace()`）：

| 文件 | 更新方式 | 使用脚本 |
|------|----------|---------|
| `SKILL.md` frontmatter | Python 原子写入 | `update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 原子重写 | `safe_io.py` 的 `safe_write()` |
| `references/*.md` | safe_io.py 的 `safe_write()` | 随技能自带 |
| 更新日志 | Python 合并脚本 | 每次发版统一维护 `references/changelog.md` |

**CRLF 编码约束**（铁律）：`SKILL.md` 必须使用 CRLF 换行符（Windows 风格）。git-sync 推送到仓库前需验证换行符状态。使用 `sync_with_exclude.py` 进行同步时，CRLF 不会被自动转换，需人工确认。

### 4.3 工具自动保障（无需人工确认）

以下事项已由工具链自动保障，不再需要人工逐项检查：

| 事项 | 保障方式 |
|------|---------|
| .md 文件写入 | `safe_io.py` 原子写入（`tmp + os.replace()`）替代 Write/Edit |
| 更新日志维护 | `bump` 子命令自动插入 `references/changelog.md` 条目 |
| CRLF 编码 | `git-sync` 推送前自动验证换行符 |
| 自审状态 | `bump` 后自动触发审计；`git-sync` 推送前再次验证 |
| 版本号三端一致 | `bump` 子命令自动同步 SKILL.md / _meta.json / changelog |
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
# ✅ 正确写法：变量名含 DATA，值含合规字面量
DEFAULT_DATA_DIR_RAW = "skills/.standardization/<skill-name>/data/"
_data_dir_abs = os.path.normpath(os.path.join(SKILL_ROOT, "..", DEFAULT_DATA_DIR_RAW))

# ❌ 错误写法：运行时计算路径，审计匹配不到
DATA_DIR = os.path.normpath(os.path.join(SKILL_ROOT, "..", "skills/.standardization/.../data/"))
```

变量名必须含 `DATA|STORAGE|DB|CACHE|CONFIG` 之一才能被审计匹配。推荐使用 `DEFAULT_DATA_DIR_RAW` + `_data_dir_abs` 双变量模式。

---

## 五、反模式速查表

预注册反模式，按影响级别分级：

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
| `fix_writing_standards(skill_dir)` | R-20 + R-18 | 统一术语 + 反模式格式修正（`**错误做法**：`→`**错误做法：**`） |
| `fix_data_dir_compliance(skill_dir)` | R-22 | 添加 data_dir 声明 |
| `fix_doc_code_consistency(skill_dir)` | R-23 | 修复文档-代码一致性 |
| `fix_split_nonstandard(skill_dir)` | R-17 | 非标章节拆分到 references/（v2.45.0） |
| `fix_section_order(skill_dir)` | R-25 C-11 | 按 body.json section_order 重排章节（v2.45.0） |
| `fix_section_constraint(skill_dir)` | must_have | 从目标技能脚本采集约束词生成 ## 约束（v2.46.0） |
| `fix_progressive_index_table(skill_dir)` | C-13 | 从 references/ 扫描文件名+H1 生成索引表，操作后自动同步（v2.46.0） |
| `fix_reclassify_section(skill_dir, action, section_title, target_section)` | R-17 Phase 3 | 通用非标归类：merge(降级###)/split(拆到refs)/delete(删除), 参数驱动（v2.47.0） |
| `fix_artifact_paths(skill_dir)` | R-11 | 修复产出物路径 |
| `fix_external_data_dir(skill_dir)` | R-12 | 修复外部数据目录 |
| `fix_sensitive_access(skill_dir)` | R-13 | 添加敏感信息访问声明 |
| `fix_critical_write(skill_dir)` | R-14 | 添加关键位置写入声明 |
| `fix_create_permissions_md(skill_dir)` | R-15 | 创建 permissions.md |
| `fix_permission_weight(skill_dir)` | R-16 | 添加权限权重说明 |
| `fix_frontmatter_fields(skill_dir)` | R-01 | 补全 frontmatter 字段（required→conditional 分层补全） |
| `fix_meta_field_sync(skill_dir)` | R-10 | 同步 _meta.json 与 frontmatter 共享字段（tags/description/trigger/data_dir） |
| `fix_meta_json_completeness(skill_dir)` | R-01（合并） | 补全 _meta.json 7 标准字段，标记非标字段供人工判断 |
| `fix_missing_data_dir(skill_dir)` | R-12 | 为引用 .standardization 但缺少 DATA_DIR 的脚本补上声明 |

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
- `fix_reclassify_section`：参数驱动（action/section_title/target_section），不写死任何章节名

`audit --fix` 执行完毕后，终端输出 fix_details 机器名列表，并强制提示 AI 将其转化为可读 changelog 描述用 safe_io 写入 references/changelog.md。

**自动同步机制**（v2.47.0+）：`fix_reclassify_section` 和 `fix_split_nonstandard` 执行后自动调用 `fix_progressive_index_table` 刷新索引表，保证 references/ 新增文件立即出现在索引表中。

---

## 七、与 git-sync 的协作（已解耦）

> **注意**：`skill-standardization` 与 `git-sync` 已完全解耦。以下仅说明集成关系作为架构参考。

```
git-sync 执行时
  ├─ 步骤 3.5: skill_audit.py audit ← 可选调用（非强制）
  └─ 审计纯警告模式，不阻断同步
```

审计功能是独立的——即使没有 git-sync，审计器也能单独运行。两个技能各自维护，互不依赖。git-sync 不再包含对 skill-standardization 的引用描述。

---

## 八、规范定义体系（spec/*.json）

| 文件 | 版本 | 职责 | 不包含 |
|------|------|------|-------|
| `frontmatter.json` | v2.5.0 | 定义 11 required + 2 conditional + 4 optional 字段，含非标字段处理策略 | 不含验证逻辑 |
| `body.json` | — | 定义章节名/层级/必须性 | 不含写作指导 |
| `rules.json` | — | 完整规则定义（ID/级别/逻辑） | 不含执行引擎 |
| `structure.json` | v2.5.0 | 目录结构规范，说明 _meta.json 严格 7 字段 + frontmatter 可含自定义字段 | 不含移动逻辑 |
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

### 标准化工作流

```
用户提出审计/改造需求
  ↓
AI 加载 skill-standardization
  ↓
读取目标 skill 的 SKILL.md
  ↓
[update/refactor 模式] 备份 → ★ inspect 强制前置扫描
  ↓
执行 audit（R-01~R-25）或 update/refactor 后续步骤
  ↓
输出审查报告（PASS/WARN/FAIL），逐条列出通过/失败/跳过
  ↓
**铁律8**：LLM 逐条阅读审计结果，真问题修复，误判标记通过
  ↓
调用 fix.py 自动修复（如有 --fix），按规则 ID 分派
  ↓
**铁律9**：`audit --verify` 强制验证 0 ERROR 0 WARN
  ↓
更新版本号（三端同步 + changelog 自动追加）
  ↓
git-sync 推送前验证 CRLF + 自审状态
```

**update 模式完整步骤**：
1. `_create_backup(skill_dir, "update", workspace)` — 时间戳完整备份
2. `skill_inspector.inspect_skill(skill_dir)` — **强制**输出结构蓝皮书
3. `_check_meta_json()` — 验证 _meta.json 7 字段 + 非标字段标记
4. `_check_skill_md()` — 验证 SKILL.md 存在性、行数、必填章节
5. `_check_dir_structure()` — 扫描根目录散落文件
6. `_check_artifact_paths()` — 产出物路径合规（R-11）
7. `_check_external_data_dir()` — 外部数据目录合规（R-12）
8. `_bump_version()` — 版本号自动更新（如传 --version-bump）
9. `_print_report()` — 输出检查报告（通过/警告计数 + 逐条详情）

**refactor 模式完整步骤**：
1. `_create_backup(skill_dir, "refactor", workspace)` — 强制备份
2. `skill_inspector.inspect_skill(skill_dir)` — **强制**输出结构蓝皮书
3. `_dry_run()` — 生成迁移计划（仅 --dry-run 时停止）
4. `_build_migration_plan()` — 按 M-01~M-06 规则编排文件迁移
5. `_execute_migration()` — 执行移动（仅 move，不 delete）
6. `_fix_code_references()` — 代码引用重写（--fix-code）
7. `_verify_migration()` — 字节一致性验证（±1% 容差）
8. `_bump_version()` — 版本号自动升级（patch）
9. `_audit_and_update_progress()` — 审计 + 进度记录

**inspect 扫描产出明细**（强制前置）：
- 结构标准化判定：标准（scripts/ + references/）/ 半标准（仅有 scripts/ 或 references/）/ 非标准（文件散落根目录）
- 元信息：SKILL.md 行数、## 章节数量及标题列表、_meta.json 字段清单
- 文件清单：按扩展名分组计数（.py / .md / .sh/.bat /.json/.yaml / 其他）
- 非标位置标记：每个不在 scripts/ 下的 .py 文件、不在 references/ 下的 .md 文件均标注 `[note] 建议迁移`
- 功能清单：每个 .py 文件的 `def` 函数名和 `class` 类名列表
- 引用概览：每个 .md 文件的行数和 ## 章节标题
- 安全数据：sensitive_access / critical_write / permission_weight / data_dir 声明值

### 审计结果判定

| 结果 | 含义 |
|:----:|------|
| **PASS** | 全部规则通过 |
| **WARN** | 仅 WARN 级未通过 |
| **FAIL** | 含 ERROR 级未通过 |

**审计报告格式**（标准输出）：
```
=======================================================
  审查结果: <skill-name> — PASS / WARN / FAIL
=======================================================
  总计: 25 | 通过: N | 失败: N | 跳过: N

规则ID     严重度     状态     详情
------------------------------------------------------
R-01     E       [OK]   发现 YAML frontmatter...
R-06     W       [OK]   发现一级标题: # ...

───────────────────────────────────────────────────────
  🛠️ 提示：发现可修复问题时...
```

每条 FAIL 项附带：
- `💡 建议修正` — 具体操作指引
- `[search] 位置` — 文件路径:行号
- `--fix` 可用时自动修复

**误报分类机制**：`_reclassify_false_positive()` 在审计运行时自动过滤已知误报模式（如系统工具名被误检为函数名），过滤后的项显示为 `ⓘ 已排除`，不计入 WARN/ERROR 统计。`--verify` 模式也使用此函数排除误报后判断是否通过。

### bump 子命令

一键升级技能版本号三端：

```bash
python -m scripts.skill_audit bump <skill-dir> --type fix    # patch 升级
python -m scripts.skill_audit bump <skill-dir> --type feature # minor 升级
python -m scripts.skill_audit bump <skill-dir> --type breaking # major 升级
python -m scripts.skill_audit bump <skill-dir> --type fix --desc "修复说明"  # 带描述
```

`audit --fix` 模式修复文件后自动执行 patch bump，changelog 写入实际修复规则名而非空话，AI 须将其转化为可读描述后写入。

### inspect 子命令

结构无关的全量扫描工具，输出技能蓝皮书：

```bash
python -m scripts.skill_inspector <skill-dir>
python -m scripts.skill_inspector <skill-dir> --json   # JSON 格式
python -m scripts.skill_builder inspect <skill-dir>    # 通过 builder 调用
```

自动适配标准结构（scripts/ + references/）和非标准结构（文件散落根目录），标记非标文件位置（如"config.py 在根目录，建议迁至 scripts/"）。update 和 refactor 流程在备份后自动执行此扫描。

---

## 十、铁律8：全报告 LLM 细筛

审计报告（`run_audit audit`）输出后，LLM **必须**逐条阅读每条结果。

审计输出已包含行号、上下文、问题描述，信息完整。`_reclassify_false_positive()` 已在 Python 侧自动过滤已知误报模式，过滤后的剩余项由 LLM 终审判断：

- **真问题** → 立即修复
- **新误报模式** → LLM 直接放过，后续由开发者按需补充

LLM **禁止**跳过终审步骤，也**禁止**将应修复的真问题解释为误报放任不管。全报告处理完毕后，才能进入铁律9验证。

## 十一、铁律9：0 ERROR 0 WARN 强制验证

`audit --verify` 在 LLM 细筛完成后执行：

1. 运行完整审计 R-01~R-25
2. 排除 `_reclassify_false_positive()` 已知的误报项
3. 有非误报的未通过项 → exit(1)，输出每项 rule_id + detail
4. 全部通过或仅误报 → exit(0)

exit code 是 LLM 无法忽略的信号。非零退出码意味着验证绝对失败，LLM **不得**声称"审计通过"。

---

> 本文档基于 skill-standardization v2.58.1 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
