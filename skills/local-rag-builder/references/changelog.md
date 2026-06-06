# 更新日志 — local-rag-builder

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
- Web 可视化设置界面
- 结构化 JSON 接口（智能体调用）
- 交互式 CLI 界面
