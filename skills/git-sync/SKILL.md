---
name: git-sync
description: 将skill代码规范化推送到码云、GitHub并生成ZIP包，自动更新README.md技能列表
agent_created: true
---

# git-sync - 三端同步技能

将skill代码规范化推送到**码云（Gitee）**、**GitHub**，并生成**ZIP安装包**。

## 核心功能

1. **自动同步文件** - 将skill完整目录结构同步到工作仓库
2. **自动更新README** - 检测并添加新技能到README.md技能列表和目录结构
3. **双平台推送** - 同时推送到Gitee和GitHub
4. **ZIP打包** - 生成标准安装包

## 触发场景

用户说"上传"、"推送"、"同步"、"打包"相关指令时触发。

---

## Skill标准文件结构

```
skill-name/
├── SKILL.md              ✅ 必需 - 技能说明文档
├── _meta.json            ✅ 必需 - 元数据
├── scripts/              ✅ 推荐 - Python脚本目录
│   ├── __init__.py       ✅ 模块入口
│   ├── cli.py            ✅ 命令行入口
│   └── *.py              ✅ 其他模块
├── references/           ✅ 可选 - 参考文档
│   └── *.md
├── assets/               ✅ 可选 - 静态资源
│   └── *.json/png/html
├── data/                 ✅ 可选 - 数据文件
│   └── *.json
└── default_config.json   ✅ 可选 - 默认配置
```

**必须排除**：
| 排除项 | 原因 |
|--------|------|
| `__pycache__/` | Python缓存 |
| `*.pyc` | 编译文件 |
| `*.html` | 本地预览文件 |
| `*.log` | 日志文件 |
| `z0_test/` | 测试目录 |

---

## 完整执行流程

### 1. 同步文件到工作仓库

```
本地: ~/.workbuddy/skills/<skill-name>/
     ↓ 同步
仓库: ~/.workbuddy/workbuddy-skills/skills/<skill-name>/
```

**复制规则**：
| 目录/文件 | 处理 |
|-----------|------|
| `SKILL.md` | 必须复制 |
| `_meta.json` | 必须复制 |
| `scripts/*.py` | 复制 |
| `references/` | 复制（递归） |
| `assets/` | 复制（递归） |
| `data/` | 复制（递归） |
| `__pycache__/` | ❌ 不复制 |
| `*.pyc` | ❌ 不复制 |

### 2. 自动更新README.md

**信息提取优先级**：
```
_meta.json → "description" > SKILL.md → description: > 默认值
```

**更新内容**：
- 技能列表表格末尾添加新技能
- 目录结构添加新技能目录

### 3. 提交并推送到双平台

```bash
git add → git commit --amend → git push gitee → git push origin
```

### 4. 生成ZIP包

```
ZIP包结构：
<skill-name>-v<version>.zip
├── SKILL.md
├── _meta.json
├── scripts/
│   └── *.py
├── references/
└── ...（与上传仓库一致）
```

---

## 常见问题

### Q1: GitHub推送失败（443超时）
→ 检查网络代理，或手动推送

### Q2: 码云推送失败
→ 检查remote：`git remote -v`

### Q3: 如何保留历史commit
→ 使用 `--no-edit --no-ff` 合并

### Q4: 本地有html文件被混入
→ 先删除临时文件再执行同步

### Q5: 想同步另一个skill
```bash
./git-sync.sh <skill-name> [version]
# 示例
./git-sync.sh svg-composer 1.3.0
```

---

## 代码管理铁律

1. ✅ 先检查仓库现有状态
2. ✅ 保持标准目录结构
3. ✅ 排除缓存/测试/临时文件
4. ✅ 自动更新README技能列表
5. ✅ ZIP与仓库结构一致
