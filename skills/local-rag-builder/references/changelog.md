# 更新日志 — local-rag-builder

## 0.3.0 (2026-06-06)

### 重构
- **双模式架构**：拆分为 `rag_skill.py`（技能模式，纯检索无 LLM）和 `rag_standalone.py`（独立模式，检索+LLM 全链路）
- `rag_core.py` 移除所有 LLM 依赖，改为纯核心层。新增 `format_skill_output()` 返回结构化 JSON（含已填充 prompt）
- `embedding_model_manager.py`：路径查找改为通用内容感知方案（`_normalize` + `_name_similarity` + `_is_model_dir`），不再依赖任何特定变形模式

### 新增
- `rag_skill.py`：零 LLM 依赖的技能接口，仅返回结构化 JSON，供任何智能体使用
- `rag_standalone.py`：独立系统，含交互式 CLI + `/llm-help` 命令 + 内置三个 LLM 方案接入指南
- `references/llm-setup.md`：结构化 LLM 接入文档（LM Studio / Ollama / vLLM 三方案含配置方式）

### 修复
- `rag_web_ui.py`：修复 `verify_llm_connection` 导入路径（已迁移到 rag_standalone）
- `config.py`/`prompt_manager.py`/`rag_env_setup.py`：exception 覆盖加固
- R-10/R-11/R-23 合规修复（产出物路径迁移、文档引用更新）
- 文档引用 `rag_interface.py` 全部更新为 `rag_skill.py`/`rag_standalone.py`

## 0.2.0 (2026-06-06)

- 重构: 嵌入模型路径查找改为通用内容感知方案（`_normalize` + `_name_similarity` + `_is_model_dir`），不再依赖特定变形模式
- 重构: `verify_model` 改用 `_is_model_dir` 通用检测
- 重构: `get_model_path` 改用相似度评分匹配
- 修复: exception 覆盖率加固（config.py/prompt_manager.py/rag_env_setup.py）
- 测试: 功能测试通过（D1-D6: 0 BLOCK, 57 WARN）

## 0.1.1 (2026-06-06)

- 修复: 数据目录路径合规（R-12）
- 修复: frontmatter 补充 trigger/trigger_negative/license 字段
- 修复: 版本号格式合规

## 0.1.0 (2026-06-06)

- 初始版本
- 环境自动检测与修复（Python 版本、缺失包）
- 嵌入模型多源下载（ModelScope/HuggingFace/LLM 搜索）
- 完整性校验与路径修正
- 6 种文本切分策略 + 组合切分
- 多知识库管理与自动分类
- Prompt 模板持久化
- Web 可视化配置界面
- 结构化 JSON 接口（智能体调用）
- 交互式 CLI 界面
