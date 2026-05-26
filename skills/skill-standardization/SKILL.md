---
name: skill-standardization
version: 2.34.1
author: wUwproject
license: MIT
description: Skill 标准化规范引擎 v2.34.2。恢复误删的 fix_r20.py/fix_r06_r20.py（通用修复工具），确认其余一次性脚本删除正确。
data_dir: ../.standardization/skill-standardization/
sensitive_access: true
critical_write: false
permission_weight: HIGH
artifact_paths: references/, scripts/skill_audit/, scripts/skill_builder/
writing_standards: fix_terms
---



















# skill-standardization v2.33.0

## ⚠️ 文件更新约束

> **本技能的所有 `.md` 文件禁止使用 Write/Edit 工具更新（会损坏 UTF-8 中文编码）。**
> 必须用 `scripts/` 下的 Python 脚本原子写入（`tmp + os.replace()`）。

| 文件 | 更新方式 | 脚本 |
|------|----------|------|
| `SKILL.md` frontmatter | Python 原子写入 | `scripts/update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 正则替换 | `scripts/fix_progressive_loading.py` |
| `references/*.md` | `scripts/safe_io.py` 的 `safe_write()` | 随技能自带 |
| 更新日志 | Python 合并脚本 | 每次发版统一维护 `references/changelog.md` |

**检查清单（每次更新前）**：
- [ ] 是否用了 Write/Edit 工具？→ 立刻停止，改用 Python 脚本
- [ ] 是否在 `references/changelog.md` 维护更新记录？→ 根目录不得有 `CHANGELOG.md`
- [ ] 更新后是否用 `python -m scripts.skill_audit audit .` 自审？→ 必须 0 ERROR 0 WARN

## 触发场景

当用户提出以下类型请求时，应触发本技能：

- [用 skill-standardization 审计/改造某技能]
- [检查某技能的 SKILL.md 是否规范]
- [创建/更新/重构一个 skill]
- [skill 的 frontmatter 怎么写]
- [R-xx 规则是什么意思]

**不触发**（以下情况不应触发本技能）：

- 用户只是问[你有什么技能]——这是闲聊，不是真的要审计/改造
- 用户要求执行某个 skill 的常规功能（如[用 git-sync 同步某个 skill]）——应直接调用该 skill，而不是先审计它
- 用户只是提到[skill]这个词，但没有明确的审计/创建/改造意图

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

- **audit 模式** — 对指定 skill 目录执行 R-01~R-22 规范审查，输出通过/失败/跳过统计
- **refactor 模式** — 改造现有技能（修复 frontmatter、迁移更新记录、统一术语、规范数据目录、R-22 数据目录合规检查）
- **create 模式** — 基于标准化模板创建新 skill，自动注入 R-07~R-09/R-18~R-22 章节引用

## 工作流程

1. 读取目标 skill 的 SKILL.md
2. 执行 R-01~R-22 规则检查
3. 输出审查报告（通过/失败/跳过）
4. 若传了 --fix，自动修正 R-11/R-12/R-22 违规

## 渐进式加载说明

本技能采用渐进式 MD 体系，SKILL.md 为轻量入口，详细规范拆分到 references/ 按需加载：

- `references/guide.md` — 完整使用指南（触发词、工作流程、输出格式）
- `references/architecture.md` — 内部架构（模块划分、RULES 注册、METHOD_MAP）
- `references/antipatterns.md` — 反模式手册（常见错误 + 正确做法标记）
- `references/faq.md` — 常见问题解答（排错、自定义规则、CI 集成）
- `references/changelog.md` — 版本更新记录

> 阅读时先看本章节，按需让 AI 加载 references/*.md。

## 数据目录说明

本技能的数据文件（审查缓存、进度文件等）存放在：

```
skills/.standardization/skill-standardization/
```

> 安装目录 `skills/skill-standardization/` 只保留 SKILL.md 和 scripts/，数据文件不越位。
