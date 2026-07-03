---
name: svg-composer
version: 3.3.2
displayName: svg-composer
description: SVG 拼接工具，支持内置 FontAwesome 字符集（0-9, A-Z）和四种拼接模式
author: wUwproject
tags: ['svg', 'composer', 'fontawesome', 'generation']
license: MIT
data_dir: skills/.standardization/svg-composer/data/
triggers: ['拼接 SVG', '合成图标', 'SVG 组合', '字符拼接', 'svg-composer']
slug: svg-composer
trigger: 拼接 SVG
trigger_negative: 生成 PNG 图片,非拼接矢量绘图
h1_position: true
external_data_dir: true
sensitive_access: false
critical_write: false
create_permissions_md: true
permission_weight: LOW
meta_field_sync: true
faq_quality: improve_qa
---
# SVG 拼接工具 (svg-composer)

> 将 SVG 符号进行横向/纵向拼接，支持内置字符集和四种拼接模式。

## 触发场景

**正向触发：**
- [拼接 / 组合 / 合成 SVG 图标或字符]
- [生成 SVG 密码本 / 验证码 / 全排列组合]
- [制作复合 SVG 图标 / Logo / 徽章]
- [批量生成 SVG 预览 HTML]

**否定条件：**
- 用户要求生成普通图片（PNG/JPG）——不是 SVG 格式
- 用户要求矢量绘图但非拼接（如画线框图）——请用 draw.io 技能

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| 能力 | 说明 | 限制 |
|------|------|------|
| **内置字符集拼接** | 基于 Font Awesome Free 字符，拼接 `0-9`、`A-Z` 文本 | 仅 36 个字符，小写自动转大写 |
| **四种拼接模式** | 顺序 / 全排列 / 笛卡尔积 / 限制长度 | 笛卡尔积输入 ≤5 字符，length ≤4 |
| **自定义符号拼接** | 从外部 SVG 文件加载符号拼接 | 依赖用户提供 .svg 文件 |
| **批量预览 HTML** | 自动生成含下载链接的预览页 | 仅内联 SVG 预览，无服务器 |

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
|--------|------|----------|----------|
| `references/functions.md` | 函数参考 | 完整函数参数与返回值说明 | 无 |
| `references/charset.md` | 字符集 | 内置字符集详情与四种拼接模式对比 | 无 |
| `references/examples.md` | 使用示例 | 11 个完整使用示例 | R-25 C-17 |
| `references/changelog.md` | 版本日志 | 版本更新记录 | R-24 |
| `references/faq.md` | 常见问题 | 常见问题与排错 | R-19, R-25 C-19 |
| `references/antipatterns.md` | 反模式 | 常见错误做法与正确做法 | R-18 |
| `references/permissions.md` | 权限说明 | 安全风险评估 | R-15, R-16 |
| `references/LICENSE.md` | 许可协议 | MIT 许可 | R-26 |

## 快速开始

```python
from svg_composer import compose_text

# 基础拼接（黑色）
svg = compose_text("HELLO", fill="black")
with open('hello.svg', 'w', encoding='utf-8') as f:
    f.write(svg)
# 输出: hello.svg — 包含 HELLO 五个字符的横向拼接 SVG

# 纵向排列
svg = compose_text("ABC", direction='vertical', canvas_size=(400, 600))
# 输出: SVG 字符串 — A/B/C 纵向排列，画布 400x600
```

## 工作流程

1. 用户输入文本，选择拼接模式
2. 指定颜色（black/white）和方向（horizontal/vertical）
3. 调用对应函数生成 SVG 字符串
4. 输出 .svg 文件
5. 可选：调用 `generate_preview_html()` 生成预览 HTML

## 能力边界

### 输入参数范围

- **text 长度**: ≤200 字符，仅 `0-9`、`A-Z`（小写自动转大写）
- **canvas_size**: 宽/高各 100-4000（像素），默认 640×640
- **margin**: 0-200（像素），默认 0
- **font_height_ratio**: 0.1-1.0，默认 0.8
- **fill 颜色**: 仅 `black`（#000000）和 `white`（#FFFFFF）
- **输入字符数**: 笛卡尔积 ≤5 且 length ≤4（≤625 组合）；全排列 ≤6（≤720 排列）

### 环境与依赖

- **Python**: 3.7+
- **依赖**: svgpathtools（`pip install svgpathtools`）
- **输出格式**: 仅 SVG 格式，无 PNG/JPG 导出

### 其他限制

- 外部 SVG 符号：仅识别含有效 path data（d 属性）的文件
- 总拼接长度超过画布时自动等比缩放
- Font Awesome Free 36 字符内置（`0-9`、`A-Z`），不可扩展

> 本技能由 wUwproject 创作并维护。
