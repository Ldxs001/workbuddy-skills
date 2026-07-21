
# RAG Assistant 架构文档

> 独立 RAG 智能体 — LLM 驱动的组合式语义检索与多库路由。
> 作者：[username-redacted] | 许可证：Apache 2.0
> 更新：2026-07-21 (v1.7.0)

---

## 一、系统概览

RAG Assistant 是一个**本地知识库问答智能体**，基于 local-rag-builder 技能构建，核心理念是从传统单轮问答升级为 **LLM 驱动的组合式检索**：

```
用户输入
  → [LLM 决策层]
       ├─ 闲聊 → 直接回答
       └─ 知识库查询 → entities/attrs 分词
           → [组合展开器] 穷举 entities × attrs
           → [多切片检索] 每片独立走完整 RAG 流程
              1. 路由（route_query → 嵌入模型 × KB签名/关键词）
              2. 检索（retrieve_documents → Chroma 相似度）
              3. (可选) 重排序（reranker）
              4. (可选) NLI 三向分类（entailment/neutral/contradiction）
              5. 构建上下文（build_context，含 NLI 标签渲染）
           → [SM3 去重合并] 按内容哈希去重
           → [LLM 综合回答] 基于完整上下文生成回答
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **LLM 分词 > 规则分词** | 实体/属性由 LLM 基于语义标注，不依赖关键词规则 |
| **穷举 > 猜测** | 所有 entities × attrs 组合都查一遍，不预判哪组最优 |
| **去重 > 冗余** | SM3 国密哈希按内容去重，避免重复上下文浪费 token |
| **自修正 > 静默丢弃** | LLM 格式错误时反馈重试（最多 5 次），不静默吞掉 || **技能完整走 > 绕路** | 每片独立走 route_query → retrieve_documents → reranker → build_context 全流程，不改造技能内部逻辑 |
| **配置持久化 > 运行时内存** | 所有 LLM 配置（backend/model/timeout/max_tokens）写入 config.json，刷新页面不丢 |

### 1.2 路由开关行为

| 开关 | 控制 | 开 | 关 |
|------|------|----|----|
| `kb.enabled` | 多知识库路由主开关 | 允许入库/出库路由工作 | 全部路由失效，全进 default |
| `kb.auto_classify` | 入库路由 | 向量模型余弦相似度匹配最佳 KB | 纯关键词匹配，无匹配进 default |
| `router.enabled` | 出库路由 | 嵌入模型 × KB签名关键词（精排开）或 × 规则关键词（精排关）。精排关时不写 KB 签名 | 纯关键词匹配，不写 KB 签名 |

---

## 二、三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | `web_ui.py` (port 8765) / `external_api.py` (port 8767) / RAG 配置页 subprocess (port 8766) | Web 界面、外部接入 API、RAG 配置页、聊天界面、模型管理 |
| **业务层** | `agent.py` / `rag_wrapper.py` / `scripts/rag_core.py` / `scripts/router.py` | 决策循环、组合查询、路由/检索/重排序 |
| **基础设施** | `llm_client.py` / `scripts/config.py` / `scripts/utils.py` / `data/` | LLM 通信、配置管理、数据持久化 |

### 2.1 文件结构

```
agent/rag-assistant/
├── main.py                          # 入口
├── setup.bat                        # Windows 一键启动
├── requirements.txt                 # 依赖清单
├── CHANGELOG.md                     # 版本更新日志
├── PROTOCOL.md                      # Web UI 接入协议规范（HTTP/CLI/文件交互，port 8765）
├── EXTERNAL_API.md                  # 外部接入 API 协议（组件级能力调用，port 8767）
├── llms.txt                         # AI 可读的项目自描述文档（llmstxt.org）
├── .gitignore
│
├── rag_assistant/                   # 智能体核心
│   ├── agent.py                     # Agent 决策循环（~900 行）
│   ├── web_ui.py                    # Web 界面（port 8765）
│   ├── external_api.py              # 外部接入 API（port 8767）
│   ├── llm_client.py                # LLM 统一客户端
│   ├── rag_wrapper.py               # RAG 封装层
│   ├── search.py                    # 联网搜索
│   ├── memory.py                    # 记忆管理
│   └── _fix_rag.py                  # 破损数据修复工具
│
├── rag_assistant/engine/            # local-rag-builder 技能核心（独立副本）
│   ├── rag_core.py                  # RAG 核心：检索/嵌入/导入
│   ├── router.py                    # 路由层
│   ├── reranker.py                  # 重排序
│   ├── knowledge_base_manager.py    # 知识库管理
│   ├── config.py                    # 配置管理
│   ├── embedding_model_manager.py   # 模型下载管理
│   ├── nli_classifier.py              # NLI 三向分类器（v0.9.0 新增）
│   ├── rag_skill.py                 # 技能接口
│   ├── rag_standalone.py            # 独立模式
│   ├── rag_web_ui.py                # RAG 配置页
│   ├── rag_setup_orchestrator.py    # 搭建编排器
│   ├── rag_env_setup.py             # 环境检测
│   ├── text_splitter.py             # 文本切分
│   ├── prompt_manager.py            # Prompt 管理
│   └── utils.py                     # 工具函数
│
├── vendor/                          # Vendored 第三方库
│
└── data/                            # 运行时数据
    ├── config/rag_config.json       # LLM 与检索配置
    ├── models/                      # 嵌入/路由/rerank 模型
    ├── kb/                          # 知识库（Chroma 向量库）
    ├── sessions/                    # 会话历史
    ├── memory/                      # 记忆数据
    ├── prompts/                     # 提示词模板
    ├── import_manifest.json          # 待入库文件清单
    ├── imports/                      # 浏览器上传临时目录（入库后自动清理）
    └── cache/                       # 缓存
```

---

## 三、组件详解

### 3.1 决策循环 — `agent.py`

核心是 `_decide_with_retry()` 方法，实现 **LLM 决策 → 解析 → 校验 → 自修正** 闭环。第一轮决策（`_build_first_pass_messages`）**不传完整历史对话**，仅传压缩摘要作为 system context，避免上一轮查询 entities 泄漏到当前决策：

```
LLM 输出
  → _parse_action()
       ├─ 无 <<ACTION 标记 → 直接聊天
       ├─ 有标记但格式错 → 返回错误原因 → 追加到 messages → LLM 修正重试
       └─ 解析成功 → 进入 _validate_action()
  → _validate_action()
       ├─ 参数缺失 → 返回拒绝原因 → LLM 修正重试（最多 5 次）
       ├─ 非法操作 → 同
       └─ 校验通过 → 执行
  → 重试耗尽 → 清上下文，全新 prompt 重新回答
```

#### _parse_action

从 LLM 输出中提取 `<<ACTION type="..." ...>>` 指令，返回 `(params_dict, error_msg)` 二元组：

解析器使用**状态机逐字符扫描**，而非正则表达式，以解决两个实际痛点：

1. **Windows 路径兼容**：`C:\Users\...` 中的反斜杠不会被当作转义前缀，`\U` 不被解释为 Unicode 序列
2. **文件名含引号**：仅 `\"` 和 `\\` 视为转义，其他 `\X` 保持字面量，支持 `尊"礼"与崇"力".pdf` 这类文件名

返回格式：
- `(None, None)` — 无动作标记，正常聊天
- `(None, "原因")` — 有 `<<ACTION` 但格式错误
- `({...}, None)` — 解析成功

#### 组合查询

当 LLM 输出 `type="query"` 时触发组合查询：

```python
# LLM 输出示例
<<ACTION type="query" entities="三个代表重要思想,老子无为而治"
                     attrs="核心观点,相同点,不同点"
                     rel="思想渊源比较">>

# Agent 自动展开为：
slices = [
    "三个代表重要思想 核心观点",
    "三个代表重要思想 相同点",
    "三个代表重要思想 不同点",
    "老子无为而治 核心观点",
    "老子无为而治 相同点",
    "老子无为而治 不同点",
    "三个代表重要思想 老子无为而治 核心观点",
    "三个代表重要思想 老子无为而治 相同点",
    "三个代表重要思想 老子无为而治 不同点",
    "三个代表重要思想 老子无为而治 思想渊源比较",
]

# 生成逻辑：
# 1. 每个 entity × 每个 attr
# 2. 如果有 ≥2 个 entity: entities 联合 × 每个 attr
# 3. 如果有 ≥2 个 entity + rel: entities 联合 × rel
```

每片独立走 `rag.query()` 完整流程，结果按 SM3 内容哈希去重后合并为单一上下文，交给 LLM 生成最终回答。

### 3.2 LLM 客户端 — `llm_client.py`

支持双后端，统一返回 `{text, reasoning, raw}`：

| 后端 | 协议 | 接口 | 模型参数 |
|------|------|------|---------|
| LM Studio | HTTP (OpenAI 兼容) | `/v1/chat/completions` | `max_tokens` / `temperature` |
| Ollama | HTTP (Ollama API) | `/api/chat` | `num_predict` / `temperature` |

两个后端都从响应中提取 `reasoning_content`（思考链），透传到前端折叠显示。

**模型发现**：调用 `/v1/models`（LM Studio）或 `/api/tags`（Ollama）列出可用模型，供前端下拉框选择。

### 3.3 Web 界面 — `web_ui.py`

基于 Python `http.server` 的单文件 Web 界面（port 8765），无外部框架依赖。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页面（LLM 配置栏 + 聊天窗口 + RAG 配置 iframe） |
| `/api/chat` | POST | 聊天接口，转发到 agent.chat() |
| `/api/config/llm` | GET | 返回当前 LLM 配置（backend/model/max_tokens/timeout） |
| `/api/config/llm` | POST | 保存 LLM 配置到 config.json 并同步运行时 |
| `/api/llm/models` | GET | 扫描后端可用模型列表 |
| `/api/llm/test` | GET | 测试 LLM 连接 |
| `/api/kbs/list` | GET | 知识库列表 |
| `/api/agent/import` | POST | 导入文件/文本到知识库 `{"path"}` / `{"content", "title"}` |
| `/api/agent/upload-files` | POST | 浏览器上传文件到服务器临时目录 `{"name", "data(base64)"}` |
| `/api/memory/inject` | POST | 向 session 注入系统通知（不触发 LLM）`{"text"}` |
| `/api/memory/reset` | POST | 重置对话历史 |
| `/api/search/toggle` | POST | 联网搜索开关 `{"enabled"}` |

**关键交互细节**：
- `loadModels()` 在页面加载后 500ms 触发，填充模型下拉框
- 配置保存后立即同步到 `self.agent.llm.*` 运行时实例
- `llm_max_tokens` 和 `llm_timeout` 持久化到 `config.json`

**文件上传流程**：点击 `📄` 或 `📁` 按钮选择文件后，文件以 base64 二进制上传到服务器 `data/imports/` 目录并记录到 `import_manifest.json`，同时聊天框出现系统通知。用户输入"入库"后 LLM 发出 `path="MANIFEST"` 指令，系统读取清单逐个走完整导入管线（PyPDFLoader → OCR 回退 → 自动路由 → 切片 → 嵌入）。

**PDF 导入**：多页 PDF 合并全部页内容后切分（`"\n\n".join(d.page_content for d in docs)`），不再仅取第 1 页。OCR 回退条件：`total_chars < 50`（扫描版 PDF 无文本层）无条件触发；`total_chars >= 50` + 中文文件名 + CJK 占比 < 10% 也触发（编码乱码检测）。英文正常 PDF 不走 OCR。

### 3.4 RAG 封装层 — `rag_wrapper.py`

将 local-rag-builder 的技能接口包装为 Agent 可调用的形式：

```python
rag.query(question, kb_name=None, k=5, score_threshold=0.0)
  → retrieve_context(question, kb_name, k, score_threshold)
    → route_query(question)                 # 路由：哪个知识库？
      → retrieve_documents(question, kb)    # 检索：取 top-K chunk
        → (可选) reranker.rerank(docs)       # 精排
      → (可选) nli_classifier.classify(docs) # NLI 三向标注
      → build_context(docs)                 # 构建上下文（含 NLI 标签）
  → return {context, docs, kb, has_context}
```

不改造技能内部的任何逻辑，完整走 `scripts/rag_core.py` → `router.py` → `reranker.py` 流程。

### 3.5 搜索模块 — `search.py`

可选的联网搜索插件，通过 `web_search_enabled` 配置开关。支持 5 种后端：DuckDuckGo（免费，默认）、Tavily、Google Custom Search、Bing Search、自定义 API。返回统一格式 `{"results": [{"title", "url", "snippet"}], "success"}`。

---

### 3.6 引用校验 — `agent.py`

v0.8.0 新增：LLM 回答后校验引用编号。第二轮系统提示强制要求：
- 每个具体事实/数字后面标注来源段落编号 `[n]`
- LLM 回答后提取所有 `[n]` 引用，检查编号是否在资料段落范围内
- 不存在的段落编号 → 告警追加到回答尾部
- 无引用 → 记录日志（不作为错误）

---

### 3.7 KB 暂停写入

v0.8.0 新增：配置页自动分类规则表格每行增加暂停/恢复按钮。

| 场景 | 行为 |
|------|------|
| 自动路由入库 | `auto_classify()` 从 rules 中过滤掉 `kb_paused` 列表中的 KB，文件自动路由到次高分的非暂停 KB |
| 用户指定入库 | `add_documents_to_kb()` 拒绝写入，提示"已暂停，请恢复或选其他 KB" |
| 查询/检索 | 完全不受影响 |
| 恢复暂停 | 再次点击按钮，KB 恢复为可写入，路由重新考虑 |

配置存储：`rag_config.json` 的 `kb_paused` 数组。

---

## 四、记忆系统 — `memory.py`

记忆系统是 Agent 维持对话连续性的核心，统一管理short-termsession、压缩摘要、知识缺口和用户习惯。

### 4.1 短期记忆

| 方法 | 功能 | 存储 |
|------|------|------|
| `append_short_term(session_id, role, content)` | 追加一条对话记录 | `data/sessions/{session_id}.txt` |
| `get_short_term(session_id)` | 读取完整对话历史 | 返回 `str` |
| `clear_short_term(session_id)` | 清空对话历史 | 删除文件 |
| `pop_oldest_lines(session_id, n)` | 弹出最旧的 N 行（用于压缩） | 返回被移除的文本 |
| `short_term_line_count(session_id)` | 当前行数 | 返回 `int` |
| `needs_compression(session_id)` | 行数 > 100 触发压缩开关 | 返回 `bool` |

当 `needs_compression()` 返回 True 时触发压缩流程（阈值：token 数 > `max_tokens × threshold_ratio`，默认 4096 × 0.7 ≈ 2867 tokens）：
- `pop_oldest_lines()` 按比例取出最旧 40% 对话 → 调 LLM 压缩为摘要（压缩指令结构化要求保留核心需求、已得结论、追问方向、最近 3 条原文） → `store_compressed()` 存入长时记忆

### 4.2 长时记忆（压缩摘要）

| 方法 | 功能 | 存储 |
|------|------|------|
| `store_compressed(session_id, summary)` | 追加一条压缩摘要 | `data/memory/compressed_{session_id}.txt` |
| `get_compressed(session_id, limit=3)` | 返回最近 N 条摘要 | 返回 `str`（多摘要拼接） |

Agent 每次调用 LLM 前通过 `build_context()` 拼接长时摘要 + 近期对话：

```python
def build_context(self, session_id="default"):
    compressed = self.get_compressed(session_id)
    recent = self.get_short_term(session_id)
    # 拼接格式
```

### 4.3 知识缺口记录 — `record_gap` / `get_gaps`

记录检索不到答案的查询，分析知识库覆盖盲区：

```json
{
  "query": "三个代表与老子无为而治的相同点",
  "kb": "政经文哲",
  "count": 3,
  "first_seen": "2026-07-08T04:20:13",
  "last_seen": "2026-07-08T04:25:27"
}
```

保留最近 200 条，相同 query 自动累加计数。

### 4.4 用户习惯记录 — `record_habit` / `get_habits`

```json
{
  "total_queries": 42,
  "rag_queries": 35,
  "chat_ratio": 0.17,
  "import_events": 2,
  "recent_rag_queries": ["...", "..."],
  "last_active": "2026-07-08T05:00:00"
}
```

### 4.5 与 Agent 的集成

Agent 的 `chat()` 入口自动处理记忆：

```
chat(message)
  ↓
append_short_term("default", message)    # 写入用户输入
  ↓
_build_first_pass_messages(message)      # 第一轮决策：不传完整历史
  ├─ system prompt（含动作格式说明）
  ├─ 压缩摘要作为 system context（【历史对话，仅作参考】）
  ├─ 用户画像提示（可选）
  └─ 当前消息作为 user message
  ↓
LLM 决策（query/search/import/直接回答）
  ↓
执行动作
  ↓
append_short_term("default", reply)      # 写入助手回复（自动剥离 <<ACTION>> 标签）
record_habit(message, is_rag, ...)       # 记录习惯
↓ 如果检索结果为空
record_gap(query, kb)                    # 记录知识缺口
```

**历史隔离**（v0.8.0）：第一轮决策不传完整历史对话，仅传压缩摘要作为 system context。避免上一轮的 entities 泄漏到当前决策。第二轮 `_second_pass()` 仍携带带 `[历史对话]` 前缀的历史消息，保证跨轮追问的上下文连贯性。

**ACTION 剥离**（v0.8.0）：写入记忆时自动使用 `re.sub(r'<<ACTION\s+.*?>>', '', content)` 剥离内部指令标签，记忆文件只有纯对话内容，不残留系统内部指令。

---

## 五、外部接口

### 5.1 Python 编程接口（API）

| 类 | 入口方法 | 返回格式 |
|----|---------|---------|
| `Agent` | `.chat(message) → dict` | `{"text", "success", "reasoning", "kb", ...}` |
| | `.reset_session()` | 无返回值 |
| `Memory` | `.get_short_term(id) → str` | 对话历史文本 |
| | `.append_short_term(id, role, content)` | 无返回值 |
| | `.get_gaps(min_count) → list[dict]` | `[{"query", "kb", "count", ...}]` |
| | `.get_habits() → dict` | `{"total_queries", "chat_ratio", ...}` |
| `LLMClient` | `.chat(messages) → dict` | `{"text", "reasoning", "raw"}` |
| | `.list_models() → list[str]` | 模型名列表 |
| | `.check_health() → bool` | 连接状态 |
| `RAGWrapper` | `.query(question, kb_name) → dict` | `{"context", "docs", "kb", "has_context"}` |
| | `.import_file(path, kb_name) → dict` | `{"success", "doc_count", "kb"}` |
| | `.import_text(text, kb_name, title) → dict` | `{"success", "doc_count", "kb"}` |
| | `.list_kbs() → dict` | 知识库字典 |
| `WebSearch` | `.search(query, max_results) → dict` | `{"results": [{"title", "url", "snippet"}], "success"}` |

### 5.2 HTTP REST API（web_ui.py, port 8765）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 主页面 HTML |
| GET | `/api/config` | 读取全局配置 |
| GET | `/api/kbs` | 知识库列表 |
| GET | `/api/llm/models?backend=xxx` | 扫描模型列表 |
| GET | `/api/llm/test` | 测试 LLM 连接 |
| GET | `/api/config/llm` | 读取 LLM 配置 |
| GET | `/api/config/query_types` | 查询类型参考 |
| GET | `/api/config/memory` | 读取记忆配置 |
| GET | `/api/config/search` | 读取搜索配置 |
| GET | `/api/chat/history` | 当前会话历史 |
| GET | `/api/agent/gaps` | 知识缺口 |
| GET | `/api/agent/query?q=&kb=` | 查询知识库 |
| GET | `/api/chat?q=` | 对话（GET） |
| GET | `/api/memory/reset` | 重置对话 |
| POST | `/api/chat` | 对话（POST）`{"message": "..."}` |
| POST | `/api/agent/query` | 查询 `{"message", "kb"}` |
| POST | `/api/agent/import` | 导入 `{"path"}` 或 `{"content", "title", "kb"}` |
| POST | `/api/agent/upload-files` | 上传文件到服务器临时目录 `{"name", "data(base64)"}` |
| POST | `/api/memory/inject` | 注入系统通知 `{"text"}` |
| POST | `/api/memory/compress` | 手动压缩记忆 |
| POST | `/api/memory/clear-context` | 清除上下文 |
| POST | `/api/config/llm` | 更新 LLM 配置 `{"backend", "model", "timeout", "maxtokens"}` |
| POST | `/api/config/query_types` | 添加/编辑/删除查询类型 |
| POST | `/api/config/memory` | 更新记忆配置 |
| POST | `/api/config/search` | 更新搜索配置 |
| POST | `/api/search/toggle` | 搜索开关 `{"enabled"}` |
| GET/POST | `/api/session/new` | 新建会话 |
| GET/POST | `/api/session/list` | 列出会话 |
| GET/POST | `/api/session/switch` | 切换会话 |
| GET/POST | `/api/session/archive` | 归档会话 |
| GET/POST | `/api/session/restore` | 恢复归档 |
| GET/POST | `/api/session/delete` | 永久删除会话 |

所有 POST 接口接受 `Content-Type: application/json`，返回 `{"success": True/False, ...}`。

### 5.2b 外部接入 API（external_api.py, port 8767）

独立端口，专供外部系统作为组件调用。27 个端点覆盖：

| 域 | 端点 | 说明 |
|----|------|------|
| 健康检查 | `GET /api/health` | 服务状态 |
| 功能开关 | `GET /api/feature/status` | 查询开关状态 |
| | `POST /api/feature/toggle` | 运行态切换路由/reranker/NLI/搜索 |
| 模型调用 | `POST /api/model/embed` | 直接调用嵌入模型 |
| | `POST /api/model/rerank` | 直接调用 Reranker |
| | `POST /api/model/nli` | 直接调用 NLI 分类器 |
| KB 管理 | `GET /api/kb/list` | 列出知识库 |
| | `POST /api/kb/create` | 创建知识库 |
| | `POST /api/kb/delete` | 删除知识库 |
| | `GET /api/kb/sources?kb=` | 列出 KB 内文档来源 |
| | `POST /api/kb/move` | 跨库移动文档 |
| | `POST /api/kb/backup` | 手动备份 |
| | `GET /api/kb/backups?kb=` | 列出备份 |
| | `POST /api/kb/restore` | 恢复备份 |
| KB 签名 | `GET /api/kb/signatures` | 列出所有签名 |
| | `POST /api/kb/signature/build` | 构建单个 KB 签名 |
| | `POST /api/kb/signature/rebuild-all` | 全量重建 |
| 提示词 | `GET/POST /api/prompt/template` | 模板读写 |
| | `POST /api/prompt/template/reset` | 重置模板 |
| | `GET/POST /api/prompt/slots` | 插槽读写 |
| | `GET /api/prompt/presets` | 预设列表 |
| | `POST /api/prompt/preset` | 保存自定义预设 |
| | `POST /api/prompt/preset/delete` | 删除预设 |
| | `POST /api/prompt/preset/apply` | 应用预设 |
| | `GET/POST /api/prompt/system-prefix` | 系统前缀读写 |
| 输入管理 | `GET /api/input/strategies` | 切分策略列表 |
| | `POST /api/input/split` | 文本切分 |
| | `POST /api/input/query-slices` | 问题组合切片展开 |

详见 `EXTERNAL_API.md`。

### 5.3 LLM 后端协议

| 后端 | 端点 | 本地端口 | 请求字段 | 响应字段 |
|------|------|---------|---------|---------|
| LM Studio | POST `/v1/chat/completions` | 1234 | `model`, `messages`, `max_tokens`, `temperature` | `choices[0].message.content`, `choices[0].message.reasoning_content` |
| Ollama | POST `/api/chat` | 11434 | `model`, `messages`, `options.num_predict`, `options.temperature` | `message.content`, `message.reasoning_content` |

### 5.4 Agent 动作协议（LLM ↔ Agent 通信）

LLM 在回复中嵌入 `<<ACTION ...>>` 标记控制 Agent 行为：

```python
<<ACTION type="query" entities="实体1,实体2" attrs="属性A,属性B" rel="关系词" kb="知识库名">>
<<ACTION type="search" query="搜索词">>
<<ACTION type="import" content="入库的完整文本内容">
<<ACTION type="import" path="MANIFEST">        # 批量导入所有待入库文件
```

解析结果：`_parse_action(reply) → (params_dict, error_msg)`
- `(None, None)` — 无动作，正常聊天
- `(None, "原因")` — 格式错误，返回给 LLM 修正
- `({...}, None)` — 解析成功，进入校验执行

### 5.5 搜索引擎协议

| 引擎 | 方式 | API Key |
|------|------|---------|
| DuckDuckGo | `requests.get(html.duckduckgo.com/html/)` | 无需 Key |
| Tavily | `POST api.tavily.com/search` | 需配置 Key |
| Google Custom Search | `GET www.googleapis.com/customsearch/v1` | 需配置 Key + CX |
| Bing Search | `GET api.bing.microsoft.com/v7.0/search` | 需配置 Key |
| 自定义 | 用户自定义 URL | 可选 |

### 5.6 技能依赖接口

RAG Assistant 通过 `rag_wrapper.py` 封装以下技能模块，不改造内部逻辑：

| 技能模块 | 导入函数 | 用途 |
|---------|---------|------|
| `rag_core` | `retrieve_context` | 检索主入口（路由→检索→reranker→build） |
| `rag_core` | `get_embeddings` | 嵌入模型管理 |
| `knowledge_base_manager` | `list_knowledge_bases` | 知识库枚举 |
| `knowledge_base_manager` | `_load_rules` / `auto_classify` | 入库路由：`_load_rules` 列出各 KB 关键词做嵌入余弦相似度（`kb.auto_classify` 开时）；出库路由：`auto_classify` 做第一层硬编码匹配，未命中时走嵌入模型 × KB 签名关键词或规则关键词（`router.enabled` 开时，具体取决于精排开关）。`kb.enabled` 关时全部路由失效，全进 default
| `config` | `load_config / save_config` | 配置持久化 |
| `prompt_manager` | `get_full_prompt` | Prompt 模板 |
| `nli_classifier` | `NLIClassifier.classify` | NLI 三向分类（v0.9.0 新增） |

---

## 六、流程详解

### 6.1 完整请求生命周期

```
用户发送消息
  ↓
web_ui.py → POST /api/chat
  ↓
agent.chat(message)
  ↓
_build_first_pass_messages(message)
  ├─ system prompt（含 entities/attrs 格式说明）
  └─ user message
  ↓
LLM 首次推理
  ↓
_parse_action(reply)
  ├─ 无 <<ACTION → 直接聊天回复
  └─ 解析成功 → _validate_action()
       ↓
       ↓ 通过
       ↓
       → type == "query"
         → _exec_query(entities, attrs, rel, kb)
           → 展开组合切片
           → for each slice:
                rag.query(slice, kb_name)
                  → retrieve_context(slice, ...)
                    → route_query → retrieve_documents → (reranker) → (NLI) → build_context
           → SM3 去重合并
           → return {context, docs, kb}
         → _second_pass(message, context, action)
           → LLM 基于上下文生成回答
       → type == "import"
         → path == "MANIFEST"
           → 读取 import_manifest.json → 逐个 import_file()
         → path == 具体路径
           → rag.import_file(path)
         → 含 content
           → rag.import_text(content)
       ↓
回答返回前端
```

### 6.2 自修正循环

```
LLM 输出
  ↓
_parse_action
  ├─ (None, None) → 正常聊天 ✅
  ├─ (None, "错误原因") → 追加到 messages → LLM 修正重试
  └─ ({...}, None) → _validate_action
       ↓ 通过 ✅ → 执行
       ↓ 拒绝 → 追加到 messages → LLM 修正重试
  ↓
5 次重试耗尽
  ↓
全新 system + user prompt 重新回答（不污染上下文）
```

### 6.3 SM3 去重策略

组合切片检索到的 docs 在合入最终上下文前，按内容做 SM3 哈希去重：

```python
seen = set()
for doc in all_docs:
    content = doc.page_content
    h = sm3(content.encode("utf-8"))
    if h not in seen:
        seen.add(h)
        unique_docs.append(doc)
```

同一段内容被多个组合切片命中时只保留一份，避免上下文膨胀。

---

## 七、与 Orchestrator 的关系

| 维度 | RAG Assistant | Orchestrator |
|------|---------------|-------------|
| **定位** | 特定领域智能体（知识库问答） | 通用技能编排框架 |
| **执行模式** | 独立运行，单任务 | 编排流水线，多技能协作 |
| **外部依赖** | local-rag-builder 技能 | workbuddy-skills 任意技能 |
| **LLM 角色** | 决策 + 分词 + 综合回答 | 粘合剂（格式转换） |
| **接口** | Web UI (port 8765) | tkinter GUI |
| **配置** | config.json + RAG 配置页 | AgentConfig |

两者可联合使用：Orchestrator 编排流水线中将 RAG Assistant 作为知识库查询节点调用。

---

## 八、部署与启动流程

```
setup.bat
  ↓
1. python --version 检查
2. pip install -r requirements.txt（首次装依赖）
  ↓
python main.py
  ↓
1. 初始化 Agent（创建 LLMClient + RAGWrapper）
2. 启动 Web UI（port 8765）
3. 启动 RAG 配置页 subprocess（port 8766）
4. 打开浏览器 http://localhost:8765
```

---

## 九、安全与隐私

- **无外部调用**：所有 LLM 请求发向本地 LM Studio / Ollama，不上传数据
- **本地知识库**：Chroma 向量库存储在本地 `data/kb/`，不离开用户机器
- **联网搜索可选**：默认关闭，需用户手动启用
- **模型本地加载**：嵌入模型/路由模型通过本地磁盘加载，不依赖外部 API
