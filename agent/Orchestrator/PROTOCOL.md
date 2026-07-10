# Orchestrator Protocol

> 版本: 2.0.0
> 更新: 2026-07-10

---

## 目录

1. [概述](#1-概述)
2. [CLI 参数](#2-cli-参数)
3. [运行模式](#3-运行模式)
4. [HTTP API](#4-http-api)
5. [Pipeline 数据格式](#5-pipeline-数据格式)
6. [配置 Schema](#6-配置-schema)
7. [批处理格式](#7-批处理格式)
8. [JSONL 管道格式](#8-jsonl-管道格式)
9. [退出码](#9-退出码)

---

## 1. 概述

Orchestrator 是一个基于本地 LLM 的 Python 智能体系统，支持:

- **ReAct 智能体循环**: 思考 → 行动 → 观察 → 重复（最多 20 步）
- **Skill Pipeline 编排**: 串行/并行/循环流水线
- **多 LLM 后端**: LM Studio / Ollama / OpenAI 兼容 / 直接 GGUF 加载
- **工具系统**: load_skill / read_file / write_file / web_fetch / web_search / python_execute

### 技术栈

- Python 3.11+ 标准库（无外部框架依赖）
- HTTP 服务器: `http.server`（内置）
- LLM 通信: `urllib`（OpenAI 兼容 API）
- 前端: 纯 HTML/CSS/JS（无构建步骤）

---

## 2. CLI 参数

```
python main.py [OPTIONS]
```

### 运行模式

| 参数 | 说明 |
|------|------|
| `--web` | 启动 Web UI（默认端口 8765） |
| `--port PORT` | Web UI 端口（数字或 `auto`） |
| `--query TEXT` | 单次问答 |
| `--batch INPUT OUTPUT` | 批处理模式 |
| `--jsonl` | JSONL 管道模式 |
| `--check` | 仅测试后端连接 |
| `--list-models` | 列出所有可用模型 |
| `--pidfile PATH` | PID 文件路径 |

### 后端选择

| 参数 | 说明 |
|------|------|
| `--backend {lm-studio,ollama,custom,direct}` | LLM 后端（默认 lm-studio） |
| `--direct` | 等同 `--backend direct` |

### API 后端参数

| 参数 | 说明 |
|------|------|
| `--base-url URL` | API 地址（custom 模式必填） |
| `--api-key KEY` | API Key |
| `--model NAME` | 模型名称 |

### 直接加载参数

| 参数 | 说明 |
|------|------|
| `--model NAME` | GGUF 模型名或序号 |
| `--gpu-layers N` | GPU 卸载层数（-1=自动） |

### 其他

| 参数 | 说明 |
|------|------|
| `--config PATH` | 配置文件路径 |
| `--no-rag` | 不加载 RAG 工具 |
| `--no-web` | 不加载网络工具 |
| `--verbose {True,False}` | 打印思考过程 |

### 示例

```bash
# 启动 Web UI
python main.py --web

# 指定端口
python main.py --web --port 8080

# 自动分配端口
python main.py --web --port auto

# Ollama 后端
python main.py --backend ollama

# OpenAI 兼容云端 API
python main.py --backend custom --base-url https://api.openai.com/v1 --api-key sk-xxx --model gpt-4

# 批处理
python main.py --batch input.json output.json

# JSONL 管道
cat queries.jsonl | python main.py --jsonl > results.jsonl

# 单次问答
python main.py --query "今天天气怎么样"
```

---

## 3. 运行模式

### 3.1 Web 模式（默认）

```
python main.py --web
```

启动 Web UI 服务器，监听 0.0.0.0:8765。提供三个 Tab:

- **对话**: ReAct 智能体交互
- **配置**: LLM 后端 / 搜索 / 提示词设置
- **Pipeline**: Skill 流水线编排

### 3.2 CLI 交互模式

```
python main.py
```

交互式命令行对话。内置命令:

| 命令 | 说明 |
|------|------|
| `/exit` 或 `exit` | 退出 |
| `/reset` | 重置会话记忆 |
| `/tools` | 查看可用工具 |
| `/help` | 帮助 |

### 3.3 批处理模式

```
python main.py --batch input.json output.json
```

读入 JSON 文件 → 执行 Pipeline → 写入 JSON 结果。

详见 [第 7 节 — 批处理格式](#7-批处理格式)。

### 3.4 JSONL 管道模式

```
cat queries.jsonl | python main.py --jsonl > results.jsonl
```

逐行读 stdin → 逐行写 stdout。适合链式调用:

```
cat input.jsonl | python main.py --jsonl | jq '.output' > results.txt
```

详见 [第 8 节 — JSONL 管道格式](#8-jsonl-管道格式)。

---

## 4. HTTP API

### 4.1 基础

- **Base URL**: `http://<host>:<port>/`
- **默认端口**: 8765
- **Content-Type**: `application/json; charset=utf-8`
- **编码**: UTF-8

### 4.2 端点清单

#### `GET /`

返回完整 Web UI 页面（HTML）。

---

#### `POST /api/chat`

智能体对话（ReAct 决策循环）。

**请求:**
```json
{
  "message": "你的问题",
  "pipeline_id": "",         // 可选，关联的 Pipeline 名称
  "skill_sub": false,        // 可选，是否启用 skill-sub 优化
  "save_chain": false,       // 可选，是否保存优化后的链到 Pipeline
  "reset": false             // 可选，重置会话
}
```

**响应:**
```json
{
  "success": true,
  "text": "回答内容（可能含 Markdown）",
  "kb": "",
  "reasoning": "推理过程（可选）"
}
```

**错误响应:**
```json
{
  "success": false,
  "error": "错误描述"
}
```

---

#### `GET /api/config`

获取完整配置。

**响应:**
```json
{
  "backend": "lmstudio",
  "model": "qwen/qwen3.6-35b-a3b",
  "timeout": 180,
  "max_tokens": 4096,
  "api_key": "",
  "base_url": "",
  "local_url": "http://localhost:1234",
  "search_backend": "duckduckgo",
  "search_url": "",
  "search_key": "",
  "search_google_key": "",
  "search_google_cx": "",
  "search_bing_key": "",
  "search_presets": [],
  "user_prompt": "",
  "system_prompt_raw": "..."
}
```

---

#### `POST /api/config`

更新配置。

**请求:** 可包含上述任意字段。只有提供的字段会被更新。

```json
{
  "backend": "ollama",
  "model": "llama3.1",
  "user_prompt": "你是一个 Python 专家",
  "search_presets": ["今日AI新闻", "Python 教程"],
  "search_backend": "duckduckgo"
}
```

**响应:** `{"success": true}`

---

#### `GET /api/llm/models`

获取 LLM 可用模型列表。

**响应:**
```json
{
  "models": ["qwen/qwen3.6-35b-a3b", "llama3.1:8b"]
}
```

---

#### `GET /api/llm/test`

测试 LLM 连接。

**响应:**
```json
{
  "success": true,
  "msg": "连接正常"
}
```

---

#### `GET /api/skills`

获取可用技能列表。

**响应:**
```json
{
  "skills": [
    {
      "name": "analysis-toolkit",
      "display_name": "数据分析工具箱",
      "description": "检验检测行业质量控制和数据分析",
      "version": "2.0.4"
    }
  ],
  "error": ""
}
```

---

#### `GET /api/pipelines`

列出已保存的 Pipeline。

**响应:**
```json
{
  "pipelines": ["my-pipeline", "test-pipe"]
}
```

---

#### `GET /api/pipelines/:name`

获取指定 Pipeline 详情。

**响应:**
```json
{
  "name": "my-pipeline",
  "nodes": [...],    // 扁平化的节点列表
  "tree": [...]      // 完整的树结构
}
```

**404 响应:** `{"error": "not found"}`

---

#### `POST /api/pipelines`

保存 Pipeline。

**请求:**
```json
{
  "name": "my-pipeline",
  "nodes": [...],     // 扁平节点
  "tree": [...]       // 完整树结构
}
```

**响应:** `{"success": true}`

---

#### `POST /api/pipelines/run`

执行 Pipeline。

**请求:**
```json
{
  "nodes": [...],     // 扁平节点（回退）
  "tree": [...]       // 完整树结构（优先）
}
```

**响应:**
```json
{
  "output": "执行结果文本",
  "steps": 5,
  "latency_ms": 1234
}
```

---

#### `POST /api/pipelines/delete`

删除 Pipeline。

**请求:** `{"name": "my-pipeline"}`

**响应:** `{"success": true}`

---

## 5. Pipeline 数据格式

### 5.1 节点结构

```json
{
  "name": "skill-name",       // 技能名称
  "display": "显示名称",       // 可选，前端显示
  "mode": "seq",              // seq | par | loop
  "children": [],              // 子节点（par/loop 时有用）
  "loop_times": 3             // 循环次数（loop 模式）
}
```

### 5.2 模式说明

| 模式 | 说明 | children 要求 |
|------|------|-------------|
| `seq` | 串行执行单个技能 | 空数组 |
| `par` | 并行组，多个技能同时执行 | ≥2 个子节点 |
| `loop` | 循环组，重复执行子节点 N 次 | 任意子节点 |

### 5.3 示例: 完整 Pipeline 树

```json
[
  {
    "name": "analysis-toolkit",
    "display": "数据分析",
    "mode": "seq",
    "children": [],
    "loop_times": 3
  },
  {
    "name": "",
    "display": "并行搜索",
    "mode": "par",
    "children": [
      {"name": "web_search", "display": "搜索新闻", "mode": "seq", "children": []},
      {"name": "web_fetch", "display": "获取详情", "mode": "seq", "children": []}
    ],
    "loop_times": 3
  },
  {
    "name": "write_file",
    "display": "保存结果",
    "mode": "seq",
    "children": [],
    "loop_times": 3
  }
]
```

### 5.4 扁平化格式

前端通过 `flattenTree()` 将树展开为扁平列表。扁平列表的每个元素只有 `name`、`display`、`mode` 三个字段（无 children/loop_times）。

```json
[
  {"name": "analysis-toolkit", "display": "数据分析", "mode": "seq"},
  {"name": "web_search", "display": "搜索新闻", "mode": "seq"},
  {"name": "web_fetch", "display": "获取详情", "mode": "seq"},
  {"name": "write_file", "display": "保存结果", "mode": "seq"}
]
```

---

## 6. 配置 Schema

配置文件路径: `data/config/settings.json`

### 完整 Schema

```json
{
  "llm": {
    "backend": "lmstudio",            // ollama | lmstudio | openai
    "base_url": "http://localhost:1234/v1",
    "api_key": "",
    "model_name": "",
    "temperature": 0.3,
    "max_tokens": 16384,
    "top_p": 0.9,
    "timeout": 180,
    "ollama_url": "http://localhost:11434",
    "lmstudio_url": "http://localhost:1234"
  },
  "agent": {
    "max_steps": 20,                  // 最大 ReAct 循环步数
    "max_retries": 3,                 // 工具失败重试次数
    "verbose": true,                  // 打印思考过程
    "stop_on_tool_error": false       // 工具失败是否终止
  },
  "memory": {
    "max_history": 20,                // 保留最近对话轮数
    "max_context_chars": 8000,        // 上下文最大字符数
    "working_memory_file": "working_memory.json"
  },
  "search": {
    "backend": "duckduckgo",          // duckduckgo | google | bing | custom
    "url": "",                        // 自定义搜索 URL
    "api_key": "",
    "google_key": "",
    "google_cx": "",
    "bing_key": "",
    "presets": []                     // 搜索预设词列表
  },
  "prompt": {
    "user": ""                        // 用户自定义提示词
  },
  "rag": {
    "skill_path": "~/.workbuddy/skills/local-rag-builder",
    "default_kb": "default",
    "k": 5,
    "score_threshold": 0.0
  }
}
```

---

## 7. 批处理格式

### 7.1 输入 JSON

```json
{
  "nodes": [
    {"name": "analysis-toolkit", "mode": "seq"},
    {"name": "web_search", "mode": "seq"}
  ],
  "tree": [
    {
      "name": "analysis-toolkit",
      "display": "数据分析",
      "mode": "seq",
      "children": []
    }
  ]
}
```

`nodes` 和 `tree` 二选一。

### 7.2 输出 JSON

```json
{
  "success": true,
  "output": "  [1] → 数据分析\n      结果: ...\n  [2] → 搜索新闻\n      结果: ...",
  "steps": 2,
  "latency_ms": 1523
}
```

**错误输出:**
```json
{
  "success": false,
  "error": "错误描述",
  "latency_ms": 0
}
```

---

## 8. JSONL 管道格式

### 8.1 输入（每行一个 JSON）

```json
{"query": "今天天气怎么样"}
{"nodes": [{"name": "web_search", "mode": "seq"}], "tree": []}
{"message": "用 Python 写一个排序算法", "pipeline_id": "my-pipe"}
```

### 8.2 输出（每行一个 JSON）

```json
{"success": true, "output": "...", "latency_ms": 1523, "error": ""}
{"success": false, "error": "错误描述", "latency_ms": 0}
```

### 8.3 管道用法

```bash
# 生成输入 → 处理 → 提取结果
echo '{"query":"搜索 Python 教程"}' | python main.py --jsonl | jq '.output'

# 从文件读取
cat queries.jsonl | python main.py --jsonl > results.jsonl

# 与 jq 链式处理
cat queries.jsonl | python main.py --jsonl | jq -c 'select(.success)' | wc -l
```

---

## 9. 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 全部成功 |
| 1 | 参数错误或执行失败 |
