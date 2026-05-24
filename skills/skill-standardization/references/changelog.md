# 更新日志（Changelog）

> 本文件记录 skill-standardization 的版本变更历史。
> 遵循 [Keep a Changelog](https://keepachangelog.com/) 格式，基于 SemVer 版本管理。

---

## 目录

- [v2.14.0（当前版本）](#2140-当前版本)
- [v2.13.4](#2134)
- [v2.13.3](#2133)
- [v2.13.2](#2132)
- [v2.13.1](#2131)
- [v2.13.0](#2130)
- [v2.12.2](#2122)
- [v2.12.1](#2121)
- [v2.12.0](#2120)
- [v2.10.1](#2101)
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

### v2.15.0（当前版本）

**完整授权注入系统 — 从 Markdown 描述升级为可执行授权代码**

### 新增
- **`_render_auth_check_py()` 重写**：改用逐行拼接，彻底解决模板转义问题（`{{}} → 实际输出为 `{{}}` 导致语法错误）
- **`_generate_auth_check_py()`**：根据权限检查报告生成 `scripts/auth_check.py` 并写入磁盘
- **`_inject_auth_imports()`**：在技能 `scripts/` 下所有 `.py` 文件头部注入 `from auth_check import authorize, initialize`
- **`_inject_initialize_calls()`**：在所有 `scripts/*.py` 的 `if __name__ == "__main__":` 块内注入一次 `initialize()` 调用
- **`_inject_auth_calls()`**：在每个高风险操作所在行之前注入 `if not authorize("rule_name", "description"): return` 调用（按文件分组，插入位置按倒序处理以防行号偏移）
- **`refactor.py` 同步更新**：通过 Agent 将 `updater.py` 的授权注入方法完整同步到 `refactor.py`，包含 `_render_auth_check_py / _generate_auth_check_py / _inject_auth_imports / _inject_initialize_calls / _inject_auth_calls / _run_permission_checker / _inject_auth_section`

### 修复
- **授权方式智能判断**：`permission_checker.py` 的 `suggest_authorization_methods()` 根据技能工作性质（`automated` / `interactive`）决定授权方式，而非一刀切按 severity 判死
- **注入逻辑完善**：`_inject_auth_section()` 现在调用上述所有新方法，实现完整授权系统注入（生成 `auth_check.py` + 注入 `authorize()` 调用 + 注入 SKILL.md 文档章节）

### 影响范围
- `scripts/skill_builder/updater.py`：新增 7 个授权注入方法，`_inject_auth_section()` 重写为完整注入流程
- `scripts/skill_builder/refactor.py`：同步更新（Agent 执行），支持 `--inject-auth` 参数
- `references/changelog.md`：新增本条目

---

## v2.14.0（当前版本）

**发布日期：2026-05-24**
**类型：Minor（授权方式智能判断：根据技能工作性质决定 unified/immediate/silent）**

### 新增
- `permission_checker.py`：新增 `_detect_skill_nature()` 方法，自动判断技能工作性质（自动化/交互式）
- `permission_checker.py`：`suggest_authorization_methods()` 重写，根据技能性质智能决定授权方式
- `permission_checker.py`：`scan()` 方法新增调用 `suggest_authorization_methods()` 并将结果合并进 issues
- `updater.py` / `refactor.py`：`inject_auth_section()` 改为读取 report 中的 `authorization_method` 字段，不再自行按 severity 判死

### 修复
- 修复授权方式一刀切问题（全部判为 immediate），现根据技能性质智能判断

---

### v2.13.4

**发布日期：2026-05-24**
**类型：Minor（新增 --inject-auth 参数，支持自动注入授权要求章节）**

### 新增
- **`skill_builder/updater.py`**：新增 `_run_permission_checker()` 和 `_inject_auth_section()` 方法，支持在 update 模式下扫描目标技能风险操作并注入授权要求章节
- **`skill_builder/refactor.py`**：同上，在 refactor 模式下注入授权要求章节
- **`skill_builder/__init__.py`**：为 `update` 和 `refactor` 子命令新增 `--inject-auth` 参数
- **`scripts/permission_checker.py`**：新增 `suggest_authorization_methods()` 方法，为每个风险操作建议授权方式（静默/统一/即时）

### 修复
- 无

---

### v2.13.3

**发布日期：2026-05-24**
**类型：Patch（增加完整性校验）**

### 新增
- **permission_checks.py v2.13.3**：`_run_permission_checker()` 增加 `permission_checker.py` 的 SHA-256 哈希完整性校验
- **脚本哈希存储**：`~/.workbuddy/skills/.standardization/skill-standardization/script_hashes.json`
- **哈希不匹配警告**：检测到 `permission_checker.py` 被篡改时输出警告

### 修复
- **重复 import os**：移除 `_run_permission_checker()` 函数内的重复 `import os`

---

### v2.13.2

**发布日期：2026-05-24**
**类型：Patch（修复 permission_checker.py 假阳性）**

### 修复

- **SENSITIVE_PATTERNS**：为所有凭证相关正则添加单词边界（），避免误匹配错误处理代码中的关键词列表（如 unauthorized、token、credential）
- **DELETE_PATTERNS**：移除 r"del "（误匹配 Python del 变量删除语句），保留 os.remove/os.rmdir/shutil.rmtree/unlink/rm/rmdir 等真实文件删除检测
- **permission_checker.py v1.0.1**：降低 skill-sub 等 skill 的假阳性风险等级

---

### v2.13.1（当前版本）

**发布日期：2026-05-24**
**类型：Patch（修复 R-15 误匹配）**

### 修复

- **R-15 检查逻辑**：`auth_patterns` 中 `r"authorize"` 误匹配 `unauthorized` 等子串，改为 `r"\bauthoriz\w*\b"`（单词边界），消除假阳性
- **`skill_audit/permission_checks.py`**：精确化授权检查正则，避免非授权相关关键词触发误报

---

### v2.13.0（当前版本）

**发布日期：2026-05-24**
**类型：Minor（安全增强 — 权限检查 + 授权管理 + 代码重构）**

### 新增

- **R-13~R-17 规则**：敏感信息访问声明、关键位置写入声明、高权限操作授权检查、权限权重说明、渐进加载引用强制
- **`permission_checker.py` v1.0.0**：权限检查器，扫描 skill 脚本，提取文件操作，计算权限权重，生成风险报告
- **`authorization_manager.py` v1.0.0**：授权管理器，统一审批 + 即时审批，防止未授权高风险操作
- **`skill_audit.py` R-13~R-17 检查方法**：调用 `permission_checker.py` CLI 进行权限检查

### 变更

- `skill_audit.py` v2.12.2 → v2.13.0
- `skill_builder.py` v2.12.2 → v2.13.0（update 模式调用 `permission_checker.py`）
- `SKILL.md` v2.12.2 → v2.13.0（从 267 行降至 198 行，符合 R-17）

### 重构

- **`skill_builder.py` → `skill_builder/` 包**：面向对象重构，拆分为 6 个模块（~200-300 行/模块）
  - `creator.py`：SkillCreator 类，负责 create 模式
  - `updater.py`：SkillUpdater 类，负责 update 模式
  - `refactor.py`：SkillRefactor 类，负责 refactor 模式
  - `version_manager.py`：VersionManager 类，负责版本号管理
  - `utils.py`：工具函数（备份、模板等）
  - `__init__.py`：主入口 + argparse 解析
  - `__main__.py`：支持 `python -m skill_builder` 执行
- **`skill_audit.py` → `skill_audit/` 包**：面向对象重构，拆分为 6 个模块（~200-300 行/模块）
  - `frontmatter_checker.py`：R-01~R-05、R-10 检查函数
  - `structure_checker.py`：R-06~R-09 检查函数
  - `artifact_checker.py`：R-11、R-12 检查函数
  - `permission_checks.py`：R-13~R-17 检查函数
  - `utils.py`：常量定义和工具函数
  - `__init__.py`：主入口 + `audit_skill()` + `format_report()` + CLI 命令
  - `__main__.py`：支持 `python -m skill_audit` 执行
- **版本号管理改进**：`_bump_version` 移除自我修改行为，版本号权威来源改为 `_meta.json`
- **触发条件精确化**：SKILL.md 增加精确触发词 + 否定条件，避免误触发
- `_meta.json` v2.12.2 → v2.13.0
- `references/guide.md` 新增"安全增强功能（v2.13.0）"章节
- `references/reference.md` 更新审查规则一览表（R-01~R-17）
- `references/rules.md` 新增 R-13~R-17 规则详解

### 修复

- `skill_audit.py` METHOD_MAP 缺少 R-13~R-17 方法映射（已添加）
- `permission_checker.py` 对 semantic-split 误判为高风险（已修复权重计算逻辑）

---

### v2.12.2（当前版本）

**发布日期：2026-05-23**
**类型：Patch（R-12 检测范围补全 — references/*.md 路径扫描）**

### 修复

- **R-12 检测盲区**：`references/*.md` 中硬编码的数据目录路径（如 `~/.workbuddy/semantic-split/data/`）未被检测。原 R-12 只扫描 `scripts/*.py` 中的 `DATA_DIR` 变量，不扫描 md 文件中的路径文字。新增「阶段6：references/*.md 数据目录路径检查」，对不含 `.standardization/` 的数据目录路径报违规
- 同步修复 `skill_builder.py` 的 R-12 检测，新增同样的阶段6

### 变更

- `skill_audit.py` v2.12.1 → v2.12.2
- `skill_builder.py` v2.12.1 → v2.12.2
- SKILL.md v2.12.1 → v2.12.2
- `_meta.json` v2.12.1 → v2.12.2

---

### v2.10.1

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

## v2.12.1

### 修复

- **R-12 `_meta.json` data_dir 末尾斜杠误报**: `_meta.json` 的 `data_dir` 值为 `.standardization/semantic-split/data/`（带末尾 `/`），而代码 `DATA_DIR` 由 `Path` 对象转字符串后无末尾 `/`，`os.path.normpath` 归一化后仍不一致。修复：比较前统一 `rstrip(os.sep)` 去除末尾分隔符。
- **skill_builder.py R-12 同源误报**: `skill_builder.py` 的 `_check_external_data_dir()` 中，`meta_abs` 拼接了 `ws_check` 前缀但 `code_norm` 未拼接，且归一化方式不一致（`replace` vs `normpath`）。修复：两边统一 `os.path.normpath` + `rstrip(os.sep)` + `replace("\\", "/")` + `lower()`。

### 变更

- `skill_audit.py` v2.12.0 → v2.12.1
- `skill_builder.py` v2.12.0 → v2.12.1
- SKILL.md v2.12.0 → v2.12.1
- `_meta.json` v2.12.0 → v2.12.1

---

## v2.12.0

> 变更记录未单独追加（从 v2.10.1 直接跳至 v2.12.0，含 R-12 磁盘存在性检查增强等）

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
# Changelog — skill-standardization

---

## v2.13.0 (YYYY-MM-DD)

### 新增功能
- 新增 R-13~R-17 安全审查规则（敏感信息访问声明、关键位置写入声明、高权限操作授权检查、权限权重说明、渐进加载强制）
- 新增 `scripts/permission_checker.py`（扫描脚本权限、计算权重、生成风险报告）
- 新增 `scripts/authorization_manager.py`（统一审批 + 即时审批，防止未授权高风险操作）
- `skill_builder.py` 的 `cmd_update` 模式现在自动调用 `permission_checker.py` 进行权限扫描

### 规则调整
- R-07：严重度 WARN → ERROR，增加触发条件合规性检查（正向触发词≥3、否定条件≥1、禁止危险表述）
- R-10：检查目标从 `manifest.json` 改为 `_meta.json`，与铁律2版本号更新规则一致
- R-11：严重度 WARN → ERROR，增加路径遍历检测、跨目录写入检测、敏感信息检测
- R-12：严重度 WARN → ERROR，增加数据泄露风险检测

### 文档更新
- `SKILL.md` 描述更新为 v2.13.0（安全增强版），frontmatter 新增 `sensitive_access: false` 和 `critical_write: false`
- `_meta.json` 版本号和描述更新
- `references/guide.md` 追加安全增强功能章节
- `references/reference.md` 追加 `permission_checker.py` 和 `authorization_manager.py` CLI 参考
- 新增 `references/rules.md`（铁律条款详解，从 SKILL.md 拆分）

### 修复
- 修复 R-10 检查逻辑，改为比对 `_meta.json` 而非 `manifest.json`
- 修复 `skill_builder.py` 缺少 `import subprocess` 的问题

---

## v2.12.2 (2025-XX-XX)

### 修复
- 修复 R-11 路径检测逻辑
- 修复 R-12 外部数据目录检查

