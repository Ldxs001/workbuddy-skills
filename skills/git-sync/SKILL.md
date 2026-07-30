---
name: git-sync
slug: git-sync
displayName: git-sync
version: 2.34.0
author: wUwproject
license: MIT
description: 全平台统一发布工具。支持 skills 和 agents 的 Gitee/GitHub/ClawHub/SkillHub/PyPI 同步与 Release 创建，LLM 驱动的文件过滤与脱敏。
sensitive_access: true
critical_write: false
permission_weight: CRITICAL
data_dir: ../.standardization/git-sync/data
tags: ['sync', 'git', 'gitee', 'github', 'deploy']
external_data_dir: true
trigger: 同步/推送/发布/上传/打包/更新 READ ME
trigger_negative: 只是看文件/通用 git 提交/文件同步到云端
h1_version: true
meta_field_sync: true
create_permissions_md: true
h1_position: true
data_dir_compliance: true
---
# git-sync — 全平台发布工具

将 skill/agent 代码规范化推送到**码云（Gitee）**、**GitHub**，并支持 **ClawHub**、**SkillHub**、**PyPI** 发布与 **Release 创建**。

## 约束

- **仅前台运行** — git-sync 包含 LLM 交互步骤（文件筛除、敏感脱敏），WorkBuddy 必须在前台会话中读取输出并写入决策文件。**禁止在后台/Bash 任务中运行**，否则 LLM 交互输出被吞会导致死锁
- **自动检测类型** — 自动识别 skill（`_meta.json`）或 agent（`rag_assistant/__init__.py`），分别走不同发布流程
- **`all` 模式** — `git-sync all` 遍历 `skills/` 和 `agent/` 全部项目
- **网络依赖** — 推送 Gitee/GitHub/ClawHub/SkillHub/PyPI 需要可用网络连接，超时阈值 60 秒
- **冲突不自动合并** — git merge 冲突需人工介入
- **固定仓库** — 同步目标固定为 `~/.workbuddy/workbuddy-skills/`
- **参数约束** — 项目名不含路径分隔符，version 格式严格 x.y.z
- **仓库规模** — 支持 1-50 个项目，每个 ≤ 500MB
- **数据持久性** — manifest.json 记录同步状态，不备份远程仓库数据

## 触发条件

**正向触发：**
- 「同步/上传/推送/发布某个 skill 或 agent」
- 「全量同步/全部发布」
- 「发布到 ClawHub/SkillHub/PyPI」
- 「创建 Release」
- 「打包/更新 README.md」
- 「检查版本号」

**否定条件：**
- 用户只是说「帮我看看这个文件」——没有同步/打包意图
- 用户要求「用 git 提交代码」——这是通用 git 操作，不是本技能

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

- **全平台发布** —— Gitee + GitHub + ClawHub + SkillHub + PyPI，一次同步全自动
- **类型自动识别** —— skill（`_meta.json`）/ agent（`__init__.py`），版本号各自读取
- **路径由 manifest 统一管理** —— 每个条目记录 `source_path`（源路径）+ `repo_path`（仓库内路径），skill 和 agent 统一走同一套逻辑
- **`all` 批量模式** —— 遍历全部 skills 和 agents 逐个同步
- **LLM 文件过滤** —— 同步前扫描源文件 → 全量打印文件列表 + 规则 → 要求 WorkBuddy 输出决策 JSON → 只复制允许的文件
- **LLM 脱敏（强制）** —— 同步后强制脱敏敏感信息（邮箱/token/路径/本地路径），无跳过选项。WorkBuddy 根据扫描发现 + 脱敏引导规则逐文件判断保留或脱敏
- **版本号三方对比** —— `_meta.json` / `SKILL.md` frontmatter / changelog
- **SKILL.md 规范审查** —— 内联审计（版本一致性 + R-23 脚本引用检查）
- **ZIP 打包 + HTML 索引** —— 生成安装包 + 可视化索引页
- **PyPI 隔离构建** —— 拷贝源码到临时目录 → 生成 setup.py → build → twine 上传，版本号自动归一化 PEP 440，dev_status 自动判别
- **Release 创建** —— git tag + GitHub/Gitee API Release（技能用 `{name}-v{ver}`，智能体用 `v{ver}`），源码包由平台自动生成

### 平台发布差异

| 平台 | 版本读取源 | 命令/工具 | 注意事项 |
|------|-----------|-----------|---------|
| Gitee | `_meta.json` (skill) / `__init__.py` (agent) | `git push` | SSH/HTTPS 凭证自动解析，支持 pull --rebase 重试 |
| GitHub | 同上 | `git push` | 同 Gitee，443 超时常见，会 retry |
| ClawHub | `_meta.json` 的 slug/version/tags | `npx clawhub publish` | API 成功时 CLI 可能误报 `invalid value`（已知 bug），检查 `ok` 关键字即可 |
| SkillHub | **必须传 `--version`**（单独读取 SKILL.md frontmatter 不可靠） | `skills_store_cli.py publish` | 不加 `--version` 可能读到旧版本导致发布失败 |
| PyPI | `__init__.py` 的 `__version__` | 隔离构建 → `twine upload --disable-progress` | Windows 上 twine 的 Rich 进度条有 GBK 编码 bug，必须加 `--disable-progress` |
| Release | 同步后当前版本 | `git tag` + GitHub API | tag 格式: skill=`{name}-v{ver}`, agent=`v{ver}`

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
| -------- |------| ---------- |----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、更新类型、修复项、升级说明。 | R-24 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/guide.md` | 使用指南 | 三种执行模式操作教程。包含：audit/create/refactor 流程、参数说明、注意事项。 | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `references/reference.md` | 命令参考 | CLI 完整命令参考。包含：所有参数、子命令、选项、示例用法。 | 无 |
| `references/blueprint_rules.md` | 判断规则 | 蓝图排除/脱敏判断规则。包含：筛除原则、脱敏原则、判定流程。 | 无 |

| 能力 | 说明 | 限制 |
|------|------|------|
| **全平台同步** | 将 skill/agent 同步到码云、GitHub、ClawHub、SkillHub、PyPI | 按 skill/agent 逐个同步，支持 `all` 批量模式 |
| **版本号三方对比** | 自动对比 _meta.json / SKILL.md frontmatter / changelog 的版本一致性 | 仅检测 x.y.z 格式版本号，不处理其他格式 |
| **敏感信息过滤** | 自动扫描并脱敏 secrets/regex/telemetry | 扫描范围限于 skill 目录，不扫描系统目录 |
| **SKILL.md 规范审查** | 内联审计版本一致性 + R-23 脚本引用检查 | 仅做静态文本分析，不验证运行时行为 |
| **ZIP 打包 + HTML 索引** | 生成安装包 + 可视化索引页 | 打包前需先同步到 workrepo |

**不支持：**
- 通用 git 提交：本技能专注于 skill/agent 仓库同步，通用 git 操作由用户手动完成
- merge 冲突解决：遇到 git merge 冲突时不会自动合并，需要用户手动处理

## 快速开始

**场景：推送技能到双平台**
用户需求：skill-name=novel-weaver, 当前版本=1.18.2, 目标版本=1.19.0
系统执行：
```bash
bash ~/.workbuddy/skills/git-sync/scripts/git-sync.sh novel-weaver
```
系统输出：[1/8] 触发判断 → 继续
[2/8] 安全校验 → 通过
[3/8] 清单检查 → 升级至 1.19.0
[4/8] 文件同步 → 已复制 47 个文件
[5/8] 敏感信息脱敏 → 2 处已替换
[6/8] 更新 README → 新增 1 条
[7/8] 提交推送 → Gitee ✅ / GitHub ✅
[8/8] 打包索引 → .zip 已生成
最终输出: 码云 ✅ / GitHub ✅ → 版本 1.19.0 已同步

**场景：仅打包不推送**
用户需求：skill-name=git-sync, 当前版本=2.23.0, --pack-only 标志
系统执行：
```bash
bash ~/.workbuddy/skills/git-sync/scripts/git-sync.sh git-sync --pack-only
```
系统输出：[1/8] 触发判断 → 继续（--pack-only 跳过推送）
[4/8] 文件同步 → 已复制 22 个文件
[8/8] 打包索引 → .dist/git-sync-v2.23.0.zip 已生成（45.2 KB，22 文件）
最终输出: .dist/git-sync-v2.23.0.zip 已生成

**场景：仅推送不打包**
用户需求：skill-name=workday-calendar, 当前版本=2.2.0, 目标版本=2.2.1, --push-only 标志
系统执行：
```bash
bash ~/.workbuddy/skills/git-sync/scripts/git-sync.sh workday-calendar --push-only
```
系统输出：[1/8] 触发判断 → 继续
[2/8] 安全校验 → 通过
[3/8] 清单检查 → 升级至 2.2.1
[4/8] 文件同步 → 已复制 31 个文件
[5/8] 敏感信息脱敏 → 0 处
[6/8] 更新 README → 无变化
[7/8] 提交推送 → 码云 ✅ / GitHub ✅
[8/8] 打包索引 → 跳过（--push-only）
最终输出: 码云 ✅ / GitHub ✅ → 版本 2.2.1 已同步

## 工作流程

1. **触发判断** → 输入 用户请求文本 → 输出 触发决策（继续/拒绝） — 解析用户请求，判断是否为同步/推送/打包意图
2. **安全校验** → 输入 目标路径 + skill 名称 → 输出 校验通过/拒绝 — 检查目标路径合法性、skill 名称白名单
3. **清单检查 + 路径解析** → 输入 manifest.json → 输出 同步状态 — 读取 manifest 条目获取 source_path/repo_path，无则按 type 走默认路径
4. **版本号对比** → 输入 仓库版本 v.s. 本地源文件 → 输出 升级/跳过/冲突 — 读取 `_meta.json`（skill）或 `__init__.py`（agent），版本号自动归一化 PEP 440
5. **LLM 文件过滤** → 输入 源目录 → 输出 允许文件列表 — 扫描源目录 → **全量打印文件列表到 stdout** → WorkBuddy 在回复中输出决策 JSON → 只复制允许的文件到 workrepo
6. **敏感信息脱敏（强制）** → 输入 工作仓库文件 → 输出 脱敏后的副本 — 扫描邮箱/token/IP 并强制替换。全自动 LLM 决策，无跳过选项
7. **更新 README** → 输入 workrepo → 输出 更新后的 README.md — 全量扫描 workrepo/skills/ + agent/，重新生成 README.md（skills 表格 + 智能体表格）
8. **提交推送** → 输入 提交信息 → 输出 推送状态 — git add/commit/push 到码云 + GitHub
9. **ZIP 打包** → 输入 技能目录 → 输出 .zip 文件 + index.html — 将 skill 目录打包为 .zip（仅 skill，agent 跳过）
10. **市场发布**（可选）→ ClawHub / SkillHub（skill）/ PyPI（agent + `--pypi`）
11. **创建 Release**（`--release` 标志）→ 打 tag + 推双平台 + 创建 GitHub Release + Gitee 发行版，源码包由平台自动生成

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

