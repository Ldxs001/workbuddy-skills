# skill-standardization 架构与规范体系文档

> 完整解读 v2.38.10 版的架构设计、审查规则体系、设计原则与编程规范  
> 生成时间：2026-05-29

---

## 一、系统概览

skill-standardization 是一个 **Skill 全生命周期标准化管理工具集**，围绕以下闭环运行：

```
规范定义（spec/*.json）
  → 构建器（skill_builder: create / update / refactor）
    → 审查器（skill_audit: R-01 ~ R-24）
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
├── _meta.json                  # 五字段元数据
├── references/                 # 渐进式文档
│   ├── guide.md                # 完整使用教程
│   ├── architecture.md         # 架构设计（本文档参考来源）
│   ├── reference.md            # API/命令参考手册
│   ├── antipatterns.md         # 13 条反模式
│   ├── faq.md                  # 24 个常见问题
│   └── changelog.md            # 版本更新日志
└── scripts/                    # 核心脚本
    ├── skill_builder/          # 构建器包（OO 重构后）
    │   ├── __init__.py         # 主入口 + argparse
    │   ├── creator.py          # SkillCreator（create 模式）
    │   ├── updater.py          # SkillUpdater（update 模式）
    │   ├── refactor.py         # Refactor（refactor 模式）
    │   ├── version_manager.py  # VersionManager
    │   └── utils.py            # 工具函数
    ├── skill_audit/            # 审查器包（OO 重构后）
    │   ├── __init__.py         # 主入口 + audit_skill()
    │   ├── frontmatter_checker.py  # R-01~R-05
    │   ├── structure_checker.py    # R-06~R-09
    │   ├── artifact_checker.py     # R-11~R-12
    │   ├── permission_checks.py    # R-13~R-17
    │   └── fix.py              # 23 条规则的自动修复函数
    ├── json_loader.py          # 渐进式 JSON 加载器
    ├── permission_checker.py   # 权限检查器
    ├── authorization_manager.py# 授权管理器
    ├── safe_io.py              # 安全文件写入（原子写入+备份）
    ├── op_logger.py            # 操作日志记录
    └── skill_rollback.py       # 回滚管理
```

### 1.3 三种执行模式

| 模式 | 命令 | 作用 | 风险等级 |
|------|------|------|---------|
| **create** | `skill_builder create <name>` | 从模板创建标准的 skill 骨架 | 🟢 无害 |
| **update** | `skill_builder update <dir> [--fix]` | 增量检查 + 可选修复 | 🟡 轻度修改 |
| **refactor** | `skill_builder refactor <dir> [--dry-run]` | 整体结构改造（移动文件） | 🔴 必须先 dry-run |

---

## 二、完整审查规则体系（R-01 ~ R-24）

24 条规则按用途分为 6 大类别，严重度分为 **ERROR**（必须修）和 **WARN**（建议修）两级。

### 2.1 类别 A：Frontmatter 结构（R-01 ~ R-05）

**目的**：确保每个 skill 有完整可解析的 YAML frontmatter，字段齐全、命名规范。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-01** | ERROR | YAML frontmatter 存在性 | 文件以 `---` 开头并包含闭合 `---` |
| **R-02** | ERROR | `name` 字段 | frontmatter 含 `name:`，值非空字符串 |
| **R-03** | ERROR | `version` 字段 | 值符合 SemVer 格式（x.y.z） |
| **R-04** | ERROR | `description` 字段 | 含 `description:`，值非空 |
| **R-05** | WARN | name = 目录名 | frontmatter 的 name 与所在目录名一致 |

**设计意图**：frontmatter 是所有 Skill 的"身份证"。没有完整 frontmatter，AI 无法正确识别 skill 的身份、版本和功能。R-05 确保目录名和声明名一致，避免混淆。

### 2.2 类别 B：正文结构（R-06 ~ R-10）

**目的**：规范 SKILL.md 正文的结构和内容质量，确保可读性。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-06** | WARN | 一级标题 | 正文包含 `# ` 开头的 H1 标题 |
| **R-07** | WARN | 触发条件章节 | 含触发场景章节，≥3 个触发词，≥1 个否定条件 |
| **R-08** | WARN | 核心能力章节 | 含核心能力/功能章节 |
| **R-09** | WARN | 工作流程章节 | 含工作流程/步骤章节 |
| **R-10** | WARN | 版本同步 | `SKILL.md version == _meta.json version`（需传入 manifest） |

**设计意图**：确保用户和 AI 都能快速理解技能的作用、何时触发、能做什么、怎么用。R-07 是防止误触发的关键——宽泛的触发词（如"画图"）会导致 skill 在不相关场景下被错误加载。R-10 保证版本号一致性。

### 2.3 类别 C：产出物与数据目录（R-11 ~ R-12）

**目的**：防止数据/产出物污染技能安装目录，规范数据目录路径。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-11** | ERROR | 产出物路径 | 产出物应放在 `skills/.standardization/<skill>/data/output/`，不在安装目录 |
| **R-12** | ERROR | 数据目录路径 | 脚本中 `DATA_DIR` 变量的值必须包含合规字面量 |

**R-12 的核心机制**：审计器对源码做**静态字符串匹配**，检查是否存在变量（名字含 `DATA|STORAGE|DB|CACHE|CONFIG`）= `"skills/.standardization/<skill>/data/"` 这样的字面量赋值。仅运行时计算路径无法通过审计。

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
| **R-13** | ERROR | 敏感信息访问 | 若脚本读取 memory/credentials/token → frontmatter 须声明 `sensitive_access: true` |
| **R-14** | ERROR | 关键位置写入 | 若写入 skills/系统目录 → 须声明 `critical_write: true` |
| **R-15** | ERROR | 高权限风险说明 | 脚本含高/严重风险操作时，`references/permissions.md` 须有风险说明 |
| **R-16** | WARN | 权限权重说明 | 建议在 SKILL.md 或 references/ 中说明各操作的权限权重 |
| **R-17** | ERROR | 渐进加载引用 | SKILL.md > 200 行时必须拆分到 references/ 并通过引用链接 |

**设计意图**：让用户在安装技能前就能了解其风险。R-15 要求高风险操作必须附带说明文档，R-17 强制大文件必须分解以保持加载效率。

### 2.5 类别 E：质量规范（R-18 ~ R-21）

**目的**：提升技能文档的内容质量，避免模糊、空洞的表述。

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-18** | WARN | 反模式具体性 | SKILL.md 含反模式章节，每条 ≥20 字且有错误+正确做法 |
| **R-19** | WARN | FAQ 有意义性 | FAQ 中问题 ≥10 字、答案 ≥15 字，非万能回答 |
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
| **R-23** | WARN | 文档-代码一致性 | SKILL.md 引用的脚本/文件真实存在，调用方式一致 |
| **R-24** | WARN | 更新日志规范 | changelog 在 `references/changelog.md`，根目录无 `CHANGELOG.md` |

### 2.7 规则汇总统计

| 类别 | 包含规则 | ERROR | WARN | 目的 |
|------|---------|:-----:|:----:|------|
| A. Frontmatter | R-01~R-05 | 4 | 1 | 技能身份标识 |
| B. 正文结构 | R-06~R-10 | 0 | 5 | 文档结构和质量 |
| C. 产出物与目录 | R-11~R-12 | 2 | 0 | 目录隔离和数据安全 |
| D. 安全与权限 | R-13~R-17 | 3 | 2 | 权限声明和风险控制 |
| E. 质量规范 | R-18~R-21 | 0 | 4 | 内容质量和可读性 |
| F. 合规与维护 | R-22~R-24 | 0 | 3 | 长期维护一致性 |
| **合计** | **R-01~R-24** | **9** | **15** | |

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

### D6: 备份优先
任何修改性操作（update --fix, refactor）在执行前均强制备份，带时间戳命名。
**目的**：确保所有变更可回滚，零数据丢失。

---

## 四、强制约束与编程规范

### 4.1 版本号三端一致规则

版本号变更时必须同步更新以下 **3 处**，缺一不可：

| # | 文件 | 字段/位置 |
|---|------|-----------|
| 1 | `SKILL.md` frontmatter | `version:` 字段 |
| 2 | `_meta.json` | `"version"` 字段 |
| 3 | `references/changelog.md`（或 `CHANGELOG.md`） | 版本条目 |

`update --fix` 已自动执行上述三端同步（v2.38.10+）。升级版本时自动追加 changelog 条目。

### 4.2 文件更新约束（重要）

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

### 4.4 排错止损规则（v2.38.5）

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

变量名必须含 `DATA|STORAGE|DB|CACHE|CONFIG` 之一才能被审计匹配。

---

## 五、反模式速查表

13 条预注册反模式，按影响级别分级：

| ID | 反模式 | 级别 | 正确做法 |
|----|--------|:----:|---------|
| AP-01 | SKILL.md 写大量教程 | 🔴 | 拆分到 references/guide.md |
| AP-02 | 根目录散落文件 | 🔴 | scripts/ + references/ + assets/ |
| AP-03 | Frontmatter 字段缺失 | 🔴 | 补全 name/version/description |
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

统一修复入口：
```python
from scripts.skill_audit.fix import apply_fix
apply_fix(skill_dir, 'R-07', 'R-18', 'R-19')  # 批量修复
```

---

## 七、与 git-sync 的集成

git-sync 在每次同步时自动触发 skill_audit 审查：

```
git-sync 执行
  ├─ 步骤 1~3: 收集/检查/提交
  ├─ 步骤 3.5: skill_audit.py audit ← 自动调用
  │   ├─ PASS → 继续
  │   ├─ WARN → 🟡 打印警告，继续
  │   └─ FAIL → 🟡 打印警告，继续（纯警告模式）
  └─ 步骤 4~6: 推送/生成 ZIP/更新 manifest
```

版本号需要三方一致（SKILL.md + _meta.json + manifest.json）。

---

## 八、规范定义体系（spec/*.json）

| 文件 | 职责 | 不包含 |
|------|------|-------|
| `frontmatter.json` | 定义字段名/类型/必须性 | 不含验证逻辑 |
| `body.json` | 定义章节名/层级/必须性 | 不含写作指导 |
| `rules.json` | 完整规则定义（ID/级别/逻辑） | 不含执行引擎 |
| `structure.json` | 目录结构规范 + 迁移规则 | 不含移动逻辑 |
| `progressive_md.json` | MD 拆分方案 + 加载协议 | 不含文件操作 |
| `_index.json` | 模块注册表 + 依赖关系 | 不含具体规范 |

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
执行 audit（R-01~R-24）或 update/refactor
  ↓
输出审查报告（PASS/WARN/FAIL）
  ↓
调用 fix.py 自动修复（如有 --fix）
  ↓
再次审计确认 0 ERROR 0 WARN
  ↓
更新版本号（三端同步 + changelog 自动追加）
  ↓
git-sync 推送 + 打包
```

### 审计结果判定

| 结果 | 含义 | git-sync 行为 |
|:----:|------|-------------|
| **PASS** | 全部通过 | 继续同步 |
| **WARN** | 仅 WARN 级失败 | 🟡 继续同步（纯警告） |
| **FAIL** | 含 ERROR 级失败 | 🟡 继续同步（纯警告） |

---

> 本文档基于 skill-standardization v2.38.10 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
