---
name: skill-standardization
version: 2.47.4
author: wUwproject
license: MIT
description: Skill 标准化规范引擎。支持 R-01~R-25 规范审查（audit/refactor/create 三模式），含权限扫描、数据目录合规检查、渐进式加载、更新日志渐进加载强制、_meta.json 字段规范性。R-07 增强：frontmatter trigger/trigger_negative 与正文一致性。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/skill-standardization/
tags: ['standardization', 'skill-builder', 'skill-audit', 'validation', 'json-loader', 'refactor', 'version-bump', 'changelog-auto', 'data-dir']
external_data_dir: true
trigger:
  - 帮我看看这个技能写得怎么样
  - 检查这个技能是否规范
  - 审计 skill
  - 创建新技能
  - 更新 skill
  - 重构技能
  - skill 规范
  - R-规则
trigger_negative: 当用户仅闲聊或问你有什么技能时不触发；单步任务如查看文件不触发
meta_field_sync: true
h1_position: true
---
# skill-standardization

## 约束

- **`.md` 文件禁止使用 Write/Edit 工具更新** — 必须用 `scripts/` 下的 Python 脚本原子写入
- **版本号三端一致** — 更新时同步 `SKILL.md` / `_meta.json` / `references/changelog.md`
- **更新后必须 `audit .` 自审** — 0 ERROR 0 WARN 方可提交
- **`--fix` 自动修正后** — 将 fix_details 转化为可读 changelog 并用 safe_io 写入

## 触发场景

当用户提出以下类型请求时，应触发本技能：

**自然语言（推荐）**：
- [帮我看看这个技能写得怎么样 / 这个技能规范吗]
- [检查/审查/评估一下这个技能]
- [给这个 skill 做个检查 / 跑一遍规范]
- [创建/生成一个新技能 / 把 xxx 做成 skill]
- [更新/改造一下这个 skill / 重构这个技能]
- [这个 skill 的 frontmatter/描述/规则怎么写]

**技术关键词**：
- [用 skill-standardization 审计/改造某技能]
- [检查某技能的 SKILL.md 是否规范]
- [创建/更新/重构一个 skill]
- [skill 的 frontmatter 怎么写]
- [R-xx 规则是什么意思]

**不触发**（以下情况不应触发本技能）：

- 用户只是问[你有什么技能]——这是闲聊，不是真的要审计/改造
- 用户要求执行某个 skill 的常规功能——应直接调用该 skill 本身，而不是先审计它
- 用户只是提到[skill]这个词，但没有明确的审计/创建/改造意图

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。





### 渐进式文件索引

| 文件名 | 位置 | 说明 |
|--------|------|------|
| `references/antipatterns.md` | 反模式（Anti-Patterns） | > 本文件收录 skill 编写过程中的常见反模式，帮助 AI 和开发者避开典型坑点。 |
| `references/architecture.md` | 架构设计 | > 本文件描述 skill-standardization v2 的整体架构、模块关系和数据流。 |
| `references/changelog.md` | changelog | - 修复 _load_body_spec 路径错误（spec/→scripts/spec/），导致 fix_sectio |
| `references/data_dir_map.md` | skill-standardization 数据目录路径引用对照表 | 1. **安装目录**（`skills/<name>/` 或 `skills/installed/<name>/`）—— |
| `references/examples.md` | 示例集合 — skill-standardization v2 | 本文件包含 skill-standardization v2 各种使用场景的完整示例。 |
| `references/faq.md` | 常见问题（FAQ） | > 本文件收集 skill-standardization v2 使用过程中的常见疑问和解答。 |
| `references/guide.md` | 使用指南 — skill-standardization v2 | 本指南提供 skill-standardization v2 三种执行模式的详细操作教程。 |
| `references/permissions.md` | 权限说明 | 权限扫描风险等级：**CRITICAL** |
| `references/reference.md` | API / 命令参考 | > 本文件为 skill-standardization v2 的完整命令参考手册。 |
| `references/rules.md` | 改写/更新铁律（AI 执行前必须遵守） | > 本文件为 skill-standardization v2.13.0 的铁律条款，AI 更新任何 skill 前必须 |
## 工作流程

**audit 模式**（仅审查）：
1. 读取目标 skill 的 SKILL.md
2. 执行 R-01~R-25 规则检查
3. 输出审查报告（PASS/WARN/FAIL），逐条列出通过/失败/跳过
4. 若传了 --fix，自动修正可修复项（R-01/R-03/R-11/R-12/R-22 等）
5. 调用 `fix.py` 按规则 ID 分派自动修复（推荐：审计后自动修复 WARN/ERROR 项）

**create 模式**（创建新技能）：
1. `python -m scripts.skill_builder create <name> --desc "描述"` — 从模板生成标准骨架
2. 自动生成 SKILL.md（含 H1/触发/核心/快速开始/工作流程章节占位符）
3. 自动生成 _meta.json（7 字段）、references/ 目录、scripts/ 目录
4. AI 或手动填充 TODO 占位符为实际内容
5. `python -m scripts.skill_audit audit <dir>` 验证合规
6. 按需补充 scripts/ 功能代码 + references/ 渐进式文档
7. **cleanup 清理** — 操作完成后清除生成过程中的临时文件

**update/refactor 模式**（改造+审查）：
1. 操作前整体备份（时间戳命名）
2. **★ 强制 inspect 蓝皮书扫描** — 输出技能结构、AST 函数签名、引用链路
3. 执行 audit（R-01~R-25）或 refactor 改造步骤
4. 调用 fix.py 自动修复（规则 ID 分派）
5. **再次审计确认 0 ERROR 0 WARN**
6. **bump 版本号**（三端同步 SKILL.md / _meta.json / changelog）
7. **cleanup 清理** — manifest 驱动删除临时文件、过期备份

> 两阶段检查协议、排错止损规则 → 详见 `references/guide.md`
> 临时文件与备份管理 → 详见 `references/guide.md` 的 cleanup 章节

## 数据目录说明

本技能的数据文件（审查缓存、进度文件、备份、日志等）存放在：

```
../.standardization/skill-standardization/
```

> 安装目录 `skills/skill-standardization/` 只保留 SKILL.md 和 scripts/，数据文件不越位。
