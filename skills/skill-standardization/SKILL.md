---
name: skill-standardization
version: 2.29.2
author: wUwproject
license: MIT
description: Skill 标准化规范引擎 v2.30.0。新增 refactor --fix-code 自动修复代码引用、审计 --fix 自动修复 R-11/R-12 路径问题、统一 spec/rules.json（R-01~R-21）、create 模式完整模板（含 R-07~R-09/R-18~R-21 章节）、migrate-data 命令迁移数据目录。
tags: ['standardization', 'skill-builder', 'skill-audit', 'json-loader', 'refactor', 'progressive-loading', 'security', 'permission-check']
antipattern_progressive: true
faq_progressive: true
writing_standards: fix_terms
sensitive_access: true
critical_write: false
permission_weight: HIGH
artifact_paths: true
---


# skill-standardization v2.30.0

> Skill 标准化规范引擎 v2.30.0，支持 R-01~R-21 审查（含权限分级、敏感信息检测、授权检查、渐进式文件质量检查）、create/update/refactor 三模式、渐进式 MD 体系、**refactor --fix-code 自动修复代码引用**、**审计 --fix 自动修复 R-11/R-12 路径问题**、**统一 spec/rules.json（R-01~R-21）**、**create 模式含完整模板（R-07~R-09/R-18~R-21）**、**migrate-data 命令迁移数据目录**。

## 触发场景

当用户提到以下意图时触发本技能：
- 创建新技能 → 触发 `create` 模式
- 更新已有技能 → 触发 `update` 模式
- 改造（refactor）已有技能 → 触发 `refactor` 模式
- 审计技能合规性 → 触发 `audit` / `audit-all` 子命令
- 迁移技能数据目录 → 触发 `migrate-data` 子命令

**不触发**：
- 用户只是普通聊天，没有技能开发/管理意图
- 用户明确说"不要用 skill-standardization"

## 核心能力

| # | 功能 | 说明 |
|---|---|---|
| 1 | **三种执行模式** | create / update / refactor（refactor 支持 --fix-code 自动修复代码引用） |
| 2 | **21 条审查规则（R-01~R-21）** | 含 --fix 自动修复 R-11/R-12、`spec/rules.json` 统一规则定义 |
| 3 | **渐进式 MD 体系** | `SKILL.md` ≤230 行，详情拆分到 `references/*.md` 按需加载 |
| 4 | **权限分级 & 五级风险** | silent / silent-risky / unified / immediate / forbidden |
| 5 | **审计 & 修复** | `audit`（R-01~R-21）、`audit-all`（全量）、`--fix` 自动修复 |
| 6 | **refactor 改造** | 三阶段（分析→审查→重写），支持 `--fix-code` 自动修复代码引用 |
| 7 | **create 完整模板** | 模板含 R-07~R-09/R-18~R-21 章节，生成的 SKILL.md 直接通过审计 |
| 8 | **migrate-data 命令** | 迁移技能数据目录到 `skills/.standardization/<skill>/` 规范路径 |
| 9 | **标准化 IO 工具** | `safe_io`（编码容错读写）、`skill_rollback`（备份回滚）、`op_logger`（操作日志） |
| 10 | **JSON 加载器** | `json_loader.py` 统一加载 `spec/*.json`，含缓存和版本检查 |
| 11 | **操作日志工具** | `op_logger.py` 结构化 JSON Lines 日志，审计追溯 |
| 12 | **create 完整模板** | 模板含 R-07~R-09/R-18~R-21 章节，生成的 SKILL.md 直接通过审计 |
| 13 | **migrate-data 命令** | 迁移技能数据目录到 `skills/.standardization/<skill>/` 规范路径 |

## 快速开始

```bash
# 创建新技能（完整模板）
python -m skill_builder create --name my-skill --desc "我的技能" --tags tag1,tag2

# 审计单个技能
python -m skill_audit audit <skill-dir> [--json] [--fix]

# 审计所有技能
python -m skill_audit audit-all [--fix]

# refactor 改造（自动修复代码引用）
python -m skill_builder refactor <skill-dir> [--fix-code]

# 迁移数据目录
python -m skill_builder migrate-data <skill-dir> [--dry-run] [--force]
```

## 工作流程

1. **create 模式**：读取 `creator.py` 的 `SKILL_TEMPLATE` → 生成 `SKILL.md` + `references/*.md` + `_meta.json` + `CHANGELOG.md`
2. **update 模式**：读取现有 `SKILL.md` → 更新 frontmatter 版本号 → 审查 R-01~R-21 → 输出修正建议
3. **refactor 模式**：stage 1（分析 SKILL.md）→ stage 2（执行 R-01~R-21 审查）→ stage 3（渐进式加载改造）→ stage 3.5（`--fix-code` 自动修复代码引用）

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

## 权限声明（R-07）

| 权限项 | 值 | 说明 |
|---|---|---|
| `sensitive_access` | `true` | 读取技能目录结构、SKILL.md 内容 |
| `critical_write` | `false` | 写入前需用户确认（create/update/refactor/migrate-data） |
| `create_permissions_md` | `true` | create 模式自动生成 `references/permissions.md` |

## 错误处理（R-08）

- 技能目录不存在 → 报错并中止
- SKILL.md 格式错误 → 报错并提示正确格式
- 审计发现 ERROR 级违规 → 报告中建议修正方式，不自动更新（除非 `--fix` 显式指定）
- `spec/rules.json` 缺失/格式错误 → 使用内置默认规则，记录 WARN

## IO 规范（R-09）

- 所有文件操作通过 `safe_io.py` 执行（编码容错、原子写入）
- 所有写操作前通过 `skill_rollback.py` 创建备份（备份清单 `rollback.json`）
- 所有操作通过 `op_logger.py` 记录日志（`logs/operation.log.jsonl`）
- 路径分隔符统一使用 `/`（跨平台兼容）

> 常见错误做法详见 `references/antipatterns.md`

> 常见问题详见 `references/faq.md`

## 主要流程

### create 模式
1. 解析命令行参数（name/desc/tags/dir）
2. 渲染 `SKILL_TEMPLATE` 生成 `SKILL.md`（含 frontmatter + 所有必需章节）
3. 生成 `_meta.json`（含 `data_dir` / `install_dir` / `created_by` / `spec_version`）
4. 生成 `references/guide.md`（完整使用教程）
5. 生成 `references/permissions.md`（权限声明模板）
6. 生成 `references/examples.md`（使用示例）
7. 生成 `CHANGELOG.md`（初始版本记录）
8. 生成 `.progress.md`（进度追踪文件）

### refactor 模式
1. **stage 1**（分析）：读取目标技能的 `SKILL.md`，提取 frontmatter、章节结构、触发词
2. **stage 2**（审查）：执行 R-01~R-21 审查，生成报告（JSON 格式）
3. **stage 3**（改造）：按审查报告进行渐进式加载改造（拆分 >230 行章节、补充缺失章节）
4. **stage 3.5**（`--fix-code`）：扫描 `scripts/` 中硬编码的数据目录引用，自动替换为 `_meta.json` 中的变量

### audit 模式
1. 加载 `spec/rules.json`（R-01~R-21 规则定义）
2. 对目标技能逐一执行规则检查（调用 `check_method`）
3. 生成审计报告（JSON 格式，含 `passed` / `severity` / `detail` / `fix`）
4. 若指定 `--fix` 且规则 `fixable: true`，自动执行修复

详见 `references/guide.md` 完整教程（按需创建）

> 版本更新记录详见 `CHANGELOG.md`

## 回滚说明（R-21）

所有写操作（create/update/refactor/migrate-data）均通过 `skill_rollback.py` 创建备份：

```bash
# 查看备份清单
python -m skill_rollback list <skill-dir>

# 回滚到指定备份
python -m skill_rollback rollback <skill-dir> --backup-id <id>

# 查看备份差异
python -m skill_rollback diff <skill-dir> --backup-id <id>
```

备份存储位置：`skills/.standardization/<skill>/backups/`

---

> 本文档由 `skill-standardization` v2.30.0 自身生成并通过 R-01~R-21 审计（PASS）。