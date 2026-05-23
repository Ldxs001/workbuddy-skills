---
name: git-sync
version: 2.0.1
author: 由 config.json 的 author 字段决定
license: MIT
description: >
  将 skill 代码规范化推送到码云、GitHub 并生成 ZIP 包，
  自动更新 README.md 技能列表，附带 _meta.json 标准化校验、
  三单一致维护清单机制、敏感信息过滤和 SKILL.md 规范化审查。
tags: [sync, git, zip, skill-manager, manifest, security]
---

# git-sync — 三端同步技能

将 skill 代码规范化推送到**码云（Gitee）**、**GitHub**，并生成 **ZIP 安装包**。

## 触发场景

当用户提到「同步、上传、推送、打包」某个 skill 时触发。

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| **按需同步**（默认） | 用户指定 skill 名称 | 只同步指定的 skill |
| **全量维护** | 明确说"全量维护"/"同步所有" | 遍历 manifest.json 所有条目 |

> 触发关键词：同步、上传、推送、打包、sync、git-sync

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | **按需同步** | 用户指定哪个就同步哪个；只有明确说"全量维护"才遍历所有技能 |
| 2 | **版本号三方对比**（v1.6） | 清单版本 vs 待更新版本，决定跳过/更新/报异常 |
| 3 | **敏感信息过滤**（v1.7） | 扫描并脱敏用户名/邮箱/Token/路径等敏感信息 |
| 4 | **SKILL.md 规范审查**（v1.8） | 同步前自动检查 R-01~R-10 合规性（纯警告不阻断） |
| 5 | **三单一致机制**（v1.3） | manifest.json ≥ 仓库实际文件 = README.md |
| 6 | **ZIP 打包 + HTML 索引**（v1.5） | 统一输出到 `.dist/` 并自动生成 index.html |

## 快速开始

```bash
# 进入脚本目录
cd ~/.workbuddy/skills/git-sync/scripts

# 同步指定 skill（自动 bump 版本号）
bash git-sync.sh <skill-name> <version>

# 示例：同步 color-toolkit v1.0.0
bash git-sync.sh color-toolkit 1.0.0

# 跳过敏感信息扫描（私有仓库用）
bash git-sync.sh my-skill 1.0.0 --skip-scan
```

## 安装后配置

编辑 `config.json` 替换占位值：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `author` | _meta.json 默认作者名 | `your-name-here` |
| `gitee.user` / `github.user` | 用于生成查看链接和 README 命令 | `your-gitee-username` |

→ 详见 `references/guide.md` 完整执行流程（步骤 0 → 6 详解）

## 敏感信息过滤

同步前自动扫描并按**文件粒度交互确认**：

| 类型 | 示例 | 严重度 |
|------|------|--------|
| 邮箱地址 | `xxx@xxx.com` | 🔴 critical |
| Token / API Key | `token=xxx` | 🔴 critical |
| 本地路径 | `C:\Users\...` | 🟡 medium |

三种模式：`prompt`（默认交互）/ `always-sanitize`（自动脱敏）/ `keep-as-is`（跳过）

→ 详见 `references/reference.md` 完整检测规则 + manifest.py CLI 速查

## 代码管理铁律

1. ✅ 先检查仓库现有状态
2. ✅ 保持标准目录结构（SKILL.md + _meta.json 在根目录）
3. ✅ 排除缓存/测试/临时文件
4. ✅ 自动更新 README 技能列表（全量生成）
5. ✅ 维护清单优先 — 未确认是否加入清单前，不盲目同步
6. ✅ ZIP 与仓库结构一致

→ [FAQ](references/faq.md) · [版本日志](references/changelog.md) · [完整参考](references/reference.md)
