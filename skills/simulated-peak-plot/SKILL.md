---
name: simulated-peak-plot
version: 2.4.0
description: Generate simulated peak plots with customizable Gaussian peaks for chromatography, spectroscopy, or any signal visualization. Use when user asks to generate peak spectra, simulate signal data, create peak plots, visualize retention times, or output data as Markdown table. Supports custom peak parameters, noise levels, baseline settings, composite peaks (N sub-peaks combined), customizable axis titles/units, CSV full data export, clickable file:// path output, and CSV data import from device exports.
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

# Simulated Peak Plot Skill v2.3.2

Generate simulated peak plots with Gaussian peaks, customizable parameters, realistic noise, Markdown table output, and CSV data export.

## Overview

This skill creates simulated peak spectra for educational, testing, or presentation purposes. It supports:
- Multiple peak types including **composite peaks** (any number of sub-peaks combined)
- Customizable time range, baseline, and noise
- **Customizable axis titles and units** (X/Y labels, mV/V/absorbance/etc.)
- **CSV complete data export** with full data points
- **Clickable file:/// path** for easy image opening
- Markdown table data output (printed in console)
- Interactive configuration with point recommendations

## New Features (v2.1)

### 1. Customizable Axis Titles
- `xlabel`: X-axis title (default: 'Time')
- `ylabel`: Y-axis title (default: 'Response')
- `x_unit`: X-axis unit (default: 'min')
- `y_unit`: Y-axis unit (default: 'mV', can be 'V', 'absorbance', etc.)

### 2. CSV Full Data Export
- Export complete dataset as CSV file
- Format: `[(t1, s1), (t2, s2), ...]`
- **RFC 4180 标准格式**：UTF-8编码，逗号分隔，数值型数据
- Header: `Time_<unit>,Signal_<unit>`
- 输出文件路径 with `file:///` URI for clicking

### 3. Customizable Grid Lines
- `grid`: 是否显示网格线 (default: True)
- `grid_linestyle`: 网格线样式 - `'solid'`, `'dashed'`, `'dotted'`, `'dashdot'`
  - solid: 实线 (-)
  - dashed: 虚线 (--)
  - dotted: 点线 (:)
  - dashdot: 点划线 (-.)
- `grid_alpha`: 网格线透明度 (default: 0.6)

### 4. CSV Data Import (Device Export)
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

### 3. Clickable Image Path
- Automatically outputs `file:///C:/path/to/image.png`
- Click directly to open in default viewer

## Workflow

### 1. Environment Check

**Always start by checking the environment:**

```bash
# Check Python availability
python --version

# Check required packages
python -c "import numpy; import matplotlib; print('All packages available')"
```

If packages are missing, instruct user to install:
```bash
pip install numpy matplotlib
```

### 2. Parameter Configuration (Interactive Dialogue)

Engage in dialogue to configure parameters. **Show the Point Recommendation Table** first.

**Time range:**
- Start: 5 min
- End: 15 min

**Default peaks (including composite with 3 sub-peaks):**
- Blank: RT=5.8, Height=300, HWHM=0.1
- Peak A: RT=7.7, Height=1500, HWHM=0.08
- Peak B: RT=10.3, Height=1200, HWHM=0.12
- Composite (3 sub-peaks): RT=11.5/12.0/12.5, Heights=1100/800/600, HWHM=0.15

**Signal settings:**
- Baseline: 20
- Noise level: 8

**Output:** PNG + Markdown table (printed to console)

Ask user:
1. "How many peaks do you want? (default: 4 including blank peak and composite)"
2. "For each peak, provide: Name, Retention Time (RT), Height, HWHM"
3. "For composite peaks: Enter number of sub-peaks (2+=composite), then provide RT/Height/HWHM for each sub-peak"
4. "Do you want to modify baseline or noise level? (default: baseline=20, noise=8)"
5. "Do you want to print data as Markdown table? (default: y)"
6. "Sample interval for table (print every N-th point)? (default: 20)"
7. "Do you want to change output filename? (default: simulated_peak)"
8. "Customize axis labels? (xlabel/ylabel, x_unit, y_unit) [default: Time/min, Response/mV]"
9. "Export complete data as CSV? (y/n) [default: n]"
10. "Show grid lines? (y/n) [default: y]"
    - If yes: "Grid line style? (1=solid, 2=dashed, 3=dotted, 4=dashdot) [default: 2]"
    - If yes: "Grid transparency (0.1-1.0)? [default: 0.6]"
11. Clickable file:/// path is always output for easy opening

### 3. Point Recommendation Table

Display a recommendation table based on:
- Time range duration
- Number of peaks
- Baseline variation
- Peak sharpness (HWHM)

**Recommendation formula:**
```
points = max(500, duration * peaks * sharpness_factor * 2)
```

Typical recommendations:

| Duration (min) | Peaks | Baseline | Suggested Points |
|----------------|-------|----------|-------------------|
| 5-10 | 2-4 | Low (<50) | 500-800 |
| 10-20 | 4-8 | Medium (50-100) | 800-1200 |
| 20-30 | 8+ | High (>100) | 1200-2000 |
| 30+ | Any | Any | 2000+ |

Also show calculation:
```
For your settings:
Duration = [t_end - t_start] min
Peaks = [num_peaks]
Baseline = [baseline]
Recommended points = max(500, [calculated_value])
```

### 4. Generate Plot and Output Data

Use the `{SKILL_DIR}/scripts/generate_peak.py` script:

```bash
python {SKILL_DIR}/scripts/generate_peak.py --interactive
```

The script will:
1. Generate the peak plot with annotations
2. Save PNG file with plot
3. Print data as Markdown table in console (optional)

### 5. Output

The script will:
- Generate the spectrum plot (PNG)
- **Output clickable file:/// path** for direct opening
- **Export CSV file with full data** (if enabled)
- Print time and signal data as Markdown table in console (optional)
- Display plot (if running in interactive environment)

## Composite Peak (N Sub-Peaks)

Composite peaks are created by combining **any number** of Gaussian peaks. This allows for various complex peak shapes:

### Common Shapes
- **Doublet (2 peaks)**: M-shaped or shoulder peaks
- **Triplet (3 peaks)**: W-shaped or triple-peak patterns
- **Multiple (4+ peaks)**:馒头形(Mantou), Poisson-like, or irregular shapes

### Configuration
Composite peaks can be defined as:
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

### Examples of Peak Shapes
| Sub-peaks | RT Distribution | Height Distribution | Resulting Shape |
|-----------|-----------------|---------------------|-----------------|
| 2 | Close RTs | Different heights | M-shape / Shoulder |
| 3 | Evenly spaced | Gradually decreasing | W-shape / Triple |
| 4 | Close RTs | Random | Irregular / Jagged |
| 3 | Same RT | Increasing then decreasing | 馒头形 (Bun shape) |

The flexibility allows users to simulate almost any peak shape by adjusting sub-peak parameters.

## Important Notes

1. **Blank peak preservation**: Always keep the first peak as a blank/reference peak (can be unnamed)
2. **Peak naming**: Rename compounds to generic "Peak A", "Peak B", etc. for universality
3. **Markdown table output**: Print data as Markdown table in console for easy copy-paste
4. **Composite peaks**: Use 'composite' type with any number of sub-peaks (1=single, 2+=complex)
5. **Point recommendation**: Show recommendation table in interactive mode to help users choose appropriate resolution
6. **Flexible shapes**: By adjusting sub-peak count and parameters, you can create M-shape,馒头形, Poisson-like, or any irregular shape
7. **Axis customization**: Use xlabel/ylabel/x_unit/y_unit to customize axis labels and units
8. **CSV export**: Set `export_csv: true` to export complete data with `[(t1, s1), (t2, s2), ...]` format
9. **Clickable path**: file:/// path is always output for easy image opening
10. **Grid lines**: Set `grid: false` to hide, or customize `grid_linestyle` and `grid_alpha`
11. **CSV Standard**: Output follows RFC 4180 format with UTF-8 encoding

## File References

- **Script**: `{SKILL_DIR}/scripts/generate_peak.py` - Main generation script with Markdown table output
- **Parameters reference**: `{SKILL_DIR}/references/parameters.md` - Detailed parameter documentation

## Example Usage

**User request**: "Generate a peak spectrum with 5 peaks including one 3-sub-peak composite, output data as table"

**Response workflow**:
1. Check environment
2. Show point recommendation table
3. Ask for peak parameters (including sub-peak count for composite)
4. Generate spectrum with Markdown table output
5. Save PNG file and print table in console

## Customization

Users can modify:
- Number of peaks (including composite peaks with N sub-peaks)
- Peak parameters (RT, height, HWHM)
- Sub-peak count in composite (2+ for complex shapes)
- Time range
- Noise and baseline levels
- Output filename and format
- Plot aesthetics (colors, labels, grid)
- Markdown table output (enable/disable, sample interval)
- **Axis titles and units (xlabel, ylabel, x_unit, y_unit)**
- **CSV full data export (export_csv: true/false)**
- **Clickable file:/// path (clickable_path: true/false)**

## JSON Configuration Example

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

### CSV Output Format (RFC 4180 Standard)
```csv
Time_min,Signal_mV
2.000000,49.782199
2.020040,46.140969
...
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| `grid` | `true` | Show/hide grid lines |
| `grid_linestyle` | `solid/dashed/dotted/dashdot` | Grid line style |
| `grid_alpha` | `0.1-1.0` | Grid transparency |
