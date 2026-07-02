# SVG 拼接工具 — 使用示例

> **加载时机**：当用户需要查看完整使用示例时加载。

## 示例 1：基础拼接（黑色）

```python
from svg_composer import compose_text

svg = compose_text("HELLO2026", fill="black", font_height_ratio=0.85)

with open('hello2026_black.svg', 'w', encoding='utf-8') as f:
    f.write(svg)
```

## 示例 2：白色文字

```python
svg = compose_text("HELLO2026", fill="white", font_height_ratio=0.85)

with open('hello2026_white.svg', 'w', encoding='utf-8') as f:
    f.write(svg)
```

## 示例 3：纵向排列

```python
svg = compose_text(
    "ABC",
    direction='vertical',
    canvas_size=(400, 600),
    margin=20,
    fill='white',
    font_height_ratio=0.7
)

with open('abc_vertical.svg', 'w', encoding='utf-8') as f:
    f.write(svg)
```

## 示例 4：模式1 - 仅顺序

```python
from svg_composer import compose_sequence
svg = compose_sequence("ABC", fill="black")
```

## 示例 5：模式2 - 全排列

```python
from svg_composer import compose_permutations

svg_list = compose_permutations("ABC", fill="black")
for i, svg in enumerate(svg_list):
    with open(f'perm_{i+1}.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
```

## 示例 6：模式3 - 笛卡尔积（密码本生成）

```python
from svg_composer import compose_combinations

# 生成 3 位数字密码本 (0-9)
svg_list = compose_combinations("0123456789", length=3, fill="black")
for i, svg in enumerate(svg_list):
    with open(f'code_{i:04d}.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
```

## 示例 7：模式4 - 限制长度

```python
from svg_composer import compose_limited
svg_list = compose_limited("ABC", limit=2, fill="black")
for i, svg in enumerate(svg_list):
    with open(f'combo_{i+1}.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
```

## 示例 8：使用外部 SVG 文件

```python
from svg_composer import compose_number

symbol_files = {'A': "assets/A.svg", '1': "assets/1.svg"}
svg = compose_number("A10", symbol_files, fill="black", margin=0)

with open('a10.svg', 'w', encoding='utf-8') as f:
    f.write(svg)
```

## 示例 9：load_symbols + layout_elements

```python
from svg_composer import load_symbols, layout_elements

symbols = load_symbols(r"D:\PycharmProjects\icons")
svg = layout_elements(
    elements=[symbols['A'], symbols['1'], symbols['0']],
    direction='horizontal', canvas_size=(640, 640),
    margin=10, fill='white'
)
```

## 示例 10：批量模式生成 + 预览 HTML

```python
from svg_composer import batch_mode_compose_with_preview

svg_list, preview_path = batch_mode_compose_with_preview(
    output_dir="output", text="ABC",
    mode='permutations', fill='black',
    generate_preview=True
)
print(f"预览页面: {preview_path}")
```

## 示例 11：生成预览 HTML

```python
from svg_composer import compose_text, generate_preview_html

html_path = generate_preview_html(
    output_dir="output", text="HELLO",
    direction='horizontal', fill='black',
    font_height_ratio=0.8
)
print(f"预览页面已生成: {html_path}")
```
