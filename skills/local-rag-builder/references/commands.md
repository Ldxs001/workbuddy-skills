# 命令速查 — local-rag-builder

| 脚本 | 作用 | 核心参数 |
|------|------|----------|
| `rag_env_setup.py` | 环境检测与修复 | `--auto-install`, `--check-only`, `--cleanup-locks`, `--mirror`, `--dry-run` |
| `embedding_model_manager.py` | 嵌入模型管理 | `--download`, `--list`, `--check`, `--remove` |
| `text_splitter.py` | 文本切分（三层流水线） | `--strategy`, `--guard`, `--secondary`, `--chunk-size`, `--input`, `--list-strategies` |
| `rag_core.py` | 共享核心（被其他模块导入，不直接运行） | — |
| **`rag_skill.py`** | **[技能模式] 纯检索接口** | **`--query`, `--kb`, `--json`** |
| **`rag_standalone.py`** | **[独立模式] 检索+LLM** | **`--query`, `--kb`, `--llm-help`, `--json`** |
| `rag_web_ui.py` | Web 配置界面 | `--port`, `--gen-html` |
| `prompt_manager.py` | Prompt 管理 | `--set`, `--show`, `--reset` |
| `knowledge_base_manager.py` | 知识库管理 | `--create`, `--import`, `--list`, `--delete`, `--set-rule`, `--classify` |
