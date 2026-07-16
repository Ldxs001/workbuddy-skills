<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# round-robin-allocator 架构与规范体系文档

> 完整解读 v1.6.0 版的架构设计、均匀轮转分配算法、四种后处理模式与可视化系统
> 生成时间：2026-06-11（v1.6.0 最新更新）

---

## 一、系统概览

round-robin-allocator 是一个 **均匀轮转分配工具**，围绕以下闭环运行：

```
用户输入（N 对象、T 轮次、K 选项、各选项比例）
  → 基数分配（按比例计算每轮每选项基准次数）
    → 轮转填充（Round-robin 轮转，最大化覆盖多样性）
      → 后处理（四种模式调整重复分布）
        → 结果输出（CSV + Markdown + HTML 可视化报表）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + CLI + HTML 可视化 | 人类可读文档、命令行交互、交互式图表 |
| **业务层** | allocator / main / visualizer | 分配算法、入口编排、结果呈现 |
| **数据层** | CSV + HTML 文件（技能数据目录） | 分配结果持久化 |

---

## 二、核心模块说明

### 2.1 allocator.py（分配引擎）

**职责**：实现均匀轮转分配的核心算法。

**入口函数**：
- `allocate(objects, rounds, options, ratios)` — 主分配函数
- 流程：基数计算 → 轮转填充 → 后处理 → 结果验证

**四种后处理模式**：

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| **none** | 不处理，保留原始轮转结果 | 允许一定程度的重复 |
| **swap** | 同一对象在相邻轮次中分配到相同选项时，与同轮次其他对象交换 | 严禁连续重复 |
| **redistribute** | 将必须调整的分配重新分配给同轮次中该选项配额未满的其他对象 | 配额严格优先 |
| **minimize** | 综合 swap + redistribute 的优点，在配额约束内最小化整体重复 | 最优均匀分布 |

**核心算法**：
```
1. 基数轮次：按 options 数量和 ratios 比例，计算每轮每选项的分配次数
2. Round-robin 填充：按选项顺序轮转分配给各对象，保证同一轮次内各选项均匀分布
3. 后处理修正：根据选择的后处理模式，修正重复分布
```

### 2.2 main.py（入口编排）

**职责**：CLI 入口 + 参数解析 + 流程编排。

**参数**：
- `--objects` / `-N` — 对象列表或数量
- `--rounds` / `-T` — 轮次数
- `--options` / `-K` — 选项列表或数量
- `--ratios` / `-R` — 各选项比例
- `--post-process` / `-P` — 后处理模式（none/swap/redistribute/minimize）
- `--output` / `-o` — 输出格式（csv/md/html/all）

### 2.3 visualizer.py（可视化引擎）

**职责**：生成分配结果的可视化报表。

**输出格式**：
- **CSV** — 结构化数据，可用于进一步分析
- **Markdown** — 人类可读的文本表格
- **HTML** — 自包含交互式图表（Chart.js 渲染）

**可视化内容**：
- 每轮次分配矩阵（热力图）
- 各对象分配分布柱状图
- 各选项覆盖度统计

---

## 三、数据流

```
用户参数
  ↓
main.py（参数解析 + 校验）
  ↓
allocator.py
  ├── 基数计算：ratios → round_base_counts
  ├── 轮转填充：round-robin → raw_allocation
  └── 后处理：四种模式 → final_allocation
  ↓
visualizer.py
  ├── CSV 导出（allocation_result.csv）
  ├── Markdown 表格（allocation_result.md）
  └── HTML 图表（allocation_result.html）
  ↓
输出路径（技能数据目录）
```

---

## 四、结果验证

分配完成后自动执行以下验证：

| 验证项 | 规则 |
|--------|------|
| 总数正确性 | 总分配次数 = N × T |
| 配额合规 | 每个选项的分配次数符合 ratios 比例 |
| 对象完整性 | 每个对象在每轮中都分配到选项 |

---

## 五、依赖

- Python 3.11+（推荐 3.13.12 managed）
- 无外部 pip 依赖（仅使用标准库）
- HTML 可视化使用 Chart.js（CDN 加载）

---

## 六、版本历史

| 版本 | 日期 | 核心变化 |
|------|------|---------|
| 1.6.0 | 2026-06-11 | 当前版本 |
| 1.0.0 | 2026-05-xx | 初始版本：基础分配 + 四种后处理模式 |
