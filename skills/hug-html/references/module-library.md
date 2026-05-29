# module-library.md — hug-html 模块库说明 (v2 网格架构)

## 两层级模块体系

```
基础模块 (base) → CSS原语（字体/颜色/渐变/图片裁切/圆角/间距）
复合模块 (composite) → 可复用 HTML 组件（引用基础模块）
网格 (grid) → N×M 布局，单元格可合并，放置复合模块
```

## 基础模块

存储在 `grid_builder.py` 的 `BASE_MODULES` 字典中。

使用方法：在 Grid Spec 中通过 `"base": ["base:font-size-xl", "base:color-dark"]` 引用。

### 分类

| 分类 | 模块前缀 | 示例 |
|------|---------|------|
| 字体大小 | `font-size-` | xxl, xl, lg, md, sm, xs, xxs |
| 字体颜色 | `color-` | dark, mid, light, white, primary, gradient-text |
| 背景 | `bg-` | white, transparent, light-blue, glass, dark, gradient-purple/blue/dark/gold |
| 圆角 | `radius-` | sm, md, lg, xl, full, pill |
| 间距 | `pad-` | xs, sm, md, lg, xl |
| 阴影 | `shadow-` | sm, md, lg, glass |
| 边框 | `border-` | glass, light, bottom, divider-gradient, divider-solid |
| 图片 | `img-` | circle, cover, contain, logo |
| 布局 | `flex-` | center, between, col; text-center/left; gap-xs/sm/md/lg |
| 透明度 | `opacity-` | 100, 90, 70, 50 |
| 动画 | `anim-` | fade, slide, hover-scale |

## 复合模块

存储在 `grid_builder.py` 的 `COMPOSITE_MODULES` 字典中。

在 Grid Spec 中通过 `"module": "composite:模块名"` 引用。

### 完整列表

| 模块名 | 用途 | data-field 槽位 |
|--------|------|-----------------|
| `header-entity` | 单实体头部 | entity-name, entity-badge |
| `header-dual` | 双实体头部(左应用+右服务) | app-name, app-badge, service-name, service-badge |
| `main-title` | 渐变主标题+副标题 | main-title, main-sub |
| `qr-card` | 单二维码卡片 | qr-image, qr-label, qr-hint |
| `qr-dual` | 双二维码并排 | qr-image-left/right, qr-label-left/right, qr-hint-left/right |
| `feature-panel` | 特性面板 | feature-icon-0/1, feature-text-0/1 |
| `comms-panel` | 通信面板 | 设备标签内容 |
| `footer-caption` | 底部标签行 | footer-tag-1/2/3 |
| `small-note` | 注释文字 | note-text |
| `text-block` | 纯文本块 | tb-title, tb-body, tb-body-2 |
| `text-img-right` | 左文右图 | ti-title, ti-desc |
| `param-panel` | 参数面板 | param-title, param-1, param-2 |
| `data-table` | 数据表格 | th-1/2, td-row*-col* |
| `stat-card` | 统计卡片 | stat-label, stat-value |

## Grid Spec 结构

完整的 Grid Spec JSON 格式：

```json
{
  "name": "模板名称",
  "desc": "描述",
  "source": "来源（可选）",
  "card_style": {
    "max_width": "400px",
    "bg": "rgba(255,255,255,0.82)",
    "backdrop": "blur(25px)",
    "border_radius": "36px",
    "shadow": "0 20px 35px rgba(...)",
    "padding": "24px 20px",
    "border": "1px solid rgba(255,255,255,0.4)"
  },
  "grid": {
    "rows": 6,
    "cols": 1,
    "gap": "0",
    "cells": [
      {
        "id": "cell-id",
        "row": 0, "col": 0,
        "rowspan": 1, "colspan": 1,
        "module": "composite:模块名",
        "style": {"background": "#xxx", "padding": "16px"},
        "html": "自定义HTML（与module二选一）"
      }
    ]
  }
}
```

## 命令行工具链

| 工具 | 命令 | 用途 |
|------|------|------|
| `grid_builder.py` | `--spec <spec> -o <html>` | 核心引擎：从 Grid Spec 生成 HTML |
| `grid_builder.py` | `--list-modules` | 列出所有 base + composite 模块 |
| `grid_builder.py` | `--list-templates` | 列出所有内置模板 |
| `grid_builder.py` | `--demo --template <name>` | 快速生成模板示例 |
| `module_assembler.py` | `--spec <spec> -o <html>` | 网格化组装（兼容旧调用方式） |
| `module_assembler.py` | `--create-spec <path>` | 交互式创建 Grid Spec |
| `template_generator.py` | `--type <name> -o <html>` | 从内置模板生成 |
| `visual_editor.py` | `--template <html> -o <editor>` | 生成网格编辑界面 |
| `visual_editor.py` | `--type <name> -o <editor>` | 从内置模板直接生成编辑界面 |
| `content_filler.py` | `fill/auto/extract` | 内容填充与提取 |
| `gen_test_grids.py` | (直接运行) | 生成模块库 JSON + 额外 Grid Spec |
