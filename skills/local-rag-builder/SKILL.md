---
name: local-rag-builder
version: 0.2.0
description: 本地 RAG 系统搭建技能，支持环境自动检测修复、嵌入模型多源下载与完整性校验、6种切分策略及组合、多知识库管理、可调 Prompt、Web 可视化配置界面
author: your-name-here
license: MIT
sensitive_access: false
critical_write: false
trigger: ['搭建 RAG 系统', '本地知识库', '嵌入模型下载', '文本切分', '向量检索', 'RAG 环境配置', '下载模型', '入库文档', '切分文档', '知识库管理']
trigger_negative: ['纯聊天', '简单问答']
tags: ['rag', 'embedding', 'llm', 'python', 'vector-db', 'text-splitter']
data_dir: skills/.standardization/local-rag-builder/data/
h1_position: true
external_data_dir: true
permission_weight: LOW
faq_quality: improve_qa
---
# local-rag-builder（本地 RAG 搭建工具）

一站式本地 RAG 系统搭建工具。支持环境自动检测修复、嵌入模型多源下载、6 种切分策略及组合、多知识库管理、可调 Prompt、Web 可视化配置。

## 触发场景

- **搭建 RAG** — "帮我搭一个本地 RAG 系统"
- **环境检测** — "检查我的 Python 环境能否跑 RAG"
- **下载模型** — "下载一个嵌入模型" / "换个模型源重试"
- **切分文档** — "对这个 Markdown 文件做层级切分"
- **向量检索** — "把这份资料入库，搜索相似内容"
- **知识库管理** — "创建一个知识库" / "把这类资料存入指定库"
- **调整参数** — "更新切分参数" / "改 Prompt 模板"
- **打开界面** — "打开 RAG 配置界面"
- **不触发**：纯 LLM 聊天、不需要检索的简单问答

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 能力 | 说明 |
|---|------|------|
| 1 | **环境自动检测修复** | 检测 Python 版本（需 3.8-3.11）、缺失包，自动创建虚拟环境安装 |
| 2 | **嵌入模型管理** | 多源下载（ModelScope / HuggingFace 镜像 / 官方 / LLM 找源），自动重试，完整性校验，路径修正 |
| 3 | **6 种切分策略 + 组合** | 固定窗口、递归切、层级/标题切、按句切、语义切、代码块保护切，支持策略组合与参数调优 |
| 4 | **多知识库管理** | 支持多个向量知识库并行，LLM 自动分类入库或用户指定 |
| 5 | **可调 Prompt** | 模板持久化，支持自定义占位符（`{context}` `{question}`），运行时编辑 |
| 6 | **Web 可视化界面** | 内嵌 HTML 配置面板，可直调 Python 核心参数，无需手动改代码 |
| 7 | **结构化接口** | 提供标准 Python API 和 CLI，便于智能体集成调用 |

## 快速开始

```bash
# 1. 进入技能目录
cd ~/.workbuddy/skills/local-rag-builder

# 2. 运行环境检测（自动修复）
python scripts/rag_env_setup.py

# 3. 下载嵌入模型（交互式选择）
python scripts/embedding_model_manager.py --interactive

# 4. 启动 Web 配置界面
python scripts/rag_web_ui.py

# 5. 启动交互式 RAG 对话
python scripts/rag_interface.py
```

## 工作流程

1. **环境准备** — `rag_env_setup.py` 检测并安装依赖
2. **模型下载** — `embedding_model_manager.py` 下载/校验嵌入模型
3. **文档入库** — `text_splitter.py` 切分文档 → `knowledge_base_manager.py` 向量化
4. **问答交互** — `rag_interface.py` 提供 CLI 交互，支持 `/prompt` `/kb` 等命令
5. **配置调整** — `rag_web_ui.py` 提供可视化面板
6. **结构化接口** — 各脚本均支持 JSON 输入输出供智能体调用

## 命令速查

| 脚本 | 作用 | 核心参数 |
|------|------|----------|
| `rag_env_setup.py` | 环境检测与修复 | `--auto-install`, `--check-only` |
| `embedding_model_manager.py` | 嵌入模型管理 | `--download`, `--list`, `--check`, `--remove` |
| `text_splitter.py` | 文本切分 | `--strategy`, `--chunk-size`, `--overlap`, `--input` |
| `rag_core.py` | RAG 核心引擎 | `--model`, `--kb`, `--question` |
| `rag_interface.py` | CLI 交互 | `--kb`, `--model` |
| `rag_web_ui.py` | Web 配置界面 | `--port` |
| `prompt_manager.py` | Prompt 管理 | `--set`, `--show`, `--reset`, `--list` |
| `knowledge_base_manager.py` | 知识库管理 | `--create`, `--import`, `--list`, `--delete`, `--classify` |

## 数据目录（skills/.standardization/local-rag-builder/data/）

```
data/
├── kb/               # 向量数据库目录（每个知识库一个子目录）
│   ├── default/      # 默认知识库
│   ├── art/          # 艺术类资料
│   └── politics/     # 政治类资料
├── models/           # 下载的嵌入模型
├── prompts/          # Prompt 模板文件
├── config/           # 运行时配置
├── output/           # 导出产物
├── logs/             # 执行日志
└── cache/            # 缓存
```

## 重要约定

1. **Python 版本**：建议 3.8-3.11（3.12+ 需测试 chromadb 兼容性）
2. **嵌入模型路径**：下载后自动修正真实路径（如 `bge-small-zh-v1___5`）
3. **知识库隔离**：不同资料自动/手动归入不同库
4. **重置**：删除 `data/` 下对应子目录即可重置相关数据

→ 详见 references/guide.md
→ 详见 references/architecture.md
→ 详见 references/examples.md
→ 详见 references/faq.md
→ 详见 references/antipatterns.md
→ 详见 references/changelog.md
→ 详见 references/permissions.md
