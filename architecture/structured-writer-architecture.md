<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# Structured Writer 架构文档

> 结构化写作智能体 — LLM 驱动的子结构级逐段写作与 RAG 增强生成。
> 作者：wUwproject | 许可证：Apache 2.0
> 更新：2026-07-26 (v0.2.5b4)

---

## 一、系统概览

Structured Writer 是一个**结构化长文写作智能体**，核心理念是从"LLM 一次写一整篇"升级为**子结构驱动的逐段生成** + **两级 RAG 增强**：

```
用户输入主题
  → [大纲规划器] LLM 生成结构化 JSON 大纲
      节 1: 引言 → [子结构A, 子结构B, 子结构C]
      节 2: 核心架构 → [子结构A, 子结构B, 子结构C]
      ...
  → [交互式大纲] 用户可调整勾选/排序/字数/重点/RAG
  → [串行写作器] 逐子结构执行:
      1. [节 RAG] 查询整节背景资料
      2. [子结构 RAG] 查询子结构针对性资料
      3. [前文注入] 最近 800 字上下文
      4. [LLM 写作] 调用写作者模型生成正文
      5. [续写检测] 若 finish_reason="length" 自动续写
      6. [状态更新] 进度轮询 + 状态文本
  → [合并输出] 全文章节拼接为 .md
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **子结构 > 整段** | 节拆分为 2-4 个子结构逐段写作，每段独立调 LLM，避免长上下文注意力衰减 |
| **材料分级 > 一股脑** | 节级 RAG 提供背景上下文，子结构级 RAG 提供针对性素材，prompt 分段注入 |
| **续写 > 截断** | token 耗尽时不丢弃已写内容，自动续写最多 5 轮 |
| **可配置 > 黑盒** | 大纲所有字段（勾选/排序/字数/重点/RAG）均可交互调整 |
| **容错 > 崩溃** | RAG 超时不塞 prompt，空内容跳过，写作者异常降级为错误提示 |
| **状态持久 > 内存** | 进度写入 state_manager，断线重连可恢复 |

---

## 二、三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | `web_ui.py` (port 8770) / 配置 Tab / 对话 Tab | Web 界面、LLM 配置面板、大纲交互、进度展示 |
| **业务层** | `planner.py` / `writer.py` / `rag_client.py` / `llm_client.py` / `state_manager.py` | 大纲规划、逐段写作、RAG 查询、LLM 通信、状态管理 |
| **基础设施** | `config_manager.py` / `main.py` / `data/` | 配置读写、服务入口、数据持久化 |

### 2.1 完整文件结构

```
structured-writer/
├── main.py                            # ★ 入口（HTTP 服务器）
├── setup.bat                          # Windows 一键启动
├── requirements.txt                   # 依赖清单
├── CHANGELOG.md                       # 版本更新日志
├── SCHEMA.md                          # 项目架构与协议说明
├── README.md                          # 项目说明
├── LICENSE                            # Apache 2.0
├── blueprint.json                     # PyPI 发布蓝图
├── config.json                        # 默认配置
│
├── structured_writer/                 # ★ 智能体核心
│   ├── __init__.py                    # 版本号: 0.2.5b4
│   ├── web_ui.py                      # HTTP 服务器 + 前端（~1700 行）
│   ├── planner.py                     # 大纲规划器（LLM 生成 JSON 大纲）
│   ├── writer.py                      # 串行写作器（两级 RAG + 续写）
│   ├── rag_client.py                  # RAG 客户端（调 rag-assistant :8767）
│   ├── llm_client.py                  # LLM 统一客户端（LM Studio / Ollama）
│   ├── state_manager.py               # 会话状态管理 + 进度追踪
│   └── config_manager.py              # 配置持久化
│
└── data/                              # 运行时数据（不出库）
    ├── config.json                    # 运行时配置
    ├── sessions/{id}.json             # 对话状态
    └── outputs/{name}.md              # 生成结果
```

---

## 三、组件详解

### 3.1 大纲规划器 — `planner.py`

核心是 `plan_outline()` 方法，调用 LLM 生成结构化 JSON 大纲。

```
用户主题 + 写作要求
  ↓
OUTLINE_SYSTEM_PROMPT（含 JSON schema + 约束 + 输出规则）
  ↓
LLM 生成 → parse_outline() 尝试 4 种解析策略:
  1. 直接 json.loads()
  2. ```json 代码块提取
  3. ``` 代码块提取
  4. 找到第一个 { 位置截取解析
  ↓ 失败 → 追加纠正指令 → 重试（最多 3 次）
  ↓
子结构规范化:
  - 如果 LLM 未生成 sub_sections → 自动补一个默认子结构
  - 补全 id / summary / word_count / _checked 等字段
```

**`parse_outline()` 解析策略**：第 4 种策略是关键——当 LLM 在 JSON 前加了中文说明时（"好的，这是生成的大纲："），找到第一个 `{` 位置截取解析。如果尾部有冗余文字，逐行从末尾截断重试。

**输出格式**（JSON）：

```json
{
  "title": "文章标题",
  "sections": [{
    "id": "s1",
    "title": "一级标题",
    "subtitle": "二级标题或简述",
    "summary": "本节总览",
    "word_count": 1200,
    "is_key": false,
    "_checked": true,
    "sub_sections": [
      {"id": "s1_1", "title": "子标题1", "summary": "...", "word_count": 400, "_checked": true},
      {"id": "s1_2", "title": "子标题2", "summary": "...", "word_count": 400, "_checked": true},
      {"id": "s1_3", "title": "子标题3", "summary": "...", "word_count": 400, "_checked": true}
    ]
  }]
}
```

### 3.2 串行写作器 — `writer.py`

核心是 `generate_article()` 函数，逐节逐子结构串行调用 LLM。

#### 3.2.1 两级 RAG 查询

```
启用了 RAG 的节:
  1. [节级别] query = "{文章标题} {节标题} {节summary}"
     → rag_client.query(kb, query)
     → section_rag_context
  2. [子结构级别] query = "{节标题} {子结构标题} {子结构summary}"
     → rag_client.query(kb, query)
     → sub_rag_contexts[{sub_id}]
  3. prompt 装配:
     if 两个 context 都有:
       【背景资料】section_rag_context
       ---
       【针对性资料】sub_rag_context
     else if 只有一个:
       直接使用
     else:
       不写参考资料段
  4. 错误处理:
     - 超时/失败 → 写入 status_text（不塞进 prompt）
     - 无结果 → status_text 显示"RAG无结果"
```

#### 3.2.2 续写机制

```
finish_reason == "stop"  → 正常写完，跳出循环
finish_reason == "length" → token 耗尽:
  content 非空 → 追加 assistant 消息 + "请继续写" → 重试（最多 5 次）
  content 为空  → 推理吃光了 token，放弃续写，跳过
```

#### 3.2.3 错误容错

| 场景 | 行为 |
|------|------|
| LLM 调用异常 | 写入错误提示到正文，标记状态为 error |
| 空内容（推理 token 耗尽） | 跳过该子结构，不影响后续 |
| 全部子结构为空 | 整节跳过，不输出空标题 |
| RAG 超时 | status_text 显示，不污染 prompt |
| RAG 无结果 | status_text 显示，不写参考资料段 |

### 3.3 RAG 客户端 — `rag_client.py`

通过 HTTP 调 rag-assistant 的 8767 外部 API，提供 `query(kb, query_text, top_k)` 方法。

- 内部调用 `POST :8767/api/kb/query`
- 该端点在 `rag-assistant v2.2.8` 新增，接收 `{query, kb, top_k, score_threshold}`，返回 `{context, sources, has_context}`
- 不消耗额外 LLM token（仅做向量检索）

### 3.4 LLM 客户端 — `llm_client.py`

支持双后端，统一返回 `{text}`（chat）或 `{content, finish_reason}`（chat_detailed）：

| 后端 | 协议 | 接口 | 默认端口 |
|------|------|------|---------|
| LM Studio | HTTP (OpenAI 兼容) | `/v1/chat/completions` | 1234 |
| Ollama | HTTP (Ollama API) | `/api/chat` | 11434 |

**`chat_detailed()`** 方法返回 `{content, finish_reason}`，用于续写检测。

**max_tokens 配置**：从 config.json 读取 `writer_model.max_tokens` / `planner_model.max_tokens`，存储为 LLMClient 实例属性。writer.py 不再自行计算覆盖。

### 3.5 状态管理器 — `state_manager.py`

管理会话的全生命周期状态：

| 方法 | 功能 |
|------|------|
| `load(session_id)` | 加载会话状态（JSON） |
| `get_state()` | 获取完整状态 |
| `set_phase(p)` | 设置阶段（plan/review/writing/done/error） |
| `update_section(id, updates)` | 更新节/子结构字段（status, actual_word_count） |
| `get_progress()` | 返回进度信息（done/total/total_words/status_text） |
| `set_status_text(text)` | 设置实时状态文本 |
| `fingerprint_check()` | MD5 指纹验证（防止规划字段被意外修改） |

---

## 四、外部接口

### 4.1 HTTP 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` 或 `/index.html` | GET | 主页面（配置 Tab + 对话 Tab） |
| `/api/config` | GET/POST | 读取/保存配置 |
| `/api/llm/models` | GET | 扫描模型列表 |
| `/api/llm/test` | POST | 测试 LLM 连接 |
| `/api/generate` | POST | 启动生成任务 |
| `/api/progress` | GET | 获取生成进度 |
| `/api/result` | GET | 获取最终结果 |
| `/api/sessions` | GET | 会话列表 |
| `/api/session/load` | GET | 加载会话 |
| `/api/rag/status` | GET | RAG 连接状态 |
| `/api/rag/start` | POST | 冷启动 RAG |

### 4.2 RAG 外部依赖

| 依赖 | 端口 | 说明 |
|------|------|------|
| rag-assistant 外部 API | 8767 | 知识库查询（/api/kb/query） |
| rag-assistant 冷启动 | 18765 | 子进程 Web UI 端口（冷启动用，不开） |

### 4.3 配置

通过 config.json 或 Web UI 配置 Tab 管理：

```json
{
  "planner_model": {"backend": "lmstudio", "model": "qwen/qwen3.5-35b-a3b", "max_tokens": 4096},
  "writer_model": {"backend": "lmstudio", "model": "qwen/qwen3.5-35b-a3b", "max_tokens": 81920, "timeout": 300},
  "rag_path": "C:/Users/sm001/WorkBuddy/rag-assistant",
  "prompt_template": "通用公文"
}
```

---

## 五、交互式大纲 UI

大纲渲染在 `web_ui.js` 中，每个节和子结构渲染为卡片：

```
┌──────────────────────────────────────────────────┐
│  大纲：大型语言模型核心结构解析                      │
│  ☑ 勾选 = 写入，取消 = 跳过                        │
│                                                    │
│  ☑ 引言                              [⭐重点][排序▾][1200][☐ RAG] │
│    ☑ [i▾] 技术演进背景            400字             │
│          简述技术发展状态...                        │ ← summary
│    ☑ [ii▾] 研究动机与目标          400字             │
│    ☑ [iii▾] 文章结构与安排        400字             │
│                                                    │
│  ☐ 结语（整节取消）                                 │
│                                                    │
│  [██████████████░░░░] 60%                          │
│  RAG完成: 白酒 → 技术演进背景（5条）               │ ← status_text
│  [开始生成]  [重新规划]                              │
└──────────────────────────────────────────────────┘
```

### 5.1 客户端状态轮询

`startProgressPolling(sid)` 每 3 秒 polling `/api/progress`：

```
GET /api/progress?session_id=xxx
  → {"done": 5, "total": 12, "status_text": "RAG查询: 白酒 → 技术演进背景"}
    ↓
前端更新: 进度条百分比 + 状态文本
```

### 5.2 勾选提交

`getOutlineData()` 收集所有卡片状态 → `POST /api/generate` → `_handle_generate` 过滤未勾选项。

---

## 六、写作管线

### 完整请求生命周期

```
用户点击"开始生成"
  ↓
POST /api/generate {session_id, orders, rag, checked, sub_orders}
  ↓
_handle_generate()
  ├─ 加载会话状态（StateManager）
  ├─ 应用勾选过滤（移除未勾选的节/子结构）
  ├─ 应用子结构排序（roman→int）
  ├─ 探测 RAG 8767 → 创建 RAGClient（如果在线）
  ├─ 创建 LLMClient（从配置读取）
  └─ 启动后台线程 _run_generation()
      ↓
generate_article(outline, rag_options, llm_client, state_mgr, rag_client)
  ├─ 逐节:
  │   ├─ 节级别 RAG 查询（如果启用）
  │   ├─ 写入 ## 节标题
  │   └─ 逐子结构:
  │       ├─ 子结构级别 RAG 查询（如果启用）
  │       ├─ 构建 prompt（节RAG + 子结构RAG + 前文）
  │       ├─ call LLM → 检测 finish_reason → 续写循环
  │       ├─ 写入 ### 子标题 + 正文
  │       └─ 更新状态（progress + status_text）
  └─ 合并全文 → 写入 .md → 更新 phase="done"
```

### 节级别 RAG 查询

```
query_text = "{title} {section.title} {section.summary}"
rag_client.query(kb, query_text)
→ {"context": "..., has_context": true}
→ 作为【背景资料】写入 prompt
```

### 子结构级别 RAG 查询

```
query_text = "{section.title} {sub.title} {sub.summary}"
rag_client.query(kb, query_text)
→ {"context": "..., has_context": true}
→ 作为【针对性资料】写入 prompt
```

### prompt 结构

```
# 文章主题

{title}

# 正写作的子结构

### {sub.title}
{sub.summary}

字数要求：约 {word_count} 字

写作要点：
{sub.summary}

前文回顾：
{context_buffer}

【背景资料】（本节整体相关）
{section_rag_context}
---
【针对性资料】（针对当前子结构）
{sub_rag_context}

请写出该节正文（Markdown 格式）。只输出正文，不输出标题行。
```

---

## 七、版本演进要点

| 版本 | 新增/变更要点 |
|------|-------------|
| v0.2.5b4 | PyPI long_description 修复（同步 CHANGELOG） |
| v0.2.5b3 | PyPI 发布准备：`app/`→`structured_writer/` + LICENSE + README + blueprint + Actions 检测 |
| v0.2.5b2 | 两级 RAG、实时状态显示、子结构摘要 UI、错误不注入 prompt |
| v0.2.5b1 | 子结构系统、大纲勾选/取消、双级排序、续写机制、RAG 对接、LLMClient max_tokens 存储 |
| v0.1.0 | 项目骨架、LLM 客户端、会话管理、大纲规划器、串行写作器、异步生成、进度轮询 |

---

*最后更新：2026-07-26*
