---
name: analysis-toolkit
version: 1.1.1
author: wUwproject
license: MIT
description: 检验检测行业质量控制和数据分析工具箱。覆盖室内质控、室间比对、批次间比对、方法验证、趋势监控五大场景。方法通用，跨领域适用。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/analysis-toolkit/
title: 分析质控工具包
summary: 检验检测行业质量控制和数据分析工具箱。覆盖室内质控、室间比对、批次间比对、方法验证、趋势监控五大场景。方法通用，跨领域适用。
trigger: ['分析', '质控', '质量控制', '室内质控', '精密度', '室间比对', '批次比对', '方法验证', '标准曲线', '检出限', '趋势监控', '预测', 'PCA', '主成分分析', 'ANOVA', '方差分析', '回归', '拟合', '质控图', '回收率', '不确定度', 'Z值', 'YYouden 图', '一致性评价']
trigger_negative: ['农产品检测', '农产品', '食品检测']
read_when: ['需要做质控分析', '需要做方法验证', '需要多组比对分析', '需要时序预测', '需要自动生成分析报告']
tags: ['qc', 'analysis', 'statistics', 'validation']
h1_position: true
trigger_quality: add_triggers
external_data_dir: true
meta_field_sync: true
antipattern_detail: add_detail
faq_quality: improve_qa
---
# analysis-toolkit：分析质控工具包

**触发词**：精密度、室内质控、室间比对、方法验证、标准曲线、趋势监控、Prophet 预测、PCA分析
**适用场景**：室内质控 | 室间比对 | 方法验证 | 趋势监控 | PCA分析 | 报告生成

> **场景驱动的检验检测分析工具箱** — 不是给你一堆函数，而是给你一套完整的分析工作流。

## 触发场景

当用户提出以下类型请求时，应触发本技能：

**自然语言（推荐）**：
- [帮我做室内质控分析 / 算一下精密度 / 画个质控图]
- [做几个实验室比对 / 算ANOVA和Z值 / 画YYouden 图]
- [做方法验证 / 算检出限定量限 / 拟合标准曲线]
- [做趋势监控 / 预测未来数据 / 跑Prophet 预测]
- [做PCA主成分分析 / 一致性评价]
- [帮我生成质控报告 / 数据分析报告]

**技术关键词**：
- [用 analysis-toolkit 做质控 / 精密度分析 / 室间比对]
- [ANOVA方差分析 / 方法验证 / 标准曲线拟合]
- [LOD/LOQ计算 / 回收率 / 不确定度评估]
- [时序分析 / 趋势预测 / 质控图 / Z值判定]

## 核心场景

> 📚 **渐进式加载**：本技能采用渐进式MD体系，`SKILL.md`为入口，详细内容拆分到`references/*.md`按需加载。

### 1️⃣ 室内质控（Internal QC）

同一实验室内部，评估方法精密度和稳定性。

| 功能 | 说明 |
|------|------|
| **多水平精密度分析** | 每水平SD/RSD/均值/中位数，合成标准差（正规算法 + 简单算法） |
| **重复限性检查** | 平行样极差检查、相对误差、允许值分级判定 |
| **质控图** | Levey-Jennings 控制图，±1σ/±2σ/±3σ限，失控点标注 |

→ `references/data-interface.md`

### 2️⃣ 室间比对（Inter-lab QC）

多家实验室/操作人员/仪器之间的结果比对。

| 功能 | 说明 |
|------|------|
| **ANOVA方差分析** | SST/SSB/SSW分解，F值计算 |
| **F临界值查表判定** | α=0.05，支持 df₁=1~24, df₂=1~20 |
| **Z值分析** | 基于ISO 13528的Z值计算与判定（满意/可疑/不满意） |
| **YYouden 图** | 双实验室比对可视化 |

→ `references/anova-analysis.md`

### 3️⃣ 批次间比对（Inter-batch QC）

不同批次的检测结果一致性检验。

| 功能 | 说明 |
|------|------|
| **批次ANOVA** | 同室间比对的ANOVA流程，应用于批次维度 |
| **重复限性** | 批次内重复性检查 |
| **允许值判定** | 根据数量级自动查找允许偏差 |

→ `references/anova-analysis.md`

### 4️⃣ 方法验证（Method Validation）

标准曲线、检出限、定量限、回收率、不确定度。

| 功能 | 说明 |
|------|------|
| **标准曲线拟合** | 线性/多项式，支持强制过零点 |
| **检出限/定量限** | 支持GB/T 27417和ICH两种标准，sigma 来源支持 curve/仪器/空白/噪声 |
| **加标回收率** | 多水平回收率计算 |
| **曲线不确定度** | EURACHEM/CITAC标准曲线分量 u_rel(curve) |
| **一致性评价** | PCA相关系数法 |

→ `references/regression-validation.md`

### 5️⃣ 趋势监控（Trend Monitoring）

长期数据跟踪与风险预警。

| 功能 | 说明 |
|------|------|
| **时序聚合分析** | 按日/周/月聚合，趋势图绘制 |
| **滚动统计** | 滚动均值、标准差、±2σ警戒线 |
| **Prophet 预测** | 多品类/整体预测，95%置信区间 |

→ `references/time-series.md`

## 快速使用

### 加载
```text
使用 分析质控工具包 做室内精密度分析
使用 分析质控工具包 做室间比对
```

### 导入
```python
from scripts.scenarios.internal_qc import internal_precision_analysis, control_chart
from scripts.scenarios.interlab_qc import interlab_comparison, z_score_analysis
from scripts.scenarios.method_validation import calibration_curve, calc_lod_loq
from scripts.scenarios.trend_monitoring import monitoring_dashboard
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


## 流水线（Pipeline）

这个工具箱支持三种用法，从简单到灵活：

- **单独用（Standalone）** — 单步调用
- **组合用（Ad-hoc Pipeline）** — 用 `pipeline()` + `step()` 临时拼一个流程
- **按场景用（Template Pipeline）** — 加载内置模板，跑完整场景

详情见 → `references/pipeline.md`

## 数据格式

统一接受 `pandas.DataFrame`，日期列为 `datetime64`。

| 参数 | 说明 | 示例值 |
|------|------|--------|
| `value_col` | 数值结果列 | "结果", "浓度", "响应值" |
| `group_col` | 分组标识列 | "品种", "实验室", "批次" |
| `date_col` | 时间列 | "日期", "检测日期" |
| `level_col` | 水平列（精密度） | "水平", "浓度水平" |
| `result_col` | 二分类结果列 | "合格/不合格", "阳性/阴性" |


## 核心能力

→ 详见 `references/antipatterns.md`
→ 详见 `references/faq.md`
- analysis-toolkit 的核心功能 1
- analysis-toolkit 的核心功能 2
- analysis-toolkit 的核心功能 3
> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。


### 渐进式文件索引

| 文件 | 位置 | 说明 |
|------|------|------|
| `references/data-interface.md` | 数据接口规范 | 标准输入输出格式、字段约定示例 |
| `references/anova-analysis.md` | ANOVA方差分析 | F临界值查表、单因素ANOVA实现 |
| `references/regression-validation.md` | 回归分析与方法验证 | 线性/多项式回归、LOD/LOQ、不确定度 |
| `references/time-series.md` | 时序分析与预测 | 趋势聚合、滚动统计、Prophet 预测 |
| `references/group-analysis.md` | 分组统计分析 | 分组聚合、阳性率分析、结论生成 |
| `references/pca-analysis.md` | PCA主成分分析 | PCA算法实现、碎石图、散点图 |
| `references/report-generation.md` | 报告生成 | Word 报告生成模板与配置 |
| `references/antipatterns.md` | 反模式 | 常见错误做法与正确做法 |
| `references/faq.md` | 常见问题 | 数据格式、错误处理等常见问答 |
| `references/permissions.md` | 权限说明 | 操作类型与风险等级 |

## 工作流程
1. 理解用户需求
2. 规划执行步骤
3. 调用相关工具/脚本
4. 返回结果给用户
> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。