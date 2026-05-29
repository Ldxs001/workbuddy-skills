---
name: hug-html
author: Ldxs
license: MIT
description: >
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/hug-html/data/
external_data_dir: true
faq_quality: improve_qa
antipattern_detail: add_detail
version: 2.0.4
---









# hug-html

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

## 触发场景

当用户提到以下内容时触发本技能：

- "生成 HTML 模板" / "HTML template" / "hug html"
- "编辑 HTML" / "可视化编辑 HTML" / "visual edit HTML"
- "HTML 模块" / "HTML module library"
- "网格布局" / "grid layout" / "N×M 网格"
- "单元格合并" / "rowspan" / "colspan"
- 输出格式：自包含 HTML 文件（毛玻璃卡片风格）

**不触发**：
- 用户仅询问 HTML 语法概念，无文件生成需求
- 用户明确请求其他特定技能

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

## 四层架构（细化）

```
骨架 (Skeleton)
├── 骨架结构 — N×M 网格、行列数、单元格合并(rowspan/colspan)、gap间距
└── 骨架样式 — 底板背景/渐变/透明度、外阴影、外边框、圆角、内外边距

模块 (Modules)  ← 模块模板 = {模块结构 + 模块样式} 预置组合
├── 模块结构 — 复合模块的 HTML 骨架（header-entity 的图标+文字布局、qr-card 的卡片+二维码结构等）
└── 模块样式 — 模块级的视觉样式（由 base 模块组合提供：字体、颜色、背景、圆角等）

基础 (Base/Primitives)
└── 基础样式 — 作用于具体文字/元素的 CSS 原语：字族、字号、字重、字色、行高、透明度、对齐方式

          方案模板 = 预置的{骨架结构 + 骨架样式 + 模块结构 + 模块样式 + 基础样式}组合
```

**编辑粒度**（可视化编辑器内）：
| 可更新 | 不可更新（需改 Grid Spec） |
|--------|---------------------------|
| ✓ 图片内容（点击输入URL / 拖放文件替换） | ✗ 骨架结构（行列数、合并方式、gap） |
| ✓ 基础样式（每个文字元素独立：字体家族/字重/字号/字色） | ✗ 模块结构（组件的HTML骨架） |
| ✓ 模块样式（通过 cell style 覆盖背景色/内边距） | ✗ 骨架样式（底板色/外阴影等） |

**大模型使用流程**（自由生成模式）：
1. 理解用户需求 → 确定骨架结构：几行几列、哪些单元格需要合并
2. 描述需要的模块 → 从复合模块库中选择匹配的模块模板，放入对应骨架位置
3. 应用基础样式 → 为每个文字元素配置字体、字号、字色、字重
4. 组合为 HTML → 直接生成自包含 HTML（data-field 标记编辑区），用 `--audit` 审查

## 核心能力

| # | 能力 | 说明 |
|---|------|------|
| 1 | **骨架结构** | N×M 网格、行列数、单元格合并（rowspan/colspan）、gap 间距 |
| 2 | **骨架样式** | 底板背景/渐变、外阴影、外边框、圆角、卡片内外边距 |
| 3 | **模块体系** | 复合模块（header-entity/qr-card/feature-panel 等 14 种）+ Base CSS 原语 |
| 4 | **方案模板库** | 内置 7+ 预置{骨架+模块+样式}组合 + **用户可自定义固化** |
| 5 | **样式预设** | 5 种内置风格：商务/科研/喜庆/丧事/技术，一键切换配色字体 |
| 6 | **基础编辑** | 每个文字元素独立控制：字体家族(8种)/字重(100-900)/字号(9-48px)/字色/透明度 |
| 7 | **图片编辑** | 点击输入URL + 拖放文件替换，所有复合模块图片均支持 |
| 8 | **生成后审计** | 自动检查 HTML 结构完整性、标签平衡、图片属性、网格越界、渲染风险 |
| 9 | **统一接口** | `--export-interfaces` 导出完整接口定义 JSON，大模型可直接理解 |
| 10 | **方案模板固化** | `--save-as <名>` 将任意生成固化为用户模板，后续按名引用 |
| 11 | **自由生成模式** | AI 参考模块库和模板范，理解需求确定骨架→选模块→设样式→生成→审计 |

## 快速开始

```bash
# 查看所有模板
python scripts/grid_builder.py --list-templates

# 从内置模板生成 HTML
python scripts/template_generator.py --type harmony-app -o "data/output/card.html"

# 生成可视化编辑界面
python scripts/visual_editor.py --type harmony-app -o "data/output/editor.html"

# 内容填充
python scripts/content_filler.py auto --template "data/output/card.html" --output "data/output/filled.html"

# 使用自定义 Grid Spec
python scripts/grid_builder.py --spec "data/templates/3x3-merge.json" -o "data/output/grid.html"

# 固化方案模板（将当前生成保存为可复用的用户模板）
python scripts/grid_builder.py --save-as my-template --spec harmony-app --desc "我的毛玻璃卡片"

# 按名称使用用户方案模板（下次直接引用）
python scripts/grid_builder.py --spec "my-template" -o "data/output/from-user-template.html"

# 导出完整接口定义（供大模型参考）
python scripts/grid_builder.py --export-interfaces "data/output/interfaces.json"
```

## 工作流程

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

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
> 该说明包含：编辑快捷键、创作模式选择、可用资源列表、固化模板提示。
> 这是帮助用户理解当前产出如何继续操作的关键步骤，不可跳过。

### 模式 B：自由生成模式（省 token）
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

## 主要工作流程

本技能使用三阶段执行框架（执行 → 审查 → 推进）：

### 阶段 1：执行
- 读取用户输入参数（模板类型、网格规格、模块选择等）
- 调用 `scripts/` 目录中的脚本进行处理
- 捕获执行结果和错误

### 阶段 2：审查
- 验证输出 HTML 文件已生成
- 检查 HTML 格式合规性（自包含，无外部依赖）
- 检查网格布局正确性（单元格位置、合并）

### 阶段 3：推进
- 使用 `preview_url` 展示生成的 HTML
- 使用 `deliver_attachments` 交付最终文件
- 若发生错误，进入错误处理流程

---

## 附录：详细文档索引

| 文档 | 内容 |
|------|------|
| `references/guide.md` | 完整使用教程（v2 网格架构） |
| `references/permissions.md` | 权限扫描报告和风险说明 |
| `references/module-library.md` | 两层级模块库说明 |
| `references/style-presets.md` | 样式预设系统说明 |
| `references/call-chains.md` | 调用链定义（skill-sub） |
| `references/antipatterns.md` | 反模式手册 |
| `references/faq.md` | 常见问题解答 |

> 版本 2.0.0 — 网格架构重构：新增 `grid_builder.py` 核心引擎、两层级模块体系、7+ 内置模板、N×M 网格布局支持。
