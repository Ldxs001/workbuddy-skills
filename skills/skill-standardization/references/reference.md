# API / 命令参考

> 本文件为 skill-standardization v2 的完整命令参考手册。
> 涵盖所有 CLI 工具的参数、返回值、错误码及配置项。

---

## 目录

1. [skill_builder — 构建器](#skill_builder)
2. [skill_audit — 审查器](#skill_audit)
3. [json_loader.py — 规范加载器](#json_loaderpy)

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
| `--backup` | flag | ❌ | `False` | 修改前自动备份 |

**检查项目（共 6 项）：**

| # | 检查项 | 自动修复？ | 说明 |
|---|--------|-----------|------|
| 1 | `_meta.json` 存在性 + 五字段完整 | ✅ --fix | 缺失字段自动补充空值 |
| 2 | `_meta.json` JSON 合法性 | ❌ | 格式错误仅警告 |
| 3 | `SKILL.md` 存在性 + frontmatter | ❌ | 需手动编辑 |
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
   ⚠️  SKILL.md 共 250 行，超过 200 行建议拆分到 references/

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
> 用途：基于 R-01~R-17 规则对 SKILL.md 进行自动化审查

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

**审查规则一览（共 17 条）：**

| ID | 级别 | 名称 | 检查内容 |
|----|------|------|----------|
| R-01 | ERROR | Frontmatter 存在性 | 文件以 `---` 开头且有闭合 |
| R-02 | ERROR | name 字段 | frontmatter 包含 `name:` |
| R-03 | ERROR | version SemVer | 版本号匹配 `\d+\.\d+\.\d+(-\w+)?` |
| R-04 | ERROR | description 字段 | frontmatter 包含 `description:` |
| R-05 | WARN | name 与目录名一致 | `name == 父目录名` |
| R-06 | WARN | 正文含一级标题 | 有 `# ` 开头的行 |
| R-07 | ERROR | 触发条件章节（合规） | 含正向触发词≥3个、否定条件≥1个，无「自动执行」等危险表述 |
| R-08 | WARN | 核心能力章节 | 匹配核心能力同义词 |
| R-09 | WARN | 工作流程章节 | 匹配工作流程同义词 |
| R-10 | ERROR | version 一致性 | SKILL.md version == _meta.json version |
| R-11 | ERROR | 产出物路径规范性 | 产出物路径符合 skills/.standardization/<skill>/ 规范，且无路径遍历、跨目录写入、敏感信息泄露风险 |
| R-12 | ERROR | 外部数据目录规范性 | 外部数据目录路径符合 skills/.standardization/<skill-name>/ 约定，_meta.json 含 data_dir 字段且一致，且无数据泄露风险 |
| R-13 | ERROR | 敏感信息访问声明 | 脚本含敏感信息访问（memory/credentials/token）时，frontmatter 须声明 sensitive_access: true 并说明用途 |
| R-14 | ERROR | 关键位置写入声明 | 脚本含关键位置写入（skills/.workbuddy/系统目录）时，frontmatter 须声明 critical_write: true 并说明用途 |
| R-15 | ERROR | 高权限操作授权检查 | 脚本含文件删除/网络请求/subprocess 调用时，执行前须调用 authorization_manager.py 请求用户授权 |
| R-16 | WARN | 权限权重说明 | 建议在 SKILL.md 或 references/ 中说明各操作的权限权重，便于审查时评估风险 |
| R-17 | ERROR | 渐进加载引用（强制） | SKILL.md > 200 行时必须拆分到 references/，并通过「→ 详见 references/xxx.md」引用 |
| R-18 | WARN | 反模式具体性 | 正文含 ## 反模式/常见错误 章节，且每条反模式含具体描述（≥20字）或代码示例 |
| R-19 | WARN | FAQ 有意义性 | 正文含 ## FAQ/常见问题 章节，且 Q&A 对有意义（Q≥10字，A≥15字） |
| R-20 | WARN | 写作规范（术语一致/无模糊表述/中英文混排） | 正文术语一致、无模糊表述（可能/应该/大概）、中英文混排有空格 |

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

## json_loader.py

> 路径：`scripts/json_loader.py`
>
> 用途：按需加载 spec/ 下的 JSON 规范定义

### load 子命令

加载指定模块的规范定义并打印到标准输出。

**语法：**
```bash
python -m json_loader load <module_name>
```

**可用模块：**

| module_name | 对应文件 | 内容概述 |
|-------------|---------|----------|
| `frontmatter` | `spec/frontmatter.json` | Frontmatter 字段定义（3必须+7可选） |
| `body` | `spec/body.json` | 正文章节规范（5必须+4推荐+N可选） |
| `rules` | `spec/rules.json` | 审查规则 R-01~R-10 完整定义 |
| `structure` | `spec/structure.json` | 目录结构规范（三级复杂度+迁移规则） |
| `progressive_md` | `spec/progressive_md.json` | 渐进式MD体系（拆分边界+加载协议+文件映射） |
| `all` | *全部* | 加载所有模块的合并视图 |

### list 子命令

列出所有可用模块及其状态。

```bash
python -m json_loader list
```

### show 子命令

显示模块的详细元信息（版本、依赖等）。

```bash
python -m json_loader show <module_name>
```

### refs 子命令

查看模块间的引用关系图。

```bash
python -m json_loader refs
```

---

## 错误码总表

| 工具 | 退出码 | 含义 |
|------|--------|------|
| skill_builder | `0` | 成功 |
| skill_builder | `1` | 参数错误/目录已存在/不存在 |
| skill_audit | `0` | 审查完成（默认模式） |
| skill_audit | `1` | 严格模式下有 ERROR（--strict） |
| json_loader | `0` | 成功 |
| json_loader | `1` | 模块不存在/文件读取失败 |

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
python -m permission_checker.py ~/.workbuddy/skills/my-skill --json
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
| 关键位置写入 | 30% | 写入 skills/.workbuddy/系统目录 |
| 网络访问 | 20% | 发起 HTTP 请求 |
| 文件删除 | 10% | 删除文件或目录 |

---

## authorization_manager.py

> 路径：`scripts/authorization_manager.py`
>
> 用途：管理高权限操作的授权请求和检查

### 基本用法

```bash
# 请求统一审批（累积多个操作）
python -m authorization_manager.py request --type batch \
  --operations '[{"type":"delete","file":"/path/to/file"},...]' \
  --skill-dir <skill-dir>

# 请求即时审批（单个高风险操作）
python -m authorization_manager.py request --type immediate \
  --operation '{"type":"delete","file":"/path/to/file"}' \
  --reason "需要删除临时文件" \
  --skill-dir <skill-dir>

# 检查是否已授权
python -m authorization_manager.py check \
  --operation '{"type":"delete","file":"/path/to/file"}' \
  --skill-dir <skill-dir>

# 列出待审批操作
python -m authorization_manager.py list --skill-dir <skill-dir>

# 审批（通过/拒绝）
python -m authorization_manager.py approve <request-id> [--approve|--reject]
```

### AI 调用示例

在 skill 脚本中调用授权管理器：

```python
import subprocess
import sys

def request_authorization(operation, reason):
    """请求用户授权（即时审批）"""
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "authorization_manager.py"),
            "request",
            "--type", "immediate",
            "--operation", json.dumps(operation, ensure_ascii=False),
            "--reason", reason,
            "--skill-dir", skill_dir,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        response = json.loads(result.stdout)
        return response.get("approved", False)
    return False

# 使用示例
if request_authorization(
    {"type": "delete", "file": "/path/to/temp.txt"},
    "需要删除临时文件"
):
    os.remove("/path/to/temp.txt")
else:
    print("❌ 用户未授权，跳过删除操作")
```

---

## 版本号更新文件映射表

| 修改类型 | 需同步版本号的文件位置 | 升级类型 |
|---------|----------------------|---------|
| 修正错别字/排版（仅 SKILL.md） | SKILL.md `version` + `_meta.json` `"version"` | PATCH（2.1.0→2.1.1） |
| 修改 `scripts/spec/*.json` 规范 | 对应 `.json` 的 `"_version"` + SKILL.md + `_meta.json` | PATCH 或 MINOR（视变更范围） |
| 修改 `scripts/*.py` 脚本逻辑 | `.py` 文件头版本字符串 + SKILL.md + `_meta.json` | MINOR（2.1.0→2.2.0） |
| 新增功能/新脚本 | 所有上述文件 + `manifest.json`（上传时同步） | MINOR 或 MAJOR |
| 仅改 `references/*.md` | 视情况——内容影响功能时升 SKILL.md + `_meta.json` | 通常 PATCH |
| git-sync 上传成功后 | `manifest.json` 由 git-sync 自动更新 | 跟随 SKILL.md 版本 |

**关键原则：**

- 本地修改只改 SKILL.md + _meta.json + 受影响的脚本/json 文件内的版本字符串
- `manifest.json` 由 git-sync 上传流程负责，本地不应擅改
- **不确定是否升级版本号时，必须询问用户**（适用于所有上述文件类型）
