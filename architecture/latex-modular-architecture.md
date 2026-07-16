<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# latex-modular 架构与规范体系文档

> 完整解读 v1.3.0 版的架构设计、七种操作模式、四流程线引擎策略与流程守卫体系
> 生成时间：2026-06-11（v1.3.0 最新更新）

---

## 一、系统概览

latex-modular 是一个 **LaTeX 模块化组合工具集**，围绕以下闭环运行：

```
源文档/模板
  → 拆解（extract/refactor：.tex → 可复用组件）
    → 组件库（13 个组件，JSON 索引）
      → 组合（compose/template：组件 → 新 .tex）
        → 增量编辑（inject：向现有 .tex 插入组件）
          → 引擎转换（convert：pdfLaTeX ↔ LuaLaTeX）
            → 编译验证（validate：lualatex/xelatex/pdflatex）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI | 人类可读文档、命令行交互 |
| **业务层** | 7 种操作模式 + 语义路由 + 流程守卫 | 文档处理、引擎转换、流程编排 |
| **数据层** | scripts/components/ + scripts/templates/ + .standardization/data/ | 组件库、模板库、运行时状态 |

---

## 二、核心模块说明

### 2.1 七种操作模式

| 模式 | 脚本 | 功能 | 输入→输出 |
|------|------|------|----------|
| **extract** | extract.py | 从已有 .tex 拆解出 preamble/commands/environments/styles 等组件 | `.tex` → 组件文件 + manifest |
| **compose** | compose.py | 按 manifest 依赖顺序组合组件，自动去重宏包 | manifest + body → `.tex` |
| **template** | template.py | 模板库加载/保存，支持 --author/--title 参数注入 | 模板名/参数 → `.tex` |
| **validate** | validate.py | lualatex/xelatex/pdflatex 编译 + 错误解析 + 自动修复 | `.tex` → PDF + 编译报告 |
| **refactor** | refactor.py | 完整 .tex → 模块化结构（组件拆分 + `\input` 主文档） | `.tex` → 组件目录 + 主文档 |
| **inject** | component_inject.py | 向现有 .tex 增量插入组件，自动拆分导言区/正文 | `.tex` + 组件 → 原文件增量更新 |
| **convert** | convert.py | pdfLaTeX → LuaLaTeX 全文档转换，原文件不动 | `.tex` → `_lualatex.tex` + 转换报告 |

### 2.2 组件库（13 个）

```
scripts/components/
├── manifest.json          # 组件索引
├── body.txt               # 正文模板（含 __AUTHOR__/__TITLE__）
├── preamble/              # 导言区（class-settings, packages）
├── commands/              # 自定义命令（title-commands, background）
├── environments/          # 自定义环境（mylist, mycolumns, abstract-env）
├── styles/                # 样式（section-style, toc-style, header-footer）
├── tables/                # 表格（table-style）
└── graphics/              # 图片（figure-insert）
```

### 2.3 模板库（3 个）

| 模板 | 类型 | 用途 |
|------|------|------|
| article.json | builtin | 学术论文（摘要、多级标题、列表） |
| report.json | builtin | 技术报告（目录、多级标题、风险评估） |
| my-template.json | custom | 用户自定义 |

### 2.4 语义路由（workflow_router.py）

**职责**：分析用户自然语言输入，自动匹配流程线或独立模式。

**三层结构**：
1. **路由分析** — 关键词匹配 → 输出流程线 + 参数
2. **验证钩子** — 检查路由与输入语义的一致性，低置信度 + 冲突时降级为独立模式
3. **文件大小钩子** — 检测源文件体积，>2MB 强制 `--lines`

### 2.5 流程守卫（workflow_state.py）

**职责**：四套流程线的步骤状态追踪与前置依赖检查。

| 流程线 | 步骤链 | 强制备份 | 强制验证 | 报告 |
|--------|--------|---------|---------|------|
| **line1 新建文档** | template → inject_params → compose → validate → report | ❌ | ✅ | ✅ |
| **line2 改造** | backup → convert → branch → final_validate → report | ✅ 第一步 | ✅ | ✅ |
| **line3 增量编辑** | backup → inject → final_validate → report | ✅ 第一步 | ✅ | ✅ |
| **line4 组件复用** | extract → compose → template → reuse → final_validate → report | ❌ | ✅ | ✅ |

### 2.6 引擎查找策略（find_engine）

```
传入完整路径 → Windows 注册表（HKLM/HKCU）
→ 系统安装路径（%ProgramFiles%）
→ 用户安装路径（%LOCALAPPDATA%）
→ TeX Live 最近 5 年版本扫描
→ where/which PATH 命令
→ 安装指引（官网 + 清华镜像 + 阿里云镜像）
```

---

## 三、数据流

### 四流程线

```
Line 1 新建:  template → compose → validate → [.tex + .pdf] + report
Line 2 改造:  [pdfLaTeX] → convert → [LuaLaTeX .tex] → 输出/入库/都要 → validate → report
Line 3 增量:  [已有 .tex] → inject 组件 → validate → [原文件 + 新内容] + report
Line 4 复用:  extract → [组件库] → compose → template → [下次复用] → validate → report
```

### 引擎支持

| 引擎 | 状态 |
|------|------|
| **LuaLaTeX** | ✅ 默认，组件库原生语法 |
| **XeLaTeX** | ✅ `--engine xelatex` 一键切换，完全兼容 |
| **pdfLaTeX** | 🔧 inject 模式动态转换组件语法；convert 模式整篇转换 |

---

## 五、依赖

- Python 3.11+（推荐 3.13.12 managed）
- LuaLaTeX（默认）/ XeLaTeX（可切换）/ pdfLaTeX（转换目标）
- MiKTeX 或 TeX Live 发行版
- 中文字体：SimSun / SimHei / KaiTi / FangSong（Windows 系统自带）

---

## 六、版本历史

| 版本 | 日期 | 核心变化 |
|------|------|---------|
| 1.3.0 | 2026-06-11 | 新增 inject/convert 模式、语义路由、流程守卫、写入守卫 |
| 1.2.4 | 2026-06-02 | 组件库路径修复、文档规范 |
| 1.0.0 | 2026-05-27 | 初始版本：extract/compose/refactor/validate/template |
