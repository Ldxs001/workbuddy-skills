# SVG 拼接工具 — 函数参考

> **加载时机**：当用户需要了解具体函数参数、返回值或使用方式时加载。

## 1. compose_text — 基础拼接（推荐）

直接拼接文本字符串，无需外部 SVG 文件。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | str | — | 要拼接的文本，如 `"ABC123"` |
| `direction` | str | `'horizontal'` | 拼接方向：`'horizontal'` / `'vertical'` |
| `canvas_size` | tuple | `(640, 640)` | 画布尺寸 |
| `margin` | float/int | `0` | 字符间距（像素） |
| `align` | str | `'center'` | 对齐方式：`'center'` / `'start'` / `'end'` |
| `fill` | str | `'black'` | 填充颜色：`'black'` 或 `'white'` |
| `font_height_ratio` | float | `0.8` | 字体高度占画布比例 |
| `charset` | str | `'fa'` | 字符集：`'fa'`（默认） |

**返回值**：SVG 字符串

## 2. compose_sequence — 模式1：仅顺序

拼接输入顺序的文字，不做任何排列组合。

```python
svg = compose_sequence("ABC", fill="black")  # → SVG("ABC")
```

## 3. compose_permutations — 模式2：全排列

输入字符的全排列（不重复组合）。

```python
svg_list = compose_permutations("ABC", fill="black")
# → [SVG("ABC"), SVG("ACB"), SVG("BAC"), SVG("BCA"), SVG("CAB"), SVG("CBA")]
```

## 4. compose_combinations — 模式3：笛卡尔积

可重复组合（密码本模式），生成指定长度的所有重复排列。

```python
svg_list = compose_combinations("ABC", length=3, fill="black")
# → 27 个: AAA, AAB, AAC, ABA... CCC
```

## 5. compose_limited — 模式4：限制长度

限制每个组合的长度，生成所有长度的全排列。

```python
svg_list = compose_limited("ABC", limit=2, fill="black")
# → 12 个: A, B, C, AB, AC, BA, BC, CA, CB
```

## 6. layout_elements — 布局拼接

将多个 SVG 符号横向或纵向拼接成一个 SVG。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `elements` | list | — | 元素列表 `{'d': path_d, 'bbox': (...) }` |
| `direction` | str | `'horizontal'` | 拼接方向 |
| `canvas_size` | tuple | `(640, 640)` | 画布尺寸 |
| `margin` | float/int | `0` | 元素间距 |
| `align` | str | `'center'` | 对齐方式 |
| `fill` | str | `'black'` | 填充颜色 |

## 7. load_symbols — 加载自定义符号

从文件夹批量加载 SVG 符号。

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol_dir` | str | 符号文件夹路径（包含 .svg 文件） |

**返回值**：字典 `{symbol_name: {'d': path_d, 'bbox': (xmin,xmax,ymin,ymax)}}`

## 8. compose_number — 外部符号拼接（兼容）

使用外部 SVG 符号文件组合字符串。

| 参数 | 类型 | 说明 |
|------|------|------|
| `target` | str | 目标字符串，如 `"A10"` |
| `symbol_files` | dict | `{字符: SVG文件路径}` |
| `fill` | str | `'black'` 或 `'white'` |
| `margin` | int | 符号间距（像素），默认 0 |

## 9. batch_mode_compose_with_preview — 批量生成 + 预览

批量生成 SVG 并自动生成预览 HTML。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output_dir` | str | — | 输出目录 |
| `text` | str | — | 输入文本 |
| `mode` | str | — | `'sequence'` / `'permutations'` / `'combinations'` / `'limited'` |
| `fill` | str | `'black'` | 填充颜色 |
| `generate_preview` | bool | `True` | 是否生成预览 HTML |

## 10. generate_preview_html — 生成预览 HTML

生成包含横向和纵向 SVG 预览的 HTML 页面。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `output_dir` | str | — | 输出目录 |
| `text` | str | — | 输入文本 |
| `direction` | str | `'horizontal'` | 拼接方向 |
| `fill` | str | `'black'` | 填充颜色 |
| `font_height_ratio` | float | `0.8` | 字体高度占画布比例 |
