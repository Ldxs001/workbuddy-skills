# 常见问题解答（FAQ）

本文档回答 hug-html 技能的常见问题。

---

## 基础问题

### Q1：这个技能支持哪些 HTML 模板类型？

**A**：支持 4 种类型：
- `promo` — 宣传面板（渐变背景 + 大标题 + 按钮）
- `product` — 产品介绍（左文右图两栏布局）
- `tech` — 技术说明（代码样式块 + 参数表格）
- `flow` — 流程图表（步骤卡片 + 编号）

详见 `references/guide.md` 完整参数说明。

---

### Q2：生成的 HTML 文件保存在哪里？

**A**：默认输出到：
```
C:/Users/sm001/.workbuddy/skills/.standardization/hug-html/data/output/
```

可通过 `--output` 参数指定自定义路径：
```bash
python "scripts/template_generator.py" --output "C:/path/to/output.html" --type promo
```

---

### Q3：如何自定义样式？

**A**：有两种方式：

**方式 A：更新预设配置文件**
```
C:/Users/sm001/.workbuddy/skills/.standardization/hug-html/data/config/style-presets.json
```

**方式 B：在调用时指定预设**
```bash
python "scripts/content_filler.py" preset --template <path> --preset business
```

可用预设：`business`（商务）、`academic`（科研）、`festive`（喜庆）、`mourning`（丧事）

详见 `references/style-presets.md`。

---

### Q4：如何使用可视化编辑器对 HTML 模板进行可视化编辑并导出最终结果？

**A**：完整使用流程如下（需要先有一个模板文件）：

**第 1 步：生成模板文件**
```bash
python "scripts/template_generator.py" --output "../.standardization/hug-html/data/output/template.html" --type promo
```

**第 2 步：根据模板生成编辑器 HTML**
```bash
python "scripts/visual_editor.py" --template "../.standardization/hug-html/data/output/template.html" --output "../.standardization/hug-html/data/output/editor.html"
```
> 注意：`--template` 参数必须指向一个已存在的 HTML 模板文件，不能省略。

**第 3 步：在浏览器中打开编辑器**
双击打开 `editor.html`，页面默认是**只读预览模式**，看到的是最终效果。

**第 4 步：进入编辑模式**
按键盘 `Ctrl+E`，页面上的可编辑区域会出现**蓝色虚线边框**，此时可以直接点击任何文字进行更新，也可以点击图片区域更换图片。

**第 5 步：导出最终 HTML**
更新完成后，滚动到页面底部，点击**"导出 HTML"** 按钮，浏览器会自动下载一个完整的 HTML 文件，所有 CSS 和 JS 都已内嵌，无需任何外部依赖。

> 导出的 HTML 文件可以直接双击在浏览器中打开预览，也可以作为最终交付物发送给他人。

---

### Q5：如何组合多个模块？

**A**：使用 `module_assembler.py`：

```bash
python "scripts/module_assembler.py" \
  --modules "gradient-purple,title-large,img-cover" \
  --output "C:/temp/assembled.html"
```

可用模块列表：
- 颜色：`gradient-purple`, `gradient-blue`, `solid-primary`, `transparent-card`
- 字体：`title-large`, `title-medium`, `body-text`, `caption`, `mono-code`
- 图片：`img-circle`, `img-logo`, `img-cover`, `img-contain`
- 布局：`two-col`, `three-col-cards`, `centered`
- 效果：`fade-in`, `hover-scale`, `divider`, `spacer`

详见 `references/module-library.md`。

---

### Q6：可以给模板填充真实内容吗？

**A**：可以，有三种方式：

**方式 A：自动填充示例内容**
```bash
python "scripts/content_filler.py" auto --template <path> --output <path>
```

**方式 B：从 JSON 文件填充**
```bash
python "scripts/content_filler.py" fill --template <path> --content "data/config/content.json" --output <path>
```

**方式 C：交互式填充**
```bash
python "scripts/content_filler.py" interactive --template <path> --output <path>
```

---

### Q7：生成的 HTML 依赖外部 CSS/JS 吗？

**A**：不依赖。所有生成的 HTML 都是**自包含**的：
- CSS 内嵌在 `<style>` 标签中
- JS 内嵌在 `<script>` 标签中
- 无外部链接、无 CDN 依赖

可直接在浏览器中打开，或嵌入到其他系统中。

---

### Q8：如何查看所有可用的调用链？

**A**：调用链定义在：
```
C:/Users/sm001/.workbuddy/skills/.standardization/hug-html/data/config/call-chains.json
```

或使用 skill-sub 查看：
```bash
python "C:/Users/sm001/.workbuddy/skills/.standardization/skill-sub/skill_sub.py" list
```

可用调用链：
- `generate-html-page` — 从需求到完整 HTML 页面
- `edit-html` — 生成可视化编辑界面并导出
- `assemble-with-modules` — 选择模块并组装成完整 HTML

---

## 进阶问题

### Q9：如何扩展新的模板类型？

**A**：更新 `scripts/template_generator.py`，在 `TEMPLATES` 字典中添加新类型：

```python
TEMPLATES = {
    "promo": {...},
    "product": {...},
    "tech": {...},
    "flow": {...},
    "your-new-type": {
        "title": "你的新模板",
        "sections": [...],
        ...
    }
}
```

然后更新 `references/guide.md` 和 `data/config/template-types.json`。

---

### Q10：可视化编辑器的编辑区域怎么定义？

**A**：在模板 HTML 中，给可编辑元素添加 `class="editable"` 和 `data-field="字段名"`：

```html
<h1 class="editable" data-field="title">默认标题</h1>
<p class="editable" data-field="content">默认内容</p>
<img class="editable" data-field="image" src="...">
```

`visual_editor.py` 会自动识别这些元素并生成编辑界面。

---

## 故障排查

### Q11：模板生成失败，报错"模块未找到"？

**A**：检查：
1. `scripts/module_assembler.py` 是否存在
2. `data/config/call-chains.json` 中模块名是否拼写正确
3. Python 版本是否 ≥ 3.8

---

### Q12：可视化编辑器打开后按 Ctrl+E 没反应？

**A**：
1. 检查浏览器控制台（F12）是否有 JS 错误
2. 确认 HTML 中包含 `<script>` 标签且未被广告拦截器屏蔽
3. 尝试用其他浏览器打开

---

> 本文档遵循 R-19 FAQ 引用规范，由 `skill-standardization v2.38.6` 生成。
