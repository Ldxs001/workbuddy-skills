# skill-sub 调用链数据结构

> 本文档定义 Chain / Step / retry_policy / failure_mode 的完整结构。
>
> **v1.20.0 新增**：Step 支持三种类型（skill / loop / branch），详见 Step 扩展类型章节。

---

## Chain（调用链）

```json
{
  "name": "string",           // 唯一名称
  "description": "string",     // 调用链描述
  "purpose": "string",        // 核心目的
  "user_intent": "string",    // 用户原始意图（用于意图匹配）
  "tags": ["string"],         // 标签（用于自动匹配）
  "created_at": "datetime",
  "updated_at": "datetime",
  "exec_count": 0,            // 执行次数
  "steps": [ ... ]            // Step 数组，见下文
}
```

---

## Step（步骤）

> **步骤类型**：通过 `type` 字段区分技能调用、循环、分支。默认 `type: "skill"`。
> `steps` / `if_steps` / `else_steps` 均为 Step 数组，支持递归嵌套。

### 通用字段（所有类型均含）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `index` | int | ✅ | 步骤序号（从 1 开始，全局唯一） |
| `type` | string | ✅ | `"skill"` / `"loop"` / `"branch"` |
| `step_name` | string | ✅ | 步骤名称（展示用） |
| `depends_on` | int[] | ❌ | 依赖的前置步骤索引，默认 `[index-1]` |
| `condition` | string | ❌ | 步骤级条件：非 `"always"` 时按需求值，为 `false` 则跳过本步骤 |
| `failure_mode` | object | ❌ | 失败处理（见下文） |
| `notes` | string | ❌ | 备注 |

---

### 类型 A：`"type": "skill"`（技能调用步骤）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `skill_name` | string | ✅ | 调用的技能名称（须已安装） |
| `action` | string | ✅ | 精炼动作描述（第一层执行用） |
| `skill_instruction` | string | ❌ | 对应 SKILL.md 中的指令名（第二层回退用） |
| `detail` | string | ❌ | 详细执行说明（第三层回退用） |
| `variables` | object | ❌ | 步骤级变量映射 `{"input": "{{step1.output}}", "output": "result"}` |
| `retry_policy` | object | ❌ | 重试策略（见下文） |

**示例：**

```json
{
  "index": 1,
  "type": "skill",
  "step_name": "代码审查",
  "skill_name": "code-review",
  "action": "审查 PR #123 的代码变更",
  "skill_instruction": "review-pr",
  "depends_on": [],
  "condition": "always",
  "variables": {"input": "{{pr_number}}", "output": "review_result"},
  "retry_policy": {"max_retries": 3, "error_types": ["network_error", "timeout"]},
  "failure_mode": {"on_exhaust": "ask", "is_milestone": false},
  "notes": "第一步，不依赖其他步骤"
}
```

---

### 类型 B：`"type": "loop"`（循环步骤）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `loop.mode` | string | ✅ | `"for_each"` 或 `"while"` |
| `loop.items` | string | 条件① | `for_each` 模式：表达式，求值结果为数组 |
| `loop.while_condition` | string | 条件① | `while` 模式：布尔表达式，求值结果为 `true`/`false` |
| `loop.loop_variable` | string | 条件② | `for_each` 模式：迭代变量名，循环体内用 `{{变量名}}` 引用当前元素 |
| `loop.steps` | Step[] | ✅ | 循环体（Step 数组，递归支持 skill/loop/branch） |
| `loop.max_iterations` | int | ❌ | 安全上限，默认 `10`；达到时按 `on_max_iteration` 处理 |
| `loop.on_max_iteration` | string | ❌ | `"break"`（中止循环）或 `"continue"`（记录警告并继续） |

> ① `for_each` 需要 `items` + `loop_variable`；`while` 需要 `while_condition`。
> ② 循环体内步骤可访问 `{{loop_variable}}`（for_each）及父步骤的 `variables`。

**示例 1：for_each 循环**

```json
{
  "index": 2,
  "type": "loop",
  "step_name": "批量代码审查",
  "loop": {
    "mode": "for_each",
    "items": "{{pr_file_list}}",
    "loop_variable": "file",
    "steps": [
      {
        "index": 2.1,
        "type": "skill",
        "step_name": "审查文件 {{file}}",
        "skill_name": "code-review",
        "action": "审查单个文件",
        "variables": {"input": "{{file}}", "output": "file_review"}
      }
    ],
    "max_iterations": 20,
    "on_max_iteration": "break"
  },
  "depends_on": [1],
  "failure_mode": {"on_exhaust": "ask", "is_milestone": false}
}
```

**示例 2：while 循环**

```json
{
  "index": 3,
  "type": "loop",
  "step_name": "重试直到成功",
  "loop": {
    "mode": "while",
    "while_condition": "{{retry_count}} < 3 && {{last_success}} == false",
    "steps": [
      {
        "index": 3.1,
        "type": "skill",
        "step_name": "尝试部署",
        "skill_name": "deploy",
        "action": "执行部署"
      }
    ],
    "max_iterations": 3,
    "on_max_iteration": "break"
  },
  "failure_mode": {"on_exhaust": "abort", "is_milestone": true}
}
```

---

### 类型 C：`"type": "branch"`（分支步骤）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `branch.condition` | string | ✅ | 布尔表达式，求值后为 `true` 或 `false` |
| `branch.if_steps` | Step[] | ✅ | 条件为 `true` 时执行的步骤数组 |
| `branch.else_steps` | Step[] | ❌ | 条件为 `false` 时执行的步骤数组（可选） |

> ① `if_steps` 和 `else_steps` 均为 Step 数组，递归支持 skill / loop / branch。
> ② 分支步骤本身不调用技能，仅做流程控制；`failure_mode` 作用于整个分支步骤（即 `if_steps` 全部失败时的行为）。

**示例：if-else 分支**

```json
{
  "index": 4,
  "type": "branch",
  "step_name": "按环境选择部署目标",
  "branch": {
    "condition": "{{env}} == 'production'",
    "if_steps": [
      {
        "index": 4.1,
        "type": "skill",
        "step_name": "生产环境部署",
        "skill_name": "deploy",
        "action": "部署到生产环境",
        "variables": {"input": "production"}
      }
    ],
    "else_steps": [
      {
        "index": 4.2,
        "type": "skill",
        "step_name": "预发环境部署",
        "skill_name": "deploy",
        "action": "部署到预发环境",
        "variables": {"input": "staging"}
      }
    ]
  },
  "depends_on": [1, 2, 3],
  "failure_mode": {"on_exhaust": "ask", "is_milestone": true}
}
```

---

## retry_policy（重试策略）

```json
{
  "max_retries": 3,              // 最大重试次数（默认从配置读取，默认 3）
  "error_types": ["file_locked", "network_error", "timeout", "auth_error"]
}
```

**错误类型说明：**

| 错误类型 | 重试间隔 | 说明 |
|---------|---------|------|
| `file_locked` | 0 秒 | 文件占用/锁定，立即重试 |
| `network_error` | 5 秒 | 网络不通/超时 |
| `timeout` | 5 秒 | 执行超时 |
| `auth_error` | - | 认证/权限错误，直接询问用户 |
| `other` | 2 秒 | 其他错误 |

---

## failure_mode（失败处理模式）

```json
{
  "on_exhaust": "ask",       // 重试耗尽后行为: "ask" | "skip" | "abort"
  "is_milestone": false      // 是否为里程碑步骤（可通过通用规则自动判断）
}
```

**on_exhaust 行为说明：**

| 值 | 说明 |
|-----|------|
| `ask` | 重试耗尽后询问用户 |
| `skip` | 跳过该步骤，继续后续步骤 |
| `abort` | 中止整条调用链 |

**里程碑行为：**
- **里程碑步骤失败** → 无论 `on_exhaust` 配置如何，**强制中止整条链**
- **里程碑步骤的 on_exhaust** → 建议设为 `abort`（validate 时会发出警告）
- **非里程碑步骤失败** → 按 `on_exhaust` 配置处理（ask/skip/abort）

---

## 条件表达式语法

`condition` / `branch.condition` / `loop.while_condition` 支持以下语法：

| 语法 | 示例 | 说明 |
|------|------|------|
| 步骤状态 | `step_1_success` | 步骤 1 成功（返回码 0） |
| 步骤状态（否定） | `step_2_failed` | 步骤 2 失败 |
| 变量存在 | `variable_OUTPUT_exists` | 变量 `OUTPUT` 已定义 |
| 变量相等 | `{{env}} == 'production'` | 字符串比较 |
| 变量数值 | `{{retry_count}} < 3` | 数值比较（`<` `>` `<=` `>=` `==` `!=`） |
| 逻辑运算 | `step_1_success && step_2_success` | `&&`（与）、`||`（或）、`!`（非） |
| 布尔常量 | `always` | 总是执行（默认） |
| 布尔常量 | `never` | 永不执行 |
