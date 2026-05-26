# skill-standardization — 变更日志

本文档记录 `skill-standardization` 的版本变更，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

## [未发布]

（本版本号对应下次发布内容## [2.31.0] - 2026-05-26

### 修复
- 删除 skill-standardization/ 下 nul 非法文件（Windows 保留字，导致 ZIP 打包失败）
- CHANGELOG.md 白名单补充（`utils.py` _KNOWN_ROOT_FILES）
- 自我审计 R-18/R-19/R-20 完全通过（PASS）

### 新增
- （无）

### 修改
- （无）

### 移除
- （无）

---

，发布时替换为具体版本号和日期）

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
