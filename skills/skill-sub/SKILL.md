---
name: skill-sub
version: 1.36.0
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

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

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
| -------- |------| ---------- |----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/adhesion.md` | 参考文档 | > **v1.25.0 新增**。粘连点是调用链中无法由 skill 自动化的缺口标记。 | 无 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/chain_schema.md` | 参考文档 | > 本文档定义 Chain / Step / retry_policy / failure_mode 的完整结构。 | 无 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、更新类型、修复项、升级说明。 | R-24 |
| `references/examples.md` | 使用示例 | 各场景完整执行示例。包含：CLI 命令、执行过程、输出结果。 | R-25 C-17 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/loop_branch.md` | 参考文档 | > 本文档是 SKILL.md 的渐进式补充，包含循环与分支编排的完整示例。 | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `references/reference.md` | 命令参考 | CLI 完整命令参考。包含：所有参数、子命令、选项、示例用法。 | 无 |
| `scripts/chain_gate.py` | 脚本 | 门禁系统 — 10 座 HARD 门禁的 check/set/status/reset | 无 |
| `scripts/chain_executor.py` | 脚本 | 执行引擎 — 含执行前蓝皮书基线自动校验 | 无 |
| `references/workflow.md` | 参考文档 | > 本文档是 SKILL.md 的渐进式补充，详细描述执行流程、里程碑判断规则、三层回退策略。 | 无 |
| `references/blueprint.md` | 参考文档 | 步骤蓝皮书结构与更新流程 | 无 |
| `references/gate.md` | 参考文档 | 门禁系统完整文档与 CLI 示例 | 无 |
| `references/private_blueprint.md` | 参考文档 | 链私有蓝皮书基线保护机制 | 无 |
| `references/llm_params.md` | 参考文档 | LLM 参数格式与门禁对应关系 | 无 |
| `references/chain_search.md` | 参考文档 | 自增强闭环历史链搜索 | 无 |
## 快速开始

| # | 功能 | 说明 |
| --- |------| ------ |
| 1 | 调用链管理 | 创建/查询/更新/删除 |
| 2 | 门禁系统 | 10 座 HARD 门禁 |
| 3 | 蓝皮书过期检测 | search 自动比对指纹 |
| 4 | 基线校验 | 执行前自动比对 |
| 5 | 粘连点 | 缺口标记+方案 |
| 6 | 历史链搜索 | n-gram 匹配 |

## 工作流程

```bash
python {SKILL_DIR}/scripts/chain_manager.py init
python {SKILL_DIR}/scripts/chain_manager.py create --name "发布链" --steps "[]"
python {SKILL_DIR}/scripts/chain_executor.py plan --name "发布链"
```

更多: create/list/show/search/delete, gate status, manager search

系统响应示例：
-  输出 ✅ 调用链创建成功
-  输出执行计划（含步骤依赖和里程碑标记）
-  输出 10 座门禁状态

## 配置



| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| 记忆参考 | bool | false | 创建时读用户记忆 |
| 命名方式 | string | auto | AI命名或询问 |
| 默认重试 | int | 3 | 1-10 可配置 |


详见 references/blueprint.md。

```bash
step_indexer.py search --intent "分析"
step_indexer.py status
```

## 能力边界与限制

参数约束：skill-dir 绝对路径 20-260 字符，描述文本 ≤120 字。最大步骤数 30 层，粘连点占比上限 30%，依赖深度上限 10 层。


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