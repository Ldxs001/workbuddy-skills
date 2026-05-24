---
name: simulated-peak-plot
version: 2.6.0
description: 生成模拟峰图（高斯峰），用于色谱、光谱或任何信号可视化。当用户要求生成峰谱、模拟信号数据、创建峰图、可视化保留时间或输出数据为Markdown表格时触发。支持自定义峰参数、噪声水平、基线设置、复合峰（N个子峰组合）、自定义坐标轴标题/单位、CSV完整数据导出、可点击的file:///路径输出、以及从设备导出数据导入CSV。
---

## 触发条件

当用户出现以下意图时，加载本技能：

- 说出"生成峰图"、"模拟信号"、"创建峰谱"
- 说出"可视化保留时间"、"输出 Markdown 表格"
- 说出"导入 CSV 数据"、"生成模拟数据"
- 需要色谱/光谱峰模拟、信号可视化、数据导出等场景

**否定条件**：除非用户明确提到生成峰图或模拟数据，否则不要主动触发。

→ 权限说明详见 `references/permission.md`（低风险，unified 授权）

## 快速开始

```bash
# 交互式生成峰图
python {SKILL_DIR}/scripts/generate_peak.py --interactive

# 从 CSV 文件导入数据
python {SKILL_DIR}/scripts/generate_peak.py --import-csv data.csv

# 使用 JSON 配置文件
python {SKILL_DIR}/scripts/generate_peak.py --config config.json
```

## 概述

本技能用于生成模拟峰图（高斯峰），适用于教学、测试或演示场景。支持：
- 多种峰类型，包括**复合峰**（任意数量子峰组合）
- 可自定义时间范围、基线和噪声
- **可自定义坐标轴标题和单位**（X/Y标签，mV/V/吸光度等）
- **CSV完整数据导出**（全部数据点）
- **可点击的 file:/// 路径**，方便直接打开图片
- Markdown表格数据输出（在控制台打印）
- 交互式配置，带点数推荐

## 新功能（v2.1）

### 1. 可自定义坐标轴标题
- `xlabel`：X轴标题（默认：`Time`）
- `ylabel`：Y轴标题（默认：`Response`）
- `x_unit`：X轴单位（默认：`min`）
- `y_unit`：Y轴单位（默认：`mV`，可设为`V`、`absorbance`等）

### 2. CSV完整数据导出
- 将完整数据集导出为CSV文件
- 格式：`[(t1, s1), (t2, s2), ...]`
- **RFC 4180标准格式**：UTF-8编码，逗号分隔，数值型数据
- 表头：`Time_<unit>,Signal_<unit>`
- 输出文件路径带 `file:///` URI，可直接点击

### 3. 可自定义网格线
- `grid`：是否显示网格线（默认：`True`）
- `grid_linestyle`：网格线样式 - `'solid'`、`'dashed'`、`'dotted'`、`'dashdot'`
  - solid：实线（-）
  - dashed：虚线（--）
  - dotted：点线（:）
  - dashdot：点划线（-.)
- `grid_alpha`：网格线透明度（默认：0.6）

### 4. CSV数据导入（设备导出）
直接导入设备导出的原始CSV数据，无需手动配置峰参数。

**命令行用法：**
```bash
python {SKILL_DIR}/scripts/generate_peak.py --import-csv data.csv
python {SKILL_DIR}/scripts/generate_peak.py --import-csv data.csv --x-col 0 --y-col 1
python {SKILL_DIR}/scripts/generate_peak.py --import-csv data.csv --no-header --output my_plot.png
```

**参数说明：**
| 参数 | 说明 |
|------|------|
| `--import-csv` | CSV文件路径（必需） |
| `--x-col` | X轴数据列索引（默认：0） |
| `--y-col` | Y轴数据列索引（默认：1） |
| `--no-header` | CSV文件无表头行 |
| `--output` | 输出PNG文件名（默认：imported_data.png） |

**支持的CSV格式：**
- 设备导出的标准格式（带表头或无表头）
- 逗号分隔，UTF-8编码
- 自动跳过非数值行

### 3. 可点击图片路径
- 自动输出 `file:///C:/path/to/image.png`
- 直接点击在默认查看器中打开

## 工作流程

### 1. 环境检查

**始终从检查环境开始：**

```bash
# 检查 Python 可用性
python --version

# 检查必需包
python -c "import numpy; import matplotlib; print('所有包可用')"
```

如果缺少包，指导用户安装：
```bash
pip install numpy matplotlib
```

### 2. 参数配置（交互式对话）

通过对话配置参数。**首先显示点数推荐表**。

**时间范围：**
- 起始：5 min
- 结束：15 min

**默认峰（包括含3个子峰的复合峰）：**
- 空白峰：RT=5.8, Height=300, HWHM=0.1
- 峰 A：RT=7.7, Height=1500, HWHM=0.08
- 峰 B：RT=10.3, Height=1200, HWHM=0.12
- 复合峰（3个子峰）：RT=11.5/12.0/12.5, Heights=1100/800/600, HWHM=0.15

**信号设置：**
- 基线：20
- 噪声水平：8

**输出：** PNG + Markdown表格（打印到控制台）

询问用户：
1. "你想要多少个峰？（默认：4，包括空白峰和复合峰）"
2. "为每个峰提供：名称、保留时间（RT）、高度、HWHM"
3. "对于复合峰：输入子峰数量（2+=复合），然后为每个子峰提供RT/高度/HWHM"
4. "是否要修改基线或噪声水平？（默认：baseline=20, noise=8）"
5. "是否要打印数据为Markdown表格？（默认：y）"
6. "表格采样间隔（每N个点打印一次）？（默认：20）"
7. "是否要更改输出文件名？（默认：simulated_peak）"
8. "自定义坐标轴标签？（xlabel/ylabel, x_unit, y_unit）[默认：Time/min, Response/mV]"
9. "导出完整数据为CSV？（y/n）[默认：n]"
10. "显示网格线？（y/n）[默认：y]"
    - 如果选是："网格线样式？（1=实线, 2=虚线, 3=点线, 4=点划线）[默认：2]"
    - 如果选是："网格透明度（0.1-1.0）？[默认：0.6]"
11. 始终输出可点击的 file:/// 路径，方便直接打开

### 3. 点数推荐表

根据以下因素显示推荐表：
- 时间范围持续时间
- 峰数量
- 基线变化
- 峰锐度（HWHM）

**推荐公式：**
```
points = max(500, duration * peaks * sharpness_factor * 2)
```

典型推荐：

| 持续时间（min） | 峰数 | 基线 | 推荐点数 |
|----------------|-------|----------|-------------------|
| 5-10 | 2-4 | 低（<50） | 500-800 |
| 10-20 | 4-8 | 中（50-100） | 800-1200 |
| 20-30 | 8+ | 高（>100） | 1200-2000 |
| 30+ | 任意 | 任意 | 2000+ |

同时显示计算：
```
对于您的设置：
持续时间 = [t_end - t_start] min
峰数 = [num_peaks]
基线 = [baseline]
推荐点数 = max(500, [calculated_value])
```

### 4. 生成图表并输出数据

使用 `{SKILL_DIR}/scripts/generate_peak.py` 脚本：

```bash
python {SKILL_DIR}/scripts/generate_peak.py --interactive
```

脚本将：
1. 生成带标注的峰图
2. 保存PNG文件
3. 在控制台打印数据作为Markdown表格（可选）

### 5. 输出

脚本将：
- 生成光谱图（PNG）
- **输出可点击的 file:/// 路径**，可直接打开
- **导出完整数据CSV文件**（如果启用）
- 在控制台打印时间和信号数据作为Markdown表格（可选）
- 显示图表（如果在交互式环境中运行）

## 复合峰（N个子峰）

复合峰通过组合**任意数量**的高斯子峰创建。这允许各种复杂峰形：

### 常见形状
- **双重峰（2个子峰）**：M形或肩峰
- **三重峰（3个子峰）**：W形或三峰模式
- **Multiple (4+ peaks)**:馒头形(Mantou), Poisson-like, or irregular shapes

### 配置
复合峰可定义为：
```json
{
  "name": "3-peak Composite",
  "type": "composite",
  "peaks": [
    {"RT": 11.5, "height": 1100, "HWH": 0.15},
    {"RT": 12.0, "height": 800, "HWH": 0.15},
    {"RT": 12.5, "height": 600, "HWH": 0.15}
  ]
}
```

### 峰形示例
| 子峰数 | RT分布 | 高度分布 | 结果形状 |
|-----------|-----------------|---------------------|-----------------|
| 2 | 接近的RT | 不同高度 | M形 / 肩峰 |
| 3 | 均匀间隔 | 递减 | W形 / 三重 |
| 4 | 接近的RT | 随机 | 不规则 / 锯齿 |
| 3 | Same RT | Increasing then decreasing | 馒头形 (Bun shape) |

通过调整子峰参数，灵活性允许用户模拟几乎任何峰形。

## 重要注意事项

1. **空白峰保留**：始终保留第一个峰作为空白/参考峰（可以无名）
2. **峰命名**：将化合物重命名为通用名"Peak A"、"Peak B"等，以保持通用性
3. **Markdown表格输出**：在控制台中打印数据为Markdown表格，便于复制粘贴
4. **复合峰**：使用'composite'类型，支持任意数量子峰（1=单个，2+=复杂）
5. **点数推荐**：在交互模式下显示推荐表，帮助用户选择适当的分辨率
6. **灵活形状**：通过调整子峰数量和参数，可以创建M形、馒头形、泊松型或任何不规则形状
7. **坐标轴自定义**：使用xlabel/ylabel/x_unit/y_unit自定义坐标轴标签和单位
8. **CSV导出**：设置`export_csv: true`以`[(t1, s1), (t2, s2), ...]`格式导出完整数据
9. **可点击路径**：始终输出file:///路径，便于直接打开图片
10. **网格线**：设置`grid: false`隐藏，或自定义`grid_linestyle`和`grid_alpha`
11. **CSV标准**：输出遵循RFC 4180格式，使用UTF-8编码

## 文件引用

- **脚本**：`{SKILL_DIR}/scripts/generate_peak.py` - 主生成脚本，支持Markdown表格输出
- **参数参考**：`{SKILL_DIR}/references/parameters.md` - 详细参数文档

## 使用示例

**用户请求**："生成包含5个峰（含1个3子峰复合峰）的峰谱，输出数据为表格"

**响应工作流**：
1. 检查环境
2. 显示点数推荐表
3. 询问峰参数（包括复合峰的子峰数量）
4. 生成带Markdown表格输出的光谱
5. 保存PNG文件并在控制台打印表格

## 自定义选项

用户可以修改：
- 峰数量（包括含N个子峰的复合峰）
- 峰参数（RT、高度、HWHM）
- 复合峰中的子峰数量（2+用于复杂形状）
- 时间范围
- 噪声和基线水平
- 输出文件名和格式
- 图表美学（颜色、标签、网格）
- Markdown表格输出（启用/禁用，采样间隔）
- **坐标轴标题和单位（xlabel、ylabel、x_unit、y_unit）**
- **CSV完整数据导出（export_csv: true/false）**
- **可点击的file:///路径（clickable_path: true/false）**

## JSON 配置示例

```json
{
  "time_range": [2, 12, 1000],
  "peaks": [
    {"name": " ", "RT": 3.5, "height": 1853, "HWHM": 0.12},
    {"name": "Peak A", "RT": 5.0, "height": 8316, "HWHM": 0.15},
    {
      "name": "Peak B (composite)",
      "type": "composite",
      "peaks": [
        {"RT": 6.3, "height": 6653, "HWHM": 0.15},
        {"RT": 6.5, "height": 3259, "HWHM": 0.12},
        {"RT": 6.6, "height": 2877, "HWHM": 0.12}
      ]
    }
  ],
  "baseline": 20,
  "noise_level": 15,
  "output": "custom_peak_plot.png",
  "xlabel": "Time",
  "ylabel": "Response",
  "x_unit": "min",
  "y_unit": "mV",
  "export_csv": true,
  "clickable_path": true,
  "grid": true,
  "grid_linestyle": "solid",
  "grid_alpha": 0.4
}
```

### CSV 输出格式（RFC 4180 标准）
```csv
Time_min,Signal_mV
2.000000,49.782199
2.020040,46.140969
...
```

| 参数 | 值 | 说明 |
|------|------|------|
|  |  | 显示/隐藏网格线 |
|  |  | 网格线样式 |
|  |  | 网格透明度 |
