---
name: skill-sub
version: 1.10.0
author: wUwproject
license: MIT
description: >
  调用链编排技能 — 既是调用链编辑器，也是粗粒度规划器。
  理解用户意图 → 规划 Skill 参与顺序 → 编辑/保存/推荐调用链 → 拼接为调用链。
tags: ["chain", "orchestration", "reusable", "skill-builder", "progressive-loading", "planner", "editor"]
---

# skill-sub v1.9.0

> 调用链编排技能 — 既是调用链编辑器，也是粗粒度规划器。理解用户意图 → 规划 Skill 参与顺序 → 编辑/保存/推荐调用链 → 拼接为调用链。

调用链编排器，兼具**编辑器**和**粗粒度规划器**双重角色，将多个 Skill 编排为调用链。

---

## 核心概念

### 什么是调用链

调用链（Chain）是一条预定义的执行流水线，将多个 Skill 的关键步骤按依赖关系串联，形成可复用的调用链。

### skill-sub 的三个角色（重要）

- ✅ **调用链编辑器** — 创建、编辑、保存、删除、列出调用链（`chain_manager.py`）
- ✅ **粗粒度规划器** — 理解用户意图，规划哪些 Skill 参与、执行顺序、依赖关系
- ✅ **编排器** — 将规划结果拼接为调用链 JSON，本身不参与调用链执行

### skill-sub 不是什么

- ❌ 本身参与调用链执行（skill-sub 是编辑器/规划器/编排器，不是链的一环）
- ❌ 针对单次任务生成绑定产物（输出的是调用链，可复用于同类任务）

---

## 调用链生成逻辑（三阶段）

> 生成调用链不是让 AI 自由发挥，而是按以下三阶段确定性地完成。
> 详细表格和示例见 `references/workflow.md`。

### 阶段1：理解（Understanding）

> **两个理解缺一不可**：不理解用户要做什么 → 链的目标不清晰；不理解 skill 能做什么 → 链的节点不靠谱。

**理解①：用户要做什么（任务目标）**
- 从用户自然语言描述中提取：任务类型、预期产物、关键约束
- 判断：这是"一次性执行"还是"可复用的通用流程"？

**理解②：涉及的 Skill 能做什么（能力边界）**
- **用户明确指定了 Skill** → 直接从用户给的列表操作，不额外遍历
- **用户未指定 Skill** → 从本地 skill 库（`~/.workbuddy/skills/` + `{workspace}/.workbuddy/skills/`）遍历挑选，匹配依据：
  - SKILL.md `description` 字段
  - SKILL.md `tags` 字段
  - 用户描述中的关键词
- 对每个候选 Skill，读取其 SKILL.md 的「核心概念」/「工作流程」章节，确认它能做什么、不能做什么

**输出**：有序 Skill 列表 + 依赖关系 + 里程碑标记 + 每个 Skill 的能力摘要（用于阶段2摘取时的精准定位）

---

### 阶段2：摘取（Extraction）

**目的**：按顺序从各 Skill 的 SKILL.md 中**摘取关键步骤描述**。

**摘取方式（两种，择优使用）：**

| 方式 | 适用场景 |
|------|---------|
| `skill_extractor.py extract --skill <name>` | 有标准化 SKILL.md 结构的 skill |
| 直接读取 SKILL.md 的「核心指令」/「工作流程」章节 | 结构不标准，需人工判断 |

**摘取内容**：步骤名称 → `step_name`；关键动作 → `action`；指令名 → `skill_instruction`。

---

### 阶段3：拼接（Composition）

**目的**：将摘取到的所有步骤，合成为**调用链 JSON**，保存到 `chains/*.json`。

**拼接规则**：填充 Chain 级字段（`name`/`description`/`purpose`/`tags`）→ 填充每个 Step 字段（`index`/`skill_name`/`action`/`depends_on`/`failure_mode`）→ 调用 `chain_manager.py create` 保存。

**详细字段映射表和 JSON 格式** → 见 `references/chain_schema.md`。

---

## 触发方式

### 1. 用户主动调用

触发示例：
- "创建一条发布流水线的调用链"
- "执行发布流水线"
- "列出所有调用链"
- "用 skill-sub 管理调用链"
- "编辑调用链 XXX 的步骤"
- "推荐适合当前任务的调用链"

### 2. 意图关键词自动匹配（推荐）

当用户意图与已保存调用链的 `tags`/`description`/`user_intent` 重合度 > 50% 时，**自动推荐**匹配的调用链，用户可选择执行或编辑。

匹配逻辑详见 `references/workflow.md`。

---

## 工作流程

```
用户请求（自然语言描述）
  ↓
【规划器角色】理解用户意图 + 规划 Skill 参与顺序
  ├── 理解①：用户要做什么（任务目标、预期产物、约束）
  ├── 理解②：Skill 能做什么（用户指定→直接用；未指定→遍历本地库挑选）
  └── 输出：有序 Skill 列表 + 依赖关系 + 里程碑 + 各 Skill 能力摘要
  ↓
【编辑器角色】创建 / 编辑调用链
  ├── 新建：执行三阶段（理解→摘取→拼接）→ chain_manager.py create
  ├── 编辑：add-step / remove-step / update-step / rename
  └── 管理：list / show / delete
  ↓
【编排器角色】拼接为调用链 → 保存到 chains/*.json
  ↓
输出：调用链已保存，可复用；或意图匹配推荐已有调用链
```

详细执行流程、里程碑判断规则、三层回退策略
  详见 `references/workflow.md`（按需加载）

---

## 快速开始

```bash
# 初始化数据目录
python {SKILL_DIR}/scripts/chain_manager.py init

# 创建调用链（AI 自动执行三阶段）
python {SKILL_DIR}/scripts/chain_manager.py create --name "链名" --description "描述"

# 编辑调用链步骤
python {SKILL_DIR}/scripts/chain_manager.py add-step --name "链名" --step-json '{...}'
python {SKILL_DIR}/scripts/chain_manager.py remove-step --name "链名" --index 2

# 执行 / 列出 / 删除调用链
python {SKILL_DIR}/scripts/chain_executor.py plan --name "链名"
python {SKILL_DIR}/scripts/chain_manager.py list
python {SKILL_DIR}/scripts/chain_manager.py delete --name "链名"

# HTML 设置界面
python {SKILL_DIR}/scripts/settings.py
```

完整 CLI 速查、脚本清单、存储机制
  详见 `references/reference.md`（按需加载）

---

## 渐进式 MD 文件体系

| 本文件（SKILL.md）包含 | 拆分到 references/ |
|----------------------------|---------------------------|
| ✅ 核心概念（三角色定位） | 📄 `workflow.md` — 详细执行流程、里程碑规则、意图匹配逻辑 |
| ✅ 三阶段生成逻辑 | 📄 `reference.md` — 完整 CLI 速查、脚本 API |
| ✅ 触发方式（含推荐逻辑） | 📄 `chain_schema.md` — Chain/Step 结构定义 |
| ✅ 工作流程概述 | 📄 `examples.md` — 完整使用示例（含编辑、推荐场景） |
| ✅ 快速开始（核心命令） | 📄 `changelog.md` — 版本更新日志 |
| ✅ 审查规则自查 | — |

---

## 规范自查（R-01~R-10）

本 skill 自身遵循 skill-standardization v2 规范，自查结果见 `references/changelog.md`。

---

## 注意事项

1. **skill-sub 本身不参与调用链** — 它是编辑器/规划器/编排器，不是链的执行环节
2. **生成的调用链是可复用的** — 不绑定单次任务，可复用于同类任务
3. **三阶段缺一不可**：不理解→摘取不全；不摘取→链内容空洞；不拼接→无产出
4. **里程碑步骤失败强制中止** — 无论 `on_exhaust` 设置
5. **本文件 ≤200 行** — 超出部分拆分到 `references/`

---

## 版本

当前版本：**1.10.0** — v1.10.0：配合 skill-standardization v2.12.0 路径规范升级，同步版本号
