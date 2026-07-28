<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# Structured Writer 架构文档

> 结构化写作智能体 — 模板驱动的多节文章串行生成，支持大纲规划、逻辑顺序编排、RAG 引用、两级校验。
> 作者：wUwproject | 许可证：Apache 2.0
> 更新：2026-07-29 (v1.1.0b4)

---

## 一、系统概览

Structured Writer 是一个**结构化长文写作智能体**，核心理念是从"LLM 一次写一整篇"升级为**模板驱动的多节串行生成** + **逻辑顺序编排** + **两级 RAG 增强** + **引用规则约束**：

```
用户输入主题 + 选择模板
  → [大纲规划器] LLM 生成结构化 JSON 大纲（按模板 content[] 字段）
      节 1: 引言 → [子结构A, 子结构B]
      节 2: 正文 → [子结构A, 子结构B, 子结构C]
      ...（is_key 自动标记重点节）
  → [交互式大纲] 用户可调整勾选/排序/字数/重点/RAG/逻辑顺序
  → [串行写作器] 按逻辑顺序分批（0→1→2）执行:
      1. [节 RAG] 查询整节背景资料（如启用）
      2. [子结构 RAG] 查询子结构针对性资料（如启用）
      3. [前文注入] style_hint + logic_hint + context_buffer
      4. [LLM 写作] 调用写作者模型生成正文
      5. [续写检测] 若 finish_reason="length" 自动续写
      6. [状态更新] 进度轮询 + 状态文本
  → [合并输出] 按 content[]/用户顺序重排 → 写入 .md
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **逻辑顺序 ≠ 输出顺序** | 写作按 `_logical_order` 分批（0→1→2），输出按 content[]/用户排序重排。先写正文再写结论最后提取摘要 |
| **模板驱动** | 文章结构由模板 `meta[]` + `content[]` + `style` + `logic` 定义，LLM 只负责填充内容，结构由配置控制 |
| **子结构 > 整段** | 节拆分为 2-4 个子结构逐段写作，每段独立调 LLM，避免长上下文注意力衰减 |
| **材料分级 > 一股脑** | 节级 RAG 提供背景上下文，子结构级 RAG 提供针对性素材，prompt 分段注入 |
| **续写 > 截断** | token 耗尽时不丢弃已写内容，自动续写最多 5 轮 |
| **可配置 > 黑盒** | 大纲所有字段（勾选/排序/字数/重点/RAG/逻辑顺序）均可交互调整 |
| **容错 > 崩溃** | RAG 超时不塞 prompt，空内容标记占位，写作者异常降级为错误提示 |
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
├── setup.py                           # PyPI 构建配置
├── pyproject.toml                     # PyPI 标准构建配置
├── requirements.txt                   # 依赖清单
├── CHANGELOG.md                       # 版本更新日志
├── SCHEMA.md                          # 项目架构与协议说明
├── README.md                          # 项目说明
├── LICENSE                            # Apache 2.0
├── config.json                        # 默认配置（含模板定义）
│
├── .github/workflows/
│   └── publish-to-pypi.yml           # GitHub Actions PyPI 自动发布
│
├── structured_writer/                 # ★ 智能体核心
│   ├── __init__.py                    # 版本号: 1.1.0b4
│   ├── web_ui.py                      # HTTP 服务器 + 前端（~2300 行）
│   ├── planner.py                     # 大纲规划器（LLM 生成 JSON 大纲）
│   ├── writer.py                      # 串行写作器（两级 RAG + 续写 + 逻辑顺序）
│   ├── rag_client.py                  # RAG 客户端（调 rag-assistant :8767）
│   ├── llm_client.py                  # LLM 统一客户端（LM Studio / Ollama）
│   ├── state_manager.py               # 会话状态管理 + 进度追踪
│   └── config_manager.py              # 配置持久化（含模板读写）
│
└── data/                              # 运行时数据（不出库）
    ├── config.json                    # 运行时配置
    ├── sessions/{id}.json             # 对话状态
    ├── archives/sessions/             # 归档会话
    └── outputs/{name}.md              # 生成结果
```

---

## 三、组件详解

### 3.1 大纲规划器 — `planner.py`

核心是 `plan_outline()` 方法，根据模板的 `meta[]` + `content[]` + `style` + `logic` 生成结构化 JSON 大纲。

**模板系统**：每个模板定义 `meta`（短数据：标题/作者/文号等）和 `content`（长文本：关键词/摘要/引言/正文/结论/参考文献）。`show_label` 控制是否在输出中显示字段标题。`logical_order` 控制写作认知顺序（0=先写，1=其次，2=最后写）。

```
用户主题 + 模板定义（meta+content+style+logic）
  ↓
OUTLINE_SYSTEM_PROMPT（含字段清单 + JSON schema + 约束）
  - 硬性要求：所有 content 字段必须在 sections 中输出，一条不能少
  - is_key: true = 重点节，字数可上浮 50%
  ↓
LLM 生成 → parse_outline() 尝试 4 种解析策略:
  1. 直接 json.loads()
  2. ```json 代码块提取
  3. ``` 代码块提取
  4. 找到第一个 { 位置截取解析 → 逐行截断重试
  ↓ 失败 → 追加纠正指令 → 重试（最多 3 次）
  ↓
_normalize_outline() 全面补全:
  - 对比 content_fields name 和 sections title，缺失的自动补入
  - 子结构补全（section 类型无子结构时自动生成一个默认子结构）
  - 补全 id / summary / word_count / _checked / is_key / show_label / _logical_order
  - _logical_order 从模板 content[].logical_order 读取，0=None=content[]顺序
```

**`parse_outline()` 解析策略**：第 4 种策略是关键——当 LLM 在 JSON 前加了中文说明时（"好的，这是生成的大纲："），找到第一个 `{` 位置截取解析。如果尾部有冗余文字，逐行从末尾截断重试。

**输出格式**（JSON）：

```json
{
  "title": "文章标题",
  "meta": {"标题": "xxx", "作者": "（待填写）"},
  "sections": [{
    "id": "s1",
    "title": "一级标题",
    "subtitle": "二级标题或简述",
    "summary": "本节总览",
    "word_count": 1200,
    "is_key": false,
    "type": "section",
    "show_label": true,
    "_logical_order": 0,
    "_checked": true,
    "sub_sections": [
      {"id": "s1_1", "title": "子标题1", "summary": "...", "word_count": 400, "_checked": true}
    ]
  }]
}
```

**字段说明**：

| 字段 | 来源 | 说明 |
|------|------|------|
| `show_label` | 模板 content[].show_label | true=输出节标题，false=纯内容 |
| `type` | 模板 content[].type | leaf=无子结构直接写，section=拆2-4个子结构 |
| `_logical_order` | 模板 content[].logical_order | 写作批次：0=第一批,1=第二批,2=最后批 |
| `is_key` | LLM 自动/用户手动 | true=重点节，字数可上浮50% |

### 3.2 串行写作器 — `writer.py`

核心是 `generate_article()` 函数，按 `_logical_order` 分批（0→1→2）逐节逐子结构串行调用 LLM，输出按 content[]/用户排序重排。

#### 3.2.0 逻辑写作顺序

```
_build_context_section_prompt() 构建 prompt（平面结构，含子结构信息但作为描述而非递归）:

写作顺序 = 按所有节的 _logical_order 排序（0→1→2）
输出顺序 = 按 content[]/用户排序重排

每个叶子节直接写（type=leaf + LLM 调用）
每个 section 节拆为子结构逐一写
```

#### 3.2.0.1 prompt 注入

每节写入 prompt 时可注入三个信息：

| 注入数据 | 来源 | 说明 |
|---------|------|------|
| `logic_hint` | 模板 `logic` 字段 | 写作阶段提示（如"先写引言和正文，再写结论，最后提取摘要"） |
| `style_hint` | 模板 `style` 字段 | 写作风格要求和引用规则 |
| `context_buffer` | 前文累积 | `_logical_order=2` 的节传全文，其他节（含子结构）截断至 `context_review_length` 字 |

#### 3.2.0.2 show_label 控制节标题

```
sec_show_label = section["show_label"]  // 从模板配置读取

if sec_show_label:
    section_md = "\n\n## 节标题\n\n"     // 带标题
else:
    section_md = ""                       // 无标题，纯内容

写入后:
  if wrote_any:          → parts_by_sid[sid] = section_md  // 有内容的完整块
  elif sec_show_label:   → parts_by_sid[sid] = "\n\n## 节标题\n\n"  // 空节仅标题
  else:                  → 不加入（show_label=false 时空节跳过）
```

#### 3.2.1 两级 RAG 查询

```
启用了 RAG 的节（在写作循环内逐节执行）:
  query_text = "{title} {section.title} {section.summary}"
  → rag_client.query(kb, query_text)
  → section_rag_context

  子结构级别（如存在子结构）:
  query_text = "{section.title} {sub.title} {sub.summary}"
  → rag_client.query(kb, query_text)
  → sub_rag_contexts[{sub_id}]
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
| LLM 调用异常 | 写入错误提示到 `section_md`，保留节标题 |
| 空内容（LLM 返回空字符串） | wrote_any=false，show_label=true 保留标题，false 跳过 |
| 全部子结构为空 | 整节 retain 标题或跳过 |
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

**max_tokens 与 temperature**：从 config.json 读取 `writer_model.max_tokens` / `planner_model.max_tokens` 及 `temperature`，存储为 LLMClient 实例属性。各调用点传 `temperature=None` 走实例属性，无需每处硬编码。

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
| `/api/config` | GET/POST | 读取/保存配置（含模板） |
| `/api/gen_template` | POST | 从对话描述生成模板定义 |
| `/api/llm/models` | GET | 扫描模型列表 |
| `/api/llm/test` | POST | 测试 LLM 连接 |
| `/api/plan` | POST | 规划 / 重新规划 |
| `/api/generate` | POST | 启动生成任务 |
| `/api/progress` | GET | 获取生成进度 |
| `/api/result` | GET | 获取最终结果 |
| `/api/sessions` | GET | 会话列表 |
| `/api/session/load` | GET | 加载会话 |
| `/api/session/archive` | POST | 归档会话 |
| `/api/session/restore` | POST | 恢复会话 |
| `/api/session/delete` | POST | 删除会话 |
| `/api/rag/status` | GET | RAG 连接状态 |
| `/api/rag/start` | POST | 冷启动 RAG |
| `/api/rag/stop` | POST | 停止 RAG（kill 进程树 + 等端口释放） |
| `/api/batch_auto` | POST | 批量自动撰写（多行输入，逐篇执行） |

### 4.2 RAG 外部依赖

| 依赖 | 端口 | 说明 |
|------|------|------|
| rag-assistant 外部 API | 8767 | 知识库查询（/api/kb/query） |
| rag-assistant 冷启动 | 18765 | 子进程 Web UI 端口（冷启动用，不开） |

### 4.3 配置

通过 config.json 或 Web UI 配置 Tab 管理：

```json
{
  "planner_model": {"backend": "lmstudio", "model": "qwen/qwen3.5-35b-a3b", "max_tokens": 4096, "temperature": 0.6},
  "writer_model": {"backend": "lmstudio", "model": "qwen/qwen3.5-35b-a3b", "max_tokens": 8192, "timeout": 300, "temperature": 0.7},
  "rag_path": "",
  "selected_template": "学术论文",
  "context_review_length": 800,
  "fact_check_enabled": false,
  "max_sessions": 20,
  "templates": {
    "学术论文": {
      "meta": [{"name":"标题","show_label":true,...}, ...],
      "content": [{"name":"关键词","show_label":true,"type":"leaf","logical_order":2}, ...],
      "style": "请以学术论文风格撰写...",
      "logic": "先写引言和正文各节，再写结论，最后提取关键词和摘要..."
    }
  },
  "user_templates": {}
}
```

---

## 五、交互式大纲 UI

大纲渲染在 `web_ui.js` 中，每个节和子结构渲染为卡片。配置 Tab 管理模板定义（meta+content 表格 + style/logic 文本域）。

```
┌──────────────────────────────────────────────────┐
│  大纲：语言大模型关键技术路径                      │
│  ☑ 勾选 = 写入，取消 = 跳过                        │
│                                                    │
│  ☑ 关键词 LEAF                       / 逻辑顺序: 最后 │
│  ☑ 摘要 LEAF                         / 逻辑顺序: 最后 │
│  ☑ 引言 SEC                          / 逻辑顺序: 自动 │
│    ☑ [s1▾] 研究背景            400字                │
│    ☑ [s2▾] 问题提出            400字                │
│  ☑ 正文 SEC 重点                   / 逻辑顺序: 自动 │
│    ☑ [s1▾] 架构演进            400字                │
│  ☑ 结论 SEC                         / 逻辑顺序: 其次 │
│  ☑ 参考文献 LEAF                    / 逻辑顺序: 最后 │
│                                                    │
│  [██████████████░░░░] 60%                          │
│  [开始生成]  [重新规划]                              │
└──────────────────────────────────────────────────┘
```

### 5.1 配置 Tab

配置 Tab 独立于对话 Tab，管理：

| 区域 | 内容 |
|------|------|
| 模板选择器 | 从下拉菜单选择模板，受 `user_templates` 标记可删除 |
| 元数据表格 | name / show_label(checkbox) / desc / source(user/auto/llm) |
| 内容树表格 | name / show_label(checkbox) / desc / type(leaf/section) / 逻辑顺序(自动/先写/其次/最后) |
| style 文本域 | 写作风格说明（注入 writer prompt 的 style_hint） |
| logic 文本域 | 写作顺序说明（注入 writer prompt 的 logic_hint） |
| 保存/另存为/删除 | 模板持久化，修改后需保存才生效 |
| 从对话生成 | 通过 LLM 对话描述生成模板（有限校验 + 容错解析） |
| RAG 路径 | 本地 rag-assistant 知识库路径 |
| 上下文回顾长度 | `context_review_length`（默认 800，子结构用） |

### 5.2 客户端状态轮询

`startProgressPolling(sid)` 每 1.5 秒 polling `/api/progress`（RAG 状态轮询同样 1.5s + cache-buster）：

```
GET /api/progress?session_id=xxx
  → {"done": 5, "total": 12, "status_text": "RAG查询: 白酒 → 技术演进背景"}
    ↓
前端更新: 进度条百分比 + 状态文本
```

### 5.3 勾选提交

`getOutlineData()` 收集所有卡片状态 → `POST /api/generate` → `_handle_generate` 过滤未勾选项。

---

## 六、写作管线

### 完整请求生命周期

```
用户点击"开始生成"
  ↓
POST /api/generate {session_id, orders, rag, sec_words, key_sections, sub_words}
  ↓
_handle_generate()
  ├─ 加载会话状态（StateManager）
  ├─ 应用勾选过滤（移除未勾选的节/子结构）
  ├─ 应用用户排序（如果提供）
  ├─ 应用重点覆盖（key_sections）
  ├─ 探测 RAG 8767 → 创建 RAGClient（如果在线）
  ├─ 创建 LLMClient（从配置读取）
  └─ 启动后台线程 _run_generation()
      ↓
generate_article(outline, user_orders, rag_options, llm_client, state_mgr, template)
  ├─ 读取 meta_fields, logic_prompt, style_prompt
  ├─ 按逻辑顺序排序批次
  ├─ 逐批（0→1→2）:
  │   ├─ 节级别 RAG 查询（如果启用）
  │   ├─ 写入节标题（据 show_label）
  │   └─ leaf 节（type=leaf）:
  │   │      ├─ 构建 prompt（+logic_hint + style_hint + context_buffer）
  │   │      ├─ call LLM → 检测 finish_reason → 续写循环
  │   │      ├─ 写入 parts_by_sid（必写入，空标记占位）
  │   │      └─ 更新状态（progress + status_text）
  │   └─ section 节（type=section）→ 逐子结构:
  │          ├─ 子结构级别 RAG 查询（如果启用）
  │          ├─ 构建 prompt（RAG + 前文截断 + logic_hint + style_hint）
  │          ├─ call LLM → 检测 finish_reason → 续写循环
  │          ├─ 写入子结构正文
  │          └─ 更新状态
  ├─ 按 output_order（content[]/用户排序）组装 parts_by_sid
  ├─ 渲染 meta_block（据 show_label 显示标签）
  ├─ 拼接 article_md → 写入 .md → phase="done"
  └─ 返回 (md_content, output_path)
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

### {section_title}
{sub_section_subtitle}

写作阶段提示：{logic_hint}        ← 来自模板 logic 字段
写作风格要求：{style_hint}        ← 来自模板 style 字段

字数要求：约 {word_count} 字
（重点节，可上浮 50%）

写作要点：
{section_summary}

前文回顾：
{context_buffer}

【RAG 参考资料】（来自知识库检索，请结合文章主题选择性引用）：
{rag_context}

【辅助知识】：
{aux_text}

请写出该节正文（Markdown 格式）。只输出正文，不输出标题行。
```

---

## 七、版本演进要点

| 版本 | 新增/变更要点 |
|------|-------------|
| v1.1.0b4 | 模板系统重构（meta+content+style+logic）、逻辑顺序编排、show_label 全链路传播、style_hint 注入、引用规则、context_buffer 策略（leaf order=2 传全文）、叶子节 parts_by_sid 修复、is_key 自动标记恢复、gen-template 容错校验、配置 Tab 模板管理、_normalize_outline 兜底补缺 |
| v1.0.28 | 事实自检内嵌标记法（零额外 LLM 调用）、temperature 可配置、RAG 停止、模型下拉框修复、子结构字数联动、大纲过滤同步进度、批量自动撰写、会话归档、深层合并 DEFAULT_CONFIG |
| v0.2.5b4 | PyPI long_description 修复（同步 CHANGELOG） |
| v0.2.5b3 | PyPI 发布准备：`app/`→`structured_writer/` + LICENSE + README + blueprint + Actions 检测 |
| v0.2.5b2 | 两级 RAG、实时状态显示、子结构摘要 UI、错误不注入 prompt |
| v0.2.5b1 | 子结构系统、大纲勾选/取消、双级排序、续写机制、RAG 对接、LLMClient max_tokens 存储 |
| v0.1.0 | 项目骨架、LLM 客户端、会话管理、大纲规划器、串行写作器、异步生成、进度轮询 |

---

*最后更新：2026-07-29 (v1.1.0b4)*
