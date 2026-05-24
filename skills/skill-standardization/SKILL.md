---
name: skill-standardization
version: 2.15.0
author: wUwproject
license: MIT
description: >
  Skill 标准化规范引擎 v2.14.0（安全增强版）。
  支持 R-01~R-17 审查（含权限分级、敏感信息检测、授权检查、触发条件合规性）、
  create/update/refactor 三模式，服务于其他 skill 的安全创建/更新/改造。
tags: ["standardization", "skill-builder", "skill-audit", "json-loader", "refactor", "progressive-loading", "security", "permission-check"]
sensitive_access: false
critical_write: false
---

# skill-standardization v2.14.0

> Skill 标准化规范引擎（安全增强版），支持 R-01~R-17 审查（含权限分级、敏感信息检测、授权检查）、create/update/refactor 三模式、渐进式 MD 体系。

提供 Skill 全生命周期标准化管理：
**create**（创建）→ **update**（更新）→ **refactor**（改造）→ **audit**（审查）→ **规范加载**

---

## 触发场景

- "使用 skill-standardization 创建/标准化 skill"
- "使用 skill-builder 审查/审计 SKILL.md 规范性"
- "使用 skill-standardization update/refactor 模式更新或改造 skill 结构"
- "按照 skill-standardization 规范进行 SKILL.md 标准化验证"
- **否定条件**：除非用户明确提到其他技能（如 skill-creator、cangjie-skill），否则优先使用本技能

---

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | **三种执行模式** | create / update / refactor |
| 2 | **17 条审查规则** | R-01~R-17（含安全规则 R-13~R-17：敏感信息访问、关键位置写入、授权检查、权限权重、渐进加载强制） |
| 3 | **标准目录结构** | 根目录仅 SKILL.md + _meta.json，三级复杂度 |
| 4 | **渐进式 MD 体系** | 主文件 ≤200 行，辅助内容拆分 references/ 按需加载 |
| 5 | **零依赖 Python 工具** | 仅标准库，跨平台兼容 |
| 6 | **信息完整性保障** | refactor 强制备份 + 全量扫描 + 映射报告 |
| 7 | **权限检查器** | `scripts/permission_checker.py` 扫描脚本权限、计算权重、生成风险报告 |
| 8 | **授权管理器** | `scripts/authorization_manager.py` 统一审批 + 即时审批，防止未授权高风险操作 |

---

## 快速开始

```bash
# 创建
python scripts/skill_builder.py create my-skill --desc "描述" --tags t1,t2
# 检查（含权限扫描）
python scripts/skill_builder.py update ~/.workbuddy/skills/my-skill
# 改造（先 dry-run！）
python scripts/skill_builder.py refactor ~/.workbuddy/skills/old-skill --dry-run
# 审查
python scripts/skill_audit.py audit ~/.workbuddy/skills/my-skill
# 权限检查（独立运行）
python scripts/permission_checker.py ~/.workbuddy/skills/my-skill --json
# 授权请求（AI 调用）
python scripts/authorization_manager.py request --type immediate --reason "需要删除临时文件"
# 加载规范（渐进式）
python scripts/json_loader.py load structure          # 目录结构
python scripts/json_loader.py load progressive_md     # 渐进式MD体系
```

→ 完整命令参考见 `references/reference.md`

---

## 工作流程

### AI 执行节奏

```
用户请求 → 加载本 SKILL.md（始终发生）
  ↓
判断任务类型
  ├── 简单（单次 create/update）──→ 仅用本文件完成
  └── 复杂（refactor / 不熟悉规范）──→ 读取 references/*.md
  ↓
执行对应模式 → 输出结果报告
  ↓
如报告含权限风险（R-13~R-17）──→ 按需加载 `references/permissions.md`
  ↓
向用户说明权限类型、风险等级、触发行为，协助用户决策
```

### 三种模式快速对照

| 模式 | 用途 | 关键参数 |
|------|------|----------|
| `create` | 从模板新建标准 skill | `--desc`, `--tags` |
| `update` | 增量检查/修复 | `--fix`, `--backup` |
| `refactor` | 整体结构改造 | `--dry-run`, `--no-backup` |

→ 三种模式详解、迁移规则 M-01~M-06、安全保障机制
→ 详见 `references/guide.md`（按需加载）

---

## 三模式执行流程（明确规定）

> AI 执行三模式时必须严格按以下流程推进，不可跳步或靠自觉。

### 创建模式（create）— 规范流程

```
Step 1  理解用户意图
        明确要创建什么 skill、触发场景、核心能力
        ↓
Step 2  规划渐进式拆分
        明确 SKILL.md 主文件保留什么（≤230行）
        明确 references/changelog.md、guide.md、permissions.md 各放什么
        ↓
Step 3  执行创建
        调用 creator.create() 创建骨架（SKILL.md + _meta.json + 三个 references/ 文件）
        ↓
Step 4  填充内容（AI 执行）
        填充 SKILL.md（确保 ≤230 行，含渐进式加载引用表）
        填充 references/guide.md（详细指南）
        ↓
Step 5  权限扫描 → 写权限声明
        运行: python scripts/permission_checker.py <skill_dir>
        根据扫描结果更新 references/permissions.md
        更新 SKILL.md frontmatter 的 authorization: 字段
        ↓
Step 6  审计循环（目标 ≥95%）
        运行: python -m scripts.skill_audit <skill_dir>
        如 verdict=PASS 且通过率 ≥95% → 进入 Step 7
        否则：根据审计报告修正 → 重跑审计 → 循环直到 ≥95%
        ↓
Step 7  收尾
        更新 references/changelog.md 记录创建版本
        输出创建报告给用户
```

**关键规则：**
- 权限扫描必须在内容填充后执行（扫描真实内容， not 模板）
- 审计循环由 AI 协调：`_check_skill_audit()` → 读结果 → 修正 → 重跑
- 不必 100%，≥95% 即可通过

---

### 更新模式（update）— 规范流程

```
Step 1  理解更新需求
        明确要更新什么功能、修复什么问题、版本号如何变更
        ↓
Step 2  执行更新检查
        调用 updater.update() 进行全面检查
        加 --fix 参数可自动修复部分问题
        加 --backup 参数创建备份
        ↓
Step 3  审计循环（目标 ≥95%）
        运行: python -m scripts.skill_audit <skill_dir>
        如 verdict=PASS 且通过率 ≥95% → 进入 Step 4
        否则：根据审计报告修正 → 重跑审计 → 循环直到 ≥95%
        ↓
Step 4  版本号更新
        更新 SKILL.md frontmatter version: 字段
        更新 _meta.json version 字段（必须一致）
        更新 references/changelog.md 记录本次更新
        ↓
Step 5  输出更新报告
        输出检查结果、修复内容、版本变更
```

**关键规则：**
- update 模式不改 SKILL.md 主文件结构，只做增量修改
- 版本号更新必须在审计通过后执行
- 如更新涉及权限变更，需重新运行 permission_checker.py

---

### 改造模式（refactor）— 规范流程

```
Step 1  先跑审计，获取所有问题
        运行: python -m scripts.skill_audit <skill_dir>
        记录所有 ERROR/WARN 项
        ↓
Step 2  规划改造方案
        根据审计结果 + refactor.MIGRATION_RULES 规划文件迁移方案
        先 dry-run 确认改造计划（--dry-run）
        ↓
Step 3  执行改造
        调用 refactor.refactor() 执行改造
        自动创建备份（除非 --no-backup）
        执行文件迁移（scripts/、references/ 归位）
        ↓
Step 4  保全检查（第一次）
        调用 refactor._preservation_check()
        检查：结构完整性 + Python 语法 + Shell 语法
        如有语法错误 → 修正 → 重跑保全检查
        ↓
Step 5  审计循环（目标 ≥95%）
        运行: python -m scripts.skill_audit <skill_dir>
        如 verdict=PASS 且通过率 ≥95% → 进入 Step 6
        否则：修正 → 重跑审计 → 循环直到 ≥95%
        ↓
Step 6  保全检查（第二次）
        再次调用 refactor._preservation_check()
        确认改造后功能不受损
        ↓
Step 7  版本号更新
        更新 SKILL.md frontmatter version: 字段（建议 +0.1.0）
        更新 _meta.json version 字段
        更新 references/changelog.md 记录本次改造
        ↓
Step 8  输出改造报告
        输出迁移计划、备份位置、检查结果、保全状态
```

**关键规则：**
- 改造前必须先 dry-run（--dry-run）确认方案
- 保全检查必须执行两次（改造后 + 审计通过后各一次）
- refactor 不改变 skill 功能，只改变目录结构和规范性

---

### 审计循环通用说明

```
审计循环（三模式共用）：
    ↓
运行 skill_audit（R-01~R-17 规则审查）
    ↓
verdict == "PASS" 且通过率 ≥95%？
    ├── 是 → 通过，继续下一步
    └── 否 → 根据审计报告修正问题 → 回到"运行 skill_audit"
    ↓
（最多循环 5 次，如仍 <95% 则输出剩余问题给用户决策）
```

**通过率计算：** `通过率 = (PASS 数) / (Total 数 - SKIP 数)`



## 渐进式 MD 文件体系

**核心原则：** 主 SKILL.md 必须可独立理解核心功能。references/ 下是按需加载的补充材料。

**本 skill 自身的拆分示范：**

| 本文件（SKILL.md）包含 | 拆分到 references/ |
|----------------------------|---------------------------|
| ✅ 触发场景、核心能力、快速开始 | 📄 `guide.md` — 三种模式详细教程 |
| ✅ 工作流程（本节） | 📄 `examples.md` — 完整示例集合 |
| ✅ 核心能力概述 | 📄 `reference.md` — API/命令参考 + 权限类型说明 |
| ✅ 版本号更新映射表 | 📄 `architecture.md` — 架构设计 |
| ✅ 注意事项、铁律 | 📄 `changelog.md` — 版本更新日志 |
| | 📄 `permissions.md` — 权限类型、风险等级、行为对照表 |
| | 📄 `faq.md` — 常见问题 |

**加载协议：**
```
用户任务 → AI 加载 SKILL.md（始终发生）
     ↓
  任务简单？ → 直接用 SKILL.md 执行
     ↓ 否
  任务复杂？ → 检查 SKILL.md 中的 references/ 引用 → 按需读取
```

### 增量更新记录规范

**核心规则：** update/refactor 模式下产生的更新记录（变更日志、差异报告、迁移映射等）必须写入 `references/changelog.md`，**禁止写入主 SKILL.md**。

| 规则 | 说明 |
|------|------|
| 主文件仅保留版本号 | SKILL.md frontmatter `version:` 是唯一的版本标识，不承载变更历史 |
| 变更记录渐进式加载 | 每次 update/refactor 操作产出的记录追加至 `references/changelog.md` |
| 主文件行数可控 | 详细历史信息不占主文件篇幅，确保 SKILL.md ≤200 行 |

---

## 审查规则（R-01 ~ R-17 概述）

| ID | 严重度 | 检查内容 |
|----|---------|----------|
| R-01 | ERROR | Frontmatter 存在性（`---` 包裹） |
| R-02 | ERROR | name 字段存在 |
| R-03 | ERROR | version 符合 SemVer |
| R-04 | ERROR | description 字段存在 |
| R-05 | WARN | name 与目录名一致 |
| R-06 | WARN | 正文含一级标题 |
| R-07 | ERROR | 含触发条件章节（须含正向触发词≥3个、否定条件≥1个、禁止"自动执行"等危险表述） |
| R-08 | WARN | 含核心能力章节 |
| R-09 | WARN | 含工作流程章节 |
| R-10 | ERROR | SKILL.md version == _meta.json version |
| R-11 | ERROR | 产出物路径规范性（铁律4：skills/.standardization/<skill>/），含路径遍历检测、跨目录写入检测、敏感信息检测 |
| R-12 | ERROR | 外部数据目录路径（`DATA_DIR`等）必须遵循 `skills/.standardization/<skill-name>/` 约定，且 `_meta.json` 必须声明 `data_dir` 字段与之一致 |
| R-13 | ERROR | 敏感信息访问声明（由 `permission_checker.py` 检查，见 references/reference.md） |
| R-14 | ERROR | 关键位置写入声明（由 `permission_checker.py` 检查，见 references/reference.md） |
| R-15 | ERROR | 高权限操作授权检查（由 `authorization_manager.py` 检查，见 references/reference.md） |
| R-16 | WARN | 权限权重说明（由 `permission_checker.py` 计算权重，见 references/guide.md） |
| R-17 | ERROR | 渐进加载引用（SKILL.md > 200 行时必须拆分到 references/ 并通过"→ 详见 references/xxx.md"引用，禁止主文件超限） |

> ⚠️ 自 v2.0 起，ERROR 级在 git-sync 中仅为警告，不阻断同步。

→ 权限详细说明（类型、风险等级、触发条件、skill 行为对照表）
→ 详见 `references/permissions.md`

→ 完整规则定义（含检查方法、修复指引、同义关键词）
→ 见 `references/reference.md`

---


---

## 渐进式加载引用

| 本文件（SKILL.md）包含 | 拆分到 references/ |
|----------------------------|---------------------------|
| ✅ 触发场景、核心能力、快速开始 | 📄 `guide.md` — 三种模式详细教程 + 安全增强功能 |
| ✅ 工作流程（本节） | 📄 `examples.md` — 完整示例集合 |
| ✅ 核心能力概述 | 📄 `reference.md` — API/命令参考 + 权限类型说明 |
| ✅ 审查规则概述（R-01~R-17） | 📄 `rules.md` — 铁律条款详解 |
| ✅ 增量更新记录规范 | 📄 `changelog.md` — 版本更新日志 |
| | 📄 `permissions.md` — 权限类型、风险等级、行为对照表 |
| | 📄 `faq.md` — 常见问题 |

→ 详见 `references/guide.md`（按需加载）

---

## 版本号更新文件映射表

→ 详见 `references/reference.md`（按需加载）

---

## 注意事项

→ 详见 `references/guide.md`（按需加载）

---