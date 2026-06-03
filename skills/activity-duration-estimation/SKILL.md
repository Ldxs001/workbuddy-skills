---
name: activity-duration-estimation
tags: ['duration-estimation', 'pert', 'monte-carlo', 'project-management', 'semantic-analysis', 'wbs', 'work-breakdown', 'project-docs', 'html-report']
version: 1.8.1
author: Ldxs
license: MIT
description: 活动历时估算 + WBS工作分解 + 项目文档生成（Activity Duration Estimation & WBS & Project Docs）—— 支持三点估算/蒙特卡洛四种方法 + WBS项目规划与分解 + 项目文档双模式生成（手动空模版/逐节自动）。输出自包含HTML评估报告和项目文档。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/activity-duration-estimation/
external_data_dir: true
trigger: 活动历时估算/三点估算/PERT/蒙特卡洛模拟/工期估算/任务历时/概率估算/β分布/正态分布/历时分析/WBS/WBS分解/项目规划/工作分解/项目分解/分解任务/立项申请书/结项报告/相关方登记册/风险登记册/项目文档/项目模板
trigger_negative: 只是询问概念不执行估算/纯数学公式讨论不含实际任务
faq_quality: improve_qa
---
# activity-duration-estimation — 全周期项目管理

> **WBS项目规划 → 活动历时估算 → 项目文档生成**，三环节完整闭环。
> 全流程由 `scripts/runner.py` 的 `run_full()` 自动编排，
> LLM 只需调用一个函数即可完成项目从分解到文档的全部工作。
> 详细内容拆分到 `references/*.md` 按需加载。

---

## 触发场景

**正向触发**：估算工期/三点估算/PERT/蒙特卡洛/β分布/OMP/紧前关系/FS-SS-FF-SF/CPM甘特图/重叠分析/P50-P90/生成评估报告：估算工期/三点估算/PERT/蒙特卡洛/β分布/OMP/紧前关系/FS-SS-FF-SF/CPM甘特图/重叠分析/P50-P90/生成评估报告

**不触发**：仅概念询问 / 纯数学讨论 / 明确使用其他技能
---

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 能力 | 说明 |
|---|------|------|
| 0 | **WBS工作分解** (子技能) | 基于3个参考模板+LLM自适应填充，支持4种分解方法，100%规则验证，自动衔接估算 |
| 1 | **项目文档生成** (子技能) | 双模式：手动模式输出特化空模版（token≈0）/ 自动模式逐节生成，4个预置模板（立项/结项/相关方/风险） |
| 2 | **四种估算方法** | 直接估算法 / β分布（PERT）估算法 / 正态分布估算法 / 蒙特卡洛模拟法 |
| 3 | **语义分析推荐** | 根据任务类型（建筑/制造/软件/科研/农业等）自动推荐最适估算方法组合 |
| 4 | **外部知识搜索** | 两阶段搜索流程：大模型自判→搜索补充→汇总推荐 |
| 4 | **CPM关键路径分析** | 基于紧前关系的关键路径计算，含ES/EF/LS/LF/总时差，自动识别关键任务 |
| 5 | **多分布蒙特卡洛** | 支持PERT-Beta、三角分布、泊松近似三种分布并行模拟，提供多维度概率评估 |
| 6 | **任务重叠分析** | 自动检测任务时间重叠，输出最大重叠数和最长重叠时段 |
| 7 | **甘特图可视化** | 基于CPM结果的甘特图（SVG），关键路径高亮标注 |
| 8 | **紧前关系规划** | 手动指定/自动规划两种模式，支持FS/SS/FF/SF四种依赖关系 |
| 9 | **HTML评估报告** | 自包含HTML，含甘特图/概率分布/重叠分析图表，有图有表有数据有分析 |
| 10 | **项目文档生成** | 双模式：手动空模版/混合逐节生成；4个P0模板（立项/结项/相关方/风险） |

### 渐进式文件索引

| 文件 | 位置 | 说明 |
|------|------|------|
| `references/methods.md` | 方法详解 | 四种估算方法的完整公式、计算步骤和适用场景 |
| `references/semantic-analysis.md` | 语义分析 | 任务参数提取、分类映射、方法推荐逻辑 |
| `references/wbs-methodology.md` | WBS方法论 | WBS四种分解方法、3个参考模板、递归分解算法、100%规则验证、多格式输出 |
| `references/project-docs-methodology.md` | 项目文档+思维工具 | 双模式设计、模板操作、12个方法论(SWOT/SMART/PDCA/RACI等)含章节映射（详见`thinking-tools.md`） |
| `references/search-integration.md` | 搜索集成 | 两阶段外部知识搜索流程 |
| `references/report-template.md` | 报告模板 | HTML评估报告模板说明 |
| `references/antipatterns.md` | 反模式 | WBS+项目文档反模式 |
| `references/faq.md` | FAQ | WBS+项目文档相关 |
| `references/changelog.md` | 更新日志 | 版本更新记录 |
| `references/templates/` | 模板目录 | 4个预置JSON模板文件 |
| `scripts/runner.py` | 编排层 | PipelineState + run_pipeline() 全流程Python驱动 |

---

## 工作流程

工作流程由 `scripts/runner.py` 自动编排，LLM 无需关心内部阶段顺序。

```python
# 推荐：一键全流程（WBS → 估算 → 报告 → 文档，全环节必做）
from scripts.runner import run_full, PipelineState
result = run_full("帮我规划并估算一个电商后台管理系统")

if result["status"] == "ok":
    state = result["state"]
    print(state.wbs_text_tree)      # ① WBS文本树
    print(state.estimate_summary)   # ② 估算摘要
    print(state.html_report_path)   # ③ HTML报告路径
    print(state.doc_content)        # ④ 项目文档
elif result["status"] == "blocked":
    # 需要LLM提供WBS数据（即使已有OMP参数，WBS也是必做的）
    wbs_data = {"name": "电商后台", "children": [...]}  # LLM提供
    state = PipelineState("帮我规划并估算一个电商后台管理系统")
    state.run_wbs(custom_data=wbs_data)
    result = state.run_full()  # 继续执行估算→报告→文档
else:
    print(result["message"])        # 错误信息
```

**全流程阶段（代码硬编码，不可跳过）：**
1. WBS分解 → `run_wbs()`（全流程模式下必做，LLM提供结构化数据）
2. WBS进入估算门控 → `_wbs_passes_estimation_gate()` 硬校验
3. 紧前关系规划 → `_prompt_llm_for_dependencies()` / 自动FS串联
4. 估算计算 → `run_estimate()`（全Python自动：CPM + MC + 重叠分析）
5. HTML评估报告 → `_generate_html_report()`（全Python自动）
6. 项目文档 → `generate_docs()`（按模板生成立项/结项/风险/相关方文档）

**各环节也可单独调用**（不经过`run_full()`全流程时）：
- 仅有估算需求 → `run_pipeline(mode="estimate")` 或 `state.run_estimate()`
- 仅需文档 → `run_pipeline(mode="docs")` 或 `state.generate_docs()`
- 仅WBS → `run_pipeline(mode="wbs")` 或 `state.run_wbs()`

### LLM交互点

当流程需要LLM推理时，`runner.py` 会抛出 `LLMInteractionRequired` 异常：

| 交互点 | 触发条件 | LLM需提供 |
|--------|---------|-----------|
| `_prompt_llm_for_wbs()` | 模糊需求 | WBS结构化数据 `{name, children: [...]}` |
| `_prompt_llm_for_omp()` | 阶段缺OMP | OMP值 `{o, m, p}` |
| `_prompt_llm_for_dependencies()` | >5个阶段 | 紧前关系或确认自动规划 |

LLM看到异常后按提示提供数据，然后继续执行即可。

---

## 快速开始

```text
场景1：直接估算 — "单阶段任务，乐观3天、最可能6天、悲观15天" → β分布：(3+4×6+15)/6=7天，σ=2天 → 68%概率5~9天
场景2：多阶段CPM — "前端(5/10/20)→后端(8/15/25)→测试(10/20/35)，依赖FS串联" → 总工期~47天，关键路径3任务TF=0 → 出HTML报告
场景3：搜索辅助 — "装配式建筑施工，无OMP，3阶段" → 自判不足→搜索同类→给出典型值→用户确认后估算
场景4：WBS→估算 — "帮我规划并估算一个电商后台管理系统" → Phase -1激活→模板匹配→分解→文本树确认→自动入Phase 0→HTML报告
场景5：项目文档 — "针对电商项目生成立项申请书，手动模式" → 加载模板→特化（填入WBS/CPM引用）→输出空模板MD；或"自动模式，从项目背景开始" → 逐节生成→确认→拼合
```

---

## WBS子技能 — Phase -1：项目规划与工作分解

> 详见 `references/wbs-methodology.md` | `scripts/wbs_engine.py`
> 全流程模式下必做，由 `run_full()` 自动触发。

---

## 项目文档生成子技能 — :project-docs

> 详见 `references/project-docs-methodology.md` | `scripts/project_docs_engine.py`

三种模式：`manual`（空模板，token≈0）/ `mixed`（按章节设 auto/outline/manual，推荐）/ `全自动`（所有节 auto）。
支持模板定制：增/删/改/重排章节、每节独立模式、另存为新模板。

```python
from project_docs_engine import set_section_mode
tpl = load_template("立项申请书")
tpl = set_section_mode(tpl, "项目背景", "auto")    # 自动生成
tpl = set_section_mode(tpl, "预算", "manual")       # 留空手动填
state.generate_docs(mode="mixed", filled_sections={"project_background": "..."})
save_template(tpl, "我的模板", overwrite=True)       # 另存自定义模板
```

**内置模板**：`立项申请书`(11节) / `结项报告书`(10节) / `相关方登记册`(4节) / `风险登记册`(5节)
---

## 子模块详解

各子模块详细说明见 `references/`：
- **Phase 0**: 语义分析与方法推荐 → `references/semantic-analysis.md`
- **Phase 1**: 外部知识搜索 → `references/search-integration.md`
- **Phase 2-3**: 紧前关系规划 + 估算计算（CPM/MC/重叠分析）→ `references/methods.md`
- **Phase 4**: HTML评估报告 → `references/report-template.md`
- **WBS方法论**: → `references/wbs-methodology.md`
- **项目文档**: → `references/project-docs-methodology.md`

| 估算方法 | 公式 | 适用场景 |
|---------|------|---------|
| 三点直接 | (O+M+P)/3 | 快速估算 |
| β分布(PERT) | (O+4M+P)/6, σ=(P-O)/6 | 标准项目管理 |
| 蒙特卡洛 | 2000+次模拟, 多分布并行 | 高不确定性项目 |

---

## 限制与边界

| 维度 | 说明 |
|------|------|
| 任务数量 | 建议 ≤50 个阶段/任务，超过时蒙特卡洛模拟耗时显著增加 |
| OMP值 | 必须满足 O ≤ M ≤ P（乐观≤最可能≤悲观），不满足时会提示修正 |
| 紧前关系 | 不能形成循环依赖（A→B→C→A），系统会检测并报错 |
| 工期单位 | 统一使用同一单位（天/小时/周），混用需先归一化 |
| 网络依赖 | 首次使用需联网搜索（非典型任务），后续使用完全离线 |
| 报告生成 | 输出自包含HTML文件，需要浏览器打开查看，不支持PDF直接导出 |

---

## 版本

**v1.8.0** — 全体系重构：依赖智能规划 + HTML 甘特图 + 多维风险分析 + WBS 深度校验
- `auto_plan_dependencies()`: 接收 phases 列表，解析 WBS 前缀分组
- `wbs_to_dependencies()`: 同父组并行，跨父组串联
- 三个 runner 调用处全部传入 phases 支持智能分组
