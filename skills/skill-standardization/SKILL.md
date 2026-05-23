---
name: skill-standardization
version: 2.3.0
author: wUwproject
license: MIT
description: >
  Skill 标准化规范引擎 v2（渐进式加载）。
  支持 R-01~R-10 审查、create/update/refactor 三模式。
tags: ["standardization", "skill-builder", "skill-audit", "json-loader", "refactor", "progressive-loading"]
---

# skill-standardization v2

> Skill 标准化规范引擎，支持 R-01~R-10 审查、create/update/refactor 三模式、渐进式 MD 体系。

提供 Skill 全生命周期标准化管理：
**create**（创建）→ **update**（更新）→ **refactor**（改造）→ **audit**（审查）→ **规范加载**

---

## 触发场景

- "创建/新建 skill"、"标准化创建 skill"
- "检查/审查/审计 SKILL.md"
- "更新/规范化已有 skill"
- "改造/重构 skill 结构"
- "SKILL.md 标准化"、"skill 标准验证"

---

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | **三种执行模式** | create / update / refactor |
| 2 | **10 条审查规则** | R-01~04 ERROR + R-05~10 WARN，纯警告不阻断 |
| 3 | **标准目录结构** | 根目录仅 SKILL.md + _meta.json，三级复杂度 |
| 4 | **渐进式 MD 体系** | 主文件 ≤200 行，辅助内容拆分 references/ 按需加载 |
| 5 | **零依赖 Python 工具** | 仅标准库，跨平台兼容 |
| 6 | **信息完整性保障** | refactor 强制备份 + 全量扫描 + 映射报告 |

---

## 快速开始

```bash
# 创建
python scripts/skill_builder.py create my-skill --desc "描述" --tags t1,t2
# 检查
python scripts/skill_builder.py update ~/.workbuddy/skills/my-skill
# 改造（先 dry-run！）
python scripts/skill_builder.py refactor ~/.workbuddy/skills/old-skill --dry-run
# 审查
python scripts/skill_audit.py audit ~/.workbuddy/skills/my-skill
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

## 渐进式 MD 文件体系

**核心原则：** 主 SKILL.md 必须可独立理解核心功能。references/ 下是按需加载的补充材料。

**本 skill 自身的拆分示范：**

| 本文件（SKILL.md）包含 | 拆分到 references/ |
|----------------------------|---------------------------|
| ✅ 触发场景、核心能力、快速开始 | 📄 `guide.md` — 三种模式详细教程 |
| ✅ 工作流程（本节） | 📄 `examples.md` — 完整示例集合 |
| ✅ 核心能力概述 | 📄 `reference.md` — API/命令参考 |
| ✅ 版本号更新映射表 | 📄 `architecture.md` — 架构设计 |
| ✅ 注意事项、铁律 | 📄 `changelog.md` — 版本更新日志 |
| | 📄 `faq.md` — 常见问题 |

**加载协议：**
```
用户任务 → AI 加载 SKILL.md（始终发生）
     ↓
  任务简单？ → 直接用 SKILL.md 执行
     ↓ 否
  任务复杂？ → 检查 SKILL.md 中的 references/ 引用 → 按需读取
```

---

## 审查规则（R-01 ~ R-10 概述）

| ID | 严重度 | 检查内容 |
|----|---------|----------|
| R-01 | ERROR | Frontmatter 存在性（`---` 包裹） |
| R-02 | ERROR | name 字段存在 |
| R-03 | ERROR | version 符合 SemVer |
| R-04 | ERROR | description 字段存在 |
| R-05 | WARN | name 与目录名一致 |
| R-06 | WARN | 正文含一级标题 |
| R-07 | WARN | 含触发条件章节 |
| R-08 | WARN | 含核心能力章节 |
| R-09 | WARN | 含工作流程章节 |
| R-10 | WARN | SKILL.md version == _meta.json version |

> ⚠️ 自 v2.0 起，ERROR 级在 git-sync 中仅为警告，不阻断同步。

→ 完整规则定义（含检查方法、修复指引、同义关键词）
→ 见 `references/reference.md`

---

## 版本号更新文件映射表

| 修改类型 | 需同步版本号的文件位置 | 升级类型 |
|---------|----------------------|---------|
| 修正错别字/排版（仅 SKILL.md） | SKILL.md `version` + `_meta.json` `"version"` | PATCH（2.1.0→2.1.1） |
| 修改 `scripts/spec/*.json` 规范 | 对应 `.json` 的 `"_version"` + SKILL.md + `_meta.json` | PATCH 或 MINOR（视变更范围） |
| 修改 `scripts/*.py` 脚本逻辑 | `.py` 文件头版本字符串 + SKILL.md + `_meta.json` | MINOR（2.1.0→2.2.0） |
| 新增功能/新脚本 | 所有上述文件 + `manifest.json`（上传时同步） | MINOR 或 MAJOR |
| 仅改 `references/*.md` | 视情况——内容影响功能时升 SKILL.md + `_meta.json` | 通常 PATCH |
| git-sync 上传成功后 | `manifest.json` 由 git-sync 自动更新 | 跟随 SKILL.md 版本 |

**关键原则：**
- 本地修改只改 SKILL.md + _meta.json + 受影响的脚本/json 文件内的版本字符串
- `manifest.json` 由 git-sync 上传流程负责，本地不应擅改
- **不确定是否升级版本号时，必须询问用户**（适用于所有上述文件类型）

---

## 注意事项

1. **refactor 前务必先 `--dry-run`**
2. **备份是 refactor 默认行为**：不要用 `--no-backup` 除非明确知道风险
3. **本文件控制在 200 行以内**：超过部分已拆分到 `references/`
4. **审查是纯警告模式**：不会阻止 git-sync 同步
5. **版本号三方一致**：修改后按上表同步

---

## ⚙️ 改写/更新铁律（AI 执行前必须遵守）

### 铁律 1：author 字段不可擅自替换

- 技能是通用工具，author 默认值必须为 `your-name-here` 占位符
- 已有 author 值（如 `"由 config.json 的 author 字段决定"`）保留原值不变
- 只有用户明确指定时才写入真实署名
- **本 skill 例外**：author 为 `wUwproject`（维护者署名，铁律1例外条款）

### 铁律 2：版本号更新规则（规范内有规定直接更新，无规定必须询问）

**规范内明确定义的文件/字段 — 直接更新，无需询问：**

| 文件 | 版本号位置 | 更新规则 |
|------|-----------|---------|
| `SKILL.md` | frontmatter `version:` | 按 SemVer 直接升级，无需询问 |
| `_meta.json` | `"version"` | 与 SKILL.md 保持一致，直接升级 |
| `scripts/spec/*.json` | `"_version"` 字段 | 对应模块变更时直接升级 |
| `scripts/*.py` | 文件头版本字符串（如 `v2.3.0`） | 脚本逻辑变更时直接升级 |

**规范未覆盖的文件/字段 — 必须询问用户：**

- 目标 skill 中存在但本规范未定义的版本号位置
- `manifest.json` 中的版本号（由 git-sync 上传流程负责，本地不应擅改）
- 任何不在上表中的文件或字段

→ 遇到上述情况时，先问用户"是否升级版本号？"，确认后再操作。

### 铁律 3：改写前必须理解每个文件的作用

- 修改任何文件前，先用 Read 工具阅读完整内容
- 理解每个字段的含义、引用关系、被哪些脚本使用
- 特别注意：`config.json`（运行时配置）、`manifest.json`（维护清单状态数据）、`_meta.json`（标准化元数据）
