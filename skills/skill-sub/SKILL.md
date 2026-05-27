---
name: skill-sub
version: 1.22.0
author: wUwproject
license: MIT
description: 调用链编排技能 v1.23.0 — 既是调用链编辑器，也是粗粒度规划器。理解用户意图 → 规划 Skill 参与顺序 → 更新/保存/推荐调用链 → 拼接为调用链（支持循环/分支编排、子步骤拓扑排序、准确步骤计数）。
tags: ['chain', 'orchestration', 'usable', 'skill-builder', 'progressive-loading', 'planner', 'editor']
data_dir: ../.standardization/skill-sub/
external_data_dir: true
sensitive_access: false
critical_write: false
permission_weight: MEDIUM
---










> 反模式详见 [references/antipatterns.md](../references/antipatterns.md)








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




# skill-sub v1.21.0

调用链编排技能。**既是调用链编辑器，也是粗粒度规划器。**

> 📢 **v1.19.1 修复**：里程碑影响分析（milestones）、动态里程碑（--dynamic）、里程碑统计（milestone-stats）、标签系统增强（list-tags）现已真正实现并注册到 parser。v1.19.0 仅标记 DONE 但未实现。

---

## 工作流程

1. **理解意图** → 分析用户输入，判断是否需要调用链
2. **规划技能顺序** → 推荐参与的 Skill 及其顺序
3. **生成调用链** → 创建 JSON 格式的调用链定义
4. **生成执行计划** → 输出 AI 可直接执行的指令序列
5. **（可选）实际执行** → 按执行计划逐步调用技能

---

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
```

---

## 循环与分支编排（v1.20.0 新增）

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
```

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
```

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

> 📚 完整 schema 参见 `references/chain_schema.md`

---

## v1.17.0 新增功能

### 1. 执行预览（Execution Preview）
`chain_executor.py plan` 生成的执行计划现在包含**可视化执行路径图**：
- 显示哪些步骤**并行**、哪些**串行**
- 标记**里程碑位置**和判断依据
- 显示**条件步骤**（有条件限制才执行）

### 2. 条件执行（Conditional Execution）
步骤支持 `condition` 字段，执行前先判断条件是否满足：
- `step_N_success` — 步骤N成功才执行
- `step_N_failed` — 步骤N失败才执行
- `always` — 总是执行（默认）
- `never` — 从不执行
- `variable_X_exists` — 变量X存在才执行

条件不满足时**跳过该步骤**，继续执行后续步骤。

### 3. 执行沙箱模式（Dry-Run）
新增 `--dry-run` 参数：
```bash
python {SKILL_DIR}/scripts/chain_executor.py plan --name "链名" --dry-run
```
- **不实际调用技能**，仅模拟执行
- 输出每步会发生什么
- 显示条件判断结果
- 显示重试策略、失败处理方式

### 4. 链备份机制（Chain Backup）
在**覆盖/删除前自动备份**到 `chains/backups/<链名>/` 目录：
```bash
# 列出备份版本
python {SKILL_DIR}/scripts/chain_manager.py list-backups --name "链名"

# 从备份恢复
python {SKILL_DIR}/scripts/chain_manager.py restore --name "链名" --version 1 --force
```
- 每次覆盖/删除前自动备份
- 保留最近 **20 个版本索引**、**10 个备份文件**
- 备份文件命名：`v<版本号>_<日期>.json`

### 5. 链版本管理（Chain Version Management）
备份机制同时维护**版本索引**（`versions.json`）：
- 每次保存自动递增版本号
- 记录备份原因（`overwrite` / `delete`）
- 支持从任意版本恢复

### 6. 摘取缓存（Extraction Cache）
`{SKILL_DIR}/scripts/skill_extractor.py` 现在**缓存**技能摘取结果：
```bash
# 正常使用（自动命中缓存）
python {SKILL_DIR}/scripts/skill_extractor.py extract --skill "triphasic-execution"

# 跳过缓存，强制重新摘取
python {SKILL_DIR}/scripts/skill_extractor.py extract --skill "triphasic-execution" --no-cache
```
- 缓存路径：`~/.workbuddy/skills/.standardization/skill-sub/cache/extraction_cache.json`
- **自动失效**：技能 `SKILL.md` 文件更新时缓存自动失效
- 保留最近 **200 个技能**的摘取结果
- 输出时显示 `📁 命中摘取缓存` 提示

---



## 详细文档

完整工作流程、使用示例、反模式与常见问题 → 见 `references/` 目录：
- `references/workflow.md` — 详细工作流程
- `references/examples.md` — 使用示例
- `references/faq.md` — 常见问题与反模式
- `references/chain_schema.md` — 调用链数据结构定义
- `references/permissions.md` — 权限说明

---

## 配置

配置界面：`python {SKILL_DIR}/scripts/settings.py`

| 配置项 | 选项 | 说明 |
|--------|------|------|
| **记忆参考** | 是 / 否 | 创建/执行调用链时，是否读取用户记忆文件增强步骤描述 |
| **命名方式** | 自动 / 人工 | 创建调用链时，由 AI 自动命名还是询问用户 |
| **默认重试次数** | 1-10（默认3） | 所有步骤的默认最大重试次数 |

---



**v1.17.0 — 执行预览 + 条件执行 + Dry-Run + 备份机制 + 版本管理 + 摘取缓存**
