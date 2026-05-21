---
name: git-sync
version: 1.6.0
author: wUwproject
license: MIT
description: >
  将skill代码规范化推送到码云、GitHub并生成ZIP包，
  自动更新README.md技能列表，附带_meta.json标准化校验
  和三单一致维护清单机制。
  v1.6 更新：【按需同步】+ 【版本号三方对比】
    - 不在全量模式下，只同步用户指定的技能
    - 新增版本号对比：清单 vs 待更新，决定跳过/更新/报异常
    - manifest.py 新增 version 子命令（查询/更新条目版本号）
  v1.5 更新：【统一输出目录】+ 【HTML 索引页】
    - 所有 ZIP 统一输出到 ~/.workbuddy/skills/.dist/（方案A）
    - 自动生成 index.html 索引页（含 file:// 超链接）（方案C）
    - 打包后自动打开 dist/ 目录（Windows explorer / macOS open）
    - 修正三单一致原则描述（清单 ⊇ 仓库 = README.md）
  v1.4 更新：【安全加固】
    - SKILL_NAME 路径穿越校验（拒绝 ../、盘符等）
    - realpath 路径范围校验（目标必须在 WORK_REPO/skills/ 内）
    - rsync --delete 替代 rm -rf + cp（更安全）
  v1.3 更新：【三单一致清单机制】
    - 新增 manifest.json 维护清单，记录计划管理的技能全集
    - 新增 manifest.py CLI，支持 list/add/remove/check/diff/sync-readme
    - git-sync.sh 同步前检查清单，不在清单中时询问用户
    - update_readme.py 改为从仓库实际文件全量生成 README.md
    - 三单一致原则：清单 ⊆ 仓库 ⊆ README.md
  v1.2 更新：【_meta.json 标准化】+ 【update_readme 独立化】
    - 新增 normalize_meta.py，标准化 _meta.json 为 5 字段
    - update_readme.py 改为独立 Python 脚本，修复 idempotency bug
  v1.1 更新：【ZIP 打包】+ 【双平台推送】
  核心逻辑 = Bash + Python，不依赖任何 Agent 平台。
  触发关键词：同步、上传、推送、打包、sync、git-sync。
tags: [sync, git, zip, skill-manager, manifest]
---

# git-sync - 三端同步技能

将 skill 代码规范化推送到**码云（Gitee）**、**GitHub**，并生成 **ZIP 安装包**。

## 核心功能

1. **按需同步** - 用户指定哪个就同步哪个；只有明确说"全量维护"才遍历所有技能
2. **版本号三方对比（v1.6 新增）** - 清单版本 vs 待更新版本，决定跳过/更新/报异常
3. **自动同步文件** - 将 skill 完整目录结构同步到工作仓库
4. **维护清单机制（v1.3 新增）** - 三单一致，防止 README 与仓库不一致
5. **自动更新 README** - 从仓库实际文件全量生成
6. **双平台推送** - 同时推送到 Gitee 和 GitHub
7. **ZIP 打包** - 生成标准安装包，统一输出到 `.dist/` 并生成 HTML 索引

## 触发场景

- **按需同步（默认）**：用户说"同步/上传/推送/打包 X"（指定名称）→ 只同步 X，不遍历维护清单或仓库目录
- **全量维护**：用户明确说"全量维护"/"同步所有"/"全部上传" → 遍历维护清单（`manifest.json`）中所有 `uploaded=true` 的条目
- 未明确"全量"时，默认按需同步，不自动遍历

---

## Skill 标准文件结构

```
<skill-name>/
├── SKILL.md              ✅ 必需 - 技能说明文档
├── _meta.json            ✅ 必需 - 元数据
├── scripts/              ✅ Python脚本目录
│   ├── __init__.py
│   └── *.py
├── references/           ✅ 可选 - 参考文档
├── assets/              ✅ 可选 - 静态资源
└── data/                ✅ 可选 - 数据文件
```

**必须排除**：

| 排除项 | 原因 |
|--------|------|
| `__pycache__/` | Python 缓存 |
| `*.pyc` | 编译文件 |
| `*.html` | 本地预览文件 |
| `*.log` | 日志文件 |

---

## 路径说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SKILLS_DIR` | `~/.workbuddy/skills` | 技能源目录 |
| `WORK_REPO` | `~/.workbuddy/workbuddy-skills` | Git工作仓库 |
| `MANIFEST_FILE` | `scripts/manifest.json` | 维护清单文件 |
| `DIST_DIR` | `SKILLS_DIR/.dist/` | ZIP 统一输出目录（v1.5新增） |

---

## 完整执行流程

### 0.3 安全校验

- SKILL_NAME 路径穿越检查（拒绝 `../`、`..\\`、`/`、`C:` 开头）
- 目标路径 realpath 范围校验（必须在 `WORK_REPO/skills/` 内）

### 0.5 维护清单检查（v1.3 新增）

同步前自动检查维护清单（`manifest.json`），决定行为：

| 检查结果 | 行为 |
|---------|------|
| `FOUND:uploaded`（在清单中且已上传） | ✅ 继续执行 |
| `FOUND:not-uploaded`（在清单中但未上传） | ⏳ 继续执行，完成后标记 `uploaded=true` |
| `NOT_FOUND`（不在清单中） | ❓ 询问用户：加入清单 / 仅本次同步 / 中止 |

### 0.7 版本号三方对比（v1.6 新增）

读取维护清单中的 `version` 字段，与待更新版本对比：

| 对比结果 | 行为 |
|---------|------|
| 清单无此条目 | ✅ 正常执行，执行完后写入 version 到清单 |
| 清单 version = 待更新 version | ❓ 询问用户是否跳过（默认跳过） |
| 清单 version < 待更新 version | ✅ 正常升级，执行完后更新清单 version |
| 清单 version > 待更新 version | ❌ 版本异常，询问处理策略（覆盖/拉取/合并/中止） |

> **注**：仓库实际文件中的 `_meta.json` version 仅作参考，以清单记录的 version 为准。

### 0. _meta.json 标准化校验

同步前自动校验并修正 `_meta.json`，确保符合标准 5 字段结构：

| 标准字段 | 说明 | 缺失时处理 |
|---------|------|-----------|
| `name` | 技能标识名 | 使用目录名 |
| `version` | 版本号 | 使用传入的 version 参数 |
| `description` | 技能描述 | 从 SKILL.md 提取 |
| `author` | 作者 | **强制设为 `wUwproject`** |
| `tags` | 标签列表 | 设为空数组 `[]` |

**自动删除的非标准字段**：`slug`、`ownerId`、`publishedAt`、`display_name`、`platforms`

### 1. 同步文件到工作仓库

将技能从 `SKILLS_DIR/<skill-name>/` 同步到 `WORK_REPO/skills/<skill-name>/`

### 2. 全量重新生成 README.md

**从仓库 `skills/` 实际目录扫描**，全量替换 README.md 中的技能列表表格和目录结构。

> **关键原则**：README.md = 仓库实际内容，不手动维护，从根本上杜绝不一致。

### 3. 提交并推送到双平台

```bash
git add → git commit → git pull --rebase → git push
```

### 4. 生成 ZIP 包

```
输出路径: SKILLS_DIR/.dist/<skill-name>-v<x.x.x>.zip
（v1.5 起统一输出到 DIST_DIR=~/.workbuddy/skills/.dist/）
```

### 5. 统一输出 + HTML 索引（v1.5 新增）

打包完成后自动执行：

1. **复制到统一目录** `~/.workbuddy/skills/.dist/`（方案A）
2. **生成 `index.html` 索引页**（方案C）
   - 列出所有 ZIP 包，含 `file://` 超链接
   - 显示文件大小和修改时间
   - 点击文件名可直接跳转/下载（浏览器需允许 file:// 协议）
3. **自动打开 dist/ 目录**
   - Windows: `explorer.exe`
   - macOS: `open`
   - Linux: `xdg-open`

---

## 维护清单管理（manifest.py）

`manifest.py` 是独立 CLI，不污染 git-sync 主逻辑。

### 子命令

```bash
# 列出清单
python manifest.py list workbuddy-skills

# 加入清单（默认 uploaded=false）
python manifest.py add workbuddy-skills my-skill --type skill --uploaded

# 从清单移除
python manifest.py remove workbuddy-skills my-skill

# 检查是否在清单内（供 git-sync.sh 调用）
python manifest.py check workbuddy-skills my-skill
# 输出：FOUND:uploaded / FOUND:not-uploaded / NOT_FOUND

# 查询/更新条目版本号（v1.6 新增）
python manifest.py version workbuddy-skills my-skill          # 查询
python manifest.py version workbuddy-skills my-skill 1.2.0  # 更新

# 对比清单(uploaded=true) vs 仓库实际文件
python manifest.py diff workbuddy-skills

# 根据仓库实际文件全量重新生成 README.md
python manifest.py sync-readme workbuddy-skills
```

### 三单一致模型

```
维护清单 (manifest.json)
    └─ 可以包含 "只登记、未上传" 的条目（uploaded:false）

执行端（仓库实际文件）
    └─ 清单中 uploaded=true 的子集

清单端（README.md）
    └─ 由 sync-readme 全量生成，永远 = 仓库实际内容
```

**不会出现 README 里有但仓库里没有的情况。**

---

## 使用方法

```bash
cd <git-sync>/scripts
bash git-sync.sh <skill-name> [version]

# 示例
bash git-sync.sh color-toolkit 1.0.0
bash git-sync.sh workday-calendar 2.1.0
```

**参数说明**：
- `skill-name`: 技能目录名（必填）
- `version`: 版本号（默认 1.0.0）

---

## 常见问题

### Q1: GitHub 推送失败（443 超时 / Permission denied）
→ 检查网络代理，或手动推送：
```bash
cd WORK_REPO
git push origin main
```

### Q2: 想保留历史 commit
→ 脚本已改为普通 commit，不再 amend

### Q3: 本地有 html 文件被混入
→ 先删除临时文件再执行同步：
```bash
rm -f SKILLS_DIR/<skill-name>/*.html
```

---

## 代码管理铁律

1. ✅ 先检查仓库现有状态
2. ✅ 保持标准目录结构（SKILL.md + _meta.json 在根目录）
3. ✅ 排除缓存/测试/临时文件
4. ✅ 自动更新 README 技能列表（全量生成）
5. ✅ ZIP 与仓库结构一致
6. ✅ 强制覆盖远程前先确认本地是正确的
7. ✅ **维护清单优先** — 未确认是否加入清单前，不盲目同步
