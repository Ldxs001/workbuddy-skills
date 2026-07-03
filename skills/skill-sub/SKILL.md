---
name: skill-sub
version: 1.35.1
author: wUwproject
license: MIT
description: 调用链编排技能 — 既是调用链编辑器，也是粗粒度规划器。理解用户意图 → 规划 Skill 参与顺序 → 更新/保存/推荐调用链 → 拼接为调用链（支持循环/分支编排、子步骤拓扑排序、准确步骤计数）。
sensitive_access: false
critical_write: false
permission_weight: MEDIUM
data_dir: ../.standardization/skill-sub/data/
tags: ['chain', 'orchestration', 'usable', 'skill-builder', 'progressive-loading', 'planner', 'editor', 'step-index', 'blueprint']
external_data_dir: true
trigger: ['规划类: 帮我规划一下/步骤是什么', '顺序类: 依次执行/先...再...', '链管理: 创建/查看/更新/删除调用链']
trigger_negative: true
meta_field_sync: true
h1_position: true
create_permissions_md: true
---
# skill-sub

## 触发条件

**正向触发：**
- 规划类：「帮我规划一下...」、「...的步骤是什么」
- 顺序类：「依次执行 A、B、C」、「先...再...」
- 链管理：「创建/查看/更新/删除调用链」
- 步骤搜索类：「搜索步骤」、「找步骤」
- 链健康检查：「检查链的健康状态」
- 仅涉及单个 skill 的简单任务

**否定条件：**
- 明确要求「不使用调用链」

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（~380行），详细内容拆分到 `references/*.md` 按需加载。

| # | 功能 | 说明 |
| --- |------| ------ |
| 1 | **调用链管理** | 创建、查询、更新、删除调用链 |
| 2 | **执行计划生成** | 生成结构化执行计划，含并行/串行标记 |
| 3 | **条件执行** | 支持条件步骤，按条件判断是否执行 |
| 4 | **循环与分支编排** | 支持 for-each/while 循环和 if-else 分支 |
| 5 | **门禁系统** | 10 座 HARD 门禁串行阻断管线（chain_gate.py），HOOK-BLOCK 输出 |
| 6 | **步骤蓝皮书过期检测** | `search` 命令前置自动比对指纹，过期直接拒绝搜索 |
| 7 | **链私有蓝皮书基线校验** | 链创建时 snapshot 步骤接口，执行前自动校验基线偏移 |
| 8 | **粘连点（Adhesion Point）** | 标记 skill 无法自动化的缺口，提供三种解决方案保证链不断 |
| 9 | **自增强闭环（模板搜索）** | `chain_manager search` 匹配历史链，相似意图直接复用 |

---

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
|--------|------|----------|----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/adhesion.md` | 参考文档 | > **v1.25.0 新增**。粘连点是调用链中无法由 skill 自动化的缺口标记。 | 无 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/chain_schema.md` | 参考文档 | > 本文档定义 Chain / Step / retry_policy / failure_mode 的完整结构。 | 无 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、变更类型、修复项、升级说明。 | R-24 |
| `references/examples.md` | 使用示例 | 各场景完整执行示例。包含：CLI 命令、执行过程、输出结果。 | R-25 C-17 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/loop_branch.md` | 参考文档 | > 本文档是 SKILL.md 的渐进式补充，包含循环与分支编排的完整示例。 | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `references/reference.md` | 命令参考 | CLI 完整命令参考。包含：所有参数、子命令、选项、示例用法。 | 无 |
| `scripts/chain_gate.py` | 脚本 | 门禁系统 — 10 座 HARD 门禁的 check/set/status/reset | 无 |
| `scripts/chain_executor.py` | 脚本 | 执行引擎 — 含执行前蓝皮书基线自动校验 | 无 |
| `references/workflow.md` | 参考文档 | > 本文档是 SKILL.md 的渐进式补充，详细描述执行流程、里程碑判断规则、三层回退策略。 | 无 |
## 快速开始

### 三步上手：创建一个最小调用链

```bash
# 第一步：初始化
python {SKILL_DIR}/scripts/chain_manager.py init

# 第二步：创建调用链（两个 skill + 一个粘连点连接）
python {SKILL_DIR}/scripts/chain_manager.py create --name "代码发布" \
  --description "从代码分析到发布的完整流程" \
  --steps '[
    {"index":1,"type":"skill","step_name":"代码审查","skill_name":"code-review","action":"审查PR"},
    {"index":2,"type":"adhesion","step_name":"审批发布","adhesion":{"reason":"发布审批需要人工决策","solutions":[{"mode":"manual","description":"人工审批发布申请"}]}},
    {"index":3,"type":"skill","step_name":"部署","skill_name":"deploy","action":"部署到生产环境"}
  ]'

# 第三步：生成执行计划
python {SKILL_DIR}/scripts/chain_executor.py plan --name "代码发布" --verbose
```

> 💡 **小贴士**：创建时如果步骤有 ERROR，会提示具体原因（如"连续缺口应合并为一个粘连点"），按提示修正后重试即可。

### 场景二：使用 chain_planner 全自动规划链

```bash
# 使用脚本模式：给定步骤ID直接生成链
python {SKILL_DIR}/scripts/chain_planner.py script \
  --steps "skill-standardization.R-01,triphasic-execution.execute,skill-standardization.R-25" \
  --name "标准化审查链"
# 输出：
# ✅ 调用链 '标准化审查链' 创建成功
# 链目录: ~/.workbuddy/skills/.standardization/skill-sub/chains/标准化审查链/
# ├── chain.json
# └── blueprints.json
```

### 场景三：使用 chain_planner 搜索+规划

```bash
# 根据意图搜索步骤
python {SKILL_DIR}/scripts/chain_planner.py suggest \
  --intent "代码审查 分析 报告" --topk 5
# 输出：
# 🔍 增强推荐: 代码审查 分析 报告
# 1. skill-standardization.R-01 [0.87] → 权限扫描
# 2. analysis-toolkit.数据分析 [0.72] → 数据分析
# 3. ...
# 🔗 自动衔接分析:
# ⛔ step1 → step2 (semantic, 0.35) 需 adhesion
# ✅ step2 → step3 (none, 0.85)
```

### 更多命令

```bash
# 生成执行计划（详细输出）
python {SKILL_DIR}/scripts/chain_executor.py plan --name "代码发布" --verbose

# 链执行前基线校验（自动）
# 如有偏移，加 --force-health 跳过
python {SKILL_DIR}/scripts/chain_executor.py plan --name "代码发布" --force-health

# 查看调用链详情
python {SKILL_DIR}/scripts/chain_manager.py show --name "代码发布"

# 列出所有调用链
python {SKILL_DIR}/scripts/chain_manager.py list

# 按意图搜索已有链（模板匹配）
python {SKILL_DIR}/scripts/chain_manager.py search --intent "代码审查 部署"

# 检查链健康状态
python {SKILL_DIR}/scripts/chain_manager.py check-health --name "代码发布"

# 查看门禁状态
python {SKILL_DIR}/scripts/chain_gate.py status

# 删除（自动备份）
python {SKILL_DIR}/scripts/chain_manager.py delete --name "代码发布" --force
```

---

## 工作流程

### 前置硬约束

- **步骤蓝皮书过期检测**：`search` 命令自动比对指纹，过期直接拒绝搜索
- **链私有蓝皮书基线校验**：`chain_executor plan` 加载链时自动比对 `_skill_md5s` vs 当前 SKILL.md，偏移则 HOOK-BLOCK
- **门禁系统**：10 座 HARD 门禁串行阻断，任一不通过则 exit(1)

### 规划执行流程（串行，门禁阻断）

| 步骤 | 名称 | 门禁 | 说明 |
|------|------|------|------|
| 0 | **蓝皮书校验** | `blueprint_verified` | `search` 自动检查指纹，过期直接拒绝 |
| 1 | **理解意图** | `intent_decomposed` | 拆解用户意图为时序子意图 |
| 2 | **步骤搜索** | `steps_searched` | 对每个子意图分别搜索候选步骤 |
| 3 | **LLM 选步骤 + 链验证** | `llm_chain_verified` | 传入 `--llm-chain-check`，passed=false 阻断 |
| 4 | **里程碑判断** | `milestones_set` | 传入 `--milestones`，缺值阻断 |
| 5 | **步骤衔接校验** | `io_validated` | I/O 类型匹配 + DAG 连通性验证 |
| 6 | **黏连点补充** | `adhesion_resolved` | 传入 `--adhesion`，有缺口未解决阻断 |
| 7 | **生成调用链** | `chain_saved` | JSON 保存 + 自动 snapshot 私有蓝皮书 |
| 8 | **链健康检查** | — | 执行前自动比对 blueprints.json vs 当前 SKILL.md |
| 9 | **执行** | `chain_loaded` → `execution_planned` → `execution_completed` | 按计划逐步调用 skill |

---

### 循环与分支编排

> → 详见核心能力的渐进式文件索引

---

## 步骤蓝皮书（步骤索引）

skill-sub 将每个已安装技能（`~/.workbuddy/skills/*/`）的 SKILL.md 解析为结构化步骤蓝图，供搜索和链规划使用。

**硬约束：`search` 命令自带指纹过期检测，蓝皮书过期直接拒绝搜索。**
```
step_indexer.py search --intent "分析数据"
→ 蓝皮书过期（1个技能）：
   - skill-X（SKILL.md 已变更）
   请先更新：scan [--force] 或 LLM 路径
→ 或跳过检测：--ignore-stale
```

### 蓝皮书更新流程（LLM 优先）

```
LLM 提取（主路径）
  ├── 1. check-fingerprint → 检测哪些 skill 的 SKILL.md 有变更
  ├── 2. prepare-llm-input → 输出变更 skill 的 SKILL.md 全文
  ├── 3. AI/Agent 调用 LLM → LLM 读取 SKILL.md，输出步骤蓝图
  ├── 4. apply-blueprint → 格式校验 + 指纹记录 + 蓝图保存
  └── 5. 自检（可选）→ LLM 再读一次核实提取完整

Regex 兜底（LLM 不可用时）
  └── scan → 正则提取（仅支持 ### 标题格式，不保准）
```

```bash
# LLM 主路径
step_indexer.py scan --check-fingerprint                       # 检测变更
step_indexer.py prepare-llm-input --skill "skill-name"         # 获取 SKILL.md
step_indexer.py apply-blueprint --skill "skill-name" \         # 保存 LLM 结果
  --steps-json '[{"step_name": "步骤名", "consumes": "输入", "produces": "输出"}]'
  [--self-check-json '{"passed":true,"issues":[]}']

# Regex 兜底（LLM 失败时）
step_indexer.py scan [--skill "skill-name"] [--force]          # 全量/增量重建
```

### 搜索

```bash
step_indexer.py search --intent "分析数据 报告 生成"
# 输出：匹配步骤列表（含 I/O 描述和匹配分数）
step_indexer.py status
# 输出：当前蓝皮书覆盖率和构建时间
```

---

## 门禁系统

所有规划、执行操作由 **10 座 HARD 门禁** 串行阻断。门禁状态存 `data/gate_state.json`。

```bash
# 查看全部门禁状态
python {SKILL_DIR}/scripts/chain_gate.py status

# 检查单个门禁（失败则 exit(1) + HOOK-BLOCK）
python {SKILL_DIR}/scripts/chain_gate.py check --name chain_connected

# 强制开放（跳过阻断）
python {SKILL_DIR}/scripts/chain_gate.py set --name chain_connected --status open

# 重置全部门禁
python {SKILL_DIR}/scripts/chain_gate.py reset
```

门禁依赖链（不可跳过）：
```
blueprint_verified → intent_decomposed → steps_searched → steps_selected
  → llm_chain_verified → milestones_set → io_validated → adhesion_resolved
  → chain_connected → chain_saved → chain_loaded → execution_planned → execution_completed
```

---

## 链私有蓝皮书（基线保护）

每条链创建时自动保存步骤接口快照到 `chains/{name}/blueprints.json`，同时记录所有涉及 skill 的 SKILL.md md5（`_skill_md5s`）。

**执行前自动校验：**
```
chain_executor plan --name "链名"
  → 自动比对 blueprints.json 中的 _skill_md5s vs 当前 SKILL.md
  → 全部一致 → 放行
  → 有偏移 → HOOK-BLOCK，不给执行
  → 跳过：--force-health
```

**手动检查：**
```bash
chain_manager.py check-health --name "链名"
# 输出：步骤A 健康 ✅ / 步骤B 已变化 ⚠️ / 步骤C 已消失 ❌
```

---

## LLM 参数（链规划时 Agent 传入）

`chain_planner.py plan` 接收 Agent 传入的 LLM 判断结果：

```bash
python {SKILL_DIR}/scripts/chain_planner.py plan \
  --intent "分析数据后做PPT" \
  --steps "analysis-toolkit.数据分析,ppt-gen.生成PPT" \
  --llm-chain-check '{"passed":true,"reason":"步骤合理","milestones":"1,2"}' \
  --milestones "1,2" \
  --adhesion '{"resolved":true,"solutions":[{"mode":"manual","desc":"手动转换"}]}'
```

参数说明：
| 参数 | 格式 | 门禁 | 阻断条件 |
|------|------|------|---------|
| `--llm-chain-check` | JSON `{passed, reason, milestones}` | `llm_chain_verified` | passed=false 或格式错误 |
| `--milestones` | 逗号分隔序号 `1,3,5` | `milestones_set` | 缺值 |
| `--adhesion` | JSON `{resolved, reason, solutions}` | `adhesion_resolved` | gap>0 但 resolved=false |

---

## 自增强闭环（历史链搜索）

每次保存的链自动成为模板，下次相似意图直接命中：

```bash
# 搜索已有链（n-gram 匹配 intent 关键词）
python {SKILL_DIR}/scripts/chain_manager.py search --intent "分析数据 报告"

# 输出：
# 🔍 链搜索: 分析数据 → 2 个匹配
#   [0.62] 分析数据后做PPT (3步) 分析数据后生成PPT并发送邮件
#   [0.45] 审计报告链 (2步) 审计代码并生成报告
```

---

## 配置

配置界面：运行以下命令启动配置界面：

```bash
python {SKILL_DIR}/scripts/settings.py
```

| 配置项 | 选项 | 说明 |
| -------- |------| ------ |
| **记忆参考** | 是 / 否 | 创建/执行调用链时，是否读取用户记忆文件增强步骤描述 |
| **命名方式** | 自动 / 人工 | 创建调用链时，由 AI 自动命名还是询问用户 |
| **默认重试次数** | 1-10（默认3） | 所有步骤的默认最大重试次数 |

---

## 能力边界与限制

### 适宜场景 ✅

| 场景 | 说明 |
| ------ |------|
| 多 skill 编排 | 涉及 2 个及以上 skill，步骤间有明确依赖关系 |
| 可固化流程 | 流程稳定、可复现，不是一次性操作 |
| 跨步骤衔接 | skill 之间需要数据转换、人工审批、流程补全 |

### 不适宜场景 ❌

| 场景 | 原因 |
| ------ |------|
| 单 skill 任务 | 直接调 skill 本身即可，不需要调用链 |
| 一次性操作 | 调用链的价值在于复用，一次性工作不值得建链 |
| 无依赖的并行任务 | 多个独立任务应并行执行，不需要编排 |
| 高度动态的流程 | 每次执行步骤都不一样，粘连点也解决不了，直接 AI 手动处理 |

### 硬限制

| 限制项 | 值 | 说明 |
| -------- |-----| ------ |
| 最大步骤数 | 30 层（含嵌套） | 超过后校验器会告警，但不阻断执行 |
| 粘连点占比 | 30% | 超过告警，建议合并或补充 skill |
| 粘连点连续 | **禁止** | 连续缺口合并为一个粘连点 |
| 依赖深度 | 10 层 | 过深依赖链难以维护和排查 |
| 循环最大迭代 | 默认 10，可配置 | 超过按 on_max_iteration 处理 |

### 常见创建错误速查

| 报错信息 | 原因 | 解决方法 |
| --------- |------| --------- |
| 连续缺口应合并为一个粘连点 | 两个 adhesion 步骤相邻 | 合并为一个 adhesion，用 hybrid 方案覆盖全部缺口 |
| 粘连点占比超过 30% | adhesion 步骤太多 | 检查是否有 skill 可以替代 |
| 缺少 solutions | adhesion 步骤没有提供方案 | 至少加一个 manual 方案 |
| 依赖不存在的步骤 | depends_on 引用了无效索引 | 检查依赖步骤的 index 是否正确 |
| 引用的 skill 不存在 | skill_name 对应的 skill 未安装 | 检查 skill 名称是否正确 |
| 检测到定时/自动化意图，但未提供 --schedule | 描述中含"每天/每周/定时"等词但没给调度配置 | 添加 --schedule 参数，或删除描述中的时间相关词 |

> **强制规则**：用户描述中包含定时/自动化意图（如"每天"、"每周"、"自动执行"等）时，**必须**提供 `--schedule` 参数配置调度信息，否则链创建被拦截。不依赖 AI 自觉判断。

