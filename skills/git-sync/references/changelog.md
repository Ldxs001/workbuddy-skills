# git-sync 版本更新日志

---

## v2.0.4（2026-05-23）

**改写类型：补充"工作流程"章节（R-09 合规）**

### 变更内容
- SKILL.md 新增 `## 工作流程` 章节，含 AI 执行节奏流程图 + 步骤概览表（步骤 0→6）
- 版本号：2.0.3 → 2.0.4（SKILL.md + _meta.json）

---

## v2.0.3（2026-05-23）

**改写类型：skill-standardization update 自动补充 _meta.json 字段**

### 变更内容
- `_meta.json` 补充缺失标签字段（`tags` 等），通过 skill-standardization v2.10.0 `update --fix` 自动完成

---

## v2.0.2（2026-05-23）

**改写类型：修复 sync_with_exclude.py 根目录判断错误**

### 问题

- `sync_with_exclude.py` 的 `should_exclude()` 用 `"/" not in p` 判断根目录，但 `rel_path` 带了 `git-sync/` 前缀，导致 `config.json` / `manifest.json` 根目录文件未被排除
- `pack_zip.py` 的 `pack_skill()` 传给 `should_exclude` 的 `rel_path` 也带了 `skill_name/` 前缀，同样误判

### 变更内容

#### `scripts/sync_with_exclude.py` — `should_exclude()` 修复
- 改用 `os.path.dirname(p) == ""` 判断真正根目录
- `sync_with_exclude()` 中 `rel_path` 修正为相对于 `src` 根目录的路径

#### `scripts/pack_zip.py` — `should_exclude()` 修复
- 同上的根目录判断修复
- `pack_skill()` 中 `rel_path` 计算修正

#### 文件变更
- 删除 `scripts/2.3.0`（zip 碎片垃圾文件）

---

## v2.0.1（2026-05-23）

**改写类型：统一排除规则（仓库同步 + ZIP 打包）**

### 问题

- 排除规则只作用于 `pack_zip.py`（ZIP 打包），`git-sync.sh` 的 `rsync` 步骤排除规则不完整
- `rsync` fallback（rm -rf + cp）完全没有排除逻辑，存在安全隐患

### 变更内容

#### 新增文件

| 文件 | 作用 |
|------|------|
| `scripts/.git-sync-exclude.txt` | 排除规则配置文件（rsync + python 共用） |
| `scripts/sync_with_exclude.py` | Python 排除复制（rsync 不可用时的 fallback） |

#### `git-sync.sh` 改进

- **新增 `RSYNC_OPTS` 数组**：与 `pack_zip.py` / `.git-sync-exclude.txt` 规则完全一致
- **白名单优先**：`--include=settings.html` + `--include=preview.html` 在排除参数之前
- **rsync fallback 重写**：不再用 `rm -rf` + 裸 `cp`，改为调用 `sync_with_exclude.py`
- 移除原 fallback 中重复的 `references/` 复制块（逻辑错误）

#### `pack_zip.py` 排除规则（已有，本次补充文档）

| 层级 | 变量 | 说明 |
|------|--------|------|
| 目录排除 | `EXCLUDE_DIRS` | `__pycache__`、`.git`、`dist` 等 |
| 精确文件名 | `EXCLUDE_FILES_EXACT` | `config.json`（仅根目录）、`manifest.json` 等 |
| glob 模式 | `EXCLUDE_FILES_GLOB` | `*.pyc`、`*.log`、`*.zip`、`*.bak` 等 |
| 功能性白名单 | `FUNCTIONAL_FILE_WHITELIST` | `settings.html`、`preview.html` |

#### 规则维护约定

- 修改排除规则时，需同步更新 3 个位置：
  1. `scripts/.git-sync-exclude.txt`（配置文件）
  2. `scripts/pack_zip.py`（Python 规则变量）
  3. `scripts/git-sync.sh`（RSYNC_OPTS 数组）
- 三者保持一致，否则排除行为会出现差异

---

## v1.10.0（2026-05-23）

**改写类型：pack_zip.py 排除规则体系重构**

### 变更内容

#### 问题
- 原 `default_exclude` 使用 `*.html` blanket 排除，导致 `settings.html` 等功能文件被错误排除
- 排除规则按扩展名粗放分类，未区分文件角色

#### 修复设计
重构为**按文件角色分类**的三层排除体系：

| 层级 | 变量 | 说明 |
|------|--------|------|
| 目录排除 | `EXCLUDE_DIRS` | `__pycache__`、`.git`、`dist`、`node_modules` 等 |
| 精确文件名 | `EXCLUDE_FILES_EXACT` | `config.json`（仅根目录）、`manifest.json`、`pack_zip.py` 等 |
| glob 模式 | `EXCLUDE_FILES_GLOB` | `*.pyc`、`*.log`、`*.zip`、`*.bak` 等 |
| 功能性白名单 | `FUNCTIONAL_FILE_WHITELIST` | `settings.html`、`preview.html` 不受 `*.html` 规则影响 |

#### 关键变更
- **移除 `*.html` blanket 排除**（不再需要，`index.html` 不在 skill 目录中）
- **新增 `FUNCTIONAL_FILE_WHITELIST`**：`settings.html`、`preview.html`
- `config.json` / `manifest.json` 精确匹配**仅排除根目录**，子目录的同名文件保留
- `should_exclude()` 函数重写，支持白名单优先逻辑

#### 文件变更
- `scripts/pack_zip.py`：整体重写，版本逻辑不变（v1.10.0 为 skill 级别版本）

---


## v1.9（当前版本）— 渐进式规范改写

- **SKILL.md 从 521 行重构为 89 行核心骨架**（减少 83%），符合 v2.0 标准的 ≤200 行要求
- **新增 `references/` 渐进式 MD 文档体系**（4个文件）：
  - `references/guide.md` — 完整执行流程步骤 0→6 详细文档
  - `references/reference.md` — CLI 速查、变量表、ZIP 排除列表、敏感信息规则
  - `references/faq.md` — 14 个 FAQ 按场景分类（同步/ZIP/清单/敏感/审查）
  - `references/changelog.md` — 完整版本历史 + Roadmap
- **frontmatter author** 从非常量引用修正为常量值 `[username-redacted]`
- **清理根目录遗留垃圾**：删除异常 ZIP 文件 `2.0.0`、6 个 `.tmp_zip_*` 临时目录、过时空目录 `references/`
- 通过 skill-standardization v2.0 update 验证：**ERROR=0, WARN=1**（WARN 为合理运行时文件例外）

## v1.8 — 规范审查集成

- 新增 SKILL.md 规范化审查功能（`skill_audit.py`）
- 集成 10 条审查规则 R-01~R-10（4 ERROR + 6 WARN）
- 同步流程从 7 步升级为 8 步（新增步骤 1.5 审查步骤 + 3.5 输出步骤）
- 零依赖轻量 YAML frontmatter 解析器（内置，无需 PyYAML）
- 支持同义词关键词匹配（容忍章节命名不一致）
- 支持 `--json` 模式输出和 `audit-all` 批量审查
- 独立 CLI 可脱离 git-sync 单独运行
- 审查策略为**纯警告模式**：ERROR 不退出非零码，不阻断同步

## v1.7 — 敏感信息过滤 + 双平台独立状态

- 新增敏感信息过滤系统（`sensitive_scan.py`）
- 维护清单支持双平台独立状态字段：
  - `gitee_ok` / `github_ok`（各自上传成功标记）
  - `gitee_version` / `github_version`（各自实际推送的版本）
- `manifest.py` 新增 `set-uploaded` 子命令，支持 `--platform` 参数
- `git-sync.sh` 推送结果分别标记，不再绑死双平台
- 执行完成后自动 `preview_url` 打开 `.dist/index.html`
- ZIP 生成后自动刷新 `index.html`（`build_index.py` 自动调用）

## v1.6 — 按需同步 + 版本号对比

- 【按需同步】不在全量模式下只同步用户指定的技能（默认行为变更）
- 【版本号三方对比】manifest 清单 version vs 待更新 version，决定跳过/更新/报异常
- `manifest.py` 新增 `version` 子命令（查询/更新条目版本号）
- 支持分平台版本号更新（`--platform gitee/github`）

## v1.5 — 统一输出目录 + HTML 索引页

- 所有 ZIP 统一输出到 `~/.workbuddy/skills/.dist/`
- 自动生成 `index.html` 索引页（含 `file://` 超链接、文件大小、修改时间）
- 打包后自动打开 dist/ 目录（Windows explorer / macOS open / Linux xdg-open）
- 修正三单一致原则描述：manifest.json ≥ 仓库实际文件 = README.md

## v1.4 — 安全加固

- 【路径穿越防护】SKILL_NAME 校验：拒绝 `../`、盘符开头等危险输入
- 【路径范围校验】`realpath` 验证目标必须在 `WORK_REPO/skills/` 内
- 【安全同步工具】优先使用 `rsync --delete` 替代 `rm -rf` + `cp -r`

## v1.3 — 三单一致维护清单机制

- 新增 `manifest.json` 维护清单，记录计划管理的技能全集
- 新增 `manifest.py` CLI 工具（list / add / remove / check / diff / sync-readme 子命令）
- git-sync.sh 同步前检查清单，不在清单中时询问用户意图
- `update_readme.py` 改为从仓库实际文件全量生成 README.md
- 确立三单一致原则：清单 ⊇ 仓库 = README.md

## v1.2 — _meta.json 标准化

- 新增 `normalize_meta.py`，标准化 `_meta.json` 为 5 字段结构
- 自动删除非标准字段（slug, ownerId, publishedAt 等）
- `update_readme.py` 独立化，修复幂等性 bug

## v1.1 — 初始版本

- ZIP 打包功能（标准安装包生成）
- 双平台推送（同时推送到 Gitee 和 GitHub）
- 基础 _meta.json 模板填充

---

## Roadmap（规划中）

| 版本 | 计划内容 | 状态 |
|------|---------|------|
| v1.9 | 支持多仓库同步（非仅 workbuddy-skills） | 规划中 |
| v2.0 | 重构为 Python 主引擎（减少 bash 脚本依赖） | 规划中 |
| v2.1 | Webhook 触发式 CI/CD 集成 | 远期 |
