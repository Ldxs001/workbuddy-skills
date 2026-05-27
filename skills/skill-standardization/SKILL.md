---
name: skill-standardization
author: wUwproject
license: MIT
description: Skill 标准化规范引擎 v2.38.0。审计输出含 filepath:line#；fix.py 统一修复工具；git-sync 后根目录 .py 清理。
sensitive_access: true
critical_write: false
permission_weight: HIGH
data_dir: ../.standardization/skill-standardization/
external_data_dir: true
writing_standards: fix_terms
artifact_paths: true
version: 
---











# skill-standardization v2.38.0

## 文件更新约束

> **本技能的所有 `.md` 文件禁止使用 Write/Edit 工具更新（会损坏 UTF-8 中文编码）。**
> 必须用 `scripts/` 下的 Python 脚本原子写入（`tmp + os.replace()`）。

| 文件 | 更新方式 | 脚本 |
|------|----------|------|
| `SKILL.md` frontmatter | Python 原子写入 | `scripts/update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 直接重建 | `scripts/safe_io.py` 的 `safe_write()` |
| `references/*.md` | `scripts/safe_io.py` 的 `safe_write()` | 随技能自带 |
| 更新日志 | Python 合并脚本 | 每次发版统一维护 `references/changelog.md` |

**检查清单（每次更新前）**：
- [ ] 是否用了 Write/Edit 工具？→ 立刻停止，改用 Python 脚本
- [ ] 是否在 `references/changelog.md` 维护更新记录？→ 根目录不得有 `CHANGELOG.md`
- [ ] 更新后是否用 `python -m scripts.skill_audit audit .` 自审？→ 必须 0 ERROR 0 WARN

> **注**：本技能的权限检查器（`permission_checker.py`）定义的敏感路径匹配模式（如 `~/.ssh/`、`~/.aws/` 等）仅用作**检测规则**，用于发现被审计 skill 是否违规访问这些路径；本技能本身不会实际访问这些敏感路径。

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

- **audit 模式** — 对指定 skill 目录执行 R-01~R-24 规范审查，输出通过/失败/跳过统计
- **refactor 模式** — 改造现有技能（修复 frontmatter、迁移更新记录、统一术语、规范数据目录、R-22 数据目录合规检查）
- **create 模式** — 基于标准化模板创建新 skill，自动注入 R-07~R-09/R-18~R-22 章节引用

## 工作流程

1. 读取目标 skill 的 SKILL.md
2. 执行 R-01~R-24 规则检查
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

## 临时文件与备份管理

> 本技能在创建、更新、改造过程中，对临时文件和备份文件进行全生命周期管理。

### 管理规则

1. **操作前整体备份**：对目标技能目录执行整体备份（时间戳命名），记录在案，确保可回滚。
2. **操作中记录**：所有临时文件（`temp/`、`*.tmp`、脚本中间产物）和备份文件（`backup/`、`_bak_*` 目录）的产生路径、时间、操作类型均记录到 `op_logger` 日志。
3. **操作后清理**：主体创建/更新/改造完成（审计通过 + 版本号更新 + 更新日志维护完毕）后，按规范清除临时文件和过期备份。
4. **py 工具兜底能力**：`scripts/safe_io.py` 所有写操作（`safe_write`、`safe_patch_by_line`、`safe_patch_regex`、`safe_insert_after`）均内置 `backup_file()` 临时备份，返回 `rollback_id`，确保删/改动作可回滚。

### 清理规范

| 文件类型 | 路径模式 | 保留时长 | 清理时机 |
|-----------|-----------|----------|------------|
| 临时文件 | `data/temp/*`、`*.tmp`、`draft_*` | 会话级（0天） | 每次操作完成后立即清除 |
| 操作备份 | `data/backup/*` | 最近 10 个 | 每次操作完成后保留最新 10 个，其余清除 |
| 整体备份 | `<skill-dir>_bak_*<timestamp>` | 操作完成确认后 | 操作完成并确认无异常后，提示用户是否清除 |
| 日志文件 | `data/logs/ops.log` | 最近 200 条 | 超过 200 条时截断，保留最新 |

### 记录格式

每条临时/备份文件记录在 `op_logger` 日志中增加 `temp_files` 字段：

```json
{
  ts: 2026-05-27T08:31:47,
  operation: refactor,
  file: skills/.standardization/skill-standardization/,
  success: true,
  rollback_id: 20260527_083147_...,
  temp_files: [skills/.standardization/skill-standardization/data/temp/xxx.tmp],
  backup_files: [skills/.standardization/skill-standardization/data/backup/20260527_...bak],
  detail: ...
}
```

> 本技能自身被更新时，同样遵守上述规则：更新前对 `skills/.standardization/skill-standardization/` 整体备份，操作中记录临时文件，更新完成后清理。

## 数据目录说明

本技能的数据文件（审查缓存、进度文件、备份、日志等）存放在：

```
skills/.standardization/skill-standardization/
```

> 安装目录 `skills/.standardization/skill-standardization/` 只保留 SKILL.md 和 scripts/，数据文件不越位。
