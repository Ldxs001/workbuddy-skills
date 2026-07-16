<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# semantic-split 架构与规范体系文档

> 完整解读 v3.1.1 版的架构设计、三管线递进调度（B 正则 → A 语义 → C 双视角推理）、10 道门禁钩子系统、自增强闭环与渐进加载决策树
> 生成时间：2026-07-02（v3.1.1 最新更新）

---

## 一、系统概览

semantic-split 是一个 **语义拆分与智能规划工具集**，将用户自然语言任务描述拆解为结构化步骤输出，围绕以下闭环运行：

```
用户输入（自然语言任务描述）
  → [钩子1] 输入校验
    → Pipeline B（正则结构分析：5W2H / 主语 / 约束标注 / 分块 / 注意力锚定）
      → [钩子2] B 管线完成
        → Pipeline A（模板库扫描：正则 → embedding → CrossEncoder 三层递进匹配）
          → [钩子3] A 扫描完成
            → [钩子4] 渐进加载决策
              ├─ 命中模板（≥0.6）→ 直接复用，0 LLM
              └─ 未命中 → [钩子5] Pipeline C 构建推理上下文
                            → [钩子6] 聚焦推理（保守方案）
                            → [钩子7] 发散推理（创新方案）
                            → [钩子8] 整合推理（最终方案）
                              → [钩子9] 保存模板（自增强闭环）
                                → [钩子10] WP 分解完成
                                  → 输出 JSON 结构化步骤
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI | 人类可读的文档、命令行交互 |
| **业务层** | semantic_pipeline / pipeline_b / pipeline_a / pipeline_c / json_manager / model_manager / setup_env | 三管线调度、结构分析、语义匹配、双视角推理、JSON 管理、模型下载、环境安装 |
| **数据层** | `.standardization/semantic-split/data/`（capabilities/ + rules/ + models/ + model_index.json） | 能力级 JSON 模板库、规则级 JSON 模板库、下载的嵌入模型、模型索引 |

### 1.2 目录结构

```
semantic-split/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据（v3.1.1）
├── references/                 # 渐进式文档（14 个文件）
│   ├── split_rules.md          # 语义拆分规则（块划分、主语映射、边界情况）
│   ├── task_type_defaults.md   # 任务类型默认映射表（5 类 + 通用默认值）
│   ├── constraint_annotation.md# 约束强度标注规则（🔴🟡⚪ + 隐式升级 + 注意力锚定 + 双方案差异）
│   ├── planning_rules.md       # 串并行规划规则（原子步骤、关联热度、里程碑、双视角整合、WP 分解）
│   ├── json_schema.md          # 能力级/规则级 JSON 结构规范（字段表、示例、存储结构）
│   ├── loading_decision_tree.md # 渐进加载决策树（规则级→能力级→模型思考完整分支）
│   ├── examples.md             # 使用示例（语义拆分 + 模板扫描）
│   ├── changelog.md            # 版本更新日志
│   ├── antipatterns.md         # 反模式指南（4 条）
│   ├── faq.md                  # 常见问题与排错
│   ├── permissions.md          # 权限声明 LOW 风险
│   ├── LICENSE.md              # MIT 许可协议
│   ├── attribution.md          # 第三方组件版权归属
│   └── automation_tasks.md     # 自动任务配置列表
└── scripts/                    # 核心脚本（7 个 Python）
    ├── semantic_pipeline.py    # 三管线统一调度入口 + 10 道门禁钩子系统 + 模板库管理
    ├── pipeline_b.py           # Pipeline B — 正则结构分析（零模型依赖）
    ├── pipeline_a.py           # Pipeline A — 语义匹配（bge-small + bge-reranker）
    ├── pipeline_c.py           # Pipeline C — 双视角推理上下文构建 + WP 分解
    ├── json_manager.py         # JSON 管理 CLI（scan / categorize / generalize / rule-gen / list / create / validate / info）
    ├── model_manager.py        # 模型管理（多源下载 / 校验 / 索引）
    └── setup_env.py            # 环境检测与 pip 依赖安装
```

### 1.3 数据目录结构

```
skills/.standardization/semantic-split/data/
├── capabilities/               # 能力级 JSON 模板（自增强闭环自动生成）
│   ├── make_product_ppt_v1.json # 示例：制作产品介绍 PPT 模板
│   └── ...
├── rules/                      # 规则级 JSON 模板（由同类能力级 ≥5 份凝练生成）
│   └── ...
├── models/                     # 下载的嵌入模型（model_manager.py 管理）
│   ├── BAAI_bge-small-zh-v1.5/ # 130MB 轻量中文嵌入
│   └── BAAI_bge-reranker-base/ # 556MB 中文 rerank
├── model_index.json            # 模型路径索引
└── outputs/                    # 输出缓存
    └── .structure_examples.json
```

---

## 二、三管线递进调度系统

### 2.1 Pipeline B：正则结构分析（Type 管线）

**核心文件**：`pipeline_b.py` | **参考**：`references/split_rules.md` + `references/constraint_annotation.md`

**零模型依赖**：纯 Python `re` 模块实现，无 pip 安装需求。这是三管线中唯一没有外部依赖的管线。

| 功能 | 函数 | 输出 | 方法 |
|------|------|------|------|
| **主语识别** | `_regex_subjects()` / `extract_subjects()` | 主语列表（用户/执行者/第三方） | SUBJECT_MAP 查表 + 去重保序 |
| **分块** | `_regex_blocks()` / `extract_blocks()` | 语义块列表（每块含主语推断） | 以 `。！？\n` 分句核 |
| **约束标注** | `_regex_constraints()` + `extract_constraints_and_attention()` | 约束列表（等级/关键词/领域） | CRITICAL_KW / SOFT_KW / EXAMPLE_KW 正则组 |
| **注意力锚定** | `extract_attention_anchoring()` | 锚定字典（critical / core / entity / example / resistance） | CORE_VERB_KW + 数量/时间正则 |
| **5W2H 提取** | `_regex_5w2h()` / `extract_5w2h()` | 七维字典（Why/What/Who/Where/When/How/How much + 覆盖率） | 7 组独立正则规则 |
| **隐式约束升级** | `_regex_detect_implicit_upgrade()` | 升级后约束列表（组织规范/法律合规/安全底线） | 5 领域正则组匹配 |
| **WP 分解** | `wps_decompose()` | 工作包列表（含耗时估算） | ESTIMATE_MAP 查表 + 逗号/顿号拆分子任务 |

#### 5W2H 七维度正则提取规则

| 维度 | 正则关键词 | 示例命中 |
|------|-----------|----------|
| **Why** | `为了、目的是、目标是、旨在、想要、想` | "为了向客户展示产品" |
| **What** | CORE_VERB_KW 动词组 | "制作PPT"、"写报告" |
| **Who** | SUBJECT_MAP 主语表 | "我"→用户、"你"→执行者 |
| **When** | DATE_KW 时间词正则 | "下周"、"周五前" |
| **Where** | `在\s*(.{2,10}?)(?:里上中处方)` | "在公司"、"在会议上" |
| **How** | HOW_KW + 工具提取 | "用公司模板"、"通过 ChatGPT" |
| **How much** | AMOUNT_KW 数量词 | "20页"、"3天" |

#### 约束关键词表

| 强度 | 正则组 | 关键词 |
|:----:|:------:|--------|
| 🔴 硬约束 | `CRITICAL_KW` | 必须、只能、截止、指定、强制、不允许、不得、禁止、一定 |
| 🟡 软约束 | `SOFT_KW` | 最好、尽量、如果、建议、通常、希望、可以、不妨 |
| ⚪ 示例 | `EXAMPLE_KW` | 比如、例如、像、假如、譬如 |
| 🚧 阻力 | `RESISTANCE_KW` | 但是、不过、担心、怕、难、卡、然而、但 |

#### 隐式约束升级领域

| 领域 | 正则组 | 升级规则 |
|:----:|:------:|----------|
| 组织规范 | 公司模板、品牌、审批、规范、章程、制度、标准、格式、命名 | 🟡 → 🟡🔴 |
| 法律合规 | 合同、数据保护、审计、合规、法律、条款、协议、版权、隐私 | 🟡 → 🔴 |
| 安全底线 | 权限、加密、安全、密码、认证、防火墙、隔离 | 🟡 → 🔴 |
| 协作依赖 | 接口、API、交付、依赖、对接、上下游、联调 | 🟡 + 影响下游标注 |
| 个人偏好 | 颜色、字体、风格、布局、喜欢、偏好 | 🟡 维持 |

**Pipeline B 产出**：完整的结构化分析结果字典，包含 subjects / blocks / constraints_attention / five_w2h / attention 五大部件，作为 Pipeline C 推理上下文的输入。

### 2.2 Pipeline A：语义匹配管线（matching pipeline）

**核心文件**：`pipeline_a.py` | **参考**：`references/json_schema.md` + `references/loading_decision_tree.md`

**三层递进匹配**：正则 → embedding（bge-small）→ BERT rerank（bge-reranker），逐层升级，在精度和成本间取得平衡。

#### 三层匹配架构

| 层 | 方法 | 模型 | 条件 | 最快路径 |
|:--:|:----:|:----:|:----:|:--------:|
| **① 正则层** | 关键词子串匹配（tags / name / description / steps） | **无** | score ≥ 0.8 直接通过 | 最快（零模型加载） |
| **② 嵌入层** | bge-small-zh-v1.5 编码 → 余弦相似度 | 92MB | score ≥ 0.6 作为候选 | 加载需 ~10 秒 |
| **③ Rerank 层** | bge-reranker-base CrossEncoder 重排序 | 1.1GB | score ≥ 0.5 最终确认 | 加载需 ~20 秒 |

#### 匹配函数详解

| 函数 | 职责 | 输入 | 输出 |
|------|------|------|------|
| `match_json(query, json_entries)` | **主入口**：三层递进匹配 | 用户 query + JSON 条目列表 | 按分数降序的匹配结果列表 |
| `_regex_match(keywords, json_data)` | 正则层：6 维子串匹配 | 拆分后的关键词 | 0.0-1.0 分数 |
| `_embedding_match(query, json_data)` | 嵌入层：余弦相似度 | query + JSON 字符串 | 0.0-1.0 分数 |
| `_rerank_match(query, candidates)` | Rerank 层：CrossEncoder top-10 重排 | query + 候选列表 | 带分数重排序结果 |
| `classify_constraint(text)` | 约束强度三分类（正则 + embedding 补充） | 单句文本 | {level, method, ...} |
| `generalize_actions(actions)` | 操作通用化（替换具体为占位符） | 操作列表 | 通用化后的操作列表 |
| `condense_rules(all_steps, threshold)` | 步骤聚类压缩（正则 → embedding 递进） | 步骤列表 | 聚类后的 condensed_steps |
| `should_load_json(query, json_entry)` | 渐进加载命中判定（三层递进） | query + 单 JSON 条目 | {hit, score, layer} |

#### 正则层匹配权重分配

| 匹配维度 | 权重 | 条件 |
|:--------:|:----:|:----:|
| tags 命中 | +0.15/条 | kw in tag or tag in kw |
| name 命中 | +0.20/条 | kw in name |
| description 命中 | +0.10/条 | kw in desc |
| steps 命中 | +0.05/步 | kw in step(name+action) |
| **最高分** | **1.0** | 超过即截断 |

#### 模型懒加载策略

```python
# pipeline_a.py 中的懒加载模式
_EMBEDDER = None
_RERANKER = None

def _load_embedder():
    # 仅在 embedding 层被需要时加载
    # CPU 推理，设置 CUDA_VISIBLE_DEVICES=-1 禁用 GPU
    # 模型路径从 MODELS_DIR 自动查找

def _load_reranker():
    # 仅在 rerank 层被需要时加载
    # 同 CPU 推理，CrossEncoder 实例化
```

模型查找路径：`MODELS_DIR / "BAAI_bge-small-zh-v1.5"` → 别名匹配（`bge-small-zh-v1.5`）→ 返回 None

**Pipeline A 产出**：json_matches 匹配结果列表 + constraint 约束分类 + pipeline_layers 使用记录（regex / embedding / rerank）。

### 2.3 Pipeline C：双视角推理管线（reasoning pipeline）

**核心文件**：`pipeline_c.py` | **参考**：`references/planning_rules.md`（第六节：双视角推理与整合规则）

**工作方式**：Python 构建推理上下文 → 智能体原生推理（LLM） → 步骤回填。Pipeline C 本身不执行推理，而是构建结构化的推理上下文引导智能体完成三阶段思考。

#### 三阶段双视角推理

```
[阶段1] 聚焦推理 (focus_reasoning)
  职责：生成保守、安全、可执行的聚焦方案
  规则：
    - 每个 5W2H 维度取最窄/最保守/最直接的值
    - 严格遵守所有🔴硬约束
    - 只使用已验证的低成本方法
    - 每个步骤 ≤30 分钟可完成
    - 输出 JSON 步骤列表（含 name/action/milestone/depends_on/parallel_group/dependency_heat）

[阶段2] 发散推理 (divergent_reasoning)
  职责：生成创新、大胆的发散方案
  规则：
    - 每个 5W2H 维度取最宽/最大胆/最间接的值
    - 🔴硬约束可轻微突破，但必须标注风险并提供备用方案
    - 引入至少一个非惯用工具或方法
    - 包含"如果无限资源会怎么做"变体
    - 输出 JSON 步骤列表 + 创新点列表

[阶段3] 整合推理 (integration_reasoning)
  职责：将聚焦方案（骨架）+ 发散方案（创新点）整合为单一方案
  规则：
    - 以聚焦方案为骨架（步骤顺序 = 聚焦方案）
    - 发散创新点通过语义相似度嵌入对应聚焦步骤
    - 所有创新步骤标注「🌟增强，来源：发散方案」
    - 涉及🔴硬约束突破的标注 ⚠️ 风险
    - 输出单一的整合后 JSON 步骤列表
```

#### 推理上下文构建

`build_reasoning_context()` 是 Pipeline C 的核心函数，构建包含以下内容的推理上下文：

| 上下文组件 | 来源 | 用途 |
|-----------|------|------|
| 5W2H 任务描述 | Pipeline B `five_w2h` | 提供七维任务全貌 |
| 约束清单 | Pipeline B `constraints_attention` | 提供🔴🟡⚪约束优先级 |
| 结构分析增强 | Pipeline B 动词/实体/NER 提取 | 增强 LLM 思考深度 |
| 模板参考 | Pipeline A `matches`（命中 ≥0.6 才提供） | few-shot 参考，提升推理质量 |
| 聚焦 Prompt | `FOCUS_SYSTEM` 常数 | 引导保守思考 |
| 发散 Prompt | `DIVERGENT_SYSTEM` 常数 | 引导创新思考 |
| 整合 Prompt | `INTEGRATION_SYSTEM` 常数 | 引导双方案整合 |

#### 步骤解析（降级策略）

`parse_steps_from_agent()` 提供三级降级解析：

| 级别 | 尝试 | 方法 |
|:----:|:----:|:----:|
| 1 | 直接 JSON 解析 | `json.loads()` → list 或 dict 提取 |
| 2 | 代码块提取 | 从 ```json ``` 区块提取 |
| 3 | 空列表回退 | 返回 [] |

---

## 三、10 道门禁钩子系统

**核心文件**：`semantic_pipeline.py`（第 37-57 行）

10 道钩子覆盖从输入校验到 WP 分解的完整流程，每道钩子独立记录状态和详情。所有钩子通过后，最终输出才被视为完整。

### 3.1 钩子定义与触发时机

```
[钩子1]  input_valid        → 输入校验通过（非空、≤2000 字）
[钩子2]  b_pipeline_done    → Pipeline B 结构分析完成
[钩子3]  a_scan_done        → Pipeline A 模板扫描完成（命中/未命中）
[钩子4]  decision_made      → 渐进加载决策（命中模板 / 未命中走语义）
[钩子5]  llm_generated      → 智能体推理启动/跳过
[钩子6]  focus_reasoning    → 聚焦方案推理（双视角第一步）
[钩子7]  divergent_reasoning→ 发散方案推理（双视角第二步）
[钩子8]  integration_reasoning → 整合方案推理（双视角第三步）
[钩子9]  template_saved     → 自动保存能力级 JSON 到 capabilities/
[钩子10] wp_done             → WP 工作包分解完成
```

### 3.2 钩子状态机

```
HOOK_STATUS = {
    "input_valid": False,           # 钩子1
    "b_pipeline_done": False,       # 钩子2
    "a_scan_done": False,           # 钩子3
    "decision_made": False,         # 钩子4
    "llm_generated": False,         # 钩子5
    "focus_reasoning": False,       # 钩子6
    "divergent_reasoning": False,   # 钩子7
    "integration_reasoning": False, # 钩子8
    "template_saved": False,        # 钩子9
    "wp_done": False,               # 钩子10
}
```

所有钩子初始化为 `False`，每个钩子在其对应操作完成后通过 `_hook()` 函数标记为 `True`。`_hook()` 同时写入 `HOOK_LOG` 列表，记录钩子名称、状态标记和详情文本。

### 3.3 三种钩子行为模式

| 模式 | 对应钩子 | 行为 |
|:----:|---------|------|
| **阻断** | input_valid | 空输入直接返回 error，不走管线 |
| **分支** | decision_made | 命中模板 → 跳管线 C；未命中 → 走 Pipeline A 语义 + Pipeline C 推理 |
| **强制顺序** | 钩子 6/7/8 | 双视角推理子步骤按 focus → diverge → integrate 强制顺序执行 |

---

## 四、自增强闭环

**核心机制**：`semantic_pipeline.py` 中的 `_save_template()` + `_scan_matching()` + `_load_all_capabilities()` + `match_json()`

### 4.1 闭环流程

```
执行完成 → _save_template() 通用化步骤 → 写入 capabilities/{task}_v1.json
  → 下次同类任务 → _scan_matching() 命中 ≥0.6 → 直接复用，0 LLM
  → 多次命中同类任务 → ≥5 份 → json_manager rule-gen → 生成规则级 JSON
    → 下次任务命中规则级 → 用 condensed_steps 生成规划，无需加载能力级细节
```

### 4.2 三步闭环机制

| 步骤 | 操作 | 触发条件 | 产出 |
|:----:|------|---------|------|
| **① 保存** | `_save_template()` 将当前步骤通用化写入 JSON | Pipeline C 推理完成且产生步骤 | `capabilities/{task}_v1.json` |
| **② 命中** | `_scan_matching()` 扫描模板库 | 每次处理新任务 | 匹配结果列表 |
| **③ 凝练** | `json_manager.py rule-gen` 将同类能力级压缩为规则级 | 同类能力级 ≥5 份（用户主动触发） | `rules/rule_{cat}_v1.json` |

### 4.3 模板保存的通用化规则

`_save_template()` 调用 `pipeline_a.generalize_actions()` 将具体操作泛化：

| 原始 | 通用化后 |
|------|----------|
| "介绍钛合金马扎" | "介绍[产品名称]" |
| "明天下午3点前交付" | "在[截止时间]前交付" |
| "导出为微信公众号格式" | "导出为[目标格式/平台]" |

通用化步骤保留结构（步骤数量、并行组、milestone、dependency_heat、depends_on），仅替换具体值为占位符。

#### 文件名生成规则

```python
task_name = re.sub(r'^(请|帮|帮我|我想|我需要|麻烦)', '', text.strip())[:20]
clean_name = re.sub(r'[^\u4e00-\u9fff\w]', '', task_name)[:16]
# 输出: capabilities/{clean_name}_v1.json
```

---

## 五、渐进加载决策树

**核心文件**：`references/loading_decision_tree.md` | **实现**：`semantic_pipeline.py` + `pipeline_a.py should_load_json()` + `json_manager.py cmd_scan()`

### 5.1 三阶段决策

```
Phase ①: 规则级扫描
  ├─ 完全命中 → 用 condensed_steps 生成规划 → 询问用户
  ├─ 部分命中 → 规则级前N步 + 渐进加载能力级补充
  ├─ 粗粒度命中 → load_capability_if_detail_needed 加载细节
  └─ 未命中 → Phase ②

Phase ②: 能力级扫描
  ├─ 命中 → 直接复用/拼装 → 询问用户
  └─ 未命中 → Phase ③

Phase ③: 模型思考
  └─ Pipeline C 双视角推理 → 生成步骤 → 询问用户
      → 用户确认执行 → 执行完成后 → _save_template() 
```

### 5.2 匹配阈值

| 层级 | 通过阈值 | 行为 |
|:----:|:--------:|------|
| 规则级完全匹配 | ≥0.6 | 直接使用 condensed_steps |
| 规则级部分匹配 | 前 N 步适用 | 加载规则级前 N 步 + 容量级补充 |
| 能力级完全匹配 | ≥0.6 | 直接使用能力级 steps |
| 能力级组合匹配 | 多个拼装覆盖 | 多个能力级拼装 |
| 能力级不命中 | <0.6 | 作为 few-shot 参考喂给智能体 |

### 5.3 脚本辅助匹配

```bash
# ① 扫描规则级
python scripts/json_manager.py scan --keywords <任务关键词> --type rule --top 3

# ② 规则级不命中时，扫描能力级
python scripts/json_manager.py scan --keywords <任务关键词> --type capability --top 5

# ③ 均不命中时，检查归类统计是否需要凝练规则级
python scripts/json_manager.py categorize --threshold 5
```

---

## 六、JSON 模板管理体系

**核心文件**：`json_manager.py` | **参考**：`references/json_schema.md`

### 6.1 双层 JSON 体系

```
规则级（rule）—— 上层抽象，粒度粗
  │  含 condensed_steps（压缩步骤）+ capability_refs（来源引用）
  │  load_capability_if_detail_needed 渐进加载指示
  │
  │ 通过 rule-gen 子命令从同类能力级 ≥5 份凝练生成
  │
能力级（capability）—— 原子单元，粒度细
    含 steps（完整步骤列表）+ generic_params（通用化占位符）
    
    通过 _save_template() 自动保存
```

### 6.2 能力级 JSON 结构

```json
{
  "id": "make_product_ppt_v1",
  "type": "capability",
  "name": "制作产品介绍 PPT",
  "version": "1.0.0",
  "created_at": "2026-05-22",
  "description": "从零制作一份产品介绍 PPT 的完整步骤",
  "generic_params": ["[产品名称]", "[核心参数]", "[截止时间]"],
  "steps": [
    {
      "id": "s1", "name": "收集资料",
      "action": "搜索/整理[产品名称]相关资料和[核心参数]",
      "parallel_group": null, "milestone": true,
      "dependency_heat": 0, "depends_on": [],
      "constraint_level": "none", "source": "focus"
    }
  ],
  "tags": ["ppt", "内容制作", "产品介绍"]
}
```

### 6.3 规则级 JSON 结构

```json
{
  "id": "rule_ppt_v1",
  "type": "rule",
  "name": "PPT 类任务规则",
  "version": "1.0.0",
  "created_at": "2026-05-22",
  "description": "统合所有 PPT 相关能力级 json",
  "source_capability_count": 5,
  "capability_refs": [
    { "id": "make_product_ppt_v1", "name": "制作产品介绍 PPT" }
  ],
  "condensed_steps": [
    {
      "id": "r1", "name": "资料与大纲",
      "milestone": true, "parallel_group": null,
      "maps_to": ["make_product_ppt_v1.s1", "make_product_ppt_v1.s2"],
      "load_capability_if_detail_needed": "make_product_ppt_v1"
    }
  ],
  "tags": ["ppt", "规则汇总"]
}
```

### 6.4 json_manager CLI 子命令

| 子命令 | 功能 | 核心参数 | 适用场景 |
|:------:|------|----------|---------|
| `scan` | 关键词扫描匹配 | `--keywords`, `--type`, `--threshold`, `--top` | 渐进加载决策的①②阶段 |
| `categorize` | 归类统计（按 tag 分组） | `--threshold`（默认 5） | 判断是否达到规则级凝练阈值 |
| `generalize` | 通用化字段替换 | `--input`, `--params`, `--auto`, `--output` | 保存模板前的通用化步骤 |
| `rule-gen` | 生成规则级 JSON 框架 | `--files` / `--tag`, `--output` | 同类能力级 ≥5 份后凝练 |
| `list` | 列出所有 JSON 文件 | `--type`, `--tag`, `--verbose` | 模板库概览 |
| `create` | 创建新 JSON 骨架 | `--type`, `--name`, `--output` | 手动创建新模板 |
| `validate` | 验证 JSON 格式 | `--file` | 字段完整性验证 |
| `info` | 显示 JSON 详情 | `--file` | 查看单条模板详细信息 |

---

## 七、模型管理

**核心文件**：`model_manager.py` | **参考**：`references/attribution.md`

### 7.1 模型清单

| 模型 | 管线 | 大小 | 类型 | 协议 |
|:----:|:----:|:----:|:----:|:----:|
| BAAI/bge-small-zh-v1.5 | Pipeline A 嵌入层 | 92MB | embedding | MIT |
| BAAI/bge-reranker-base | Pipeline A 重排序层 | 556MB | CrossEncoder | MIT |
| **合计** | | **~648MB** | **全部商业友好** | |

> Pipeline B 为纯正则实现，零模型依赖。v3.0.1 删除了 Stanza（1.1GB），从 3 个模型减为 2 个。

### 7.2 多源递进下载

| 优先级 | 源名称 | 方法 | 说明 |
|:------:|:------:|:----:|------|
| 1 | modelscope | `snapshot_download()` | ModelScope 国内镜像（推荐） |
| 2 | hf_mirror | `snapshot_download()` + HF_ENDPOINT | HuggingFace 国内镜像 |
| 3 | hf_official | `snapshot_download()` | HuggingFace 官方源 |
| 4 | hf_direct | `hf_hub_download()` 逐文件 | 最稳定，避免子进程死锁 |

每源最多 2 次重试，下载后自动完整性检查和路径索引。

### 7.3 模型路径查找

`_find_actual_model_path()` 使用内容感知方式查找模型路径：

```python
# 先查 MODELS_DIR（按名称相似度）
for d in os.listdir(MODELS_DIR):
    score = _name_similarity(_normalize(target), _normalize(d))
    if score > best_score and _is_model_dir(dp):
        best_score, best = score, dp

# 未找到则查 HF 缓存
safe_id = f"models--{model_id.replace('/', '--')}"
snap_dir = CACHE_DIR / safe_id / "snapshots"
```

---

## 八、核心设计原则

### D1: Pipeline B 零外部依赖

Pipeline B（正则结构分析）仅使用 Python 标准库 `re` + `pathlib`，零 `pip install` 需求。5W2H 提取、主语识别、约束标注、注意力锚定全部用正则实现。

**目的**：最常用的结构分析管线即装即用，无需下载模型。

### D2: 三层递进匹配（成本最优）

Pipeline A 的三层匹配（正则 → embedding → rerank）在精度和成本间渐近升级：

```
正则层（零成本，毫秒级）→ 不够再加 embedding（百毫秒级）→ 还不够再加 rerank（秒级）
```

**目的**：85%+ 的匹配在正则层解决，避免不必要的模型加载。

### D3: 自增强闭环

每完成一次任务自动生成能力级 JSON 模板，下次同类任务避免重复推理。多份能力级可凝练为规则级，实现从零到库的知识积累。

**目的**：系统越用越不用思考，LLM 调用量随使用递减。

### D4: 双视角推理强制

Pipeline C 强制走聚焦 → 发散 → 整合三阶段推理，10 道门禁的钩子 6/7/8 分别约束三个阶段。

**目的**：避免单一视角偏倚，聚焦方案保证可执行性，发散方案提供创新灵感。

### D5: 渐进加载

规则级 → 能力级 → 模型思考，只有上层不命中时才降级到下层。命中即用，0 LLM。

**目的**：LLM 调用量化化，典型任务 80% 可在规则级/能力级层解决。

### D6: 松耦合模块化

4 个管线脚本（pipeline_b / pipeline_a / pipeline_c / semantic_pipeline）+ 3 个辅助脚本（json_manager / model_manager / setup_env）各自独立，通过函数导入和 JSON 数据交换耦合。

**目的**：每个管线可独立升级/替换，不影响其他模块。

### D7: JSON 通用化 ≠ 抽象

能力级 JSON 的通用化是字段替换（具体值 → 占位符），不是抽象提炼。步骤粒度、结构、并行关系全部保留。

**目的**：通用化后仍保持精确的可执行性，不会丢失步骤细节。

### D8: 原子写入安全

所有 JSON 文件写入使用 `.tmp` + `os.replace()` 原子操作模式，防止写入过程中断导致文件损坏。

---

## 九、交互方式

### 9.1 主入口命令行

```bash
# 完整流程（含智能体推理）
python scripts/semantic_pipeline.py --text "帮我用公司模板做一份PPT，下周五前交给客户"

# JSON 格式输出
python scripts/semantic_pipeline.py --text "..." --json

# 完整中间结果（含所有管线数据）
python scripts/semantic_pipeline.py --text "..." --json --full

# 跳过智能体推理（返回骨架）
python scripts/semantic_pipeline.py --text "..." --skip-llm

# 显示门禁钩子状态
python scripts/semantic_pipeline.py --text "..." --hooks

# 从文件读取输入
python scripts/semantic_pipeline.py --file input.txt --json
```

### 9.2 JSON 管理命令行

| 子命令 | 完整命令示例 |
|:------:|-------------|
| scan | `python scripts/json_manager.py scan --keywords ppt 制作 --top 5` |
| categorize | `python scripts/json_manager.py categorize --threshold 5` |
| generalize | `python scripts/json_manager.py generalize --input xxx.json --params "钛合金马扎=[产品名称]"` |
| rule-gen | `python scripts/json_manager.py rule-gen --tag ppt --output rule_ppt_v1.json` |
| list | `python scripts/json_manager.py list --type capability --verbose` |
| create | `python scripts/json_manager.py create --type capability --name make_report_v1` |
| validate | `python scripts/json_manager.py validate --file xxx.json` |
| info | `python scripts/json_manager.py info --file xxx.json` |

### 9.3 模型管理命令行

```bash
# 下载所有模型（建议仅 Pipeline A）
python scripts/model_manager.py --download-all

# 下载指定模型
python scripts/model_manager.py --download bge-small
python scripts/model_manager.py --download bge-rerank

# 列出已下载模型
python scripts/model_manager.py --list

# 验证所有模型完整性
python scripts/model_manager.py --verify-all
```

### 9.4 环境安装

```bash
# 国内推荐（阿里云镜像）
python scripts/setup_env.py --auto-install --mirror aliyun

# 仅检测
python scripts/setup_env.py --check-only

# 清华镜像
python scripts/setup_env.py --auto-install --mirror tsinghua
```

---

## 十、外部依赖

| 包 | 用途 | 必需？ | 对应管线 |
|:--:|:----:|:------:|:--------:|
| sentence-transformers | bge embedding + CrossEncoder | 是 | Pipeline A |
| huggingface-hub | 模型下载（hf_hub_download） | 是 | model_manager |
| modelscope | ModelScope 国内下载 | 可选 | model_manager |
| torch | PyTorch 后端（sentence-transformers 依赖） | 推荐 | Pipeline A |

> **Pipeline B 零依赖**：纯 Python 标准库实现，即装即用。
> **Pipeline C 零依赖**：推理上下文构建使用 Python 标准库，推理由智能体原生完成。

---

## 十一、版本历史

| 版本 | 日期 | 核心变化 |
|:----:|:----:|:--------|
| 2.1.0 | 2026-05-22 | 初始标准化版本：skill-standardization 引擎创建 |
| 2.2.0 | 2026-05-23 | R-11 产出物路径修正：`data/` → `.standardization/semantic-split/data/` |
| 2.3.0 | 2026-05-23 | DATA_DIR 路径修正 + _meta.json data_dir 字段 |
| 2.4.0 | 2026-05-23 | 5W2H 维度提取 + 约束标注 + 双视角推理整合 |
| 2.4.1 | 2026-05-23 | SKILL.md 瘦身 (315→200行) + 渐进式 MD 体系完善 |
| 2.5.0 | 2026-05-23 | 标准化改造：章节重排、示例更新、路径修正 |
| 2.6.0 | 2026-06-30 | refactor 全流程：0 ERROR 0 WARN |
| **3.0.0** | **2026-07-01** | **三管线架构落地：pipeline_a/b/c + semantic_pipeline + model_manager + setup_env + 自增强闭环 + 10 道钩子** |
| 3.0.1 | 2026-07-01 | 删除 Stanza（1.1GB），Pipeline B 纯正则化 + 钩子系统 7→10 道 |
| 3.0.2 | 2026-07-01 | 双视角推理门禁强制化 + 清理所有 spaCy 残留 |
| 3.1.0 | 2026-07-01 | 修复 pipeline_b/c 死代码 + model_manager 索引错误 + 自增强闭环接入钩子 |
| **3.1.1** | **2026-07-01** | **渐进式索引表恢复完整（R-25 fix 吞列 bug）** |

---

## 十二、数据流全景

```
输入文本（≤2000字）
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ Pipeline B — 正则结构分析（零模型）                       │
│  ├─ 主语识别 → SUBJECT_MAP 查表                          │
│  ├─ 分块 → 。！？\n 分句核                                │
│  ├─ 约束标注 → 3 组正则关键词                             │
│  ├─ 注意力锚定 → CRITICAL/CORE/ENTITY/EXAMPLE/RESISTANCE │
│  ├─ 5W2H → 7 维正则规则                                  │
│  └─ 隐式升级 → 5 领域正则组                              │
└──────────────┬───────────────────────────────────────────┘
               │ {subjects, blocks, constraints, five_w2h, attention}
               ▼
┌──────────────────────────────────────────────────────────┐
│ Pipeline A — 模板库扫描（bge-small → bge-reranker）      │
│  ├─ regex层: 关键词子串匹配（零模型）                     │
│  ├─ embedding层: 余弦相似度（需模型）                     │
│  └─ rerank层: CrossEncoder 重排序（需模型）               │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ 渐进加载决策                                             │
│  ├─ 规则级完全命中（≥0.6）→ 直接复用                     │
│  ├─ 规则级部分命中 → 渐进加载能力级                       │
│  ├─ 能力级完全命中（≥0.6）→ 直接复用/拼装                │
│  └─ 不命中 → Pipeline C 双视角推理                       │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│ Pipeline C — 双视角推理（智能体原生）                     │
│  ├─ [钩子6] 聚焦方案：保守骨架                            │
│  ├─ [钩子7] 发散方案：创新点                              │
│  ├─ [钩子8] 整合方案：骨架+创新点融合                     │
│  ├─ [钩子9] 保存模板 → capabilities/{task}_v1.json       │
│  └─ [钩子10] WP分解 → 工作包列表                         │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
输出 JSON（steps + wps + hooks + pipeline_summary）
```

---

> 本文档基于 semantic-split v3.1.1 的 SKILL.md + 14 个 references/*.md + 7 个核心脚本综合分析整理。
