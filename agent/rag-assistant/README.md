# RAG Assistant

本地知识库智能体系统。基于 ChromaDB + 本地 LLM 的多知识库 RAG 查询引擎。

## 特性

- **多知识库路由** — 文档入库/出库均使用嵌入模型做语义路由
- **穷举组合检索** — LLM 将问题分解为 entities × attrs 元组，多路独立检索
- **自修正循环** — LLM 输出格式/动作校验失败时自动反馈重试
- **Web 界面** — 配置管理 + 对话窗口，双 Tab 切换
- **CLI 模式** — `--batch` / `--jsonl` 管道模式
- **完全本地** — 所有数据在本地，不需要任何外部 API

## 快速开始

```bash
pip install rag-assistant-ldxs
python main.py --port 8765
```

## 依赖

- Python ≥ 3.9
- ChromaDB（向量存储）
- LM Studio 或 Ollama（LLM 后端）
- 嵌入模型（BGE / BCE / E5 系列）

## 协议

Apache 2.0
