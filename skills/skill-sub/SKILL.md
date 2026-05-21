---
agent_created: true
---

# Skill Chain - 多技能调用链编排

> 将多个 Skill 在用户意图下整合为可复用的执行链。提取关键步骤、统一规划、持久存储、一键执行。

---

## 核心概念

### 什么是调用链（Chain）

调用链是一组有序的 Skill 执行步骤，抽象了用户完成某类任务时需要的多技能协作流程。它：

- **不改变原始 Skill**：只记录调用方式和关键步骤，实际执行仍通过原始 Skill 完成
- **提取关键步骤**：从 SKILL.md 中提炼精炼的执行要点，减少上下文占用
- **可复用**：保存后可反复使用，无需每次重新规划
- **可调整**：支持增删改步骤、调整顺序、修改参数

### 数据结构

```
Chain（调用链）
├── name: string          # 唯一名称，用于查询和执行
├── description: string   # 调用链描述
├── purpose: string       # 核心目的
├── user_intent: string   # 用户原始意图
├── tags: string[]        # 标签（便于搜索）
├── created_at: datetime
├── updated_at: datetime
├── exec_count: number    # 执行次数
└── steps: Step[]         # 有序步骤数组

Step（步骤）
├── index: number         # 步骤序号（从1开始）
├── skill_name: string    # 调用的技能名称
├── step_name: string     # 步骤名称
├── action: string        # 精炼的关键动作描述
├── detail: string        # 详细执行说明（可选）
├── depends_on: number[]  # 依赖的步骤索引（可选，默认依赖前一步）
├── condition: string     # 条件表达式（可选，默认无条件执行）
├── variables: object     # 步骤级变量（输入/输出映射）
└── notes: string         # 备注（可选）
```

---

## 触发场景

当用户执行以下操作时触发本技能：

| 场景 | 触发指令示例 |
|------|-------------|
| **创建调用链** | 「帮我规划一个调用链」「创建技能调用链」「编排多技能流程」 |
| **预生成调用链** | 「帮我看看哪些技能可以用」「我需要做XX，有哪些技能可以组合」 |
| **查询调用链** | 「查看调用链」「列出所有调用链」「有哪些已保存的调用链」 |
| **执行调用链** | 「运行调用链XX」「用调用链XX完成任务」「执行XX调用链」 |
| **调整调用链** | 「修改调用链XX」「给XX调用链添加步骤」「调整XX的步骤顺序」 |
| **描述意图直接执行** | 「帮我做XX（涉及多技能）」→ 自动匹配或创建调用链 |

---

## 核心指令

### 1. 创建调用链 (`create`)

**触发**：用户描述需要组合多个技能完成任务。

**AI 执行流程**：

```
步骤 A：分析用户意图
  → 理解用户想完成什么
  → 识别需要哪些技能参与
  → 如果用户未指定技能，扫描 ~/.workbuddy/skills/ 下列出可用技能

步骤 B：读取技能信息
  → 对每个涉及的技能，读取其 SKILL.md
  → 提取关键执行步骤（触发条件、核心指令、输入输出）
  → 使用 scripts/skill_extractor.py 辅助提取

步骤 C：规划执行步骤
  → 根据用户意图，将多个技能的关键步骤整合为有序步骤列表
  → 确定步骤间的依赖关系
  → 识别可并行的步骤
  → 标注步骤间的数据传递关系

步骤 D：展示规划并确认
  → 以表格形式展示调用链规划
  → 列出每个步骤：技能名、步骤名、动作描述、依赖关系
  → 询问用户确认或调整

步骤 E：命名与保存
  → 自动根据目的生成建议名称
  → 询问用户确认名称或自定义
  → 询问用户是否保存（记录）调用链
  → 如果保存，调用 chain_manager.py create
```

**输出格式**：

```
【调用链规划】{名称}

📌 目的：{一句话说明}
🏷️ 标签：{tag1, tag2}
📝 用户意图：{用户原始意图}

执行步骤：
  ┌──────┬─────────────────┬──────────────┬──────────────────────────────┐
  │ 步骤 │ 技能            │ 步骤名称     │ 关键动作                     │
  ├──────┼─────────────────┼──────────────┼──────────────────────────────┤
  │  1   │ {skill_1}       │ {step_name}  │ {精炼动作描述}               │
  │  2   │ {skill_2}       │ {step_name}  │ {精炼动作描述}               │
  │  ... │                 │              │                              │
  └──────┴─────────────────┴──────────────┴──────────────────────────────┘

依赖关系：步骤2 → 依赖步骤1（说明数据传递）
并行机会：步骤3 和 步骤4 可并行执行

是否保存此调用链？（y/n）
调用链名称：{建议名称}，可自定义
```

### 2. 预生成调用链 (`suggest`)

**触发**：用户告知意图但未指定具体技能，希望 AI 推荐技能组合。

**AI 执行流程**：

```
步骤 A：理解用户意图
  → 分析用户描述的任务目标

步骤 B：扫描可用技能
  → 列出 ~/.workbuddy/skills/ 下所有已安装技能
  → 对每个技能读取 SKILL.md 的 description 和触发条件
  → 筛选与用户意图相关的技能

步骤 C：匹配技能组合
  → 根据意图匹配最相关的 2-5 个技能
  → 按执行逻辑排序（数据准备 → 核心处理 → 结果输出）
  → 如果有多个可行组合，列出推荐方案

步骤 D：展示建议
  → 推荐方案：技能组合 + 预估步骤
  → 备选方案（如有）
  → 询问用户选择哪个方案或自定义
```

**输出格式**：

```
【技能组合建议】

🎯 用户意图：{意图描述}

📌 推荐方案：
  涉及技能：{skill_1} → {skill_2} → {skill_3}
  预估步骤：{N} 步
  组合理由：{为什么选这些技能}

📌 备选方案（如有）：
  方案B：{技能组合} - {简述}

选择方案或自定义？（输入方案编号 / 自定义技能组合）
```

### 3. 查询调用链 (`list` / `show`)

**触发**：用户查看已保存的调用链。

**AI 执行流程**：

```
步骤 A：读取调用链列表
  → 调用 chain_manager.py list 列出所有调用链
  → 或 chain_manager.py show --name {name} 查看详情

步骤 B：展示结果
  → 列表模式：名称、描述、步骤数、执行次数、创建时间
  → 详情模式：完整步骤列表
```

**CLI 调用**：

```bash
# 列出所有调用链
python {SKILL_DIR}/scripts/chain_manager.py list

# 查看指定调用链详情
python {SKILL_DIR}/scripts/chain_manager.py show --name "调用链名称"

# 按标签搜索
python {SKILL_DIR}/scripts/chain_manager.py list --tag "标签名"
```

### 4. 执行调用链 (`run`)

**触发**：用户指定调用链名称并要求执行。

**AI 执行流程**：

```
步骤 A：加载调用链
  → 调用 chain_manager.py show --name {name} 获取完整定义
  → 检查所有涉及的技能是否已安装

步骤 B：解析执行计划
  → 构建步骤依赖图
  → 确定执行顺序（考虑并行机会）
  → 准备步骤间变量传递

步骤 C：逐步执行
  → 按顺序加载每个技能
  → 按照 action 描述执行关键步骤
  → 处理步骤间数据传递
  → 支持 condition 条件判断（跳过/执行）
  → 每步执行后简要汇报结果

步骤 D：执行总结
  → 汇总所有步骤执行结果
  → 更新调用链执行次数
```

**CLI 调用**：

```bash
# 执行调用链
python {SKILL_DIR}/scripts/chain_manager.py run --name "调用链名称"

# 执行并输出详细步骤
python {SKILL_DIR}/scripts/chain_manager.py run --name "调用链名称" --verbose
```

**⚠️ 重要执行规则**：

1. **原始技能优先**：执行时必须加载原始 SKILL.md，按照原始技能的指令执行，不可跳过或简化
2. **上下文精炼**：加载技能前，先向用户展示本步骤的精炼 action，让用户了解即将做什么
3. **步骤隔离**：每个技能步骤执行完成后，记录关键输出（变量），作为后续步骤的输入
4. **错误处理**：某步失败时，询问用户是否跳过、重试或中止整个调用链

### 5. 调整调用链 (`edit`)

**触发**：用户修改已保存的调用链。

**支持的调整操作**：

| 操作 | 指令示例 | 说明 |
|------|---------|------|
| 添加步骤 | 「给XX添加一步YY」 | 在指定位置插入新步骤 |
| 删除步骤 | 「删除XX的第N步」 | 移除指定步骤 |
| 修改步骤 | 「修改XX的第N步为YY」 | 更新步骤的技能/动作 |
| 调整顺序 | 「把XX的第N步移到第M步」 | 重新排序 |
| 修改依赖 | 「XX的第N步依赖第M步」 | 更新依赖关系 |
| 修改名称/描述 | 「重命名XX为YY」 | 更新元数据 |

**CLI 调用**：

```bash
# 添加步骤
python {SKILL_DIR}/scripts/chain_manager.py add-step --name "调用链名称" --after 2 \
  --skill "skill_name" --step-name "步骤名" --action "动作描述"

# 删除步骤
python {SKILL_DIR}/scripts/chain_manager.py remove-step --name "调用链名称" --step 3

# 更新步骤
python {SKILL_DIR}/scripts/chain_manager.py update-step --name "调用链名称" --step 2 \
  --action "新的动作描述"

# 重命名调用链
python {SKILL_DIR}/scripts/chain_manager.py rename --name "旧名称" --new-name "新名称"
```

### 6. 删除调用链 (`delete`)

**触发**：用户删除不再需要的调用链。

```bash
python {SKILL_DIR}/scripts/chain_manager.py delete --name "调用链名称"
```

**⚠️ 必须确认**：删除前必须向用户展示调用链信息并请求确认。

---

## 存储机制

### 数据目录

| 路径 | 说明 |
|------|------|
| `CHAIN_HOME/chains/` | 调用链 JSON 文件（每个链一个文件） |
| `CHAIN_HOME/chains/index.json` | 调用链索引（名称→文件路径映射） |
| `CHAIN_HOME/templates/` | 调用链模板（可选，预置常用组合） |
| `CHAIN_HOME/config.json` | 配置文件 |

**默认 CHAIN_HOME**：`~/.workbuddy/skill-sub/`

### 文件格式

**调用链文件**：`chains/{name}.json`

```json
{
  "name": "技能发布流水线",
  "description": "技能开发完成后的一站式发布流程",
  "purpose": "将技能从本地开发环境发布到 SkillHub/ClawHub",
  "user_intent": "我想把开发好的技能打包发布",
  "tags": ["发布", "技能管理", "git"],
  "steps": [
    {
      "index": 1,
      "skill_name": "skills-security-check",
      "step_name": "安全审计",
      "action": "对 SKILL.md 和所有脚本文件进行安全审计",
      "detail": "检查 P0/P1/P2 风险级别",
      "depends_on": [],
      "variables": {
        "input": {"skill_path": "{skill_dir}"},
        "output": {"audit_result": "通过/不通过"}
      }
    },
    {
      "index": 2,
      "skill_name": "skill-sub",
      "step_name": "打包ZIP",
      "action": "按规则打包技能为ZIP（仅含SKILL.md、_meta.json、scripts/*.py）",
      "depends_on": [1],
      "variables": {
        "input": {"audit_result": "通过"},
        "output": {"zip_path": "{workspace}/{name}.zip"}
      }
    },
    {
      "index": 3,
      "skill_name": "git-sync",
      "step_name": "同步仓库",
      "action": "将技能代码推送到 GitHub 仓库",
      "depends_on": [1],
      "variables": {
        "input": {"audit_result": "通过"},
        "output": {"repo_url": "..."}
      }
    }
  ],
  "created_at": "2026-05-21T15:30:00",
  "updated_at": "2026-05-21T15:30:00",
  "exec_count": 0
}
```

---

## AI 执行指令（Agent 必读）

### 核心原则

1. **不替代原始技能**：本技能是编排层，实际执行必须通过加载原始 SKILL.md 完成
2. **精炼提取**：从原始 SKILL.md 中提取最关键的执行步骤，而非复制全文
3. **变量传递**：注意步骤间的数据依赖，将上一步的输出作为下一步的输入
4. **用户确认**：创建和修改调用链时必须请用户确认；执行时默认直接执行（除非链中配置了确认点）

### 创建调用链的完整流程

```
收到用户创建请求
  │
  ├─ 1. 分析意图 → 识别需要的技能列表
  │
  ├─ 2. 如果用户未指定技能：
  │   → 扫描 ~/.workbuddy/skills/ 获取可用技能列表
  │   → 读取每个相关技能的 SKILL.md（只需 description + 触发条件 + 核心指令部分）
  │   → 推荐技能组合方案
  │
  ├─ 3. 读取所有涉及技能的 SKILL.md
  │   → 使用 skill_extractor.py 提取关键步骤
  │   → 或由 AI 直接阅读并提炼
  │
  ├─ 4. 规划执行步骤
  │   → 按执行逻辑排序
  │   → 标注依赖关系
  │   → 识别并行机会
  │
  ├─ 5. 展示规划（表格形式）
  │   → 请用户确认或调整
  │
  ├─ 6. 命名
  │   → AI 根据目的自动生成建议名称
  │   → 用户可自定义
  │
  ├─ 7. 询问是否保存
  │   → 保存 → chain_manager.py create
  │   → 不保存 → 仅本次执行
  │
  └─ 8. 如果用户要求立即执行 → 进入执行流程
```

### 执行调用链的完整流程

```
收到执行请求（chain_name）
  │
  ├─ 1. 加载调用链定义
  │   → chain_manager.py show --name {chain_name}
  │   → 检查涉及技能是否已安装
  │
  ├─ 2. 展示执行概览
  │   → 步骤列表 + 预计执行内容
  │
  ├─ 3. 逐步执行
  │   对于每个步骤：
  │     a. 展示精炼 action（让用户知道即将做什么）
  │     b. 加载对应技能的 SKILL.md
  │     c. 按 action 描述执行关键步骤
  │     d. 记录输出变量
  │     e. 汇报执行结果
  │
  ├─ 4. 执行总结
  │   → 各步骤结果汇总
  │   → 更新 exec_count
  │
  └─ 5. 错误处理
      → 失败步骤：询问 跳过/重试/中止
      → 部分成功：记录哪些步骤完成、哪些未完成
```

### 意图自动匹配（智能推荐）

当用户只描述任务（未指定调用链名称）时：

```
用户：「帮我做XX」
  │
  ├─ 1. 搜索已保存调用链
  │   → 按标签和描述匹配用户意图
  │   → 找到匹配 → 建议使用该调用链
  │
  ├─ 2. 未找到匹配 → 进入预生成流程
  │   → 扫描可用技能
  │   → 推荐技能组合
  │   → 生成调用链规划
  │
  └─ 3. 展示建议 → 用户确认 → 执行
```

---

## 脚本清单

| 脚本 | 功能 | 依赖 |
|------|------|------|
| `chain_manager.py` | 调用链 CRUD + 执行（create/list/show/run/edit/delete） | 无（标准库） |
| `skill_extractor.py` | 从 SKILL.md 提取关键步骤 | 无（标准库） |

所有脚本零外部依赖，仅使用 Python 标准库。跨平台支持 Windows/Linux/macOS。

---

## CLI 速查

```bash
# 初始化数据目录
python {SKILL_DIR}/scripts/chain_manager.py init

# 创建调用链
python {SKILL_DIR}/scripts/chain_manager.py create --name "名称" \
  --description "描述" --purpose "目的" --steps '[...]'

# 列出所有调用链
python {SKILL_DIR}/scripts/chain_manager.py list [--tag "标签"]

# 查看调用链详情
python {SKILL_DIR}/scripts/chain_manager.py show --name "名称"

# 执行调用链
python {SKILL_DIR}/scripts/chain_manager.py run --name "名称" [--verbose]

# 编辑调用链
python {SKILL_DIR}/scripts/chain_manager.py add-step --name "名称" --after N \
  --skill "技能" --step-name "步骤名" --action "动作"
python {SKILL_DIR}/scripts/chain_manager.py remove-step --name "名称" --step N
python {SKILL_DIR}/scripts/chain_manager.py update-step --name "名称" --step N \
  --action "新动作"
python {SKILL_DIR}/scripts/chain_manager.py rename --name "旧名" --new-name "新名"

# 删除调用链
python {SKILL_DIR}/scripts/chain_manager.py delete --name "名称"

# 提取技能关键步骤
python {SKILL_DIR}/scripts/skill_extractor.py extract --skill "技能名" [--path "路径"]

# 扫描所有技能（预生成用）
python {SKILL_DIR}/scripts/skill_extractor.py scan [--tag "标签"]
```

---

## 使用示例

### 示例 1：首次创建调用链

```
用户：帮我规划一个调用链，用于技能开发和发布

AI：
  【技能扫描】发现以下相关技能：
  - skills-security-check（安全审计）
  - git-sync（Git 同步）
  - drawiodo（绘图）

  【调用链规划】技能发布流水线

  📌 目的：将技能从开发到发布的一站式流程
  🏷️ 标签：发布, 技能管理

  执行步骤：
  ┌──────┬───────────────────────┬──────────────┬────────────────────────────┐
  │ 步骤 │ 技能                  │ 步骤名称     │ 关键动作                   │
  ├──────┼───────────────────────┼──────────────┼────────────────────────────┤
  │  1   │ skills-security-check │ 安全审计     │ 审计SKILL.md和脚本文件     │
  │  2   │ (内置打包)            │ ZIP打包      │ 按规则打包为ZIP            │
  │  3   │ git-sync              │ 代码同步     │推送到GitHub仓库            │
  └──────┴───────────────────────┴──────────────┴────────────────────────────┘

  建议名称：技能发布流水线
  是否保存此调用链？(y/n)
```

### 示例 2：直接使用调用链执行

```
用户：用「技能发布流水线」发布 svg-composer 技能

AI：
  【加载调用链】技能发布流水线（3步）

  步骤 1/3：安全审计
  → 加载 skills-security-check 技能
  → 审计 svg-composer 的 SKILL.md 和 scripts/
  → 结果：✅ P2 安全

  步骤 2/3：ZIP打包
  → 按规则打包：SKILL.md + _meta.json + scripts/*.py
  → 结果：✅ svg-composer-v3.2.0.zip

  步骤 3/3：代码同步
  → 加载 git-sync 技能
  → 推送到 GitHub Ldxs001/workbuddy-skills
  → 结果：✅ 已推送

  【执行完成】3/3 步骤成功
```

### 示例 3：意图匹配自动推荐

```
用户：帮我做一篇学术论文的深度调研

AI：
  【意图分析】学术调研需要：搜索+深度阅读+引用管理

  未找到匹配的已保存调用链，推荐技能组合：

  📌 推荐方案：
  涉及技能：Deep Research（调研框架）→ arxiv-reader（论文精读）→ citation-manager（引用管理）
  预估步骤：5步
  组合理由：先确定调研范围，再精读关键论文，最后整理引用

  是否创建调用链「学术论文深度调研」？(y/n)
```

---

## 注意事项

1. **技能可发现性**：预生成功能依赖技能的 SKILL.md 中有清晰的 description 和触发条件描述
2. **步骤粒度**：action 字段应精炼到一句话，detail 可展开说明。太长会浪费上下文，太短会丢失关键信息
3. **并行执行**：当两个步骤无依赖关系时，可标注为可并行，但实际执行由 AI 判断是否真的并行
4. **版本兼容**：如果技能更新导致 SKILL.md 结构变化，调用链中的步骤可能需要更新
5. **错误恢复**：执行中断后，可从失败的步骤继续执行
