# Structured Writer — 结构化写作智能体

基于 LLM 的结构化文章写作助手，支持子结构规划、RAG 知识库查询、续写、大纲交互调整。

## 快速开始

```bash
pip install structured-writer-ldxs
structured-writer-ldxs --port 8770
```

## 特性

- **子结构系统** — 每节自动分解为 2-4 个子结构，逐子结构串行写作
- **两级 RAG** — 节级别背景资料 + 子结构级别针对性资料
- **续写机制** — 检测 token 截断自动续写
- **交互式大纲** — 勾选/排序/字数编辑/重点标记
- **多模板** — 通用公文/新闻报道/论文综述/技术报告

## 配置

打开 `http://localhost:8770` 进入配置界面，设置 LLM 后端（LM Studio / Ollama）和写作参数。

## 版本

当前版本: 0.2.5b2

## 许可证

Apache 2.0
