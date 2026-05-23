# 更新日志（Changelog）

> 本文件记录 skill-standardization 的版本变更历史。
> 遵循 [Keep a Changelog](https://keepachangelog.com/) 格式，基于 SemVer 版本管理。

---

## 目录

- [v2.10.1（当前版本）](#2101-当前版本)
- [v2.10.0](#2100)
- [v2.9.0](#290)
- [v2.8.2](#282)
- [v2.8.1](#281)
- [v2.8.0](#280)
- [v2.7.3](#273)
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

### v2.10.1（当前版本）

**发布日期：2026-05-23**
**类型：Patch（R-11/R-12 假阳性修复 — 路径比较器规范化 + 中文标点过滤）**

### 修复

- **R-12 _meta.json vs 代码路径比较**: `_meta.json data_dir` 用相对路径（`standardization/...`），代码 `DATA_DIR` 解析为绝对路径（`C:\Users\...\standardization\...`）→ 直接字符串比较永远失败。修复：将 `meta_data_dir` 按 workspace root 解析为绝对路径后再比较。
- **R-12 路径分隔符假阳性**: `os.path.normpath()` 在 Windows 下将 `/` 转为 `\`，但 `expected_pattern` 保留 `/` → `expected_pattern not in norm` 在 Windows 上误报。修复：`expected_pattern` 同样通过 `os.path.normpath()` 规范化。
- **R-11 中文标点误收**: 路径提取正则 `[^"\')\s,]+` 不排除中文标点 `。，；：！？、…—` → docstring 末尾 `。` 被收入路径 `standardization/semantic-split/data/。`。修复：扩展排除字符集。

### 变更

- `skill_audit.py` v2.10.0 → v2.10.1（2 处修复）
- `skill_builder.py` v2.10.0 → v2.10.1（2 处修复）
- SKILL.md v2.10.0 → v2.10.1
- `_meta.json` v2.10.0 → v2.10.1

### 验证

批量审查 6 个技能（git-sync, skill-sub, triphasic-execution, everything-search-breadmemory, semantic-split, skill-standardization）：
- everything-search-breadmemory: PASS（原 5 处 R-12 违规 → 全部消除）
- semantic-split: PASS（原 3 处 R-12 违规 → 全部消除）
- 其余 4 个技能：PASS

---

### v2.10.0

**发布日期：2026-05-23**
**类型：Minor（正则器自我修复 — cmd_update 接入 R-12 + R-11/R-12 磁盘路径验证增强）**

### 修复

- **P0**: `cmd_update()` 接入 R-12 外部数据目录检查（此前 update 模式完全跳过 R-12，报告误报"0 ERROR"）
  - 新增 `_check_external_data_dir()` 函数（5 阶段：变量扫描 → 路径约定检查 → _meta.json 声明 → 一致性校验 → 磁盘存在性）
  - 新增 `_DATA_VAR_RE` 通用变量检测模式
  - 新增 `_extract_path_value()` 路径提取函数
- **P1**: R-12 增加磁盘路径真实性验证（`skill_audit.py` + `skill_builder.py`）
  - 新增 `_find_workspace_root()` / `_get_workspace_dir()` 统一解析工作区根目录
  - 检查 `standardization/<skill>/data/` 目录在磁盘上真实存在
  - 目录不存在时报告 `DISK` 级违规
- **P2**: R-11 增加标准化路径磁盘验证
  - 新增 `_verify_standardization_paths()` / `_verify_standardization_paths_builder()`
  - 对脚本中声称的 `standardization/...` 路径验证磁盘存在性
  - 路径声明了但目录不存在 → 报告违规
- **P3**: `skill_audit.py` 版本描述修正（"R-01~R-11" → "R-01~R-12"）
  - 文件头注释、CLI epilog、CLI description 三处同步

### 变更

- `skill_builder.py` v2.9.0 → v2.10.0
- `skill_audit.py` v2.9.0 → v2.10.0
- SKILL.md v2.9.0 → v2.10.0
- `_meta.json` v2.9.0 → v2.10.0

### 设计原则

正则器必须先把自己修正确。R-12 定义后从未在 update 模式执行；R-11/R-12 仅做子串匹配不验证磁盘路径，导致虚假放行。本次修复补上了这两个关键缺口。

---

### v2.9.0

**发布日期：2026-05-23**
**类型：Minor（版本号自动更新 + changelog 自动追加 + 路径描述彻底泛化）**

### 新增

- **`--version-bump` 参数**（patch/minor/major）：`cmd_update()` 自动升级版本号
  - 更新 SKILL.md frontmatter `version:`
  - 更新 `_meta.json` `"version"`
  - 更新 `skill_builder.py` `__version__` + 文件头版本注释
  - 更新 `skill_audit.py` 文件头版本注释
- **`--changelog` 参数**：与 `--version-bump` 联动，自动追加变更记录到 `references/changelog.md`
  - 遵循 Keep a Changelog 格式
  - 自动写入发布日期和版本号

### 修复

- **R-12 路径描述彻底泛化**：三处 `~/.workbuddy/<skill>/` 替换为 `standardization/<skill>/`
  - `SKILL.md` R-12 审查规则描述
  - `skill_audit.py` RULES[11] check 字段
  - `changelog.md` v2.8.0 条目
- **changelog.md v2.8.0 条目**：`data_dir` 默认值路径同步修正
- 补全 v2.8.1、v2.8.2 缺失的 changelog 条目

### 根因分析

此前版本号不更新、changelog 不写的根因：
- `cmd_update()` 是纯检查/报告工具，没有版本管理逻辑
- 版本号映射表是纯文档，无代码执行
- 完全依赖 AI 按 SKILL.md 文档手动操作，人类和 AI 都会遗漏

---

### v2.8.2

**发布日期：2026-05-23**
**类型：Patch（_get_workspace_dir 根本性修复 + 版本号全线同步）**

### 修复

- **`_get_workspace_dir()` 重写**：从 `Path.cwd()` 改为从 skill_dir 向上遍历查找 `.workbuddy` 目录，父目录为 workspace 根
- 版本号全线同步：SKILL.md、_meta.json、skill_builder.py header+`__version__`、skill_audit.py header → 2.8.2

---

### v2.8.1

**发布日期：2026-05-23**
**类型：Patch（R-12 路径泛化 v1 + skill_builder fix 逻辑修正）**

### 修复

- R-12 变量检测泛化：4个硬编码 → `DATA|STORAGE|DB|CACHE|CONFIG` + `_DIR|_PATH` 广义模式
- R-12 预期路径从 `~/.workbuddy/<skill>/data/` → `standardization/<skill>/data/`
- skill_builder fix 逻辑 bug：两处 `~/.workbuddy/{name}/data/` 默认值修正为 `standardization/{name}/data/`
- rules.json、META_TEMPLATE 同步更新

---

### v2.8.0

**发布日期：2026-05-23**
**类型：Minor（新增 R-12 外部数据目录规范性检查）**

### 新增

- **R-12 外部数据目录规范性**（WARN 级）
  - 扫描 scripts/ 中所有文件，提取 DATA_DIR/data_dir 等变量赋值
  - 检查路径是否在 `standardization/<skill-name>/` 下（与铁律4同一目录，非框架绑定）
  - 检查 `_meta.json` 是否声明 `data_dir` 字段
  - 检查 `_meta.json` data_dir 与实际代码路径是否一致
- **`_meta.json` 模板新增 `data_dir` 字段**
  - META_TEMPLATE 新增 `"data_dir": "standardization/<name>/data/"`
  - update 模式新增 `data_dir` 到 required_meta_keys（默认值 `standardization/<name>/data/`）
  - fix 模式下自动补充缺失的 `data_dir` 字段

### 变更

- `skill_audit.py` v2.7.0 → v2.8.0
- `skill_builder.py` v2.7.0 → v2.8.0
- `scripts/spec/rules.json` v2.5.0 → v2.6.0，_total_rules: 11→12，_warn_count: 7→8
- SKILL.md 规则列表新增 R-12

### 修复

- 修正 SKILL.md R-11 描述不完整（补充"非标准子目录 + 全目录交叉引用追踪"）
- 修正 `references/changelog.md` 路径引用错误（`spec/rules.json` → `scripts/spec/rules.json`）

---

### v2.7.3

**发布日期：2026-05-23**
**类型：Patch（修正 changelog 路径引用 + 规范内版本号对齐）**

### 变更

- `references/changelog.md`：`spec/rules.json` 路径修正为 `scripts/spec/rules.json`
- `references/changelog.md`：footer 版本号 v2.7.0 → v2.7.3

---

### v2.7.2

**发布日期：2026-05-23**
**类型：Patch（R-11 建议路径冗余修复）**

### 修复

- R-11 建议路径冗余：`data/data/test.json` → `data/test.json`
- 优化建议信息展示格式

---

### v2.7.1

**发布日期：2026-05-23**
**类型：Patch（R-11 扩展测试验证）**

### 修复

- R-11 扩展功能验证通过（mock 技能 8 处违规全部检出）
- 微调违规建议文案

---

### v2.7.0

**发布日期：2026-05-23**
**类型：Minor（R-11 非标准子目录扫描扩展）**

### 新增

- **R-11 非标准子目录扫描**：在根目录文件检测之外，新增产出物目录递归扫描
  - `_ARTIFACT_DIR_CLASSIFY`：30+ 产出物目录名 → (分类, 描述) 映射（data/cache/outputs/temp 四类）
  - `_ARTIFACT_EXTS_COMPREHENSIVE`：50+ 产出物文件扩展名全面定义，按分类组织
  - `_check_artifact_directories`：检测根目录非标准子目录（data/cache/outputs/temp/logs/等）
  - `_scan_dir_recursive`：递归扫描产出物目录内所有文件，生成迁移建议
  - `_scan_unknown_dir`：对未匹配的未知目录，通过内容分析推断是否为产出物目录
  - **嵌套检测**：同时扫描 scripts/ 和 references/ 下的非标准子目录
- **产出物分类体系 v2**：
  - `data/` — 持久化数据：`.db`/`.json`/`.csv`/`.pkl`/`.parquet`/`.npy` 等
  - `cache/` — 缓存：`.cache` 目录及缓存文件
  - `outputs/` — 输出产物：`.html`/`.pdf`/`.png`/`.xlsx`/`.log` 等
  - `temp/` — 临时文件：`.tmp`/`.bak`/`.swp`/`.lock`/`.pid` 等

### 变更

- `skill_audit.py` v2.6.0 → v2.7.0
- `skill_builder.py` v2.6.0 → v2.7.0
- R-11 描述更新为："scripts/ + 根目录 + 非标子目录 产出路径规范 + 全目录交叉引用追踪"

---

### v2.6.0

**发布日期：2026-05-22**
**类型：Minor（SKILL.md 审查规则 R-09/R-10 回调 + 完整化）**

### 新增

- **R-10 版本一致性检查**：SKILL.md `version:` 与 `manifest.json` 记录对比
- **铁律 2 完善**：规范内明确定义的文件/字段 — 直接更新，无需询问

### 变更

- R-09 名称从"工作流程/使用方式章节"简化为"工作流程章节"
- R-09/R-10 从 ERROR 降为 WARN（不阻断 git-sync）
- `scripts/spec/rules.json` v2.3.0 → v2.4.0
- _total_rules: 10 → 11，_error_count: 4 → 4，_warn_count: 6 → 7

### 修复

- 铁律 2 澄清：规范未覆盖的字段（如 `manifest.json` 版本）必须询问用户

---

### v2.5.0

**发布日期：2026-05-22**
**类型：Minor（铁律 2 增强 + 版本号决策树）**

### 新增

- **铁律 2 决策树**：规范内明确定义 vs 未覆盖 → 直接更新 vs 必须询问
- **版本号更新映射表**：6 种修改类型 × 对应文件 × 升级类型
- **`--workspace` 参数**：指定工作区根目录（用于铁律 4 路径建议）

### 变更

- SKILL.md 新增"版本号更新文件映射表"章节
- `skill_audit.py` / `skill_builder.py` 帮助信息更新

---

### v2.4.0

**发布日期：2026-05-22**
**类型：Minor（R-09/R-10 规则新增 + 铁律 2 完善）**

### 新增

- **R-09 工作流程章节**（WARN）：检查正文含"工作流程"/"使用方式"等章节
- **R-10 版本一致性**（WARN）：SKILL.md version 与 `_meta.json` version 对比
- **铁律 4 细化**：目录分类表（data/cache/outputs/temp 四类的典型文件示例）

### 变更

- _total_rules: 8 → 10，_warn_count: 4 → 6
- `scripts/spec/rules.json` v2.2.0 → v2.3.0

---

### v2.3.0

**发布日期：2026-05-22**
**类型：Minor（铁律 1/2/3/4 全面补充）**

### 新增

- **铁律 1**：author 字段不可擅自替换（默认值 `your-name-here`）
- **铁律 2**：版本号更新规则（规范内有规定直接更新，无规定必须询问）
- **铁律 3**：改写前必须理解每个文件的作用
- **铁律 4**：产出物路径管理规范（`<workspace>/standardization/<skill>/` 四分类）
- **`references/architecture.md`**：架构设计文档（按需加载）

### 变更

- SKILL.md 正文从 ~80 行拆分为 ~60 行 + `references/` 下 6 个 MD
- 触发场景描述更精准
- `scripts/spec/rules.json` v2.1.0 → v2.2.0

### 修复

- SKILL.md 拼写错误修正

---

### v2.1.0

**发布日期：2026-05-21**
**类型：Minor（R-05~R-08 规则新增 + 审查工具完善）**

### 新增

- **R-05 名称一致性**（WARN）：frontmatter name 与目录名对比
- **R-06 一级标题**（WARN）：正文 `# ` 检测
- **R-07 触发条件**（WARN）：同义关键词映射（`TRIGGER_KEYWORDS`）
- **R-08 核心能力**（WARN）：同义关键词映射（`CORE_KEYWORDS`）
- **`skill_audit.py`**：独立 CLI 工具 + `--json` 输出模式（供 git-sync 调用）

### 变更

- _total_rules: 4 → 8，_warn_count: 0 → 4
- `scripts/spec/rules.json` v2.0.0 → v2.1.0

---

### v2.0.1

**发布日期：2026-05-21**
**类型：Patch（BUG 修复）**

### 修复

- `skill_audit.py`：修复 `--json` 模式下中文编码错误（Windows）
- `skill_builder.py`：`--help` 信息错误修正

---

### v2.0.0（重大升级）

**发布日期：2026-05-21**
**类型：Major（架构重构 + 规则引擎）**

### 新增

- **规则引擎 R-01~R-04**：Frontmatter 存在性 / name 字段 / version SemVer / description 字段
- **三种执行模式**：`create` / `update` / `refactor`
- **渐进式 MD 体系**：主文件 ≤200 行，辅助内容拆分 `references/`
- **`scripts/spec/rules.json`**：规则持久化定义（独立维护）
- **`scripts/json_loader.py`**：按需加载规范模块

### 变更

- 从 v1.x 单文件模式重构为三文件体系（`skill_audit.py` + `skill_builder.py` + `spec/rules.json`）
- SKILL.md 从操作指南转型为"技能本身就是规范的示范"

---

### v1.0.0（初始版本）

**发布日期：2026-05-20**
**类型：Initial**

- 初始版本：单文件 `skill_audit.py` 嵌入规则
- 支持 SKILL.md frontmatter 基础检查
- 手动修复建议（无自动 fix 模式）

*本文件由 skill-standardization v2.10.0 维护。*
