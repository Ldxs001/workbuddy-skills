---
name: skill-sub
version: 1.24.7
author: wUwproject
license: MIT
description: 调用链编排技能 — 既是调用链编辑器，也是粗粒度规划器
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/skill-sub/data/
tags: ['chain', 'orchestration', 'usable', 'skill-builder', 'progressive-loading', 'planner', 'editor']
external_data_dir: true
trigger: ['规划类: 帮我规划一下/步骤是什么', '顺序类: 依次执行/先...再...', '链管理: 创建/查看/更新/删除调用链']
trigger_negative: ['不使用调用链', '手动逐步执行']
---
# skill-sub

> 反模式详见 [references/antipatterns.md](references/antipatterns.md)


## 触发场景

**当用户提出以下意图时触发本技能：**
- 规划类：「帮我规划一下...」、「...的步骤是什么」
- 顺序类：「依次执行 A、B、C」、「先...再...」
- 链管理：「创建/查看/更新/删除调用链」

**否定条件**：仅当用户明确要求「不使用调用链」或「手动逐步执行」时，不自动触发。


## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 功能 | 说明 |
|---|------|------|
| 1 | **调用链管理** | 创建、查询、更新、删除调用链 |
| 2 | **执行计划生成** | 生成结构化执行计划，含并行/串行标记 |
| 3 | **条件执行** | 支持条件步骤，按条件判断是否执行 |
| 4 | **循环与分支编排** | 支持 for-each/while 循环和 if-else 分支 |
| 5 | **Dry-Run 模式** | 模拟执行，不实际调用技能 |
| 6 | **链备份与版本管理** | 自动备份，支持版本恢复 |

---

---




### 渐进式文件索引

| 文件名 | 位置 | 说明 |
|--------|------|------|
| `references/antipatterns.md` | skill-sub 反模式 | > 本文档收录 skill-sub 使用中的常见错误和正确做法。完整反模式示例见 `references/faq.md` |
| `references/chain_schema.md` | skill-sub 调用链数据结构 | > 本文档定义 Chain / Step / retry_policy / failure_mode 的完整结构。 |
| `references/changelog.md` | skill-sub 更新日志 | - **循环步骤（Loop Step）** — `type: "loop"` 支持 `for_each` / `whil |
| `references/examples.md` | skill-sub 使用示例 | > 本文档是 SKILL.md 的渐进式补充，提供完整使用示例。 |
| `references/faq.md` | skill-sub 常见问题 | > 本文档是 SKILL.md 的渐进式补充，收录常见问题与使用技巧。 |
| `references/permissions.md` | 权限说明 | 权限扫描风险等级：**MEDIUM** |
| `references/reference.md` | skill-sub 参考手册 | > 本文档是 SKILL.md 的渐进式补充，包含完整 CLI 速查、脚本 API、存储格式。 |
| `references/workflow.md` | skill-sub 详细工作流程 | > 本文档是 SKILL.md 的渐进式补充，详细描述执行流程、里程碑判断规则、三层回退策略。 |
## 快速开始

```bash
# 初始化
python {SKILL_DIR}/scripts/chain_manager.py init

# 创建调用链
python {SKILL_DIR}/scripts/chain_manager.py create --name "发布流水线" --description "技能发布流程" --purpose "一键发布" --steps '[...]'

# 生成执行计划（含执行预览）
python {SKILL_DIR}/scripts/chain_executor.py plan --name "发布流水线" --verbose

# Dry-Run 模拟执行（不实际调用技能）
python {SKILL_DIR}/scripts/chain_executor.py plan --name "发布流水线" --dry-run

# 查看调用链
python {SKILL_DIR}/scripts/chain_manager.py show --name "发布流水线"

# 列出所有调用链
python {SKILL_DIR}/scripts/chain_manager.py list

# 删除（自动备份）
python {SKILL_DIR}/scripts/chain_manager.py delete --name "发布流水线" --force
```text

---




## 工作流程

1. **理解意图** → 分析用户输入，判断是否需要调用链
2. **规划技能顺序** → 推荐参与的 Skill 及其顺序
3. **生成调用链** → 创建 JSON 格式的调用链定义
4. **生成执行计划** → 输出 AI 可直接执行的指令序列
5. **（可选）实际执行** → 按执行计划逐步调用技能

---

### 循环与分支编排

### for-each 循环

在调用链 JSON 中，将某步骤的 `type` 设为 `"loop"`，并定义 `loop` 对象：

```json
{
  "type": "loop",
  "step_name": "批量处理文件",
  "loop": {
    "mode": "for_each",
    "items": "{{file_list}}",
    "loop_variable": "f",
    "max_iterations": 10,
    "steps": [
      {"type": "skill", "skill_name": "file-ops", "step_name": "处理单个文件", "action": "处理 {{f}}"}
    ]
  }
}
```text

### while 循环

```json
{
  "type": "loop",
  "step_name": "重试直到成功",
  "loop": {
    "mode": "while",
    "while_condition": "{{retry_count}} < 3 and {{last_result}} != 'success'",
    "max_iterations": 3,
    "steps": [
      {"type": "skill", "skill_name": "api-call", "step_name": "调用接口", "action": "重试第 {{retry_count}} 次"}
    ]
  }
}
```text

### if-else 分支

```json
{
  "type": "branch",
  "step_name": "按环境部署",
  "branch": {
    "condition": "{{env}} == 'prod'",
    "if_steps": [
      {"type": "skill", "skill_name": "deploy", "step_name": "生产部署", "action": "部署到生产环境"}
    ],
    "else_steps": [
      {"type": "skill", "skill_name": "deploy", "step_name": "预发部署", "action": "部署到预发环境"}
    ]
  }
}
```

> 📚 完整 schema 详见 `references/chain_schema.md`

---



## 配置

配置界面：`python {SKILL_DIR}/scripts/settings.py`

| 配置项 | 选项 | 说明 |
|--------|------|------|
| **记忆参考** | 是 / 否 | 创建/执行调用链时，是否读取用户记忆文件增强步骤描述 |
| **命名方式** | 自动 / 人工 | 创建调用链时，由 AI 自动命名还是询问用户 |
| **默认重试次数** | 1-10（默认3） | 所有步骤的默认最大重试次数 |

---