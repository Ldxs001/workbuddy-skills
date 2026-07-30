<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# Structured Writer 架构文档

> 结构化写作智能体 — LLM 驱动的子结构级逐段写作与自检。
> 作者：wUwproject | 许可证：Apache 2.0
> 更新：2026-07-29 (v1.1.0b9)

---

## 一、系统概览

Structured Writer 是一个**结构化长文写作智能体**，核心理念是从"LLM 一次写一整篇"升级为**模板驱动的结构约束** + **子结构驱动的逐段生成** + **两级 RAG 增强**：

```
用户选择/创建模板
  → [模板系统] 模板定义 meta+content+style+logic 四元结构
  → [用户填写] meta 字段（标题/作者/单位等），content 字段自动参与大纲
  → [大纲规划器] LLM 根据模板 content 生成结构化 JSON 大纲
      节 1: 引言 → [子结构A, 子结构B, 子结构C]
      节 2: 方法 → [子结构A, 子结构B]
      ...
  → [交互式大纲] 用户可调整勾选/排序/字数/重点/RAG
  → [串行写作器] 逐子结构执行:
      1. [节 RAG] 查询整节背景资料
      2. [子结构 RAG] 查询子结构针对性资料
      3. [引用来源注入] 文档元数据（标题/作者）全局累积，所有节共享
      4. [前文注入] 最近 N 字上下文（可配置）
      5. [LLM 写作] 调用写作者模型生成正文
      6. [续写检测] 若 finish_reason="length" 自动续写
      7. [状态更新] 进度轮询 + 状态文本
  → [引用后处理] 引用自{文件名} → [N] + 自动生成参考文献节
  → [合并输出] 全文章节拼接为 .md
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **模板 > 空白** | 文章结构由模板定义（meta+content），LLM 和用户都在模板确定的边界内操作 |
| **子结构 > 整段** | 节拆分为 2-4 个子结构逐段写作，每段独立调 LLM，避免长上下文注意力衰减 |
| **材料分级 > 一股脑** | 节级 RAG 提供背景上下文，子结构级 RAG 提供针对性素材，文档元数据全局共享 |
| **引用后处理 > LLM 格式** | LLM 写自然语言标记（引用自{文件名}），确定性代码替换为编号 [N] 并生成参考文献 |
| **续写 > 截断** | token 耗尽时不丢弃已写内容，自动续写最多 5 轮 |
| **可配置 > 黑盒** | 模板所有字段可编辑，大纲所有字段（勾选/排序/字数/重点/RAG/辅助知识）均可交互调整 |
| **容错 > 崩溃** | RAG 超时不塞 prompt，空内容跳过，写作者异常降级为错误提示 |
| **状态持久 > 内存** | 进度写入 state_manager，断线重连可恢复 |

---

## 二、三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | `web_ui.py` (port 8770) / 配置 Tab / 对话 Tab | Web 界面、LLM 配置面板、模板编辑器、大纲交互、进度展示、已完成文章列表 |
| **业务层** | `planner.py` / `writer.py` / `rag_client.py` / `llm_client.py` / `state_manager.py` / `citation_validator.py` | 大纲规划、逐段写作、RAG 查询、LLM 通信、状态管理、引用验证 |
| **基础设施** | `config_manager.py` / `main.py` / `data/` | 配置读写（含模板分离存储）、服务入口、数据持久化 |

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
├── config.json                        # 默认配置（不含模板）
│
├── structured_writer/                 # ★ 智能体核心
│   ├── __init__.py                    # 版本号: 1.1.0b9
│   ├── web_ui.py                      # HTTP 服务器 + 前端（~3700 行）
│   ├── planner.py                     # 大纲规划器（LLM 生成 JSON 大纲）
│   ├── writer.py                      # 串行写作器（两级 RAG + 续写 + 引用后处理）
│   ├── rag_client.py                  # RAG 客户端（调 rag-assistant :8767）
│   ├── llm_client.py                  # LLM 统一客户端（LM Studio / Ollama）
│   ├── state_manager.py               # 会话状态管理 + 进度追踪
│   ├── citation_validator.py          # 引用验证（扫描+报告）
│   └── config_manager.py              # 配置读写 + 模板分离存储 + 旧格式迁移
│
└── data/                              # 运行时数据（不出库）
    ├── config.json                    # 运行时配置
    ├── sessions/{id}.json             # 对话状态
    ├── archives/sessions/             # 归档会话
    ├── outputs/{name}.md              # 生成结果
    └── templates/
        └── user_templates.json        # 用户自定义模板（内置模板在代码中）
```

---

## 三、模板系统

### 3.1 模板结构

每个模板由四个部分组成：

```
{
  "meta": [...],       // 元数据区 — 短标识信息（标题/作者/单位/文号等）
  "content": [...],    // 内容树区 — 文章正文结构（摘要/引言/方法/结论等）
  "style": "...",      // 风格提示词 — 控制文风语气
  "logic": "..."       // 逻辑提示词 — 控制 LLM 写作认知流程顺序
}
```

**meta 字段**：每条含 name/show_label/desc/source。source 分三类：

| source | 含义 |
|--------|------|
| user | 用户必须填写（如作者、单位、文号） |
| auto | 用户可选填，留空由 LLM 生成（如标题） |
| llm | 由 LLM 生成（如关键词），推荐放 content |

**content 字段**：每条含 name/show_label/desc/type/logical_order。

| type | 含义 |
|------|------|
| leaf | 单段内容，不拆子结构（摘要、关键词、参考文献） |
| section | 需要拆 2-4 个子结构（引言、方法、结果、结论） |

**logical_order**：控制 LLM 写作的认知流程顺序，而非文章最终顺序：

| 值 | 含义 |
|----|------|
| （不设） | 按 content[] 顺序写 |
| 0 | 先写 |
| 1 | 其次写 |
| 2 | 最后写（如摘要、关键词、参考文献需在全文完成后提取） |

### 3.2 内置模板 vs 用户模板

模板分两层存储：

```
内置模板（8个）                   用户模板
config_manager.py 代码常量          data/templates/user_templates.json
  ├── 日常写作                       ├── 法律文书模板 ★
  ├── 学术论文 (IMRaD)               └── （另存为/对话生成创建）
  ├── 正式公文
  ├── 新闻报道
  ├── 技术报告
  ├── 通用公文
  ├── 论文综述
  └── 自定义
```

**行为差异：**

| 操作 | 内置模板 | 用户模板 |
|------|---------|---------|
| 保存 | 禁用（只读） | 可用 |
| 另存为 | 创建副本到 data/templates/ | 创建副本 |
| 删除 | 禁用 | 双击确认后删除 |
| 下拉框标识 | 无标记 | 名称后带 ★ |
| 升级影响 | 不受影响（代码级） | 不受影响（独立文件） |

### 3.3 引用校验

content 字段支持 `citation_check` 和 `citation_format` 配置：

```json
{"name": "参考文献", "type": "leaf", "citation_check": true, "citation_format": "[x]=1."}
```

- `citation_check=true` 时，写作完成后触发引用后处理
- `citation_format` 格式：`[x]=1.` 中 `=` 前为行内标记模板，后为参考文献列表前缀
- 字段名含"参考文献"或"引用"时，`_normalize_template()` 自动设 `citation_check=true`

### 3.4 模板生成（对话生成）

通过 `POST /api/gen-template` 调用 LLM 生成模板。流程：

```
用户描述需求（自然语言）
  ↓
GEN_TEMPLATE_SYSTEM_PROMPT（含 JSON schema + 二分法规则 + 引用规则）
  ↓
LLM 生成 → 多级 JSON 容错解析（最多重试 3 次）
  ↓
_normalize_template() 校验并补默认值
  ↓
存入 data/templates/user_templates.json → 标记为用户模板
```

---

## 四、组件详解

### 4.1 大纲规划器 — `planner.py`

核心是 `plan_outline()` 方法，调用 LLM 根据模板的 meta+content 生成结构化 JSON 大纲。

```
用户主题 + 模板(content) + 已填 meta
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
  - leaf 类型不补子结构
  - section 类型如果 LLM 未生成 sub_sections → 自动补一个默认子结构
  - 补全 id / summary / word_count / _checked / _logical_order 等字段
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
    "_logical_order": 0,
    "sub_sections": [
      {"id": "s1_1", "title": "子标题1", "summary": "...", "word_count": 400, "_checked": true},
      {"id": "s1_2", "title": "子标题2", "summary": "...", "word_count": 400, "_checked": true},
      {"id": "s1_3", "title": "子标题3", "summary": "...", "word_count": 400, "_checked": true}
    ]
  }]
}
```

### 4.2 串行写作器 — `writer.py`

核心是 `generate_article()` 函数，逐节逐子结构串行调用 LLM。

#### 4.2.1 两级 RAG 查询

```
启用了 RAG 的节:
  1. [节级别] query = "{文章标题} {节标题} {节summary}"
     → rag_client.query(kb, query, include_header=needs_metadata)
     → section_rag_context + all_rag_headers（全局累积）
  2. [子结构级别] query = "{节标题} {子结构标题} {子结构summary}"
     → rag_client.query(kb, query, include_header=needs_metadata)
     → sub_rag_contexts[{sub_id}] + all_rag_headers（全局累积）
  3. prompt 装配:
     if 两个 context 都有:
       【引用来源】headers_text（文档元数据）
       ---
       【背景资料】section_rag_context
       ---
       【针对性资料】sub_rag_context
     else if 只有一个:
       直接使用
     else:
       不写参考资料段
```

**all_rag_headers 全局共享机制**：

```
第1节（引言）查RAG → headers = {paper1.pdf: [标题, 作者]}
第2节（方法）查RAG → headers = {paper1.pdf: [...], paper2.pdf: [...]}
...
第N节（参考文献/结论）写的时候 → all_rag_headers 已有全部文档元数据
  → LLM 可以在任何位置引用前面任何节见过的文档
  → 用于 引用自{文件名} 标记
```

语义检索内容（rag_context）逐节独立，文档元数据（headers）全文共享。

#### 4.2.2 引用后处理

写作完成后，如果模板的参考文献字段启用了 `citation_check=true`：

```
1. 正则扫描全文：提取所有 引用自{文件名} 标记
2. 去重：按首次出现顺序编号
3. 替换：引用自{文件名} → [1] [2] ...
4. 构建参考文献节：
   从 all_rag_headers 取文档元数据（标题/作者/单位）
   按编号排列：1. 标题 / 作者 / 单位
   替换 ## 参考文献 节的内容
```

引用标记指令（`引用自{文件名}`）在每节的 prompt 中通过「引用来源」段注入，LLM 无需额外配置就知道使用该格式。

#### 4.2.3 续写机制

```
finish_reason == "stop"  → 正常写完，跳出循环
finish_reason == "length" → token 耗尽:
  content 非空 → 追加 assistant 消息 + "请继续写" → 重试（最多 5 次）
  content 为空  → 推理吃光了 token，放弃续写，跳过
```

#### 4.2.4 错误容错

| 场景 | 行为 |
|------|------|
| LLM 调用异常 | 写入错误提示到正文，标记状态为 error |
| 空内容（推理 token 耗尽） | 跳过该子结构，不影响后续 |
| 全部子结构为空 | 整节跳过，不输出空标题 |
| RAG 超时 | status_text 显示，不污染 prompt |
| RAG 无结果 | status_text 显示，不写参考资料段 |

### 4.3 引用验证 — `citation_validator.py`

独立于写作者，对已完成的文章进行引用一致性校验：

- 扫描正文中的 `[N]` 编号，验证是否连续（无跳号、无重复）
- 验证所有 `[N]` 在参考文献节中都有对应条目
- 输出验证报告，追加到文章末尾

### 4.4 RAG 客户端 — `rag_client.py`

通过 HTTP 调 rag-assistant 的 8767 外部 API，提供 `query(kb, query_text, top_k, include_header)` 方法。

- 内部调用 `POST :8767/api/kb/query`
- `include_header=true` 返回 headers（文档元数据）
- 不消耗额外 LLM token（仅做向量检索）

### 4.5 LLM 客户端 — `llm_client.py`

支持双后端：

| 后端 | 协议 | 接口 | 默认端口 |
|------|------|------|---------|
| LM Studio | HTTP (OpenAI 兼容) | `/v1/chat/completions` | 1234 |
| Ollama | HTTP (Ollama API) | `/api/chat` | 11434 |

**`chat_detailed()`** 方法返回 `{content, finish_reason}`，用于续写检测。

**max_tokens 与 temperature**：从 config.json 读取 `writer_model.max_tokens` / `planner_model.max_tokens` 及 `temperature`，存储为 LLMClient 实例属性。各调用点传 `temperature=None` 走实例属性。

### 4.6 状态管理器 — `state_manager.py`

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

### 4.7 配置管理器 — `config_manager.py`

管理 config.json + data/templates/user_templates.json：

| 功能 | 说明 |
|------|------|
| 配置读写 | 原子写入（tmp → replace），深层合并默认值 |
| 内置模板 | `DEFAULT_TEMPLATES` 代码常量，8 个内置模板，只读 |
| 用户模板 | 存 `data/templates/user_templates.json`，可创建/编辑/删除 |
| 模板合并 | `get_all_templates()` 合并内置+用户，用户覆盖同名内置 |
| 旧格式迁移 | `_migrate_old_templates()` 从 config.json 迁移旧模板到独立文件 |

---

## 五、外部接口

### 5.1 HTTP 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` 或 `/index.html` | GET | 主页面（配置 Tab + 对话 Tab） |
| `/api/config` | GET/POST | 读取/保存配置 |
| `/api/llm/models` | GET | 扫描模型列表 |
| `/api/llm/test` | POST | 测试 LLM 连接 |
| `/api/plan` | POST | 生成/重新规划大纲 |
| `/api/generate` | POST | 启动生成任务 |
| `/api/progress` | GET | 获取生成进度 |
| `/api/result` | GET | 获取最终结果 |
| `/api/stop` | POST | 停止生成（delay/immediate） |
| `/api/sessions` | GET | 会话列表 |
| `/api/session/new` | POST | 新建会话 |
| `/api/session/load` | GET | 加载会话 |
| `/api/session/archive` | POST | 归档会话 |
| `/api/session/restore` | POST | 恢复会话 |
| `/api/session/delete` | POST | 删除会话 |
| `/api/chat` | POST | 对话消息处理（含写作意图检测） |
| `/api/gen-template` | POST | LLM 生成模板 |
| `/api/rag/status` | GET | RAG 连接状态 |
| `/api/rag/start` | POST | 冷启动 RAG |
| `/api/rag/stop` | POST | 停止 RAG（kill 进程树 + 等端口释放） |
| `/api/batch_auto` | POST | 批量自动撰写（多行输入，逐篇执行） |
| `/api/batch_progress` | GET | 批量撰写进度 |
| `/api/outputs` | GET | 已完成文章列表 |
| `/api/outputs/read` | GET | 读取文章内容（?file=xxx.md） |
| `/api/outputs/delete` | POST | 删除文章 |

### 5.2 RAG 外部依赖

| 依赖 | 端口 | 说明 |
|------|------|------|
| rag-assistant 外部 API | 8767 | 知识库查询（/api/kb/query） |
| rag-assistant 冷启动 | 18765 | 子进程 Web UI 端口（冷启动用，不开） |

### 5.3 配置

通过 config.json 或 Web UI 配置 Tab 管理。config.json 不含模板数据：

```json
{
  "planner_model": {"backend": "lmstudio", "model": "", "max_tokens": 4096, "temperature": 0.6},
  "writer_model": {"backend": "lmstudio", "model": "", "max_tokens": 8192, "timeout": 300, "temperature": 0.7},
  "selected_template": "通用公文",
  "rag_path": "",
  "context_review_length": 8000,
  "fact_check_enabled": false,
  "max_sessions": 20
}
```

---

## 六、UI 布局

对话界面为三栏布局：

```
┌──────────┬──────────────────────┬──────────────┐
│ 会话管理  │     对话交互          │ 已完成文章    │
│          │                      │              │
│ [新建]   │  [助手] 欢迎使用...   │ 文件名1      │
│ 会话1    │  主题输入...          │ 文件名2      │
│ 会话2    │  [大纲卡片]           │ 文件名3      │
│ ...      │  ☑ 引言 [重点][RAG]  │ ...          │
│ 归档     │  ☑ 方法              │ (30秒自动刷新)│
│          │  [进度条]             │              │
│          │  [开始生成][重新规划]  │              │
│          │                      │              │
│          └──────────────────────┘              │
│          meta 输入栏（模板驱动）  │              │
│          [标题] [作者] [单位]... │              │
└──────────┴──────────────────────┴──────────────┘
```

### 6.1 meta 输入栏

- 位于输入框上方，由当前选中的模板决定显示哪些字段
- meta 字段在对话开始时自动渲染（不再需要切模板才能看到）
- source=user 字段必须填写，source=auto 字段可选（留空 LLM 生成）

### 6.2 模板编辑器

配置 Tab 中的模板管理区：

- 下拉框选择模板（内置模板无标记，用户模板带 ★）
- 当前选中模板显示 [内置] 或 [���户] 徽章
- 元数据表格：名称/显示标签/字段意义/填写者（user/auto/llm）
- 内容树表格：名称/显示标签/字段意义/子结构类型(leaf/section)/逻辑顺序/引用格式
- 保存按钮（内置模板禁用）、另存为、删除（内置模板禁用）、从对话生成

### 6.3 已完成文章列表

右侧栏显示 `data/outputs/` 下所有 .md 文件：

- 按修改时间倒序排列
- 点击文件名弹出模态框显示全文
- ✕ 按钮确认后删除
- 每 30 秒自动刷新

---

## 七、交互式大纲 UI

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

### 7.1 客户端状态轮询

`startProgressPolling(sid)` 每 1.5 秒 polling `/api/progress`：

```
GET /api/progress?session_id=xxx
  → {"done": 5, "total": 12, "status_text": "RAG查询: 白酒 → 技术演进背景"}
    ↓
前端更新: 进度条百分比 + 状态文本
```

### 7.2 勾选提交

`getOutlineData()` 收集所有卡片状态 → `POST /api/generate` → `_handle_generate` 过滤未勾选项。

---

## 八、写作管线

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
  ├─ 从模板构建 citation_config（citation_check + citation_format）
  ├─ 创建 LLMClient（从配置读取）
  └─ 启动后台线程 _run_generation()
      ↓
generate_article(outline, rag_options, llm_client, state_mgr, rag_client, template, citation_config)
  ├─ 逐节（按 logical_order 排序写作，按 content[] 顺序输出）:
  │   ├─ 节级别 RAG 查询（如果启用）
  │   │   └─ all_rag_headers 累积
  │   ├─ 写入 ## 节标题
  │   └─ 逐子结构:
  │       ├─ 子结构级别 RAG 查询（如果启用）
  │       │   └─ all_rag_headers 累积
  │       ├─ 构建 prompt（引用来源 + 节RAG + 子结构RAG + 前文 + 【事实待核查】标注）
  │       ├─ call LLM → 检测 finish_reason → 续写循环
  │       ├─ 解析 【事实待核查】标记 → 收集到 sub_fact_notes
  │       ├─ 写入 ### 子标题 + 正文（不含标记）
  │       └─ 更新状态（progress + status_text）
  ├─ 引用后处理（如 citation_check=true）:
  │   ├─ 正则扫描 引用自{文件名}
  │   ├─ 去重编号 → 替换为 [N]
  │   └─ 填充参考文献节
  ├─ 追加事实自检汇总表
  ├─ 引用验证（如启用）: citation_validator
  ├─ 写入 .md → data/outputs/{timestamp}_{title}.md
  └─ 更新 phase="done"
```

### Prompt 结构

```
# 文章主题

{title}

写作阶段提示：
{logic_hint}

【全文风格背景】（仅作为整体行文风格参考）
{style_hint}

【前文回顾】（已完成的内容，用于了解文章逻辑走向，不要重复书写）
{context_buffer}

【当前章节要求】
字数要求：约 {word_count} 字
写作要点：
{section_summary}

【引用来源】（正文引用时使用「引用自{文件名}」格式标注，如「引用自paper1.pdf」）：
doc1.pdf: 标题 / 作者 / 单位
doc2.pdf: 标题 / 作者 / 单位

【背景资料】（本节整体相关）
{section_rag_context}

【针对性资料】（针对当前子结构）
{sub_rag_context}

请写出该节正文（Markdown 格式）。只输出正文，不输出标题行。

写完后，在末尾另起一行用「【事实待核查】」标注本节中你
不确定准确性的数据、前沿信息或案例。
如果没有需标注的内容，写「【事实待核查】无」。
```

---

## 九、版本演进要点

| 版本 | 新增/变更要点 |
|------|-------------|
| v1.1.0b9 | 模板存储分离（内置代码级只读 + 用户 data/）、引用校验字段、IMRaD 内置模板结构、三栏布局+已完成文章列表、meta 输入栏自动加载、gen-template 增加引用规则、内置模板只读保护 |
| v1.0.28 | 事实自检内嵌标记法（零额外 LLM 调用）、temperature 可配置、RAG 停止、模型下拉框修复、子结构字数联动、大纲过滤同步进度、批量自动撰写、会话归档、深层合并 DEFAULT_CONFIG |
| v0.2.5b4 | PyPI long_description 修复（同步 CHANGELOG） |
| v0.2.5b3 | PyPI 发布准备：`app/`→`structured_writer/` + LICENSE + README + blueprint + Actions 检测 |
| v0.2.5b2 | 两级 RAG、实时状态显示、子结构摘要 UI、错误不注入 prompt |
| v0.2.5b1 | 子结构系统、大纲勾选/取消、双级排序、续写机制、RAG 对接、LLMClient max_tokens 存储 |
| v0.1.0 | 项目骨架、LLM 客户端、会话管理、大纲规划器、串行写作器、异步生成、进度轮询 |

---

*最后更新：2026-07-29*
