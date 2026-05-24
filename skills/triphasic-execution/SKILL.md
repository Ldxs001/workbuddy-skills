---
name: triphasic-execution
version: 5.13.0
author: wUwproject
license: MIT
description: >
  Execute→Review→Advance 三步循环执行框架。所有任务按此节奏推进，
  防止无限死循环或单步骤卡住。附带结构化问题日志、风险手册和经验教训登记册。
tags: [framework, execution, debugging, problem-tracking, risk-tracking, lessons-learned, cross-platform, settings, configuration, config-ui]
category: workflow
---

# Triphasic Execution Framework v5.13.0

执行 → 审查 → 推进。每次交互只做一件事，三者缺一不可。

---

## 触发条件

当用户出现以下意图时，加载本技能：

- 说出"三步执行"、"执行审查推进"、"triphasic"
- 说出"问题记录"、"经验教训"、"problem logger"
- 说出"打开 triphasic 设置"、"triphasic settings"
- 需要结构化执行框架防止死循环或跳步
- 复杂多步骤任务，需要强制进度追踪和中断恢复

---

## 核心能力

| # | 能力 | 说明 |
|---|------|------|
| 1 | **语义拆分前置（F-01）** | 任务开始前强制输出语义拆分，明确主语/目的/诉求/动机 |
| 2 | **任务规划强制（F-02）** | 所有任务必须先输出规划，无论大小 |
| 3 | **三步循环执行** | Execute→Review→Advance，每步必须完整，不可跳过 |
| 4 | **进度文件持久化（F-03/F-07/F-09）** | init→update→complete，中断后可 resume 恢复；**complete 强制校验（v5.12）** |
| 5 | **问题/风险/经验记录** | 任务完成后强制记录（复杂任务 Python 侧校验），积累 PROBLEMS.md / RISKS.md / LESSONS_REGISTER.md |
| 6 | **最多 3 次重试（F-08）** | 同一步骤失败 3 次必须换方案，禁止第 4 次重试 |
| 7 | **双模式支持** | 按需调用模式（默认）/ 全局自动模式 |
| 8 | **HTML 设置界面** | `settings.py` 可视化配置技能参数 |
| 9 | **complete 强制校验（v5.12）** | `complete` 时 Python 侧校验步骤完成率、记录文件、总结文件；`--force` 只跳过步骤检查，`--no-enforce` 关闭记录校验 |

---

## 快速开始

```bash
# 按需调用（默认）— 任务开头说出关键词即可
"使用 triphasic-execution 执行以下任务：..."

# 全局自动模式 — 所有任务自动套用框架
编辑 assets/default_config.json → "mode": "auto"

# 可视化配置
python {SKILL_DIR}/scripts/settings.py
```

---

## ⚡ [LOADING PROTOCOL]

skill 加载后，AI 输出以下状态标识：

```
[triphasic] skill loaded — 执行顺序：语义拆分 → 任务规划 → 执行/审查/推进
```

| 观察结果 | 结论 |
|---------|------|
| 状态输出在任务相关内容之前出现 | ✅ 执行顺序正确 |
| 状态输出在任务执行后才出现 | ❌ 执行顺序错误 |
| 无状态输出 | ❌ skill 未加载 |

---

## 🚨 [MANDATORY] 强制约束总表

> **本节是整个技能的执行宪法。违反任意一条 = 违规，必须立即停止并补救。**

| 序号 | 约束内容 | 触发时机 | Python 强制 |
|------|---------|---------|------------|
| **F-01** | 收到任务后首先执行语义拆分，禁止直接进入规划 | 收到任务第一个响应 | ❌ AI 自觉 |
| **F-02** | 语义拆分完成后必须输出【任务规划】，禁止直接执行 | 语义拆分输出后 | ❌ AI 自觉（需用户确认规划）|
| **F-03** | 任务规划输出后立即调用 `task_progress.py init` | 规划确认后 | ✅ 文件不存在则后续 update/complete 报错 |
| **F-04** | 每步 EXECUTE 开始前重述本步骤任务目的 | 每步执行前 | ❌ AI 自觉 |
| **F-05** | 每步执行后必须紧跟 REVIEW，禁止连续执行两步 | 每步执行后 | ❌ AI 自觉 |
| **F-06** | 每步 REVIEW 后必须紧跟 ADVANCE | 每步 REVIEW 后 | ❌ AI 自觉 |
| **F-07** | 每步 ADVANCE 后调用 `task_progress.py update` | 每步 ADVANCE 后 | ✅ update 校验 init 存在性 |
| **F-08** | 同一步骤失败 3 次后必须换方案，禁止第 4 次重试 | 重试计数达到 3 | ⚠️ 部分（update 记录重试次数）|
| **F-09** | 任务完成后调用 `task_progress.py complete` | 任务完成时 | ✅ **v5.12 强制**：校验步骤完成率、记录文件、summary.json |
| **F-10** | 任务完成后必须输出【任务完成】总结 | 任务结束时 | ⚠️ 部分（summary.json 自动生成）|

### 自检指令

```
[自检] 当前阶段：[阶段名称]
- F-01 语义拆分：[已完成/待执行]
- F-02 任务规划：[已完成/待执行]
- F-03 进度文件创建：[已完成/待执行]
- 当前步骤 N：[待执行/执行中/已完成]
违规项：[无/F-XX 描述]
```

---

## 工作流程

```
用户任务
  ↓ [F-01 MANDATORY]
语义拆分 → 输出块分析（主语/目的/诉求/动机）
  ↓ [F-02 MANDATORY]
任务规划 → 明确目的/要求/工具/结果/风险 → 确认执行
  ↓ [F-03 MANDATORY]
task_progress.py init → 创建进度文件
  ↓
执行循环（每步骤）：
  🔧 EXECUTE（重述目的 → 执行）
    ↓ [F-05]
  🔍 REVIEW（✅/❌/⚠️ + 证据）
    ↓ [F-06]
  📍 ADVANCE（继续/换方案/完成）
    ↓ [F-07]
  task_progress.py update
  ↓
任务完成
  ↓ [F-09] task_progress.py complete
  ↓ [F-10] 输出【任务完成】总结
  ↓ [MANDATORY] 问题/风险/经验记录
```

→ 详细规则、模板、禁止行为清单见 `references/mandatory.md`
→ 完整示例见 `references/examples.md`
→ CLI 命令、进度文件、数据目录、安装见 `references/reference.md`

---

## 循环规则（摘要）

1. **语义拆分先行** — 收到任务的第一个动作
2. **规划先行** — 所有任务必须先输出任务规划
3. **临时文件持久化** — init → update（每步）→ complete
4. **最小单元** — 单次工具调用，每步立即审查+推进
5. **最多 3 次重试** — 3 次失败后必须换方案
6. **大任务才拆分** — 3步以上输出步骤列表
7. **中断可恢复** — 进度文件保留，重启后 resume

---

## 快速命令

```bash
# 进度文件
python {SKILL_DIR}/scripts/task_progress.py init --task "名称" --purpose "目的" --requirements "要求" --risks "风险" --steps '[...]'
python {SKILL_DIR}/scripts/task_progress.py update --task "名称" --step 1 --status success --review "..." --advance "..."
python {SKILL_DIR}/scripts/task_progress.py complete --task "名称"  # --force 跳过步骤检查；--no-enforce 关闭记录校验
python {SKILL_DIR}/scripts/task_progress.py resume --task "名称"

# 问题/风险/经验
python {SKILL_DIR}/scripts/problem_logger.py add --scene "场景" --symptom "症状" --cause "原因" --solution "方案" --task "任务"
python {SKILL_DIR}/scripts/problem_logger.py add-risk --description "风险" --impact "影响" --mitigation "缓解" --task "任务"
python {SKILL_DIR}/scripts/problem_logger.py merge-to-lessons

# 设置界面
python {SKILL_DIR}/scripts/settings.py
```

---

## 渐进式 MD 文件体系

| 本文件（SKILL.md）包含 | 拆分到 references/ |
|---|---|
| ✅ 触发条件、核心能力、强制约束总表 | 📄 `mandatory.md` — Phase 0~4 详细规则、模板、禁止行为 |
| ✅ 工作流程概述、循环规则 | 📄 `examples.md` — 完整执行示例 |
| ✅ 快速命令 | 📄 `reference.md` — 进度文件机制、问题记录、安装、数据目录 |

---

## 版本

当前版本：**5.13.0** — v5.13.0：补充权限权重说明（R-16），references/reference.md 追加权限权重表格及风险等级评估
