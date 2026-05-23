# API / 命令参考

> 本文件为 skill-standardization v2 的完整命令参考手册。
> 涵盖所有 CLI 工具的参数、返回值、错误码及配置项。

---

## 目录

1. [skill_builder.py — 构建器](#skill_builderpy)
2. [skill_audit.py — 审查器](#skill_auditpy)
3. [json_loader.py — 规范加载器](#json_loaderpy)

---

## skill_builder.py

> 路径：`scripts/skill_builder.py`
>
> 用途：Skill 全生命周期管理（创建/更新/改造）

### create 命令

从模板初始化一个新的标准 skill。

**语法：**
```bash
python scripts/skill_builder.py create <name> [--desc <text>] [--dir <path>] [--tags <tag1,tag2,...>]
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
├── _meta.json        # {name, version: "0.1.0", description, author: "wUwproject", tags}
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
python scripts/skill_builder.py create my-tool --desc "通用工具" --tags tool,utility
```

---

### update 命令

对已有 skill 进行增量规范化检查。

**语法：**
```bash
python scripts/skill_builder.py update <skill_dir> [--fix] [--backup]
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
python scripts/skill_builder.py refactor <skill_dir> [--no-backup] [--dry-run]
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

## skill_audit.py

> 路径：`scripts/skill_audit.py`
>
> 用途：基于 R-01~R-11 规则对 SKILL.md 进行自动化审查

### audit 命令

**语法：**
```bash
python scripts/skill_audit.py audit <skill_dir> [--json] [--strict]
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `<skill_dir>` | positional | ✅ | — | Skill 目录路径 |
| `--json` | flag | ❌ | `False` | 以 JSON 格式输出结果 |
| `--strict` | flag | ❌ | `False` | 严格模式（ERROR 级 exit(1)） |

**审查规则一览（共 11 条）：**

| ID | 级别 | 名称 | 检查内容 |
|----|------|------|----------|
| R-01 | ERROR | Frontmatter 存在性 | 文件以 `---` 开头且有闭合 |
| R-02 | ERROR | name 字段 | frontmatter 包含 `name:` |
| R-03 | ERROR | version SemVer | 版本号匹配 `\d+\.\d+\.\d+(-\w+)?` |
| R-04 | ERROR | description 字段 | frontmatter 包含 `description:` |
| R-05 | WARN | name 与目录名一致 | `name == 父目录名` |
| R-06 | WARN | 正文含一级标题 | 有 `# ` 开头的行 |
| R-07 | WARN | 触发条件章节 | 匹配触发条件同义词 |
| R-08 | WARN | 核心能力章节 | 匹配核心能力同义词 |
| R-09 | WARN | 工作流程章节 | 匹配工作流程同义词 |
| R-10 | WARN | version 一致性 | SKILL.md version == manifest.json version |
| R-11 | WARN | 产出物路径规范性 | scripts/ + 根目录 路径规范 + 全目录交叉引用追踪（铁律4） |

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
python scripts/json_loader.py load <module_name>
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
python scripts/json_loader.py list
```

### show 子命令

显示模块的详细元信息（版本、依赖等）。

```bash
python scripts/json_loader.py show <module_name>
```

### refs 子命令

查看模块间的引用关系图。

```bash
python scripts/json_loader.py refs
```

---

## 错误码总表

| 工具 | 退出码 | 含义 |
|------|--------|------|
| skill_builder.py | `0` | 成功 |
| skill_builder.py | `1` | 参数错误/目录已存在/不存在 |
| skill_audit.py | `0` | 审查完成（默认模式） |
| skill_audit.py | `1` | 严格模式下有 ERROR（--strict） |
| json_loader.py | `0` | 成功 |
| json_loader.py | `1` | 模块不存在/文件读取失败 |

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
