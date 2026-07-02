# SVG 拼接工具 — 常见问题

> **加载时机**：当用户遇到错误或异常时加载。

## 参数错误类

### Q: 调用 compose_text() 后输出空白 SVG 文件

A: 输入文本为空字符串或包含不受支持的字符。检查输入文本是否属于 `0-9` 或 `A-Z` 范围（仅 36 个字符）。小写字母会自动转为大写，非字母数字字符会被跳过。

### Q: 传入 black 以外的颜色后 SVG 显示异常

A: 仅支持 `'black'`（#000000）和 `'white'（#FFFFFF）两种颜色。传入其他值时函数不会报错但渲染效果不可预期。

### Q: 纵向排列时字符被压扁或显示不全

A: canvas_size 需适配文字方向。纵向拼接建议设置 height > width（如 `canvas_size=(400, 600)`），并适当降低 font_height_ratio（0.6-0.7）。

## 依赖与环境错误类

### Q: import svg_composer 失败

A: 确认 Python 版本 ≥ 3.7。运行 `pip install svgpathtools` 安装依赖。如果安装失败，检查网络连接或更换 pip 镜像源。

### Q: 生成的预览 HTML 在浏览器中打不开

A: 浏览器安全策略限制 file:// 协议访问本地文件。将生成的 output 目录移到非系统目录（如桌面）后再打开，或使用 VS Code Live Server 等本地服务器查看。

## 外部资源错误类

### Q: load_symbols() 返回空字典

A: 确认 `symbol_dir` 路径存在且包含 `.svg` 文件。每个 SVG 文件需包含有效的 path 数据（d 属性），仅含 `<image>` 或 `<rect>` 等非 path 元素的 SVG 不会被识别。

### Q: 外部符号拼接后字符间距异常

A: 外部 SVG 文件没有内置的 advance_ratio。使用 `layout_elements()` 配合手动 margin 参数（建议 10-50）调整间距。

## 性能问题类

### Q: compose_combinations() 执行卡死

A: 输入字符较多且 length 较大时组合数指数增长。限制：输入字符 ≤5，length ≤4（最大 5^4=625 个组合）。6 字符 + length=5 产生 7776 个组合，需等待较长时间。
