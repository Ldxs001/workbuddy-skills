# RAG Assistant

> 本地知识库问答智能体 — LLM 驱动的组合式语义检索与多库路由。
> 作者：wUwproject | 许可证：Apache 2.0

基于 local-rag-builder 技能构建的独立 RAG 智能体，支持 LM Studio / Ollama 双后端。

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **组合式查询** | LLM 自动对问题做实体/属性分词（entities + attrs），穷举组合后独立检索，SM3 去重合并，LLM 综合回答 |
| **多库路由** | 硬编码关键词 + 语义回退（FallbackRouter）双路由，自动匹配最相关的知识库 |
| **自修正决策** | LLM 输出格式错误时自动反馈重试（最多 5 次），重试耗尽时清上下文重来 |
| **配置持久化** | timeout / max_tokens / backend / model 全部保存到 config.json，刷新页面不丢 |
| **联网搜索** | 可选启用，扩展知识库覆盖范围 |

---

## 文件结构

```
agent/rag-assistant/
├── main.py                           # 入口，CLI + Web 双模式
├── rag_assistant/
│   ├── agent.py                      # Agent 决策循环
│   ├── web_ui.py                     # Web 界面（port 8765）
│   ├── llm_client.py                 # LLM 统一客户端
│   ├── rag_wrapper.py                # 技能封装层
│   ├── search.py                     # 联网搜索
│   └── memory.py                     # 记忆管理
├── scripts/                          # 技能核心模块
├── vendor/                           # 内嵌第三方库
└── data/                             # 运行时数据
    ├── config/rag_config.json        # LLM 与检索配置
    ├── models/                       # 嵌入/路由/rerank 模型
    ├── kb/                           # 知识库（Chroma 向量库）
    └── ...
```

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动（需要 LM Studio 或 Ollama 运行中）
python main.py

# 3. 打开浏览器访问 http://localhost:8765
```

## 架构概览

```
┌──────────────────────────────────────────────────┐
│                  入库流程                          │
├──────────────────────────────────────────────────┤
│  上传文件 / 文本输入                              │
│    → [LLM 决策 import]                            │
│    → [文档加载] PDF(PyPDFLoader + OCR回退) / 文本   │
│    → [入库路由] 嵌入模型 × KB关键词(余弦相似度)     │
│    → [切片流水线] 多策略切分(recursive/headers/     │
│                    semantic) + guard栈             │
│    → [ChromaDB 写入] upsert + 自动备份             │
│    → [KB 签名更新] TF-IDF 关键词提炼 → 路由用      │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│                  查询流程                          │
├──────────────────────────────────────────────────┤
│  用户输入                                         │
│    → [LLM 决策层]                                  │
│         ├─ 闲聊 → 直接回答                         │
│         └─ 知识库查询 → entities/attrs 分词         │
│             → [组合展开器] 穷举 entities × attrs     │
│             → [多切片检索] 每片独立走完整 RAG 流程    │
│                1. 路由（嵌入模型 × KB签名/关键词）    │
│                2. 检索（Chroma 相似度）              │
│                3. (可选) 重排序（reranker）          │
│             → [SM3 去重合并]                       │
│             → [LLM 综合回答]                       │
└──────────────────────────────────────────────────┘
```

## 依赖

- LM Studio 或 Ollama（本地 LLM 推理服务）
- Python 3.9+
- 嵌入模型（推荐 BAAI/bge-small-zh-v1.5）
- ChromaDB（向量存储，自动安装）

## 协议

Apache 2.0
