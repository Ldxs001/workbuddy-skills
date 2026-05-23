# 更新日志（Changelog）

> 本文件记录 skill-standardization 的版本变更历史。
> 遵循 [Keep a Changelog](https://keepachangelog.com/) 格式，基于 SemVer 版本管理。

---

## 目录

- [v2.7.3（当前版本）](#273-当前版本)
- [v2.7.2](#272)
- [v2.7.1](#271)
- [v2.7.0](#270)
- [v2.6.0](#260)
- [v2.5.0](#250)
- [v2.4.0](#240)
- [v2.3.0](#230)
- [v2.1.0](#210)
- [v2.0.1](#201)
- [v2.0.0（重大升级）](#200-重大升级)
- [v1.0.0（初始版本）](#100-初始版本)

---

### v2.7.3（当前版本）

**发布日期：2026-05-23**
**类型：Minor（R-11 非标准子目录 + 全面产出物定义扩展）**

### 新增

- **R-11 非标准子目录扫描**：在根目录文件检测之外，新增产出物目录递归扫描
  - `_ARTIFACT_DIR_CLASSIFY`：30+ 产出物目录名 → (分类, 描述) 映射（data/cache/outputs/temp 四类）
  - `_ARTIFACT_EXTS_COMPREHENSIVE`：50+ 产出物文件扩展名全面定义，按分类组织
  - `_check_artifact_directories`：检测根目录非标准子目录（data/cache/outputs/temp/logs/等）
  - `_scan_dir_recursive`：递归扫描产出物目录内所有文件，生成迁移建议
  - `_scan_unknown_dir`：对未匹配的未知目录，通过内容分析推断是否为产出物目录
  - **嵌套检测**：同时扫描 scripts/ 和 references/ 下的非标准子目录
- **产出物分类体系 v2**：
  - `data/` — 持久化数据：.db/.json/.csv/.pkl/.parquet/.npy 等
  - `cache/` — 缓存：.cache 目录及缓存文件
  - `outputs/` — 输出产物：.html/.pdf/.png/.xlsx/.log 等
  - `temp/` — 临时文件：.tmp/.bak/.swp/.lock/.pid 等

### 变更

- `skill_audit.py` v2.6.0 → v2.7.0
- `skill_builder.py` v2.6.0 → v2.7.0
- R-11 描述更新为："scripts/ + 根目录 + 非标子目录 产出路径规范"
- 根目录白名单扩展：增加 `.gitkeep`
- `_check_root_artifact_files` 使用新的 `_classify_artifact_by_ext` 统一分类
- `_ARTIFACT_EXTS_COMPREHENSIVE` 包含 50+ 扩展名（原 16 种 → 50+）

### 设计理由

- 原有 R-11 仅检测根目录文件，遗漏了 data/、cache/、outputs/ 等非标准子目录
- 这些目录明显是产出物目录（非技能结构组成部分），其内容也需要迁移检查
- 全面产出物定义让检测不再依赖"已有哪些扩展名"的硬编码枚举，而是建立系统化分类

### 技术细节

| 项目 | v2.7.2 | v2.7.3 |
|------|--------|--------|
| 检测范围 | scripts/ + 根目录文件 | + 根目录子目录 + scripts/子目录 + references/子目录 |
| 产出物目录模式 | — | 30+ 种（data/cache/outputs/temp/logs/backup...） |
| 产出物文件扩展名 | 16 种 | 50+ 种（.pkl/.parquet/.npy/.xlsx/.lock 等） |
| 目录递归扫描 | — | os.walk 递归列出所有文件 |
| 嵌套检测 | — | scripts/data/, references/output/ 等 |

---

### v2.7.2

**发布日期：2026-05-23**
**类型：Minor（R-11 根目录产出物检测扩展）**

### 新增

- **R-11 根目录产物扫描**：在 scripts/ 扫描之外，新增技能根目录文件检测
  - `skill_audit.py` 新增 `_check_root_artifact_files`：检测根目录中非 SKILL.md/_meta_json 的数据文件（.json/.csv/.yaml/.db 等）
  - `skill_builder.py` 新增 `_check_root_artifact_files_builder`：同步增加根目录扫描
  - 根目录产出物自动分类（data/outputs），给出标准路径迁移建议
  - 交叉引用追踪修复：根目录文件不再把自身报告为关联引用

### 变更

- `skill_audit.py` v2.5.0 → v2.6.0
- R-11 描述更新为："scripts/ + 根目录 产出路径规范 + 全目录交叉引用追踪"
- R-11 检测覆盖从仅 scripts/ 扩展到技能全目录

### 设计理由

- 原有 R-11 只扫描 scripts/ 中的写入模式，无法检测已存在于根目录的产出物文件
- git-sync 的 config.json / manifest.json 等运行时数据文件在根目录违反了铁律4，但 R-11 未能检出
- 根目录扫描填补了这一检测盲区，实现"无论产出物从何而来都能被检测到"

### 技术细节

| 项目 | v2.7.1 | v2.7.2 |
|------|--------|--------|
| 检测范围 | scripts/ | scripts/ + 根目录 |
| 根目录白名单 | — | SKILL.md, _meta.json, .gitignore |
| 根目录产物扩展名 | — | .json/.csv/.yaml/.db 等 16 种 |
| 交叉引用自排除 | 脚本行号 | 脚本行号 + 根目录文件名 |

---

### v2.7.1

**发布日期：2026-05-23**
**类型：Patch（R-11 交叉引用追踪增强）**

### 新增

- **R-11 交叉引用追踪**：从 `scripts/` 发现的每个违规路径出发，反向搜索整个技能目录（SKILL.md、references/*.md、_meta.json 等），找出所有引用同一路径的关联文件，一并报告在"关联引用"列表中
- 违规格式从纯文本字符串升级为结构化对象 `{source, path_literal, suggestion, cross_refs}`
- `_extract_path_literal()` 辅助函数：从违规行提取完整路径字面量
- `_trace_cross_references()`：独立的交叉引用搜索引擎，排除 scripts/ 自身，仅扫描文本文件

### 修复

- `open("output/report.html", "w")` regex 改为捕获完整路径 `output/report.html` 而非仅捕获目录名 `output`
- 建议路径 `suggestion` 现在正确处理完整文件路径（如 `outputs/report.html` 而非 `outputs/`）
- `_ARTIFACT_DIR_NAMES` 排序优化：长名在前避免部分匹配（`outputs` 优先于 `output`）
- Shell 正则统一使用 `_ARTIFACT_DIR_RE` 而非硬编码

### 变更

- `skill_audit.py` v2.4.0 → v2.5.0
- `skill_builder.py` v2.5.0 → v2.6.0

### 测试验证

- 模拟 5 处违规 + 3 个文件引用同一路径：全部检出并正确报告关联文件位置
- skill-standardization 自身审查：R-11 PASS

---

### v2.7.0

**发布日期：2026-05-23**
**类型：Minor（新审查规则 R-11）**

### 新增

- **R-11：产出物路径规范性审查（铁律4落地检测）**：
  - `skill_audit.py` 新增 `check_artifact_paths` 方法，自动扫描 `scripts/` 下 `.py/.sh/.bat/.ps1` 文件，检测硬编码产出路径指向技能目录内部的违规行为
  - `skill_builder.py` `cmd_update()` 同步增加产出物路径检查（检查4）
  - 检测模式覆盖：`Path(__file__).parent / "output"`、`os.path.dirname(__file__)` + 产出子目录、`open("output/...", "w")` 相对路径写入、`Path("data").mkdir()` 等
  - 自动区分合规/违规：含 `"standardization"` 关键字的路径放行，纯读操作 `"r"` 模式放行
  - 根据目录名自动推断产出物分类（data/cache/outputs/temp），给出迁移建议

### 变更

- 审查规则从 10 条增至 11 条（R-01~04 ERROR + R-05~11 WARN）
- `skill_audit.py` v2.3.0 → v2.4.0
- `skill_builder.py` v2.4.0 → v2.5.0（文件头已为 v2.5.0，同步工具体现）
- `scripts/spec/rules.json` v2.2.0 → v2.3.0，_total_rules: 10→11，_warn_count: 6→7

### 设计理由

- 铁律4（产出物路径管理规范）此前只定义了规范，缺少自动化检测手段
- update/refactor 模式下可以主动发现违规并提示修正，形成"规范定义 → 审查检测 → 建议修正"完整闭环
- 检测仅告警不阻断（WARN 级），由技能维护者决定是否修正

### 技术细节

| 项目 | v2.6.0 | v2.7.0 |
|------|--------|--------|
| 审查规则数 | 10 | 11 |
| 检测代码新增 | — | ~150 行（audit+builder） |
| 检测文件类型 | — | .py/.sh/.bat/.ps1 |
| 违规模式数 | — | 6 种正则 + shell 重定向检测 |

---

### v2.6.0

**发布日期：2026-05-23**
**类型：Minor（规范语义修正 + 路径重命名）**

### 新增/修正内容

#### 规范修正

- **铁律4 语义重写**：从"标准化工具自身备份/报告路径"改为"所有技能运行时产出物统一路径管理"。核心概念从工具自指变为通用规范——日程技能出 `.ics`、任务技能出清单 `.json`、数据处理出缓存，全部走 `<workspace>/standardization/<skill>/` 统一管理。

- **子目录重命名**（更通用）：
  - `backups/` → `data/`（持久化业务数据）
  - `reports/` → `outputs/`（生成/导出产物）
  - `cache/` → 保留（短期缓存）
  - `temp/` → 保留（临时文件）

#### 工具同步

- **skill_builder.py v2.4.0 → v2.5.0**：`_create_backup()` 目标从 `data/`（原 `backups/`），`_save_report()` 目标从 `outputs/`（原 `reports/`）

### 技术细节

| 项目 | v2.5.0 | v2.6.0 |
|------|--------|--------|
| 铁律4 适用范围 | create/update/refactor 三模式 | 所有技能一切运行时 |
| 备份路径 | `.../backups/` | `.../data/` |
| 报告路径 | `.../reports/` | `.../outputs/` |
| skill_builder.py | v2.4.0 | v2.5.0 |

---

### v2.5.0

**发布日期：2026-05-23**
**类型：Minor（工具路径改造）**

### 新增/修正内容

#### 工具改造

- **skill_builder.py v2.2.0 → v2.4.0**：产出物路径全面改造 — `_create_backup()` 备份路径从 `skill_dir.parent` 改为 `<workspace>/standardization/<skill>/backups/`，新增 `_get_workspace_dir()`、`_get_standardization_dir()`、`_save_report()` 辅助函数。update/refactor 模式报告自动落盘到 `<workspace>/standardization/<skill>/reports/`。新增 `--workspace` / `-w` CLI 参数。

#### 设计理由

- 技能更新/重装时备份和报告不再因覆盖而丢失（铁律4落地实现）
- 工作区级隔离，不同 skill 产出物互不污染
- `--workspace` / `-w` 可显式指定，默认使用 `Path.cwd()`

### 技术细节

| 项目 | v2.4.0 | v2.5.0 |
|------|--------|--------|
| skill_builder.py 版本 | v2.1.0 | v2.4.0 |
| 备份路径 | `skill_dir.parent/` | `workspace/standardization/<skill>/backups/` |
| 报告输出 | 仅 stdout | stdout + `reports/*.txt` |
| CLI 参数 | — | + `--workspace` / `-w` |

---

### v2.4.0

**发布日期：2026-05-23**
**类型：Minor（规范新增）**

### 新增/修正内容

#### 规范新增

- **增量更新记录渐进式加载规定**：update/refactor 模式下产出的变更记录必须写入 `references/changelog.md`，禁止写入主 SKILL.md。确保主文件行数可控，详细历史信息按需加载。

- **铁律 4：产出物路径管理规范**（新增）：create/update/refactor 三种模式产生的所有产出物类文件（备份、报告、缓存、临时文件等）统一存至工作区标准化路径 `<workspace>/.workbuddy/standardization/<skill_name>/` 下分门别类子目录（`backups/`、`reports/`、`cache/`、`temp/`），禁止放在技能文件夹下，防止更新覆盖导致积累性产出丢失。

### 技术细节

| 项目 | v2.3.0 | v2.4.0 |
|------|--------|--------|
| 铁律数量 | 3 条 | 4 条（新增铁律4） |
| 渐进式MD规范 | 基本拆分规则 | + 增量changelog加载规则 |
| SKILL.md 行数 | 200 行 | ~250 行（新增2节规范内容） |

---

### v2.3.0

**发布日期：2026-05-23**
**类型：Minor（Bug 修复 + 版本号同步）**

### 新增/修正内容

#### Bug 修复
- `scripts/skill_audit.py`：修复 `yaml_has_description` 在 `fm=None` 时崩溃的问题（`AttributeError: 'NoneType' object has no attribute 'get'`）
  - 根因：`fm` 为 `None` 时直接调用 `fm.get()`
  - 修复：增加 `if has_desc else ""` 守卫

#### 版本号同步
- `scripts/skill_audit.py` 文件头 `v2.2.0` → `v2.3.0`
- `scripts/skill_builder.py` 文件头 `v2.1.0` → `v2.3.0`（之前遗漏未同步）
- SKILL.md `version:` `2.2.0` → `2.3.0`
- `_meta.json` `"version"` `2.2.0` → `2.3.0`

#### SKILL.md 行数控制
- 精简空行，将文件控制在 200 行以内（R-04 渐进式要求）

### 技术细节

| 项目 | v2.2.0 | v2.3.0 |
|------|--------|--------|
| SKILL.md 行数 | 188~203 行（波动） | 200 行（≤200 ✅） |
| skill_audit.py bug | 有（fm=None 崩溃） | 已修复 ✅ |
| skill_builder.py 版本字符串 | v2.1.0（遗漏） | v2.3.0（同步）✅ |

---

## v2.2.0

**发布日期：2026-05-23**
**类型：Minor（功能增强 + 规范完善）**

### 新增/修正内容

#### SKILL.md 结构完善
- 补充 `## 工作流程` 章节（含 AI 执行节奏流程图 + 三模式对照表），R-09 修正为 ✅
- 一级标题加入"渐进式加载示范"语义
- description 更新，体现渐进式加载特性
- tags 新增 `"progressive-loading"`

#### 版本号管理规范化
- **版本号更新文件映射表彻底重做** — 原表只覆盖 SKILL.md/_meta.json/manifest.json，严重不完整
- 新映射表覆盖所有含版本号位置：SKILL.md `version:`、`_meta.json` `"version"`、`scripts/spec/*.json` `"_version"`、`scripts/*.py` 文件头版本字符串
- **铁律 2 重写** — 原规则"不确定就问"与更新器/修改器逻辑冲突，按用户要求改为：
  - 规范内明确定义的文件/字段 → **直接更新，无需询问**
  - 规范未覆盖的文件/字段 → **必须询问用户**

#### 脚本版本号同步
- `scripts/skill_audit.py` 文件头 `v1.0.0` → `v2.2.0`
- `scripts/skill_builder.py` 文件头 `v1.0` → `v2.2.0`

#### 渐进式 MD 体系示范
- SKILL.md 缩减至 188 行（≤200），超标内容拆分至 `references/`
- 移除 `## 版本更新日志`（已拆分至 `references/changelog.md`）
- 新增"本 skill 自身的文件拆分示范"表格
- 所有详细内容正确指向 `references/*.md`

### 技术细节

| 项目 | v2.1.0 | v2.2.0 |
|------|--------|--------|
| SKILL.md 行数 | ~230 行（超标） | 188 行（≤200 ✅） |
| R-09 通过 | ❌ | ✅ |
| 版本号映射覆盖 | 3 个文件 | 全链路（SKILL.md + _meta + spec/*.json + *.py） |
| 铁律 2 逻辑 | "不确定就问"（有误） | "规范内有规定直接更新，无规定必须询问" |

---

## v2.1.0

**发布日期：2026-05-22**
**类型：Minor（功能增强）**

### 新增功能

#### skill_audit.py 独立副本
- skill-standardization 现在包含**自有**的 `skill_audit.py` 副本（522行）
- 与 git-sync 的审查脚本**完全隔离**，各自维护各自的生命周期
- 消除了"与 git-sync 共享"的跨 skill 依赖
- 支持独立执行：`python scripts/skill_audit.py audit <skill_dir>`

### 变更内容

#### Skill 隔离化
- SKILL.md 移除"与 git-sync 共享"措辞，明确各 skill 脚本独立性
- 规范文件结构说明更新，标注 skill_audit.py 为 `[v2.1新增]`

### 技术细节

| 项目 | v2.0.1 | v2.1.0 |
|------|--------|--------|
| 脚本数量 | 3 (builder + json_loader) | 4 (+audit 独立副本) |
| 跨 skill 依赖 | 有 (audit 来自 git-sync) | 无 (完全自包含) |

---

## v2.0.1

**发布日期：2026-05-22**
**类型：Patch（修复）**

### 变更内容

#### 目录重命名
- `docs/` → `references/` — 对齐标准规范中的渐进式 MD 目录命名
- 更新所有内部引用路径

---

## v2.0.0（重大升级）

**发布日期：2026-05-22**
**类型：Major（重大升级）**

### 新增功能

#### skill_builder.py 构建器
- **create 命令** — 从模板初始化完全符合标准的 skill 目录结构
  - 自动生成 SKILL.md（含 frontmatter + TODO 占位符模板）
  - 自动生成 _meta.json（五字段标准元数据）
  - 创建 references/ 和 scripts/ 占位目录
  - 支持 `--desc`、`--dir`、`--tags` 参数自定义

- **update 命令** — 对已有 skill 进行增量规范化检查
  - 检查 _meta.json 存在性和字段完整性（可自动修复）
  - 检查 SKILL.md frontmatter 和必填章节
  - 文件大小合理性提示（>200 行建议拆分）
  - 根目录规范性检查
  - 支持 `--fix` 自动修复和 `--backup` 备份

- **refactor 命令** — 非标 skill 整体结构改造
  - 全量扫描文件生成清单（路径+大小+时间）
  - 按 M-01~M-06 规则自动归类移动文件
  - 强制备份机制（时间戳命名）
  - 信息零丢失验证（字节一致性检查，允许 1% 容差）
  - 完整迁移映射表输出
  - 支持 `--dry-run` 预览模式

#### 标准目录结构规范
- 新增 `spec/structure.json` — 目录结构规范定义
- 定义三级复杂度模型（minimal / standard / full）
- 明确根目录仅允许 SKILL.md + _meta.json
- 规范子目录用途：references/（渐进式MD）、scripts/（脚本）、assets/（资源）、tests/（测试）

#### 渐进式 MD 文件体系
- 新增 `spec/progressive_md.json` — 渐进式MD体系规范
- 定义主文件 vs 辅助文档的拆分边界
- 明确加载协议（SKILL.md 独立可用 → 复杂任务按需加载 references/）
- 标准化引用语法（→ 语法指向渐进式文件）
- 注册 6 个标准渐进式文件名

#### spec/_index.json 模块索引
- 新增集中式模块注册表
- 支持依赖声明（_depends_on）
- 统一版本号管理（_version）
- 为 json_loader.py 提供模块发现能力

### 变更内容

#### 审查策略升级
- **git-sync 集成模式变更**: ERROR 级问题不再导致 exit(1)
- **纯警告模式**: skill_audit.py 始终返回退出码 0
- **不阻断同步**: git-sync 收到退出码 0 后继续执行后续步骤
- **向后兼容**: 保留 --strict 参数支持严格模式（可选）

#### SKILL.md 结构重构
- 主文件从单一大文档精简为 ≤200 行核心版
- 详细内容拆分到 references/ 渐进式 MD 文件
- 新增三种执行模式详解章节（create/update/refactor）
- 新增标准目录结构规范章节
- 新增渐进式 MD 文件体系章节
- 新增规范文件结构说明章节

### 技术细节

| 项目 | v1.0 | v2.0 |
|------|------|------|
| 脚本数量 | 2 (audit + json_loader) | 4 (audit + json_loader + builder) |
| Spec 文件数 | 3 (frontmatter + body + rules) | 6 (+ structure + progressive_md + _index) |
| CLI 命令数 | 2 (audit + load/list/show) | 8 (create/update/refactor + audit + load/list/show/refs) |
| 文档文件数 | 1 (SKILL.md) | 7 (SKILL.md + 6个references/*.md) |
| 迁移规则数 | 0 | 6 (M-01 ~ M-06) |

### 已知限制

1. create 模板目前硬编码在源码中（未来计划支持外部模板）
2. update --fix 仅能修复 _meta.json 相关问题
3. refactor 不处理文件内容的修改（仅移动位置）
4. 审查规则暂不支持外部自定义规则文件
5. 无单元测试套件（v2.1 计划补充）

---

## v1.0.0（初始版本）

**发布日期：2025-xx-xx**
**类型：初始发布**

### 新增功能

#### 核心 Skill 结构
- 基于 **SKILL.md 标准化规范草案 v0.1** 创建完整 skill
- 实现 **R-01 ~ R-10** 共 10 条自动审查规则
  - R-01: Frontmatter 存在性检查
  - R-02: name 字段检查
  - R-03: version SemVer 格式检查
  - R-04: description 字段检查
  - R-05: name 与目录名一致性检查
  - R-06: 正文一级标题检查
  - R-07: 触发条件章节检查
  - R-08: 核心能力章节检查
  - R-09: 工作流程章节检查
  - R-10: version 一致性检查

#### 工具脚本
- **skill_audit.py** — 独立审查工具
  - `audit` 子命令：对指定 skill 目录执行全量审查
  - `--json` 参数：输出结构化 JSON 结果
  - `--strict` 参数：严格模式（ERROR 级 exit(1)）
  - 同义词模糊匹配支持
  - 人类可读 + 机器可读双格式输出

- **json_loader.py** — 渐进式 JSON 加载器
  - `load` 子命令：按需加载指定 spec JSON
  - `list` 子命令：列出所有可用模块
  - `show` 子命令：显示模块详细信息
  - 从 `_index.json` 读取模块注册信息

#### Spec 规范定义
- **spec/frontmatter.json** — 字段规范（3必须 + 7可选）
- **spec/body.json** — 正文章节规范（5必须 + 4推荐 + N可选）
- **spec/rules.json** — 审查规则完整定义

#### Git-Sync 集成
- 提供 git-sync 步骤 3.5 自动审查入口
- 双模式运行：独立 CLI / git-sync 子进程调用
- ERROR 级默认退出非零码（v2.0 已改为纯警告模式）

### 设计原则
- 零外部依赖（纯 Python 标准库）
- 跨平台兼容（Windows/Linux/macOS）
- UTF-8 编码统一
- 人类优先的可读性设计

---

## 版本路线图（Roadmap）

### v2.1.0（计划中）

- [ ] 单元测试套件（覆盖 create/update/refactor/audit 全路径）
- [ ] create 外部模板文件支持
- [ ] update --fix 增强（frontmeter 补充、章节模板插入）
- [ ] 版本号自动同步工具（一键更新所有位置）

### v2.3.0（计划中）

- [ ] 审查规则外置配置（支持 .skillrc 或 rules_custom.json）
- [ ] refactor 内容感知移动（根据文件内容智能判断目标目录）
- [ ] 多语言 SKILL.md 支持（i18n 模板）
- [ ] 交互式 create 向导模式

### v3.0.0（远期规划）

- [ ] Skill 间依赖关系管理
- [ ] Schema 校验增强（JSON Schema 验证）
- [ ] Web UI 管理界面
- [ ] 插件系统（第三方规则扩展）

---

*本文件由 skill-standardization v2.7.3 维护。*
*最后更新：2026-05-23*
