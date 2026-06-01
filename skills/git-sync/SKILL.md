---
name: git-sync
version: 2.7.2
author: wUwproject
license: MIT
description: 将skill代码规范化推送到码云、GitHub，并生成ZIP安装包。修复跳过同步时状态显示「成功」的误导问题，改为跳过。修复审计问题，统一术语，修正自审粒度。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/git-sync/
tags: [sync, git, zip, skill-manager, manifest, security]
external_data_dir: true
trigger: 同步/上传/推送/发布某个skill
trigger_negative: 只是看文件/通用git提交/文件同步到云端
h1_version: true
---
# git-sync — 三端同步技能

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
- **SKILL.md 规范审查** —— 内联审计（版本一致性 + R-23 脚本引用检查）
- **ZIP 打包 + HTML 索引** —— 生成安装包 + 可视化索引页


### 渐进式文件索引

| 文件名 | 位置 | 说明 |
|--------|------|------|
| `antipatterns.md` | git-sync 反模式 | 常见错误和注意事项，避免误用本技能。 |
| `changelog.md` | changelog.md — git-sync 更新日志 | - 版本号 2.6.28 → 2.6.29（`update --fix` 自动 bump） |
| `faq.md` | git-sync 常见问题 | --- |
| `guide.md` | git-sync 完整使用指南 | > 本文档是 SKILL.md 的渐进式补充，包含完整的执行流程、步骤详解和配置说明。 |
| `permissions.md` | git-sync — 权限说明（详细版） | > 本文档由 `permission_checker.py` 扫描生成，记录 git-sync 所有权限需求、风险等级及 |
| `reference.md` | git-sync 完整参考手册 | > CLI 命令速查、路径变量、排除列表、文件结构规范。 |
本技能采用渐进式 MD 体系，`SKILL.md` 为轻量入口，详细规范拆分到 `references/` 按需加载。

> → 详见 `references/antipatterns.md`
> → 详见 `references/faq.md`：

- 🔴 `references/guide.md` — **必读**，完整执行流程 + AI 输出要求
- `references/reference.md` — CLI 命令速查、Git 调用规范、路径变量
- `references/changelog.md` — 版本更新记录
- `references/architecture.md` — 内部架构（脚本映射、目录结构）
- `references/antipatterns.md` — 反模式（常见错误）
- `references/faq.md` — 常见问题（443 超时、版本冲突等）

## 数据目录说明

本技能的数据文件（扫描结果、临时副本、ZIP 包等）存放在：

```
skills/.standardization/git-sync/
```

通过 frontmatter 的 `data_dir: ../.standardization/git-sync/` 声明。安装目录 `skills/git-sync/` 只保留 SKILL.md 和 scripts/。


## 约束
- 禁止字母数字
- 必须实施完整的授权检查机制
- R-20 写作规范修复**：faq.md 中"应该"改为"必须"（模糊表述→确定性描述）；SKILL.md 中 `git-sy
- 修复 SKILL.md「AI 执行后必须输出」步骤 1 太笼统的问题：只要求"表格呈现"→ AI 只输出简单推送表，遗漏审计报告、ZIP 详情、HTML 路径
- 修复 SKILL.md 标题仍是 `v2.6.24` 未同步更新

### 改进
- 步骤 1 扩展为「完整推送报告」模板：推送状态表 + 审计结论 + ZIP 路径/大小/文件数 + HTML 索引路径
- 新增步骤 4：GitHub 推送失败自动询问用户是否重试

---
## 2.6.26 (2026-05-29)

### 修复
- 修复 `SKILL.md` fro
- `SKILL.md` 新增「AI 执行后必须输出」章节：明确 3 步必做操作
- `SKILL.md` 渐进式加载列表新增 `guide.md`（标为必读）
- `guide.md` 已有的 `preview_url` 指令现在被 SKILL.md 显式引用

---

## 2.6.25 (2026-05-28)

### 修复
- 修复 `