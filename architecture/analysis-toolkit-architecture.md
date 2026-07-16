<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# analysis-toolkit 架构与规范体系文档

> 完整解读 v2.0.0 版的架构设计、四层算子体系、Pipeline 数据流、标准管理与输出规范
> 生成时间：2026-06-17（v2.0.0 最新更新）

---

## 一、系统概览

analysis-toolkit 是一个 **检验检测行业质量控制和数据分析工具箱**，采用四层算子架构，覆盖从原始数据输入到分析报告输出的完整工作流。

```
原始数据 (DataFrame / array-like / dict)
  → 场景分析
       → 室内质控（internal_qc: 精密度 / 质控图 / 重复限性）
       → 室间/批次比对（interlab_qc: ANOVA / Z值 / YYouden 图）
       → 方法验证（method_validation: 标准曲线 / LOD/LOQ / 回收率 / 不确定度）
       → 趋势监控（trend_monitoring: 聚合 / 滚动统计 / Prophet 预测）
       → 分组/PCA/回归/ANOVA/总误差/不确定度（辅助分析）
  → 四层算子架构
       第1层：细粒度算子（operations/ → 原子级统计/不确定度/总误差/回归算子）
       第2层：组合层（Pipeline → step/run/publish 编排）
       第3层：场景模板（pipeline/templates/ → 预置6大场景模板）
       第4层：自扩展（查标准 → 自动补全算子 → 注册模板）
  → 输出管线（reporting/: markdown / HTML 报告 / report_engine / serve_config）
  → 标准管理（standards/: 标准注册表 / 搜索链 / 模板管理）
```

### 1.1 四层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **场景层** | `scenarios/internal_qc` / `scenarios/interlab_qc` / `scenarios/method_validation` / `scenarios/trend_monitoring` | 面向用户的 4 大分析场景入口函数 |
| **算子层** | `operations/operators`（统计/回归/ANOVA 原子算子） / `operations/total_error`（总误差评估） / `operations/uncertainty`（不确定度传递） / `operations/registry`（算子注册表） / `operations/generator`（缺口自动发现） / `operations/self_test`（公式级自测试） / `operations/viz`（可视化算子） | 细粒度原子算子，可独立调用也可被 Pipeline 组合 |
| **引擎层** | `analysis/regression` / `analysis/anova` / `analysis/pca_analysis` / `analysis/time_series` / `analysis/group_analysis` / `analysis/validation` | 核心算法实现：回归、方差分析、主成分分析、时序预测、方法验证 |
| **基础设施层** | `core/stats`（统计函数）/ `core/qc_tables`（允差值表）/ `core/loader`（数据加载）/ `core/matrix_ops`（矩阵运算） / `core/data_prep`（数据预处理） / `pipeline/`（流水线引擎） / `reporting/`（报告模块） / `standards/`（标准管理） | 统计基础、矩阵运算、流水线编排、输出格式化、标准搜索 |

### 1.2 目录结构

```
analysis-toolkit/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据
├── references/                 # 渐进式文档
│   ├── data-interface.md       # 数据接口规范（v2：必填/条件必填/可选/互斥标注）
│   ├── anova-analysis.md       # ANOVA 方差分析（F临界值查表、单因素实现）
│   ├── regression-validation.md# 回归分析与方法验证（线性/多项式回归、LOD/LOQ、不确定度）
│   ├── time-series.md          # 时序分析与预测（趋势聚合、滚动统计、Prophet 预测）
│   ├── group-analysis.md       # 分组统计分析（分组聚合、阳性率分析、结论生成）
│   ├── pca-analysis.md         # PCA 主成分分析（算法实现、碎石图、散点图、一致性评价）
│   ├── report-generation.md    # 报告生成（Word 报告生成模板与配置）
│   ├── pipeline.md             # 流水线参考（四种用法、模板=场景+报告）
│   ├── quickstart.md           # 快速开始（导入、完整代码示例）
│   ├── standards-interface.md  # 标准接口（标准注册/搜索、模板管理）
│   ├── changelog.md            # 版本更新日志
│   ├── antipatterns.md         # 反模式
│   ├── faq.md                  # 常见问题
│   ├── LICENSE.md              # MIT 许可协议
│   └── permissions.md          # 权限说明
└── scripts/                    # 核心脚本
    ├── __init__.py             # 模块入口
    ├── scenarios/              # 4 大分析场景（面向用户）
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
    │   ├── matrix_ops.py       # 矩阵运算
    │   └── data_prep.py        # 数据预处理（异常值过滤、格式标准化）
    ├── operations/             # 细粒度算子层（v2 新增核心组件）
    │   ├── __init__.py
    │   ├── operators.py        # 原子算子：统计/回归/ANOVA/质控图/Z值
    │   ├── registry.py         # 算子注册表（元信息、发现、分类）
    │   ├── generator.py        # 自动缺口发现 + 算子补全
    │   ├── self_test.py        # 算子公式级自测试
    │   ├── total_error.py      # 总误差评估（TEa/bias/SD 综合计算）
    │   ├── uncertainty.py      # 不确定度传递（GUM 框架 + 合成/扩展）
    │   └── viz.py              # 可视化算子（质控图/散点图/时序图）
    ├── pipeline/               # 流水线引擎
    │   ├── __init__.py
    │   ├── engine.py           # Pipeline 核心引擎（step/run/publish）
    │   ├── registry.py         # 流水线模板注册/查找
    │   ├── hooks.py            # 流水线钩子（输出钩子、验证钩子）
    │   ├── verify.py           # 场景交叉验证
    │   ├── verify_approximation.py # 通用逼近验证（v2 新增：异源算法比对）
    │   └── templates/          # 预置流程模板
    │       ├── default/        # 6 个默认模板
    │       │   ├── 室内质控全流程.json
    │       │   ├── 室间比对ANOVA.json
    │       │   ├── 方法验证标准曲线.json
    │       │   ├── 趋势监控看板.json
    │       │   ├── 总误差评估.json      # v2 新增
    │       │   └── 测量不确定度评定.json # v2 新增
    │       └── user/           # 用户自定义模板
    ├── reporting/              # 报告模块（v2 重构：从 output/ 升级）
    │   ├── __init__.py
    │   ├── markdown.py         # Markdown 表格输出
    │   ├── renderer.py         # HTML 报告渲染
    │   ├── report_engine.py    # 报告引擎（模板=场景+报告独立编排）
    │   ├── hooks.py            # 强制输出钩子
    │   └── serve_config.py     # HTML 内联服务器配置（v2 新增）
    ├── docgen/                 # 文档生成
    │   ├── __init__.py
    │   └── report_gen.py       # Word 报告生成
    └── standards/              # 标准管理（v2 新增模块）
        ├── __init__.py
        ├── registry.py         # 标准注册表（方法原理、判定阈值、公式）
        ├── searcher.py         # 标准搜索链（按场景/方法/标准号搜索）
        └── template_manager.py # 标准模板管理
```

### 1.3 数据目录结构

```
skills/.standardization/analysis-toolkit/data/
└── constraint-list.json        # 算子约束数据
```

---

## 二、四大分析场景

### 2.1 场景 1：室内质控（internal_qc）

**职责**：同一实验室内部，评估方法精密度和稳定性。

| 函数 | 说明 | 返回值 |
|------|------|--------|
| `internal_precision_analysis(data, level_col, value_col[, n_replicates])` | 多水平精密度分析 | `{per_level, synthetic_std, synthetic_std_simple, synthetic_rsd, synthetic_rsd_simple}` |
| `control_chart(data, value_col[, date_col])` | Levey-Jennings 控制图 | `(figure, stats)` |
| `repeatability_check(results[, tolerance_pct])` | 重复限性检查（极差/相对误差/分级判定） | `{max_deviation, is_acceptable, ...}` |

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
| `youden_plot(data_a, data_b[, label_a, label_b])` | YYouden 双实验室比对图 | `figure` |
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
| `calibration_curve(x, y[, force_zero, degree])` | 标准曲线拟合（线性/多项式） | degree: 1=线性, >1=多项式 |
| `calc_lod_loq(sigma, slope[, standard, sigma_source, calibration_data])` | 检出限/定量限计算 | standard: "gbt27417" / "ich" |
| `calc_recovery(measured, spiked[, blank])` | 加标回收率 | blank 默认 0 |
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
| `monitoring_dashboard(data, date_col, value_col[, group_col, freq, window])` | 趋势监控看板 | HTML 报告 |
| `forecast_alert(data, date_col, value_col[, group_col, freq, periods, alert_threshold])` | 风险预警 | `{alert, forecast_growth, ...}` |

**支持的聚合频率**：`D`（日）、`W`（周）、`M`（月）、`Q`（季度）

---

## 三、四层算子架构（v2 核心设计）

### 3.1 架构总览

```
第1层：细粒度算子层（operations/）
  ┌──────────────────────────────────────────────┐
  │ operators.py → 统计/回归/ANOVA/质控图/评级等    │
  │ total_error.py → TEa + bias + SD 综合计算      │
  │ uncertainty.py → GUM 框架不确定度传递           │
  │ viz.py → 可视化算子                             │
  │ registry.py → 注册表（自动注册、分类、元信息）    │
  │ generator.py → 缺口自动发现                     │
  │ self_test.py → 公式级自测试                     │
  └──────────────────────────────────────────────┘
                     ↓
第2层：组合层（Pipeline）
  ┌──────────────────────────────────────────────┐
  │ Pipeline / Step → step() + run() + publish() │
  │ 数据引用语法：%input%, %步骤名%, %步骤名.字段%  │
  └──────────────────────────────────────────────┘
                     ↓
第3层：场景模板（pipeline/templates/default/）
  ┌──────────────────────────────────────────────┐
  │ 6 个预置模板（室内质控/室间比对/方法验证/       │
  │ 趋势监控/总误差评估/测量不确定度评定）           │
  │ 模板 = 场景模板(分析) × 报告模板(可视化)        │
  └──────────────────────────────────────────────┘
                     ↓
第4层：自扩展
  ┌──────────────────────────────────────────────┐
  │ 查标准 → 自动补全算子 → 注册模板               │
  └──────────────────────────────────────────────┘
```

### 3.2 算子注册表

算子通过 `operations/registry.py` 统一注册，每类算子记录以下元信息：

| 字段 | 说明 |
|------|------|
| `name` | 算子名称（如 `calc_mean`, `anova_oneway`） |
| `category` | 分类（statistics / regression / qc / visualization） |
| `input_type` | 输入类型（DataFrame / array-like / scalar） |
| `output_schema` | 输出结构描述 |
| `dependencies` | 依赖的 standards 标准号 |
| `self_test` | 关联的自测试用例 |

算子注册后可通过 `generator.py` 自动发现缺口——检查标准中要求但未实现的算子，自动生成模板代码。

### 3.3 总误差评估（operations/total_error）

v2 新增的核心算子，覆盖 CLIA/PT 总误差框架：

| 函数 | 说明 |
|------|------|
| `total_error_calc(bias, cv, te_a)` | TE = bias + 1.96×CV，对比 TEa 判定 |
| `bias_estimation(reference, measured)` | 偏倚估计（相对/绝对） |
| `sd_estimation(data)` | 标准差估计 |
| `te_summary(bias, cv, te_a)` | 输出 TEa 验证结论 |
| `te_uncertainty_combine(...)` | 总误差与不确定度联合评估 |

### 3.4 不确定度评定（operations/uncertainty）

基于 GUM 框架的不确定度传递：

| 函数 | 说明 |
|------|------|
| `standard_uncertainty(values, type)` | A类/B类不确定度 |
| `combined_uncertainty(components)` | 合成不确定度 |
| `expanded_uncertainty(u_combined, k)` | 扩展不确定度（k=2 默认） |
| `uncertainty_budget(sources)` | 不确定度分量清单 |

### 3.5 自测试体系

`operations/self_test.py` 为每个算子提供公式级自测试：

```
calc_mean  → 验证均值公式
calc_sd    → 验证标准差公式
anova_oneway → 验证 F 值与 p 值
total_error_calc → 验证 TEa 判定边界
```

验证结果记录在 `.standardization/analysis-toolkit/data/constraint-list.json`。

---

## 四、验证体系

### 4.1 场景交叉验证（pipeline/verify.py）

异源实现比对：例如 ANOVA 场景同时用 `scipy.stats.f_oneway` 和内置 F 值查表计算，差异小于容忍度即通过。

| 验证类型 | 方法 | 应用场景 |
|---------|------|---------|
| 场景交叉验证 | 两种独立算法算同一指标比差异 | ANOVA、回归 |
| 逼近验证 | 逆向/特例法验证通用公式 | 总误差、不确定度 |

### 4.2 通用逼近验证（pipeline/verify_approximation.py）

v2 新增：对总误差、不确定度等复杂场景，用退化条件（如 bias=0, CV=0）检验公式在边界处的正确性：

```
退化条件：bias=0, CV=0 → TE=0  ✅
退化条件：CV=0 → TE=bias  ✅
边界条件：总误差刚好等于 TEa → 判定为 borderline
```

---

## 五、标准管理（standards/）

v2 新增的独立模块，提供标准注册、搜索和模板管理。

| 模块 | 功能 |
|------|------|
| `standards/registry.py` | 标准注册表：按标准号/方法名注册判定阈值、公式、适用范围 |
| `standards/searcher.py` | 搜索链：按场景→方法→标准号三级搜索，返回最佳匹配标准 |
| `standards/template_manager.py` | 模板管理：从标准注册表自动生成 Pipeline 模板 |

**示例标准条目**：
```python
{
  "id": "gbt27417",
  "name": "合格评定 化学分析方法确认和验证指南",
  "scenes": ["method_validation"],
  "params": {"lod_factor": 3, "loq_factor": 9},
  "formulas": {"lod": "3*sigma/b", "loq": "9*sigma/b"}
}
```

---

## 六、Pipeline 流水线

### 6.1 架构设计

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

### 6.2 四种用法

| 用法 | 说明 | 适用场景 |
|:----:|------|---------|
| **单独用** | 单步调用算子 | 快速计算单元指标 |
| **组合用** | `Pipeline()` + `step()` 临时拼装 | 一次性分析流程 |
| **场景模板** | `load_template()` 加载内置模板 | 标准分析流程（含 HTML 报告） |
| **自扩展** | 查标准 → 自动补全算子 → 注册模板 | 新标准/新方法接入 |

### 6.3 数据引用语法

| 语法 | 含义 |
|:----:|------|
| `%input%` | 整个原始输入 |
| `%步骤名%` | 该步骤的完整返回值 |
| `%步骤名.字段名%` | 返回值中的某个字段 |

### 6.4 预置流水线模板（6 个）

| 模板 | 流程 | 来源 |
|:----:|------|:----:|
| 室内质控全流程 | 录入→精密度分析→质控图→重复限性 | `templates/default/室内质控全流程.json` |
| 室间比对ANOVA | 录入→ANOVA→Z值→YYouden图 | `templates/default/室间比对ANOVA.json` |
| 方法验证标准曲线 | 输入浓度/响应→拟合→LOD/LOQ→不确定度→图 | `templates/default/方法验证标准曲线.json` |
| 趋势监控看板 | 录入→聚合→滚动统计→Prophet预测 | `templates/default/趋势监控看板.json` |
| 总误差评估 | 计算 TE → 对比 TEa → 判定 | `templates/default/总误差评估.json` |
| 测量不确定度评定 | A类→B类→合成→扩展 | `templates/default/测量不确定度评定.json` |

### 6.5 Pipeline 钩子（pipeline/hooks.py）

Publish 前可注册强制输出钩子：

| 钩子 | 触发时机 | 功能 |
|:----:|---------|------|
| `markdown_hook` | publish 前 | 强制输出 markdown 表格 |
| `html_hook` | publish 前 | 强制输出 HTML 报告 |
| `validation_hook` | publish 前 | 强制运行验证（交叉/逼近） |

### 6.6 模板 = 场景 + HTML 报告包

v2 模板体系将分析逻辑与 HTML 渲染解耦：

```
场景模板        报告模板
  ↓               ↓
load_template("总误差评估")
  ↓
pipe.run(data)  →  数值结果
  ↓
render_from_template("总误差评估", results)  →  HTML
```

`reporting/report_engine.py` 负责报告模板的加载和渲染，`reporting/serve_config.py` 负责 HTML 内联配置。

---

## 七、报告模块（reporting/）

v2 从 `output/` 重构升级为 `reporting/`。

| 模块 | 功能 |
|:----:|------|
| `markdown.py` | Markdown 表格输出（自动适配列宽、对齐） |
| `renderer.py` | HTML 报告渲染（自包含，无外部依赖） |
| `report_engine.py` | 报告引擎：按模板名加载报告模板并渲染 |
| `hooks.py` | 输出钩子（强制 publish 时执行特定输出） |
| `serve_config.py` | HTML 内联服务器配置（图片/数据内联策略） |

---

## 八、统一输入输出规范

### 8.1 输入类型

| 类型 | 适用场景 |
|------|---------|
| `pd.DataFrame` | 多列结构化数据（原始检测记录、批量数据） |
| `array-like` | 单维度数值序列（浓度、响应值、平行样） |
| `dict` | 传递中间结果（calibration_data, 统计结果） |

### 8.2 参数标注规范（v2 新增）

| 标注 | 含义 | 示例 |
|:----:|------|------|
| **`[必填]`** | 必须提供，不填则抛 ValueError | `value_col[必填]` |
| **`[条件必填]`** | 特定场景下必须提供 | `reference[条件必填]`（总误差计算） |
| **`[可选]`** | 不提供则使用默认值 | `blank[可选]`（回收率计算） |
| **`[互斥]`** | 与另一个参数二选一 | `calibration_data` / `sigma+slope` |

### 8.3 列名约定

| 参数 | 说明 | 典型列名 |
|------|------|----------|
| `value_col` | 数值结果列 | "结果", "浓度", "响应值" |
| `group_col` | 分组标识 | "品种", "批次", "实验室" |
| `date_col` | 时间列 | "日期", "检测日期" |
| `level_col` | 水平列 | "水平", "浓度水平" |
| `lab_col` | 实验室列 | "实验室", "操作人" |
| `batch_col` | 批次列 | "批次", "批号" |

### 8.4 输出规范

所有场景函数返回 `dict`，可选包含 `fig`（matplotlib Figure）和 `conclusion`（结论文本）。
所有场景函数通过 `publish()` 自动输出 markdown 表格 + HTML 报告。

可视化函数（5 个）生成自包含 HTML 报告：
- `control_chart` → 室内质控图
- `youden_plot` → YYouden 图
- `calibration_curve` → 标准曲线图
- `monitoring_dashboard` → 趋势监控看板
- `prophet_forecast` → Prophet 预测图

---

## 九、外部依赖

| 包 | 用途 | 必需？ | 说明 |
|:--:|:----:|::----:|------|
| numpy | 数值计算 | 必需 | 核心依赖 |
| pandas | 数据处理 | 必需 | DataFrame 操作 |
| scipy | 统计函数 | 必需 | F临界值、ANOVA |
| matplotlib | 可视化 | 必需 | 所有图表 |
| python-docx | Word 报告 | 可选 | 报告生成 |
| prophet | 时序预测 | 可选 | Facebook Prophet |

---

## 十、版本历史

| 版本 | 日期 | 核心变化 |
|:----:|:----:|:--------|
| 1.0.0 | 2026-06-08 | 初始版本：5 大场景 + Pipeline + 输出模块 |
| 1.1.0 | 2026-06-08 | 新增 `scripts/output/` 标准化输出模块；5 个可视化函数生成 HTML 报告；数据目录迁移至 `.standardization/` |
| 1.1.1 | 2026-06-08 | 修复 SKILL.md 示例代码 API 签名；统一导入路径；修复文档输出表 key 名 |
| 1.2.0 | 2026-06-08 | 新增 `operations/` 算子层：注册表、缺口自动发现、自测试 |
| 1.3.0 | 2026-06-09 | 新增 `standards/` 标准管理模块；Pipeline 模板扩展至 6 个 |
| 1.4.0 | 2026-06-09 | F 临界值表系统性修复：F(5,4)、F(6,14) 等 10+ 处修正 |
| 1.4.1 | 2026-06-09 | 删除 SKILL.md 中多余的渐进式加载模板句 |
| 1.5.0 | 2026-06-17 | skill-standardization 标准化改造：R-01~R-26 审计通过 |
| **2.0.0** | **2026-06-17** | **四层算子架构重构：operations/ 细粒度算子层 + total_error + uncertainty + standards/ 标准管理 + reporting/ 重构 + 逼近验证体系** |

---

> 本文档基于 analysis-toolkit v2.0.0 的 SKILL.md + 15 个 references/*.md + 45+ 核心脚本综合分析整理。
