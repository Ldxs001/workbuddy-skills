# RAG Assistant 外部接入协议 v1.0

> 本文档定义 RAG Assistant 对外暴露的全部接口契约。
> 任何第三方系统（编排器、多智能体、定时脚本、文件交换程序）可据此接入，无需本系统提供适配代码。
>
> **本文档覆盖 Web UI API（port 8765）。**
> **组件级外部 API（port 8767）详见 `EXTERNAL_API.md`。**

---

## 目录

1. [HTTP API 契约](#1-http-api-契约)
2. [配置契约](#2-配置契约)
3. [文件交互契约](#3-文件交互契约)
4. [CLI 契约](#4-cli-契约)
5. [模型调用契约](#5-模型调用契约)

---

## 1. HTTP API 契约

### 1.1 通用约定

| 项目 | 值 |
|------|----|
| **默认端口** | 8765 |
| **监听地址** | `0.0.0.0`（可配置 `--host`） |
| **协议** | HTTP/1.1 |
| **字符集** | UTF-8 |
| **Content-Type** | `application/json; charset=utf-8`（API） |
| **错误码** | 非 2xx 时 body 含 `error` 字段 |

### 1.2 端点清单

#### `GET /api/kbs` — 列出知识库

**请求**：无参数

**响应**：
```json
{
  "kbs": {
    "白酒": { "doc_count": 1283, "path": "..." },
    "啤酒": { "doc_count": 217, "path": "..." }
  },
  "success": true
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `kbs` | object | 键为 KB 名称，值为 KB 元信息（含 doc_count） |
| `success` | boolean | 是否成功 |

---

#### `GET /api/config` — 获取完整配置

**请求**：无参数

**响应**：返回 `rag_config.json` 的完整内容（参见 [2. 配置契约](#2-配置契约)）

---

#### `GET /api/config/llm` — 获取 LLM 配置

**响应**：
```json
{
  "backend": "lmstudio",
  "model": "qwen/qwen3.5-35b-a3b",
  "max_tokens": 40960,
  "timeout": 1800,
  "success": true
}
```

| 字段 | 类型 | 可选值 |
|------|------|--------|
| `backend` | string | `"ollama"` / `"lmstudio"` |
| `model` | string | 后端可用模型名 |
| `max_tokens` | int | 最大输出 token 数 |
| `timeout` | int | 请求超时（秒） |

---

#### `POST /api/config/llm` — 更新 LLM 配置

**请求**：
```json
{
  "backend": "lmstudio",
  "model": "qwen/qwen3.5-35b-a3b",
  "timeout": 1800,
  "maxtokens": 40960
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `backend` | 是 | 切换 LLM 后端 |
| `model` | 否 | 模型名，为空时自动选第一个 |
| `timeout` | 否 | 默认 180 |
| `maxtokens` | 否 | 默认 4096 |

**响应**：`{"success": true}`

---

#### `GET /api/llm/models` — 列出可用模型

**查询参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `backend` | 否 | 指定后端，不传则用当前配置 |

**响应**：
```json
{
  "models": ["qwq:32b", "llama3.1:8b"],
  "success": true
}
```

---

#### `GET /api/llm/test` — 测试 LLM 连接

**响应**：
```json
{
  "success": true,
  "message": "连接正常"
}
```

---

#### `POST /api/search/toggle` — 开关联网搜索

**请求**：
```json
{
  "enabled": true
}
```

**响应**：`{"success": true}`

---

#### `POST /api/agent/query` — 直接查询（不走 Agent 决策循环）

**请求**：
```json
{
  "message": "茅台1935的酿造工艺",
  "kb": "白酒",
  "mode": "rag_only",
  "top_k": 10,
  "score_threshold": 0.0,
  "return_sources": true
}
```

| 字段 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `message` | 是 | — | 查询文本 |
| `kb` | 否 | 自动路由 | 指定知识库名称 |
| `mode` | 否 | `"auto"` | `"rag_only"` / `"search_only"` / `"auto"`（自动决策） |
| `top_k` | 否 | 5 | 检索返回的文档块数 |
| `score_threshold` | 否 | 0.0 | 相关性阈值 |
| `return_sources` | 否 | false | 是否在响应中包含 source 详情 |

**等价 GET**：`GET /api/agent/query?q=xxx&kb=xxx&mode=rag_only`

**响应**：
```json
{
  "success": true,
  "text": "茅台1935采用传统大曲酱香工艺...",
  "sources": [
    {
      "kb": "白酒",
      "document": "茅台1935工艺说明.pdf",
      "relevance": 0.89,
      "chunk": "茅台1935酿造工艺：采用大曲酱香工艺..."
    }
  ],
  "kb": "白酒",
  "route_method": "embedding_signature",
  "confidence": 0.85,
  "has_context": true,
  "search_used": false,
  "latency_ms": 342
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | LLM 生成回答文本 |
| `sources` | array | 检索来源列表（仅 `return_sources=true` 时返回） |
| `kb` | string | 实际命中的知识库 |
| `route_method` | string | 路由方法：`"hardcoded"` / `"embedding_signature"` / `"embedding_keyword"` / `"default"` / `"direct"` |
| `has_context` | boolean | 是否检索到相关内容 |
| `search_used` | boolean | 是否触发了联网搜索回退 |
| `latency_ms` | int | 处理耗时（毫秒） |

---

#### `POST /api/agent/import` — 导入文档/文本到知识库

支持三种模式：

**模式 A：结构化知识（title + content）**
```json
{
  "title": "茅台1935工艺说明",
  "content": "茅台1935采用传统大曲酱香工艺...",
  "kb": "白酒"
}
```

**模式 B：纯文本**
```json
{
  "text": "茅台1935采用传统大曲酱香工艺...",
  "kb": "白酒"
}
```

**模式 C：文件路径**
```json
{
  "path": "C:\\docs\\茅台工艺.pdf",
  "kb": "白酒"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `kb` | 否 | 目标知识库，不填自动分类或走 `default` |
| `title` | 模式A必填 | 文档标题 |
| `content` | 模式A必填 | 文档正文 |
| `text` | 模式B必填 | 纯文本内容 |
| `path` | 模式C必填 | 文件或文件夹路径 |

**响应**：
```json
{
  "success": true,
  "doc_count": 12,
  "kb": "白酒"
}
```

---

#### `GET /api/agent/gaps` — 知识缺口列表

**响应**：
```json
{
  "gaps": [
    {
      "query": "茅台1949的历史",
      "kb": "白酒",
      "count": 3,
      "first_seen": "2026-07-01T10:00:00",
      "last_seen": "2026-07-08T08:30:00"
    }
  ],
  "success": true
}
```

| 字段 | 说明 |
|------|------|
| `gaps[].query` | 用户问过但没找到答案的问题 |
| `gaps[].count` | 出现次数（`>= min_count` 才返回，默认 1） |
| `gaps[].first_seen` | 首次出现时间 |
| `gaps[].last_seen` | 最近出现时间 |

---

#### `GET /api/memory/reset` — 重置会话记忆

**响应**：`{"success": true}`

---

#### `POST /api/chat` — Agent 决策循环聊天（人机交互用）

**请求**：
```json
{
  "message": "茅台1935怎么样？"
}
```

**响应**：
```json
{
  "success": true,
  "text": "基于知识库资料，茅台1935...",
  "reasoning": "",
  "kb": "白酒",
  "search_used": false
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | string | 回答文本 |
| `reasoning` | string | 推理链（从 LLM 透传，不一定有） |
| `kb` | string | 命中的知识库 |
| `search_used` | boolean | 是否走了联网搜索 |
| `success` | boolean | 请求是否成功 |
| `error` | string | 失败时才有 |

**等价 GET**：`GET /api/chat?q=xxx`

---

## 2. 配置契约

### 2.1 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 主配置 | `data/config/rag_config.json` | RAG 引擎全部配置 |
| 应用配置 | `config.json`（项目根目录） | 顶层应用配置（可覆盖） |

### 2.2 rag_config.json 完整 Schema

```json
{
  // ── 运行模式 ──
  "mode": "integrated",                          // 固定值，扩展用

  // ── 输入源 ──
  "input_sources": {
    "enable_pdf": true,                         // 是否开启 PDF 解析
    "enable_ocr": true,                         // 扫描 PDF 是否自动 OCR 回退
    "enable_html2md": true,                     // HTML 是否转 Markdown
    "pdf_backend": "pypdf"                      // "pypdf" | "pdfplumber"
  },

  // ── 文本切分 ──
  "splitting": {
    "strategy": "recursive",                     // 主策略：见下表
    "chunk_size": 500,                           // 切分块大小
    "chunk_overlap": 50,                         // 块间重叠
    "separators": ["\n\n", "\n", "。", "；", "，", " ", ""],
    "guards": ["code", "table"],                 // 守卫：见下表
    "secondary_strategy": "semantic",            // 次要策略
    "headers_to_split_on": [["#","h1"], ["##","h2"], ["###","h3"]],
    "semantic_breakpoint": "percentile"           // "percentile" | "interquartile" | "standard_deviation"
  },

  // ── 路由 ──
  "router": {
    "enabled": true,                             // 总开关
    "fallback": {
      "enabled": true,                           // 语义回退开关
      "model_path": "BAAI/bge-reranker-base",    // 路由模型
      "min_score_threshold": 0.3,               // 最低路由分数
      "broadcast_on_fail": true,                 // 失败时全量广播
      "auto_update_signatures": true             // 导入后自动更新 KB 签名
    }
  },

  // ── 重排序 ──
  "reranker": {
    "enabled": true,                             // 总开关
    "mode": "model",                             // "model" | "rule" | "hybrid"
    "model_path": "BAAI/bge-reranker-base",      // reranker 模型
    "top_k": 5,                                  // 精排后保留的文档数
    "sort_rules": []                             // 规则排序列表
  },

  // ── 检索 ──
  "retrieval": {
    "k": 20,                                     // 初始检索数量
    "score_threshold": null,                     // 相似度阈值（null=不限）
    "search_type": "similarity"                  // "similarity" | "mmr" | "similarity_score_threshold"
  },

  // ── LLM 设置 ──
  "llm": {
    "base_url": "http://localhost:1234/v1",      // LM Studio 地址
    "api_key": "not-needed",                     // API Key
    "temperature": 0.1,                          // 生成温度
    "max_tokens": 512,                           // 最大输出 token
    "model_name": ""                             // 模型名（优先使用顶层 llm_model）
  },
  "llm_backend": "lmstudio",                     // "ollama" | "lmstudio"
  "llm_model": "qwen/qwen3.5-35b-a3b",          // LLM 模型名
  "llm_timeout": 1800,                           // LLM 请求超时（秒）
  "llm_max_tokens": 40960,                       // LLM 最大输出 token

  // ── 嵌入模型 ──
  "embedding": {
    "model_path": "maidalun1020/bce-embedding-base_v1",
    "normalize_embeddings": true                 // 是否归一化
  },

  // ── 知识库 ──
  "kb": {
    "active_kb": "default",                      // 当前活跃知识库
    "auto_classify": false                       // 导入时自动分类
  },

  // ── Prompt ──
  "prompt": {
    "template_file": "default_template.txt",
    "user_template": "请用 Markdown 格式输出...",
    "system_prefix": "基于以下资料回答问题..."
  },

  // ── 功能开关 ──
  "web_search_enabled": true,                    // 联网搜索

  // ── 极客模式 ──
  "geek_mode": {
    "edit_enabled": false                        // 是否允许直接编辑配置（Web UI 极客模式面板）
    // 编辑器分区：Prompt / 嵌入模型&检索 / 重排序 / 切片 / 路由层 / 知识库 / LLM / 其他
  }
}
```

### 2.3 切分策略可选值

| 策略名 | 说明 |
|--------|------|
| `recursive` | 递归分割（默认，最通用） |
| `headers` | 按标题层级切分 |
| `semantic` | 语义断点切分 |
| `sentence` | 按句号切分 |
| `fixed` | 固定窗口切分 |

### 2.4 守卫（Guard）可选值

| 守卫名 | 说明 |
|--------|------|
| `code` | 保护代码块不被切碎 |
| `table` | 保护表格不被切碎 |
| `mermaid` | 保护 Mermaid 图表 |
| `math` | 保护数学公式 |
| `html` | 保护 HTML 标签 |

### 2.5 功能开关总表

| 配置路径 | 类型 | 默认 | 说明 |
|---------|------|------|------|
| `router.enabled` | bool | true | 开启出库路由层（查询→最佳 KB） |
| `router.fallback.enabled` | bool | true | 开启语义回退路由 |
| `reranker.enabled` | bool | true | 开启重排序 |
| `web_search_enabled` | bool | true | 开启联网搜索 |
| `input_sources.enable_pdf` | bool | true | 开启 PDF 解析 |
| `input_sources.enable_ocr` | bool | true | 开启 OCR 回退 |
| `kb.enabled` | bool | true | 开启多知识库（关闭时全走 default） |
| `kb.auto_classify` | bool | false | 入库时自动分类（入库路由：嵌入模型 × KB关键词） |
| `geek_mode.edit_enabled` | bool | false | 是否允许配置编辑 |

---

## 3. 文件交互契约

### 3.1 通用约定

RAG Assistant **不内置 watcher 实现**。以下规范供外部系统编写自己的监听/查询脚本时参考。

### 3.2 输入文件格式

#### 单次查询：`query.json`

```json
{
  "query": "茅台1935的酿造工艺",
  "kb": "白酒",
  "mode": "auto",
  "top_k": 10,
  "score_threshold": 0.0,
  "session_id": "batch-001",
  "output_file": "result.json"
}
```

| 字段 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `query` | 是 | — | 查询文本 |
| `kb` | 否 | 自动路由 | 知识库名称 |
| `mode` | 否 | `"auto"` | `"rag_only"` / `"search_only"` / `"auto"` |
| `top_k` | 否 | 5 | 检索返回数 |
| `score_threshold` | 否 | 0.0 | 相关性阈值 |
| `session_id` | 否 | `"default"` | 会话 ID，管理记忆 |
| `output_file` | 否 | stdout | 结果输出路径 |

#### 批量查询：`queries.jsonl`

每行一个 JSON 对象（NDJSON 格式）：

```jsonl
{"query": "茅台工艺", "kb": "白酒"}
{"query": "啤酒原料", "kb": "啤酒"}
{"query": "液相色谱柱效公式", "kb": "理化检测"}
```

#### 直接导入：任意支持格式文件

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| PDF | `.pdf` | 含 OCR 自动回退 |
| 文本 | `.txt` | UTF-8 |
| Markdown | `.md` | 保留标题结构 |
| HTML | `.html` | 自动转 Markdown |
| Word | `.docx` | |
| CSV | `.csv` | |

### 3.3 输出文件格式

#### 单次结果：`result.json`

```json
{
  "status": "success",
  "answer": "茅台1935采用传统大曲酱香工艺...",
  "sources": [
    {
      "kb": "白酒",
      "document": "茅台1935工艺说明.pdf",
      "relevance": 0.89,
      "chunk": "茅台1935酿造工艺..."
    }
  ],
  "kb": "白酒",
  "route_method": "embedding_signature",
  "confidence": 0.85,
  "has_context": true,
  "search_used": false,
  "latency_ms": 342,
  "error": ""
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `"success"` / `"error"` |
| `answer` | string | LLM 生成回答 |
| `sources` | array | 来源文档列表 |
| `kb` | string | 命中知识库 |
| `route_method` | string | 路由方法 |
| `has_context` | boolean | 是否有检索结果 |
| `search_used` | boolean | 是否搜索了网页 |
| `latency_ms` | int | 耗时 |
| `error` | string | 错误信息 |

#### 批量结果：`results.jsonl`

每行对应一个输入的输出，保持与输入相同的顺序：

```jsonl
{"status":"success","answer":"茅台..."}
{"status":"success","answer":"啤酒..."}
{"status":"error","error":"知识库未就绪"}
```

### 3.4 目录组织规范（建议）

```
data/
  inbox/          ← 外部丢入 query.json / 文件 → 自动处理
  outbox/         ← 处理后生成 result.json
  processing/     ← 处理中锁定（防重复处理）
  errors/         ← 失败归档
```

外部系统的 watcher 按以下规则实现：
1. 轮询 `inbox/` 目录
2. 读到 `.json` → 解析为 query 对象 → 调用 `POST /api/agent/query` 或 CLI `--batch --input`
3. 读到 `.jsonl` → 逐行解析 → CLI `--jsonl` 模式
4. 读到 `.pdf`/`.txt`/`.md` 等 → 调用 `POST /api/agent/import`
5. 结果写入 `outbox/`
6. 处理完文件移到 `processing/` 或删除

---

## 4. CLI 契约

### 4.1 启动模式

```bash
# 人机交互 — Web 界面
python main.py                              # 默认端口 8765
python main.py --port 8080 --host 127.0.0.1

# 人机交互 — CLI 命令行
python main.py --no-web                     # 交互式命令行

# 批量处理 — 单文件
python main.py --batch --input query.json --output result.json

# 批量处理 — 管道（JSONL）
cat queries.jsonl | python main.py --jsonl

# 迁移
python main.py migrate                      # 从 local-rag-builder 迁移数据
```

### 4.2 参数清单

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--port` | int | 8765 | Web 端口 |
| `--host` | string | 0.0.0.0 | 监听地址 |
| `--data-dir` | string | `./data` | 数据目录 |
| `--config` | string | — | 覆盖配置文件 |
| `--no-web` | flag | false | CLI 对话模式 |
| `--batch` | flag | false | 批量处理模式 |
| `--input` | string | — | JSON 输入文件 |
| `--output` | string | — | JSON 输出文件 |
| `--jsonl` | flag | false | 管道 JSONL 模式 |
| `--pidfile` | string | — | PID 文件路径 |

### 4.3 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 全部成功 |
| 1 | 部分失败 |
| 2 | 严重错误 |

---

## 5. 模型调用契约

### 5.1 模型角色对照表

| 角色 | 配置路径 | 值格式 | 示例 | 下载来源 |
|------|---------|--------|------|---------|
| **嵌入模型** | `rag_config.embedding.model_path` | HuggingFace ID 或本地路径 | `maidalun1020/bce-embedding-base_v1` | ModelScope / HuggingFace |
| **Reranker 模型** | `rag_config.reranker.model_path` | HuggingFace ID 或本地路径 | `BAAI/bge-reranker-base` | ModelScope / HuggingFace |
| **路由模型** | 跟随嵌入模型 + 精排模型 | 出库路由始终用嵌入模型做余弦相似度；精排开时路由×KB签名，关时×关键词。精排模型同时用于 KB 签名生成 | `maidalun1020/bce-embedding-base_v1`（路由）+ `mxbai-rerank-base-v1`（签名/精排） | — |
| **LLM 模型** | `rag_config.llm.model_name` + `llm_backend` | 后端 + 模型名组合 | `lmstudio` + `qwen/qwen3.5-35b-a3b` | Ollama / LM Studio |

### 5.2 嵌入模型规范

- **模型类型**：Sentence Transformer 兼容（HuggingFace）
- **加载方式**：`local_files_only=True`（必须已本地下载）
- **设备**：自动检测 CUDA / CPU
- **索引方式**：`model_index.json` 中注册

### 5.3 切换模型方式

#### 方式 A：通过 API

```bash
# 切换嵌入模型
curl -X POST http://localhost:8765/api/config \
  -H "Content-Type: application/json" \
  -d '{"embedding": {"model_path": "BAAI/bge-small-zh-v1.5"}}'

# 切换 LLM
curl -X POST http://localhost:8765/api/config/llm \
  -H "Content-Type: application/json" \
  -d '{"backend": "ollama", "model": "llama3.1:8b"}'
```

#### 方式 B：直接改配置文件

编辑 `data/config/rag_config.json`，修改对应模型路径后重启。

#### 方式 C：下载新模型

```bash
python scripts/embedding_model_manager.py --model BAAI/bge-small-zh-v1.5
```

---

## 附录 A：数据结构参考

### A.1 Source 对象

```json
{
  "kb": "白酒",
  "document": "茅台工艺.pdf",
  "relevance": 0.89,
  "chunk": "茅台1935酿造工艺...",
  "metadata": {
    "source": "茅台工艺.pdf",
    "page": 1,
    "_kb": "白酒"
  }
}
```

### A.2 路由方法枚举

| 值 | 说明 |
|------|------|
| `"hardcoded"` | 命中硬编码关键词规则 |
| `"embedding_signature"` | 嵌入模型 × KB签名关键词（精排开时）或 × 规则关键词（精排关时） |
| `"default"` | 无匹配，路由到 default |
| `"direct"` | 用户指定了知识库，直接检索 |
| `"broadcast"` | 失败后全量广播所有 KB |

---

> 以上协议版本：v1.0
> 对应 RAG Assistant 版本：v1.7.0
> 组件级外部 API 详见：`EXTERNAL_API.md`（port 8767，27 个端点）
> 协议更新方式：修改此文件 + bump 版本号
