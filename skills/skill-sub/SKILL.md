# skill-sub

> **调用链编排技能** - 将多个 Skill 整合为可复用的执行链，步骤级串联，减少上下文占用。

**版本**: 1.2.0 | **零外部依赖** | **跨平台**

---

## 核心概念

### 什么是调用链

调用链（Chain）是一条预定义的执行流水线，将多个 Skill 的**关键步骤**按依赖关系串联，形成可复用的执行模板。

**与直接逐个调用 Skill 的区别**：

| 维度 | 逐个调用 Skill | 使用调用链 |
|------|---------------|-----------|
| 上下文占用 | 每次加载完整 SKILL.md | 仅加载精炼的 action 描述 |
| 执行顺序 | 依赖 AI 记忆 | 结构化依赖图，确定性执行 |
| 复用性 | 每次重新描述 | 一键执行，可分享 |
| 错误处理 | 无策略 | 分级重试 + 里程碑中止 |

### 数据结构

**Chain（调用链）**：
```
Chain
├── name: string          # 唯一名称
├── description: string   # 调用链描述
├── purpose: string       # 核心目的
├── user_intent: string   # 用户原始意图
├── tags: string[]        # 标签
├── created_at: datetime
├── updated_at: datetime
├── exec_count: number    # 执行次数
└── steps: Step[]         # 有序步骤数组
```

**Step（步骤）**：
```
Step
├── index: number              # 步骤序号（从1开始）
├── skill_name: string         # 调用的技能名称
├── step_name: string          # 步骤名称
├── action: string             # 精炼的关键动作描述
├── skill_instruction: string  # 原始指令名称（从 SKILL.md 提取）
├── detail: string             # 详细执行说明（可选）
├── depends_on: number[]       # 依赖的步骤索引（可选，默认依赖前一步）
├── condition: string          # 条件表达式（可选）
├── variables: object          # 步骤级变量（输入/输出映射）
├── retry_policy: object       # 重试策略（可选，有默认值）
├── failure_mode: object       # 失败处理模式（可选，有默认值+自动判断）
└── notes: string              # 备注（可选）
```

**retry_policy（重试策略）**：
```
retry_policy
├── max_retries: number    # 最大重试次数（默认从设置读取，默认3）
└── error_types: string[]  # 适用的错误类型（可选，默认全部）
    可选值:
    - file_locked     # 文件占用/锁定（立即重试，0s）
    - network_error   # 网络不通/超时（间隔5秒）
    - auth_error      # 认证/权限错误（直接询问用户，不重试）
    - timeout         # 执行超时（间隔5秒）
```

**failure_mode（失败处理模式）**：
```
failure_mode
├── on_exhaust: string   # 重试耗尽后行为: "ask" | "skip" | "abort"
└── is_milestone: bool   # 是否为里程碑步骤（可通过通用规则自动判断）
```

---

## 触发方式

### 1. 用户主动调用

用户明确要求创建或执行调用链时触发。

触发示例：
- "创建一条发布流水线的调用链"
- "执行发布流水线"
- "列出所有调用链"
- "用 skill-sub 管理调用链"

### 2. 意图关键词自动匹配

当用户意图与已保存调用链的 `tags`/`description`/`user_intent` 重合度 > 50% 时，自动推荐匹配的调用链。

匹配规则：
1. 提取用户输入的关键词
2. 与每条调用链的 tags + description + user_intent 做关键词重合度计算
3. 重合度 > 50% → 推荐给用户确认
4. 用户确认后自动执行

---

## 设置

### 设置项说明

| 设置项 | 选项 | 说明 |
|--------|------|------|
| **记忆参考** | 是 / 否 | 创建/执行调用链时，是否读取用户记忆文件增强步骤描述 |
| **命名方式** | 自动 / 人工 | 创建调用链时，由 AI 自动命名还是询问用户 |
| **默认重试次数** | 1-10（默认3） | 所有步骤的默认最大重试次数 |

### 当前配置

> **配置路径**：`~/.workbuddy/skill-sub/config.json`
> **默认配置**：`{skill_dir}/assets/default_config.json`

通过以下方式查看和修改配置：

**方式 1：HTML 设置界面（推荐）**

Agent 执行：
1. 运行 `python {SKILL_DIR}/scripts/settings.py --serve-only`
2. 解析输出中的 `SERVER_STARTED:<port>`
3. 打开浏览器 `http://localhost:{port}/`
4. 轮询 `{SKILL_DIR}/.settings_done` 标志文件
5. 检测到标志文件后关闭服务器

**方式 2：命令行查看**

```bash
python {SKILL_DIR}/scripts/settings.py --get-config
```

**方式 3：命令行保存**

```bash
python {SKILL_DIR}/scripts/settings.py --save-config '{"use_memory_reference": true, "naming_mode": "auto", "default_max_retries": 5}'
```

### 对话式设置（回退方案）

当 HTML 设置界面无法打开时，通过对话方式收集配置：

```
步骤 1：记忆参考
是否在创建调用链时参考用户记忆文件？（输入 y/n）:

步骤 2：命名方式
调用链命名方式（输入 1/2 选择）：
1. 自动 — AI 根据意图和目的自动生成名称
2. 人工 — 每次创建时询问用户
请输入：

步骤 3：默认重试次数
请输入默认最大重试次数（1-10，默认3）:

步骤 4：保存
Agent 执行: python settings.py --save-config '<json>'
```

---

## 里程碑通用判断规则

> **设计原则**：不完全依赖 AI 自觉判断，基于步骤的**结构特征**自动确定里程碑。

### 判断规则（优先级从高到低）

| 优先级 | 规则 | 说明 | 示例 |
|--------|------|------|------|
| 1 | 用户显式标记 | `is_milestone=true` | 用户手动指定 |
| 2 | 显式取消 | `is_milestone=false` | 用户明确不需要 |
| 3 | 短链全部标记 | 总步骤数 ≤ 2 → 全部里程碑 | 链太短，每步都关键 |
| 4 | 关键词匹配 | 步骤名包含特定关键词 → 里程碑 | "安全审计"、"部署上线" |
| 5 | 瓶颈点 | 被 ≥2 个后续步骤依赖 → 里程碑 | 多个步骤依赖该步骤的输出 |
| 6 | 最终交付 | 是最后一步 → 里程碑 | 最终产出物 |
| 7 | 默认非里程碑 | 以上均不满足 | 辅助/中间步骤 |

### 里程碑关键词

中英文关键词（步骤名包含任一即匹配）：

```
审计、安全、部署、发布、上线、打包、测试、验证、校验、审批、审核、
付款、支付、下单、提交、推送、导入、导出、迁移、备份、恢复、
audit、deploy、release、publish、push、test、verify、validate、
approve、review、payment、submit、import、export、migrate、
backup、restore、build、compile、install
```

### 里程碑行为

- **里程碑步骤失败** → 无论 `on_exhaust` 设置如何，**强制中止整条链**
- **里程碑步骤的 on_exhaust** → 建议设为 `abort`（validate 时会发出警告）
- **非里程碑步骤失败** → 按 `on_exhaust` 设置处理（ask/skip/abort）

---

## 核心指令

### 创建（create）

AI 执行 6 步流程：

1. **分析意图**：理解用户想串联哪些技能、达成什么目的
2. **读取技能信息**：对每个涉及技能，运行 `skill_extractor.py scan` 提取关键步骤和指令
3. **规划步骤**：确定步骤顺序、依赖关系、并行机会
4. **设置策略**：根据里程碑规则自动判断 + 用户确认调整
5. **展示确认**：展示完整调用链供用户确认（包括里程碑标记和判断依据）
6. **命名保存**：根据设置决定自动命名或询问用户

> **记忆参考（设置启用时）**：在步骤2后，读取 MEMORY.md 和近期日志，提取用户偏好和习惯，用于增强步骤描述的个性化。

### 预生成（suggest）

扫描已安装技能，推荐可能的技能组合：

```bash
python {SKILL_DIR}/scripts/skill_extractor.py scan
```

### 查询（list / show）

```bash
# 列出所有调用链
python {SKILL_DIR}/scripts/chain_manager.py list
python {SKILL_DIR}/scripts/chain_manager.py list --tag "发布"

# 查看详情（含里程碑判断依据）
python {SKILL_DIR}/scripts/chain_manager.py show --name "发布流水线"

# 查看当前配置
python {SKILL_DIR}/scripts/chain_manager.py config
```

### 执行（run）

三步执行流程：

1. **生成执行计划**：`chain_executor.py plan --name <名称>`
2. **按计划执行**：AI 读取执行计划，逐步执行
3. **汇报结果**：每步执行后汇报 ✅/❌，里程碑步骤失败则中止

**三层回退策略**：
- **第一层**：仅用 action 精炼描述直接执行（上下文占用最低）
- **第二层**：按需读取 SKILL.md 对应指令片段（通过 skill_instruction 定位）
- **第三层**：加载完整 SKILL.md（上下文占用最高，仅必要时使用）

**分级重试策略**：

| 错误类型 | 重试间隔 | 说明 |
|---------|---------|------|
| file_locked | 0 秒 | 文件占用/锁定，立即重试 |
| network_error | 5 秒 | 网络不通/超时 |
| timeout | 5 秒 | 执行超时 |
| auth_error | - | 认证/权限错误，直接询问用户 |
| other | 2 秒 | 其他错误 |

重试次数从设置读取（默认3次），耗尽后按 `on_exhaust` 处理。

### 调整（edit）

```bash
# 添加步骤
python {SKILL_DIR}/scripts/chain_manager.py add-step --name "链名" --after 1 --skill "技能名" --step-name "步骤名" --action "动作"

# 删除步骤
python {SKILL_DIR}/scripts/chain_manager.py remove-step --name "链名" --step 3

# 更新步骤
python {SKILL_DIR}/scripts/chain_manager.py update-step --name "链名" --step 2 --action "新动作"
python {SKILL_DIR}/scripts/chain_manager.py update-step --name "链名" --step 1 --milestone
python {SKILL_DIR}/scripts/chain_manager.py update-step --name "链名" --step 3 --no-milestone
python {SKILL_DIR}/scripts/chain_manager.py update-step --name "链名" --step 1 --retry-max 5
python {SKILL_DIR}/scripts/chain_manager.py update-step --name "链名" --step 2 --on-exhaust abort

# 重命名
python {SKILL_DIR}/scripts/chain_manager.py rename --name "旧名" --new-name "新名"
```

### 删除（delete）

```bash
python {SKILL_DIR}/scripts/chain_manager.py delete --name "链名" --force
```

---

## 存储机制

### 数据目录

```
~/.workbuddy/skill-sub/
├── config.json           # 用户配置（设置界面写入）
└── chains/               # 调用链数据
    ├── index.json        # 调用链索引
    ├── 发布流水线.json    # 每条链一个文件
    └── ...
```

### 调用链 JSON 格式

```json
{
  "name": "发布流水线",
  "description": "技能发布完整流程",
  "purpose": "一键发布技能到 SkillHub/ClawHub",
  "user_intent": "帮我打包发布这个技能",
  "tags": ["发布", "技能管理"],
  "created_at": "2026-05-21T15:00:00",
  "updated_at": "2026-05-21T19:00:00",
  "exec_count": 5,
  "steps": [
    {
      "index": 1,
      "skill_name": "skills-security-check",
      "step_name": "安全审计",
      "action": "对技能目录执行安全审计，检查敏感信息泄露",
      "skill_instruction": "security-audit",
      "depends_on": [],
      "retry_policy": {"max_retries": 3},
      "failure_mode": {"on_exhaust": "abort", "is_milestone": true}
    },
    {
      "index": 2,
      "skill_name": "(内置)",
      "step_name": "打包",
      "action": "按规范打包为 ZIP（仅含 SKILL.md、_meta.json、scripts/*.py）",
      "depends_on": [1],
      "retry_policy": {"max_retries": 3},
      "failure_mode": {"on_exhaust": "ask", "is_milestone": false}
    },
    {
      "index": 3,
      "skill_name": "git-sync",
      "step_name": "推送代码",
      "action": "推送到 Gitee 和 GitHub 仓库",
      "depends_on": [2],
      "retry_policy": {"max_retries": 3, "error_types": ["network_error", "timeout"]},
      "failure_mode": {"on_exhaust": "ask", "is_milestone": false}
    }
  ]
}
```

---

## AI 执行指令

### Agent 必读原则

1. **执行前通读调用链**：读取整条链的所有步骤，理解全局依赖关系
2. **三层回退**：每个步骤优先用 action 执行，不充分时再读取 SKILL.md
3. **里程碑步骤失败立即中止**：不继续后续步骤
4. **非里程碑步骤失败按 on_exhaust 处理**：ask（询问）/ skip（跳过）/ abort（中止）
5. **记录变量传递**：步骤输出变量作为后续步骤输入
6. **命名遵循设置**：`naming_mode=auto` 时 AI 自动命名，`manual` 时询问用户

### 完整流程图

```
用户触发创建
  │
  ├─ 分析意图 → 确定需要哪些技能
  │
  ├─ 读取技能信息（skill_extractor.py scan）
  │   └─ [设置: 记忆参考=是] → 额外读取 MEMORY.md + 日志
  │
  ├─ 规划步骤（提取关键步骤 → 排列顺序 → 设置依赖）
  │
  ├─ 里程碑判断（classify_milestones 自动判断）
  │   ├─ 关键词匹配
  │   ├─ 瓶颈点检测
  │   └─ 最后一步标记
  │   └─ 展示判断依据 → 用户确认调整
  │
  ├─ 展示完整调用链 → 用户确认
  │
  └─ 命名保存
      ├─ [设置: naming_mode=auto] → AI 自动命名
      └─ [设置: naming_mode=manual] → 询问用户
```

```
用户触发执行
  │
  ├─ 生成执行计划（chain_executor.py plan）
  │
  ├─ 逐步骤执行
  │   ├─ 第一层：用 action 直接执行
  │   ├─ 失败 → 分级重试（最多 N 次，N 从设置读取）
  │   ├─ 仍失败 → 按 on_exhaust 处理
  │   │   ├─ ask → 询问用户
  │   │   ├─ skip → 跳过，继续下一步
  │   │   └─ abort → 中止整条链
  │   │
  │   └─ 里程碑步骤失败 → 强制中止（无论 on_exhaust）
  │
  └─ 汇报结果
```

---

## 脚本清单

| 脚本 | 功能 |
|------|------|
| `chain_manager.py` | 调用链 CRUD（init/create/list/show/run/add-step/remove-step/update-step/rename/delete/config） |
| `chain_executor.py` | 执行引擎（plan/quick/validate） + 里程碑分类 + 配置集成 |
| `skill_extractor.py` | 从 SKILL.md 提取关键步骤和指令名称（extract/scan） |
| `settings.py` | HTML 设置界面 + CLI 配置管理（v1.2.0 新增） |

---

## CLI 速查

```bash
# 初始化
python chain_manager.py init

# 设置
python settings.py                          # 交互式设置（打开浏览器）
python settings.py --serve-only             # Agent 模式
python settings.py --get-config             # 查看配置
python settings.py --save-config '<json>'   # 保存配置
python chain_manager.py config              # 查看配置

# 创建
python chain_manager.py create --name "链名" --description "描述" --purpose "目的" --steps '[...]'

# 查询
python chain_manager.py list [--tag "标签"]
python chain_manager.py show --name "链名"

# 执行
python chain_executor.py plan --name "链名" [-v] [--json]
python chain_executor.py quick --steps '[...]' --name "临时"
python chain_executor.py validate --name "链名"

# 调整
python chain_manager.py add-step --name "链名" ...
python chain_manager.py remove-step --name "链名" --step N
python chain_manager.py update-step --name "链名" --step N [--action ...] [--milestone] [--retry-max N]
python chain_manager.py rename --name "旧名" --new-name "新名"

# 删除
python chain_manager.py delete --name "链名" --force
```

---

## 使用示例

### 示例 1：创建发布流水线

```
用户：帮我创建一条发布流水线的调用链，包含安全审计、打包、推送

AI：
  1. 分析意图 → 需要 skills-security-check + 内置打包 + git-sync
  2. 读取技能信息 → 提取关键步骤
  3. 规划步骤：
     步骤1: 安全审计 → 依赖:无 → 里程碑(关键词:审计)
     步骤2: 打包 → 依赖:[1] → 非里程碑
     步骤3: 推送代码 → 依赖:[2] → 非里程碑(最后一步→里程碑)
  4. 展示确认
  5. [设置: naming_mode=auto] → AI 命名为 "发布流水线"
  6. 保存
```

### 示例 2：执行调用链

```
用户：执行发布流水线

AI：
  1. 生成执行计划 → 3步，2个里程碑
  2. 步骤1（安全审计）→ 第一层 action → ✅成功
  3. 步骤2（打包）→ 第一层 action → ❌文件占用
     → 分级重试: file_locked → 立即重试 → ✅成功
  4. 步骤3（推送代码）→ 第一层 action → ❌网络错误
     → 分级重试: network_error → 5秒后重试 → ✅成功
  5. 汇报: 全部 3/3 步成功
```

### 示例 3：查看里程碑判断

```
用户：查看发布流水线详情

AI：
  📌 调用链: 发布流水线
  ...
  📐 里程碑判断依据:
     ★ 步骤1(安全审计): 关键词匹配: '审计'
     ○ 步骤2(打包): 默认规则（非关键节点）
     ★ 步骤3(推送代码): 最终交付步骤
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SKILL_SUB_HOME` / `SKILL_CHAIN_HOME` | 数据目录 | `~/.workbuddy/skill-sub/` |
| `WORKBUDDY_SKILLS_DIR` | 技能安装目录 | `~/.workbuddy/skills/` |
