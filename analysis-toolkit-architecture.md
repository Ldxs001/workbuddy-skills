# analysis-toolkit 架构与规范体系文档

> 完整解读 v1.1.1 版的架构设计、5 大分析场景、Pipeline 数据流与输出规范
> 生成时间：2026-06-08（v1.1.1 最新更新）

---

## 一、系统概览

analysis-toolkit 是一个 **检验检测行业质量控制和数据分析工具箱**，覆盖从原始数据输入到分析报告输出的完整工作流。

```
原始数据 (DataFrame / array-like / dict)
  → 场景分析
       → 室内质控（internal_qc: 精密度 / 质控图 / 重复限性）
       → 室间/批次比对（interlab_qc: ANOVA / Z值 / YYouden 图）
       → 方法验证（method_validation: 标准曲线 / LOD/LOQ / 回收率 / 不确定度）
       → 趋势监控（trend_monitoring: 聚合 / 滚动统计 / Prophet 预测）
       → 分组/PCA/回归/ANOVA（辅助分析）
  → 输出管线（output: markdown 表格 / HTML 报告 / 强制输出钩子）
  → Pipeline 流水线（按场景模板编排多步骤流程）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **场景层** | `scenarios/internal_qc` / `scenarios/interlab_qc` / `scenarios/method_validation` / `scenarios/trend_monitoring` | 面向用户的 5 大分析场景入口函数 |
| **引擎层** | `analysis/regression` / `analysis/anova` / `analysis/pca_analysis` / `analysis/time_series` / `analysis/group_analysis` / `analysis/validation` | 核心算法实现：回归、方差分析、主成分分析、时序预测 |
| **基础设施层** | `core/stats`（统计函数）/ `core/qc_tables`（允差值表）/ `core/loader`（数据加载）/ `core/matrix_ops`（矩阵运算） / `pipeline/`（流水线引擎） / `output/`（输出模块） / `docgen/`（报告生成） | 统计基础、矩阵运算、流水线编排、输出格式化 |

### 1.2 目录结构

```
analysis-toolkit/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据
├── references/                 # 渐进式文档
│   ├── data-interface.md       # 数据接口规范（入参类型、列名约定、输出格式）
│   ├── anova-analysis.md       # ANOVA 方差分析（F临界值查表、单因素实现）
│   ├── regression-validation.md# 回归分析与方法验证（线性/多项式回归、LOD/LOQ、不确定度）
│   ├── time-series.md          # 时序分析与预测（趋势聚合、滚动统计、Prophet 预测）
│   ├── group-analysis.md       # 分组统计分析（分组聚合、阳性率分析、结论生成）
│   ├── pca-analysis.md         # PCA 主成分分析（算法实现、碎石图、散点图、一致性评价）
│   ├── report-generation.md    # 报告生成（Word 报告生成模板与配置）
│   ├── changelog.md            # 版本更新日志
│   ├── antipatterns.md         # 反模式
│   └── permissions.md          # 权限说明
└── scripts/                    # 核心脚本
    ├── __init__.py             # 模块入口
    ├── scenarios/              # 5 大分析场景（面向用户）
    │   ├── __init__.py
    │   ├── internal_qc.py      # 室内质控：精密度/质控图/重复限性
    │   ├── interlab_qc.py      # 室间/批次比对：ANOVA/Z值/YYouden
    │   ├── method_validation.py# 方法验证：标准曲线/LOD/LOQ/回收率/不确定度
    │   └── trend_monitoring.py # 趋势监控：聚合/滚动统计/Prophet 预测
    ├── analysis/               # 核心算法引擎
    │   ├── __init__.py
    │   ├── regression.py       # 线性/多项式回归 + 统计检验 + 可视化
    │   ├── anova.py            # 单因素 ANOVA + F临界值查表
    │   ├── pca_analysis.py     # PCA 主成分分析 + 一致性评价
    │   ├── time_series.py      # 时序聚合 + Prophet 预测
    │   ├── group_analysis.py   # 分组聚合 + 阳性率 + 结论生成
    │   └── validation.py       # LOD/LOQ + 回收率 + 不确定度传递
    ├── core/                   # 基础设施
    │   ├── __init__.py
    │   ├── stats.py            # 统计函数（精密度、合成标准差）
    │   ├── qc_tables.py        # 允差值表（按数量级查找）
    │   ├── loader.py           # 数据加载
    │   └── matrix_ops.py       # 矩阵运算
    ├── pipeline/               # 流水线引擎
    │   ├── __init__.py
    │   ├── engine.py           # Pipeline 核心引擎（step/run/publish）
    │   ├── registry.py         # 流水线模板注册
    │   ├── verify.py           # 流水线校验
    │   └── templates/          # 预置流程模板
    │       ├── default/        # 默认模板（室内质控全流程/室间比对ANOVA/方法验证标准曲线/趋势监控看板）
    │       └── user/           # 用户自定义模板
    ├── output/                 # 输出模块
    │   ├── __init__.py
    │   ├── markdown.py         # Markdown 表格输出
    │   ├── renderer.py         # HTML 报告渲染
    │   └── hooks.py            # 强制输出钩子
    └── docgen/                 # 文档生成
        ├── __init__.py
        └── report_gen.py       # Word 报告生成
```

### 1.3 数据目录结构

```
skills/.standardization/analysis-toolkit/data/
├── reports/                    # 生成的 HTML 报告
│   ├── internal_qc.html        # 室内质控报告
│   ├── interlab_anova.html     # 室间比对报告
│   ├── calibration_curve.html  # 标准曲线报告
│   ├── trend_dashboard.html    # 趋势监控看板
│   └── prophet_forecast.html   # Prophet 预测报告
└── templates/                  # 用户保存的流水线模板（通过 pipeline 保存）
```

---

## 二、五大分析场景

### 2.1 场景 1：室内质控（internal_qc）

**职责**：同一实验室内部，评估方法精密度和稳定性。

| 函数 | 说明 | 返回值 |
|------|------|--------|
| `internal_precision_analysis(data, level_col, value_col, n_replicates)` | 多水平精密度分析 | `{per_level, synthetic_std, synthetic_std_simple, synthetic_rsd, synthetic_rsd_simple}` |
| `control_chart(data, value_col, date_col)` | Levey-Jennings 控制图 | `(figure, stats)` |
| `repeatability_check(results, tolerance_pct)` | 重复限性检查（极差/相对误差/分级判定） | `{max_deviation, is_acceptable, ...}` |

**数据流**：
```
DataFrame → internal_precision_analysis → per_level DataFrame + 合成标准差
                                       ↓
repeatability_check ← 数值列表（平行样）
                                       ↓
control_chart ← DataFrame → Levey-Jennings 图 (SVG/HTML)
```

**合成标准差算法**：
- **标准算法**：`sqrt(∑(n_i-1)SD_i² / ∑(n_i-k))`
- **简单算法**：`sqrt(∑SD_i² / k)`

### 2.2 场景 2：室间比对 / 批次比对（interlab_qc）

**职责**：多家实验室/操作人员/仪器，或多个批次之间的结果比对。

| 函数 | 说明 | 返回值 |
|------|------|--------|
| `interlab_comparison(data, lab_col, value_col)` | ANOVA 方差分析 | `{sst, ssb, ssw, f_value, f_critical, conclusion, ...}` |
| `z_score_analysis(data, lab_col, value_col)` | ISO 13528 Z值分析 | `{z_scores, conclusion, ...}` |
| `youden_plot(data_a, data_b, label_a, label_b)` | YYouden 双实验室比对图 | `figure` |
| `interbatch_analysis(data, batch_col, value_col)` | 批次间 ANOVA | 同 interlab_comparison |

**Z值判定标准**：
| Z值范围 | 判定 |
|:-------:|:----:|
| `\|Z\| ≤ 2` | 满意 |
| `2 < \|Z\| < 3` | 可疑 |
| `\|Z\| ≥ 3` | 不满意 |

### 2.3 场景 3：方法验证（method_validation）

**职责**：标准曲线拟合、检出限/定量限、回收率、曲线不确定度。

| 函数 | 说明 | 关键参数 |
|------|------|----------|
| `calibration_curve(x, y, force_zero, degree)` | 标准曲线拟合（线性/多项式） | degree: 1=线性, >1=多项式 |
| `calc_lod_loq(sigma, slope, standard, sigma_source, calibration_data)` | 检出限/定量限计算 | standard: "gbt27417"/"ich" |
| `calc_recovery(measured, spiked, blank)` | 加标回收率 | blank 默认 0 |
| `curve_uncertainty(calibration_data, sample_responses)` | 曲线不确定度 | EURACHEM/CITAC |

**LOD/LOQ 标准对比**：

| 标准 | LOD | LOQ |
|:----:|:---:|:---:|
| GB/T 27417-2017 | 3σ/b | 3×LOD |
| ICH Q2(R1)/药典 | 3.3σ/b | 10σ/b |

**sigma 来源**：
| 来源 | 说明 | 适用场景 |
|:----:|------|----------|
| `curve` | Sy/x（曲线剩余标准差） | 校准方程法（默认） |
| `instrument` | 仪器精密度 SD | 需单独做精密度试验 |
| `blank` | 空白测定 SD（n≥10） | 空白标准偏差法 |
| `noise` | 基线噪声 SD | 光谱类仪器 |

### 2.4 场景 4：趋势监控（trend_monitoring）

**职责**：长期数据跟踪、聚合分析、风险预警、Prophet 预测。

| 函数 | 说明 | 返回值 |
|------|------|--------|
| `monitoring_dashboard(data, date_col, value_col, group_col, freq, window)` | 趋势监控看板 | HTML 报告 |
| `forecast_alert(data, date_col, value_col, group_col, freq, periods, alert_threshold)` | 风险预警 | `{alert, forecast_growth, ...}` |

**支持的聚合频率**：`D`（日）、`W`（周）、`M`（月）、`Q`（季度）

### 2.5 场景 5：辅助分析

| 函数 | 来源 | 说明 |
|------|:----:|------|
| `group_analyze(df, group_col, metric_col, agg_funcs)` | group_analysis | 分组统计 + 阳性率分析 |
| `group_compare_plot(df, group_col, metric_col)` | group_analysis | 分组对比可视化 |
| `pca_analyze(df, variance_threshold, n_components)` | pca_analysis | 主成分分析 + 碎石图/散点图 |
| `consistency_evaluation(sample_scores, ...)` | pca_analysis | PCA 相关系数一致性评价 |
| `time_trend_analyze(data, date_col, value_col, freq)` | time_series | 时序聚合统计 |
| `rolling_stats(data, date_col, value_col, window)` | time_series | 滚动均值和 ±2σ 警戒线 |
| `prophet_forecast(data, date_col, value_col, periods)` | time_series | Prophet 多品类预测 |
| `linear_regression(x, y, force_zero)` | regression | 一元线性回归 |
| `polynomial_regression(x, y, degree)` | regression | 多项式回归 |
| `regression_stats(x, y, model_result)` | regression | 回归统计检验（r2、F值） |
| `regression_plot(x, y, model_result)` | regression | 回归拟合可视化 |
| `anova_oneway(groups)` | anova | 单因素 ANOVA |

---

## 三、Pipeline 流水线

### 3.1 架构设计

```
输入 (DataFrame / dict / 单值)
  ↓
step("步骤名", func, ...)  → 注册步骤
step("步骤名", func, ...)
  ↓
run(%input%)  → 按顺序执行，步骤间通过引用语法传递数据
  ↓
publish()  → 统一输出：markdown 表格 + HTML 报告
```

### 3.2 数据引用语法

| 语法 | 含义 |
|:----:|------|
| `%input%` | 整个原始输入 |
| `%步骤名%` | 该步骤的完整返回值 |
| `%步骤名.字段名%` | 返回值中的某个字段 |

### 3.3 预置流水线模板

| 模板 | 流程 | 来源 |
|:----:|------|:----:|
| 室内质控全流程 | 录入→精密度分析→质控图→重复限性 | `templates/default/室内质控全流程.json` |
| 室间比对ANOVA | 录入→ANOVA→Z值→YYouden图 | `templates/default/室间比对ANOVA.json` |
| 方法验证标准曲线 | 输入浓度/响应→拟合→LOD/LOQ→不确定度→图 | `templates/default/方法验证标准曲线.json` |
| 趋势监控看板 | 录入→聚合→滚动统计→Prophet预测 | `templates/default/趋势监控看板.json` |

---

## 四、统一输入输出规范

### 4.1 输入类型

| 类型 | 适用场景 |
|------|---------|
| `pd.DataFrame` | 多列结构化数据（原始检测记录、批量数据） |
| `array-like` | 单维度数值序列（浓度、响应值、平行样） |
| `dict` | 传递中间结果（calibration_data, 统计结果） |

### 4.2 列名约定

| 参数 | 说明 | 典型列名 |
|------|------|----------|
| `value_col` | 数值结果列 | "结果", "浓度", "响应值" |
| `group_col` | 分组标识 | "品种", "批次", "实验室" |
| `date_col` | 时间列 | "日期", "检测日期" |
| `level_col` | 水平列 | "水平", "浓度水平" |
| `lab_col` | 实验室列 | "实验室", "操作人" |
| `batch_col` | 批次列 | "批次", "批号" |

### 4.3 输出规范

所有场景函数返回 `dict`，可选包含 `fig`（matplotlib Figure）和 `conclusion`（结论文本）。
所有场景函数通过 `publish()` 自动输出 markdown 表格 + HTML 报告。

可视化函数（5 个）生成自包含 HTML 报告：
- `control_chart` → 室内质控图
- `youden_plot` → YYouden 图
- `calibration_curve` → 标准曲线图
- `monitoring_dashboard` → 趋势监控看板
- `prophet_forecast` → Prophet 预测图

---

## 五、外部依赖

| 包 | 用途 | 必需？ | 说明 |
|:--:|:----:|::----:|------|
| numpy | 数值计算 | 必需 | 核心依赖 |
| pandas | 数据处理 | 必需 | DataFrame 操作 |
| scipy | 统计函数 | 必需 | F临界值、ANOVA |
| matplotlib | 可视化 | 必需 | 所有图表 |
| python-docx | Word 报告 | 可选 | 报告生成 |
| prophet | 时序预测 | 可选 | Facebook Prophet |

---

## 六、版本历史

| 版本 | 日期 | 核心变化 |
|:----:|:----:|:--------|
| 1.0.0 | 2026-06-08 | 初始版本：5 大场景 + Pipeline + 输出模块 |
| 1.1.0 | 2026-06-08 | 新增 `scripts/output/` 标准化输出模块；5 个可视化函数生成 HTML 报告；数据目录迁移至 `.standardization/` |
| 1.1.1 | 2026-06-08 | 修复 SKILL.md 示例代码 API 签名；统一导入路径；修复文档输出表 key 名 |

---

> 本文档基于 analysis-toolkit v1.1.1 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
