# 快速使用

### 加载
```text
使用 分析质控工具包 做室内精密度分析
使用 分析质控工具包 做室间比对
```

### 导入
```python
# 场景函数（推荐，完整分析）
from scripts.scenarios.internal_qc import internal_precision_analysis, control_chart
from scripts.scenarios.interlab_qc import interlab_comparison, z_score_analysis
from scripts.scenarios.method_validation import calibration_curve, calc_lod_loq
from scripts.scenarios.trend_monitoring import monitoring_dashboard

# 细粒度算子（v2 新增）
from scripts.operations import (
    calc_mean, calc_sd, calc_rsd, calc_bias,
    calc_ubias, calc_u_combined, calc_expanded_u,
    calc_te_from_values, calc_te_judgment,
    calc_tcrit,
)
```

### 完整示例

```python
# 1. 加载数据
import pandas as pd
df = pd.read_excel("数据.xlsx")

# 2. 室内精密度分析
from scripts.scenarios import internal_qc
result = internal_qc.internal_precision_analysis(df, "水平", "结果")
print(result["synthetic_std"])  # 合成标准差

# 3. 质控图
fig, stats = internal_qc.control_chart(df, "结果")

# 4. 室间比对
from scripts.scenarios import interlab_qc
comp = interlab_qc.interlab_comparison(df, "实验室", "结果")
print(comp["conclusion"])

# 5. Z值分析
z_df = interlab_qc.z_score_analysis(df, "实验室", "结果")

# 6. 标准曲线
from scripts.scenarios import method_validation
curve = method_validation.calibration_curve(x, y)
lod_loq = method_validation.calc_lod_loq(calibration_data=curve, standard="gbt27417")
```

### 端到端完整流程（推荐顺序）

以下是从数据读取到生成报告的一次性完整流程：


