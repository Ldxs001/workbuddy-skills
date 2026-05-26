---
name: git-sync
version: 2.6.21
author: wUwproject
license: MIT
description: 将skill代码规范化推送到码云、GitHub，并生成ZIP安装包。修复push前提前pull导致的本地修改被覆盖问题。
sensitive_access: true
critical_write: false
permission_weight: CRITICAL
artifact_paths: []
writing_standards: fix_terms
data_dir: ../.standardization/git-sync/
antipattern_reference: true
faq_reference: true
---



# git-sync v2.6.21 — 三端同步技能

将 skill 代码规范化推送到**码云（Gitee）**、**GitHub**，并生成 **ZIP 安装包**。

## 触发场景

当用户提出以下类型请求时，应触发本技能：

- 「同步/上传/推送/发布某个 skill」
- 「打包某个 skill」
- 「更新 README.md 的技能列表」
- 「检查某个 skill 的版本号」

**不触发**（以下情况不应触发本技能）：

- 用户只是说「帮我看看这个文件」——没有同步/打包意图
- 用户要求「用 git 提交代码」——这是通用 git 操作，不是 skill 同步
- 用户提到「同步」但指的是文件同步（如「同步到云端」）——不是 skill 仓库同步

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

- **三端同步** —— 码云、GitHub、本地 `.dist/` 目录
- **版本号三方对比** —— `_meta.json` / `SKILL.md` frontmatter / `references/changelog.md`
- **敏感信息过滤** —— 自动扫描并脱敏 `secrets/regex/telemetry`
- **SKILL.md 规范审查** —— 调用 `skill-standardization` 进行审计
- **ZIP 打包 + HTML 索引** —— 生成安装包 + 可视化索引页

## 工作流程

```workflow
1. 读取目标 skill 的 _meta.json + SKILL.md
2. 三方版本号对比（不一致则中断）
3. 调用 skill-standardization 审查 SKILL.md 规范性
4. 敏感信息扫描（.gitignore + regex + telemetry）
5. 脱敏处理（副本中替换，原文件不动）
6. 三端同步（Git 推送 + ZIP 打包 + README 更新）
7. 生成 HTML 索引（.dist/index.html）
```

## 渐进式加载说明

本技能采用渐进式 MD 体系，`SKILL.md` 为轻量入口，详细规范拆分到 `references/` 按需加载：

- `references/reference.md` — 完整参考手册（命令、配置、故障排查）
- `references/changelog.md` — 版本更新记录
- `references/architecture.md` — 内部架构（脚本映射、目录结构）

> 💡 阅读时先看本章节，按需让 AI 加载 `references/*.md`。

## 数据目录说明

本技能的数据文件（扫描结果、临时副本、ZIP 包等）存放在：

```
skills/.standardization/git-sync/
```

通过 frontmatter 的 `data_dir: ../.standardization/git-sync/` 声明。安装目录 `skills/git-sync/` 只保留 SKILL.md 和 scripts/。
