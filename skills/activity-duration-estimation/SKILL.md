---
name: activity-duration-estimation
tags: ['duration-estimation', 'pert', 'monte-carlo', 'project-management', 'semantic-analysis', 'wbs', 'work-breakdown', 'project-docs', 'html-report', 'settings', 'knowledge-base', 'economic-analysis', 'evm', 'earned-value']
version: 1.11.0
author: wUwproject
license: MIT
description: 活动历时估算 + WBS工作分解 + 项目文档生成 + 经济效益分析 + 挣值管理（Activity Duration Estimation & WBS & Project Docs & Economic Analysis & EVM）—— 支持三点估算/蒙特卡洛四种方法 + WBS项目规划与分解 + 项目文档双模式生成（手动空模版/逐节自动）+ ROI/NPV/IRR/BCR 经济效益分析 + PV/EV/AC/SPI/CPI 挣值管理。三库隔离架构：shared.db + economic.db + evm.db。输出自包含HTML评估报告、经济效益分析报告和挣值分析报告。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/activity-duration-estimation/
external_data_dir: true
trigger: 活动历时估算/三点估算/PERT/蒙特卡洛模拟/工期估算/任务历时/概率估算/β分布/正态分布/历时分析/WBS/WBS分解/项目规划/工作分解/项目分解/分解任务/立项申请书/结项报告/相关方登记册/风险登记册/项目文档/项目模板/经济效益分析/投资回报/ROI/NPV/IRR/BCR/投资回收期/可行性分析/项目经济效益/折现分析/多折现率对比/挣值管理/EVM/PV/EV/AC/SPI/CPI/成本绩效/进度偏差/挣得值/EAC/挣值分析
trigger_negative: 只是询问概念不执行估算/纯数学公式讨论不含实际任务
faq_quality: improve_qa
meta_field_sync: true
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
| 5 | **知识库查询/写入** (新增) | 按需信息通道，与联网搜索平行。标准字段硬编码，LLM做格式翻译入库。支持历史项目查询、OMP基准检索、外部数据库/文件（SQLite/CSV/MD/DOCX/JSON）按标准导入 |
| 6 | **CPM关键路径分析** | 基于紧前关系的关键路径计算，含ES/EF/LS/LF/总时差，自动识别关键任务 |
| 7 | **多分布蒙特卡洛** | 支持PERT-Beta、三角分布、泊松近似三种分布并行模拟，提供多维度概率评估 |
| 8 | **任务重叠分析** | 自动检测任务时间重叠，输出最大重叠数和最长重叠时段 |
| 9 | **甘特图可视化** | 基于CPM结果的甘特图（SVG），关键路径高亮标注 |
| 10 | **紧前关系规划** | 手动指定/自动规划两种模式，支持FS/SS/FF/SF四种依赖关系 |
| 11 | **HTML评估报告** | 自包含HTML，含甘特图/概率分布/重叠分析图表，有图有表有数据有分析 |
| 12 | **项目文档生成** | 双模式：手动空模版/混合逐节生成；4个P0模板（立项/结项/相关方/风险） |
| 13 | **全局设置系统** | 5项可调整设置（联网搜索/知识库采集/知识库调用/文档指定/文档撰写），每项可选 auto/manual。`scripts/settings_server.py` 提供 HTML 可视化设置面板。设置通过 `state.settings` 注入流程，LLM 可读取 `_get_setting()` 决定行为。 |
| 14 | **经济效益分析** (分支子技能) | 独立于全流程，单独触发。ROI/NPV/IRR/BCR/PBP 计算引擎 + HTML 报告 + 独立 economic.db 知识库。可插入立项申请书模板。 |
| 15 | **挣值管理** (分支子技能) | 独立于全流程，单独触发。PV/EV/AC/SPI/CPI/EAC 计算引擎 + HTML 报告 + 独立 evm.db 知识库。可插入结项报告书模板。 |

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
| `references/risk-dimensions.md` | 风险维度 | D1~D7七类风险维度选择条件和缓解措施 |
| `references/thinking-tools.md` | 思维工具 | SWOT/SMART/PDCA/RACI等12个项目管理思维工具 |
| `references/faq.md` | FAQ | WBS+项目文档相关 |
| `references/changelog.md` | 更新日志 | 版本更新记录 |
| `references/economic-analysis-methodology.md` | 经济效益分析方法论 | ROI/NPV/IRR/BCR/PBP 公式、计算引擎 API、知识库字段、跨库引用规则 |
| `references/evm-methodology.md` | 挣值管理方法论 | PV/EV/AC/SPI/CPI/EAC 公式、计算引擎 API、知识库字段、跨库引用规则 |
| `references/templates/` | 模板目录 | 4个预置JSON模板文件（立项/结项/相关方/风险） |
| `references/knowledge-interface.md` | 知识库接口 | 按需信息通道设计、标准字段定义、LLM格式解析指引、外部数据对接规范 |
| `scripts/runner.py` | 编排层 | PipelineState + run_pipeline() 全流程Python驱动 |
| `scripts/knowledge_schema.py` | 知识库标准 | 标准字段定义、格式转换器、外部数据库映射规则 + economic/evm/registry 字段定义 |
| `scripts/project_knowledge.py` | 共享知识库引擎 | shared.db：SQLite+FTS5实现：查询/写入/外部对接/基准积累 |
| `scripts/economic_knowledge.py` | 经济效益知识库引擎 | economic.db：独立CRUD、索引查询、跨库ATTACH shared.db |
| `scripts/evm_knowledge.py` | 挣值管理知识库引擎 | evm.db：独立CRUD、索引查询、跨库ATTACH shared.db |
| `scripts/economic_analysis_engine.py` | 经济效益分析引擎 | ROI/NPV/IRR/BCR 完整计算 + 多折现率对比 + 逐年现金流 |
| `scripts/evm_engine.py` | 挣值管理引擎 | PV/EV/AC/SPI/CPI/EAC 完整计算 + 修正/不修正两模式 |
| `scripts/settings_manager.py` | 全局设置管理 | 5项设置（web_search/kb_collect/kb_query/doc_template/doc_write）读/写/校验/CLI |
| `scripts/settings_server.py` | 设置可视化服务 | HTTP服务器，浏览器打开即可可视化更新全部设置，更新后立即生效 |
| `scripts/templates/settings.html` | 设置面板UI | 自包含HTML设置界面，约束联动（文档指定为空时禁用模板要求选项） |
| `scripts/templates/economic-report.html` | 经济效益报告模板 | 自包含HTML：多折现率对比、NPV曲线图、逐年现金流、ROI/IRR/BCR卡片 |
| `scripts/templates/evm-report.html` | 挣值分析报告模板 | 自包含HTML：SPI/CPI趋势图、绩效快照卡片、完工预测表 |

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

**全流程阶段（代码硬编码，不可跳过，与 runner.py 中 6 个阶段一一对应）：**

1. WBS分解 → `run_wbs()`（全流程模式下必做，LLM提供结构化数据）
2. WBS进入估算门控 → `_wbs_passes_estimation_gate()` 硬校验
3. 紧前关系规划 → `_prompt_llm_for_dependencies()` / 自动FS串联
4. 估算计算 → `run_estimate()`（全Python自动：CPM + MC + 重叠分析）
5. HTML评估报告 → `_generate_html_report()`（全Python自动）
6. 项目文档 → `generate_docs()`（按模板生成立项/结项/风险/相关方文档）

**单独调用模式**（不经过`run_full()`全流程，按需使用）：

| 需求 | 调用方式 |
|------|---------|
| 仅有估算需求 | `run_pipeline(mode="estimate")` 或 `state.run_estimate()` |
| 仅需文档 | `run_pipeline(mode="docs")` 或 `state.generate_docs()` |
| 仅WBS分解 | `run_pipeline(mode="wbs")` 或 `state.run_wbs()` |

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
场景1：直接估算 — "乐观3天、最可能6天、悲观15天" → β分布7天, σ=2天 → 68%概率5~9天
场景2：多阶段CPM — "前端(5/10/20)→后端(8/15/25)→测试(10/20/35), FS" → 总工期47天 →出HTML报告
场景3：搜索辅助 — "装配式建筑施工" → 搜索同类→给出典型OMP→确认→估算
场景4：WBS→估算 — "帮我规划并估算电商后台" → 分解→确认→HTML报告
场景5：项目文档 — "生成立项申请书, 手动模式" → 空模板→"自动填充背景"→逐节生成→拼合
场景6：经济效益分析 — "初始100万, 年收益12万, 年支出5万, 5年, 终值200万, 折现率10%" → NPV=50.72, IRR=20.35%
场景7：挣值管理 — "项目到D阶段, 做挣值分析" → EV=320.27, SPI=1.01, CPI=1.07, EAC=379.73
```

## 常用操作速查

| 我想... | 一句话答案 |
|---------|-----------|
| 快速估算一个项目工期 | 调用 `from scripts.runner import run_full; result = run_full("项目描述")` — AI 自动拆解+估算+出报告 |
| 只用 WBS 不做估算 | `state.run_wbs()` — 只做工作分解，不进估算流程 |
| 指定每个任务的 OMP | 在 WBS 数据结构中填写 `{"o": 3, "m": 5, "p": 8}` 字段 |
| 用我自己的文档模板 | `load_template() → customize_sections() → save_template()` — 增删改排章节后另存 |
| 修改全局设置 | `python scripts/settings_manager.py set <key> <value>` — 纯 CLI，无需 LLM 参与 |
| HTML 报告打不开 | 报告是自包含 HTML，直接用浏览器打开 state.html_report_path |
| 调整蒙特卡洛模拟次数 | `run_full(mc_iterations=5000)` — 默认 2000，数值越高越精确但越慢 |
| 从历史项目参考数据 | 告诉 LLM「查一下同类项目的基准数据」— 会自动搜索 SQLite 知识库 |

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

当前版本 **v1.11.0** — 详见 `references/changelog.md`
