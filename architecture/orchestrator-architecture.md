<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# Orchestrator 架构文档 — v2.0.0

> 链驱动智能体系统 — Pipeline 为主体，LLM 为执行器。
> 作者：wUwproject | 许可证：Apache 2.0
> 更新：2026-07-10

---

## 一、系统概览

Orchestrator 是一个**链驱动智能体系统**，核心理念是放弃 ReAct 循环（"LLM 当大脑"），改为**链为主体、LLM 为执行器**的确定性架构：

```
用户编排 Pipeline → 选择链 + 下达任务
  → Round 1：需求分析（LLM 分析任务与链的关系）
    → Round 2：（可选）skill-sub 优化（算法黏连检查 + 里程碑）
      → Round 3+：逐步执行
        → 步骤 1：llm.chat(技能描述 + 参数 + 前一步输出)
        → 步骤 2：llm.chat(...)
        → ... 直到链结束
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **链是主体** | 没有链就没有对话。Pipeline 编辑器是主界面，对话是执行结果展示 |
| **LLM 是执行器** | LLM 不做路径决策（由编排器决定），只负责执行每个步骤 |
| **三种真执行** | seq = llm.chat 单次调用，par = ThreadPoolExecutor 真并行，loop = for 真循环 |
| **技能即积木** | 不改动任何现有技能，通过编排组合达成复杂任务 |
| **配置可调** | 超时和 max_tokens 从配置读取，非硬编码 |

### 1.2 与 v1.x 的关键差异

| 维度 | v1.x（ReAct 架构） | v2.0（链驱动） |
|------|-------------------|---------------|
| **界面** | tkinter GUI（gui_agent.py） | **Web UI**（web_ui.py）三 Tab |
| **执行模式** | ReAct 循环（agent.run → 思考→工具→观察） | **链驱动**（预编排 → 逐步骤 llm.chat） |
| **Pipeline 编辑器** | Treeview 控件 | **可视化拖拽画布** |
| **并行** | threading.Thread join | **ThreadPoolExecutor** 真并行 |
| **循环** | 顺序遍历 children | **for 循环** 真重复 |
| **参数传递** | 隐式对话历史 | **显式 params/extra** 字段 |
| **skill-sub** | 仅算法优化（去重/拓扑） | **算法+LLM**：读 SKILL.md → 黏连检查 → 里程碑 |
| **对话** | ReAct 自由对话 | **链驱动**：选链 → 分析 → 优化 → 执行 |
| **批处理** | 无 | **--batch/--jsonl** 模式 |
| **接口文档** | 无 | **PROTOCOL.md** 完整 API 契约 |
| **数据格式** | 仅 Pipeline JSON | **rich tree**：含 params/extra/skill-sub 数据 |

---

## 二、双入口架构

Orchestrator 有两种运行方式：

```
Orchestrator/
├── main.py                    # CLI 入口（Web UI/批处理/管道/交互）
└── orchestrator/               # Python 包
    ├── web_ui.py               # Web UI 服务器 + 前端内嵌 HTML
    ├── agent_loop.py           # ReAct 循环（仅无链时回退）
    ├── chain_engine.py         # 执行引擎 + 固化功能
    ├── chain_model.py          # 数据模型
    ├── llm_client.py           # LLM 通信
    ├── memory.py               # 记忆系统
    ├── skill_scanner.py        # SKILL.md 扫描器
    ├── agent_config.py         # 配置管理
    ├── static/web_ui.js        # 前端 JS
    └── tools/                  # 工具模块
```

### 2.1 Web UI 模式（主）

```
python main.py --web
```

启动 HTTP 服务器，提供三 Tab：

| Tab | 功能 | 对应文件 |
|-----|------|---------|
| **对话** | 链驱动执行：选链 → 下达任务 → 多轮次展示 | `web_ui.py` / `web_ui.js` |
| **配置** | LLM 后端 / 搜索 / 提示词 / 技能路径 | `web_ui.py` |
| **Pipeline** | 可视化 seq/par/loop 编排器 | `web_ui.py` / `web_ui.js` |

### 2.2 批处理 / 管道模式

```
python main.py --batch input.json output.json   # JSON 批处理
cat queries.jsonl | python main.py --jsonl > out.jsonl  # JSONL 管道
```

无需 LLM 连接，纯 Pipeline 解析 + 步骤输出。

---

## 三、Web UI 架构

### 3.1 HTTP 服务器

基于 Python 标准库 `http.server.BaseHTTPRequestHandler`，零外部依赖。

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | Web UI 主页面（HTML 内联） |
| `/api/chat` | POST | 链驱动对话 / ReAct 回退 |
| `/api/config` | GET/POST | 配置读写 |
| `/api/skills` | GET | 技能列表 |
| `/api/pipelines` | GET/POST | Pipeline 列表 / 保存 |
| `/api/pipelines/run` | POST | 执行 Pipeline |
| `/api/pipelines/delete` | POST | 删除 Pipeline |

### 3.2 对话三阶段（链驱动）

```
Round 1 — 需求分析
  LLM 分析任务 + 技能链 → 返回分析结果
  ↓
Round 2 — skill-sub 优化（可选，勾选开启）
  读 SKILL.md → 算法黏连检查 → LLM 模糊回退 → 里程碑标记
  ↓
Round 3+ — 逐步执行
  步骤 1 → llm.chat(技能描述 + 参数) → 输出
  步骤 2 → llm.chat(上一步输出 + 参数) → 输出
  ...
```

### 3.3 Pipeline 编辑器

三栏布局：

```
┌──────┬──────────────────────┬──────┐
│ 左栏 │      中栏            │ 右栏 │
│ 技能 ├──────────────────────┤ 已保 │
│ 列表 │  编排画布            │ 存   │
│      │  [seq] 技能A  [x]    │ Pipe │
│      │  [par] 并行组        │ line │
│      │    [seq] 技能B       │ 列表 │
│      │    [seq] 技能C       │      │
│      │  [loop] 循环×3       │      │
│      │    [seq] 技能D       │      │
└──────┴──────────────────────┴──────┘
```

| 操作 | 说明 |
|------|------|
| **双击左侧技能** | 添加到画布（seq 模式） |
| **点 +并行组** | 创建 par 容器 |
| **点 +循环组** | 创建 loop 容器 |
| **双击节点** | 编辑参数（key=value） |
| **右键模式切换** | seq/par/loop 切换 |
| **保存** | 模态框输入名称 → JSON 保存 |
| **运行** | 发送到后端执行引擎 |

---

## 四、执行引擎

### 4.1 链执行（_execute_tree）

核心执行函数，支持三种模式：

```
_execute_tree(nodes, output, depth, step_counter, prev_output):
  for node in nodes:
    if mode == "seq":
      result = _execute_single_skill(name, params, prev_output)
      prev_output = result  # 传递下一步
    elif mode == "par":
      ThreadPoolExecutor:
        for child in children:
          executor.submit(_execute_single_skill, ...)
      # 等所有完成
    elif mode == "loop":
      for t in range(times):
        _execute_tree(children, ...)
```

### 4.2 单技能执行（_execute_single_skill）

不再走 `agent.run()`（ReAct 循环），直接 `llm.chat()`：

```python
prompt = (
    f"执行步骤「{display}」。\n\n"
    f"技能说明:\n{skill_desc}"
    f"{'参数:\n' + param_str if param_str else ''}"
    f"{context}\n\n"
    f"输出该步骤的执行结果。不要解释。"
)
response = llm.chat([{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=exec_max_tokens)
```

### 4.3 skill-sub 优化

算法主导的链分析（非 LLM 自由发挥）：

```
1. 读 SKILL.md → 提取 tags/triggers/description
2. 算法规则比较步骤间兼容性：
   - 分析类→生成类 → 不兼容，插入转换步骤
   - 数据类→图表类 → 兼容，直接传递
3. LLM 模糊回退（仅当算法无法确定时）
4. 里程碑自动标记（含"完成/结果/报告"等关键词）
```

---

## 五、数据模型

### 5.1 PipelineNode（chain_model.py）

```python
@dataclass
class PipelineNode:
    id: str               # UUID hex[:8]
    skill_name: str       # 技能 slug
    display_name: str     # 显示名称
    mode: str             # seq | par | loop
    children: list        # 子节点
    loop_times: int       # 循环次数
    input_text: str       # 用户输入
    params: dict          # 技能参数（v2.0 新增）
    extra: dict           # skill-sub 优化数据（v2.0 新增）
```

### 5.2 前端节点（web_ui.js）

```javascript
{
  name: "skill-name",
  display: "显示名称",
  mode: "seq|par|loop",
  children: [],
  loop_times: 3,
  params: {}            // 用户编辑的参数
}
```

### 5.3 保存格式（chains/{name}.json）

```json
{
  "name": "my-pipeline",
  "nodes": [...],       // 扁平化节点
  "tree": [...]         // 完整树结构（含 params/extra）
}
```

`tree` 保留全部字段（含 skill-sub 注入的黏连点/里程碑），`nodes` 为扁平化执行格式。

---

## 六、LLM 客户端

### 6.1 架构

基于纯 `urllib` 的 OpenAI 兼容客户端，支持多后端：

| 后端 | 地址 |
|------|------|
| LM Studio | `http://localhost:1234/v1` |
| Ollama | `http://localhost:11434/v1` |
| OpenAI 兼容 | 自定义 |

### 6.2 关键配置

```
llm.timeout:      180 秒（可调至 1800）— 链步执行超时
llm.max_tokens:   4096（可调至 131072）— 每步最大输出
```

这些值从配置读取，`_execute_single_skill` 和 `_execute_chain_step` 均使用配置值。

---

## 七、配置系统

### 7.1 配置页（Web UI）

| 区域 | 配置项 |
|------|--------|
| **LLM 后端** | 后端类型 / 地址 / Key / 模型 / 超时 / Max Tokens |
| **联网搜索** | 搜索后端（DuckDuckGo/Google/Bing/自定义） |
| **搜索预设** | 预定义搜索词，在对话栏快速选用 |
| **提示词** | 系统提示词（只读）+ 用户提示词（可编辑） |
| **技能路径** | 自定义技能扫描目录 |

### 7.2 配置文件（data/config/settings.json）

```json
{
  "llm": { "backend": "lmstudio", "timeout": 180, "max_tokens": 4096, ... },
  "agent": { "max_steps": 20, "verbose": true },
  "memory": { "max_history": 20, "max_context_chars": 8000 },
  "search": { "backend": "duckduckgo", "presets": [] },
  "prompt": { "user": "" },
  "skills": { "dirs": [] }
}
```

---

## 八、协议与接口

### 8.1 PROTOCOL.md

两份完整接口契约文档：

| 文档 | 内容 |
|------|------|
| **PROTOCOL.md** | CLI 参数 / HTTP API / Pipeline 格式 / 配置 Schema / 批处理格式 / 退出码 |

### 8.2 CLI 接口

```
python main.py                         # 交互模式
python main.py --web                   # Web UI（主模式）
python main.py --backend ollama        # Ollama 后端
python main.py --batch in.json out.json # 批处理
python main.py --jsonl                 # 管道模式
```

### 8.3 导出（__init__.py）

```python
__all__ = [
    "Agent", "AgentConfig", "LLMClient",
    "ConversationMemory", "WorkingMemory",
    "execute_pipeline", "execute_node",
    "Pipeline", "PipelineNode",
    "scan_skills", "search_skills",
    # 7 个工具类
]
```

---

## 九、演变路线

| 阶段 | 状态 | 内容 |
|------|------|------|
| v1.0 | 完成 | 初始 ReAct 循环架构 |
| v1.1 | 完成 | Skill Pipeline 基础编排 |
| v1.2 | 完成 | 固化功能、Apache 2.0 发布 |
| **v2.0** | **当前** | **链驱动架构重塑**：Web UI / 真并行循环 / skill-sub 优化 / PROTOCOL.md / batch+jsonl / 配置驱动超时 |
| v2.1 | 规划 | 技能真实执行（链步骤调用 load_skill + python_execute） |
| v2.2 | 规划 | 跨链状态共享、分支条件、循环变量 |

---

## 十、目录结构（agent/Orchestrator/）

```
agent/Orchestrator/
├── main.py               # CLI 入口
├── orchestrator/          # Python 包
│   ├── __init__.py        # 导出
│   ├── agent_loop.py      # ReAct 循环（回退）
│   ├── agent_config.py    # 配置管理
│   ├── chain_engine.py    # 执行引擎
│   ├── chain_model.py     # 数据模型
│   ├── memory.py          # 记忆系统
│   ├── llm_client.py      # LLM 通信
│   ├── skill_scanner.py   # 技能扫描
│   ├── web_ui.py          # Web UI 服务器
│   ├── static/web_ui.js   # 前端 JS
│   ├── tool_base.py       # 工具基类
│   └── tools/             # 工具模块
├── PROTOCOL.md            # 接口文档
├── setup.bat              # 启动脚本
└── requirements.txt       # 依赖
```
