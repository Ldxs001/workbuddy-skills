---
name: git-sync
description: 将skill代码规范化推送到码云、GitHub并生成ZIP包，自动更新README.md技能列表
agent_created: true
---

# git-sync - 三端同步技能

将 skill 代码规范化推送到**码云（Gitee）**、**GitHub**，并生成 **ZIP 安装包**。

## 核心功能

1. **自动同步文件** - 将 skill 完整目录结构同步到工作仓库
2. **自动更新 README** - 检测并添加新技能到 README.md 技能列表和目录结构
3. **双平台推送** - 同时推送到 Gitee 和 GitHub
4. **ZIP 打包** - 生成标准安装包

## 触发场景

用户说"上传"、"推送"、"同步"、"打包"相关指令时触发。

---

## Skill 标准文件结构

```
skill-name/
├── SKILL.md              ✅ 必需 - 技能说明文档
├── _meta.json            ✅ 必需 - 元数据
├── scripts/              ✅ Python脚本目录
│   ├── __init__.py
│   ├── cli.py
│   └── *.py
├── references/           ✅ 可选 - 参考文档
│   └── *.md
├── assets/              ✅ 可选 - 静态资源
│   └── *.json/png
├── data/                ✅ 可选 - 数据文件
│   └── *.json
└── default_config.json  ✅ 可选 - 默认配置
```

**必须排除**：

| 排除项 | 原因 |
|--------|------|
| `__pycache__/` | Python 缓存 |
| `*.pyc` | 编译文件 |
| `*.html` | 本地预览文件 |
| `*.log` | 日志文件 |

---

## 完整执行流程

### 1. 同步文件到工作仓库

```
本地: ~/.workbuddy/skills/<skill-name>/
     ↓ 同步（保持原结构）
仓库: ~/.workbuddy/workbuddy-skills/skills/<skill-name>/
```

**复制规则**：

| 目录/文件 | 处理 |
|-----------|------|
| `SKILL.md` | ✅ 必须复制 |
| `_meta.json` | ✅ 必须复制 |
| `scripts/*.py` | ✅ 复制 |
| `references/` | ✅ 复制（递归） |
| `assets/` | ✅ 复制（递归） |
| `data/` | ✅ 复制（递归） |
| `__pycache__/` | ❌ 不复制 |
| `*.pyc` | ❌ 不复制 |
| `*.html` | ❌ 不复制 |

### 2. 自动更新 README.md

**信息提取优先级**：

```
_meta.json → "description" > SKILL.md → description: > 默认值
```

**更新内容**：
- 技能列表表格末尾添加新技能
- 目录结构中，将最后一个 `└──` 改为 `├──`，然后追加 `└── 新技能/`

### 3. 提交并推送到双平台

```bash
git add → git commit → git pull --rebase → git push
```

### 4. 生成 ZIP 包

```
ZIP包结构（以skill-name为根目录）：
<skill-name>-v<version>.zip
├── SKILL.md
├── _meta.json
├── scripts/
│   └── *.py
├── references/
└── ...（与上传仓库结构一致）
```

---

## 使用方法

```bash
cd ~/.workbuddy/skills/git-sync/scripts
bash git-sync.sh <skill-name> [version]

# 示例
bash git-sync.sh color-toolkit 1.0.0
bash git-sync.sh workday-calendar 2.1.0
```

---

## 常见问题

### Q1: GitHub 推送失败（443 超时 / Permission denied）
→ 检查网络代理，或手动推送：
```bash
cd ~/.workbuddy/workbuddy-skills
git push origin main
```

### Q2: README 中出现重复条目
→ 是之前脚本 bug 造成的。用以下命令修复：
```bash
# 找到干净提交并强制重置
git log --oneline | head -20  # 找一个没有重复的提交
git reset --hard <干净commit>
git push <remote> --force
```

### Q3: 想保留历史 commit
→ 去掉 `git commit --amend`，用普通 commit

### Q4: 本地有 html 文件被混入
→ 先删除临时文件再执行同步：
```bash
rm -f ~/.workbuddy/skills/<skill-name>/*.html
```

---

## 代码管理铁律

1. ✅ 先检查仓库现有状态
2. ✅ 保持标准目录结构（SKILL.md + _meta.json 在根目录，py 文件在 scripts/）
3. ✅ 排除缓存/测试/临时文件
4. ✅ 自动更新 README 技能列表
5. ✅ ZIP 与仓库结构一致
6. ✅ 强制覆盖远程前先确认本地是正确的
