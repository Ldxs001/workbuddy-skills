# Orchestrator 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
版本号遵循语义版本控制（`orchestrator/__init__.py` 唯一源）。

---

## [1.1.0] - 2026-07-10

### 重构
- **项目迁移**：从 `D:\Code~\PythonProject\local_agent\` 迁移到 `C:\Users\sm001\WorkBuddy\Orchestrator\`
- **统一结构**：所有核心代码移入 `orchestrator/` 子包，`run_agent.py` → `main.py`
- **配置整理**：`settings.json` → `data/config/settings.json`，`working_memory.json` → `data/memory/working_memory.json`
- **文档补齐**：新增 `llms.txt`、`CHANGELOG.md`、`LICENSE`、`requirements.txt`
- **名称统一**：所有 import 从 `local_agent.xxx` → `orchestrator.xxx`
