---
name: latex-modular
data_dir: ../.standardization/latex-modular/data
version: 1.2.1
author: wUwproject
license: MIT
description: LaTeX 模块化组合技能。提取 LaTeX 文档头/组件（表格、图片、列表、章节样式）作为可组合模块，通过 Python 脚本稳定组合生成不报错的 lualatex 文档，支持从原始 LaTeX 代码重构进模块化体系。
tags: ['latex', 'modular', 'template', 'luatex', 'xelatex', 'document-generation', 'refactor']
trigger: ['latex-modular', 'latex 模块化', '模块化模板', 'LaTeX 文档 模块化']
trigger_negative: false
external_data_dir: false
sensitive_access: false
critical_write: false
permission_weight: LOW
h1_position: true
meta_field_sync: true
---
# latex-modular

## 触发场景

### 文件更新约束

> **本技能的 `.md` 文件禁止使用 Write/Edit 工具更新。**
> 必须用 `scripts/` 下的 Python 脚本原子写入（`tmp + os.replace()`）。

| 文件 | 更新方式 | 脚本 |
|------|----------|--------|
| `SKILL.md` frontmatter | Python 原子写入 | `scripts/update_frontmatter.py` |
| `SKILL.md` 正文 | Python 直接重建 | `scripts/safe_write.py` 的 `safe_write()` |
| `scripts/components/*.tex` | Python 写入 | `scripts/component_manager.py` |
| `references/*.md` | `scripts/safe_write.py` | 随技能自带 |

- [把这段 LaTeX 做成模块化模板]
- [生成一个 LaTeX 文档，用模块化方式]
- [重构这个 LaTeX 代码进模块化体系]
- [提取 LaTeX 的组件，做成可复用模块]
- [用 latex-modular 生成一个...文档]
- [验证这段 LaTeX 能不能编译通过]

**不触发**：
- 用户只是问 [LaTeX 怎么写]——这是闲聊
- 用户要求直接编辑 .tex 文件而不使用模块化方式

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

- **extract 模式** — 从已有 LaTeX 代码中提取文档头、宏包、自定义命令、环境、样式，保存为可复用组件
- **compose 模式** — 通过 Python 脚本按模块组合生成完整 LaTeX 文档，确保编译无错误
- **refactor 模式** — 将原始 LaTeX 代码重构进模块化体系，保留原文语义，按模块拆分存储
- **validate 模式** — 使用 lualatex 编译验证生成的 .tex 文件，报告错误并返回修复建议
- **template 模式** — 模板库+自定义保存+内容注入。支持 `--template` 按名加载、`--save-as` 保存自定义模板、`--content` 注入正文、`--list-templates` 等，内置 article/report 两种预设模板（`scripts/template.py` + `scripts/templates/`）

### 渐进式文件索引

| 文件 | 位置 | 说明 |
|------|------|------|
| `references/guide.md` | 使用指南 | 完整使用指南（触发词、工作流程、输出格式） |
| `references/architecture.md` | 架构说明 | 内部架构（组件分类、组合引擎、验证器） |
| `references/antipatterns.md` | 反模式 | 常见 LaTeX 错误 + 正确做法 |
| `references/faq.md` | FAQ | 常见问题解答（宏包冲突、字体问题、编译错误） |
| `references/changelog.md` | 更新日志 | 版本更新记录 |
| `references/component-spec.md` | 组件规范 | 命名、参数、依赖声明 |

### 脚本工具

| 脚本 | 功能 |
|------|------|
| `scripts/compose.py` | 模块组合引擎，按依赖顺序组合组件 |
| `scripts/extract.py` | 从 LaTeX 源文件提取组件 |
| `scripts/validate.py` | 编译验证，调用 lualatex 并检查输出 |
| `scripts/refactor.py` | 重构引擎，将原始 LaTeX 转为模块化结构 |
| `scripts/template.py` | 模板库管理：`--template` 加载、`--save-as` 保存、`--content` 注入、`--list-templates` 等 |
| `scripts/component_manager.py` | 组件库管理（增删改查） |
| `scripts/safe_write.py` | 原子写入工具（tmp + os.replace）|
| `scripts/update_frontmatter.py` | 更新 SKILL.md frontmatter |

### 依赖

- Python 3.11+（推荐 3.13.12 managed）
- **lualatex**（默认，推荐）：`/c/Program Files/MiKTeX/miktex/bin/x64/lualatex`
- 也可通过 `--engine xelatex` 切换为 **xelatex**
- 不推荐 pdflatex
- **首次编译**时 MiKTeX 会自动安装缺失宏包，可能需要等待
- 中文字体依赖：SimSun、SimHei、KaiTi、FangSong（Windows 系统自带）

## 工作流程

### extract 模式（提取组件）

1. 读取用户提供的 LaTeX 源文件
2. 解析文档结构：导言区（\\documentclass 到 \\begin{document}）、正文区
3. 提取组件并分类保存到 `scripts/components/`：
   - `preamble/*.tex` — 宏包引入、颜色定义、字体设置
   - `environments/*.tex` — 自定义环境（mylist、mycolumns 等）
   - `commands/*.tex` — 自定义命令（\\timu、\\seeref 等）
   - `styles/*.tex` — 章节样式、目录样式、页眉页脚
   - `tables/*.tex` — 表格样式模板
   - `graphics/*.tex` — 图片插入模板
4. 生成组件索引 `scripts/components/manifest.json`

### compose 模式（组合生成）

1. 读取 `scripts/components/manifest.json` 获取可用组件列表
2. 根据用户需求选择所需组件
3. 调用 `scripts/compose.py` 按正确顺序组合：
   - 第1层：文档类声明
   - 第2层：宏包引入（自动去重）
   - 第3层：自定义命令和环境
   - 第4层：样式设置
   - 第5层：文档正文（用户提供）
4. 输出完整 .tex 文件

### 组件库结构

```
scripts/components/
├── manifest.json          # 组件索引
├── preamble/              # 导言区组件
│   ├── class-settings.tex
│   ├── packages.tex
│   ├── colors.tex
│   └── fonts.tex
├── environments/          # 自定义环境
│   ├── mylist.tex
│   ├── mycolumns.tex
│   └── abstract-env.tex
├── commands/              # 自定义命令
│   ├── title-commands.tex
│   ├── ref-commands.tex
│   └── font-commands.tex
├── styles/                # 样式设置
│   ├── section-style.tex
│   ├── toc-style.tex
│   └── header-footer.tex
├── tables/                # 表格模板
│   ├── standard-table.tex
│   └── multirow-table.tex
└── graphics/              # 图片模板
    ├── figure-insert.tex
    └── background.tex
```

### refactor 模式（重构）

1. 读取原始 LaTeX 文件
2. 解析并提取各组件到 `scripts/components/` 对应目录
3. 生成模块化版本的主文档（使用 \\input{} 或 \\include{} 引入组件）
4. 验证重构后文档编译通过

### validate 模式（编译验证）

1. 调用 `scripts/validate.py`
2. 使用系统 lualatex 编译 .tex 文件
3. 捕获编译输出，解析错误和警告
4. 返回结构化报告：成功/失败、错误位置、修复建议
