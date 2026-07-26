# RAG Assistant

> 本地知识库问答智能体 — LLM 驱动的组合式语义检索与多库路由。
> 版本：2.0.0b1 | 作者：wUwproject | 许可证：Apache 2.0

## ⚠️ 从 1.x 升级到 2.x 必须重建 HNSW 索引

**2.x 将向量搜索引擎从 ChromaDB 内置 HNSW 替换为独立 hnswlib 索引，以解决 ChromaDB Rust 后端在 Windows 上的 HNSW 持久化 bug。**

升级后首次搜索会自动触发懒重建（每个 KB 约 1-2 分钟），也可手动点击 🔨 HNSW 按钮，或通过 `POST /api/kb/rebuild-hnsw` API 触发。

- **重建不可跳过**：ChromaDB HNSW 和 hnswlib 索引格式不兼容
- **旧索引自动清理**：重建后 ChromaDB 的 HNSW 段文件会自动废弃
- **数据不丢失**：文档文本和 metadata 全部保留，仅重新计算向量索引

基于 local-rag-builder 技能构建的独立 RAG 智能体，支持 LM Studio / Ollama 双后端。

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动（需要 LM Studio 或 Ollama 运行中）
python main.py

# 3. 打开浏览器访问 http://localhost:8765

# 同时启动外部 API（可选）
python main.py --api-port 8767
```

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **组合式查询** | LLM 自动做 entities/attrs 分词，穷举组合后独立检索，SM3 去重合并，LLM 综合回答 |
| **多库路由** | 硬编码关键词 + 嵌入模型×KB签名语义回退两级路由 |
| **三层推理流水线** | 检索 → Reranker 精排 → NLI 三向分类（entailment/neutral/contradiction） |
| **自修正决策** | LLM 格式错误时自动反馈重试（最多 5 次），重试耗尽时清上下文重来 |
| **功能运行态切换** | 路由/重排序/NLI/搜索开关无需改配置重启 |
| **联网搜索** | 5 种后端：DuckDuckGo/Tavily/Google/Bing/自定义 |

---

## 文件结构

```
rag-assistant/
├── main.py                           # 入口（CLI/Web/Batch/External API 四模式）
├── setup.bat                         # Windows 一键启动
├── requirements.txt                  # 依赖清单
├── CHANGELOG.md                      # 版本更新日志
│
├── rag_assistant/                    # 智能体核心
│   ├── agent.py                      # LLM 决策循环
│   ├── web_ui.py                     # Web 界面（port 8765）
│   ├── external_api.py               # 外部接入 API（port 8767）← 新增
│   ├── llm_client.py                 # LLM 统一客户端（LM Studio / Ollama）
│   ├── rag_wrapper.py                # 技能封装层
│   ├── search.py                     # 联网搜索（5 种后端）
│   ├── memory.py                     # 三层记忆系统
│   └── _fix_rag.py                   # 破损数据修复工具
│
├── engine/                           # 技能引擎（独立副本）
│   ├── rag_core.py                   # 检索/路由/rerank/NLI 编排
│   ├── router.py                     # 两级路由 + KB 签名生成
│   ├── reranker.py                   # 重排序（model/rule/hybrid）
│   ├── nli_classifier.py             # NLI 三向分类器
│   ├── knowledge_base_manager.py     # KB CRUD + 备份/恢复/移动
│   ├── text_splitter.py              # 5 种切分策略 + 5 种守卫
│   ├── prompt_manager.py             # 提示词管理（模板/插槽/预设）
│   └── ...
│
├── vendor/                           # 内嵌第三方库（bs4/pypdf/markdownify）
└── data/                             # 运行时数据
    ├── config/rag_config.json        # 全量配置
    ├── kb/                           # ChromaDB 知识库
    ├── models/                       # 嵌入/reranker/NLI 模型
    ├── sessions/                     # 会话历史
    ├── memory/                       # 压缩摘要/知识缺口/习惯
    └── prompts/                      # 自定义模板/预设
```

---

## 启动模式

```bash
python main.py                              # Web UI（port 8765）
python main.py --api-port 8767              # Web UI + 外部 API
python main.py --no-web --api-port 8767     # 仅外部 API
python main.py --no-web                     # CLI 交互模式
python main.py --batch --input q.json --output r.json   # 批量处理
cat queries.jsonl | python main.py --jsonl              # 管道模式
python main.py migrate                      # 从 local-rag-builder 迁移
```

---

## 架构概览

```
用户输入
  → [LLM 决策层]
       ├─ 闲聊 → 直接回答
       └─ 知识库查询 → entities/attrs 分词
           → [组合展开器] 穷举 entities × attrs
           → [多切片检索] 每片独立走完整 RAG 流程
              1. 路由（嵌入模型 × KB签名/关键词）
              2. 检索（Chroma 相似度）
              3. (可选) 重排序（reranker）
              4. (可选) NLI 三向分类（entailment/neutral/contradiction）
           → [SM3 去重合并]（保留 NLI 标签）
           → [LLM 综合回答]（带 NLI 标签辅助判断）
```

---

## 文档导航

| 文档 | 用途 |
|------|------|
| `PROTOCOL.md` | Web UI API 契约（port 8765）— 聊天/配置/文件交互 |
| `EXTERNAL_API.md` | 外部接入 API 契约（port 8767）— 功能开关/模型调用/KB管理/提示词/切分 |
| `rag_assistant/engine/rag-assistant-architecture.md` | 内部架构设计文档 |
| `CHANGELOG.md` | 完整版本更新日志 |
| `llms.txt` | AI 可读项目描述（llmstxt.org 规范） |

---

## 三端口架构

| 端口 | 模块 | 定位 | 文档 |
|------|------|------|------|
| 8765 | `web_ui.py` | 人机交互（聊天+配置面板） | `PROTOCOL.md` |
| 8766 | `rag_web_ui.py`（subprocess） | KB/模型配置 GUI | 架构文档 |
| 8767 | `external_api.py` | 系统间集成（组件级调用） | `EXTERNAL_API.md` |

---

## 技术栈

- **LLM 后端**：LM Studio（OpenAI 兼容） / Ollama
- **向量存储**：ChromaDB（langchain-chroma）
- **嵌入模型**：BCE-embedding-base_v1（本地加载）
- **Reranker**：BAAI/bge-reranker-base（本地加载）
- **NLI 分类**：MoritzLaurer/mDeBERTa-v3-base-mnli-xnli（本地加载）
- **文本切分**：5 种策略 + GuardStack 守卫栈
- **哈希去重**：SM3 国密哈希

## 依赖

- LM Studio 或 Ollama（本地 LLM 推理服务）
- Python 3.9+
- 嵌入模型（推荐 maidalun1020/bce-embedding-base_v1）
- ChromaDB（向量存储，自动安装）

## 协议

Apache 2.0
