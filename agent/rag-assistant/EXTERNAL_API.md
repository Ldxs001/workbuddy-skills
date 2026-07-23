# RAG Assistant 外部接入 API 协议 v1.0

> 本文档定义 RAG Assistant 外部接入 API 的完整契约。
> 供第三方系统（编排器、多智能体框架、定时脚本）将 RAG Assistant 作为组件嵌入更大系统时使用。
>
> **端口：** 8767（默认），通过 `python main.py --api-port 8767` 启动
> **与 Web UI（8765）完全隔离，互不影响**

---

## 设计目标

当外部系统需要把 RAG Assistant 当作一个"知识库问答组件"嵌入更大的系统时，需要能：

1. **运行态切换功能开关**（路由/重排序/NLI/搜索）无需改配置文件重启
2. **直接调用向量/rank/NLI 模型**，不只能走完整 RAG 流程
3. **新建/删除/移动 KB**，管理 KB 签名
4. **运行态管理提示词**（模板/插槽/预设/系统前缀）
5. **文本切分和问题组合切片展开**，供外部预处理使用

---

## 启动方式

```bash
# 同时启动 Web UI + 外部 API
python main.py --api-port 8767

# 指定不同端口
python main.py --api-port 9000 --port 8765

# 仅外部 API（不启动 Web UI）
python main.py --no-web --api-port 8767
```

---

## 通用约定

| 项目 | 值 |
|------|-----|
| **默认端口** | 8767 |
| **协议** | HTTP/1.1 |
| **字符集** | UTF-8 |
| **Content-Type** | `application/json; charset=utf-8` |
| **错误响应** | 非 2xx 时 body 含 `error` 字段 |
| **统一返回格式** | `{"success": bool, ...}` |

---

## 端点总览

| 域 | 端点数 | 说明 |
|----|--------|------|
| 健康检查 | 1 | 服务状态 |
| 功能开关 | 2 | 运行态切换/查询 |
| 模型调用 | 3 | 嵌入/Reranker/NLI |
| KB 管理 | 7 | 创建/删除/列表/源/移动/备份/恢复 |
| KB 签名 | 3 | 列表/构建/全量重建 |
| 提示词管理 | 8 | 模板/插槽/预设/前缀 |
| 输入管理 | 3 | 切分/切片展开/策略列表 |
| **合计** | **27** | |

---

## 1. 健康检查

### `GET /api/health`

**响应：**
```json
{
  "success": true,
  "status": "running",
  "version": "1.7.0"
}
```

---

## 2. 功能开关

### `GET /api/feature/status` — 查询所有功能开关状态

**响应：**
```json
{
  "success": true,
  "router": true,
  "reranker": true,
  "nli": false,
  "web_search": false,
  "auto_classify": true,
  "geek_mode": false
}
```

### `POST /api/feature/toggle` — 运行态切换功能开关

**请求：**
```json
{
  "toggles": {
    "router": false,
    "reranker": true,
    "nli": true,
    "web_search": false
  }
}
```

| 功能名 | 说明 |
|--------|------|
| `router` | 出库路由（查询→最佳 KB） |
| `reranker` | 重排序 |
| `nli` | NLI 三向分类 |
| `web_search` | 联网搜索 |
| `auto_classify` | 入库自动分类 |
| `geek_mode` | 极客模式（配置编辑） |

**响应：**
```json
{
  "success": true,
  "changed": ["router=off", "reranker=on", "nli=on"]
}
```

**说明：** 持久化到 `rag_config.json`，重启后保持。

---

## 3. 模型直接调用

### `POST /api/model/embed` — 嵌入模型

**请求：**
```json
{
  "texts": ["茅台1935的酿造工艺", "液相色谱柱效"]
}
```

或单条：
```json
{
  "text": "茅台1935的酿造工艺"
}
```

**响应：**
```json
{
  "success": true,
  "vectors": [[0.0123, -0.0456, ...], [0.0789, ...]],
  "dimension": 768,
  "count": 2
}
```

### `POST /api/model/rerank` — 重排序

**请求：**
```json
{
  "query": "茅台1935的酿造工艺",
  "docs": [
    "茅台1935采用传统大曲酱香工艺...",
    "五粮液使用浓香型酿造...",
    "啤酒发酵温度控制..."
  ],
  "top_k": 2
}
```

也接受对象列表：
```json
{
  "query": "茅台工艺",
  "docs": [
    {"content": "茅台1935...", "metadata": {"source": "doc1.pdf"}},
    {"content": "五粮液...", "metadata": {"source": "doc2.pdf"}}
  ]
}
```

**响应：**
```json
{
  "success": true,
  "reranked": [
    {
      "content": "茅台1935采用传统大曲酱香工艺...",
      "metadata": {"source": "doc1.pdf"},
      "score": 0.89
    }
  ],
  "count": 2
}
```

### `POST /api/model/nli` — NLI 三向分类

**请求：**
```json
{
  "query": "茅台1935采用大曲酱香工艺",
  "docs": [
    "茅台1935酿造工艺采用大曲酱香...",
    "五粮液使用浓香型工艺...",
    "啤酒通过发酵酿造..."
  ],
  "top_k": 0
}
```

**响应：**
```json
{
  "success": true,
  "results": [
    {
      "content": "茅台1935酿造工艺采用大曲酱香...",
      "label": "entailment",
      "scores": {"entailment": 0.92, "neutral": 0.06, "contradiction": 0.02}
    },
    {
      "content": "五粮液使用浓香型工艺...",
      "label": "contradiction",
      "scores": {"entailment": 0.05, "neutral": 0.10, "contradiction": 0.85}
    }
  ],
  "count": 2
}
```

| NLI 标签 | 说明 |
|----------|------|
| `entailment` | 蕴含：文档支持查询 |
| `neutral` | 中立：文档与查询无明确关系 |
| `contradiction` | 矛盾：文档与查询对立 |

---

## 4. KB 管理

### `GET /api/kb/list` — 列出所有知识库

**响应：**
```json
{
  "success": true,
  "kbs": {
    "白酒": {"doc_count": 1283, "path": "..."},
    "理化检测": {"doc_count": 761, "path": "..."}
  },
  "stats": {"total_kbs": 13, "total_docs": 4094}
}
```

### `POST /api/kb/create` — 创建知识库

**请求：**
```json
{
  "name": "新知识库",
  "description": "存储XX领域文档",
  "model_id": ""
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | KB 名称 |
| `description` | 否 | 描述 |
| `model_id` | 否 | 指定嵌入模型，空则用全局默认 |

**响应：** `{"success": true, "message": "知识库 '新知识库' 已创建", "kb": "新知识库"}`

### `POST /api/kb/delete` — 删除知识库

**请求：** `{"name": "新知识库"}`

**说明：** `default` 知识库不可删除。删除后签名也同步清理。

### `GET /api/kb/sources?kb=白酒` — 列出 KB 内文档来源

**响应：**
```json
{
  "success": true,
  "kb": "白酒",
  "sources": {
    "茅台1935工艺说明.pdf": 12,
    "五粮液标准.docx": 8
  }
}
```

### `POST /api/kb/move` — 跨库移动文档

**请求：**
```json
{
  "src_kb": "白酒",
  "target_kb": "其他酒",
  "sources": ["葡萄酒", "黄酒"]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `src_kb` | 是 | 源知识库 |
| `target_kb` | 是 | 目标知识库 |
| `sources` | 是 | 要移动的 source 名称列表（模糊匹配） |

**说明：** 两个 KB 的向量模型必须一致才能移动。移动后自动重建两个 KB 的签名。

### `POST /api/kb/backup` — 手动备份 KB

**请求：** `{"kb": "白酒"}`

**响应：** `{"success": true, "message": "已备份", "backup_path": "..."}`

### `GET /api/kb/backups?kb=白酒` — 列出 KB 备份

**响应：**
```json
{
  "success": true,
  "kb": "白酒",
  "backups": [
    {"name": "白酒_20260721_003000.zip", "size": "15.3MB", "time": "2026-07-21T00:30:00"}
  ]
}
```

### `POST /api/kb/restore` — 恢复 KB 备份

**请求：** `{"kb": "白酒", "backup_name": "白酒_20260721_003000.zip"}`

---

## 5. KB 签名管理

### `GET /api/kb/signatures` — 列出所有 KB 签名

**响应：**
```json
{
  "success": true,
  "signatures": {
    "白酒": {
      "signature": "茅台 · 酱香 · 大曲 · 酿造 · 工艺",
      "signatures": ["茅台 酱香 大曲", "五粮液 浓香 发酵"],
      "method": "reranker",
      "version": "v2"
    }
  }
}
```

### `POST /api/kb/signature/build` — 构建单个 KB 签名

**请求：** `{"kb": "白酒"}`

**说明：** 从 KB 的 ChromaDB 读取文档 chunk，执行四分法采样→jieba 提词→BCE 排序→更新签名和分类规则。

### `POST /api/kb/signature/rebuild-all` — 重建所有 KB 签名

**请求：** 无参数

**说明：** 遍历所有非 default KB，逐个重建签名。

---

## 6. 提示词管理

### `GET /api/prompt/template` — 获取当前模板

**响应：**
```json
{
  "success": true,
  "template": "请用 Markdown 格式输出...",
  "template_path": "data/prompts/custom_prompt_template.txt"
}
```

### `POST /api/prompt/template` — 保存模板

**请求：** `{"content": "新的模板内容..."}`

### `POST /api/prompt/template/reset` — 重置模板为默认

### `GET /api/prompt/slots` — 获取插槽值

**响应：**
```json
{
  "success": true,
  "slots": {
    "cite_format": "[n]",
    "output_style": "Markdown",
    "fallback": "礼貌告知用户"
  }
}
```

### `POST /api/prompt/slots` — 保存插槽值

**请求：** `{"slots": {"cite_format": "[来源]", "output_style": "表格"}}`

### `GET /api/prompt/presets` — 获取所有预设

**响应：**
```json
{
  "success": true,
  "presets": {
    "default": {"label": "默认", "slots": {...}},
    "structured": {"label": "结构化", "slots": {...}},
    "custom_xxx": {"label": "科研模式", "slots": {...}}
  },
  "selected": "custom_xxx"
}
```

### `POST /api/prompt/preset` — 保存自定义预设

**请求：**
```json
{
  "label": "学术模式",
  "slots": {"cite_format": "[n]", "output_style": "学术体", "fallback": "..."},
  "description": "学术论文风格输出"
}
```

### `POST /api/prompt/preset/delete` — 删除自定义预设

**请求：** `{"key": "custom_xxx"}`

### `POST /api/prompt/preset/apply` — 应用预设

**请求：** `{"key": "custom_xxx"}`

**说明：** 应用预设后，插槽值立即更新为该预设的值。

### `GET /api/prompt/system-prefix` — 获取系统前缀

### `POST /api/prompt/system-prefix` — 设置系统前缀

**请求：** `{"prefix": "你是一个专业的知识库助手..."}`

---

## 7. 输入管理

### `GET /api/input/strategies` — 获取切分策略和守卫列表

**响应：**
```json
{
  "success": true,
  "strategies": {
    "recursive": {"description": "递归分割", "config_schema": {...}},
    "semantic": {"description": "语义断点", "config_schema": {...}}
  },
  "guards": {
    "code": "保护代码块",
    "table": "保护表格",
    "mermaid": "保护 Mermaid 图表",
    "math": "保护数学公式",
    "html": "保护 HTML 标签"
  }
}
```

### `POST /api/input/split` — 文本切分

**请求：**
```json
{
  "text": "一段很长的文本...",
  "strategy": "recursive",
  "secondary": "semantic",
  "chunk_size": 500,
  "chunk_overlap": 50,
  "guards": ["code", "table", "math"],
  "separators": ["\n\n", "\n", "。", "；"]
}
```

| 字段 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `text` | 是 | — | 要切分的文本 |
| `strategy` | 否 | 配置值 | 主切分策略 |
| `secondary` | 否 | 配置值 | 次要策略 |
| `chunk_size` | 否 | 500 | 块大小 |
| `chunk_overlap` | 否 | 50 | 块重叠 |
| `guards` | 否 | 配置值 | 守卫列表 |
| `separators` | 否 | 配置值 | 分隔符列表 |

**策略可选值：** `recursive` / `headers` / `semantic` / `sentence` / `fixed`
**守卫可选值：** `code` / `table` / `mermaid` / `math` / `html`

**响应：**
```json
{
  "success": true,
  "chunks": [
    {"content": "第一段...", "metadata": {}, "length": 487},
    {"content": "第二段...", "metadata": {}, "length": 502}
  ],
  "count": 2,
  "strategy": "recursive",
  "chunk_size": 500,
  "chunk_overlap": 50
}
```

### `POST /api/input/query-slices` — 问题组合切片展开

将 LLM 标注的 entities × attrs 穷举展开为查询切片列表，供外部系统并行检索。

**请求：**
```json
{
  "entities": "茅台,五粮液",
  "attrs": "酿造工艺,口感,历史",
  "rel": "对比"
}
```

**响应：**
```json
{
  "success": true,
  "slices": [
    "茅台",
    "茅台 酿造工艺",
    "茅台 口感",
    "茅台 历史",
    "五粮液",
    "五粮液 酿造工艺",
    "五粮液 口感",
    "五粮液 历史",
    "茅台 五粮液 对比",
    "茅台 五粮液 酿造工艺 对比",
    "茅台 五粮液 口感 对比",
    "茅台 五粮液 历史 对比"
  ],
  "count": 12,
  "entities": ["茅台", "五粮液"],
  "attrs": ["酿造工艺", "口感", "历史"],
  "rel": "对比"
}
```

**展开规则：**
1. 每个 entity 单独（宽泛检索）
2. 每个 entity × 每个 attr（事实块检索）
3. 若 ≥2 entity + rel：entity 两两组合 × rel + 每个 attr
4. 若 1 entity + rel：attrs 两两配对 × rel

---

## 与现有协议的关系

| 协议 | 端口 | 定位 | 文档 |
|------|------|------|------|
| Web UI API | 8765 | 人机交互（聊天界面+配置面板） | `PROTOCOL.md` |
| RAG 配置页 | 8766 | KB/模型配置 GUI | 架构文档 |
| **外部 API** | **8767** | **系统间集成（本文件）** | `EXTERNAL_API.md` |

三个端口完全隔离，互不影响。外部 API 不包含聊天/对话端点（那些在 8765 上），仅提供组件级别的能力调用。

---

## Python 编程接口等价调用

所有 REST 端点均可通过 Python 直接调用底层函数实现：

```python
# 功能开关
from config import load_config, save_config
cfg = load_config()
cfg["router"]["enabled"] = False
save_config(cfg)

# 嵌入
from rag_core import get_embeddings
emb = get_embeddings()
vector = emb.embed_query("文本")

# Reranker
from reranker import Reranker
reranker = Reranker(cfg)
reranked = reranker.rerank("query", docs)

# NLI
from nli_classifier import get_nli_classifier
classifier = get_nli_classifier()
results = classifier.classify("query", docs)

# KB 管理
from knowledge_base_manager import create_knowledge_base, move_kb_documents, list_kb_sources
from router import build_kb_signature, list_kb_signatures, rebuild_all_signatures

# 提示词
from prompt_manager import load_template, save_template, load_slots, save_slots
from prompt_manager import get_all_presets, save_custom_preset, apply_preset

# 文本切分
from text_splitter import split_pipeline, get_all_strategies_info
```

---

> 协议版本：v1.0
> 对应 RAG Assistant 版本：v1.7.0
> 更新方式：修改此文件 + bump 版本号
