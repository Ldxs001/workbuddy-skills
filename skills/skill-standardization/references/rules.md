# 改写/更新铁律（AI 执行前必须遵守）

> 本文件为 skill-standardization v2.13.0 的铁律条款，AI 更新任何 skill 前必须严格遵守。

---


## 铁律 1：author 字段不可擅自替换

- 技能是通用工具，author 默认值必须为 `your-name-here` 占位符
- 已有 author 值（如 `"由 config.json 的 author 字段决定"`）保留原值不变
- 只有用户明确指定时才写入真实署名
- **本 skill 例外**：author 为 `[username-redacted]`（维护者署名，铁律1例外条款）

---

## 铁律 2：版本号更新规则（规范内有规定直接更新，无规定必须询问）

**规范内明确定义的文件/字段 — 直接更新，无需询问：**

| 文件 | 版本号位置 | 更新规则 |
|------|-----------|----------|
| `SKILL.md` | frontmatter `version:` | 按 SemVer 直接升级，无需询问 |
| `_meta.json` | `"version"` | 与 SKILL.md 保持一致，直接升级 |
| `scripts/spec/*.json` | `"_version"` 字段 | 对应模块更新时直接升级 |
| `scripts/*.py` | 文件头版本字符串（如 `v2.3.0`） | 脚本逻辑更新时直接升级 |

**规范未覆盖的文件/字段 — 必须询问用户：**

- 目标 skill 中存在但本规范未定义的版本号位置
- `manifest.json` 中的版本号（由 git-sync 上传流程负责，本地不应擅改）
- 任何不在上表中的文件或字段

→ 遇到上述情况时，先问用户"是否升级版本号？"，确认后再操作。

---

## 铁律 3：改写前必须理解每个文件的作用

- 更新任何文件前，先用 Read 工具阅读完整内容
- 理解每个字段的含义、引用关系、被哪些脚本使用
- 特别注意：`config.json`（运行时配置）、`manifest.json`（维护清单状态数据）、`_meta.json`（标准化元数据）

---

## 铁律 4：产出物路径管理规范

**核心规则：** 任何技能在运行时产生的业务文件（日程、任务清单、缓存、导出、配置快照等）统一存放至 `skills/.standardization/<skill_name>/` 路径下，**禁止放在技能文件夹下**，防止技能更新/重装时积累性数据丢失。

> 这条规则约束的是技能**运行期**产生的用户数据，不是标准化过程本身的备份。无论是 create/update/refactor 模式还是日常运行，技能都不应把自己的产出物嵌在自身目录内。

### 标准化路径

`.standardization/` 位于 `skills/` 目录内部。从脚本向上 2-3 级即可定位 `skills/`，然后 `.standardization/<skill_name>/`。

```
skills/
├── .standardization/
│   └── <skill_name>/
│       ├── data/             # 持久化业务数据（日程 .ics、任务清单 .json、配置快照等）
│       ├── cache/            # 短期缓存（可重建，可随技能升级清空）
│       ├── outputs/          # 生成/导出产物（报表 .html、图表 .png、文档 .md 等）
│       └── temp/             # 临时文件（会话级，可随时清理）
├── git-sync/
│   ├── SKILL.md
│   └── scripts/
├── other-skill/
│   └── ...
```

### 分类规则

| 产出物类型 | 目标子目录 | 典型文件示例 |
|-----------|-----------|--------------|
| **持久化业务数据** | `data/` | 日程 `.ics`、任务清单 `.json`、配置快照、用户偏好、积累性数据 |
| **短期缓存** | `cache/` | HTTP 缓存、模型推理缓存、`*.pkl`、中间计算结果 |
| **生成/导出产物** | `outputs/` | 报表 `.html/.pdf`、图表 `.png`、导出 `.csv`、生成的文档 |
| **临时文件** | `temp/` | `*.tmp`、`draft_*`、阶段性中间产物、会话级临时数据 |

### 设计理由

- **技能文件夹干净**：仅保留源代码（SKILL.md + scripts/ + references/ 等），更新覆盖不丢失用户积累的数据
- **工作区级隔离**：不同技能的产出物存放在各自子目录，互不污染

---

## 铁律 5：R-13~R-17 安全规则强制检查

> 自 v2.13.0 起，所有 skill 必须通过上述 5 条安全规则检查。

### R-13：敏感信息访问声明

**检查内容：**
- 脚本含敏感信息访问（`memory/`、`credentials`、`token`、`password` 等）时，frontmatter 须声明 `sensitive_access: true` 并说明用途
- 敏感信息访问包括：读取 memory 文件、访问凭证、读取 token、读取密码等

**修复方法：**
1. 在 `SKILL.md` frontmatter 中添加 `sensitive_access: true`
2. 在 `SKILL.md` 中说明敏感信息访问的用途

**检查方法：**
- `permission_checker.py` 扫描脚本中的敏感信息访问模式
- 检查 frontmatter 是否声明 `sensitive_access: true`

---

## 铁律 6：临时文件与备份必须记录并清理

- 所有创建、更新、改造过程中产生的临时文件和备份文件，**必须**记录到 `op_logger` 日志（`temp_files` 和 `backup_files` 字段）
- 主体操作完成后（审计通过 + 版本号更新 + 更新日志维护完毕），**必须**按规范清除临时文件（会话级，立即清除）和过期备份（保留最新 10 个）
- 更新/改造前**必须**对目标技能目录执行整体备份（`backup_skill()`），备份命名格式：`<skill-dir>_bak_<operation>_<YYYYMMDD_HHMMSS>`
- `scripts/safe_io.py` 所有写操作**必须**内置 `backup_file()` 临时备份，返回 `rollback_id`，确保删/改动作可回滚


---

### R-14：关键位置写入声明

**检查内容：**
- 脚本含关键位置写入（`skills/`、`.workbuddy/`、`系统目录`）时，frontmatter 须声明 `critical_write: true` 并说明用途
- 关键位置写入包括：写入 skills 目录、写入技能数据目录、写入系统目录等

**修复方法：**
1. 在 `SKILL.md` frontmatter 中添加 `critical_write: true`
2. 在 `SKILL.md` 中说明关键位置写入的用途

**检查方法：**
- `permission_checker.py` 扫描脚本中的关键位置写入模式
- 检查 frontmatter 是否声明 `critical_write: true`

---

### R-15：高权限操作授权检查

**检查内容：**
- 脚本含文件删除/网络请求/subprocess 调用时，执行前须调用 `authorization_manager.py` 请求用户授权
- 高权限操作包括：`os.remove`、`shutil.rmtree`、`requests.get`、`subprocess.run` 等

**修复方法：**
1. 在脚本中调用 `authorization_manager.py request` 请求授权
2. 根据用户授权结果决定是否执行高权限操作

**检查方法：**
- 检查脚本中是否调用 `authorization_manager.py`
- 检查是否包含授权检查逻辑（`check_authorization`、`request_authorization` 等）

---

### R-16：权限权重说明

**检查内容：**
- 建议在 `SKILL.md` 或 `references/` 中说明各操作的权限权重，便于审查时评估风险
- 权限权重模型：
  - 敏感信息访问：40%
  - 关键位置写入：30%
  - 网络访问：20%
  - 文件删除：10%
  - Subprocess 调用：+20% 额外加权

**修复方法：**
1. 在 `SKILL.md` 中添加"权限权重说明"章节
2. 或在 `references/` 中创建权限权重说明文档

**检查方法：**
- 检查 `references/` 中是否有权限权重说明文档
- 检查 `SKILL.md` 中是否包含权限权重说明

---

### R-17：渐进加载引用（强制）

**检查内容：**
- `SKILL.md` > 200 行时必须拆分到 `references/`，并通过「→ 详见 references/xxx.md」引用
- 禁止主文件超限（> 200 行）

**修复方法：**
1. 将 `SKILL.md` 中详细内容拆分到 `references/xxx.md`
2. 在 `SKILL.md` 中添加引用链接：「→ 详见 references/xxx.md」

**检查方法：**
- 计算 `SKILL.md` 行数
- 如果 > 200 行，检查是否有 `references/` 引用

---

---

## 铁律 7：更新日志渐进加载（R-24）

> 自 v2.38.6 起，更新日志（changelog）**禁止**直接写在 `SKILL.md` 正文中。

### 规则内容

- `SKILL.md` **不得**含有 `## 更新日志` / `## Changelog` / `## 更新记录` 等章节
- `SKILL.md` **不得**含有版本号标题（如 `## v2.3.0`）形式的更新记录
- 更新日志必须放在 `references/changelog.md` 中
- `SKILL.md` 中只能保留一行引用：
  ```
  → 详见 references/changelog.md
  ```

### 设计理由

- `SKILL.md` 是**入口文件**，应当保持精简（≤230 行）
- 更新日志会不断累积，直接写在 `SKILL.md` 会导致文件迅速膨胀
- 渐进式加载是 skill-standardization 的核心规范之一（R-17~R-21）

### 修复方法

1. 将 `SKILL.md` 中的更新日志章节移至 `references/changelog.md`
2. 在 `SKILL.md` 原位置替换为：`→ 详见 references/changelog.md`
3. 确认 `references/changelog.md` 格式规范（每条含版本号、日期、更新说明）

### 检查方法

- `structure_checker.py` 的 `check_changelog_progressive()` 函数
- 正则检测 `## 更新日志` / `## Changelog` / `## vX.Y.Z` 等模式
