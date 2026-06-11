# latex-modular 架构说明 v1.3.0

## 模块划分

```
latex-modular/
├── SKILL.md                     # 技能入口（219行，≤230行限制）
├── _meta.json                   # 元数据（版本/描述等）
├── scripts/                     # Python 脚本（14 个）
│   ├── safe_write.py           # 原子写入 + 安全删除
│   ├── extract.py              # 从 LaTeX 源文件提取组件
│   ├── compose.py              # 模块组合引擎
│   ├── validate.py             # 编译验证器（lualatex/xelatex/pdflatex）
│   ├── refactor.py            # 重构引擎（.tex → 模块化结构）
│   ├── template.py            # 模板库管理（加载/保存/注入）
│   ├── component_manager.py    # 组件库管理（增删改查）
│   ├── component_inject.py    # 增量注入（向现有 .tex 插入组件）
│   ├── convert.py             # 引擎转换（pdfLaTeX → LuaLaTeX）
│   ├── workflow_router.py     # 语义路由（分析输入 → 匹配流程线）
│   ├── workflow_state.py      # 流程守卫（步骤依赖检查 + 状态持久化）
│   ├── workflow_report.py     # 结构化报告（Markdown 表格）
│   ├── write_guard.py         # 写入守卫（AST 扫描直接 open() 'w'）
│   └── update_frontmatter.py  # 更新 SKILL.md frontmatter
├── scripts/components/         # 组件库（13 个组件）
│   ├── manifest.json          # 组件索引
│   ├── body.txt               # 正文模板（含 __AUTHOR__/__TITLE__ 占位符）
│   ├── preamble/              # 导言区组件（class-settings, packages）
│   ├── environments/          # 自定义环境（mylist, mycolumns, abstract-env）
│   ├── commands/              # 自定义命令（title-commands, background）
│   ├── styles/                # 样式配置（section-style, toc-style, header-footer）
│   ├── tables/                # 表格模板（table-style）
│   └── graphics/              # 图片模板（figure-insert）
├── scripts/templates/          # 模板库（JSON 格式，3 个）
│   ├── article.json           # 学术论文模板
│   ├── report.json            # 技术报告模板
│   └── my-template.json       # 用户自定义模板
└── references/                # 渐进式加载参考文档（7 个）
    ├── guide.md                # 完整使用指南 + 快速用例
    ├── architecture.md         # 本文件
    ├── antipatterns.md         # 反模式手册
    ├── faq.md                 # 常见问题
    ├── changelog.md          # 版本更新记录
    ├── component-spec.md     # 组件规范
    └── permissions.md        # 权限说明
```

## 核心模块说明

### 1. safe_write.py（原子写入工具）

**功能**：所有文件写入操作必须通过此模块，确保 UTF-8 中文编码不损坏。

**核心函数**：
- `safe_write(filepath, content, encoding="utf-8")` — 原子写入（tmp + os.replace）
- `safe_delete(filepath, backup=True)` — 安全删除（先备份到 .backup/ 再删除）
- `safe_patch_by_line(filepath, line_num, new_line)` — 按行号精确替换
- `safe_patch_regex(filepath, pattern, replacement)` — 正则替换
- `safe_insert_after(filepath, after_pattern, insert_text)` — 在匹配行后插入

**安全保证**：
```
普通 open("w")：      写入中途崩溃 → 文件半截损坏
safe_write()：        先写 tmp → os.replace 原子交换 → 永不写半截
safe_delete()：       先备份 .backup/ → 再 unlink → 可回滚
```

### 2. extract.py（组件提取器）

**功能**：从已有 LuaLaTeX 源文件提取组件到模块化库。

**提取规则**：按正则模式匹配，将导言区内容分类到不同组件文件（documentclass / usepackage / 字体 / 命令 / 环境 / 样式 / 页眉页脚）。

**输出**：
- `scripts/components/manifest.json` — 组件索引
- `scripts/components/<category>/<name>.txt` — 各组件文件

### 3. compose.py（组合引擎）

**功能**：按依赖顺序组合组件，生成完整可编译的 .tex 文件。

**组合顺序**：
1. 文档类声明（`\documentclass`）
2. 宏包引入（自动去重 + 按 `PACKAGE_ORDER` 排序）
3. 颜色定义（`xcolor`）
4. 字体配置（`fontspec`、`ctex`）
5. 页面配置（`geometry`）
6. 作图支持（`pgfplots`、`tikz`）
7. 自定义环境（`\NewDocumentEnvironment`）
8. 自定义命令（`\newcommand`）
9. 章节样式（`\ctexset`）
10. 目录样式（`tocloft`）
11. 页眉页脚（`fancyhdr`）
12. 正文内容（`\begin{document}` ... `\end{document}`）

**宏包排序**：字体 → 版式 → 颜色/图形 → 作图 → 列表/分栏 → 表格 → 其他

### 4. validate.py（编译验证器）

**功能**：编译 .tex 文件，解析错误并给出修复建议。

**验证流程**：
1. 查找引擎路径（`find_engine()` — 见下方引擎查找）
2. 执行编译（`compile_tex()`，超时 120 秒）
3. 解析错误和警告（`parse_errors_and_warnings()`）
4. 尝试自动修复（`attempt_auto_fix()`，可选）
5. 打印报告（`print_report()`）

**支持的引擎**：lualatex / xelatex / pdflatex（通过 `--engine` 切换）

### 5. refactor.py（重构引擎）

**功能**：将原始 LaTeX 代码重构进模块化体系，保留原文语义。

**重构流程**：
1. 读取源文件 → 2. 分割为导言区和正文区 → 3. 分类到模块 → 4. 保存到 `scripts/components/` → 5. 生成模块化主文档（`\input{}` 引入组件）→ 6. 编译验证

### 6. template.py（模板库管理）

**功能**：JSON 格式模板库，支持加载/保存/搜索/注入参数。

**子命令**：
- `--template xxx` — 按名加载模板
- `--list-templates` — 列出所有模板
- `--save-as xxx` — 保存自定义模板
- `--author` / `--title` — 参数注入
- `--validate` / `--skip-validation` — 编译控制

**内置模板**：article（学术论文）、report（技术报告）

### 7. component_inject.py（增量注入）

**功能**：向现有 .tex 文件中增量插入组件，不破坏用户原有内容。自动拆分组件的导言区（追加到目标导言区）和正文（插入到指定位置）。

**参数**：
- `--after` / `--before` / `--replace` — 正则定位
- `--at-begin-document` / `--at-end-document` — 锚点定位
- `--engine auto` — 自动检测目标文档引擎
- `--lines START-END` — 大文件局部处理

### 8. convert.py（引擎转换）

**功能**：将完整的 pdfLaTeX 文档转换为 LuaLaTeX 兼容语法。原文件不动，输出新文件 + 转换报告。

**转换规则**：
- 删除 `inputenc` / `fontenc`（LuaLaTeX 不需要）
- `CJKutf8` → `ctex`
- `times` / `helvet` / `courier` → `fontspec`（注释掉，留用户决定）
- 删除 dvips / dvipdfmx 等驱动选项
- 标记 EPS / `\special` 等需人工确认项

### 9. workflow_router.py（语义路由）

**功能**：分析用户自然语言输入，自动匹配 4 条流程线之一或独立模式。

**三层结构**：
1. 路由分析 — 关键词匹配 → 输出流程线 + 参数
2. 验证钩子 — 检查路由与输入语义的一致性，低置信度 + 冲突时降级为独立模式
3. 文件大小钩子 — 自动检测源文件体积，>2MB 强制 `--lines`

### 10. workflow_state.py（流程守卫）

**功能**：四套流程线的步骤状态追踪与前置依赖检查。

| 流程线 | 步骤链 |
|--------|--------|
| line1 新建 | template → inject_params → compose → validate → report |
| line2 改造 | backup → convert → branch → final_validate → report |
| line3 增量 | backup → inject → final_validate → report |
| line4 复用 | extract → compose → template → reuse → final_validate → report |
| standalone | execute → final_validate → report |

状态持久化在 `.standardization/latex-modular/data/workflow_state/`。

### 11. workflow_report.py（结构化报告）

**功能**：按流程线类型生成 Markdown 表格报告，内容因流程而异（Line 1 含模板/作者/标题，Line 2 含源文件/备份/分支/输出路径等）。

### 12. write_guard.py（写入守卫）

**功能**：AST 静态分析扫描脚本中的直接 `open() 'w'` / `os.remove()` / `os.unlink()` 调用，作为流程前置钩子使用。

## 数据流

### 4 条流程线

```
Line 1 新建:  template → compose → validate → [.tex + .pdf] + report
Line 2 改造:  [pdfLaTeX] → convert → [LuaLaTeX .tex] → 输出/入库/都要 → validate → report
Line 3 增量:  [已有 .tex] → inject 组件 → validate → [原文件 + 新内容] + report
Line 4 复用:  extract → [组件库] → compose → template → [下次复用] → validate → report
```

### 引擎查找策略（find_engine）

```
传入完整路径 → Windows 注册表 → 系统/用户安装路径
→ TeX Live 最近 5 年版本扫描 → where/which PATH → 安装指引
```

## 依赖

- Python 3.11+（推荐 3.13.12 managed）
- LuaLaTeX（默认）/ XeLaTeX（`--engine xelatex` 切换）/ pdfLaTeX（inject 模式动态转换）
- 中文字体：SimSun / SimHei / KaiTi / FangSong（Windows 系统自带）

## 编码规范

- 所有 `.md` 文件：UTF-8（必须用 `safe_write.py` 写入，禁止直接用 Write/Edit 工具）
- 所有 `.tex` 文件：UTF-8（LaTeX 侧用 `ctex` 或 `fontspec`）
- 所有 `.py` 文件：UTF-8（Python 侧用 `encoding="utf-8"` 打开文件）
