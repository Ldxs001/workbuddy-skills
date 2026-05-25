---
name: git-sync
version: 2.6.11
author: 由 config.json 的 author 字段决定
license: MIT
description: >
tags: ['sync', 'git', 'zip', 'skill-manager', 'manifest', 'security']
sensitive_access: false
critical_write: false
permission_weight: LOW
authorization: false
trigger_negative: true
section_antipattern: true
writing_standards: fix_terms
progressive_loading_explicit: true
antipattern_count: add_examples
---

# git-sync v2.6.6 — 三端同步技能

将 skill 代码规范化推送到**码云（Gitee）**、**GitHub**，并生成 **ZIP 安装包**。

## 触发场景

当用户提到「同步、上传、推送、打包」某个 skill 时触发。

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| **按需同步**（默认） | 用户指定 skill 名称 | 只同步指定的 skill |
| **全量维护** | 明确说"全量维护"/"同步所有" | 遍历 manifest.json 所有条目 |

> 触发关键词：同步、上传、推送、打包、sync、git-sync
>
> **否定条件**：以下情况不触发本技能——（1）用户只是询问同步流程而不要求执行；（2）用户明确说"不要同步"/"跳过同步"；（3）用户要求使用其他同步方式（如手动 git 命令）。

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 功能 | 说明 |
|---|------|------|
| 1 | **按需同步** | 用户指定哪个就同步哪个；只有明确说"全量维护"才遍历所有技能 |
| 2 | **版本号三方对比**（v1.6） | 清单版本 vs 待更新版本，决定跳过/更新/报异常 |
| 3 | **敏感信息过滤**（v1.7） | 扫描并脱敏用户名/邮箱/Token/路径等敏感信息 |
| 4 | **SKILL.md 规范审查**（v1.8） | 同步前自动检查 R-01~R-10 合规性（纯警告不阻断） |
| 5 | **三单一致机制**（v1.3） | manifest.json ≥ 仓库实际文件 = README.md |
| 6 | **ZIP 打包 + HTML 索引**（v1.5） | 统一输出到 `.dist/` 并自动生成 index.html |
| 7 | **安全修复**（v2.6.0） | 删除 `__import__` 动态导入，改善授权检查实现（内置异常处理） |
| 8 | **空文件排除**（v2.6.5） | ZIP 打包和同步时自动排除 0 KB 空文件（如 .gitkeep） |

## 工作流程

### AI 执行节奏

```
用户请求同步 → 加载本 SKILL.md
  ↓
确定同步模式
  ├── 按需同步（指定 skill 名）──→ 单 skill 流水线
  └── 全量维护（明确说"全量"/"同步所有"）──→ 遍历 manifest.json
  ↓
执行同步流水线：
  安全校验 → 清单检查 → 版本对比 → 敏感扫描 → 规范审查 → 同步推送 → ZIP 打包 → README 更新
  ↓
输出结果报告（✅/❌/⚠️）
```

### 步骤概览

| 步骤 | 名称 | 说明 |
|------|------|------|
| 0 | 安全校验 | 路径穿越防护、目标范围检查 |
| 0.5 | 清单检查 | manifest.json 状态验证 |
| 0.7 | 版本对比 | 清单版本 vs 待更新版本 |
| 1 | 敏感扫描 | Token/邮箱/路径检测与脱敏 |
| 2 | 规范审查 | R-01~R-12 audit（纯警告） |
| 3 | 同步推送 | Git 双端推送（Gitee + GitHub） |
| 4 | ZIP 打包 | 生成 `.dist/` 包 + index.html（自动排除空文件） |
| 5 | README 更新 | 全量重建技能列表 |
| 6 | 清单维护 | 更新 manifest.json 状态标记 |
| 7 | **安全修复**（v2.6.0） | 删除 `__import__` 动态导入，改善授权检查 |

→ 完整步骤详解见 `references/guide.md`

## 反模式

> 常见错误和注意事项，避免误用本技能。

### 1. 盲目全量同步

**错误做法**：用户只是提了一下某个 skill，就自动触发全量同步。

**正确做法**：除非用户明确说"全量维护"/"同步所有"，否则只同步指定的 skill。

### 2. 忽略敏感信息扫描

**错误做法**：跳过敏感信息扫描，直接同步推送。

**正确做法**：同步前必须运行敏感信息扫描，防止 Token/邮箱/路径泄露。

### 3. 滥用 `--skip-scan`

**错误做法**：对私有仓库直接使用 `--skip-scan` 跳过扫描，不考虑后续分享风险。

**正确做法**：私有内容经常被后续镜像、打包分享、或推送到其他 remote。`--skip-scan` 仅限完全确认无敏感信息时使用。

→ 详见 `references/antipatterns.md`

## 快速开始

> 详细命令和参数说明见 `references/guide.md`（按需加载）

**核心命令：**

```bash
bash git-sync.sh <skill-name> <version>
```

- `<skill-name>`：技能目录名（如 `color-toolkit`）
- `<version>`：版本号（如 `1.0.0`）
- 可选：`--skip-scan` 跳过敏感信息扫描（⚠️ 仅限确认无敏感信息时）

## 安装后配置

编辑 `config.json` 替换占位值：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `author` | _meta.json 默认作者名 | `your-name-here` |
| `gitee.user` / `github.user` | 用于生成查看链接和 README 命令 | `your-gitee-username` |

→ 详见 `references/guide.md` 完整执行流程（步骤 0 → 6 详解）

## 修复记录

### v2.6.5 (2026-05-25)

**打包优化**：

1. **排除空文件（0 KB）** — `pack_zip.py` 和 `sync_with_exclude.py` 新增空文件排除逻辑，自动跳过 `.gitkeep` 等占位文件
2. **增加 `--skip-scan` 安全警告** — FAQ Q11 增加安全提示：私有内容经常被镜像/分享，跳过扫描会增加敏感信息泄露风险

**影响文件**：
- `scripts/pack_zip.py` — 新增空文件排除 + `.gitkeep` 精确排除
- `scripts/sync_with_exclude.py` — 新增空文件排除 + `.gitkeep` 精确排除
- `references/faq.md` — Q11 增加安全警告

### v2.6.0 (2026-05-24)

**安全修复**：

1. **删除 `__import__` 动态导入** — 将 `sync_with_exclude.py` 中的 `__import__("subprocess")` 改为标准 `import subprocess`
2. **改善授权检查实现** — 将授权检查逻辑改为内置异常处理，避免外部脚本依赖不可控
3. **路径安全检查** — 在 `sync_with_exclude.py` 中添加源/目标路径一致性检查，防止误删目录

**影响文件**：
- `scripts/sync_with_exclude.py` — 修复 `__import__` + 添加路径安全检查
- `scripts/sensitive_scan.py` — 验证无 `__import__` 动态导入

---

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
7. ✅ **ZIP 自动排除空文件（0 KB）** — 防止 `.gitkeep` 等占位文件被打入包

→ [FAQ](references/faq.md) · [版本日志](references/changelog.md) · [完整参考](references/reference.md)

---

## 渐进式加载引用表

> 本表声明渐进式加载结构：SKILL.md 主文件含核心触发 + 引用表，详细内容拆分至 references/ 按需加载。

| 本文件（SKILL.md）包含 | 拆分到 references/ |
|----------------------------|---------------------------|
| ✅ 触发场景、核心能力、快速开始、工作流程（渐进式加载） | 📄 `references/guide.md` — 步骤详解 + 敏感信息过滤规则 |
| ✅ 版本记录 | 📄 `references/changelog.md` — 版本更新历史 |
| ✅ 权限说明 | 📄 `references/permissions.md` — 权限类型、风险等级、行为对照表 |
| ✅ 详细参考 | 📄 `references/reference.md` — API/命令参考 |
| ✅ 常见问题 | 📄 `references/faq.md` — FAQ |

→ 详见 `references/guide.md`（按需加载）

---

## 版本

当前版本：**2.6.5** — v2.6.5：打包排除空文件（0 KB）+ .gitkeep；增加--skip-scan安全警告

→ [更新日志](references/changelog.md) · [完整参考](references/reference.md)
