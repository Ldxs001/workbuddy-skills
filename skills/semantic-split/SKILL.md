---
name: semantic-split
slug: semantic-split
displayName: 语义拆分与智能规划
description: 语义拆分与智能规划。将自然语言拆分为结构化需求块，三管线协同调度（正则结构分析→bge语义匹配→bge-reranker重排序），5W2H提取与约束标注增强语义理解，双视角推理整合为单一执行步骤，自增强闭环自动沉淀能力级JSON模板，7门禁钩子系统管控流程。
trigger: ['帮我做', '我需要', '交给你了', '帮我分析', '需求拆分']
license: MIT
data_dir: .standardization/semantic-split/data
version: 3.0.2
author: wUwproject
tags: ['semantic-split', 'task-planning', 'json-accumulation', 'progressive-loading', '5w2h', 'constraint-annotation', 'self-reinforcing-loop']
trigger_negative: true
external_data_dir: true
sensitive_access: false
critical_write: false
permission_weight: LOW
meta_field_sync: true
create_permissions_md: true
faq_quality: improve_qa
h1_position: true
trigger_quality: refine_triggers
---
# semantic-split

> 语义拆分与智能规划。三管线递进调度 + 自增强闭环沉淀。

## 输入输出

- **输入**：≤2000 字纯文本（任务描述）
- **输出**：JSON 结构化需求块（含步骤列表、WP 分解、钩子门禁状态）
- **依赖**：sentence-transformers（embedding + rerank）

## 触发条件

**正向触发：**
- [需求拆分] "帮我把这个需求拆开" / "拆分一下这个任务"
- [语义规划] "帮我规划一下怎么做" / "整理一下思路"
- [5W2H分析] "帮我分析这个需求" / "5W2H分析一下"
- [JSON管理] "管理json文件" / "json_manager"
- [渐进匹配] "加载规则" / "匹配json"

**不触发：**
- 简单问答、闲聊、问候
- 单步任务

---

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | **Pipeline B 结构分析** | 纯正则（5W2H/主语/约束/分块/注意力锚定），零外部依赖 |
| 2 | **Pipeline A 语义匹配** | 正则→bge-small(embedding)→bge-reranker(CrossEncoder)|
| 3 | **Pipeline C 智能体推理** | 结构分析 + 模板参考 喂给智能体 → 增强思考 → 生成步骤 |
| 4 | **覆盖率阈值路由** | 正则层覆盖率≥80% 直接通过，<80% 升级到 bge 语义层 |
| 5 | **自增强闭环** | 执行 → 通用化 → 保存为 JSON 模板 → 下次命中 → 0 LLM |
| 6 | **模板库扫描** | 每次请求自动扫描 capabilities/ 库，命中≥0.6 则作为 few-shot 参考或直接复用 |
| 7 | **10 道门禁钩子** | input_valid → b_pipeline_done → a_scan_done → decision_made → llm_generated → **focus_reasoning → divergent_reasoning → integration_reasoning** → template_saved → wp_done |
| 8 | **json 管理工具** | `json_manager.py` CLI 统一管理能力级/规则级 json |

> 📚 渐进式体系：`SKILL.md` 为入口，详细内容按需加载见下方索引。

### 渐进式文件索引

| 文件 | 内容 |
|-----|------|
| `references/LICENSE.md` | MIT 许可协议 |
| `references/changelog.md` | 版本更新日志 |
| `references/attribution.md` | 第三方组件版权声明与许可说明 |
| `references/json_schema.md` | 能力级/规则级 JSON 格式定义 |
| `references/loading_decision_tree.md` | 渐进加载决策流程（含自增强闭环） |
| `references/planning_rules.md` | 双视角推理与规划生成规则 |
| `references/split_rules.md` | 语义拆分规则 |
| `references/constraint_annotation.md` | 约束标注规则与注意力锚定 |
| `references/examples.md` | 各功能输出格式示例 |
| `references/faq.md` | 常见问题与排错 |
| `references/permissions.md` | 权限扫描与风险评估 |
| `references/task_type_defaults.md` | 5W2H 任务类型默认值映射 |
| `references/antipatterns.md` | 反模式指南 |
| `references/automation_tasks.md` | 自动任务配置 |

---

## 快速开始

```bash
# 0. 安装依赖
pip install sentence-transformers huggingface-hub

# 1. 下载 BGE 模型
python scripts/model_manager.py --download bge-small
python scripts/model_manager.py --download bge-rerank

# 2. 三管线调度
python scripts/semantic_pipeline.py --text "帮我做一份PPT" --hooks

# 3. 查看流程门禁
python scripts/semantic_pipeline.py --text "帮我分析Q2数据" --hooks

# 4. JSON 管理（模板库操作）
python scripts/json_manager.py scan --keywords PPT
```

---

## 三管线职责

| 管线 | 方法 | 模型 | 产出 |
|:----|:----|:----:|:----|
| **B 结构分析** | 纯正则 | **无** | 5W2H七维 / 主语 / 约束等级 / 分块 / 注意力锚定 |
| **A 语义匹配** | 正则 → embedding → rerank | bge-small + bge-reranker ✅ | 模板库扫描 / 相似度匹配 / 约束分类 |
| **C 智能体推理** | 智能体原生推理 | — | 步骤列表 / WP分解 / 模板沉淀 |

> Pipeline B 的 5W2H / 主语 / 约束提取不需要模型，纯正则完成。
> 正则词表覆盖常见动词/主语/时间/地点/数量词，边界 case 由 Pipeline C（LLM）推理补全。
> bge-small / bge-reranker 不参与结构分析，只做模板库语义匹配。

## 工作流程

```
输入文本
    │
    ▼
[钩子1] input_valid → 输入校验
    │
    ▼
[钩子2] b_pipeline_done → Pipeline B：正则层
    │  5W2H 提取 / 主语识别 / 约束标注 / 分块
    │  （零模型，纯 regex）
    │
    ▼
[钩子3] a_scan_done → Pipeline A：模板库扫描
    │  bge-small: embedding 编码 → 余弦相似度匹配
    │  bge-reranker: CrossEncoder 重排序
    │  （仅模板匹配，不参与结构分析）
    │  ┌─ 命中 ≥0.6 → 模板作为 few-shot 参考
    │  └─ 未命中   → 空
    │
    ▼
[钩子4] decision_made → 渐进决策
    │  ┌─ 模板命中 ≥0.6 → 直接复用（0 智能体调用）
    │  └─ 未命中       → 传递 结构分析结果 + 模板参考 给智能体
    │
    ▼
[钩子5] llm_generated → Pipeline C：智能体推理
    │  拿到: 5W2H + 约束 + 结构分析 + 模板参考(few-shot)
    │
    ▼
[钩子6] focus_reasoning → 聚焦推理（保守方案）
    │  智能体必须执行: 生成安全可靠的执行方案
    │
    ▼
[钩子7] divergent_reasoning → 发散推理（创新方案）
    │  智能体必须执行: 生成创新大胆的执行方案
    │
    ▼
[钩子8] integration_reasoning → 整合推理
    │  智能体必须执行: 聚焦方案(骨架) + 发散方案(创新点) → 最终方案
    │  输出: 步骤列表
    │
    ▼
[钩子9] template_saved → 自动保存为能力级 JSON
    │  步骤通用化 → 写入 capabilities/{task}_v1.json
    │
    ▼
[钩子10] wp_done → WP 分解完成
    │
    ▼
输出 JSON
```

---

## 模型清单

| 模型 | 管线 | 大小 | 协议 |
|:----|:----|:---:|:----:|
| BAAI/bge-small-zh-v1.5 | Pipeline A 嵌入层 | 92MB | MIT |
| BAAI/bge-reranker-base | Pipeline A 重排序层 | 1.1GB | MIT |
| **合计** | | **~1.2GB** | **全部商业友好** |

> Pipeline B 为纯正则实现，零模型依赖。
> 无外部 API 调用，无 LLM 配置需求。Pipeline C 由智能体原生推理。
