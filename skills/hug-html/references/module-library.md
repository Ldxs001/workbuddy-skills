# module-library.md — 可复用 HTML 模块库

本文件描述 `hug-html` 的模块库系统（`module_assembler.py`）。

---

## 模块结构

每个模块是一个 HTML 片段，存储在 `data/modules/modules.json` 中：

```json
{
  "category": {
    "module-name": {
      "desc": "模块描述",
      "html": "<div style=\"...\">HTML 片段</div>",
      "editable": true
    }
  }
}
```

- `editable: true` — 模块内含 `data-field` 可编辑区域
- `editable: false` — 固定模块（如占位图、分割线）

---

## 模块分类

### color — 颜色面板

| 模块名 | 效果 |
|---------|------|
| `gradient-purple` | 粉紫渐变背景面板 |
| `gradient-blue` | 蓝绿渐变背景面板 |
| `solid-primary` | 主色实心面板（紫底白字）|
| `transparent-card` | 白底半透明卡片 |

### font — 文字样式

| 模块名 | 效果 |
|---------|------|
| `title-large` | 大标题 2.8em，加粗，主色 |
| `title-medium` | 中标题 1.6em，主色 |
| `body-text` | 正文 1em，行高 1.8 |
| `caption` | 说明文字 0.9em，灰色 |
| `mono-code` | 代码样式，Consolas 字体 |

### image — 图片样式

| 模块名 | 效果 |
|---------|------|
| `img-circle` | 圆形裁剪（头像/Logo），150×150px |
| `img-logo` | Logo 样式，左上角定位，80px 宽 |
| `img-cover` | 封面图，100% 宽×200px 高，cover 裁剪 |
| `img-contain` | 完整显示，不变形，contain |

### layout — 布局

| 模块名 | 效果 |
|---------|------|
| `two-col` | 两栏布局（左文右图）|
| `three-col-cards` | 三栏卡片网格 |
| `centered` | 居中单栏（max-width 700px）|

### effect — 动态效果

| 模块名 | 效果 |
|---------|------|
| `fade-in` | 淡入动画（0.6s）|
| `hover-scale` | 悬停放大 1.03 倍 |
| `divider` | 分割线（`<hr>`）|
| `spacer` | 空白间隔 20px |

### template — 完整模板片段

| 模块名 | 效果 |
|---------|------|
| `promo-panel` | 宣传面板（渐变背景 + 标题 + 按钮）|
| `product-intro` | 产品介绍（图文左右）|
| `tech-block` | 技术说明块（代码样式）|
| `flow-step` | 流程步骤卡片（含编号圆）|

### style — 风格预设模块

| 模块名 | 效果 |
|---------|------|
| `business` | 商务风格（深蓝灰系）|
| `academic` | 科研风格（白底宋体）|
| `festive` | 喜庆风格（红金配色）|
| `mourning` | 丧事风格（黑白灰素雅）|

---

## 使用方法

### 列出所有模块

```bash
python "scripts/module_assembler.py" --list
```

### 组装模块

```bash
python "scripts/module_assembler.py" ^
  --modules "color:gradient-purple,font:title-large,image:img-cover,layout:two-col" ^
  --output "data/output/assembled.html"
```

模块名支持两种格式：
- `category:name` — 精确定位
- `name` — 在所有分类中搜索

### 添加自定义模块

编辑 `data/modules/modules.json`，添加新模块：

```json
{
  "my-category": {
    "my-module": {
      "desc": "我的自定义模块",
      "html": "<div style=\"...\">内容</div>",
      "editable": true
    }
  }
}
```

或用 `--save` 从当前 `MODULE_LIB` 常量重新生成：

```bash
python "scripts/module_assembler.py" --save
```

---

## 标准接口

所有含 `data-field="<name>"` 的模块元素，可被 `content_filler.py` 程序化填充：

```html
<h2 class="edit-text" data-field="my_title">默认标题</h2>
```

填充时自动匹配 `data-field` 值并替换内容。
