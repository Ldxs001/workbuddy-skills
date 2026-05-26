# skill-standardization — 变更日志

本文档记录 `skill-standardization` 的版本变更，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

## [2.33.0] - 2026-05-26

### 新增
- **R-22 fix 模式实测**：`fix_data_dir_compliance()` 加入备份（`skills/.standardization/skill-standardization/data/backup/`）、操作日志（`skills/.standardization/skill-standardization/data/logs/`）、回滚能力，参考 `universal-file-ops` 设计
- **R-22 dry-run 支持**：`fix_data_dir_compliance(skill_dir, dry_run=True)` 预览迁移计划而不执行
- **`refactor` 模式增强**：`references/guide.md` 执行流程加入 R-22 数据目录规范检查步骤

### 修改
- `check_data_dir_compliance()` 不再返回 `fix` 字段（避免与 `_apply_fixes()` 格式不兼容），R-22 修复通过 `fix_data_dir_compliance()` 单独调用
- `refactor` 模式描述更新（`SKILL.md` 核心能力章节加入「R-22 数据目录合规检查」）

### 修复
- （无）

### 移除
- （无）

---

## [2.32.0] - 2026-05-26

### 新增
- **R-22 数据目录规范检查**：自动识别安装目录越位数据文件（构建产物/缓存/日志），`--fix` 模式自动迁移到 `data_dir:` 声明的数据目录
- **`data_dir_checker.py` 模块**：分类/检查/修复数据目录合规性

### 修改
- `skill_audit` 支持 R-22 规则（WARN 级别，fixable）
- `audit --fix` 模式加入 `fix_data_dir_compliance()` 调用
- `utils.py` RULES 新增 R-22 定义

### 修复
- （无）

### 移除
- （无）

---

## [2.31.0] - 2026-05-26

### 修复
- 删除 skill-standardization/ 下 `nul` 非法文件（Windows 保留字，导致 ZIP 打包失败）
- `CHANGELOG.md` 白名单补充（`utils.py` `_KNOWN_ROOT_FILES`）
- 自我审计 R-18/R-19/R-20 完全通过（PASS）

### 新增
- （无）

### 修改
- （无）

### 移除
- （无）

---

## [2.30.0] - 2026-05-26

### 新增
- **Plan 1**：`refactor --fix-code` 自动修复 `scripts/` 中硬编码的数据目录路径引用（新增 `_fix_code_references()` 方法）
- **Plan 2**：`audit --fix` 自动修复 R-11/R-12 路径问题（新增 `fix_artifact_paths()` 和 `fix_external_data_dir()` 函数）
- **Plan 4**：`create` 模式完整模板（含 R-07~R-09 权限/错误处理/IO 规范，R-18~R-21 文档/测试/变更日志/回滚章节）
- **Plan 5**：`migrate-data` 命令（新增 `SkillMigrator` 类，支持迁移技能数据目录到 `skills/.standardization/<skill>/` 规范路径）
- `references/guide.md`、`references/permissions.md`、`references/examples.md` 模板自动生成

### 修改
- **Plan 3**：统一 `spec/rules.json`（整合 R-01~R-21 规则定义，含 severity、fixable、description、check_method、fix_guidance）
- `creator.py` 的 `META_TEMPLATE` 新增 `data_dir`、`install_dir`、`created_by`、`spec_version` 字段
- `refactor.py` 新增 `--fix-code` 参数，stage 3.5 代码引用修复
- `artifact_checker.py` 新增 `--fix` 参数支持

### 修复
- 修复 Windows GBK 终端 emoji 编码错误（所有脚本输出改为 ASCII 等价符号）
- 修复 `migrator.py` 语法错误（`for py_file =` → `for py_file in`）
- 修复 `skill_builder/__init__.py` 多次编辑导致乱码（重写文件）
- 清理 `skill_builder/__init__.py` 死代码（`SKILL_TEMPLATE` 和 `META_TEMPLATE` 常量）
- 修复 `utils.py` `_KNOWN_ROOT_FILES` 白名单缺失 `CHANGELOG.md` / `.progress.md`（导致 R-11 误报）

### 移除
- （无）

---

## [2.29.2] - 2026-05-24

### 新增
- 标准化 IO 工具（`safe_io.py`、`skill_rollback.py`、`op_logger.py`）
- `safe_io.py`：编码容错读取、原子写入、正则替换（替代 `Edit` 工具）
- `skill_rollback.py`：备份清单管理、按 ID 回滚、差异对比
- `op_logger.py`：结构化 JSON Lines 日志，审计追溯
- 审查出错时建议修正方式输出
- `create` 模式输出创建模板

### 修复
- 修复 R-20 中英文混排误报

---

## [2.14.0] - 2026-05-20

### 新增
- 支持 R-01~R-17 审查（含权限分级、敏感信息检测、授权检查、触发条件合规性）
- create/update/refactor 三模式
- 授权方式智能判断（根据技能工作性质决定 unified/immediate/silent）

---

## 版本号说明

本技能遵循 **语义化版本 2.0.0**（Semantic Versioning）：

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

---

> 变更日志由 `skill-standardization` 自身维护。
