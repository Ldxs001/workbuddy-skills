---
name: drawiodo
author: wUwproject
license: MIT
version: 2.4.0
description: draw.io 自动做图 Skill。当用户要求画图、生成图表、做架构图、流程图、UML、ER 图、时序图、思维导图等时触发。生成 .drawio 文件并用 draw.io 打开。支持思考-确认-迭代-版本回溯的完整工作流，8 个 Hook Point 安全校验。
tags: ['diagram', 'drawio', 'flowchart', 'architecture', 'uml', 'er', 'visualization']
allowed-tools: ['Bash', 'Read', 'Write', 'Edit']
trigger: ['画一个.*图|生成.*图|做一个图表', '架构图|流程图|UML|ER图|时序图|思维导图', 'draw\\\\\\\\.io|drawio|diagrams\\\\\\\\.net', '网络拓扑|组织架构|系统架构']
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

## 钩子系统（强制约束）

**关键操作由 Python 端自动执行，不依赖 LLM 自觉。**
备份、版本管理初始化、版本上限清理均由钩子在脚本层直接完成，
LLM 无权跳过这些操作。

→ 详见 [钩子系统](references/hooks.md)

### 8 个 Hook Point

| Hook Point | 强制操作 | 说明 |
|---|---|---|
| `pre_think` | 输入非空校验（阻断） | 空输入直接阻断 |
| `post_think` | 分析结果校验 | 缺失字段仅警告 |
| `pre_confirm` | 选项完整性校验（阻断）+ 快捷跳过（清除选项） | 不足 2 项或快捷跳转均阻断/跳过 |
| `post_confirm` | 用户选择解析 | - |
| `pre_iterate` | 自动创建目录 + **自动备份** | 备份由 Python 调用 VersionManager |
| `post_iterate` | 输出校验 + **自动初始化版本管理** + **自动打开预览** | init 和预览都由 Python 执行 |
| `pre_vc` | **自动清理超限版本** | 删除最旧版本由 Python 执行 |
| `post_vc` | 版本状态报告 | - |

### 执行规则

- **abort=True** -> 立即阻断流程（LLM 无权绕过）
- **success=False 但不 abort** -> 记录警告，不阻塞
- 所有操作由 Python 端算法强制完成

### 在阶段代码中调用

```python
from drawio_hooks import hooks

# 在阶段开始时
results = hooks('pre_iterate', {
    'output_path': output_path,
    'is_update': True,          # 会触发自动备份
})
for r in results:
    if r.abort:
        return  # 钩子已处理，阻断并返回
    if not r.success:
        print(f'Warning: {r.message}')

# 在阶段结束时
results = hooks('post_iterate', {
    'output_path': output_path,  # 会触发自动 init 版本管理
})
```

### 注册/注销自定义钩子

```python
from drawio_hooks import register, unregister

@register('pre_think', name='my_check', description='自定义校验')
def my_hook(ctx):
    if 'special' not in ctx.get('user_input', ''):
        return {'success': False, 'message': '缺少特殊参数', 'abort': True}
    return {'success': True, 'message': 'ok'}

unregister('post_iterate', 'preview_trigger')  # 禁用自动预览
```

### CLI 管理命令

```bash
python {SKILL_DIR}/scripts/drawio_hooks.py list     # 查看所有注册钩子
python {SKILL_DIR}/scripts/drawio_hooks.py check    # 全流程自检
python {SKILL_DIR}/scripts/drawio_hooks.py history  # 查看执行历史
```

---

## 生成图表

→ 详见 [图表生成参考](references/generation.md)

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

- 文件命名：`{类型}_{描述}.drawio`，如 `architecture_microservice.drawio`
- 生成后自动用 draw.io 打开预览 
- 交付附件给用户 
- 每次生成/更新后初始化或更新版本管理 
- 路径信息见 `_meta.json` data_dir 声明 + frontmatter data_dir 字段

## 核心文件 

| 文件 | 路径 | 说明 |
|------|------|------|
| 核心库 | `scripts/drawio_gen.py` | 节点/连线/容器/XML 生成 |
| 模板库 | `scripts/drawio_templates.py` | 8 种图表模板 |
| Agent 入口 | `scripts/drawio_agent.py` | CLI/自然语言解析 |
| 版本管理 | `scripts/drawio_version.py` | 5 版本回溯系统 |
