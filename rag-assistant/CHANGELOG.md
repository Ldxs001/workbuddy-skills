# rag-assistant 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本号遵循语义版本控制（`__init__.py` 唯一源）。

---

## [0.2.0] - 2026-07-08

### 新增
- **`RAG_PROTOCOL.md`** — 完整的外部接入协议规范，覆盖：
  - HTTP API 契约：13 个端点，全量请求/响应 JSON Schema
  - 配置契约：`rag_config.json` 完整字段说明 + 功能开关总表
  - 文件交互契约：`query.json` / `queries.jsonl` / `result.json` 格式定义
  - CLI 契约：参数清单 + 退出码
  - 模型调用契约：嵌入/reranker/LLM/路由四类模型对照表
- **`llms.txt`** — 遵循 llmstxt.org 标准的 AI 可读项目自描述文档，平台无关
- **`--batch` CLI 模式** — `python main.py --batch --input q.json --output r.json`，结构化输入输出
- **`--jsonl` 管道模式** — `cat queries.jsonl | python main.py --jsonl`，逐行处理
- **`_execute_structured()`** — 绕过 Agent 决策循环的直接 RAG 查询函数，支持 `rag_only` / `search_only` / `auto` 三种模式
- **`--pidfile` 参数** — 进程管理用 PID 文件写入

### 文档
- `main.py` 参数列表扩充（`--batch` / `--input` / `--output` / `--jsonl` / `--pidfile`）
- 开发目录与发布目录的 3 文件差分同步完成

---

## [0.1.0] - 2026-07-07

从 `local-rag-builder` v1.5.0 技能抽取为独立智能体应用。
所有 `rag_assistant/` 模块均为 07-07 新建，基于技能能力重新设计上层架构。

### 架构（自包容技能副本）
- `scripts/` — local-rag-builder 完整技能副本（rag_core / router / reranker / text_splitter / KB 管理 / 嵌入模型管理 / prompt 管理）
- `vendor/` — 嵌入第三方依赖（bs4 / pypdf / markdownify / soupsieve）
- `rag_assistant/agent.py` — LLM 自主决策循环（query / search / import 三动作 + 自修正 + 穷举组合查询）
- `rag_assistant/rag_wrapper.py` — 技能封装桥接层，保持技能完整流程
- `rag_assistant/llm_client.py` — Ollama（/api/chat） + LM Studio（OpenAI 兼容）双后端
- `rag_assistant/memory.py` — 三层记忆：短期对话 / LLM 压缩摘要 / 知识缺口 / 用户习惯统计
- `rag_assistant/search.py` — 联网搜索回退（DuckDuckGo / Tavily / urllib fallback）
- `rag_assistant/web_ui.py` — 自包含 HTTP 服务器 + 双 Tab（配置 iframe + 对话），文件拖拽导入

### 功能
- Web 界面（默认 8765 端口），支持 LLM 配置切换、模型列表、知识库浏览、文件拖拽导入
- CLI 交互模式（`--no-web`），支持 `/reset` 记忆重置
- `migrate` 子命令从 local-rag-builder 技能迁移已有知识库和模型
- 13 个知识库（白酒 / 啤酒 / 理化检测 / 生物医疗 / 量子物理 / LLM 理论 / 神经科学 / 政经文哲 / 设备条件 / τ scaling / 其他酒 / 诸子百家 / default）
- 双后端 LLM 支持 + 两级路由 + Reranker 重排序
- setup.bat 一键启动

---

## 版本来源

rag-assistant 从以下技能/版本演化而来（详见对应 skills 仓库的 changelog）：

| 来源 | 版本范围 | 时期 |
|------|---------|------|
| `local-rag-builder` | v0.1.0 → v1.5.0 | 2026-06-06 → 2026-07-07 |
| `rag-assistant`（独立） | v0.1.0 → 当前 | 2026-07-07 → 至今 |
