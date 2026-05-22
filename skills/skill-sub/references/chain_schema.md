# skill-sub 调用链数据结构

> 本文档定义 Chain / Step / retry_policy / failure_mode 的完整结构。

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

```json
{
  "index": 1,                         // 步骤序号（从1开始）
  "skill_name": "skill-name",          // 调用的技能名称
  "step_name": "步骤名称",            // 步骤名称（展示用）
  "action": "精炼的关键动作描述",     // 用于第一层执行（上下文占用最低）
  "skill_instruction": "指令名称",    // 对应 SKILL.md 中的指令名（用于第二层回退）
  "detail": "详细执行说明（可选）",  // 用于第三层回退
  "depends_on": [1],                // 依赖的步骤索引（可选，默认依赖前一步）
  "condition": "表达式（可选）",      // 条件执行
  "variables": {                     // 步骤级变量（输入/输出映射）
    "input": "{{step1.output}}",
    "output": "result"
  },
  "retry_policy": { ... },           // 见下文
  "failure_mode": { ... },           // 见下文
  "notes": "备注（可选）"
}
```

---

## retry_policy（重试策略）

```json
{
  "max_retries": 3,              // 最大重试次数（默认从设置读取，默认3）
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
- **里程碑步骤失败** → 无论 `on_exhaust` 设置如何，**强制中止整条链**
- **里程碑步骤的 on_exhaust** → 建议设为 `abort`（validate 时会发出警告）
- **非里程碑步骤失败** → 按 `on_exhaust` 设置处理（ask/skip/abort）
