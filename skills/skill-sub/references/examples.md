# skill-sub 使用示例

> 本文档是 SKILL.md 的渐进式补充，提供完整使用示例。

---

## 示例 1：创建发布流水线调用链

```
用户：帮我创建一条发布流水线的调用链，包含安全审计、打包、推送

AI：
  1. 分析意图 → 需要 skills-security-check + 内置打包 + git-sync
  2. 读取技能信息 → 提取关键步骤
  3. 规划步骤：
     步骤1: 安全审计 → 依赖:无 → 里程碑(关键词:审计)
     步骤2: 打包 → 依赖:[1] → 非里程碑
     步骤3: 推送代码 → 依赖:[2] → 里程碑(最后一步)
  4. 展示确认
  5. [设置: naming_mode=auto] → AI 命名为 "发布流水线"
  6. 保存
```

**生成的调用链 JSON：**

```json
{
  "name": "发布流水线",
  "description": "技能发布完整流程",
  "purpose": "一键发布技能到 SkillHub/ClawHub",
  "user_intent": "帮我打包发布这个技能",
  "tags": ["发布", "技能管理"],
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
      "failure_mode": {"on_exhaust": "ask", "is_milestone": true}
    }
  ]
}
```

---

## 示例 2：执行调用链

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

---

## 示例 3：查看里程碑判断依据

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

## 示例 4：用 skill-sub 生成通用调用链模板

> 注意：skill-sub 本身**不参与**调用链，它只负责生成调用链模板。

**场景**：用户希望将"语义理解 → 规划 → 三步循环执行 → 标准化审查"这套流程固化为可复用的调用链。

```
用户：帮我创建一条"标准化执行流水线"调用链

AI：
  1. 分析意图 → 需要 semantic-split + triphasic-execution + skill-standardization
  2. 读取技能信息：
     - semantic-split：提取关键步骤（语义拆分、规划生成）
     - triphasic-execution：提取三步循环步骤
     - skill-standardization：提取审查/改写步骤
  3. 规划步骤（通用模板，不绑定具体任务）：
     步骤1: 语义理解 → 依赖:无 → 非里程碑
     步骤2: 规划步骤 → 依赖:[1] → 非里程碑
     步骤3: 三步循环执行 → 依赖:[2] → 里程碑
     步骤4: 标准化审查 → 依赖:[3] → 里程碑(关键词:审查)
  4. 展示确认
  5. 保存为通用模板 "标准化执行流水线"
```

**关键点**：生成的调用链是**通用模板**，适用于所有需要"语义理解→规划→执行→审查"的任务，不绑定某一次具体任务。

---

## 示例 5：意图自动匹配

```
用户：我想把几个技能串起来用

AI：
  [扫描调用链库，计算意图重合度]
  💡 检测到您可能想使用以下调用链：
    1. "发布流水线"（重合度 67%）— 包含安全审计、打包、推送
    2. "标准化执行流水线"（重合度 53%）— 包含语义拆分、执行、审查
  
  是否执行某条链？
```
