# 功能参考

## 负峰支持
将 height 设为负数即可生成倒峰。Y轴自动缩放包含负区间，标注自动反向指向下方。

```json
{"name": "Negative Peak", "RT": 8.0, "height": -1200, "HWHM": 0.1}
```

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
