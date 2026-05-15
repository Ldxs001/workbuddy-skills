---
name: triphasic-execution
version: 3.0.0
author: WorkBuddy
license: MIT
agent_created: true
description: >
  Execute→Review→Advance 三步循环执行框架。所有任务按此节奏推进，
  防止无限死循环或单步骤卡住。附带结构化问题日志系统和经验教训登记册。
  支持两种调用方式：1) 直接调用（Agent 读取本技能后遵循三步框架）；
  2) 注册为 exec 全局管理（exec_wrapper 拦截所有命令，daemon 后台监控）。
  触发关键词：三步执行、循环框架、执行审查推进、triphasic、问题记录、
  经验教训、problem logger、exec wrapper、exec guard。
tags: [framework, execution, debugging, problem-tracking, lessons-learned]
category: workflow
---

# Triphasic Execution Framework v3.0

执行 → 审查 → 推进。每次交互只做一件事，三者缺一不可。

---

## 核心规则

### Phase 1 — 执行 (EXECUTE)
- 实际运行命令、调用工具、测试代码
- 只跑一个主要命令（可并行多个独立命令）
- 不提前分析结果，不跳到审查阶段

### Phase 2 — 审查 (REVIEW)
- 分析执行结果，给出明确判断：✅成功 / ❌失败 / ⚠️部分
- 列出具体证据（数据、错误码、状态）
- 不执行新操作

### Phase 3 — 推进 (ADVANCE)
- 基于审查结论决定下一步
- 明确：继续 / 换方向 / 结束 / 向上返回
- 不直接执行，只规划

## 循环规则

1. **最小单元** = 单次工具调用，每步必须立即审查+推进
2. **最多 3 次重试** — 3 次失败后必须换方案或向上回溯
3. **大任务先拆分** — 输出步骤列表，大循环=步骤间推进，小循环=步骤内迭代
4. **完成后必须输出总结** — 目标/结果/关键发现/异常记录，不可静默消失

## 禁止行为

- ❌ 连续执行不审查
- ❌ 只审查不推进
- ❌ 同一操作重复 3 次以上无策略调整
- ❌ 任务完成后不输出总结
- ❌ 遇到问题硬跑不换思路

---

## 两种调用方式

### 方式 1：直接调用（Skill 模式，推荐）

Agent 加载本技能后，遵循三步框架。问题由 Agent 通过 `problem_logger.py` 自主记录。

```bash
# 初始化数据目录（首次使用）
python {SKILL_DIR}/scripts/problem_logger.py init

# Agent 记录问题
python {SKILL_DIR}/scripts/problem_logger.py add \
  --scene "API测试" --symptom "HTTP 503" \
  --cause "服务端限流" --solution "增加重试机制"

# 搜索历史问题（执行前检索，避免重复踩坑）
python {SKILL_DIR}/scripts/problem_logger.py search "503"

# 列出最近问题
python {SKILL_DIR}/scripts/problem_logger.py list --recent 10

# 更新问题（补充原因/解决路径）
python {SKILL_DIR}/scripts/problem_logger.py update --id P001 --cause "xxx" --solution "yyy"

# 生成经验教训登记册
python {SKILL_DIR}/scripts/problem_logger.py merge-to-lessons
```

### 方式 2：注册为 exec 全局管理（Wrapper 模式）

自动拦截所有 shell 命令，后台 daemon 实时监控异常。

```bash
# 启动后台监控守护进程
python {SKILL_DIR}/scripts/problem_daemon.py start

# 查看守护进程状态
python {SKILL_DIR}/scripts/problem_daemon.py status

# 停止守护进程
python {SKILL_DIR}/scripts/problem_daemon.py stop

# 使用 exec_wrapper 拦截命令
python {SKILL_DIR}/scripts/exec_wrapper.py "your command here"
```

**全局注册（可选）：**

```bash
# Linux/Mac (.bashrc / .zshrc):
export TRIPHASIC_HOME=~/.workbuddy/triphasic
alias exec="python3 {SKILL_DIR}/scripts/exec_wrapper.py"

# Windows (PowerShell Profile):
$env:TRIPHASIC_HOME = "$env:USERPROFILE\.workbuddy\triphasic"
function exec { python "{SKILL_DIR}\scripts\exec_wrapper.py" @args }
```

---

## 数据目录

所有数据存储在 `TRIPHASIC_HOME` 环境变量指定的目录：

| 路径 | 说明 |
|------|------|
| `TRIPHASIC_HOME/.problem_logs/problems.jsonl` | JSONL 问题日志（机器可读，防丢失） |
| `TRIPHASIC_HOME/.problem_logs/daemon.log` | 守护进程运行日志 |
| `TRIPHASIC_HOME/PROBLEMS.md` | 问题清单（人类可读） |
| `TRIPHASIC_HOME/RISKS.md` | 风险手册 |
| `TRIPHASIC_HOME/LESSONS_REGISTER.md` | 经验教训登记册 |
| `TRIPHASIC_HOME/.exec_output_pipe.txt` | exec 输出管道文件 |
| `TRIPHASIC_HOME/config.json` | 用户配置 |

**默认值**：`~/.workbuddy/triphasic/`

所有脚本支持 `--home` 参数覆盖，优先级：`--home` > `TRIPHASIC_HOME` > 默认值

---

## 配置

首次 `init` 后，编辑 `TRIPHASIC_HOME/config.json` 自定义：

```json
{
  "enabled": true,
  "poll_interval_ms": 100,
  "error_patterns": ["error|Error|ERROR", "exception|Exception", "failed|Failed"],
  "auto_resolve_timeout_hours": 24
}
```

---

## 定时任务集成

```bash
# 每天定时检查未解决问题 + 生成登记册
python {SKILL_DIR}/scripts/cron_helper.py

# 仅查看统计
python {SKILL_DIR}/scripts/lessons_register.py stats
```

---

## 完整示例

```
用户：请验证 xx 信源是否可用

【步骤拆分】
步骤 1: 分析信源
步骤 2: 测试信源（最多 3 次重试）
步骤 3: 输出结论

### 🔧 [EXECUTE] - 步骤 2 (重试 1)
web_fetch xx 信源 → 返回 503

### 🔍 [REVIEW] - 步骤 2 (重试 1)
❌失败 — HTTP 503，可能为偶发波动

### 📍 [ADVANCE] - 步骤 2 (重试 1)
推进：重试 2

...（最多 3 次）

【任务完成总结】
- 目标：验证 xx 信源
- 结果：❌失败 — 连续 3 次 HTTP 503
- 异常记录：已记录到 PROBLEMS.md
```

---

## 脚本清单

| 脚本 | 功能 | 依赖 |
|------|------|------|
| `problem_logger.py` | 问题 CRUD + 合并登记册 | 无 |
| `exec_wrapper.py` | 命令执行拦截器 | 无 |
| `problem_daemon.py` | 后台监控守护进程 | 无 |
| `lessons_register.py` | 登记册管理（generate/diff/stats） | 无 |
| `cron_helper.py` | 定时任务钩子 | 无 |

所有脚本零外部依赖，仅使用 Python 标准库。跨平台支持 Windows/Linux/macOS。
