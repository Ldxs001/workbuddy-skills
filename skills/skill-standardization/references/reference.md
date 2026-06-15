# API / 命令参考

> 本文件为 skill-standardization v2 的完整命令参考手册。
> 涵盖所有 CLI 工具的参数、返回值、错误码及配置项。

---

## 目录

1. [skill_builder — 构建器](#skill_builder)
2. [skill_audit — 审查器](#skill_audit)

---

## skill_builder

> 路径：`scripts/skill_builder/`
>
> 用途：Skill 全生命周期管理（创建/更新/改造）

### create 命令

从模板初始化一个新的标准 skill。

**语法：**
```bash
python -m skill_builder create <name> [--desc <text>] [--dir <path>] [--tags <tag1,tag2,...>]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | positional | ✅ | — | Skill 名称，同时作为目录名和 name 字段 |
| `--desc` / `-d` | option | ❌ | `"<name> skill"` | 技能描述（写入 frontmatter 和 _meta.json） |
| `--dir` | option | ❌ | 当前目录 | 父目录路径 |
| `--tags` | option (nargs*) | ❌ | `[]` | 标签列表（空格分隔） |

**输出结构：**
```
<name>/
├── SKILL.md          # 含 frontmatter + TODO 占位符模板
├── _meta.json        # {name, version: "0.1.0", description, author: "[username-redacted]", tags}
├── references/.gitkeep
└── scripts/.gitkeep
```

**退出码：**
| 码 | 含义 |
|----|------|
| `0` | 创建成功 |
| `1` | 目录已存在 |

**示例：**
```bash
python -m skill_builder create my-tool --desc "通用工具" --tags tool,utility
```

---

### update 命令

对已有 skill 进行增量规范化检查。

**语法：**
```bash
python -m skill_builder update <skill_dir> [--fix] [--backup]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `skill_dir` | positional | ✅ | — | Skill 目录的绝对或相对路径 |
| `--fix` | flag | ❌ | `False` | 自动修复可修复的问题 |
| `--backup` | flag | ❌ | `False` | 更新前自动备份 |

**检查项目（共 6 项）：**

| # | 检查项 | 自动修复？ | 说明 |
|---|--------|-----------|------|
| 1 | `_meta.json` 存在性 + 五字段完整 | ✅ --fix | 缺失字段自动补充空值 |
| 2 | `_meta.json` JSON 合法性 | ❌ | 格式错误仅警告 |
| 3 | `SKILL.md` 存在性 + frontmatter | ❌ | 需手动更新 |
| 4 | 必填章节完整性（3个） | ❌ | 模糊匹配关键词 |
| 5 | 文件大小 + 根目录规范性 | 💡 | 建议性提示 |
| 6 | scripts/ + 根目录 产出物路径规范性 | 💡 | 扫描铁律4违规 + 交叉引用追踪（v2.7.2 增强） |

**报告格式：**
```
==================================================
📋 Skill 更新检查报告: <name>
==================================================

✅ 通过项:
   ✅ _meta.json 结构正常

⚠️  警告/建议:
   ⚠️  SKILL.md 共 250 行，超过 230 行建议拆分到 references/

结论: ERROR=0 WARN=1 PASS=1
```

**退出码：** 始终 `0`（纯报告模式）。

---

### refactor 命令

对非标 skill 进行整体结构改造。

**语法：**
```bash
python -m skill_builder refactor <skill_dir> [--no-backup] [--dry-run]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `skill_dir` | positional | ✅ | — | 要改造的 Skill 目录路径 |
| `--no-backup` | flag | ❌ | `False` | 不创建备份（不推荐！） |
| `--dry-run` | flag | ❌ | `False` | 仅输出计划，不执行实际操作 |

**执行阶段：**

| 阶段 | 动作 | 输出 |
|------|------|------|
| 阶段 1 | 全量扫描 | 文件清单（路径+大小+时间）+ 散落文件分析 |
| 阶段 2 | 备份 | 时间戳命名备份目录 |
| 阶段 3 | 迁移 | 按 M-01~M-06 规则移动文件 |
| 阶段 4 | 验证 | 字节一致性对比 + 迁移映射表 |

**迁移规则速查：**

| 源文件类型 | 目标目录 | 规则 ID |
|-----------|---------|---------|
| `.py`, `.sh`, `.bat`, `.ps1` | `scripts/` | M-01 |
| `.md`（非 SKILL.md） | `references/` | M-02 |
| `.txt`, `.cfg`, `.ini`, `.toml`, `.yaml`, `.yml` | `scripts/` | M-03/M-06 |
| `.json`（非 meta/spec） | `scripts/` | M-04 |
| `.png`, `.jpg`, `.gif`, `.svg`, `.ico` | `assets/`（自动创建） | M-05 |
| `__pycache__/` | 排除（跳过） | M-05 |

**dry-run 输出示例：**
```
🔍 阶段 1: 全量扫描 old-skill
----------------------------------------
  发现 8 个文件:
    SKILL.md                                    2.1KB
    README.md                                   5.3KB
    tool.py                                     1.2KB
    config.json                               512.0B
    ...

  📋 重构计划:

  将要移动的文件 (4):
    README.md                     → references/README.md
    tool.py                       → scripts/tool.py
    config.json                   → scripts/config.json
    logo.png                      → assets/logo.png

  保持在原位的文件 (4):
    SKILL.md                        (standard root file)
    .gitignore                      (git)
    _skillhub_meta.json             (legacy meta (keep))
```

**退出码：**
| 码 | 含义 |
|----|------|
| `0` | 执行成功（含 dry-run） |
| `1` | 目录不存在 |

---

## skill_audit

> 路径：`scripts/skill_audit/`
>
> 用途：基于 R-01~R-26 规则对 SKILL.md 进行自动化审查

### audit 命令

**语法：**
```bash
python -m skill_audit audit <skill_dir> [--json] [--strict]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `<skill_dir>` | positional | ✅ | — | Skill 目录路径 |
| `--json` | flag | ❌ | `False` | 以 JSON 格式输出结果 |
| `--strict` | flag | ❌ | `False` | 严格模式（ERROR 级 exit(1)） |

**审查规则一览（共 25 条）：**

| ID | 级别 | 名称 | 检查内容 |
|----|------|------|----------|
| R-01 | ERROR | Frontmatter 存在性 | 文件以 `---` 开头且有闭合 |
| R-02 | ERROR | name 字段 | frontmatter 包含 `name:` |
| R-03 | ERROR | version SemVer | 版本号匹配 `\d+\.\d+\.\d+(-\w+)?` |
| R-04 | ERROR | description 字段 | frontmatter 包含 `description:` |
| R-05 | WARN | name 与目录名一致 | `name == 父目录名` |
| R-26 | WARN | 正文含一级标题 | 有 `# ` 开头的行 |
| R-07 | ERROR | 触发条件章节（合规） | 含正向触发词≥3个、否定条件≥1个，无「自动执行」等危险表述 |
| R-08 | WARN | 核心能力章节 | 匹配核心能力同义词 |
| R-09 | WARN | 工作流程章节 | 匹配工作流程同义词 |
| R-10 | ERROR | version 一致性 | SKILL.md version == _meta.json version |
| R-11 | ERROR | 产出物路径规范性 | 产出物路径符合 skills/.standardization/<skill>/ 规范，且无路径遍历、跨目录写入、敏感信息泄露风险 |
| R-12 | ERROR | 外部数据目录规范性 | 外部数据目录路径符合 skills/.standardization/<skill-name>/ 约定，_meta.json 含 data_dir 字段且一致，且无数据泄露风险 |
| R-13 | ERROR | 敏感信息访问声明 | 脚本含敏感信息访问（memory/credentials/token）时，frontmatter 须声明 sensitive_access: true 并说明用途 |
| R-14 | ERROR | 关键位置写入声明 | 脚本含关键位置写入（skills/技能数据目录/系统目录）时，frontmatter 须声明 critical_write: true 并说明用途 |
| R-15 | ERROR | 高权限操作授权检查 | 脚本含文件删除/网络请求/subprocess 调用时，须在 frontmatter 声明对应权限并说明用途 |
| R-16 | WARN | 权限权重说明 | 建议在 SKILL.md 或 references/ 中说明各操作的权限权重，便于审查时评估风险 |
| R-17 | ERROR | 渐进加载引用（强制） | SKILL.md > 230 行时必须拆分到 references/，并通过「→ 详见 references/xxx.md」引用 |
| R-18 | WARN | 反模式具体性 | 正文含 ## 反模式/常见错误 章节，且每条反模式含具体描述（≥20字）或代码示例 |
| R-19 | WARN | FAQ 有意义性 | 正文含 ## FAQ/常见问题 章节，且 Q&A 对有意义（Q≥10字，A≥15字） |
| R-20 | WARN | 写作规范（术语一致/禁止模糊表述/中英文混排） | 正文术语一致、无模糊表述、中英文混排有空格 |
| R-21 | WARN | 渐进式加载显式说明 | SKILL.md 在显眼位置（核心能力/工作流程章节）显式说明渐进式加载（含「渐进式加载」或「progressive」关键词） |
| R-22 | WARN | 数据目录规范检查 | 安装目录无越位数据文件（构建产物/缓存/日志应放在 data_dir: 声明的数据目录） |
| R-23 | WARN | 文档-代码一致性检查 | SKILL.md 中引用的脚本/文件/函数名真实存在，代码示例中的调用方式与实际代码一致 |
| R-24 | WARN | 更新日志渐进加载 | 更新日志必须放在 references/changelog.md，SKILL.md 只能有引用 |

**JSON 输出格式：**
```json
{
  "skill": "my-skill",
  "timestamp": "2026-05-22T19:00:00",
  "results": [
    {"id": "R-01", "level": "ERROR", "status": "PASS", "detail": "..."},
    {"id": "R-02", "level": "ERROR", "status": "PASS", "detail": "..."}
  ],
  "summary": {"error": 0, "warn": 2, "pass": 8, "total": 10},
  "exit_code": 0
}
```

---

## 错误码总表

| 工具 | 退出码 | 含义 |
|------|--------|------|
| skill_builder | `0` | 成功 |
| skill_builder | `1` | 参数错误/目录已存在/不存在 |
| skill_audit | `0` | 审查完成（默认模式） |
| skill_audit | `1` | 严格模式下有 ERROR（--strict） |

---

## 配置与环境

### 无外部依赖

所有脚本均使用 Python 标准库：
- `argparse` — CLI 参数解析
- `json` — JSON 读写
- `pathlib` — 路径操作
- `shutil` — 文件移动/复制
- `re` — 正则表达式
- `datetime` — 时间戳生成

### Python 版本要求

- **最低**: Python 3.8+
- **推荐**: Python 3.11+
- **测试环境**: Python 3.11.8 (Windows)

### 编码约定

- 所有文件使用 **UTF-8** 编码
- JSON 输出使用 `ensure_ascii=False` 支持中文
- 换行符：LF（Unix 风格）

---

## permission_checker.py

> 路径：`scripts/permission_checker.py`
>
> 用途：扫描 skill 脚本，提取文件操作，计算权限权重，生成风险报告

### 基本用法

```bash
# 扫描单个 skill
python -m permission_checker.py <skill-dir> [--json]

# 输出 JSON 报告（供 AI 解析）
python -m permission_checker.py skills/my-skill --json
```

### 输出格式（JSON）

```json
{
  "skill_dir": "/path/to/skill",
  "risk_level": "medium",
  "permission_weight": 0.45,
  "stats": {
    "files_scanned": 3,
    "lines_scanned": 450,
    "issues_found": 5
  },
  "issues": [...],
  "summary": {
    "total_issues": 5,
    "high_severity": 2,
    "error_severity": 1,
    "recommendation": "建议修复高严重度问题后再发布"
  },
  "report_file": "/path/to/report.json"
}
```

### 权限权重计算

| 维度 | 权重 | 说明 |
|------|------|------|
| 敏感信息访问 | 40% | 读取 memory/credentials/token 等 |
| 关键位置写入 | 30% | 写入 skills/技能数据目录/系统目录 |
| 网络访问 | 20% | 发起 HTTP 请求 |
| 文件删除 | 10% | 删除文件或目录 |

---

## 版本号更新文件映射表

| 更新类型 | 需同步版本号的文件位置 | 升级类型 |
|---------|----------------------|---------|
| 修正错别字/排版（仅 SKILL.md） | SKILL.md `version` + `_meta.json` `"version"` | PATCH（2.1.0→2.1.1） |
| 更新 `scripts/spec/*.json` 规范 | 对应 `.json` 的 `"_version"` + SKILL.md + `_meta.json` | PATCH 或 MINOR（视更新范围） |
| 更新 `scripts/*.py` 脚本逻辑 | `.py` 文件头版本字符串 + SKILL.md + `_meta.json` | MINOR（2.1.0→2.2.0） |
| 新增功能/新脚本 | 所有上述文件 + `manifest.json`（上传时同步） | MINOR 或 MAJOR |
| 仅改 `references/*.md` | 视情况——内容影响功能时升 SKILL.md + `_meta.json` | 通常 PATCH |
| 最终同步上传后 | `manifest.json` 由同步流程自动更新 | 跟随 SKILL.md 版本 |

**关键原则：**

- 本地更新只改 SKILL.md + _meta.json + 受影响的脚本/json 文件内的版本字符串
- `manifest.json` 由同步上传流程负责，本地不应擅改
- **不确定是否升级版本号时，必须询问用户**（适用于所有上述文件类型）


---

## CLI 命令参考

以下列出所有可通过命令行直接调用的脚本及其参数。

### safe_io — 标准化文件 IO

**已有 API 文档：** 见上文 [safe_io](#safe_io) 章节。

**CLI 子命令：**

```bash
# 读取文件（输出到 stdout 或指定文件）
python scripts/safe_io.py read --file <path> [--output <path>]

# 写入文件（覆盖，默认自动备份）
python scripts/safe_io.py write --file <path> --content "<text>" [--no-backup]
python scripts/safe_io.py write --file <path> --stdin [--no-backup]   # 从 stdin 读取

# 正则替换（默认自动备份）
python scripts/safe_io.py patch-regex --file <path> --pattern "<regex>" --replacement "<repl>" [--flags 0] [--no-backup]

# 按行号替换（默认自动备份）
python scripts/safe_io.py patch-line --file <path> --line <N> --content "<text>" [--no-backup]
```

**参数表：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--file` | str | 是 | - | 目标文件路径 |
| `--content` | str | 否 | `""` | 写入/替换内容 |
| `--stdin` | flag | 否 | False | 从标准输入读取(与`--content`互斥) |
| `--no-backup` | flag | 否 | False | 跳过自动备份(仅 write/patch-*) |
| `--pattern` | str | 是 | - | 正则表达式模式 |
| `--replacement` | str | 是 | - | 替换字符串 |
| `--flags` | int | 否 | 0 | Python re 标志位 |
| `--line` | int | 是 | - | 目标行号 |
| `--output` | str | 否 | stdout | 输出文件路径(仅 read) |

---

### permission_checker — 权限检查器

**已有 API 文档：** 见上文 [permission_checker](#permission_checker) 章节。

**CLI 用法：**

```bash
# 基础扫描
python scripts/permission_checker.py <skill_dir>

# 详细日志 + JSON 报告导出
python scripts/permission_checker.py <skill_dir> --verbose --output report.json
```

**参数表：**

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `skill_dir` | str(位置) | 是 | - | 技能根目录路径 |
| `--verbose` / `-v` | flag | 否 | False | 输出详细扫描日志 |
| `--output` / `-o` | str | 否 | None | JSON 报告输出路径 |

**Python API：**

```python
from permission_checker import PermissionChecker
checker = PermissionChecker('/path/to/skill', verbose=False)
report = checker.generate_report()  # 等价于 checker.scan()
# report = { 'risk_level': 'LOW', 'stats': {...}, 'findings': [...] }
```

---

### skill_audit.fix — 统一修复工具

**功能：** 为全部23条审计规则(R-01~R-26)提供针对性修复函数。`apply_fix()` 是统一入口。

**Python API（无独立 CLI）：**

```python
from skill_audit.fix import apply_fix, list_fixable

# 查看所有可修复的 key
keys = list_fixable()

# 修复单个规则
n = apply_fix('/path/to/skill', 'name', value='my-skill')          # R-01
n = apply_fix('/path/to/skill', 'version', value='1.2.3')          # R-04
n = apply_fix('/path/to/skill', 'sensitive_access', value=True)    # R-13
n = apply_fix('/path/to/skill', 'artifact_paths', violations=[...]) # R-11
```

**fix_key -> 规则映射表：**

| fix_key | 规则 | 修复行为 | 常用参数 |
|---------|------|----------|----------|
| `name` | R-01 | 添加/更正 name | value="技能名" |
| `description` | R-02 | 添加/更正 description | value="描述" |
| `author` | R-03 | 添加 author | value="作者名" |
| `version` | R-04 | 更正版本号格式 | value="1.2.3" |
| `skill_macro` | R-05 | 添加 skill_macro | value="unified" |
| `h1` | R-26 | 添加一级标题 | value="标题" |
| `section_trigger` | R-07 | 添加触发场景章节 | - |
| `section_core` | R-08 | 添加核心能力章节 | - |
| `section_workflow` | R-09 | 添加工作流程章节 | - |
| `home_url` | R-10 | 添加 home_url | value="URL" |
| `artifact_paths` | R-11 | 迁出违规文件 | violations=[...] |
| `external_data_dir` | R-12 | 统一数据目录路径 | - |
| `sensitive_access` | R-13 | 敏感访问声明 | value=True/False |
| `critical_write` | R-14 | 关键写入声明 | value=True/False |
| `create_permissions_md` | R-15 | 创建权限说明文档 | - |
| `permission_weight` | R-16 | 权限权重说明 | value="LOW/MEDIUM/HIGH/CRITICAL" |
| `progressive_loading` | R-17 | 渐进加载拆分 | - |
| `antipattern_progressive` | R-18 | 反模式到 references/ | - |
| `faq_progressive` | R-19 | FAQ 到 references/ | - |
| `writing_standards` | R-20 | 写作规范自动更正 | - |
| `progressive_loading_explicit` | R-21 | 渐进加载显式声明 | - |
| `data_dir_compliance` | R-22 | 数据目录规范修复 | dry_run=True/False |
| `doc_code_consistency` | R-23 | 文档-代码一致性 | - |

---

### progress_manager — 过程管理

**功能：** 读写 `.standardization/<skill>/.progress.md`，追踪审计执行进度。仅在审计结束后一次性更新，不逐条写入。

**Python API（无独立 CLI）：**

```python
from progress_manager import (
    create_progress,
    update_progress_from_audit,
    finalize_progress,
    load_progress,
    format_progress_markdown,
)

data_dir = 'skills/.standardization/my-skill'

# 创建进度文件
create_progress(data_dir, mode='update')

# 审计后更新进度
update_progress_from_audit(data_dir, audit_result)

# 写入最终结果
finalize_progress(data_dir, audit_result)

# 读取当前进度（用于断点续传）
progress = load_progress(data_dir)
# {'R-01': {'passed': True, 'detail': '...'}, 'R-02': {...}, ...}

# 格式化进度条
md = format_progress_markdown(data_dir)
# '**进度**：`████████░░░░░░░░░░░░` 16/24 通过（8 失败）'
```

---

### permission_checks — 权限检查函数集

**功能：** R-13~R-26 权限相关规则的检查函数。被 audit 引擎调用，无独立 CLI。

**Python API：**

```python
from skill_audit.permission_checks import (
    check_sensitive_access_declaration,    # R-13
    check_critical_write_declaration,      # R-14
    check_authorization_present,           # R-15
    check_permission_weight_explained,     # R-16
    check_progressive_loading_forced,      # R-17
)

# 每个函数接收统一签名
result = check_sensitive_access_declaration(
    filepath='SKILL.md',
    content=full_text,
    fm=frontmatter_dict,
    body=body_text,
    skill_dir='/path/to/skill'
)
# result = {'passed': bool, 'detail': str, 'fix': {...} (可选), 'skip': bool (可选)}
```


---

## 内部模块速查表

以下模块被 audit 引擎（`skill_audit` / `skill_builder`）内部调用，通常不需要直接 CLI 调用。
在排查审计故障或定制检查逻辑时按需查阅。

| 模块 | 所属包 | 职责 | 关键函数 |
|------|--------|------|----------|
| `artifact_checker.py` | skill_audit | R-11 产出物路径检查 + 修复 | `check_artifact_paths()`, `fix_external_data_dir()` |
| `data_dir_checker.py` | skill_audit | R-22 数据目录规范检查 + 修复 | `check_data_dir_compliance()`, `fix_data_dir_compliance()` |
| `structure_checker.py` | skill_audit | 技能目录结构完整性检查 | `check_structure()` |
| `frontmatter_checker.py` | skill_audit | Frontmatter 字段验证（R-01~R-26） | `check_frontmatter()` |
| `fix.py` | skill_audit | 统一修复分发（R-01~R-26） | `apply_fix()`, `list_fixable()` — 见 [skill_audit.fix](#skill_auditfix-统一修复工具) |
| `permission_checks.py` | skill_audit | R-13~R-26 权限检查函数 | 见 [permission_checks](#permission_checks-权限检查函数集) |
| `report_generator.py` | skill_audit | 审计报告生成（text/json/html） | `generate_report()` |
| `utils.py` | skill_audit | `parse_simple_yaml_frontmatter()` 等工具函数 | `parse_simple_yaml_frontmatter()` |
| `creator.py` | skill_builder | Create 模式标准化流程 | `standardize_create()` |
| `updater.py` | skill_builder | Update 模式标准化流程 | `standardize_update()` |
| `migrator.py` | skill_builder | Refactor 模式迁移流程 | `standardize_refactor()` |
| `version_manager.py` | skill_builder | 版本号检测与升级策略 | `detect_version()`, `upgrade_version()` |

### 调用关系

```
skill_builder
  ├─ creator / updater / migrator  (模式路由)
  └─ version_manager               (版本管理)
skill_audit
  ├─ audit_runner                  (编排25条规则)
  ├─ frontmatter_checker           (R-01~R-26)
  ├─ structure_checker             (R-07~R-26)
  ├─ permission_checks             (R-13~R-26)
  ├─ artifact_checker              (R-11)
  ├─ data_dir_checker              (R-22)
  ├─ fix.py                        (apply_fix分发)
  ├─ report_generator              (输出格式化)
  └─ utils.py                      (通用工具)
permission_checker                 (权限扫描)
progress_manager                   (进度追踪)
safe_io                            (基础设施)
```

## 脚本 CLI 使用参考
以下是 skill-standardization 下所有带命令行接口的脚本的使用说明，按照渐进式加载规范放入本章节，大模型可根据需要加载本章节参考。
---
### scripts/safe_io.py
**功能**: 提供原子化、备份安全的文件读写操作，是所有 .md 文件更新的唯一合规入口。
**子命令**: `read`、`write`、`patch-regex`、`patch-line`
**用法**:
```bash
python scripts/safe_io.py read --file <path> [--output <output_path>]
python scripts/safe_io.py write --file <path> --content "<内容>" [--no-backup]
python scripts/safe_io.py patch-regex --file <path> --pattern "<正则表达式>" --replacement "<替换内容>" [--flags 0] [--no-backup]
python scripts/safe_io.py patch-line --file <path> --line <行号> --content "<内容>" [--no-backup]
```
**参数说明**:
| 子命令 | 参数 | 说明 | 必需 | 默认值 |
|---------|------|------|------|--------|
| 通用 | `--file` | 目标文件路径 | 是 | — |
| `read` | `--output` | 输出文件路径（默认 stdout） | 否 | stdout |
| `write` | `--content` | 要写入的内容 | 是 | — |
| `write` | `--no-backup` | 跳过自动备份 | 否 | `False` |
| `patch-regex` | `--pattern` | 正则表达式模式 | 是 | — |
| `patch-regex` | `--replacement` | 替换字符串 | 是 | — |
| `patch-regex` | `--flags` | 正则标志位 | 否 | 0 |
| `patch-regex` | `--no-backup` | 跳过自动备份 | 否 | `False` |
| `patch-line` | `--line` | 目标行号 | 是 | — |
| `patch-line` | `--content` | 替换后的行内容 | 是 | — |
| `patch-line` | `--no-backup` | 跳过自动备份 | 否 | `False` |
**示例**:
```bash
python scripts/safe_io.py read --file SKILL.md
python scripts/safe_io.py write --file test.md --content "# 测试内容"
python scripts/safe_io.py patch-regex --file SKILL.md --pattern "version: .*" --replacement "version: 2.38.8"
python scripts/safe_io.py patch-line --file SKILL.md --line 5 --content "version: 2.38.8"
```
---
### scripts/permission_checker.py
**功能**: 扫描技能目录的权限风险，检查敏感访问、关键写入、授权说明等。
**用法**:
```bash
python scripts/permission_checker.py <skill_dir> [--verbose] [--output <report_path>]
```
**参数说明**:
| 参数 | 说明 | 必需 | 默认值 |
|------|------|------|--------|
| `skill_dir` | 目标技能根目录路径 | 是 | — |
| `--verbose` / `-v` | 输出详细扫描日志 | 否 | `False` |
| `--output` / `-o` | 扫描报告输出路径（JSON 格式） | 否 | stdout |
**示例**:
```bash
python scripts/permission_checker.py .
python scripts/permission_checker.py . --verbose --output permission_report.json
```
---
### scripts/progress_manager.py
**功能**: 管理审计进度，支持创建进度文件、更新进度、加载进度、格式化进度条（无独立 CLI，仅作为 API 供其他脚本调用）。
**Python API 示例**:
```python
from progress_manager import create_progress, update_progress, load_progress, format_progress

create_progress('.standardization/skill-standardization')
update_progress('.standardization/skill-standardization', audit_result)
progress = load_progress('.standardization/skill-standardization')
print(format_progress('.standardization/skill-standardization'))
```
---
### scripts/skill_audit/fix.py（通过 `audit --fix` 调用）
**功能**: 统一修复入口，根据审计结果自动修复可修复的规则违规（覆盖 R-01~R-26）。
**调用方式**: `python -m scripts.skill_audit audit <skill-dir> --fix`
或使用子命令: `python -m scripts.skill_audit fix <skill_dir> --key <fix_key>`
**用法**:
```bash
python -m scripts.skill_audit audit <skill-dir> --fix
python -m scripts.skill_audit fix <skill_dir> --key R-11
```
**参数说明**:
| 命令 | 参数 | 说明 | 必需 | 默认值 |
|---------|------|------|------|--------|
| `audit --fix` | `skill-dir` | 目标技能根目录路径 | 是 | — |
| `audit --fix` | `--fix` | 自动修复可修复规则 | 是 | off |
| `fix` | `skill_dir` | 目标技能根目录路径 | 是 | — |
| `fix` | `--key` | 要修复的 fix key | 是 | — |
| `fix` | `--dry-run` | 仅模拟不更新 | 否 | false |
---
### scripts/skill_audit/fix.py
**功能**: 规则级修复函数库，提供每个规则（R-01~R-26）的独立修复函数，供 `audit --fix` 或 `audit fix` 子命令调用。
**Python API 示例**:
```python
from skill_audit.fix import apply_fix, list_fixable_rules

fixable = list_fixable_rules()
apply_fix('.', 'R-11', violations=[{'file': 'scripts/foo.py', 'reason': '临时脚本'}])
apply_fix('.', 'R-13', sensitive_access=True)
```
---
### scripts/skill_audit/artifact_checker.py
**功能**: 检查产出物路径合规性（R-11），确保仅 SKILL.md、_meta.json、scripts/、references/ 出现在根目录。
**Python API 示例**:
```python
from skill_audit.artifact_checker import check_artifacts

result = check_artifacts('.')
# {'passed': True, 'violations': [], 'details': '...'}
```
---
### scripts/skill_audit/data_dir_checker.py
**功能**: 检查数据目录合规性（R-12），确保外部数据目录路径统一为 `.standardization/<skill>/`。
**Python API 示例**:
```python
from skill_audit.data_dir_checker import check_data_dir

result = check_data_dir('.')
# {'passed': True, 'issues': [], 'details': '...'}
```
---
