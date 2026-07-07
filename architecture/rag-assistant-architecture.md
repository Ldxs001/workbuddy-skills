
# RAG Assistant 架构文档

> 独立 RAG 智能体 — LLM 驱动的组合式语义检索与多库路由。
> 作者：wUwproject | 许可证：Apache 2.0
> 更新：2026-07-08

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
              1. 路由（route_query → 硬编码/语义/FallbackRouter）
              2. 检索（retrieve_documents → Chroma 相似度）
              3. (可选) 重排序（reranker）
              4. 构建上下文（build_context）
           → [SM3 去重合并] 按内容哈希去重
           → [LLM 综合回答] 基于完整上下文生成回答
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **LLM 分词 > 规则分词** | 实体/属性由 LLM 基于语义标注，不依赖关键词规则 |
| **穷举 > 猜测** | 所有 entities × attrs 组合都查一遍，不预判哪组最优 |
| **去重 > 冗余** | SM3 国密哈希按内容去重，避免重复上下文浪费 token |
| **自修正 > 静默丢弃** | LLM 格式错误时反馈重试（最多 5 次），不静默吞掉 |
| **技能完整走 > 绕路** | 每片独立走 route_query → retrieve_documents → reranker → build_context 全流程，不改造技能内部逻辑 |
| **配置持久化 > 运行时内存** | 所有 LLM 配置（backend/model/timeout/max_tokens）写入 config.json，刷新页面不丢 |

---

## 二、三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | `web_ui.py` (port 8765) / RAG 配置页 subprocess (port 8766) | Web 界面、LLM 配置面板、聊天界面、模型管理、知识库配置 |
| **业务层** | `agent.py` / `rag_wrapper.py` / `scripts/rag_core.py` / `scripts/router.py` | 决策循环、组合查询、路由/检索/重排序 |
| **基础设施** | `llm_client.py` / `scripts/config.py` / `scripts/utils.py` / `data/` | LLM 通信、配置管理、数据持久化 |

### 2.1 文件结构

```
rag-assistant/
├── main.py                          # 入口
├── setup.bat                        # Windows 一键启动
├── requirements.txt                 # 依赖清单
├── .gitignore
│
├── rag_assistant/                   # 智能体核心
│   ├── agent.py                     # Agent 决策循环（~430 行）
│   ├── web_ui.py                    # Web 界面（port 8765）
│   ├── llm_client.py                # LLM 统一客户端
│   ├── rag_wrapper.py               # RAG 封装层
│   ├── search.py                    # 联网搜索
│   └── memory.py                    # 记忆管理
│
├── scripts/                         # local-rag-builder 技能核心
│   ├── rag_core.py                  # RAG 核心：检索/嵌入/导入
│   ├── router.py                    # 路由层
│   ├── reranker.py                  # 重排序
│   ├── knowledge_base_manager.py    # 知识库管理
│   ├── config.py                    # 配置管理
│   ├── embedding_model_manager.py   # 模型下载管理
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
    └── cache/                       # 缓存
```

---

## 三、组件详解

### 3.1 决策循环 — `agent.py`

核心是 `_decide_with_retry()` 方法，实现 **LLM 决策 → 解析 → 校验 → 自修正** 闭环：

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
| `/api/kbs/import` | POST | 导入文件到知识库 |
| `/api/import/file` | POST | 上传文件入库 |
| `/api/import/folder` | POST | 上传文件夹入库 |
| `/api/memory/reset` | POST | 重置对话历史 |

**关键交互细节**：
- `loadModels()` 在页面加载后 500ms 触发，填充模型下拉框
- 配置保存后立即同步到 `self.agent.llm.*` 运行时实例
- `llm_max_tokens` 和 `llm_timeout` 持久化到 `config.json`

### 3.4 RAG 封装层 — `rag_wrapper.py`

将 local-rag-builder 的技能接口包装为 Agent 可调用的形式：

```python
rag.query(question, kb_name=None, k=5, score_threshold=0.0)
  → retrieve_context(question, kb_name, k, score_threshold)
    → route_query(question)                 # 路由：哪个知识库？
      → retrieve_documents(question, kb)    # 检索：取 top-K chunk
        → (可选) reranker.rerank(docs)       # 精排
      → build_context(docs)                 # 构建上下文
  → return {context, docs, kb, has_context}
```

不改造技能内部的任何逻辑，完整走 `scripts/rag_core.py` → `router.py` → `reranker.py` 流程。

### 3.5 搜索模块 — `search.py`

可选的联网搜索插件，通过 `web_search_enabled` 配置开关。使用 DuckDuckGo 等免费搜索 API，返回网页摘要作为补充上下文。

---

## 四、外部接口

### 4.1 LLM 后端接口

#### 请求格式（统一转换为后端对应协议）

| 场景 | 协议 | 端点 |
|------|------|------|
| LM Studio 聊天 | HTTP POST | `http://localhost:1234/v1/chat/completions` |
| Ollama 聊天 | HTTP POST | `http://localhost:11434/api/chat` |
| LM Studio 模型列表 | HTTP GET | `http://localhost:1234/v1/models` |
| Ollama 模型列表 | HTTP GET | `http://localhost:11434/api/tags` |

**请求体格式**（以 LM Studio 为例）：
```json
{
  "model": "qwen/qwen3.5-35b-a3b",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "max_tokens": 40960,
  "temperature": 0.7,
  "stream": false
}
```

**响应格式**：
```json
{
  "text": "最终回答内容",
  "reasoning": "思考链内容（如模型支持）",
  "raw": { ... "原始完整响应" }
}
```

### 4.2 RAG 配置页接口

RAG 配置页（`scripts/rag_web_ui.py`）以 subprocess 方式启动在 port 8766：

| 端点 | 说明 |
|------|------|
| `rag_web_ui.py` | 模型下载、知识库管理、文本切分配置、路由规则编辑、Prompt 模板管理 |

启动方式：
```python
subprocess.Popen(["python", "scripts/rag_web_ui.py", "--port", "8766"])
```

### 4.3 知识库存储接口

| 存储 | 格式 | 路径 |
|------|------|------|
| 向量数据 | Chroma (sqlite3 + parquet) | `data/kb/{kb_name}/` |
| KB 索引 | JSON | `data/kb/kb_index.json` |
| KB 签名 | JSON | `data/kb/kb_signatures.json` |
| 分类规则 | JSON | `data/kb/auto_classify_rules.json` |

### 4.4 配置接口

配置文件：`data/config/rag_config.json`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `embedding.model_path` | string | `""` | 嵌入模型路径，空则自动扫描 |
| `router.enabled` | bool | `true` | 启用路由层 |
| `reranker.enabled` | bool | `false` | 启用重排序 |
| `retrieval.k` | int | `5` | 每库检索 top-K |
| `retrieval.score_threshold` | float | `0.0` | 相似度阈值 |
| `llm_backend` | string | `"lmstudio"` | LLM 后端类型 |
| `llm_model` | string | `""` | 模型名称 |
| `llm_timeout` | int | `180` | API 超时秒数 |
| `llm_max_tokens` | int | `4096` | 最大输出 token 数 |
| `web_search_enabled` | bool | `false` | 联网搜索开关 |

---

## 五、流程详解

### 5.1 完整请求生命周期

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
                    → route_query → retrieve_documents → (reranker) → build_context
           → SM3 去重合并
           → return {context, docs, kb}
         → _second_pass(message, context, action)
           → LLM 基于上下文生成回答
       → type == "import"
         → rag.import_file(path)
       ↓
回答返回前端
```

### 5.2 自修正循环

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

### 5.3 SM3 去重策略

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

## 六、与 Orchestrator 的关系

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

## 七、部署与启动流程

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

## 八、安全与隐私

- **无外部调用**：所有 LLM 请求发向本地 LM Studio / Ollama，不上传数据
- **本地知识库**：Chroma 向量库存储在本地 `data/kb/`，不离开用户机器
- **联网搜索可选**：默认关闭，需用户手动启用
- **模型本地加载**：嵌入模型/路由模型通过本地磁盘加载，不依赖外部 API
