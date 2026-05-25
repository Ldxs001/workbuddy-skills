---
name: skill-standardization
version: 2.27.0
author: wUwproject
license: MIT
description: Skill 标准化规范引擎 v2.26.0。修复审查规则数不一致（SKILL.md/reference.md/utils.py/__init__.py 统一为 R-01~R-21、补充 R-21 到审查规则表）。
tags: ['standardization', 'skill-builder', 'skill-audit', 'json-loader', 'refactor', 'progressive-loading', 'security', 'permission-check']
sensitive_access: true
critical_write: false
create_permissions_md: true
permission_weight: HIGH
antipattern_count: add_examples
section_faq: true
writing_standards: fix_terms
antipattern_vague: add_detail
section_antipattern: true
progressive_loading_explicit: true
---

# skill-standardization v2.25.0

> Skill 标准化规范引擎（安全增强版），支持 R-01~R-21 审查（含权限分级、敏感信息检测、授权检查、渐进式文件质量检查）、create/update/refactor 三模式、渐进式 MD 体系。

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

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。用本技能创建/更新/改造的技能均遵循此规范。

| # | 功能 | 说明 |
|---|------|------|
| 1 | **三种执行模式** | create / update / refactor |
| 2 | **21 条审查规则** | R-01~R-21（含安全规则、渐进式文件质量检查） |
| 3 | **标准目录结构** | 根目录仅 SKILL.md + _meta.json，三级复杂度 |
| 4 | **渐进式 MD 体系** | 主文件 ≤230 行，辅助内容拆分 references/ 按需加载 |
| 5 | **零依赖 Python 工具** | 仅标准库，跨平台兼容 |
| 6 | **信息完整性保障** | refactor 强制备份 + 全量扫描 + 映射报告 |
| 7 | **权限检查器** | `scripts/permission_checker.py` 扫描脚本权限、计算权重、生成风险报告 |
| 8 | **授权管理器** | `scripts/authorization_manager.py` 统一审批 + 即时审批，防止未授权高风险操作 |

---

## 快速开始

```bash
# ══════════════════════════════════════════════════════════
# 调用指引（非常重要！）
# ══════════════════════════════════════════════════════════
#
# 本 skill 的 scripts/ 下有两种结构：
#   1. 包结构（需 python -m 调用）：skill_builder、skill_audit
#   2. 单文件（直接 python 调用）：permission_checker.py、authorization_manager.py
#
# ══════════════════════════════════════════════════════════

# 创建（包结构，必须用 python -m）
cd ~/.workbuddy/skills/skill-standardization/scripts
python -m skill_builder create my-skill --desc "描述" --tags t1,t2

# 更新（包结构，必须用 python -m）
python -m skill_builder update ~/.workbuddy/skills/my-skill

# 改造（包结构，必须用 python -m，先 dry-run！）
python -m skill_builder refactor ~/.workbuddy/skills/old-skill --dry-run

# 审查（包结构，必须用 python -m）
python -m skill_audit audit ~/.workbuddy/skills/my-skill
python -m skill_audit audit-all ~/.workbuddy/skills

# 权限检查（单文件，直接调用）
python scripts/permission_checker.py ~/.workbuddy/skills/my-skill --json

# 授权请求（单文件，直接调用）
python scripts/authorization_manager.py request --type immediate --reason "需要删除临时文件"
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
```

### 三种模式快速对照

| 模式 | 用途 | 关键参数 |
|------|------|----------|
| `create` | 从模板创建标准 skill | `--desc`, `--tags` |
| `update` | 增量检查/修复 | `--fix`, `--backup` |
| `refactor` | 整体结构改造 | `--dry-run`, `--no-backup` |

→ 三种模式详解、迁移规则 M-01~M-06、安全保障机制
→ 详见 `references/guide.md`（按需加载）

---

## 渐进式 MD 文件体系

**核心原则：** 主 SKILL.md 必须可独立理解核心功能。references/ 下是按需加载的补充材料。

**本 skill 自身的拆分示范：**

| 本文件（SKILL.md）包含 | 拆分到 references/ |
|----------------------------|---------------------------|
| ✅ 触发场景、核心能力、快速开始 | 📄 `guide.md` — 三种模式详细教程 |
| ✅ 工作流程（本节） | 📄 `examples.md` — 完整示例集合 |
| ✅ 核心能力概述 | 📄 `reference.md` — API/命令参考 |
| ✅ 审查规则概述 | 📄 `changelog.md` — 版本更新日志 |
| | 📄 `faq.md` — 常见问题 |
| | 📄 `antipatterns.md` — 反模式收录 |

**加载协议：**
```
用户任务 → AI 加载 SKILL.md（始终发生）
     ↓
  任务简单？ → 直接用 SKILL.md 执行
     ↓ 否
  任务复杂？ → 检查 SKILL.md 中的 references/ 引用 → 按需读取
```

→ 反模式详见 `references/antipatterns.md`
→ 常见问题详见 `references/faq.md`

---

## 审查规则（R-01 ~ R-21 概述）

| ID | 严重度 | 检查内容 |
|----|---------|----------|
| R-01 | ERROR | Frontmatter 存在性（`---` 包裹） |
| R-02 | ERROR | name 字段存在 |
| R-03 | ERROR | version 符合 SemVer |
| R-04 | ERROR | description 字段存在 |
| R-05 | WARN | name 与目录名一致 |
| R-06 | WARN | 正文含一级标题 |
| R-07 | ERROR | 含触发条件章节（须含正向触发词≥3个、否定条件≥1个） |
| R-08 | WARN | 含核心能力章节 |
| R-09 | WARN | 含工作流程章节 |
| R-10 | ERROR | SKILL.md version == _meta.json version |
| R-11 | ERROR | 产出物路径规范性（铁律4） |
| R-12 | ERROR | 外部数据目录路径遵循 `skills/.standardization/<skill-name>/` |
| R-13 | ERROR | 敏感信息访问声明 |
| R-14 | ERROR | 关键位置写入声明 |
| R-15 | ERROR | 高权限操作授权检查 |
| R-16 | WARN | 权限权重说明 |
| R-17 | ERROR | 渐进加载引用（SKILL.md > 230 行时必须拆分） |
| R-18 | WARN | 反模式具体性（引用 `references/antipatterns.md` 且内容具体） |
| R-19 | WARN | FAQ 有意义性（引用 `references/faq.md` 且 Q&A 对有意义） |
| R-20 | WARN | 写作规范（术语一致/无模糊表述/中英文混排） |
| R-21 | WARN | 渐进式加载显式说明（SKILL.md 显眼位置含「渐进式加载」或「progressive」关键词） |

> ⚠️ 自 v2.0 起，ERROR 级在 git-sync 中仅为警告，不阻断同步。

→ 完整规则定义（含检查方法、修复指引、同义关键词）
→ 见 `references/reference.md`

---

## ⚙️ 改写/更新铁律（AI 执行前必须遵守）

→ 详见 `references/rules.md`（按需加载）
