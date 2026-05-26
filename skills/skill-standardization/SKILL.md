---
name: skill-standardization
version: 2.31.0
author: wUwproject
license: MIT
description: ['Skill 标准化规范引擎 v2.32.0。支持 R-01~R-22 审查（含数据目录规范检查 R-22）、refactor --fix-code 自动修复代码引用、audit --fix 自动修复 R-11/R-12/R-22 路径问题、统一 spec/rules.json、create 模式完整模板、migrate-data 命令迁移数据目录。', 'standardization', 'skill-builder', 'skill-audit', 'json-loader', 'refactor', 'progressive-loading', 'security', 'permission-check']
data_dir: ../.standardization/skill-standardization/
sensitive_access: true
critical_write: false
permission_weight: HIGH
artifact_paths: true
writing_standards: fix_terms
---


# skill-standardization v2.32.0


## 触发场景

当用户提出以下类型请求时，应触发本技能：

- 「用 skill-standardization 审计/改造某技能」
- 「检查某技能的 SKILL.md 是否规范」
- 「创建/更新/重构一个 skill」
- 「修复某技能的目录结构/数据路径」
- 「对某 skill 执行标准化审查」

**否定条件**：仅当用户明确要求「不使用标准化流程」或「手动编辑」时，不自动触发。


## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

本技能提供以下核心能力：

1. **R-01~R-22 规则审查** —— 对 SKILL.md 执行 22 条规范化审查
2. **refactor 模式** —— 改造现有技能（修复 frontmatter、迁移更新记录、统一术语、规范数据目录）
3. **create 模式** —— 从零创建符合规范的技能（含完整模板）
4. **audit --fix 模式** —— 自动修复 R-11/R-12/R-22 路径违规
5. **migrate-data 命令** —— 迁移技能数据目录到 `skills/.standardization/<skill>/` 规范路径


## 工作流程

→ 详见 [references/guide.md](references/guide.md)（完整执行流程章节）


## 渐进式加载说明

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

**引用说明**：
- 反模式 → 详见 [references/antipatterns.md](references/antipatterns.md)
- FAQ → 详见 [references/faq.md](references/faq.md)
