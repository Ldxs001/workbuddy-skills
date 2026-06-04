---
name: drawiodo
author: wUwproject
license: MIT
version: 2.2.2
description: draw.io 自动做图 Skill。当用户要求画图、生成图表、做架构图、流程图、UML、ER 图、时序图、思维导图等时触发。生成 .drawio 文件并用 draw.io 打开。支持思考-确认-迭代-版本回溯的完整工作流。
tags: ['diagram', 'drawio', 'flowchart', 'architecture', 'uml', 'er', 'visualization']
allowed-tools: ['Bash', 'Read', 'Write', 'Edit']
trigger: ['画一个.*图|生成.*图|做一个图表', '架构图|流程图|UML|ER图|时序图|思维导图', 'draw\\.io|drawio|diagrams\\.net', '网络拓扑|组织架构|系统架构']
trigger_negative: true
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: skills/.standardization/drawiodo/data/
external_data_dir: true
meta_field_sync: true
---
# drawiodo: draw.io 自动做图 Skill

## 触发条件

当用户提出以下意图时触发：
- "画一个 xxx 图"、"生成 xxx 图"、"做一个图表"
- "架构图"、"流程图"、"UML 类图"、"ER 图"、"时序图"、"思维导图"
- "用 draw.io 画"、"生成 drawio 文件"
- "画网络拓扑"、"画组织架构"、"画系统架构"
- "按照这个示例改成..."、"参照这个图改..."、"基于这个样式做一个..."
- 用户提供截图/示例文件并要求生成类似图表
- 任何涉及 draw.io / diagrams.net 的需求

## 不触发

以下情况**不触发**本技能：
- 用户只是问"你会画图吗"、"有什么画图工具"——闲聊
- 用户明确要求用其他工具（如"用 mermaid 画流程图"）
- 用户只是提到"图"字但没有画图意图（如"这个图怎么读"）
- 用户要求编辑已有的图片文件（如 .png/.jpg）——本技能生成的是 .drawio 文件

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

1. **自然语言 → 图表**：理解用户描述，自动判断图表类型，生成 .drawio 文件
2. **8 种模板**：流程图、架构图、UML 类图、ER 图、树形图、时序图、思维导图、网络拓扑
3. **迭代更新**：在现有文件基础上精确更新，支持版本回溯（最多 5 版本）
4. **思考-确认-执行工作流**：先分析需求、展示方案、等待确认，再动手画图
5. **本地预览**：生成后用 `draw.io.exe` 打开，即时查看结果

## 工作流程

1. **思考分析（Think）**：分析用户需求，判断图表类型和输入类型，输出结构化思考结果
2. **方案确认（Confirm）**：向用户展示分析方案，用 AskUserQuestion 等待确认 
3. **迭代更新（Iterate）**：确认后生成/更新图表，每次更新前保存版本 
4. **版本回溯（Version Control）**：支持随时回溯到之前的版本（v1~v5）

→ 详见 [执行流程详解](references/guide.md)

## 执行流程（4 阶段工作流）

本技能采用 **思考(Think) → 确认(Confirm) → 迭代(Iterate) → 版本回溯(Version Control)** 四阶段工作流。

→ 详见 [执行流程详解](references/guide.md)

**各阶段要点**：
- **Think**：分析用户需求，判断图表类型和输入类型，输出结构化思考结果 
- **Confirm**：向用户展示方案，用 AskUserQuestion 等待确认（必须确认后才能动手）
- **Iterate**：在现有文件基础上精确更新，每次更新前保存版本（v1→v2→v3...）
- **Version Control**：最多保留 5 个版本，支持随时回溯 

**快捷模式**（可跳过确认）：
1. 简单流程图（3-5 个步骤的线性流程）
2. 明确的模板调用（用户给出完整的 JSON spec）
3. 已确认方案后的迭代更新 

**版本管理命令**：
```bash
python {SKILL_DIR}/scripts/drawio_version.py init <文件.drawio> "初始版本"
python {SKILL_DIR}/scripts/drawio_version.py save <文件.drawio> "更新了 XX"
python {SKILL_DIR}/scripts/drawio_version.py list <文件.drawio>
python {SKILL_DIR}/scripts/drawio_version.py restore <文件.drawio> v2
```

---

## 生成图表

### 方式 A - Python API 调用（推荐）

```python
import sys
sys.path.insert(0, "{SKILLS_DIR}/drawiodo/scripts")
from drawio_templates import *

# 流程图 
builder = create_flowchart(["开始", "处理", "结束"])
builder.save("output.drawio")

# 架构图 
builder = create_architecture([
    {"name": "Frontend", "components": ["React", "Vue"], "color": Styles.BLUE_NODE},
    {"name": "Backend", "components": ["API", "Auth"], "color": Styles.GREEN_NODE},
])
builder.save("output.drawio")

# 自定义（完全控制） 
from drawio_gen import DrawIOBuilder, Styles
builder = DrawIOBuilder(name="My Diagram")
builder.add_node("Node1", 100, 100, 120, 60, style=Styles.BLUE_NODE)
builder.add_node("Node2", 100, 220, 120, 60, style=Styles.GREEN_NODE)
builder.connect(node1, node2, "label")
builder.save("output.drawio")
```

### 方式 B - CLI 调用 

```bash
cd {workspace}
python {SKILL_DIR}/scripts/drawio_agent.py "画一个用户登录流程图：输入账号 → 验证 → 查询数据库 → 返回结果"
python {SKILL_DIR}/scripts/drawio_agent.py spec.json  # JSON 模式 
```

### 方式 C - JSON spec 文件 

```json
{
  "type": "flowchart",
  "title": "用户登录",
  "steps": ["输入账号", "验证密码", "查询数据库", "返回结果"]
}
```

支持的 type：`flowchart`, `architecture`, `class_diagram`, `er_diagram`, `tree`, `sequence`, `mindmap`, `network`

### 打开预览 

```bash
"C:\Program Files\draw.io\draw.io.exe" "生成的文件路径"
```

---

## API 参考 

→ 详见 [API 参考](references/api_reference.md)

## 坐标系与布局规则 

→ 详见 [坐标系与布局规则](references/layout_rules.md)

## 已知问题与修复记录 

→ 详见 [已知问题与修复记录](references/known_issues.md)

→ 详见 [反模式](references/antipatterns.md)
→ 详见 [常见问题](references/faq.md)

---

## 输出规范 

- 输出目录：`{workspace}` 
- 文件命名：`{类型}_{描述}.drawio`，如 `architecture_microservice.drawio`
- 生成后自动用 draw.io 打开预览 
- 交付附件给用户 
- 每次生成/更新后初始化或更新版本管理 

## 核心文件 

| 文件 | 路径 | 说明 |
|------|------|------|
| 核心库 | `scripts/drawio_gen.py` | 节点/连线/容器/XML 生成 |
| 模板库 | `scripts/drawio_templates.py` | 8 种图表模板 |
| Agent 入口 | `scripts/drawio_agent.py` | CLI/自然语言解析 |
| 版本管理 | `scripts/drawio_version.py` | 5 版本回溯系统 |
| draw.io | `C:\Program Files\draw.io\draw.io.exe` | 本地安装路径 |
| 输出目录 | `{workspace}` | 所有图表输出到此 |
