# Skill Pipeline Orchestrator 架构文档

> Skill Pipeline Orchestrator — 用编排替代 ReAct，技能是积木，编排是图纸。
> 作者：wUwproject | 许可证：Apache 2.0
> 更新：2026-07-06

---

## 一、系统概览

Skill Pipeline Orchestrator 是一个**技能流水线编排工具**，核心理念是放弃传统的 ReAct 循环（"LLM 当大脑"）架构，改为**确定性技能组合**架构：

```
用户输入
  → [语义拆分 (可选)]         # 5W2H 分解意图为子步骤
    → [skill-sub 优化 (可选)]  # 算法级优化：循环/并行/去重
      → [执行引擎]            # 遍历 Pipeline 节点
        → [粘合层]            # LLM 读取前后 SKILL.md 做格式转换
        → [LLM/脚本执行]      # 调用技能（LLM 或脚本模式）
        → [自审 (可选)]       # HTML 校验/颜色检查/LLM 审查
          ↖ 失败重试 ≤3 次
      → [输出]                # FILE marker 解析 + 文件保存
```

### 1.1 核心设计原则

| 原则 | 说明 |
|------|------|
| **技能 = 积木** | 不改动任何现有技能，通过编排组合达成复杂任务 |
| **编排 = 图纸** | 顺序/并行/循环三种模式，Pipeline JSON 序列化可保存/可加载 |
| **LLM = 胶水** | LLM 只做两件事：读 SKILL.md 理解技能接口、粘合前后输出格式 |
| **固化 > 调用** | 通用能力（优化/拆分/审查/颜色/文件）硬编码内置，不依赖外部技能 |
| **可选 > 强制** | 所有增强功能都有开关，不勾选 = 直通执行 |

---

## 二、三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | `gui_agent.py` | tkinter 三区 GUI：技能列表 / 编排画布 / 底部输入+控制 |
| **业务层** | `chain_engine.py` / `chain_model.py` | 执行引擎、固化功能、数据模型 |
| **基础设施** | `llm_client.py` / `skill_scanner.py` / `agent_config.py` | LLM 通信、技能扫描、配置管理 |

### 2.1 目录结构

```
local_agent/
├── gui_agent.py              # 主窗口 GUI（~820 行）
├── chain_engine.py            # 执行引擎 + 所有固化功能（~830 行）
├── chain_model.py             # 数据模型（SkillInfo / PipelineNode / Pipeline）
├── llm_client.py              # 纯 urllib OpenAI 兼容客户端
├── skill_scanner.py           # SKILL.md YAML frontmatter 扫描器
├── agent_config.py            # 配置管理（AgentConfig / 默认值）
├── model_manager.py           # 模型管理器
├── run_agent.py               # 旧版运行入口（保留兼容）
├── agent_loop.py              # 旧版 ReAct 循环（保留兼容）
├── direct_llm_client.py       # 直加载 GGUF 客户端
├── memory.py                  # 记忆管理
├── tool_base.py               # 工具基类
├── tools/                     # 工具目录
│   ├── file_tool.py
│   ├── rag_tool.py
│   ├── skill_loader.py
│   └── web_tool.py
├── working_memory.json        # 工作记忆持久化
└── __init__.py                # 模块导出
```

---

## 三、数据模型（chain_model.py）

### 3.1 SkillInfo

扫描到的技能元数据，来自 SKILL.md 的 YAML frontmatter：

```
name / display_name / description / version / author
tags / triggers / path / permission_weight
sensitive_access / critical_write / error
```

### 3.2 PipelineNode

流水线中的一个节点（支持递归嵌套）：

```
id            — UUID hex[:8]
skill_name    — 技能 slug
display_name  — 显示名称
mode          — seq | par | loop
children      — 子节点列表（par/loop 容器用）
loop_start    — 循环起始
loop_end      — 循环结束
loop_times    — 循环次数
input_text    — 用户对该步骤的输入
```

### 3.3 Pipeline

完整流水线：

```
name           — 流水线名称
nodes          — PipelineNode 列表
optimize       — 是否启用 skill-sub 优化
semantic_split — 是否启用语义拆分
triphasic      — 是否启用三步自审
created        — 创建时间
updated        — 更新时间
```

### 3.4 序列化

- `to_dict()` / `to_json()` — 递归序列化 nodes（含 children）
- `from_dict()` / `from_json()` — 递归反序列化
- JSON 格式用于：保存/加载流水线、LLM 粘合上下文

---

## 四、GUI 架构（gui_agent.py）

### 4.1 三区布局

```
┌─────────────────────┬──────────────────────────────────┐
│ 左栏 260px          │ 右栏 (剩余宽度)                   │
│ 技能列表            │ 编排画布                          │
│ [搜索框]            │ [流水线名称]                      │
│ ┌─────────┬───┬──┐ │ ┌──────────────────────────────┐  │
│ │ 技能名  │版本│描述│ │ │ 1. hug-html [SEQ]          │  │
│ │ hug-html│3.0│HTML│ │ │ 2. 并行 3个 [PAR]          │  │
│ │ git-sync│2.2│同步│ │ │ 3. 循环 1→3 [LOOP]         │  │
│ └─────────┴───┴──┘ │ └──────────────────────────────┘  │
│ 双击添加到流水线    │ [+顺序] [+并行] [+循环] [×删除]   │
├─────────────────────┴──────────────────────────────────┤
│ 底部: [📎选文件] [📁选文件夹] [⚙设置]  输入框   [▶运行] │
│        [💾保存链] [📂加载链]         进度: 就绪         │
└────────────────────────────────────────────────────────┘
```

### 4.2 交互流程

1. **技能扫描** — `_scan_skills()` → `skill_scanner.scan_skills()` → 填充 Treeview
2. **搜索过滤** — `search_var.trace("w")` → `_filter_skills()` → 实时过滤
3. **添加步骤** — 双击技能或点击按钮 → 创建 PipelineNode → 添加到 `pipeline.nodes`
4. **容器操作** — 选中多个节点 → 包裹为 par/loop 容器
5. **运行** — `_run_pipeline()` → 异步线程 → `execute_pipeline()`
6. **结果展示** — `_show_result()` → 弹窗显示 + 文件保存按钮
7. **保存/加载** — 序列化为 JSON → `chains/` 目录

### 4.3 设置对话框

PanedWindow 双栏布局（左设置 + 右手册）：

| 设置区域 | 内容 |
|---------|------|
| 技能目录 | Listbox + 添加/删除 |
| 超时 | LLM 超时、脚本执行超时 |
| max_tokens | 最大输出 token 数 |
| 自动续接 | 启用/禁用、续接 token 数、续接次数 |
| 可选功能 | 语义拆分、三步自审（均勾选启用） |

---

## 五、执行引擎（chain_engine.py）

### 5.1 执行流

```
execute_pipeline():
  1. LLM 连接预检
  2. [语义拆分] _semantic_split() — 可选
  3. [skill-sub 优化] _optimize_pipeline() — 可选
  4. 遍历 flat nodes:
     a. [粘合] 读前后 SKILL.md → _llm_glue() → 格式转换
     b. [执行] execute_node():
        - seq → 读 SKILL.md → 脚本执行 or LLM 执行
        - par → threading 并行执行 children
        - loop → 循环执行 children
     c. [自审] _triphasic_execute_step() — 可选
  5. FILE marker 解析 + 文件保存
```

### 5.2 粘合机制（_llm_glue）

```
前一个技能输出 (任意格式)
  → LLM 读前一个技能的 SKILL.md（了解输出格式）
  → LLM 读后一个技能的 SKILL.md（了解输入要求）
  → LLM 精确转换格式
  → 输出给下一个技能执行
```

### 5.3 技能执行（execute_node）

两种模式自动选择：

| 条件 | 执行方式 | 说明 |
|------|---------|------|
| 存在主脚本 | `_run_script()` | subprocess 运行 `.py`/`.bat`/`.sh` |
| 无主脚本 | `_llm_call()` | LLM 读取 SKILL.md + 上下文执行 |

### 5.4 并行/循环执行

- **并行**：`threading.Thread` → `join(timeout=1800)` → 合并结果
- **循环**：顺序遍历 `children` → 当前输出作为下次输入 → `loop_times` 控制次数

---

## 六、固化功能详解

### 6.1 skill-sub 优化（`_optimize_pipeline`）

纯算法，不调任何外部技能：

| 阶段 | 算法 | 条件 | 操作 |
|------|------|------|------|
| 1 | 连续重复检测 | 同 skill_name 连续 ≥2 次 seq | 包裹为 loop 节点 |
| 2 | 并行检测 | 不同 skill 连续 ≥3 个 seq | 包裹为 par 节点 |
| 3 | 精确去重 | 优化后相邻完全相同 seq | 删除 |
| 4 | 原样保留 | 其他情况 | 顺序不变 |

### 6.2 语义拆分（`_semantic_split`）

固化 semantic-split 的 5W2H 正则提取：

```
正则匹配: 什么/为什么/谁/哪里/什么时候/怎么做/多少
步骤拆分: "先...再..." "第一步...第二步..." 标记
输出: [{step, desc, 5w2h, depends_on}]
```

### 6.3 三步自审（`_triphasic_execute_step`）

固化 triphasic-execution 的 Execute→Review→Advance：

```
步骤:
  Execute  → 调用 execute_node()
  Review   → _self_review_output():
               ├── HTML 校验（标签配对/emoji/CDN）
               ├── 颜色对比度检查（WCAG ≥ 3:1）
               └── LLM 深度审查（输出质量/排版/代码）
  Advance  → 通过 → 继续下一步
          → 不通过 → 审查意见追加到上下文 → 重试（最多 3 次）
```

### 6.4 常驻内置工具

| 工具 | 功能 | 实现 |
|------|------|------|
| `_file_op()` | 原子读写追加删 | 临时文件 + `os.replace` 原子写入 |
| `_color_validate()` | 颜色格式校验 | `#RGB` / `#RRGGBB` 正则 + 规范化 |
| `_calc_contrast()` | WCAG 对比度计算 | 相对亮度公式 → 对比度比 |
| `_color_check()` | 全文颜色冲突检测 | 扫描所有 `#RRGGBB`，检出 < 3:1 的对 |
| `_validate_html()` | HTML 结构校验 | 标签配对、emoji 检测、外部 CDN |
| `_auto_heal_run()` | Python 自动装包 | ImportError → `pip install` → 重试 ×3 |

---

## 七、LLM 客户端（llm_client.py）

### 7.1 架构

```
LLMClient
  ├── __init__(config: AgentConfig)   # 从配置初始化
  ├── check_connection()              # GET /v1/models 检测
  ├── set_timeout()                   # 可设到 86400s（24h）
  ├── set_max_tokens()                # 可设到 131072
  ├── set_continuation_tokens()       # 续接专用 max_tokens
  ├── set_max_continuations()         # 续接次数（max 20）
  ├── chat()                          # 非流式，带自动续接
  ├── chat_stream()                   # 流式
  ├── ask()                           # 单轮 system+user
  └── chat_with_retry()               # 指数退避重试
```

### 7.2 自动续接

```
chat() 逻辑:
  1. 发请求（第一次用 max_tokens）
  2. 检测 finish_reason
  3. 如果是 "length" 且 continuation_enabled:
     → 追加 assistant + user("继续输出") 到 messages
     → 用 _continuation_tokens 发送续接请求
     → 最多 max_continuations 次
  4. 拼接所有输出返回
```

### 7.3 支持的 LLM 后端

| 后端 | base_url |
|------|----------|
| LM Studio | `http://localhost:1234/v1` |
| Ollama | `http://localhost:11434/v1` |
| vLLM | `http://localhost:8000/v1` |

---

## 八、固化 vs 调用的权衡

| 能力 | 实现方式 | 理由 |
|------|---------|------|
| skill-sub 优化 | 硬编码算法 | 依赖分析/并行检测 是纯确定逻辑，无需 LLM |
| 语义拆分 | 正则 + LLM | 5W2H 提取是确定性的，步骤拆解用 LLM |
| 三步自审 | 硬编码 + LLM | HTML/颜色校验是确定性的，深度审查用 LLM |
| 颜色工具 | 硬编码 | WCAG 公式是确定的，零模型调用 |
| 文件操作 | 硬编码 | 原子写入是 OS 操作，零模型调用 |
| Python 装包 | 硬编码 | pip install 是工具调用，零模型调用 |

**原则**：确定性逻辑 → 硬编码；需要理解语义 → LLM。

---

## 九、安全与容错

### 9.1 执行安全

| 机制 | 说明 |
|------|------|
| LLM 连接预检 | 执行前检查后端可达性 |
| 超时控制 | LLM 超时可配（默认 600s）、脚本超时可配（默认 1800s）|
| 续接次数上限 | 最多 20 次续接 |
| 审查重试上限 | 最多 3 次重试 |
| 失败不阻断 | 优化/拆分/审查 失败均返回 False 继续执行 |

### 9.2 输出安全

| 机制 | 说明 |
|------|------|
| 文件名安全化 | 替换 `\ / : * ? " < > \|` 为 `_` |
| 原子写入 | 先写 `.tmp` 再 `os.replace()` |
| FILE marker 解析 | 只有 `[FILE:...]...[/FILE]` 格式触发文件保存 |

---

## 十、演变路线

| 阶段 | 状态 | 内容 |
|------|------|------|
| v1.0 | 完成 | 初始 ReAct 循环架构 |
| v1.1 | 完成 | Skill Pipeline Orchestrator 重写 |
| v1.1+ | 完成 | 布局修复、续接设置、skill-sub 固化 |
| v1.2 | 完成 | 大规模功能固化（7项内置能力） |
| v1.2+ | 当前 | Apache 2.0 发布、架构文档 |
| v1.3 | 规划 | Hug-html 集成、更智能的 LLM 粘合 |
| v1.4 | 规划 | 多模型支持、流水线并行加速 |
