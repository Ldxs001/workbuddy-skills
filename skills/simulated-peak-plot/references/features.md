# 功能参考

## 负峰支持
将 height 设为负数即可生成倒峰。Y轴自动缩放包含负区间，标注自动反向指向下方。

```json
{"name": "Negative Peak", "RT": 8.0, "height": -1200, "HWHM": 0.1}
```

## 使用场景示例

### 场景1：混合正负峰
同一谱图中正峰和负峰共存，模拟溶剂峰倒置。
```json
{
  "t_start": 0, "t_end": 12, "scan_rate": 150,
  "peaks": [
    {"name": " ", "RT": 1.2, "height": -800, "HWHM": 0.10, "annotate": false},
    {"name": "Peak A", "RT": 4.5, "height": 1800, "HWHM": 0.08},
    {"name": "Neg Peak", "RT": 7.0, "height": -350, "HWHM": 0.12},
    {"name": "Peak B", "RT": 9.5, "height": 1200, "HWHM": 0.10}
  ],
  "baseline": 10, "noise_level": 5
}
```

### 场景2：簇峰 + 单峰混合
两个紧密相邻的峰簇和孤立峰共存。
```json
{
  "t_start": 0, "t_end": 15, "scan_rate": 100,
  "peaks": [
    {"name": "Peak A", "RT": 3.0, "height": 900, "HWHM": 0.12},
    {
      "name": "Cluster",
      "type": "cluster",
      "peaks": [
        {"RT": 6.0, "height": 500, "HWHM": 0.10},
        {"RT": 6.2, "height": 450, "HWHM": 0.10},
        {"RT": 6.5, "height": 300, "HWHM": 0.12}
      ]
    },
    {"name": "Peak B", "RT": 10.0, "height": 1500, "HWHM": 0.08}
  ],
  "baseline": 0, "noise_level": 8
}
```

### 场景3：融峰 + 负峰 + 单峰
多种峰类型混排。
```json
{
  "t_start": 0, "t_end": 10, "scan_rate": 150,
  "peaks": [
    {"name": " ", "RT": 1.0, "height": -20, "HWHM": 0.08, "annotate": false},
    {"name": "Peak A", "RT": 4.0, "height": 500, "HWHM": 0.10},
    {
      "name": "Merged",
      "type": "merged",
      "peaks": [
        {"RT": 6.0, "height": 300, "HWHM": 0.10},
        {"RT": 6.2, "height": 280, "HWHM": 0.10},
        {"RT": 6.4, "height": 200, "HWHM": 0.12}
      ]
    },
    {"name": "Peak B", "RT": 8.5, "height": 800, "HWHM": 0.10}
  ],
  "baseline": 5, "noise_level": 3
}
```

## 簇峰 vs 融峰

## 簇峰 vs 融峰
| 类型 | type | 标注行为 |
|------|------|----------|
| 簇峰 | cluster | 每个子峰独立标注为 {name}-N |
| 融峰 | merged | 单一标注在合成信号最高点 |

簇峰配置示例：
```json
{
  "name": "Cluster B",
  "type": "cluster",
  "peaks": [
    {"RT": 6.17, "height": 87, "HWHM": 0.08},
    {"RT": 6.52, "height": 64, "HWHM": 0.08}
  ]
}
```

## 扫描速率
总点数 = (t_end - t_start) × scan_rate。scan_rate 默认 100 pts/min。

## 坐标轴自定义
xlabel/ylabel/x_unit/y_unit 控制坐标轴标题和单位。

## CSV 格式
导出遵循 RFC 4180 标准，UTF-8编码，表头 Time_{unit},Signal_{unit}。

## 网格线
grid: true/false, grid_linestyle: solid/dashed/dotted/dashdot, grid_alpha: 0.1-1.0
