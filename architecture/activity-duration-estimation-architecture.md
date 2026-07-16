<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# activity-duration-estimation 架构与规范体系文档

> 完整解读 v1.11.0 版的架构设计、七子技能体系、三库隔离模式与全流程编排
> 生成时间：2026-06-06（v1.11.0 最新更新）

---

## 一、系统概览

activity-duration-estimation 是一个 **全周期项目管理工具集**，围绕以下闭环运行：

```
用户需求（自然语言）
  → 语义分析（5W2H 参数提取 + 约束标注 + 任务类型分类）
    → 方法推荐（LLM 自判 → 外部知识搜索补充）
      → WBS 分解（4 种方法 + 3 种参考模板 + 100% 规则验证）
        → 历时估算（四点估算 / β分布 / 正态分布 / 蒙特卡洛四种方法并行）
          → CPM 关键路径分析（四种依赖类型 + 重叠分析 + 甘特图 SVG）
            → 项目文档生成（双模式：手动/混合/全自动 + 4 个 P0 模板）
              → 经济效益分析（ROI/NPV/IRR/BCR/PBP）| 挣值管理（PV/EV/AC/SPI/CPI/EAC）
```

### 1.1 四层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI + HTML 报表 + 设置面板 | 人类可读的文档、命令行交互、可视化报表和配置 |
| **业务层** | analysis_engine / wbs_engine / project_docs_engine / economic_analysis_engine / evm_engine / runner | 估算、分解、文档、分析的核心逻辑 |
| **数据层** | project_knowledge / economic_knowledge / evm_knowledge（三库隔离）+ knowledge_schema | SQLite 知识库 + 标准化接口 |
| **配置层** | settings_manager / settings_server | 运行时设置 + HTML 可视化面板 |

### 1.2 目录结构

```
activity-duration-estimation/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据
├── references/                 # 渐进式文档（15 个文件）
│   ├── methods.md              # 四种估算方法详解
│   ├── wbs-methodology.md      # WBS 分解方法论
│   ├── semantic-analysis.md    # 语义分析架构
│   ├── project-docs-methodology.md  # 项目文档生成方法论
│   ├── economic-analysis-methodology.md  # 经济效益分析方法论
│   ├── evm-methodology.md      # 挣值管理方法论
│   ├── risk-dimensions.md      # 7 类风险维度
│   ├── search-integration.md   # 外部知识搜索集成
│   ├── knowledge-interface.md  # 知识库接口设计
│   ├── thinking-tools.md       # 12 种思维工具
│   ├── report-template.md      # 报表模板
│   ├── antipatterns.md         # 反模式
│   ├── faq.md                  # 常见问题
│   ├── changelog.md            # 版本更新日志
│   └── templates/              # JSON 文档模板
│       ├── 立项申请书.json       # 11 节 P0 模板
│       ├── 结项报告书.json       # 10 节 P0 模板
│       ├── 相关方登记册.json      # 4 节 P0 模板
│       └── 风险登记册.json        # 5 节 P0 模板
└── scripts/                    # 核心脚本（14 个 Python + 4 个 HTML 模板）
    ├── runner.py               # 全流程编排层：PipelineState + run_pipeline()
    ├── analysis_engine.py      # 估算核心引擎：CPM / MC / 重叠分析 / 甘特图 SVG
    ├── wbs_engine.py           # WBS 分解引擎：4 方法 / 3 模板 / 多格式输出
    ├── project_docs_engine.py  # 项目文档生成引擎：双模式 / 12 思维工具
    ├── economic_analysis_engine.py  # 经济效益分析引擎：ROI/NPV/IRR/BCR/PBP
    ├── evm_engine.py           # 挣值管理引擎：PV/EV/AC/SPI/CPI/EAC
    ├── knowledge_schema.py     # 知识库标准化接口：YAML+MD 格式 / 字段映射
    ├── project_knowledge.py    # shared.db 引擎：SQLite+FTS5 查询/写入/外部对接
    ├── economic_knowledge.py   # economic.db 引擎：经济效益独立知识库
    ├── evm_knowledge.py        # evm.db 引擎：挣值管理独立知识库
    ├── risk_dimensions.py      # 7 类风险维度匹配引擎（D1-D7）
    ├── settings_manager.py     # 全局设置 CRUD + CLI 交互
    ├── settings_server.py      # 设置可视化面板 HTTP 服务器
    ├── full_test.py            # 全功能测试套件（100/100 PASS）
    └── templates/              # HTML 报表模板
        ├── report-template.html       # 主报表模板
        ├── economic-report.html       # 经济效益报表模板
        ├── evm-report.html            # 挣值管理报表模板
        └── settings.html              # 设置面板模板
```

---

## 二、七大子技能体系

> ⚡ **统一入口**：`runner.py` 提供 `run_full()` 全流程执行，`run_pipeline()` 分阶段执行。
> 子技能可独立运行：`python scripts/analysis_engine.py --wbs "xxx"`、`python scripts/economic_analysis_engine.py --roi "yyy"`

### 2.1 子技能 A：语义分析与方法推荐

**核心文件**：`analysis_engine.py`

| 功能 | 实现 | 输出 |
|------|------|------|
| 5W2H 参数提取 | 正则 + LLM 双通道提取 | 结构化的 7 维参数表 |
| 三级约束标注 | 约束强度检测（必须 > 建议 > 可选） | 约束矩阵 |
| 任务类型分类 | 6 类（软件/建筑/制造/科研/农业/活动） | 类型标记 |
| 估算方法推荐 | 任务类型 → 自动匹配最优方法组合 | 方法建议 + 置信度 |

**外部知识搜索**（两阶段流程）：
1. **LLM 自判**：LLM 判断是否需要外部知识补充
2. **搜索补充**：WebSearch 获取领域参数 → 融入参数表

### 2.2 子技能 B：WBS 工作分解

**核心文件**：`wbs_engine.py` | **参考**：`references/wbs-methodology.md`

| 功能 | 说明 |
|------|------|
| **4 种分解方法** | 交付成果式 / 生命周期式 / 模块组件式 / 职能领域式 |
| **3 个参考模板** | LLM 自适应填充 |
| **100% 规则验证** | 启发式检查父子节点覆盖度 |
| **4 种输出格式** | 文本树 / Markdown / JSON / SVG 甘特图 |

**关键类**：

| 类/函数 | 说明 |
|---------|------|
| `WBSNode` | WBS 节点：name / level / description / deliverables / criteria / children |
| `WBSResult` | WBS 结果：root_nodes / coverage_ratio / validation_warnings |
| `build_node_tree(tasks, method)` | 按指定方法构建 WBS 树 |
| `validate_coverage(wbs_result)` | 100% 规则验证 |

### 2.3 子技能 C：活动历时估算（四种方法）

**核心文件**：`analysis_engine.py` | **参考**：`references/methods.md`

#### 四种估算方法

| 方法 | 公式 | 特征 | 适用场景 |
|:----:|:----:|:----:|:--------:|
| **直接估算** | (O+M+P)/3 | 简单平均，适合数据充分 | 历史数据丰富的任务 |
| **β分布/PERT** | (O+4M+P)/6 | 加权平均，偏向最可能值 | 软件、研发类任务 |
| **正态分布** | 以 M 为均值，P-O 为范围 | 标准差量化不确定性 | 重复性任务 |
| **蒙特卡洛模拟** | 2000+ 次采样（PERT-Beta / 三角 / 泊松并行） | 概率分布 + 置信区间 | 高风险、高不确定性任务 |

#### CPM 关键路径分析

| 参数 | 含义 |
|:----:|------|
| ES / EF | 最早开始时间 / 最早结束时间 |
| LS / LF | 最晚开始时间 / 最晚结束时间 |
| TF（总浮动） | 不影响总工期的最大延迟 |
| FF（自由浮动） | 不影响后续任务的最大延迟 |

四种依赖类型：FS（完成-开始）/ SS（开始-开始）/ FF（完成-完成）/ SF（开始-完成）

#### 任务重叠分析

使用**扫描线算法**处理并行任务的重叠关系，输出视觉化的甘特图 SVG。

### 2.4 子技能 D：项目文档生成

**核心文件**：`project_docs_engine.py` | **参考**：`references/project-docs-methodology.md`

#### 双模式生成

| 模式 | 行为 | 适用场景 |
|:----:|------|---------|
| **手动模式** | 输出空模板（占位符），用户自行填充 | 仅需框架 |
| **混合模式** | 按章节设 auto / outline / manual | 部分内容需人工确认 |
| **全自动模式** | 所有节 auto，LLM 完整填充 | 快速产出 |

#### 4 个 P0 模板

| 模板 | 节数 | 视图 |
|:----:|:----:|:----:|
| 立项申请书 | 11 | 模板填充 + 思维工具嵌入 |
| 结项报告书 | 10 | 模板填充 + 自动摘要 |
| 相关方登记册 | 4 | 表格生成 |
| 风险登记册 | 5 | 风险表格 + D1-D7 维度匹配 |

#### 12 个思维工具嵌入

SWOT / SMART / PDCA / RACI / 5W1H / 5 Whys / 鱼骨图 / Pareto / Kano / Gantt / PERT / Decision Matrix

### 2.5 子技能 E：经济效益分析

**核心文件**：`economic_analysis_engine.py` | **参考**：`references/economic-analysis-methodology.md`

| 指标 | 说明 | 计算公式 |
|:----:|------|:--------:|
| **ROI** | 投资回报率 | (收益 - 成本) / 成本 × 100% |
| **NPV** | 净现值 | Σ(CF_t / (1+r)^t) - 初始投资 |
| **IRR** | 内部收益率 | NPV = 0 时的折现率（牛顿迭代法） |
| **BCR** | 效益成本比 | 总收益现值 / 总成本现值 |
| **PBP** | 回收期 | 累计现金流转正的年数 |

**输出**：自包含 HTML 报表（Chart.js 图表），含逐年现金流表、多折现率对比。

### 2.6 子技能 F：挣值管理

**核心文件**：`evm_engine.py` | **参考**：`references/evm-methodology.md`

| 参数 | 含义 | 公式 |
|:----:|------|:----:|
| PV | 计划值 | 计划完成工作量 × 预算单价 |
| EV | 挣值 | 实际完成工作量 × 预算单价 |
| AC | 实际成本 | 实际花费 |
| SPI | 进度绩效指数 | EV / PV |
| CPI | 成本绩效指数 | EV / AC |
| EAC | 完工估算 | BAC / CPI |

**双模式**：不纠偏模式（EAC = AC + (BAC - EV)）/ 纠偏模式（EAC = AC + (BAC - EV) / CPI）

**输出**：自包含 HTML 报表（SPI/CPI 趋势图 + 预测曲线）。

### 2.7 子技能 G：三库隔离知识库

**核心文件**：`project_knowledge.py` / `economic_knowledge.py` / `evm_knowledge.py`
**参考**：`references/knowledge-interface.md`

#### 三库架构

```
activity-duration-estimation/
  └── data/
      ├── shared.db       (project_knowledge: 共享知识库 - SQLite FTS5)
      ├── economic.db     (economic_knowledge: 经济效益知识库)
      └── evm.db          (evm_knowledge: 挣值管理知识库)
```

#### 知识条目格式（YAML + Markdown）

```yaml
---
id: "ade-001"
type: "industry_standard"
source: "PMBOK_6th"
tags: [dur_est, pert, cpm]
---

## 三点估算公式

β分布（PERT）：(O + 4M + P) / 6
```

**标准化接口**（`knowledge_schema.py`）：
| 函数 | 说明 |
|------|------|
| `entry_to_markdown(entry)` | 知识条目 → Markdown 文档 |
| `parse_markdown_entry(md_text)` | Markdown → 知识条目 |
| `query_knowledge(db_path, query)` | 跨库查询 |
| `skill_registry(query)` | 自动判断查询目标库 |

---

## 三、全流程编排

### 3.1 PipelineState

`runner.py` 的核心状态机：

```python
@dataclass
class PipelineState:
    phase: str                    # 当前阶段：parse / wbs / estimate / cpm / report / doc
    task_description: str        # 原始任务描述
    parsed_params: dict          # 5W2H 解析结果
    wbs_result: Optional[WBSResult]     # WBS 分解结果
    estimation_result: Optional[dict]   # 估算结果
    cpm_result: Optional[dict]         # CPM 分析结果
    report_html: Optional[str]         # HTML 报表
    docs: Optional[dict]               # 项目文档
    errors: List[str]                  # 错误日志
```

### 3.2 6 阶段执行顺序

```
Phase 1: parse      — 语义分析 + 5W2H 提取 + 任务类型分类 + 方法推荐
Phase 2: wbs        — WBS 分解（4 方法选一 + 100% 规则验证）
Phase 3: estimate   — 四点估算 / β分布 / 正态 / 蒙特卡洛并行
Phase 4: cpm        — CPM 关键路径 + 重叠分析 + 甘特图 SVG
Phase 5: report     — 自包含 HTML 报表生成
Phase 6: docs       — 项目文档生成（混合模式概率最大）
```

### 3.3 LLM 交互点异常

`LLMInteractionRequired` 异常在以下场景被触发，通知 LLM 参与：
- `parse` 阶段：5W2H 参数不完整 → 询问用户补充
- `wbs` 阶段：分解方法不确定 → 询问用户偏好
- `estimate` 阶段：参数缺失 → 询问用户或搜索外部知识
- `docs` 阶段：模板选择 → 询问用户

---

## 四、核心设计原则

### D1: 零外部依赖
所有脚本仅使用 Python 标准库 + SQLite，零 pip install。
**目的**：降低安装门槛，即装即用。

### D2: 子技能隔离
七个子技能各自维护独立代码和知识库，通过 `runner.py` 统一调度。
**目的**：每个子技能可独立使用，也可组合成全流程。

### D3: 自包含输出
所有报表（经济效益分析、挣值管理、主报告）均为自包含 HTML，无外部依赖。
**目的**：无需部署服务器，双击 HTML 即可查看。

### D4: 知识库即文档
`references/knowledge-interface.md` 定义了 YAML+MD 双格式标准，知识条目可读、可写、可导出。
**目的**：知识库不仅是存储，也是人类可读的参考文档。

### D5: 三阶段文档生成
手动 → 混合 → 全自动，覆盖从"仅框架"到"完整产出"全 spectrum。
**目的**：适应不同用户对文档完成度的需求差异。

---

## 五、配置体系

`settings_manager.py` 统一管理，JSON 格式持久化，支持 CLI 和 HTML 面板两种修改方式。

| 配置项 | 默认值 | 说明 |
|:------:|:------:|------|
| `web_search_mode` | auto | 外部知识搜索模式（auto / manual） |
| `kb_collect_mode` | auto | 知识库采集模式（auto / manual） |
| `kb_query_mode` | auto | 知识库查询模式（auto / manual） |
| `doc_template` | null | 项目文档模板选择 |
| `doc_write_mode` | auto | 文档写入模式（auto / manual / template） |

HTML 面板支持实时修改并保存。

---

## 六、配置体系

*（本节延续上一节标题的编号，实为同一节）*

settings_manager.py 支持以下交互方式：

| 方式 | 命令 |
|:----:|------|
| CLI 查看 | `python scripts/settings_manager.py --show` |
| CLI 设置 | `python scripts/settings_manager.py --set web_search_mode=manual` |
| HTML 面板 | 启动服务 `python scripts/settings_server.py` → 浏览器打开 localhost 端口 |

---

## 七、风险维度体系

**核心文件**：`risk_dimensions.py` | **参考**：`references/risk-dimensions.md`

7 类风险维度（D1-D7）：

| 维度 | 范围 | 输出 |
|:----:|------|:----:|
| D1 技术风险 | 技术实现不确定性 | 概率 × 影响矩阵 |
| D2 进度风险 | 工期延误可能性 | 关键路径浮动预警 |
| D3 成本风险 | 预算超支概率 | 蒙特卡洛成本分布 |
| D4 资源风险 | 人力/设备短缺 | 资源负荷热力图 |
| D5 质量风险 | 质量不达标 | 缺陷预测 |
| D6 外部风险 | 供应链/政策变化 | 情景树 |
| D7 管理风险 | 沟通/决策失效 | RACI 缺口 |

---

## 八、完整测试

`full_test.py` 是全功能测试套件，100/100 PASS，覆盖：

| 测试类别 | 数 | 说明 |
|:--------:|:--:|------|
| WBS 分解 | 12 | 4 方法 × 3 场景 |
| 估算方法 | 16 | 4 方法 × 4 边界条件 |
| CPM 分析 | 8 | 4 依赖类型 × 2 拓扑 |
| 蒙特卡洛模拟 | 6 | 3 分布 × 2 采样规模 |
| 经济效益 | 10 | 5 指标 × 2 场景 |
| 挣值管理 | 8 | 2 模式 × 4 场景 |
| 项目文档 | 12 | 3 模式 × 4 模板 |
| 风险维度 | 8 | 7 维度 + 组合 |
| 知识库接口 | 10 | CRUD × 3 库 |
| 边界鲁棒性 | 10 | 空/零/超大值 |

---

> 本文档基于 activity-duration-estimation v1.11.0 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
