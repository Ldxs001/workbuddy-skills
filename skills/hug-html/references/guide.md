# hug-html 完整使用教程

HTML 模板生成技能，支持可视化编辑、模块库组装、样式预设。

---

## 快速开始

### 1. 生成 HTML 模板

```bash
python "scripts/template_generator.py" --output "data/output/template.html" --type promo
```

`--type` 选项：
- `promo` — 宣传面板（粉紫渐变）
- `product` — 产品介绍（绿青渐变）
- `tech` — 技术说明（深色代码风格）
- `flow` — 流程明白纸（橙黄渐变）

### 2. 生成可视化编辑界面

```bash
python "scripts/visual_editor.py" --template "data/output/template.html" --output "data/output/editor.html"
```

生成的 `editor.html` 可直接在浏览器打开，支持：
- 点击文字区域直接编辑
- 点击图片更换 URL
- 顶部工具栏：加粗/斜体/下划线、字色/背景色、字号、透明度
- 图片样式：圆形裁剪 / 封面填充 / Logo 左上 / 完整显示
- 快捷键：`Ctrl+E` 进入/退出编辑，`Ctrl+S` 生成最终 HTML

### 3. 模块库组装

```bash
# 查看所有可用模块
python "scripts/module_assembler.py" --list

# 组装指定模块
python "scripts/module_assembler.py" --modules "color:gradient-purple,font:title-large,image:img-cover,layout:two-col" --output "data/output/assembled.html"
```

模块分类：
| 分类 | 模块示例 |
|------|---------|
| `color` | `gradient-purple`, `gradient-blue`, `solid-primary`, `transparent-card` |
| `font` | `title-large`, `title-medium`, `body-text`, `caption`, `mono-code` |
| `image` | `img-circle`, `img-logo`, `img-cover`, `img-contain` |
| `layout` | `two-col`, `three-col-cards`, `centered` |
| `effect` | `fade-in`, `hover-scale`, `divider`, `spacer` |
| `template` | `promo-panel`, `product-intro`, `tech-block`, `flow-step` |
| `style` | `business`, `academic`, `festive`, `mourning` |

### 4. 内容填充

```bash
# 自动填充示例内容
python "scripts/content_filler.py" --template "data/output/template.html" --auto --output "data/output/filled.html"

# 用 JSON 文件填充
python "scripts/content_filler.py" --template "data/output/template.html" --content "data/config/content.json" --output "data/output/final.html"

# 从 HTML 提取内容到 JSON
python "scripts/content_filler.py" --extract "data/output/editor.html" --output "data/config/content.json"
```

---

## 图片处理说明

本技能**用 HTML/CSS 实现图片效果**，无需真实图片处理库：

| 效果 | CSS 实现方式 |
|------|-------------|
| 圆形裁剪（头像/Logo） | `border-radius: 50%; object-fit: cover` |
| Logo 左上角 | `position: absolute; top: 12px; left: 12px; width: 80px` |
| 封面填充 | `width: 100%; height: 200px; object-fit: cover` |
| 完整显示（不变形） | `width: 100%; height: auto; object-fit: contain` |
| 透明度 | `opacity: 0.9`（或 0.7 / 0.5 / 0.3） |

---

## 样式预设

| 预设名 | 适用场景 | 主色调 |
|---------|---------|---------|
| `business` | 商务报告、正式文档 | 深蓝灰 `#1a2a4a` |
| `academic` | 科研论文、技术报告 | 黑 `#333` + 宋体 |
| `festive` | 婚庆、节日、庆典 | 红金 `#c0392b` + 金 `#FFD700` |
| `mourning` | 讣告、悼念 | 黑白灰素雅 |
| `tech` | 技术文档、代码说明 | 深灰 `#2D3436` + Consolas |

---

## 调用链（skill-sub）

本技能已注册以下调用链（见 `references/call-chains.md`）：

1. **generate-html** — 从需求到最终 HTML 的完整流程
2. **edit-html** — 生成模板 → 生成编辑界面 → 用户编辑 → 导出最终 HTML
3. **assemble-with-modules** — 选择模块 → 组装 → 填充内容 → 输出

---

## 可编辑区域标准接口

所有模板使用 `data-field="<字段名>"` 标识可编辑区域，方便程序化填充：

```html
<h1 class="edit-text" data-field="title">可编辑标题</h1>
<p class="edit-text" data-field="desc">可编辑描述</p>
<img class="editable-img" data-field="image" src="...">
```

`content_filler.py` 通过 `data-field` 属性自动定位并替换内容。

---

## 输出文件位置

所有输出默认保存在：
```
C:/Users/sm001/.workbuddy/skills/hug-html/data/output/
```

---

## 常见问题

**Q: 生成的 HTML 在浏览器中打开后中文乱码？**
A: 确认 HTML 含 `<meta charset="UTF-8">`，且文件以 UTF-8 编码保存（本技能默认 UTF-8）。

**Q: 可视化编辑器点击没有反应？**
A: 确认浏览器 JS 未被禁用；打开浏览器控制台（F12）查看是否有报错。

**Q: 如何添加自定义模块？**
A: 编辑 `data/modules/modules.json`，或调用 `module_assembler.py --save` 根据当前 `MODULE_LIB` 重新生成。
