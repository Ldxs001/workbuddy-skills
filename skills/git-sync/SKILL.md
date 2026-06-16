---
name: git-sync
version: 2.21.1
author: wUwproject
license: MIT
description: 将skill代码规范化推送到码云、GitHub，并生成ZIP安装包。修复_push_with_cred_url/pull_with_cred_url未检查URL内嵌token的缺陷（remote URL已含token时不需查git-credentials）。
sensitive_access: true
critical_write: false
permission_weight: CRITICAL
data_dir: ../.standardization/git-sync/
tags: ['sync', 'git', 'gitee', 'github', 'deploy']
external_data_dir: true
trigger: 同步/推送/发布/上传/打包/更新READ ME
trigger_negative: 只是看文件/通用git提交/文件同步到云端
h1_version: true
meta_field_sync: true
create_permissions_md: true
h1_position: true
data_dir_compliance: true
---
# git-sync — 三端同步技能

将 skill 代码规范化推送到**码云（Gitee）**、**GitHub**，并生成 **ZIP 安装包**。

## 约束

- 一次同步一个技能。不支持批量推送多个技能（全量同步需通过 manifest.json 遍历）
- 需要网络连接。Gitee 和 GitHub 推送需要可用的网络连接
- 不支持 git merge。遇到冲突时不会自动合并，需要手动处理
- 仅同步到 workbuddy-skills 仓库。同步目标固定为 `~/.workbuddy/workbuddy-skills/`
- 参数约束。skill-name 只能是一个技能名（不含路径分隔符），version 格式为 x.y.z

## 触发条件

**正向触发：**
- 「同步/上传/推送/发布某个 skill」
- 「打包某个 skill」
- 「更新 README.md 的技能列表」
- 「检查某个 skill 的版本号」

**否定条件：**
- 用户只是说「帮我看看这个文件」——没有同步/打包意图
- 用户要求「用 git 提交代码」——这是通用 git 操作，不是 skill 同步
- 用户提到「同步」但指的是文件同步（如「同步到云端」）——不是 skill 仓库同步

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

- **三端同步** —— 码云、GitHub、本地 `.dist/` 目录
- **版本号三方对比** —— `_meta.json` / `SKILL.md` frontmatter / changelog
- **敏感信息过滤** —— 自动扫描并脱敏 `secrets/regex/telemetry`
- **SKILL.md 规范审查** —— 内联审计（版本一致性 + R-23 脚本引用检查）
- **ZIP 打包 + HTML 索引** —— 生成安装包 + 可视化索引页

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
|--------|------|----------|----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、变更类型、修复项、升级说明。 | R-24 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/guide.md` | 使用指南 | 三种执行模式操作教程。包含：audit/create/refactor 流程、参数说明、注意事项。 | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `references/reference.md` | 命令参考 | CLI 完整命令参考。包含：所有参数、子命令、选项、示例用法。 | 无 |
## 快速开始

**场景：推送单个技能到双平台**

**场景：仅打包不推送**
## 工作流程

?. **触发判断** → 输入 用户请求同步/推送/打包 skill → 输出 触发/不触发决策
?. **安全校验** → 输入 目标路径+skill名称 → 输出 校验通过/拒绝
?. **清单检查** → 输入 本地manifest.json版本 → 输出 升级/跳过/冲突
?. **文件同步** → 输入 源skill目录 → 输出 同步到workrepo/
?. **敏感信息脱敏** → 输入 文件列表 → 输出 脱敏后的副本
?. **更新README** → 输入 skills/目录 → 输出 README.md
?. **提交推送** → 输入 提交信息 → 输出 推送状态
?. **打包索引** → 输入 技能目录 → 输出 .zip+index.html
## 数据目录说明

本技能的数据文件存放在：
```text
skills/.standardization/git-sync/
├── data/
│   ├── config.json     # 平台配置（用户名、仓库名、分支等）
│   └── manifest.json   # 技能同步状态清单
└── backup/             # 改造/更新前的自动备份
```
安装目录 `skills/git-sync/` 只保留 SKILL.md 和 scripts/。

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为轻量入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。完整文件清单见「核心能力 → 渐进式文件索引」表格。

