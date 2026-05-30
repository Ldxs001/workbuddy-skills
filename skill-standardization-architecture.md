# skill-standardization 架构与规范体系文档

> 完整解读 v2.44.0 版的架构设计、审查规则体系、标准化执行流程与修复体系  
> 生成时间：2026-05-31

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
├── SKILL.md                    # 主文件（≤200行，渐进式入口）
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
    │   ├── fix.py              # 自动修复函数（20+ 规则）
    │   └── utils.py            # 工具函数
    ├── json_loader.py          # 渐进式 JSON 加载器
    ├── skill_inspector.py      # 技能结构蓝皮书生成器（v2.44.0 新增）
    ├── permission_checker.py   # 权限检查器
    ├── authorization_manager.py# 授权管理器
    ├── safe_io.py              # 安全文件写入（原子写入+备份）
    ├── op_logger.py            # 操作日志记录
    ├── op_logger_patch.py      # 操作日志补丁
    ├── data_dir_checker.py     # 数据目录合规检查器
    ├── artifact_checker.py     # 产出物检查器
    ├── run_audit.py            # 独立审计入口
    ├── progress_manager.py     # 进度管理器
    ├── update_all_versions.py  # 全版本更新
    ├── update_skill_frontmatter.py # frontmatter 更新脚本
    ├── migrator.py             # 迁移器
    ├── restore_from_gitee.py   # 从码云恢复
    ├── patch_utils.py          # 补丁工具函数
    ├── fix.py                  # 修复器
    ├── creator.py              # 创建器
    ├── refactor.py             # 改造器
    ├── updater.py              # 更新器
    ├── version_manager.py      # 版本管理器
    └── spec/                   # 规范定义（JSON Schema）
        ├── _index.json         # 模块注册索引
        ├── frontmatter.json    # Frontmatter 字段规范 v2.5.0
        ├── body.json           # 正文章节结构规范
        ├── rules.json          # 审查规则完整定义
        ├── structure.json      # 目录结构规范 v2.5.0
        └── progressive_md.json # 渐进式 MD 体系规范
```

### 1.3 三种执行模式

| 模式 | 命令 | 作用 | 风险等级 |
|------|------|------|---------|
| **create** | `skill_builder create <name>` | 从模板创建标准的 skill 骨架 | 🟢 无害 |
| **update** | `skill_builder update <dir> [--fix]` | 增量检查 + 可选修复 | 🟡 轻度修改 |
| **refactor** | `skill_builder refactor <dir> [--dry-run]` | 整体结构改造（移动文件） | 🔴 必须先 dry-run |

此外，审计模式可通过 `python -m scripts.skill_audit audit <dir>` 独立运行。

---

## 二、完整审查规则体系（R-01 ~ R-25）

25 条规则按用途分为 6 大类别，严重度分为 **ERROR**（必须修）和 **WARN**（建议修）两级。

### 2.1 类别 A：Frontmatter 结构（R-01 ~ R-05）

**目的**：确保每个 skill 有完整可解析的 YAML frontmatter，字段齐全、命名规范。R-01 在 v2.44.0 合并了 _meta.json 7 字段检查。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-01** | ERROR | YAML frontmatter 存在性 + 字段完整性 + **_meta.json 7 字段检查**（v2.44.0 合并） | 文件以 `---` 开头并包含闭合 `---`；11 required + 2 conditional 字段分层检查；_meta.json 7 标准字段完整 |
| **R-02** | ERROR | `name` 字段 | frontmatter 含 `name:`，值非空字符串 |
| **R-03** | ERROR | `version` 字段 | 值符合 SemVer 格式（x.y.z） |
| **R-04** | ERROR | `description` 字段 | 含 `description:`，值非空 |
| **R-05** | WARN | name = 目录名 | frontmatter 的 name 与所在目录名一致 |

**Frontmatter 字段分层体系**（v2.40.1+）：
- **11 required**：name/version/description/author/license/tags/data_dir/external_data_dir/sensitive_access/critical_write/permission_weight
- **2 conditional**：trigger/trigger_negative（正文有触发词/否定条件时必填）
- **4 optional**：references/category/priority/deprecated

**非标字段处理策略**（v2.41.0+）：
- **_meta.json 非标字段**：标记并提示人工判断是否需要删除或迁移（审计仅提醒，不自动删除）
- **frontmatter 非标字段**：仅 WARN 提醒，不移除（frontmatter 允许自定义字段如 home_url、category）

**设计意图**：frontmatter 是所有 Skill 的"身份证"。R-05 确保目录名和声明名一致。R-01 在 v2.44.0 合并了 `_meta.json` 7 字段检查，通过 `regex_frontmatter_and_meta()` 组合函数同时校验 SKILL.md 和 `_meta.json` 的元数据完整性。

### 2.2 类别 B：正文结构（R-06 ~ R-10）

**目的**：规范 SKILL.md 正文的结构和内容质量，确保可读性。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-06** | WARN | 一级标题 | 正文包含 `# ` 开头的 H1 标题 |
| **R-07** | WARN | 触发条件章节 | 含触发场景章节，≥3 个触发词，≥1 个否定条件，且与 frontmatter 的 trigger/trigger_negative 一致性 |
| **R-08** | WARN | 核心能力章节 | 含核心能力/功能章节 |
| **R-09** | WARN | 工作流程章节 | 含工作流程/步骤章节 |
| **R-10** | WARN | 版本同步 | 自动读取 _meta.json + SKILL.md + changelog 三端版本号对比一致性；新增 mtime 时序检查（代码文件比 changelog 新时告警） |

**R-07 增强**：不仅检查章节存在性，还比对 frontmatter 的 trigger/trigger_negative 字段与正文触发词的一致性。
**R-10 增强**：不再依赖 `--manifest-version` CLI 参数，改为自动读取 _meta.json 和 changelog 进行三端对比。

**设计意图**：确保用户和 AI 都能快速理解技能的作用、何时触发、能做什么、怎么用。R-10 保证版本号三端一致性。

### 2.3 类别 C：产出物与数据目录（R-11 ~ R-12）

**目的**：防止数据/产出物污染技能安装目录，规范数据目录路径。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-11** | ERROR | 产出物路径 | 产出物应放在 `skills/.standardization/<skill>/data/output/`，不在安装目录 |
| **R-12** | ERROR | 数据目录路径 | 脚本中 `DATA_DIR` 变量的值必须包含合规字面量 |

**R-12 的核心机制**：审计器对源码做**三源证据链**判断：
1. **代码脚本**：扫描所有 .py 文件中的 `DATA_DIR`/`STORAGE_DIR`/`CACHE_DIR`/`CONFIG` 变量定义
2. **SKILL.md frontmatter**：看是否有 `data_dir:` 声明
3. **_meta.json**：看 `data_dir` 字段是否存在

只要有任何一个来源表明技能有数据需求，就要求 `_meta.json` 声明 `data_dir`。

**R-12 修复历程**（v2.38.11）：修复了 `_extract_path_value` 函数不存在导致的漏检问题（R-12 对脚本的检测从没真正运行过），并新增 step 1.5 检测引用 `.standardization` 但无 `DATA_DIR` 的脚本。

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
| **R-17** | ERROR | 渐进加载引用 | SKILL.md > 200 行时必须拆分到 references/ 并通过引用链接 |

**设计意图**：让用户在安装技能前就能了解其风险。R-15 要求高风险操作必须附带说明文档，R-17 强制大文件必须分解以保持加载效率。

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
| **R-22** | WARN | 数据目录合规 | `_meta.json` 含 `data_dir` 字段，scripts/ 中 `DATA_DIR` 指向合规路径 |
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

### 2.7 类别 G：文档写作格式（R-25 — v2.44.0 新增）

**目的**：统一 SKILL.md 的写作格式，提供标准化的排版建议。R-25 整体为 WARN 级，其 10 项子检查中 C-01 为 ERROR 级（仅作内部参考，不提升规则总体级别），其余均为 WARN 建议级。

| 编号 | 级别 | 检查项 | 说明 |
|:----:|:----:|--------|------|
| C-01 | ERROR | H1 标题格式 | 必须为 `# <技能名>`，不得含版本号（版本号由 version 字段管理） |
| C-02 | WARN | 标题层级 | 限制在 `##` 和 `###`，不应出现 `####+` |
| C-03 | WARN | 表格使用 | 结构化信息应使用表格展示 |
| C-04 | WARN | 引用块使用 | 提示/注意/警告应使用 `>` 引用块包装 |
| C-05 | WARN | 列表区分 | 有序列表用于步骤流程，无序列表用于选项列举 |
| C-06 | WARN | 加粗使用 | 关键术语/约束/规则名使用 `**加粗**` 强调 |
| C-07 | WARN | 语言标识 | 代码块应带语言标识（` ```bash `、` ```python `） |
| C-08 | WARN | Checklist | 操作前自检使用 `- [ ]` checklist 格式 |
| C-09 | WARN | 渐进引用 | 引用渐进式文件统一使用 `→ 详见 references/xxx.md` |
| C-10 | WARN | 空行规范 | frontmatter 闭合后 ≤2 个连续空行；正文 ≤4 个连续换行 |

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
| G. 写作格式 | **R-25** | 0 | 1 | 文档排版统一建议（10 项子检查仅 C-01 为 ERROR 级，但不改变规则总体 WARN 级别） |
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
v2.44.0 新增：备份后、改造前**强制运行 skill_inspector** 结构扫描，输出技能蓝皮书（元信息、目录树、章节、函数清单、引用概览、安全数据），确保 AI/开发者了解全貌后再动手。
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

`update --fix` 已自动执行上述三端同步（v2.38.10+）。`bump` 子命令（v2.39.0+）可一键升级版本号三端。

### 4.2 文件更新约束

所有 `.md` 文件**禁止使用 Write/Edit 工具更新**（会损坏 UTF-8 中文编码），必须用 Python 脚本原子写入：

| 文件 | 更新方式 | 使用脚本 |
|------|----------|---------|
| `SKILL.md` frontmatter | Python 原子写入 | `update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 正则替换 | `fix_progressive_loading.py` |
| `references/*.md` | safe_io.py 的 `safe_write()` | 随技能自带 |
| 更新日志 | Python 合并脚本 | 每次发版统一维护 |

### 4.3 检查清单（每次更新前）

- [ ] 是否用了 Write/Edit 工具？→ 立刻停止，改用 Python 脚本
- [ ] 是否在 `references/changelog.md` 维护更新记录？→ 根目录不得有 `CHANGELOG.md`
- [ ] 更新后是否用 `python -m scripts.skill_audit audit .` 自审？→ 必须 0 ERROR 0 WARN

### 4.4 排错止损规则（v2.38.4+）

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

13 条预注册反模式，按影响级别分级：

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
| `fix_h1(skill_dir)` | R-06 | 删除正文一级标题 |
| `fix_section_trigger(skill_dir)` | R-07 | 添加触发条件章节 |
| `fix_section_core(skill_dir)` | R-08 | 添加核心能力章节 |
| `fix_section_workflow(skill_dir)` | R-09 | 添加工作流程章节 |
| `fix_progressive_loading(skill_dir)` | R-21 | 添加渐进式加载模板句 |
| `fix_antipattern_progressive(skill_dir)` | R-18 | 创建/更新 antipatterns.md |
| `fix_faq_progressive(skill_dir)` | R-19 | 创建/更新 faq.md |
| `fix_writing_standards(skill_dir)` | R-20 | 统一术语 |
| `fix_data_dir_compliance(skill_dir)` | R-22 | 添加 data_dir 声明 |
| `fix_doc_code_consistency(skill_dir)` | R-23 | 修复文档-代码一致性 |
| `fix_artifact_paths(skill_dir)` | R-11 | 修复产出物路径 |
| `fix_external_data_dir(skill_dir)` | R-12 | 修复外部数据目录 |
| `fix_sensitive_access(skill_dir)` | R-13 | 添加敏感信息访问声明 |
| `fix_critical_write(skill_dir)` | R-14 | 添加关键位置写入声明 |
| `fix_create_permissions_md(skill_dir)` | R-15 | 创建 permissions.md |
| `fix_permission_weight(skill_dir)` | R-16 | 添加权限权重说明 |
| `fix_frontmatter_fields(skill_dir)` | R-01 | 补全 frontmatter 字段（required→conditional 分层补全） |
| `fix_meta_json_completeness(skill_dir)` | R-01（合并） | 补全 _meta.json 7 标准字段，标记非标字段供人工判断 |
| `fix_missing_data_dir(skill_dir)` | R-12 | 为引用 .standardization 但缺少 DATA_DIR 的脚本补上声明 |

统一修复入口：
```python
from scripts.skill_audit.fix import apply_fix
apply_fix(skill_dir, 'R-07', 'R-18', 'R-19')  # 批量修复
```

---

## 七、与 git-sync 的协作（已解耦）

> **注意**：`skill-standardization` 与 `git-sync` 已完全解耦（v2.38.13）。以下仅说明过去的集成关系作为架构参考，不代表当前依赖。

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
输出审查报告（PASS/WARN/FAIL）
  ↓
调用 fix.py 自动修复（如有 --fix）
  ↓
再次审计确认 0 ERROR 0 WARN
  ↓
更新版本号（三端同步 + changelog 自动追加）
```

**inspect 扫描产出**（v2.44.0 强制前置）：
- 元信息（SKILL.md 行数、## 章节数、_meta.json 字段）
- 文件清单（按 .py/.md/.sh/.json 分类，标记非标位置）
- 全部 ## 章节一览
- 每个 .py 文件的 def/class 清单
- 每个 .md 文件的行数和 H2 章节
- 安全 & 数据声明
- 结构标准化程度判定（标准/半标准/非标准）

### 审计结果判定

| 结果 | 含义 |
|:----:|------|
| **PASS** | 全部规则通过 |
| **WARN** | 仅 WARN 级未通过 |
| **FAIL** | 含 ERROR 级未通过 |

### bump 子命令（v2.39.0+）

一键升级技能版本号三端：

```bash
python -m scripts.skill_builder bump <skill-dir> --type fix    # patch 升级
python -m scripts.skill_builder bump <skill-dir> --type feature # minor 升级
python -m scripts.skill_builder bump <skill-dir> --type breaking # major 升级
python -m scripts.skill_builder bump <skill-dir> --type fix --desc "修复了XX问题"  # 带描述
```

`audit --fix` 模式修复文件后自动执行 patch bump（v2.39.0+），不再忘记更新版本号。

### inspect 子命令（v2.44.0 新增）

结构无关的全量扫描工具，输出技能蓝皮书：

```bash
python -m scripts.skill_inspector <skill-dir>
python -m scripts.skill_inspector <skill-dir> --json   # JSON 格式
python -m scripts.skill_builder inspect <skill-dir>    # 通过 builder 调用
```

自动适配标准结构（scripts/ + references/）和非标准结构（文件散落根目录），标记非标文件位置（如"config.py 在根目录，建议迁至 scripts/"）。update 和 refactor 流程在备份后自动执行此扫描。

---

> 本文档基于 skill-standardization v2.44.0 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
