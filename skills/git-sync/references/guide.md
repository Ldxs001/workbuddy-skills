# git-sync 完整使用指南

> 本文档是 SKILL.md 的渐进式补充，包含完整的执行流程、步骤详解和配置说明。

---

## 完整执行流程（步骤 0 → 9）

### 步骤 0：参数解析 + 类型检测（v2.25+）

| 操作 | 说明 |
|------|------|
| 参数解析 | `--skip-market` / `--market-only` / `--pypi` / `--release` |
| `all` 模式 | `git-sync all` 遍历 `skills/` 和 `agent/` 全部项目 |
| 类型检测 | 自动识别 skill（`_meta.json`）或 agent（`__init__.py`） |
| 版本号读取 | skill→`_meta.json`，agent→`__init__.py` 中的 `__version__` |

### 步骤 0.5：文件路径校准（v2.3+）

| 校验项 | 规则 |
|--------|------|
| 路径穿越防护 | 拒绝 `../`、`..\\`、`/` 开头、`C:` 开头 |
| 目标路径范围 | `realpath` 必须在 `WORK_REPO/{skills|agent}/` 内 |

### 步骤 0.7：版本号比对（v1.6+）

与仓库中已有版本对比，决定是否需要同步：版本相同跳过，本地更新则正常升级。

### 步骤 1：维护清单检查（v1.3+）

同步前自动检查 `manifest.json`。

### 步骤 2~3.5：标准校验（仅 skill）

| 步骤 | 操作 | 适用 |
|------|------|------|
| 2 | `_meta.json` 标准化校验 | skill 仅 |
| 3 | SKILL.md 规范审查（只读） | skill 仅 |

### 步骤 3.7：LLM 文件过滤器（v2.29.0，替换硬编码黑名单）

Python 扫描源目录文件树 + 自动查找规则文件（`blueprint*`, `*rules*`, `blueprints/`），生成扫描报告后**全量打印文件列表 + 排除规则到 stdout**，要求 WorkBuddy 在回复中输出决策 JSON。决策写入 `.file_filter_{name}.json.decisions.json`，**重新运行 git-sync 后读取该文件继续同步**。

交互流程：
1. git-sync 扫描文件 → 打印完整文件列表 + 排除规则 → 退出（返回 None）
2. WorkBuddy 看到输出后，审核文件列表，按规则决定保留/排除
3. WorkBuddy 在回复中输出 `{"allow": ["path/to/file.py", ...]}`，**同时写入决策文件**
4. 重新运行 git-sync → 读取决策文件 → 只复制允许的文件 → 继续后续步骤

| 环境 | 行为 |
|------|------|
| 有决策文件 | 直接读取，跳过审核 |
| 无决策文件 | 打印审核指令，等待 WorkBuddy 回复决策 |
| 决策文件解析失败 | 默认保留所有文件 |

### 步骤 4：同步文件

仅复制 LLM 允许列表中的文件到 `workbuddy-skills/` 仓库。

### 步骤 4.5：LLM 脱敏

扫描已同步文件中的敏感信息（邮箱/token/IP），LLM 自动决策 keep/sanitize，执行脱敏。

### 步骤 5：更新 README.md（skill + agent）

全量扫描 workrepo/skills/ + agent/，生成技能表格 + 智能体表格。

### 步骤 6：提交并推送到双平台

Gitee + GitHub，失败自动 pull --rebase 重试。

### 步骤 6.7：更新清单上传状态

### 步骤 7：生成 ZIP 安装包（仅 skill）

### 步骤 7.5：打包前敏感扫描

### 步骤 8：发布到平台（非静默，直接输出）

| 类型 | 平台 | 命令 |
|------|------|------|
| skill | ClawHub | `npx clawhub publish`（shell=True，已知 CLI bug）|
| skill | SkillHub | `skills_store_cli.py publish --version <ver>`（必须传 --version）|
| agent | PyPI | 隔离构建 → `twine upload --disable-progress`（--pypi 标志）|

### 步骤 9：创建 Release（--release 标志）

打 tag + 推双平台 + 创建 GitHub Release + Gitee 发行版。
- tag 格式：skill=`{name}-v{ver}`，agent=`v{ver}`
- 源码包由 GitHub/Gitee 自动从 tag 生成（Source code zip/tar.gz）
- 同时推送 `pypi/{type}/{name}/{version}` 触发 tag，供 GitHub Actions Trusted Publisher 工作流使用
- 仅 `--release` 标志时执行，平时同步不创建 Release

### 步骤 1：_meta.json 版本同步

同步 version 字段，补全缺失的 name/description，**保留所有既有字段**（不删除任何字段）。

| 标准字段 | 缺失时处理 |
|---------|-----------|
| `name` | 使用目录名 |
| `version` | 使用传入的 version 参数 |
| `description` | 从 SKILL.md 提取 |
| `author` | 从 config.json 读取（缺省为 `your-name-here`） |
| `tags` | 设为空数组 `[]` |

### 步骤 1.5：SKILL.md 内联审计（v2.6.31+）

- **方式**：`git-sync.py` 内置 `step_skill_audit()`，作为同步工作流的一部分自动执行
- **检查项**：版本一致性（`_meta.json` vs `SKILL.md` frontmatter）+ R-23 脚本引用规范
- **模式**：纯警告不阻断（始终 exit(0)）
- **输出**：终端打印检查报告（ERROR=0 WARN=N PASS=M）

### 步骤 2：同步文件到工作仓库

将技能从 ``~/.workbuddy/skills/`<skill-name>/` 同步到 `WORK_REPO/skills/<skill-name>/`。

### 步骤 3：全量重新生成 README.md

> **关键原则**：README.md = 仓库实际内容，不手动维护。

从仓库 `skills/` 目录实际扫描，全量替换 README.md 中的技能列表表格和目录结构。

### 步骤 3.5：SKILL.md 审查输出

审查结果以人类可读格式打印到终端：

```
==================================================
📋 Skill 更新检查报告: <skill-name>
==================================================

✅ 通过项:
   ✅ _meta.json 结构正常
   ...

⚠️  警告/建议:
   💡 具体警告信息...

结论: ERROR=0 WARN=1 PASS=5
```

### 步骤 4：提交并推送到双平台

```bash
git add → git commit → git pull --rebase → git push
```

推送结果分别记录（对应三单一致的状态标记）：
- 码云成功 → 更新 `gitee_version` + 标记 `gitee_ok=true`（Gitee 三单一致）
- GitHub 成功 → 更新 `github_version` + 标记 `github_ok=true`（GitHub 三单一致）
- `uploaded` = `gitee_ok AND github_ok`（双平台均三单一致）

### 步骤 5：生成 ZIP 安装包

```
输出: `.dist/<skill-name>-v<x.x.x>.zip`
排除: *.zip, __pycache__/, .DS_Store, .git, *.html, *.log, ...
```

打包在临时副本中进行，不影响源文件。敏感信息过滤（如果启用）作用于副本。

### 步骤 6：统一输出 + HTML 索引

1. 复制 ZIP 到统一目录 `~/.workbuddy/skills/.dist/`
2. 自动生成/刷新 `index.html` 索引页（含 file:// 链接 + 文件大小 + 时间）
3. 自动打开 dist/ 目录（Windows explorer / macOS open / Linux xdg-open）

> **每次执行完毕后 AI 必须主动调用 `preview_url` 打开 index.html。**

---

## config.json 完整配置模板

```json
{
  "author": "你的作者名",
  "email": "你的邮箱（可选，用于 git commit author）",
  "gitee": {
    "user": "你的码云用户名",
    "repo": "workbuddy-skills",
    "branch": "main",
    "remote_name": "gitee"
  },
  "github": {
    "user": "你的 GitHub 用户名",
    "repo": "workbuddy-skills",
    "branch": "main",
    "remote_name": "origin"
  }
}
```

**关键字段说明**：

| 字段 | 影响范围 |
|------|---------|
| `author` | `_meta.json` 默认作者名；敏感扫描中的用户名检测基准 |
| `email` | git commit 的 author email（`git-sync.py` 中的 `step_commit_and_push()` 使用） |
| `gitee.user` / `github.user` | 生成的查看链接和 README 安装命令中的用户名占位符 |
| `gitee.repo` / `github.repo` | 工作仓库名称（通常两个平台相同） |
| `branch` | 推送目标分支（通常为 main） |

---

## 跨平台环境适配

> 本技能依赖 `rsync` 做本地文件同步。不同平台/安装方式下 `rsync` 可用性不同，需提前确认。

### 环境矩阵

| 环境 | rsync 是否可用 | 说明 |
|------|----------------|------|
| Linux / macOS | ✅ 自带 | 无需额外操作 |
| Git for Windows 完整版 | ✅ 自带 | 位于 Git 安装目录的 usr/bin/ 下 |
| **WorkBuddy PortableGit** | ❌ 不含 | 需手动安装（见下方） |
| Cygwin / MSYS2 | ✅ 自带 | 通过包管理器安装 |
| WSL | ✅ 自带 | 无需额外操作 |

### Windows 下 Python 路径转换问题（重要）

当 `rsync` 不可用时，脚本会 fallback 到 `sync_with_exclude.py`（Python 方案）。

**问题根因：**
- Git Bash 只对 **MSYS2 编译的程序** 自动转换 Unix 路径（`/c/Users/...` → `C:\Users\...`）
- 如果 `python` 是 **Windows 原生 exe**（如 `.workbuddy\binaries\...`），路径不会被转换
- Python 收到 `/c/Users/...` 会误解为 `C:\c\Users\...`，导致文件找不到

**症状：**
```
C:\Users\USERNAME\.workbuddy\binaries\python\...\python.exe: can't open file 'c:\\c\\Users\\...'
```

**解决方案（任选其一）：**

| 方案 | 操作 | 推荐度 |
|------|------|--------|
| **A. 安装 rsync** | 见下方「各平台安装 rsync」| ⭐⭐⭐ 最推荐 |
| **B. 用 MSYS2 版 Python** | `pacman -S python`（MSYS2 内）| ⭐⭐ |
| **C. 手动调用 Python 时传 Windows 路径** | `python sync_with_exclude.py "C:\..." "C:\..."` | ⭐ 临时 |

### 各平台安装 rsync

#### Windows（WorkBuddy PortableGit 环境）

**方式一：下载独立 rsync.exe 放到 PortableGit**

```bash
# 在 Git Bash 中执行，下载 rsync.exe 到 PortableGit/usr/bin/
cd $HOME/.workbuddy/vendor/PortableGit/usr/bin/
# 从 Git for Windows 获取 rsync 工具
# 在 Git Bash 中执行：
cd $HOME/.workbuddy/vendor/PortableGit/usr/bin/
# 安装 rsync（如已安装可跳过）
# 验证
rsync --version
```

# 验证
rsync --version
```

**方式二：安装完整版 Git for Windows**

从 [git-scm.com](https://git-scm.com/download/win) 下载安装，**安装时勾选「Use Unix tools from the Command Prompt」**，安装后 `rsync` 可用。

#### Linux

```bash
# Debian/Ubuntu
sudo apt install rsync

# RHEL/CentOS
sudo yum install rsync

# Arch
sudo pacman -S rsync
```

#### macOS

```bash
# 自带 rsync，如缺失：
brew install rsync
```

#### MSYS2 / Cygwin

```bash
# MSYS2
pacman -S rsync

# Cygwin（通过安装程序添加 rsync 包）
```

### 故障排除

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `rsync: command not found` | rsync 未安装或未在 PATH | 按上方对应平台安装 |
| `can't open file 'c:\\c\\Users\\...'` | Python fallback 路径转换失败 | 安装 rsync，或传 Windows 路径调用 Python |
| `SCRIPT_DIR` 路径计算错误 | 用绝对路径调用 `bash git-sync.sh` | **先 `cd` 到脚本目录再执行**（见下方正确调用方式）|

### 正确调用方式

本机 rsync 不可用，实际走 `git-sync.py`。支持以下用法：

```bash
# 基础用法（自动识别类型）
python git-sync.py <name>

# 指定版本
python git-sync.py <name> <version>

# 跳过市场发布
python git-sync.py <name> --skip-market

# 只发市场不推 git
python git-sync.py <name> --market-only

# 发布到 PyPI（仅 agent）
python git-sync.py <name> --pypi

# 创建 Release
python git-sync.py <name> --release

# 全部项目
python git-sync.py all

# 组合使用
python git-sync.py rag-assistant --pypi --release --skip-market
```

---

## 配置说明（LLM 参考）

> 本技能的配置存放在数据目录，脚本自动读取，无需手动创建文件。

### 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| `config.json` | `skills/.standardization/git-sync/data/config.json` | 平台用户名、仓库名、分支等配置 |
| `manifest.json` | `skills/.standardization/git-sync/data/manifest.json` | 技能同步状态清单 |

### config.json 字段说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `author` | `_meta.json` 默认作者名；敏感扫描中的用户名检测基准 | `[username-redacted]` |
| `gitee.user` | 码云用户名，用于生成查看链接和 README 命令 | `[username-redacted]` |
| `gitee.repo` | 码云仓库名 | `workbuddy-skills` |
| `gitee.branch` | 码云推送目标分支 | `main` |
| `github.user` | GitHub 用户名 | `[username-redacted]` |
| `github.repo` | GitHub 仓库名 | `workbuddy-skills` |
| `github.branch` | GitHub 推送目标分支 | `main` |

### 脚本读取方式

所有 `git-sync` 脚本通过以下逻辑定位 `config.json`：

```python
import os
SKILLS_DIR = os.path.expanduser('~/.workbuddy/skills')
GIT_SYNC_DATA = os.path.join(SKILLS_DIR, '.standardization', 'git-sync', 'data')
config_path = os.path.join(GIT_SYNC_DATA, 'config.json')
```

### 初始化配置

首次使用本技能前，确保数据目录中存在 `config.json`：

```bash
mkdir -p ~/.workbuddy/skills/.standardization/git-sync/data
cat > ~/.workbuddy/skills/.standardization/git-sync/data/config.json << 'EOF'
{
  "author": "your-name-here",
  "gitee": {
    "user": "your-gitee-username",
    "repo": "workbuddy-skills",
    "branch": "main",
    "remote_name": "gitee"
  },
  "github": {
    "user": "your-github-username",
    "repo": "workbuddy-skills",
    "branch": "main",
    "remote_name": "origin"
  }
}
EOF
```

> ⚠️ `config.json` 含用户名等敏感信息，已被 `--exclude=config.json` 排除在同步/打包范围外，不会上传到远程仓库。
