---
name: hug-html
tags: []
version: 3.0.3
author: Ldxs
license: MIT
description: 组件式HTML模块引擎。8种原子组件自由组合 + 3级约束, cell merging, two-level module system (base + composite), 7+ built-in templates, grid-aware visual editor, style presets, post-generation audit, user template save-as, Chinese error handling.
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/hug-html/data/
external_data_dir: true
trigger: 生成 HTML 模板/编辑 HTML/HTML 模块/网格布局/单元格合并/可视化编辑/输出自包含 HTML
trigger_negative: 只是简单文本编辑/不涉及 HTML 生成/使用其他框架
---
# hug-html

> → 详见 `references/antipatterns.md`
> → 详见 `references/faq.md`

## 触发场景

当用户提到以下内容时触发本技能：

- "生成 HTML 模板" / "HTML template" / "hug html"
- "编辑 HTML" / "可视化编辑 HTML" / "visual edit HTML"
- "HTML 模块" / "HTML module library"
- "网格布局" / "grid layout" / "N×M 网格"
- "单元格合并" / "rowspan" / "colspan"
- 输出格式：自包含 HTML 文件（毛玻璃卡片风格）

**复杂需求触发示例**（以下场景同样支持）：
- "我需要一个APP推广卡片，要有个二维码—可以用，支持"
- "帮我做一个带表格和参数配置的HTML面板—支持，用 data-table + param-panel 模块"
- "生成一个双端对比的推广页面—支持，用 header-dual + qr-dual"
- "这个模板我想保存下来以后用—支持，用 --save-as 固化"
- "给我生成的HTML加一个可视化编辑界面—支持，用 visual_editor.py"

**不触发**：
- 用户仅询问 HTML 语法概念，无文件生成需求
- 用户明确请求其他特定技能

## 四层架构（细化）

```
骨架 (Skeleton)
├── 骨架结构 — N×M 网格、行列数、单元格合并(rowspan/colspan)、gap间距
├── 骨架样式 — 底板背景/渐变/透明度、外阴影、外边框、圆角、内外边距
└── 约束模式 — fill(完全贴合) / fit(等比缩放) / clip(裁剪遮挡)

模块 (Module)  ← 组件组合 = {组件声明 + 约束 + 比例} 自由搭配
├── 组件组合 — 8种原子组件自由搭配（text/image/icon/qrcode/table/divider/spacer/group）
├── 组合逻辑 — 方向(row/column)、比例(ratios)、对齐(align/cross_align)
└── 约束传递 — 骨架约束模块 → 模块约束组件（递归）

组件 (Component)  ← 8种原子类型
├── text     — 纯文本（title/body/caption 三种变体）
├── image    — 图片（支持 fit/cover/fill 填充模式）
├── icon     — 图标（FontAwesome / SVG内联）
├── qrcode   — 二维码（API生成）
├── table    — 数据表格（表头+行）
├── divider  — 分割线
├── spacer   — 空白占位
└── group    — 组合容器（递归包含子组件）

基础样式 (Base)
└── CSS原语 — 字体/颜色/渐变/圆角/间距/阴影/边框
```

**编辑粒度**（可视化编辑器内）：
| 可更新 | 不可更新（需改 Grid Spec） |
|--------|---------------------------|
| ✓ 图片内容（点击输入URL / 拖放文件替换） | ✗ 骨架结构（行列数、合并方式、gap） |
| ✓ 基础样式（每个文字元素独立：字体家族/字重/字号/字色） | ✗ 模块结构（组件的HTML骨架） |
| ✓ 模块样式（通过 cell style 覆盖背景色/内边距） | ✗ 骨架样式（底板色/外阴影等） |

**大模型使用流程**（自由生成模式）：
1. 理解用户需求 → 确定骨架结构：几行几列、哪些单元格需要合并
2. 确定约束模式：fill/fit/clip → 决定骨架对模块、模块对组件的约束
3. 描述需要的组件 → 从8种原子组件中自由组合，放入对应骨架位置
4. 配置组合逻辑：方向、比例、对齐方式
5. 生成 HTML → 可直接用 `module_assembler.py` 或自由生成自包含 HTML

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 能力 | 说明 |
|---|------|------|
| 1 | **骨架结构** | N×M 网格、行列数、单元格合并（rowspan/colspan）、gap 间距 |
| 2 | **骨架约束** | 3级约束（fill/fit/clip），递归传递到组件级别 |
| 3 | **组件体系** | 8种原子组件（text/image/icon/qrcode/table/divider/spacer/group），自由组合 |
| 4 | **组合逻辑** | 方向(row/column)、比例(ratios)、对齐(align)、8方向位置 |
| 5 | **方案模板库** | 内置 7+ 预置{骨架+组件+样式}组合 + **用户可自定义固化** |
| 6 | **样式预设** | 5 种内置风格：商务/科研/喜庆/丧事/技术，一键切换配色字体 |
| 7 | **基础编辑** | 每个文字元素独立控制：字体家族(8种)/字重(100-900)/字号(9-48px)/字色/透明度 |
| 8 | **图片编辑** | 点击输入URL + 拖放文件替换，所有图片组件均支持 |
| 9 | **生成后审计** | 自动检查 HTML 结构完整性、标签平衡、图片属性、网格越界、渲染风险 |
| 10 | **统一接口** | `--export-interfaces` 导出完整接口定义 JSON，大模型可直接理解 |
| 11 | **方案模板固化** | `--save-as <名>` 将任意生成固化为用户模板，后续按名引用 |
| 12 | **自由生成模式** | AI 参考组件库，理解需求确定骨架→组合组件→约束→生成→审计 |
| 13 | **向后兼容** | 旧格式 `"module": "composite:xxx"` 仍然支持 |

## 能力边界

> **明确这个技能能做什么、不能做什么，避免使用时"不知道支不支持"。**

### ✅ 支持的场景

| 场景 | 说明 | 示例触发词 |
|------|------|-----------|
| 生成推广卡片 | 应用推广、活动宣传、产品介绍的毛玻璃卡片 | "生成一个APP推广HTML卡片" |
| 生成信息面板 | 带表格、参数、二维码的信息展示面板 | "做一个带二维码和参数描述的HTML" |
| 生成可视化编辑模板 | 带 Ctrl+E 可编辑的 HTML | "生成一个可视化编辑的HTML模板" |
| 生成日历/周历仪表板 | 假日管理、年份控制、工日统计的交互仪表板 | "生成一个周历交互HTML" |
| 生成双端对比卡片 | 左应用右元服务/双实体的对比展示 | "生成一个双端推广卡片" |
| 内容填充 | 自动/手动填充 data-field 标记的文字和图片 | "给这个HTML模板填充示例内容" |
| 方案模板固化 | 将当前设计保存为可复用的用户模板 | "把这个模板保存为 my-card" |
| 自由创作 HTML | AI 参考模块库直接编写自包含 HTML | "帮我写一个毛玻璃风格的首页" |

### ❌ 不支持 / 不适合的场景

| 场景 | 为什么不支持 | 替代方案 |
|------|-------------|---------|
| 复杂前端应用（SPA / 数据可视化大屏） | 本技能面向静态 HTML+CSS 卡片，不支持路由/状态管理/API调用 | 手写 React/Vue 项目 |
| 多页面 HTML 站点 | 本技能是单页面自包含 HTML 生成器，不处理页面间导航 | 手写或使用静态站点生成器 |
| PDF / 图片输出 | 本技能输出 HTML 文件，不直接生成图片或 PDF | 生成 HTML 后用浏览器打印或截图 |
| 外部 CSS/JS 框架集成 | 本技能强调零外部依赖的自包含 HTML | 手动引入 CDN 或在 `scripts` 字段写自定义 JS |
| 非网格布局的自由排版 | 本技能基于 CSS Grid 网格系统，不适合绝对定位的自由排版 | 使用自由生成模式直接手写 HTML |
| 后端交互 / 数据库读写 | 本技能是纯前端 HTML，无后端能力 | 搭配 Node.js / Flask 等后端框架 |

### ⚠️ 需要注意的边界情况

| 情况 | 说明 |
|------|------|
| 网格越界 | 单元格的 row/col 索引 + rowspan/colspan 不能超过网格总行列数，否则 CSS Grid 会异常渲染 |
| 毛玻璃裁剪 | `backdrop-filter` 需要容器有 `overflow:hidden`，否则内容可能被裁剪 |
| JSON 模板路径 | `--spec` 参数支持绝对路径、相对路径和内置模板名；文件不存在会输出中文错误提示 |
| 文件编码 | 所有输入输出文件必须为 UTF-8 编码；其他编码可能导致乱码 |
| 编辑模式兼容性 | Ctrl+E 编辑模式需要现代浏览器（Chrome/Edge/Firefox），不支持 IE |

## 快速开始

```bash
# 列出所有组件类型（v3 新！）
python scripts/module_assembler.py --list-components

# 导出完整的组件接口定义
python scripts/module_assembler.py --export-interfaces "data/output/interfaces.json"

# 生成组件系统演示HTML
python scripts/module_assembler.py --demo

# 查看所有模板（向后兼容）
python scripts/grid_builder.py --list-templates

# 从内置模板生成 HTML
python scripts/template_generator.py --type harmony-app -o "data/output/card.html"

# 使用自定义 Grid Spec（支持新旧两种格式）
python scripts/grid_builder.py --spec "data/templates/3x3-merge.json" -o "data/output/grid.html"

# 导出完整接口定义（供大模型参考）
python scripts/grid_builder.py --export-interfaces "data/output/interfaces.json"
```

## 工作流程

本技能支持两种生成模式，**每次生成完成后必须输出生成说明**（`print_generation_guide()` 自动输出）：

### 模式 A：结构化模式（推荐）
1. **解析需求** — 理解用户需要的布局（行列数、合并、内容类型）
2. **选择/创建 Grid Spec** — 选择内置模板或用 JSON 定义自定义网格
3. **引用模块** — 从模块库中选择 base/composite 模块放入格子
4. **生成 HTML** — 调用 `grid_builder.py` 生成，**自动执行审计**
5. **生成编辑界面**（可选）— 调用 `visual_editor.py`
6. **内容填充**（可选）— 调用 `content_filler.py`
7. **输出结果** — 用 `preview_url` 展示，`deliver_attachments` 交付

### 模式 B：自由生成模式（省 token）

> **🛑 [MANDATORY] 每次生成完成后，必须阅读 `print_generation_guide()` 输出的生成说明并向用户展示。**
1. **参考模块库** — 先执行 `python scripts/grid_builder.py --list-modules` 查看可用的 base/composite 模块
2. **参考模板范例** — 先执行 `python scripts/grid_builder.py --list-templates` 查看内置模板风格
3. **参考样式预设** — 先执行 `python scripts/grid_builder.py --list-presets` 查看可用风格
4. **AI 自由生成** — 基于上述参考，直接编写自包含 HTML（使用 data-field 标记可编辑区域）
5. **保存到文件** — 使用 Write 工具写入 `data/output/`
6. **审计 [MANDATORY]** — 调用 `python scripts/grid_builder.py --audit <文件>`，不可跳过
7. **输出结果** — 用 `preview_url` 展示

> 自由生成模式适用场景：简单卡片、快速原型、不需要网格拆分的页面。
> 结构化模式适用场景：复杂网格布局、需要批量生产、可复用模板。

## 权限说明

| 工具 | 访问级别 | 用途 |
|------|----------|------|
| Read | 只读 | 读取 Grid Spec、模块库、样式预设 |
| Write | 写入 | 将输出 HTML 写入 `data/output/` |
| Bash | 受限 | 运行内部处理脚本（限制在 `scripts/` 目录内） |

- **不会**访问系统敏感路径或凭证文件
- **不会**向外部网络发送数据
- **不会**执行用户 Shell 配置文件

## 错误处理说明

> v2.1.0 起，所有脚本均集成了中文错误处理机制：

1. **所有错误输出中文** — 不再显示英文 Traceback，改为 `❌ [错误类型] 说明 + 💡 修复建议`
2. **参数校验前置** — 缺少必填参数时会输出中文提示和"--help 查看参数说明"
3. **文件操作安全** — 文件不存在/编码不对/JSON格式错误，都有详细中文指引
4. **调试模式** — 添加 `--debug` 参数可显示完整堆栈（仅供开发调试用）
5. **常见错误快速查** — 见下方"错误排查"章节或 `references/faq.md`

> 如果遇到报错看不懂、或者修复建议不管用的情况，查阅 `references/faq.md` 或直接要求 AI 协助排查。

## 附录：详细文档索引

| 文档 | 内容 |
|------|------|
| `references/guide.md` | 完整使用教程（v3 组件式架构） |
| `references/module-library.md` | 组件系统 + 约束系统 + 组合示例（v3 新版） |
| `references/permissions.md` | 权限扫描报告和风险说明 |
| `references/style-presets.md` | 样式预设系统说明 |
| `references/call-chains.md` | 调用链定义（skill-sub） |
| `references/antipatterns.md` | 反模式手册 |
| `references/faq.md` | 常见问题解答 |

## 错误排查（快速入门）

> 脚本报错了？不要慌。所有错误提示已改为中文，并附带修复建议。

| 错误现象 | 可能原因 | 怎么做 |
|----------|---------|--------|
| ❌ [文件错误] 找不到文件 | 路径写错了 | 检查路径是否存在，用绝对路径试试 |
| ❌ [JSON错误] 格式错误 | JSON 语法有问题 | 用 jsonlint.com 校验，或检查多了一个逗号 |
| ❌ [模板错误] 未知模板 | 模板名写错了 | 用 `--list-templates` 查看所有可用模板 |
| ❌ [参数错误] 缺参数 | 命令写少了参数 | 用 `--help` 查看完整参数说明 |
| ⚠️ 审计警告 | HTML 有小问题但不致命 | 检查输出的 [WARN] 内容，逐一修正 |
| 浏览器打开是空白 | HTML 文件编码问题 | 确认文件是 UTF-8 编码保存的 |

> 完整错误排查指南见 `references/faq.md`。

> 版本 2.1.2 — 全面中文异常处理：所有脚本输出的英文 Traceback 改为中文错误提示+修复建议；新增能力边界定义和错误排查指引。
