# Skill Pipeline Orchestrator

> **技能流水线编排工具** — 用编排替代 ReAct，技能是积木，编排是图纸。
> 作者：wUwproject | 许可证：Apache 2.0

本工具替代传统的 ReAct 循环架构，将技能（Skill）视为积木、编排（Pipeline）视为图纸，LLM 只负责读 SKILL.md 和粘合数据。

## 核心概念

- **Skill Pipeline Orchestrator** — 放弃 ReAct 循环"LLM 当大脑"架构，改为确定性技能组合
- **三种编排模式**：顺序（seq）、并行（par）、循环（loop）
- **LLM 粘合层**：自动读取前后技能的 SKILL.md，完成格式转换
- **技能无需改造**：直接使用 ~/.workbuddy/skills/ 下任意 SKILL.md 定义的技能

## 文件结构

| 文件 | 作用 |
|------|------|
| `gui_agent.py` | tkinter GUI 三区布局（左栏技能列表 / 右栏编排画布 / 底部输入+控制） |
| `chain_model.py` | SkillInfo / PipelineNode / Pipeline 数据模型，JSON 序列化 |
| `chain_engine.py` | 执行引擎 + 固化功能（skill-sub 优化/语义拆分/三步自审/颜色校验/HTML 校验/Python 自动装包） |
| `skill_scanner.py` | 扫描 ~/.workbuddy/skills/ 下所有 SKILL.md，纯字符串解析 YAML frontmatter |
| `llm_client.py` | 纯 urllib OpenAI 兼容客户端（支持自动续接） |
| `agent_config.py` | 配置管理 |
| `model_manager.py` | 模型管理 |
| `run_agent.py` | 旧版运行入口 |
| `agent_loop.py` | 旧版 ReAct 循环（保留兼容） |
| `tools/` | 工具目录 |

## 内置固化功能

| 功能 | 开关 | 说明 |
|------|------|------|
| skill-sub 优化 | 勾选 | 自动分析流水线：连续同技能→循环，独立步骤→并行，重复→去重 |
| 语义拆分 | 勾选 | 5W2H 分析用户意图，拆解为子步骤 |
| 三步自审 | 勾选 | 每步执行→审查→推进循环，自动重试×3 |
| 自动续接 | 配置 | LLM 输出截断时自动追加"继续"请求 |
| 文件原子操作 | 常驻 | 原子读写追加删 |
| 颜色校验 | 常驻 | WCAG 对比度检测 |
| Python 自动装包 | 常驻 | ImportError 自动 pip install |
| HTML 校验 | 常驻 | 标签配对/emoji/CDN 检测 |

## 使用方法

```bash
# 启动 GUI
python gui_agent.py
```

GUI 提供完整交互：搜索技能 → 拖入编排画布 → 设置模式 → 输入任务 → 运行。

## 许可证

Apache 2.0 — 详见 LICENSE 文件
