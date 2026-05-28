### Q4：可视化编辑器怎么用？

**A**：完整使用流程共 5 步，需要先有一个模板文件才能生成编辑器。

**第 1 步：生成模板文件**
```bash
python "C:/Users/sm001/.workbuddy/skills/hug-html/scripts/template_generator.py" --output "../.standardization/hug-html/data/output/template.html" --type promo
```

**第 2 步：根据模板生成编辑器 HTML**
```bash
python "C:/Users/sm001/.workbuddy/skills/hug-html/scripts/visual_editor.py" --template "../.standardization/hug-html/data/output/template.html" --output "../.standardization/hug-html/data/output/editor.html"
```
> 注意：`--template` 参数必须指向一个已存在的 HTML 模板文件，不能省略。

**第 3 步：在浏览器中打开编辑器**
双击打开 `editor.html`，页面默认是**只读预览模式**，看到的是最终效果。

**第 4 步：进入编辑模式**
按键盘 `Ctrl+E`，页面上的可编辑区域会出现**蓝色虚线边框**，此时可以直接点击任何文字进行更新，也可以点击图片区域更换图片。

**第 5 步：导出最终 HTML**
更新完成后，滚动到页面底部，点击**"导出 HTML"** 按钮，浏览器会自动下载一个完整的 HTML 文件，所有 CSS 和 JS 都已内嵌，无需任何外部依赖。

> 导出的 HTML 文件可以直接双击在浏览器中打开预览，也可以作为最终交付物发送给他人。
