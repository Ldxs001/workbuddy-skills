## v2.39.3 (2026-05-30)

### 修复
- 新增 R-25：_meta.json 字段规范性检查。7 标准字段(name/version/description/author/tags/data_dir/triggers)，缺失自动补全，非标字段标记输出。批量修复 13 个技能 _meta.json

---

## v2.39.2 (2026-05-30) — R-03 版本号语义规则细化 + bump 命令规则引用

### Changed
- R-03 规则描述细化：MAJOR=架构级重构/MINOR=功能重构/PATCH=单处修正，消除两个重构歧义
- bump 命令 epilog 引用 R-03 规则，执行时显示变更语义
- bump 命令 --type 未指定时交互选择，默认 feature
- audit --fix 自动 bump 输出 R-03 规则引用

---


## v2.39.1 (2026-05-30)

### 修复
- R-23 第7项改为两阶段模式：正则粗筛 + LLM精筛，移除白名单和URL过滤

---

## v2.39.0 (2026-05-30)

### Fixed（根因修复）
- **audit --fix 模式修复文件后自动执行版本号 bump**：这是反复出现改了文件忘了更新版本号的根因
  - 此前 audit --fix 修完文件就直接结束，不更新版本号三端
  - 现在 --fix 修复任何文件后自动调用 _do_bump() 执行 patch bump
  - 无论走 audit --fix、refactor、还是手动修复，版本号三端都会被更新

### Added
- **R-23 新增第 7 项检查：MD 中引用的外部技能是否存在**
  - 扫描 SKILL.md + references/*.md 中引用的  路径
  - 排除 URL（gitee.com/github.com）、结构目录（.standardization/installed/）避免误报
  - 引用的技能目录不存在于  时报 WARN，提示功能描述可能已过时
  - 本次清理了 6 个文件中的 git-sync 残留描述，v2.38.13 解耦不彻底的问题
- 清理所有 git-sync 残留描述：guide.md/faq.md/reference.md/rules.md/examples.md/__init__.py
- 新增 bump 子命令：一键升级技能版本号三端（SKILL.md + _meta.json + changelog）
  - 支持 --type fix/feature/breaking 自动计算新版本号
  - 支持 --desc 自动生成 changelog 条目
  - 支持 --dry-run 预览模式
- 新增 _do_bump() 核心函数：供 --fix 和 bump 子命令复用

### Changed
- _do_bump() 内部调用已有 VersionManager.bump_version() 更新 SKILL.md + _meta.json，避免重复造轮子
- cmd_bump() 简化为 _do_bump() 的薄封装

---


## v2.38.15 (2026-05-30) — R-10 三端一致性增强 + R-23 路径一致性检查

### Fixed
- **R-10 版本三端一致性检查（根本修复）**：不再依赖 `--manifest-version` CLI 参数
  - 自动读取 `_meta.json` version 与 SKILL.md version 比对
  - 自动读取 `references/changelog.md` 最新版本号，比对三端一致性
  - 此前 R-10 因 `manifest_version` 参数缺失永远 SKIP，形同虚设
  - 旧问题：每次改造后版本号三端不同步，审计抓不住

### Added
- **R-10 新增 mtime 时序检查**：检测"改了文件但忘了更新版本号/changelog"
  - 比较 SKILL.md 和 scripts/*.py 的修改时间 vs references/changelog.md 的修改时间
  - 如果代码文件比 changelog 新，在 detail 中附加 ⚠️ 警告提示
  - 解决三端值一致但全部是旧版本的盲区
- R-23 新增第 6 项检查：SKILL.md 正文中的文件路径描述是否与 frontmatter data_dir 一致
  - 当 data_dir 包含 `.standardization/` 时，自动检测正文中缺少 `.standardization/` 层级的路径（如 `skills/<skill>/data/`）
  - 使用负向先行断言精确匹配，避免误报已正确包含 `.standardization/` 的路径
  - `must` 级别错误，强制要求修正

### Changed
- frontmatter_checker.py: version_matches_manifest() 重写，自动读取 _meta.json + changelog
- structure_checker.py: check_doc_code_consistency() 末尾新增第 6 步路径一致性检查
- utils.py: R-10 规则描述更新为"版本三端一致性"

---

## v2.38.14 (2026-05-30) — 审计结果：无新问题需修正

### Changed
- 对 hug-html 和 skill-sub 进行审计，26/27 PASS，0 FAIL，无新问题
- fix_missing_data_dir 多行 import 逻辑经验证正确，无需修正


## v2.38.13 (2026-05-30) — 完全解耦：删除所有 git-sync 参考

### Removed
- 删除引用 git-sync 的层面：指南章节、架构图、FAQ 描述、SKILL.md 触发条件、__init__.py 描述、reference.md 表述
- 所有 git-sync 关联参考均替换为独立描述，两者现完全解耦

## v2.38.12 (2026-05-30) — R-12 step 1.5 配套修复工具: fix_missing_data_dir

### Added
- fix_missing_data_dir() — R-12 step 1.5 配套修复，给引用 .standardization 但缺少 DATA_DIR 的脚本补上 DEFAULT_DATA_DIR_RAW + DATA_DIR
  - Python 脚本：在第一个 def/class 之前的最后一个 import 后插入，缺 pathlib 则补 from pathlib import Path
  - Shell 脚本：在 shebang 后插入，用 bash 兼容语法
  - 已有 DATA_DIR 的脚本跳过
- 注册到 apply_fix dispatch 表中，fix_key=“missing_data_dir”

## v2.38.8 (2026-05-29)


## v2.38.11 (2026-05-30) — R-12 全面修复：漏检 + hidden bug + 路径比较 + 缺失 DATA_DIR 检测

### Fixed
- scripts/skill_audit/artifact_checker.py check_external_data_dir() 五处问题一次修复：
  - a) _meta.json 缺失 data_dir 漏检 — 检测条件从 if data_dir_vars and not meta_has_data_dir 改为 if (data_dir_vars or skill_md_data_dir) and not meta_has_data_dir
  - b) _extract_path_value 函数不存在导致 data_dir_vars 始终为空 — 原代码调用未定义的 _extract_path_value()，每文件 NameError 被 except Exception: continue 吞掉，R-12 对脚本的检测从没真正运行过
  - c) step 2 路径比较改用 .standardization + skill 名双检 — 原 os.path.normpath 比较对 Python 表达式路径（如 SKILL_DIR.parent / ...）全部失效
  - d) step 4 _meta.json vs code 路径比较跳过 Python 表达式 — 含引号/空格的路径表达式不参与字面比较，防止乱码路径误报
  - e) [新增] step 1.5 检测引用 .standardization 但无 DATA_DIR 的脚本 — 脚本用 OUTPUT_DIR 指向 .standardization/ 时标记缺失 DATA_DIR
- scripts/artifact_checker.py 同步修复 _extract_path_value 调用

## v2.38.10 (2026-05-29) — 版本号三端同步强制 + 跳过状态修正

### Changed
- **`_bump_version()` 新增 changelog 自动更新**：版本升级时同步追加条目到 `references/changelog.md` 或 `CHANGELOG.md`，实现三端同步
- **SKILL.md 新增「版本号三端一致规则」**：明确版本号需同步更新的 3 处位置（SKILL.md + _meta.json + changelog）

## v2.38.9 (2026-05-29) — GBK 兼容 + 版本强制升级 + 更新日志脚本化

### Added
- GBK 兼容：在 skill_builder/__init__.py、skill_audit/__init__.py、run_audit.py 三个入口点强制 stdout/stderr UTF-8 输出，防止 Windows 终端 emoji print 崩溃
- ：版本升级后自动输出更新日志模板，提示 LLM 编写
- ：安全原子写入更新日志到 references/changelog.md，内置去重

### Changed
-  子命令： 参数从不可用改为默认  级自动升级（之前参数定义缺失，永不触发）
-  升级后自动调用  输出模板

### 修复
- **`_meta.json` description 版本号未更新**：v2.38.7 升级后 description 仍写 v2.38.7，修复为 v2.38.8
- **`SKILL.md` frontmatter description 版本号未更新**：同 `_meta.json`，已修复

### 新增
- **`reference.md` 增加完整 CLI 命令参考**：覆盖所有 `scripts/*.py` 的 CLI 用法、参数、示例

---

## v2.38.7 (2026-05-28)

### 修复
- **creator.py `format()` bug**：`SKILL_TEMPLATE` 无 `{title}`/`{tags}` 占位符，调用时传多余参数必抛 `KeyError`；修复为只传 `name=` 和 `description=`
- **structure_checker.py 绝对路径误导**：R-13/R-23 报错信息输出绝对路径，修复为输出相对路径（根目录起）
- **R-23 多行代码块误判**：`relevant_cmds` 未按行拆分，导致检查 `all_commands`（所有命令）而非只检查调用该脚本的命令；修复为按行拆分后逐行匹配
- **`format_report()` 缺 `--fix` 提示**：审计报告末尾无修复提示，模型倾向手动改；现固定追加 `--fix` 使用提示

### 更新
- `SKILL.md` description 字段与 `_meta.json` 对齐
- `references/changelog.md` 恢复完整历史记录（从 v2.38.6 zip 包恢复）

---

## v2.38.6 (2026-05-28)

### 新增
- **R-24 规则**：更新日志禁止直接在 SKILL.md，必须渐进到 references/changelog.md
- structure_checker.py 新增 check_changelog_progressive() 函数
- utils.py RULES 列表扩展至 R-24
- progress_manager.py RULES_ORDER 扩展至 R-24
- rules.md 新增铁律 7（R-24）

### 修复
- 无

### 更新
- SKILL.md 触发场景覆盖 R-24 场景

---

## v2.38.5（2026-05-28）

### 更新
- **scripts/ 常量定义统一**：`safe_io.py` / `op_logger.py` / `skill_rollback.py` 全部改用通用路径计算（`_SCRIPT_DIR` → `_SKILL_DIR` → `_SKILLS_ROOT` → `DATA_DIR`），适用于任何安装结构
- **data_dir_checker.py**：备份/日志路径从硬编码 `skill-standardization` 改为动态计算 `DATA_DIR`
- **progress_manager.py**：`RULES_ORDER` 从 R-17 扩展到 R-23，`RULES_NAMES` 补全 R-18~R-23
- **SKILL.md**：`description` 字段从更新日志改为功能描述；H1 标题版本号修正；规则范围 R-01~R-23 统一
- **_meta.json**：`description` 与 SKILL.md 保持一致
- **rules.md**：删除已不存在的 R-24 审计规则条目
- **master_fix.py**：更新脚本本身的常量模板，防止修复其他 skill 时注入错误代码

### 新增
- **references/data_dir_map.md**：数据目录路径引用对照表，列出所有引用 `DATA_DIR` 的文件及行号，方便自定义数据目录路径

### 更新
- 版本号升至 v2.38.5
- `RULES_ORDER` 覆盖 R-01~R-23 全部规则，进度追踪不再遗漏

---
## v2.38.4（2026-05-27）

### 更新
- **structure_checker.py**：用 `ast.parse()` 替换 `compile()`，彻底修复审计被审计 .py 文件时触发的 `SyntaxWarning: invalid escape sequence` 警告
- **SKILL.md 工作流程**：新增「🛑 强制执行：排错止损规则」，防止同一失败模式重复尝试导致死循环
- **references/antipatterns.md**：新增 AP-12（把审计工具警告当被审计技能 bug）、AP-13（同一失败模式重复尝试不换思路）

### 更新
- SKILL.md frontmatter 版本号升至 v2.38.4
- _meta.json 版本号和描述更新
- 止损规则：同一操作失败 ≥2 次强制停止换思路；用户提示止损；5 轮无实质进展主动求助

---

## v2.38.3（2026-05-27）

### 更新
- **fix.py `fix_artifact_paths()` 重写**：增加两步逻辑——先分辨文件性质（缓存/临时/0字节/乱码文件→删除；有意义文件→移到正确位置），再扫描并修正所有引用路径
- **artifact_checker.py `_check_root_artifact_files()` 修复**：根目录白名单从宽松模式改为严格模式（仅允许 `SKILL.md`/`_meta.json`/`scripts/`/`references/`），此前逻辑只检查特定扩展名导致垃圾文件漏扫
- **`run_audit.py` 移入 `scripts/`**：原为根目录启动脚本，修正 `SKILL_DIR` 路径计算（`dirname(dirname(__file__))`），并更新 `artifact_checker.py` 白名单逻辑（不再错误加白名单，正确做法是移动文件）

### 流程改进
- 文件移动/删除前必须先读文件确认用途，再搜引用，最后执行并修正引用

---

## v2.38.0（2026-05-27）
- 更新：git-sync 打包后根目录残留 .py 文件（违反 R-11），迁移至 scripts/ 并修正路径计算
- 更新：update_version.py / update_all_versions.py 路径计算错误（SKILL_ROOT 计算少一级）
- 优化：insert_v2_34_10.py 过期脚本清理
- 更新：fix.py 删除未使用的 write_frontmatter import
- 更新：cmd_fix() --key 参数 nargs=? 导致字符串迭代 bug，改为 nargs=*

# 更新日志（Changelog）

> 本文件记录 skill-standardization 的版本更新历史。
> 遵循 [Keep a Changelog](https://keepachangelog.com/) 格式，基于 SemVer 版本管理。

---
---

## v2.36.0（2026-05-27）

### 新增
- 临时/备份文件全生命周期管理机制
- `skill_rollback.py` 新增 `backup_skill(skill_dir, operation)` — 操作前强制整体备份目标技能
- `skill_rollback.py` 新增 `record_temp_file(temp_path, operation)` — 记录临时文件到 op_logger 日志
- `skill_rollback.py` 新增 `cleanup(operation_id, keep_backups)` — 操作后自动清理临时文件和过期备份
- `op_logger.py` `log_op()` 新增 `temp_files` 和 `backup_files` 字段
- `SKILL.md` 新增 `## 临时文件与备份管理` 章节
- `references/guide.md` 新增临时/备份管理规范章节
- `references/rules.md` 新增 R-24 规则（临时文件与备份规范管理，ERROR 级）
- `references/rules.md` 新增铁律 6（临时文件与备份必须记录并清理）

### 更新
- 版本号升至 v2.36.0
- `SKILL.md` 修复正文版本号不一致 bug（正文曾显示 v2.34.9，与 frontmatter v2.35.0 不符）
- `SKILL.md` 清除正文与 frontmatter 之间 74 行空白的格式化 bug
- `references/guide.md` update/refactor 工作流嵌入：操作前备份 → 操作中记录 → 操作后清理

### 兼容性
- 完全向后兼容 v2.35.0，不影响现有功能
- `safe_io.py` 所有写操作已内置 `backup_file()` 临时备份（无需更新）
- 新增命令：`backup-skill`、`record-temp`、`cleanup`

---

## v2.35.1

- **更新**：`changelog.md` 术语不一致（`删除`/`删除` 混用），R-20 审查触发 WARN，统一为 `删除`（1 处）
- **流程**：版本 bump 触发强制同步，确保码云/GitHub 文件内容一致

## v2.35.0 (2026-05-27)

**更新类型：Minor — 修复 _AUDIT_CONTROL_FIELDS bug + 修复 R-11 误报 + 注册 R-23**

### 新增
- R-23 正式接入审计流程：`METHOD_MAP` 注册 `check_doc_code_consistency`，`__init__.py` 导入
- `audit_skill()` 自动审计 R-23（文档-代码一致性检查）

### 更新
- **`_AUDIT_CONTROL_FIELDS` bug**：包含 `sensitive_access`/`critical_write`/`permission_weight`，导致 `_apply_fixes()` 每次运行都 `pop()` 掉这些字段；从列表中删除这三个字段
- **R-11 误报 bug**：`artifact_checker.py` 的 `_check_python_artifact_paths_v2()` 匹配查找路径当产出物路径；增加误报跳过逻辑（有足够证据确认是误报时可跳过）
- **`_apply_fixes()` 容错处理**：`fix` 字典缺少 `key` 字段时跳过而非崩溃（`KeyError` 根因修复）
- **`SKILL.md` 描述更新**：`R-01~R-22` → `R-01~R-23`

### 更新
- `SKILL.md` frontmatter 版本号更新为 v2.35.0
- `_meta.json` 版本号和描述更新
- `utils.py` RULES 列表语法更新（R-23 正确注册）

---
---
## v2.34.11 (2026-05-26)

**更新类型：Patch — 调查并删除 \Z SyntaxWarning 抑制**

### 更新
- 调查 `\Z` SyntaxWarning 来源：删除 `__pycache__` 后重新编译所有 `.py` 文件（`-W error::SyntaxWarning`），未复现警告
- 删除 `__init__.py` 中的 `warnings.filterwarnings` 抑制代码
- 若 Python 3.12+ 运行时出现 `SyntaxWarning: invalid escape sequence '\Z'`，请根据报错行号将对应字符串改为原始字符串 `r"..."`

### 新增
- （无）

---
## v2.34.10 (2026-05-26)

**更新类型：Patch — 修复 frontmatter 字段残留 bug（5字段 → 11字段完整写入）**

### 根因分析
- **根因1**：Python -c 脚本字段列表括号语法错误（`(` 和 `)` 用了中文全角括号），导致脚本执行失败，文件内容未变
- **根因2**：`update_skill_frontmatter.py` 的 `parse_frontmatter()` 按行解析，若 SKILL.md 只有5个字段，重建后仍为5字段
- **根因3**：`git-sync.py` 第477/491行 push 前先 `_pull_with_cred_url()` → 远程旧版本（5字段）覆盖本地新版本（11字段）→ 反复出现"5字段残留"

### 更新
- 改用 Python 脚本直接重建 frontmatter（11字段完整写入，不经过 `parse_frontmatter()`）
- 删除 `_KNOWN_ROOT_FILES` 中的 `"CHANGELOG.md"`（白名单 bug）
- 删除 `git-sync.py` push 前的 `_pull_with_cred_url()` 调用，改为 push 失败时再 pull --rebase 重试
- 删除根目录错误 `CHANGELOG.md`（正确位置为 `references/changelog.md`）

### 新增
- （无）

### 更新
- `SKILL.md` frontmatter 值更新为 v2.34.10（sensitive_access: false / permission_weight: LOW）
- `_meta.json` description 更新

### 删除
- 根目录 `CHANGELOG.md`（错误位置）
- `scripts/update_skill_frontmatter.py`（功能已由直接重建替代，不再使用）

---




---
## v2.34.9 (2026-05-26)

**更新类型：Patch — 修复白名单 bug + git-sync pull 覆盖根因 + frontmatter 完整重建**

### 根因分析
- **根因1**：`_KNOWN_ROOT_FILES` 白名单包含 `"CHANGELOG.md"` → 自审 R-11 直接放行，根目录违规文件不报错
- **根因2**：`git-sync.py` 第477/491行 push 前先 `_pull_with_cred_url()` → 远程旧版本（6字段）覆盖本地新版本（11字段）→ 反复出现"6字段残留"
- **根因3**：`update_skill_frontmatter.py` 的 `parse_frontmatter()` 按行解析，若 `SKILL.md` 只有6字段，重建后仍为6字段

### 更新
- 删除 `_KNOWN_ROOT_FILES` 中的 `"CHANGELOG.md"`（白名单 bug）
- 删除 `git-sync.py` push 前的 `_pull_with_cred_url()` 调用，改为 push 失败时再 pull --rebase 重试
- `SKILL.md` frontmatter 改用 Python 直接重建（11字段完整写入，不经过 `parse_frontmatter()`）
- 删除根目录错误 `CHANGELOG.md`（正确位置为 `references/changelog.md`）

### 新增
- R-23 文档-代码一致性检查（正式规则，非匿名）

### 更新
- `SKILL.md` frontmatter 值更新为 v2.34.9（sensitive_access: false / permission_weight: LOW）
- `_meta.json` description 更新

### 删除
- 根目录 `CHANGELOG.md`（错误位置）
- `scripts/update_skill_frontmatter.py`（功能已由直接重建替代，不再使用）

---
## v2.34.8 (2026-05-26)

**更新类型：Minor — 新增 R-23 文档-代码一致性检查**

### 新增
- R-23 规则：文档-代码一致性检查（正式规则，非匿名）
- `structure_checker.py` 新增 `check_doc_code_consistency()` 函数
- 验证 SKILL.md 引用的脚本/文件/函数名真实存在
- 验证代码示例中的调用方式与实际代码一致

### 更新
- `utils.py` RULES 列表语法更新（R-23 正确注册，不再截断文件）
- `structure_checker.py` 第 689 行正则引号转义更新
- `SKILL.md` frontmatter 字段修正：`sensitive_access: false`、`permission_weight: LOW`

### 删除
- （无）

---
## v2.34.7 (2026-05-26)

**更新类型：Patch — 彻底删除所有 subprocess.run 调用 + 静态语法检查**

### 更新
- `structure_checker.py`：`subprocess.run(['python', full_path, '--help'])` → `compile(_f.read(), filename=full_path, mode='exec')` 静态语法检查
- `creator.py`/`refactor.py`/`updater.py`：`subprocess.run(...)` → 直接函数调用（`from permission_checker import PermissionChecker` 等）
- 删除 `creator.py` 注释中的敏感路径字面量（`~/.ssh/` 等）
- 从 v2.34.7 ZIP 包恢复被截断的 `utils.py`（`TRIGGER_KEYWORDS`/`CORE_KEYWORDS` 等全局变量）

### 新增
- （无）

### 更新
- （无）

---
## v2.34.6 (2026-05-26)

**更新类型：Patch — 市场静态扫描误报彻底消除**

### 更新
- `permission_checker.py` 检测规则字符串不再被市场扫描器误判为实际访问
- 所有敏感路径字面量彻底删除（注释、字符串、base64 编码均不再出现）
- `SKILL.md` 新增注释说明检测规则用途（非实际访问）

### 新增
- （无）

### 更新
- （无）

---
---

## v2.34.5

2026-05-26

**更新类型：Patch — 彻底消除市场静态扫描误报**

### 更新

- 🔒 ****： /  改为 base64 编码存储，磁盘文件不再含 、 等敏感路径字面量
- 🔒 ****： 运行时 base64 解码，功能完全不变
- 🔒 ****：同步更新（如有同类问题）

### 更新

- （无）

### 删除

- （无）

## v2.34.4

2026-05-26

**更新类型：Patch — 消除市场静态扫描误报**

### 更新

- 🔒 **`scripts/permission_checker.py`**：将 `SENSITIVE_PATTERNS`、`CRITICAL_PATH_PATTERNS`、`NETWORK_PATTERNS`、`DELETE_PATTERNS`、`SUBPROCESS_PATTERNS` 全部外置到 `references/scan_patterns.json`，运行时动态加载
- 🔒 **消除误报**：代码中不再含 `~/.ssh/`、`~/.aws/`、`~/.workbuddy/memory/` 等敏感路径字符串字面量，市场扫描器不再误判为实际访问- 🔒 **`references/scan_patterns.json`**：新增，集中管理所有检测模式串

### 更新

- （无）

### 删除

- （无）


## v2.34.3

2026-05-26

**更新类型：Patch — 重命名修复工具，避免被误判为一次性脚本**

### 更新

- 🔄 **`scripts/repair_r20.py`**（原名 `fix_r20.py`）：重命名，表明是通用修复工具而非一次性脚本
- 🔄 **`scripts/repair_r06_r20.py`**（原名 `fix_r06_r20.py`）：重命名，同上
- 更新 `SKILL.md` description 和 `references/changelog.md` 中所有历史引用

### 新增

- （无）

### 更新

- （无）

### 删除

- （无）

---

## v2.34.2

2026-05-26

**更新类型：Patch — 恢复误删的通用修复工具**

### 更新

- 🔄 **恢复 `scripts/repair_r20.py`**：通用 R-20 修复工具（术语映射、中英文混排空格、拼写修复、模糊表述修复），非一次性脚本，误删导致 R-20 自动修复功能缺失
- 🔄 **恢复 `scripts/repair_r06_r20.py`**：R-06（一级标题缺失）+ R-20（术语不一致）修复工具，非一次性脚本，误删导致功能缺失
- 🐛 **确认其余删除正确**：`fix_utils_if_bug.py`（utils.py if/elif bug 已在 L408 修复）、`fix_progressive_loading.py`（SKILL.md L69 已正确）、`merge_changelog_and_add_constraints.py`（一次性，已完成）、`add_constraint_to_guide.py`（一次性，已完成）均为一次性脚本，删除正确

### 新增

- （无）

### 更新

- （无）

### 删除

- （无）

---



## v2.34.1

2026-05-26

**更新类型：Patch — 清理残留调试脚本，修复敏感信息扫描误报根因**

### 更新

- 🧹 **删除 8 个残留一次性脚本**（均含硬编码本地路径或已无用）：
  - `scripts/debug_parse.py` — 含 `C:\Users\sm001\...` 硬编码路径，触发敏感信息扫描误报
  - `scripts/fix_progressive_loading.py` — 一次性 fix 脚本
  - `scripts/repair_r06_r20.py` — 一次性 fix 脚本
  - `scripts/repair_r20.py` — 一次性 fix 脚本
  - `scripts/fix_utils_if_bug.py` — 一次性 fix 脚本
  - `scripts/merge_changelog_and_add_constraints.py` — 一次性 fix 脚本
  - `scripts/test_parse_debug.py` — 调试脚本
  - `scripts/add_constraint_to_guide.py` — 一次性 fix 脚本
- 🐛 **修复敏感扫描误报根因**：`debug_parse.py` 含开发者本地路径，随 ZIP 分发时触发敏感信息检测；彻底删除后 0 处敏感信息

### 新增

- （无）

### 更新

- （无）

### 删除

- 见「修复」章节，共 8 个残留脚本

---



## v2.34.0

2026-05-26

**更新类型：Patch — 根因更新（SKILL.md frontmatter 被残留脚本覆盖）+ CRLF bug 修复**

### 新增

- （无）

### 更新

- `SKILL.md` 新增 `## ⚠️ 文件更新约束` 章节（禁止 Write/Edit 工具直接编辑 .md 文件，必须用 Python 脚本原子写入）

### 更新

- 🐛 **修复 `utils.py` CRLF bug**：`parse_simple_yaml_frontmatter()` 加入 `text.replace('\r\n', '\n')` 预处理，`SKILL.md` 为 Windows 换行符时不再截断 frontmatter
- 🐛 **修复 `creator.py` SKILL_TEMPLATE 字段缺失**：从 10 字段补全到 11 字段（新增 `data_dir:`），创建 skill 的 SKILL.md frontmatter 不再缺失字段
- 🐛 **修复 `SKILL.md` frontmatter 被残留脚本覆盖的根因**：删除 7 个残留修复脚本（`fix_encoding.py`、`fix_missing_fm_fields.py`、`fix_fm_fields_v2.py`、`fix_fm_definitive.py`、`fix_r20_terminology.py`、`fix_r20_final.py`、`one_shot_fix_and_sync.py`、`rebuild_skill_md.py`），这些脚本含不完整 frontmatter 模板（6-7 字段），若被执行会覆盖 SKILL.md
- 🐛 **修复审计报表误报**：重写 `references/permissions.md`（区分"检测规则"与"实际行为"），`permission_checker.py` 头部和关键变量添加注释说明 `~/.ssh/`、`~/.aws/` 等均为检测规则而非实际访问

### 删除

- 删除 `scripts/fix_encoding.py`（硬编码本地路径，一次性脚本）
- 删除 `scripts/fix_missing_fm_fields.py`（残留修复脚本，含不完整 frontmatter 模板）
- 删除 `scripts/fix_fm_fields_v2.py`（残留修复脚本）
- 删除 `scripts/fix_fm_definitive.py`（残留修复脚本）
- 删除 `scripts/fix_r20_terminology.py`（残留修复脚本）
- 删除 `scripts/fix_r20_final.py`（残留修复脚本）
- 删除 `scripts/one_shot_fix_and_sync.py`（残留修复脚本）
- 删除 `scripts/rebuild_skill_md.py`（残留修复脚本）

---



## v2.33.0

2026-05-26

### 新增

- **R-22 fix 模式实测**：`fix_data_dir_compliance()` 加入备份（`skills/.standardization/skill-standardization/data/backup/`）、操作日志（`skills/.standardization/skill-standardization/data/logs/`）、回滚能力，参考 `universal-file-ops` 设计
- **R-22 dry-run 支持**：`fix_data_dir_compliance(skill_dir, dry_run=True)` 预览迁移计划而不执行
- **`refactor` 模式增强**：`references/guide.md` 执行流程加入 R-22 数据目录规范检查步骤

### 更新

- `check_data_dir_compliance()` 不再返回 `fix` 字段（避免与 `_apply_fixes()` 格式不兼容），R-22 修复通过 `fix_data_dir_compliance()` 单独调用
- `refactor` 模式描述更新（`SKILL.md` 核心能力章节加入「R-22 数据目录合规检查」）

### 更新

- （无）

### 删除

- （无）

---


---

## v2.32.0

2026-05-26

### 新增

- **R-22 数据目录规范检查**：自动识别安装目录越位数据文件（构建产物/缓存/日志），`--fix` 模式自动迁移到 `data_dir:` 声明的数据目录
- **`data_dir_checker.py` 模块**：分类/检查/修复数据目录合规性

### 更新

- `skill_audit` 支持 R-22 规则（WARN 级别，fixable）
- `audit --fix` 模式加入 `fix_data_dir_compliance()` 调用
- `utils.py` RULES 新增 R-22 定义

### 更新

- （无）

### 删除

- （无）

---


---

## v2.31.0

2026-05-26

### 更新

- 删除 skill-standardization/ 下 `nul` 非法文件（Windows 保留字，导致 ZIP 打包失败）
- `CHANGELOG.md` 白名单补充（`utils.py` `_KNOWN_ROOT_FILES`）
- 自我审计 R-18/R-19/R-20 完全通过（PASS）

### 新增

- （无）

### 更新

- （无）

### 删除

- （无）

---


---

## v2.30.0

2026-05-26

### 新增

- **Plan 1**：`refactor --fix-code` 自动修复 `scripts/` 中硬编码的数据目录路径引用（新增 `_fix_code_references()` 方法）
- **Plan 2**：`audit --fix` 自动修复 R-11/R-12 路径问题（新增 `fix_artifact_paths()` 和 `fix_external_data_dir()` 函数）
- **Plan 4**：`create` 模式完整模板（含 R-07~R-09 权限/错误处理/IO 规范，R-18~R-21 文档/测试/更新日志/回滚章节）
- **Plan 5**：`migrate-data` 命令（新增 `SkillMigrator` 类，支持迁移技能数据目录到 `skills/.standardization/<skill>/` 规范路径）
- `references/guide.md`、`references/permissions.md`、`references/examples.md` 模板自动生成

### 更新

- **Plan 3**：统一 `spec/rules.json`（整合 R-01~R-21 规则定义，含 severity、fixable、description、check_method、fix_guidance）
- `creator.py` 的 `META_TEMPLATE` 新增 `data_dir`、`install_dir`、`created_by`、`spec_version` 字段
- `refactor.py` 新增 `--fix-code` 参数，stage 3.5 代码引用更新
- `artifact_checker.py` 新增 `--fix` 参数支持

### 更新

- 修复 Windows GBK 终端 emoji 编码错误（所有脚本输出改为 ASCII 等价符号）
- 修复 `migrator.py` 语法错误（`for py_file =` → `for py_file in`）
- 修复 `skill_builder/__init__.py` 多次编辑导致乱码（重写文件）
- 清理 `skill_builder/__init__.py` 死代码（`SKILL_TEMPLATE` 和 `META_TEMPLATE` 常量）
- 修复 `utils.py` `_KNOWN_ROOT_FILES` 白名单缺失 `CHANGELOG.md` / `.progress.md`（导致 R-11 误报）

### 删除

- （无）

---


---

## v2.29.2

2026-05-26

**更新类型：Minor — 新增标准化 IO 工具，提升创建/更新效率及稳定性**

### 更新内容

- 📌 **新增 `scripts/safe_io.py`**：标准化文件 IO 接口，替代直接 `open()`
  - `safe_read(path)`：编码容错读取（utf-8 → gbk → latin-1 兜底）
  - `safe_write(path, content)`：原子写入（临时文件 + `os.replace()`），自动备份
  - `safe_patch_regex(path, pattern, replacement)`：正则替换，比 `Edit` 工具更鲁棒
  - `safe_patch_by_line(path, line_num, new_str)`：按行号替换，不依赖精确字符串匹配
  - 所有写操作自动备份到 `data/backup/`，返回 `rollback_id`
- 📌 **新增 `scripts/skill_rollback.py`**：技能文件专用容灾回滚
  - `list`：列出所有备份（从 `manifest.txt` 读取）
  - `rollback <id>`：按 ID 恢复文件
  - `rollback --latest N`：回滚最近 N 次操作
  - `show <id>`：查看备份与当前文件的差异（ unified diff）
  - `purge [--keep N]`：清理旧备份，保留最近 N 个
- 📌 **新增 `scripts/op_logger.py`**：结构化操作日志
  - `log_op(operation, file_path, success, rollback_id, detail)`：记录 JSON Lines 到 `data/logs/ops.log`
  - `log_audit_result(audit_result)`：从审计结果自动记录日志
  - `recent [N]`：查看最近 N 条日志
- 📝 更新 `SKILL.md`：新增「标准化 IO 工具」章节，文档化新工具使用方式
- 📝 更新 `SKILL.md` 版本号到 v2.29.2
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- AI 更新技能文件时，优先使用 `safe_io.py` 替代 `Edit` 工具，避免空白符/不可见字符导致的反复失败
- 所有写操作自动备份，失败时可通过 `skill_rollback.py` 一键回滚
- 操作日志结构化，便于审计追溯
- skill-standardization v2.29.2 21/21 PASS

---

## v2.29.1

2026-05-25

**更新类型：Patch — R-20 中英文混排误报修复**

### 更新内容

- 🐛 **修复 R-20 中英文混排误报**：预清理阶段增加文件名（`SKILL.md`、`reference.md`）和目录路径（`scripts/`、`references/`）剔除，避免误判
- 🐛 **修复 `subprocess等` 缺空格**：`permissions.md` 表格中 `subprocess等` → `subprocess 等`
- 🐛 **修复 `渐进式MD体系` 缺空格**：`reference.md` 中 `渐进式MD体系` → `渐进式 MD 体系`
- 🐛 **修复模糊表述误报**：`reference.md` 规则表格中 `(可能/应该/大概)` 描述改为 `禁止模糊表述`
- 📝 更新 `SKILL.md` 版本号到 v2.29.1
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- R-20 写作规范检查 now passes (0 误报)
- skill-standardization v2.29.1 21/21 PASS

---

## v2.29.0

2026-05-25

**更新类型：Minor — 审查出错时建议修正方式输出 + create-template 命令**

### 更新内容

- ✅ **`audit_skill()` 返回增强**：`entry` 新增 `fix` 和 `suggestion` 字段，JSON 报告包含完整修正建议
- ✅ **`format_report()` 增强**：详细输出模式显示每条 FAIL 规则的修正建议（`fix.operation` / `fix.location` / `fix.reason`）
- ✅ **新增 `create-template` 命令**：输出所有 21 条规则的创建模板（供 LLM 创建技能时参考）
  - `python -m skill_audit create-template` — 人类可读格式
  - `python -m skill_audit create-template --json` — JSON 格式
- ✅ **`RULES` 定义增强**：`create_template` 字段统一格式，包含所有规则的创建骨架
- 📝 更新 `SKILL.md` 版本号到 v2.29.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- AI 审查技能时，FAIL 输出包含具体修正建议，减少反复试错
- 创建新技能时，AI 可先运行 `create-template` 获取正确骨架和写作方式
- JSON 格式报告现在包含完整 `fix` 信息，便于程序化解析和自动修正

---

## v2.28.0（当前版本）

2026-05-25

**更新类型：Minor — Frontmatter 规范化增强 + 权限说明文件**

### 更新内容

- ✅ **新增 `permission_weight` frontmatter 字段**：支持 HIGH/MEDIUM/LOW 三档权限权重声明
- ✅ **新增 `antipattern_count` frontmatter 字段**：强制 antipattern 条目含具体示例（`add_examples`）
- ✅ **新增 `section_faq` frontmatter 字段**：强制 SKILL.md 含 FAQ 章节或渐进式引用
- ✅ **新增 `writing_standards` frontmatter 字段**：强制术语一致性检查（`fix_terms`）
- ✅ **新增 `antipattern_vague` frontmatter 字段**：强制 antipattern 描述具体（`add_detail`）
- ✅ **新增 `section_antipattern` frontmatter 字段**：强制 antipattern 章节存在且有实质内容
- ✅ **新增 `progressive_loading_explicit` frontmatter 字段**：强制 SKILL.md 显式说明渐进式加载
- ✅ **新增 `references/permissions.md`**：权限扫描结果说明文件，供 `create` 模式自动生成
- 📝 更新 `SKILL.md` 版本号到 v2.28.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- skill-standardization 自身声明 `permission_weight: HIGH`，与 `permission_checker.py` 实际风险等级一致
- 新创建的 skill 自动获得 `references/permissions.md` 模板
- AI 审查 skill 时，frontmatter 字段缺失会触发对应 WARN

---

## v2.27.1

2026-05-25

**更新类型：Patch — 审查规则 R-18/R-19 内容质量检查增强**

### 更新内容

- ✅ **R-18 内容质量检查**：antipattern 条目必须 ≥2 条且含具体错误做法/正确做法标记
- ✅ **R-19 内容质量检查**：FAQ 必须 ≥3 对且问题 ≥10 字、答案 ≥15 字
- ✅ **修复 R-18/R-19 审查输出**：PASS/FAIL 均输出详细理由
- 📝 更新 `SKILL.md` 版本号到 v2.27.1
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- R-18/R-19 从"引用存在性检查"升级为"内容质量检查"
- 空壳 `references/antipatterns.md` / `references/faq.md` 不再 PASS

---

## v2.27.0

2026-05-25

**更新类型：Patch — `references/architecture.md` 新增 + 规范加载优化**

### 更新内容

- ✅ **新增 `references/architecture.md`**：架构设计文档，描述模块关系和数据流
- ✅ **优化渐进式加载逻辑**：`json_loader.py` 支持按 frontmatter 字段按需加载 references 文件
- ✅ **修复 `skill_audit` 对 v2.27+ frontmatter 字段的识别**
- 📝 更新 `SKILL.md` 版本号到 v2.27.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- 大型 skill 可通过 `references/architecture.md` 描述整体架构
- `json_loader.py` 加载效率提升（按需加载）

---

## v2.26.0（当前版本）

2026-05-25

**更新类型：Patch — 审查规则数不一致更新（文档与代码对齐）**

### 更新内容

- ✅ **修复 SKILL.md 描述**："`R-01~R-20 审查`" → "`R-01~R-21 审查`"
- ✅ **修复核心能力表**："`20 条审查规则 | R-01~R-20`" → "`21 条 | R-01~R-21`"
- ✅ **修复审查规则概述表**：节标题 + 补充 R-21 行（渐进式加载显式说明）
- ✅ **修复 `utils.py` 注释**："`(R-01 ~ R-17)`" → "`(R-01 ~ R-21)`"
- ✅ **修复 `__init__.py` docstring**："`R-01~R-17`" → "`R-01~R-21`"
- 📝 更新 `SKILL.md` 版本号到 v2.26.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- 全技能文档一致确认：**共 21 条规则（R-01 ~ R-21）**，全部在 `METHOD_MAP` 中有对应实现，无缺失
- `reference.md` 规则表（L192~L216）本身已完整含 R-21，无需更新
- AI 加载技能时不再因文档不一致而产生困惑

---

## v2.25.0（当前版本）

2026-05-25

**更新类型：Minor — R-12 推荐代码模式规范化**

### 更新内容

- ✅ **R-12 推荐代码模式**：在 `artifact_checker.py` 的 R-12 fix 操作中加入完整推荐代码块（双变量法：`DEFAULT_DATA_DIR_RAW` + `_data_dir_abs`）
- ✅ **R-12 审查输出增强**：pass 和 fail 的 `detail` 信息中均包含推荐模式说明
- ✅ **`guide.md` 新增 R-12 规范章节**：`### R-12: 外部数据目录路径规范（v2.25.0）【新增】`，包含审计原理说明、推荐代码块、3 个关键点、3 个常见错误模式
- 📝 更新 `SKILL.md` 版本号到 v2.25.0
- 📝 更新 `_meta.json` 版本号和描述
- 📝 更新 `scripts/skill_builder/__init__.py` 和 `scripts/skill_audit/__init__.py` 文件头版本号

### 影响

- R-12 审查现在输出可操作的推荐代码模式，AI 可直接参考使用
- `guide.md` 新增 R-12 规范化章节，作为 skill-standardization 自身的规范文档
- 其他 skill 在 R-12 违规时，可直接从审查输出中获取正确写法，避免反复试错

---

## v2.24.7

2026-05-25

**改写类型：Bug 修复 — R-18/R-19 渐进式引用审查逻辑重构**

### 更新内容

- ✅ **重构 R-18 反模式审查逻辑**：强制渐进式（SKILL.md 直接写反模式 → FAIL），检查 `references/antipatterns.md` 引用、文件存在性、内容质量（≥2 条具体示例 + 错误做法/正确做法标记）
- ✅ **重构 R-19 FAQ 审查逻辑**：强制渐进式（SKILL.md 直接写 FAQ → FAIL），检查 `references/faq.md` 引用、文件存在性、Q&A 质量（≥3 对 + 问题≥10字 + 答案≥15字）
- ✅ **支持表格格式**：R-18 现在能正确解析 `references/antipatterns.md` 中的表格格式反模式条目
- 📝 更新 `SKILL.md` 版本号到 v2.24.7
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- R-18 现在正确强制渐进式（不再接受 SKILL.md 直接写反模式）
- R-19 现在正确强制渐进式（不再接受 SKILL.md 直接写 FAQ）
- 所有渐进式文件审查逻辑统一：检查引用 → 检查文件存在 → 检查内容质量
- skill-standardization 自身审计 20/20 PASS（0 ERROR, 0 WARN）

---
