# RAG Assistant

> **本地知识库问答智能体** — LLM 驱动的组合式语义检索与多库路由。
> 作者：wUwproject | 许可证：Apache 2.0

基于 `local-rag-builder` 技能构建的独立 RAG 智能体，支持 LM Studio / Ollama 双后端。

## 核心特性

- **组合式查询** — LLM 自动对问题做实体/属性分词（entities + attrs），穷举组合后独立检索，SM3 去重合并，LLM 综合回答
- **多库路由** — 硬编码关键词 + 语义回退（FallbackRouter）双路由，自动匹配最相关的知识库
- **自修正决策** — LLM 输出格式错误时自动反馈重试（最多 5 次），重试耗尽时清上下文重来
- **配置持久化** — timeout / max_tokens / backend / model 全部保存到 `config.json`，刷新页面不丢
- **思考过程折叠** — LLM 推理过程以可折叠 `🤔` 框显示，不影响正常回答
- **联网搜索** — 可选启用，扩展知识库覆盖范围

## 文件结构

| 文件 | 作用 |
|------|------|
| `main.py` | 入口，CLI + Web 双模式 |
| `rag_assistant/agent.py` | Agent 决策循环（entities/attrs 分词 → 自修正 → 知识库检索 → 综合回答） |
| `rag_assistant/web_ui.py` | Web 界面（port 8765），LLM 配置面板 + 聊天界面 |
| `rag_assistant/llm_client.py` | LLM 统一客户端（Ollama + LM Studio），含 reasoning_content 提取 |
| `rag_assistant/rag_wrapper.py` | 技能封装层，完整走 local-rag-builder 流程 |
| `scripts/` | local-rag-builder 技能核心模块（路由 / 检索 / rerank / 知识库管理） |
| `setup.bat` | Windows 一键启动 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 下载嵌入模型（通过 RAG 配置页）
#    启动后打开 http://localhost:8766 → 模型管理 → 下载

# 3. 启动
python main.py

# 4. 打开浏览器访问 http://localhost:8765
```

### 启动脚本

```bash
setup.bat          # Windows 一键启动（自动装依赖 + 启动 + 打开浏览器）
```

## 配置

LM Studio / Ollama 后端、模型选择、timeout、max_tokens 等通过 Web 界面（port 8765）顶部配置栏设置，自动保存到 `data/config/rag_config.json`。

嵌入模型和路由模型通过 RAG 配置页（port 8766）下载和管理。

## 依赖

- LM Studio 或 Ollama（本地 LLM 推理服务）
- Python 3.11+
- 嵌入模型（通过 RAG 配置页下载，推荐 BAAI/bge-small-zh-v1.5）

## 许可证

Apache 2.0 — 详见 LICENSE 文件
