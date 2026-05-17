---
name: triphasic-execution
version: 5.3.0
author: WorkBuddy
license: MIT
agent_created: true
description: >
  Execute→Review→Advance 三步循环执行框架。所有任务按此节奏推进，
  防止无限死循环或单步骤卡住。附带结构化问题日志、风险手册和经验教训登记册。
  v5.3 更新：【人机交互调用】+ 【中断捕获】+ 【强制记录】
    - 新增人机交互调用方式（用户对话触发记录）
    - exec_wrapper.py 支持捕获 Ctrl+C/SIGTERM 中断事件
    - 问题记录从"AI自觉"改为"任务结束强制步骤"
  v5.2 更新：【完善监控边界说明】+ 【风险记录命令】
    - 新增 add-risk 命令，支持任务拆分阶段的风险记录
    - 明确说明监控能力边界（全局模式 vs 临时调用）
    - 说明问题、风险、经验的调用方式和定时任务命令
  v5.1 更新：【修复保存后服务器关闭问题】+ 【添加"完成设置"按钮】
    - 修复：保存配置后服务器保持运行，不再自动关闭
    - 新增：保存成功后显示"完成设置"按钮，手动关闭服务器
    - 修复：/done 端点正确创建 .settings_done 标志文件
  v5.0 更新：【HTML 设置界面】+ 【双模式设计】+ 【跨平台通用化】
    - 安装后首次运行自动弹出 HTML 设置界面（系统默认浏览器）
    - 支持配置：调用方式、记录文件路径、任务规划确认
    - 设置值同时写入 config.json 和 SKILL.md
    - 支持再次呼出设置界面（发送"打开 triphasic 设置"等）
    - 按需调用模式（默认）：用户主动加载技能 → 执行三步框架；不调用就不记录
    - 全局自动模式（可选）：配置 mode=global → daemon 后台监控，自动捕获异常并记录
  核心逻辑 = Python CLI，不依赖任何 Agent 平台。
  安装路径由调用方（Agent/平台）通过 --target 或 TRIPHASIC_SKILL_DIR 环境变量决定。
  触发关键词：三步执行、循环框架、执行审查推进、triphasic、问题记录、
  经验教训、problem logger、exec wrapper、exec guard、
  打开 triphasic 设置、修改 triphasic 配置、triphasic settings、打开设置界面。
tags: [framework, execution, debugging, problem-tracking, risk-tracking, lessons-learned, cross-platform, settings, configuration, config-ui]
category: workflow
---

# Triphasic Execution Framework v5.2

执行 → 审查 → 推进。每次交互只做一件事，三者缺一不可。

---

## ⚠️ 监控能力边界（重要说明）

### 全局模式 vs 临时调用

| 功能 | 全局模式（Global） | 临时调用（按需） |
|------|-------------------|-----------------|
| **问题记录** | ✅ 自动（Shell 命令失败/中断） | ✅ 任务结束后强制执行 |
| **风险记录** | ✅ 自动（Shell 命令异常） | ✅ 任务拆分时强制执行 |
| **经验积累** | ❌ 手动调用 merge-to-lessons | ❌ 手动调用 merge-to-lessons |

### 全局模式的实际覆盖率

> **✅ 全局模式可以监控**：通过 `exec_wrapper.py` 执行的 **Shell 命令**。

- ✅ **能自动记录**：
  - Shell 命令执行失败（退出码非零）
  - Shell 命令被中断（Ctrl+C / SIGTERM）
  - Shell 输出中匹配错误模式的文本

- ❌ **无法自动记录**：
  - Read/Write/Edit 等直接工具调用
  - ToolSearch/DeferExecuteTool 等 API 调用
  - AI 推理错误、幻觉
  - 逻辑错误（命令成功执行但结果错误）

**实际覆盖率**：约 **30-40%**（仅 Shell 命令部分）

### 临时调用的实际行为

> **⚠️ 重要**：临时调用模式下，记录是**任务结束后的强制步骤**，不是可选的。

- ✅ **任务结束后强制记录**：
  - 识别问题 → 必须调用 `add`
  - 识别风险 → 必须调用 `add-risk`
  - 任务完成 → 必须调用 `merge-to-lessons`

- ✅ **用户触发时必须执行**：
  - 用户说"记录问题" → 立即调用 `add`
  - 用户说"记录风险" → 立即调用 `add-risk`
  - 用户说"总结经验" → 立即调用 `merge-to-lessons`

---

## 问题、风险、经验调用方式

### 1. 问题记录（Problem Logging）

**触发时机**：任务执行过程中发现错误/异常时

```bash
# 标准调用
python {SKILL_DIR}/scripts/problem_logger.py add \
  --scene "API测试" \
  --symptom "HTTP 503" \
  --cause "服务端限流" \
  --solution "增加重试机制" \
  --task "用户头像接口"

# 最小调用（仅必填项）
python {SKILL_DIR}/scripts/problem_logger.py add \
  --scene "文件读取" \
  --symptom "FileNotFoundError"
```

### 2. 风险记录（Risk Logging）

**触发时机**：任务拆分（Phase 1）时识别到潜在风险

```bash
# 标准调用
python {SKILL_DIR}/scripts/problem_logger.py add-risk \
  --description "网络不稳定可能导致API调用失败" \
  --impact "用户体验下降，转化率降低" \
  --mitigation "增加重试机制和降级策略" \
  --task "用户头像接口"

# 最小调用（仅必填项）
python {SKILL_DIR}/scripts/problem_logger.py add-risk \
  --description "第三方服务可能宕机"
```

### 3. 经验积累（Lessons Learned）

**触发时机**：任务完成后或定期（如每天/每周）

```bash
# 合并问题清单和风险手册到经验教训登记册
python {SKILL_DIR}/scripts/problem_logger.py merge-to-lessons

# 查看统计
python {SKILL_DIR}/scripts/lessons_register.py stats
```

---

## 人机交互调用方式（与AI对话触发记录）

### 触发指令示例

用户可以通过以下方式触发AI执行记录：

```
用户：请审查上面执行的任务，记录问题和风险

用户：任务结束了，帮我总结问题和经验

用户：记录一下刚才的错误：API超时

用户：帮我把今天的经验整理一下

用户：记录一下风险：网络不稳定
```

### AI响应模板

当用户触发记录时，AI应执行以下流程：

```
### 📋 任务后记录

**问题记录**：
python {SKILL_DIR}/scripts/problem_logger.py add \
  --scene "任务执行" \
  --symptom "错误描述" \
  --cause "原因分析" \
  --solution "解决建议" \
  --task "任务名称"

**风险记录**：
python {SKILL_DIR}/scripts/problem_logger.py add-risk \
  --description "风险描述" \
  --impact "影响评估" \
  --mitigation "缓解措施" \
  --task "任务名称"

**经验积累**：
python {SKILL_DIR}/scripts/problem_logger.py merge-to-lessons
```

### 强制记录规则

> **⚠️ 重要**：每次任务执行完成后，AI必须执行以下记录步骤：
>
> 1. **任务结束时自动记录**（强制，非可选）：
>    - 回顾执行过程，识别问题 → 调用 `add`
>    - 回顾执行过程，识别风险 → 调用 `add-risk`
>    - 执行完成后 → 调用 `merge-to-lessons`
>
> 2. **用户触发时记录**（必须执行）：
>    - 用户说"记录问题" → 立即调用 `add`
>    - 用户说"记录风险" → 立即调用 `add-risk`
>    - 用户说"总结经验" → 立即调用 `merge-to-lessons`

---

## 定时任务集成

### WorkBuddy 定时任务命令

在 WorkBuddy 中创建定时任务时，使用以下命令：

#### 每日经验积累（推荐）

**任务类型**：Shell 命令
**命令**：
```bash
python {SKILL_DIR}/scripts/problem_logger.py merge-to-lessons
```

**定时设置**（根据需求选择）：
- 每天 22:00：`0 22 * * *`
- 每天早上 08:00：`0 8 * * *`

#### 定时检查未解决问题

```bash
python {SKILL_DIR}/scripts/cron_helper.py
```

---

## 设置界面（v5.1 更新）

安装技能后首次运行 `install.py` 时，会自动弹出 HTML 设置界面（系统默认浏览器），引导用户完成初始配置。

### 设置项说明

| 设置项 | 选项 | 说明 |
|---|---|---|
| **默认调用方式** | 调用模式（按需） / 全局模式 | 控制技能激活方式 |
| **记录文件路径** | TRIPHASIC_HOME、Problems、Risks、Lessons、Logs | 未自定义时使用默认值 |
| **任务规划确认** | 询问确认后再执行 / 直接按照规划执行 | 控制 Agent 执行前是否请求确认 |

### 当前配置

> **调用方式**：🟢 按需调用模式（默认）
> **数据目录**：`~/.workbuddy/triphasic/`
> **任务规划确认**：询问确认后再执行

（上方配置会根据实际设置值自动更新）

### 再次呼出设置界面

**方式 1：通过 Agent 对话（推荐）**
- 向 Agent 发送："打开 triphasic 设置"、"修改配置"、"打开设置界面"
- Agent 执行步骤：
  1. 运行 `python {SKILL_DIR}/scripts/settings.py --serve-only`，解析输出中的 `SERVER_STARTED:<port>`
  2. 调用 `webbrowser.open(f"http://localhost:{port}/")` 打开浏览器
  3. 轮询检查 `{SKILL_DIR}/.settings_done` 标志文件是否存在
  4. 检测到标志文件后，调用 `python -c "from settings import shutdown_server; shutdown_server()"` 关闭服务器

**方式 2：手动运行脚本（终端）**
```bash
python {SKILL_DIR}/scripts/settings.py
```
（脚本会自动启动服务器、打开浏览器、阻塞等待设置完成）

### 对话式设置（回退方案）

当 HTML 设置界面无法打开时（例如浏览器不可用、系统无图形界面等），Agent 应通过对话方式收集配置。

**触发条件：**
- Agent 调用 `webbrowser.open()` 失败（`--serve-only` 模式下）
- 用户明确说"使用对话方式设置"、"不用 HTML"

**对话流程（Agent 必须严格遵循）：**

```
步骤 1：确认默认调用方式
请确定默认调用方式（输入 1/2 选择）：
1. 按需调用模式（默认）— 用户主动加载技能时才启用
2. 全局自动模式 — 后台 daemon 监控，自动捕获异常
请输入（1 或 2）：

步骤 2：确认数据目录路径
当前数据目录为：~/.workbuddy/triphasic/
- 确认请直接输入 y
- 更改请输入具体路径（例如：D:\my_data\triphasic）
请输入：

步骤 3：确认任务规划
任务规划是否需要确认（输入 1/2 选择）：
1. 确认 — 执行前询问用户
2. 无需确认 — 直接按照规划执行
请输入（1 或 2）：

步骤 4：总结配置
已收集配置：
- 调用方式：[用户选择]
- 数据目录：[用户路径]
- 任务确认：[true/false]
确认保存？（y/n）

步骤 5：保存配置
Agent 执行：
  python {SKILL_DIR}/scripts/settings.py --save-config '{json}'
```

**Agent 执行指令（对话式设置）：**

1. 先尝试 `--serve-only` 方式打开 HTML 设置界面
2. 如果浏览器不可用，按上述对话流程逐步询问用户
3. 收集完配置后，构造 JSON，调用：
   ```bash
   python {SKILL_DIR}/scripts/settings.py --save-config '{json_string}'
   ```
4. 检查退出码：0 表示成功，向用户确认"✅ 设置已保存"

**对话式设置完成后的操作：**
1. 将用户选择写入 `TRIPHASIC_HOME/config.json`
2. 调用 `update_skill_md()` 更新 `SKILL.md`
3. 向用户确认"设置已保存"

---

## 双模式设计（v4.1 核心更新）

### 核心理念：用户习惯决定启动方式
> **当前配置：🟢 按需调用模式（默认）**

| 维度 | 按需调用模式（默认） | 全局自动模式（可选） |
|---|---|---|
| **触发条件** | 用户主动加载技能 | 配置 `mode: global` + 启动 daemon |
| **记录行为** | 调用时才记录三步框架 | 所有任务自动应用三步框架 |
| **后台守护** | 不启动 daemon | `problem_daemon.py` 持续监控 |
| **异常捕获** | 靠 Agent 主动调用 CLI 命令记录 | 自动捕获 + 写入 PROBLEMS.md |
| **适用场景** | 日常简单任务、跨平台协作 | 复杂多步骤项目、长期维护 |

### 按需调用模式（默认，符合"不调用就不记录"习惯）

用户主动加载技能后，Agent 遵循三步框架，通过 CLI 命令手动记录问题。

### 全局自动模式（可选，适合长期项目）

```bash
# 安装时选择 global 模式
python install.py --mode global

# 启动守护进程（仅一次）
python problem_daemon.py start

# 此后所有命令异常 → 自动捕获 → 自动写入 PROBLEMS.md
```

注意：daemon 不自启，必须手动 `problem_daemon.py start`。

---

## 跨平台通用化设计（v4.1 核心更新）

核心逻辑 = Python CLI，不依赖任何 Agent 平台。安装路径由调用方决定。

```bash
# 安装路径由调用方通过 --target 或 TRIPHASIC_SKILL_DIR 指定
python install.py --target /path/to/skills

# 数据目录由调用方通过 --home 或 TRIPHASIC_HOME 指定
python problem_logger.py --home /path/to/data init
```

| 平台 | 集成方式 | 是否必须 |
|---|---|---|
| **WorkBuddy** | `execute_command` 调用 CLI | 可选（纯 CLI 也可用） |
| **Cursor** | Terminal 运行 CLI | 可选 |
| **VS Code** | 任务运行器调用 CLI | 可选 |
| **纯手动** | 直接运行 Python 脚本 | 原生支持 |

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

# 记录问题（任务执行中发现错误时）
python {SKILL_DIR}/scripts/problem_logger.py add \
  --scene "API测试" --symptom "HTTP 503" \
  --cause "服务端限流" --solution "增加重试机制"

# 记录风险（任务拆分时识别到潜在风险）
python {SKILL_DIR}/scripts/problem_logger.py add-risk \
  --description "网络不稳定可能导致API调用失败" \
  --impact "用户体验下降" \
  --mitigation "增加重试机制"

# 搜索历史问题（执行前检索，避免重复踩坑）
python {SKILL_DIR}/scripts/problem_logger.py search "503"

# 列出最近问题
python {SKILL_DIR}/scripts/problem_logger.py list --recent 10

# 更新问题（补充原因/解决路径）
python {SKILL_DIR}/scripts/problem_logger.py update --id P001 --cause "xxx" --solution "yyy"

# 生成经验教训登记册（任务完成后或定时调用）
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
| `TRIPHASIC_HOME/.problem_logs/problems.jsonl` | JSONL 问题日志（机器可读，防丢失） |
| `TRIPHASIC_HOME/.problem_logs/risks.jsonl` | JSONL 风险日志（机器可读，防丢失） |
| `TRIPHASIC_HOME/PROBLEMS.md` | 问题清单（人类可读） |
| `TRIPHASIC_HOME/RISKS.md` | 风险手册 |
| `TRIPHASIC_HOME/LESSONS_REGISTER.md` | 经验教训登记册 |
| `TRIPHASIC_HOME/.exec_output_pipe.txt` | exec 输出管道文件 |
| `TRIPHASIC_HOME/config.json` | 用户配置 |

**当前配置**：`~/.workbuddy/triphasic/`（可通过设置界面修改）

所有脚本支持 `--home` 参数覆盖，优先级：`--home` > `TRIPHASIC_HOME` > 默认值

---

## 安装（v4.1：路径由调用方决定）

```bash
# 基础安装（按需调用模式，默认）
python install.py

# 全局自动模式
python install.py --mode global

# 指定安装路径（由 Agent/平台决定）
python install.py --target ~/.workbuddy/skills/
python install.py --target ~/.openclaw/workspace/skills/

# 指定数据目录
python install.py --home ~/.myagent/triphasic/

# 卸载
python install.py --uninstall
```

---

## 配置

首次 `init` 后，编辑 `TRIPHASIC_HOME/config.json` 自定义：

```json
{
  "enabled": true,
  "mode": "on_demand",
  "poll_interval_ms": 100,
  "error_patterns": ["error|Error|ERROR", "exception|Exception", "failed|Failed"],
  "auto_resolve_timeout_hours": 24,
  "daemon": {
    "enabled": false,
    "start_on_boot": false
  },
  "hooks": {
    "pre_exec_search": true,
    "auto_record_exception": true,
    "require_task_confirmation": true
  }
}
```

> **当前配置（由设置界面写入，自动更新）：**
> 实际配置值存储在 `TRIPHASIC_HOME/config.json`，可通过运行 `python {SKILL_DIR}/scripts/settings.py` 查看和修改。

- `mode`: `"on_demand"`（默认，按需调用）| `"global"`（全局自动）
- `daemon.enabled`: 仅 `mode=global` 时应设为 `true`
- `daemon.start_on_boot`: 始终 `false`，daemon 必须手动启动

---

## 定时任务集成

### WorkBuddy 定时任务命令

#### 每日经验积累（推荐）

**任务类型**：Shell 命令
**命令**：
```bash
python {SKILL_DIR}/scripts/problem_logger.py merge-to-lessons
```

**定时设置**（根据需求选择）：
- 每天 22:00：`0 22 * * *`
- 每天早上 08:00：`0 8 * * *`

#### 定时检查未解决问题

```bash
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
| `install.py` | 安装/卸载（支持 --mode --target --home） | 无 |
| `settings.py` | HTML 设置界面（v5.0 新增） | 无 |
| `problem_logger.py` | 问题/风险 CRUD + 合并登记册（add/add-risk/list/search/update/merge-to-lessons） | 无 |
| `exec_wrapper.py` | 命令执行拦截器 | 无 |
| `problem_daemon.py` | 后台监控守护进程（仅全局模式） | 无 |
| `lessons_register.py` | 登记册管理（generate/diff/stats） | 无 |
| `cron_helper.py` | 定时任务钩子 | 无 |

所有脚本零外部依赖，仅使用 Python 标准库。跨平台支持 Windows/Linux/macOS。
