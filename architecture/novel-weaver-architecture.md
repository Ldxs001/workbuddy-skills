# novel-weaver 架构与规范体系文档

> 完整解读 v1.35.3 版的架构设计、写作管线（Phase 1→2→3）、5 道流程门禁、六检系统与 30+ 钩子体系
> 生成时间：2026-07-02（v1.35.3 最新更新）

---

## 一、系统概览

novel-weaver 是一个 **结构化小说写作辅助工具集**，采用管线式架构将小说创作分解为 3 个阶段（设置→写作→完结），以 5 道流程门禁和 30+ 钩子实施硬约束管控。

```
用户模糊想法
  ↓
Phase 1 — 场景配置 & 大纲
  ├── LLM 生成场景配置（人物/时代/地点/冲突）
  ├── LLM 生成一级大纲（L01-L15 章标题+概述）
  ├── [门禁] 大纲因果链验证 → outline_causality
  └── 用户确认
    ↓ [用户确认后才可继续]
Phase 2 — 章节写作（逐章循环 L##）
  ├── plan-chapter 规划章子结构（S01-S05）
  ├── [门禁] 子结构因果链验证 → sub_causality
  ├── [门禁] set-phase → writing（require 双门禁）
  │
  ├── 循环：逐子结构写作（串行阻断式）
  │   ├── context_loader 加载上下文（4 区块优先级）
  │   ├── LLM 输出正文 → write-sub 格式校验+组装
  │   ├── atomic_writer 原子写入（fsync）
  │   └── state_manager update-sub
  │
  ├── 最后一子结构写完后 → 自动触发 finalize-chapter
  └── finalize-chapter 六检：
      章内连通性 → 跨章承诺链 → 风格校验 → 逻辑检查
      → 语义检查(BERT) → 推理审核(DeepSeek-R1)
        ↓ [六检全过 → chapter_finalized:L## 门禁标记]
      ↓ [所有章完成]
Phase 3 — 全文完结
  ├── 大纲忠实度报告 → fidelity 门禁
  ├── 结尾收束验证 → ending_verify 门禁
  └── set-phase → stage3_ready → 完结
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI | 人类可读的文档、命令行交互 |
| **业务层** | 18 个 Python 脚本（见目录结构） | 写作管线全部业务逻辑：规划/写作/检查/校验 |
| **数据层** | `.standardization/novel-weaver/projects/` | 项目状态（novel_state.json）、门禁状态、章节正文、检查报告 |

### 1.2 目录结构

```
novel-weaver/
├── SKILL.md                    # 主文件（渐进式入口）
├── _meta.json                  # 7 字段元数据（v1.35.3）
├── references/                 # 渐进式文档
│   ├── execution_standards.md  # 字数管理/文体规范/状态结构/角色表/结尾收束/实体追踪
│   ├── hooks.md                # 全量流程钩子 + 门禁系统一览
│   ├── antipatterns.md         # 常见反模式
│   ├── faq.md                  # 常见问题与排错
│   ├── examples.md             # 使用示例
│   ├── changelog.md            # 版本更新日志
│   ├── permissions.md          # 权限声明
│   └── LICENSE.md              # MIT 许可协议
└── scripts/                    # 核心脚本（18 个 Python）
    ├── _path_utils.py          # 统一路径管理（DATA_DIR / state_path / list_projects）
    ├── novel_workflow_engine.py# 工作流引擎：plan-chapter/write-sub/finalize-chapter/…
    ├── novel_pipeline_gate.py  # 门禁系统：pass/require/status
    ├── novel_state_manager.py  # 状态管理：init/update-sub/add-char/…
    ├── novel_context_loader.py # 上下文加载器：4 区块优先级 + 串行阻断
    ├── novel_atomic_writer.py  # 原子写入器：格式校验 / fsync / 署名检测
    ├── novel_causality_check.py# 因果链验证（大纲级 + 子结构级）
    ├── novel_continuity.py     # 连通性检查（章内 + 跨章承诺链）
    ├── novel_style_check.py    # 风格校验（禁用词/末行标记/行数）
    ├── novel_logic_check.py    # 逻辑检查（角色/时间线/概述匹配）
    ├── novel_semantic_check.py # 语义检查（BERT bge-small-zh，有模型时）
    ├── novel_reasoning_check.py# 推理审核（DeepSeek-R1 1.5B，有模型时）
    ├── novel_entity_extractor.py# 实体关系提取与追踪
    ├── novel_character_registry.py# 角色注册与别名管理
    ├── novel_timeline.py       # 时间线管理
    └── novel_fidelity.py       # 大纲忠实度报告 + 结尾收束验证
```

### 1.3 数据目录结构

```
.standardization/novel-weaver/projects/
├── <项目名>/
│   ├── data/
│   │   ├── novel_state.json       # 项目状态（核心）
│   │   ├── .workbuddy/
│   │   │   └── gate_state.json    # 门禁状态
│   │   └── reports/               # 检查报告输出
│   ├── chapters/                  # 章节正文
│   │   ├── L01/                   # 第 1 章
│   │   │   ├── S01.txt            # 子结构 1
│   │   │   ├── S02.txt
│   │   │   └── ...
│   │   ├── L02/
│   │   └── ...
│   └── .project                   # 路径缓存

.standardization/novel-weaver/models/
├── bge-small-zh/                  # BERT ~92MB（语义检查可选）
└── ds-r1-distill-qwen-1.5b/      # DeepSeek-R1 ~3.7GB（推理审核可选）
```

所有路径由 `_path_utils.py` 统一管理，LLM 禁止手工拼写路径。

---

## 二、三阶段写作管线

### 2.1 Phase 1 — 场景配置 & 大纲（规划阶段）

| 步骤 | 操作 | 脚本 | 产出 |
|:----:|------|------|------|
| 1 | LLM 生成场景配置 | — | novel_info（人物/时代/地点/风土人情/核心冲突） |
| 2 | LLM 生成一级大纲 | — | chapters[]（L01-L15 编号+标题+每章概述） |
| 3 | 大纲因果链验证 | `novel_causality_check.py outline` | outline_causality 门禁 |
| 4 | 用户确认 | — | 确认/修正 |
| 5 | 初始化 novel_state.json | `novel_state_manager.py init` | novel_state.json（chapters/characters/timeline 骨架） |

**数据流**：
```
用户想法 → LLM → scenario_config.json
  → LLM → chapters (L01-L15)
    → causality_check(outline) → [门禁] outline_causality
      → 用户确认
        → state_manager init → novel_state.json
```

### 2.2 Phase 2 — 章节写作（逐章循环）

这是最复杂的阶段，每章按以下子流程执行：

#### 2.2.1 章前规划

| 步骤 | 操作 | 脚本 | 产出 |
|:----:|------|------|------|
| 6 | 规划章子结构 | `workflow_engine.py plan-chapter` | sub_structures[] JSON |
| 7 | 注册到 state | `state_manager.py` | MD5 指纹锁定 + 字数目标 |
| 8 | 子结构因果链验证 | `causality_check.py sub-structure` | sub_causality 门禁 |
| 9 | set-phase writing | `pipeline_gate.py pass` | phase=writing |

`plan-chapter` 必须包含：
- **必填 writing_prompt**（≥50 字符），缺失则 HOOK-BLOCK
- 可选 emotions（角色情绪状态）
- tone（写作基调）
- 新角色检测：sub_structures 中出现未登记角色名时 HARD-BLOCK

#### 2.2.2 每子结构写作循环

```
[循环] 对每个子结构 S01 → S02 → ... → S05（串行，不可并行）：

10. context_loader 加载上下文
    → 4 区块优先级输出：
      A: 标识+硬性字数/文风/署名约束+写作命题框
      B: 末3行+人物+人格+实体+轨迹+节奏
      C: 收尾+钩子+输出模板
      D: (扩展)

11. → [串行阻断] 检测上一子结构是否为 completed
      pending → HOOK-BLOCK 并输出修复命令
      completed → 继续

12. → LLM 输出纯正文（末尾可带可选【别名】行）

13. → write-sub 自动组装：
      标题行 + 别名行 + 标记行 + 正文
      → atomic_writer.v4 校验正文合法性
      → fsync 原子写入 .txt 文件

14. → state_manager update-sub 标记 completed

15. → 新角色登记：add-char（如适用）

[循环结束]
```

#### 2.2.3 上下文加载器（context_loader）4 区块优先级

区块 A — 标识+约束（最高优先级）：
- 项目标识 + phase/stage/section
- 硬性字数范围（meta.length 决定）+ 上浮校验值
- 文风约束 + 署名约束
- 写作命题框（有命题 prompt 原文，无则 fallback 合成）

区块 B — 上下文连续性：
- 末 3 行（与上子结构衔接）
- 参与人物 + 人格矩阵（chapters[].personalities）
- 实体轨迹（chapters[].entity_trajectories）
- 前章已登记的 entity_mentions
- 节奏控制（紧张/舒缓/中性）

区块 C — 收尾约束：
- 收尾类型（ordinary/hook）
- is_ending 标记（该子结构是否为终章终节）
- 输出模板

### 2.3 Phase 3 — 全文完结

| 步骤 | 操作 | 脚本 | 产出 |
|:----:|------|------|------|
| 16 | 大纲忠实度报告 | `novel_fidelity.py generate-report` | fidelity 门禁 |
| 17 | 结尾收束验证 | `novel_fidelity.py verify-ending` | ending_verify 门禁 |
| 18 | set-phase stage3_ready | `pipeline_gate.py require` | phase=stage3_ready |

---

## 三、5 道流程门禁系统

**核心文件**：`novel_pipeline_gate.py`

### 3.1 门禁一览

| 门禁 | 在读什么 | 由谁 pass | 被谁 require | 阻断后果 |
|:----:|---------|-----------|-------------|---------|
| `outline_causality` | 章概述因果链 | causality_check.py outline（自动） | set-phase → writing | LLM 无法开始写作 |
| `sub_causality` | 子结构因果链 | causality_check.py sub-structure（自动） | set-phase → writing | LLM 无法开始写作 |
| `chapter_finalized:L##` | 章完结六检 | finalize-chapter（HARD 全过时） | — | 不阻断 phase，仅标记完成 |
| `fidelity` | 大纲忠实度 | fidelity.py generate-report | set-phase → stage3_ready | LLM 无法推进到完结阶段 |
| `ending_verify` | 结尾收束验证 | fidelity.py verify-ending | set-phase → stage3_ready | LLM 无法推进到完结阶段 |

### 3.2 门禁状态机

所有门禁有序、不可逆。查看状态：
```bash
python novel_pipeline_gate.py status <state_path>
```

输出示例：
```
[门禁状态] 当前阶段: writing
  outline_causality     ✅ PASSED
  sub_causality:L01     ✅ PASSED
  chapter_finalized:L01 ⬜ PENDING
  fidelity              ⬜ PENDING
  ending_verify         ⬜ PENDING
```

### 3.3 阶段转换条件

| 阶段转换 | 前提门禁 | 后果 |
|---------|---------|------|
| Phase 1 → Phase 2 | outline_causality + 用户确认 | 允许开始写作 |
| 每章写作开始 | sub_causality + set-phase writing | 允许 plan-chapter |
| 每章完结 | 六检全部 HARD 通过 | 标记 chapter_finalized:L## |
| Phase 2 → Phase 3 | fidelity + ending_verify | 允许 set-phase stage3_ready |

---

## 四、六检系统（finalize-chapter）

**自动触发**：最后一个子结构写入完成后 write-sub 自动触发，无需手动执行。

### 4.1 六检执行链

```
[1] 章内连通性 (novel_continuity.py)
    SOFT: 检测子结构间时间/角色是否断裂
    输出: 连通性报告（不阻断）

[2] 跨章承诺链 (novel_continuity.py)
    SOFT: 检测上章尾与下章头的关键词续接
    输出: 续接检测报告（不阻断）

[3] 风格校验 (novel_style_check.py)
    HARD: 禁用词检测 / 末行编号检测 / 超200行阻断
    输出: 通过/失败（失败则阻断）

[4] 逻辑检查 (novel_logic_check.py)
    HARD: 角色一致性 + 时间线 + 概述关键词命中率
          命中率 < 30% 则阻断
    输出: 通过/失败（失败则阻断）

[5] 语义检查 (novel_semantic_check.py) — 有模型时可选
    HARD: overview-vs-content 语义对齐 < 0.4 阻断
          + 子结构间语义跳跃 < 0.4 阻断
    SOFT: 情绪偏离 / 同义冗余 / 跨章主题延续
    模型: BAAI/bge-small-zh-v1.5 (92MB, CPU)
    无模型时自动跳过（绝不联网）

[6] 推理审核 (novel_reasoning_check.py) — 有模型时可选
    5 项推理审核:
      ① 因果合理性
      ② 人物行为一致性
      ③ 情绪弧自然度
      ④ 对话匹配度
      ⑤ 论证可靠性
    按结果输出 HARD 或 SOFT
    模型: deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B (~3.7GB, CPU)
    无模型时自动跳过（绝不联网）
```

### 4.2 检查等级矩阵

| 检查 | 等级 | 阻断？ | 依赖模型 | 数据来源 |
|:----:|:----:|:------:|:--------:|---------|
| 章内连通性 | SOFT | 否 | 无 | novel_state.json + chapters/ |
| 跨章承诺链 | SOFT | 否 | 无 | novel_state.json + chapters/ |
| 风格校验 | HARD | 是 | 无 | .txt 文件正文 |
| 逻辑检查 | HARD | 是 | 无 | novel_state.json + .txt |
| 语义检查 | HARD | 是 | bge-small-zh | overview + content |
| 推理审核 | HARD/SOFT | 条件性 | DeepSeek-R1 | 全文分析 |

有 HARD 问题则阻断（不标记门禁），写入 `_fixes.json`；全部通过则标记 `chapter_finalized:L##` 门禁。

---

## 五、30+ 钩子系统

**核心文件**：`references/hooks.md`

### 5.1 钩子类型分类

| 类型 | 数量 | 行为 | 示例 |
|:----:|:----:|------|------|
| **阻断式** | 15+ | 条件不满足则报错退出 | 串行阻断、署名检测、新角色检测 |
| **代码级硬约束** | 5+ | 脚本层面强制执行 | MD5 指纹、原子写入、子结构存在性验证 |
| **软性（不阻断）** | 5+ | 仅提醒不阻止 | 更新/扩写提醒、连通性检查 |
| **信息式** | 3+ | 注入信息供 LLM 参考 | 字数约束注入 |
| **编排式** | 2+ | 自动串联多步操作 | finalize-chapter 自动化 |

### 5.2 关键阻断钩子明细

| 钩子 | 触发时机 | 阻断条件 | 阻断后行为 |
|------|---------|---------|-----------|
| 大纲确认 | Phase 1 完成时 | 未确认 | 禁止进入 Phase 2 |
| 大纲因果链验证 | 用户确认大纲前 | 因果不递进 | 报错退出，需修正大纲 |
| 子结构因果链验证 | plan-chapter 后 | 因果不递进 | 报错退出，需调整子结构 |
| 串行阻断 | 每段写作前（context_loader） | 上一子结构非 completed | HOOK-BLOCK + 输出修复命令 |
| 子结构存在性验证 | 每段写作前 | 未注册子结构 | 报错退出 |
| 署名检测 | 每段写入时 | signature=off | 阻断写入 |
| 角色登记 | 新角色出场时 | 未 add-char | HARD-BLOCK |
| 一键完结章节 | 子结构全部完成后 | HARD 问题存在 | 写入 _fixes.json 并阻断 |
| 结尾收束验证 | 全文完成后 | 收束不完整 | 阻断 set-phase stage3_ready |

---

## 六、核心状态管理

**核心文件**：`novel_state_manager.py`

### 6.1 novel_state.json 结构

```
{
  "project_name": "...",
  "phase": "setting|writing|completed",
  "info": { /* 场景配置 */ },
  "chapters": [{
    "id": "L01",
    "title": "...",
    "overview": "...",
    "personalities": [/* 人格矩阵 */],
    "entity_trajectories": [/* 实体轨迹 */],
    "sub_structures": [{
      "id": "S01",
      "title": "...",
      "state": "pending|writing|completed",
      "writing_prompt": "...",
      "tone": "...",
      "emotions": {"角色": "情绪"},
      "is_ending": false,
      "is_hook": false
    }]
  }],
  "characters": [{
    "id": "...",
    "name": "...",
    "aliases": [],
    "personality": { /* 人格五维度 */ }
  }],
  "timeline": [/* 时间线记录 */]
}
```

MD5 指纹锁定核心字段（chapters/sub_structures/characters），LLM 不可直接更新。

### 6.2 子结构状态转换

```
pending → writing → completed (单向不可逆)

HARD-BLOCK 条件：
  - state=pending 但有 sub_structure 不存在 → 存在性阻断
  - state=pending 但上一子结构非 completed → 串行阻断
  - update-sub 写入新角色但未 add-char → 角色登记阻断
```

---

## 七、模型系统

### 7.1 模型清单

| 模型 | 用途 | 大小 | 是否必需 | 安装方式 |
|:----:|:----:|:----:|:--------:|---------|
| BAAI/bge-small-zh-v1.5 | 语义检查（六检第5步） | 92MB | 可选（无则跳过） | pip install sentence-transformers |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B | 推理审核（六检第6步） | ~3.7GB | 可选（无则跳过） | pip install transformers torch accelerate |

### 7.2 安全约束

- **GPU 安全**：强制 CPU 运行 (`CUDA_VISIBLE_DEVICES=-1`)，避免与 LM Studio 等 GPU 应用冲突
- **断网安全**：无模型时自动跳过，绝不联网下载
- **路径规范**：模型文件缓存到 `.standardization/novel-weaver/models/`，由 `_path_utils.py` 统一管理

---

## 八、核心设计原则

### D1: 管线式流程管控

写作过程分解为 Phase 1→2→3，阶段间以门禁隔开。未通过前置门禁不得进入下一阶段。这防止 LLM 跳过规划直接写作。

### D2: 串行阻断

子结构写作必须串行执行：S01 → S02 → ... → S05。context_loader 检测上一子结构是否为 `completed`，否则 HOOK-BLOCK。这是防止 LLM 同时写多个子结构导致混乱的硬约束。

### D3: 硬约束优先，模型增强可选

六检前 4 步（连通性/风格/逻辑）由 Python 刚性规则驱动，无外部依赖。后 2 步（语义/推理）依赖本地模型，无模型时静默跳过。核心质量关卡不依赖模型可用性。

### D4: MD5 指纹保护

novel_state_manager.py 对核心字段（chapters/sub_structures/characters）做 MD5 指纹校验，LLM 不可通过直接写 JSON 更新这些字段。必须通过 state_manager CLI 操作。

### D5: 别名自动管理

write-sub 时检测正文字末是否有 `【别名】` 声明行。有则剥离并调用 `register-alias` 注册到 `characters[].aliases`；无则自动补 `【别名】无`。

### D6: 阶段自动推进

最后一个子结构写入后 write-sub 自动触发 finalize-chapter，无需手动执行。六检通过后自动标记门禁。

### D7: 原子写入安全

`novel_atomic_writer.py` 在写入前执行格式校验 + 署名检测 + 字数校验，写入时使用 fsync 确保数据落盘。写入中断不会产生残缺文件。

### D8: 统一路径管理

所有项目数据路径由 `_path_utils.py` 统一管理。LLM 禁止手工拼写路径，禁止直接 Read memory/ 目录下的文件。新会话第一件事是 `list-projects`。

---

## 九、交互方式

### 9.1 主命令

```bash
# 新会话第一件事：列出所有项目
python scripts/novel_workflow_engine.py list-projects

# 规划章节子结构
python scripts/novel_workflow_engine.py plan-chapter <state_path> L01

# 写入子结构
python scripts/novel_workflow_engine.py write-sub <state_path> L01 S01

# 完结章节
python scripts/novel_workflow_engine.py finalize-chapter <state_path> L01
```

### 9.2 状态与门禁管理

```bash
# 查看门禁状态
python scripts/novel_pipeline_gate.py status <state_path>

# 标记门禁通过
python scripts/novel_pipeline_gate.py pass <gate_name> <state_path>

# 检查门禁前提
python scripts/novel_pipeline_gate.py require <gate_name> <state_path>
```

### 9.3 状态管理

```bash
# 初始化项目状态
python scripts/novel_state_manager.py init <project_name> --chapters <json>

# 更新子结构状态
python scripts/novel_state_manager.py update-sub --chapter L01 --sub S01

# 添加角色
python scripts/novel_state_manager.py add-char --name <name>

# 注册别名
python scripts/novel_state_manager.py register-alias --char <id> --alias <alias>
```

### 9.4 检查与验证

```bash
# 因果链验证
python scripts/novel_causality_check.py outline <state_path>
python scripts/novel_causality_check.py sub-structure <state_path> L01

# 连通性检查
python scripts/novel_continuity.py check <state_path> L01

# 风格校验
python scripts/novel_style_check.py <chapter_file>

# 逻辑检查
python scripts/novel_logic_check.py <state_path> L01

# 大纲忠实度报告
python scripts/novel_fidelity.py generate-report <state_path>
```

---

## 十、外部依赖

| 依赖 | 用途 | 必需？ |
|:----:|:----:|:------:|
| Python 3.8+ | 运行时 | 必需 |
| sentence-transformers | BERT 语义检查（第5步） | 可选 |
| transformers + torch + accelerate | DeepSeek-R1 推理审核（第6步） | 可选 |

> **刚性规则零依赖**：六检前 4 步、门禁系统、状态管理、上下文加载、原子写入全部使用 Python 标准库实现。

---

## 十一、版本历史

| 版本 | 日期 | 核心变化 |
|:----:|:----:|:--------|
| ... | ... | ... |
| **1.35.3** | 2026-07-01 | 最新版本：全流程硬约束 + 门禁跟踪 + 别名自动管理 |

---

## 十二、数据流全景

```
用户模糊想法
  │
  ▼
Phase 1 — 场景配置 & 大纲
  │
  ├── LLM 生成场景配置 (novel_info)
  │   → characters / era / location / conflict
  │
  ├── LLM 生成一级大纲 (chapters)
  │   → L01-L15: title + overview
  │
  ├── [门禁] outline_causality
  │   └── novel_causality_check.py outline
  │
  └── 用户确认
      │
      ▼
Phase 2 — 逐章写作（L01 → L02 → ... → L15）
      │
      ├── plan-chapter
      │   → sub_structures (S01-S05)
      │   → [新角色检测] HARD-BLOCK → add-char 解决
      │   → [writing_prompt 缺失] HOOK-BLOCK
      │
      ├── [门禁] sub_causality
      │   └── novel_causality_check.py sub-structure
      │
      ├── [门禁] set-phase → writing
      │   └── require outline_causality + sub_causality
      │
      ├── [逐子结构循环 S01 → S02 → ... → S05]
      │   │
      │   ├── [串行阻断] 上一子结构 completed?
      │   │   └── N → HOOK-BLOCK
      │   │
      │   ├── context_loader
      │   │   → 4 区块 (A 约束 → B 连续性 → C 收尾 → D 扩展)
      │   │
      │   ├── LLM 输出正文
      │   │   → 纯文本 + 可选【别名】行
      │   │
      │   ├── write-sub → atomic_writer
      │   │   → 格式校验 + 署名检测 + fsync + 原子写入
      │   │
      │   └── state_manager update-sub
      │       → 标记 completed + 可选 add-char
      │
      ├── [自动] finalize-chapter
      │   ├── 章内连通性 (SOFT)
      │   ├── 跨章承诺链 (SOFT)
      │   ├── 风格校验 (HARD)
      │   ├── 逻辑检查 (HARD)
      │   ├── 语义检查 (HARD, 有模型时)
      │   └── 推理审核 (HARD/SOFT, 有模型时)
      │   → 全部通过 → chapter_finalized:L## ✅
      │   → 有 HARD 问题 → 写入 _fixes.json ❌
      │
      ▼ [所有章完成]
Phase 3 — 全文完结
      │
      ├── novel_fidelity.py generate-report
      │   → [门禁] fidelity
      │
      ├── novel_fidelity.py verify-ending
      │   → [门禁] ending_verify
      │
      └── set-phase → stage3_ready
          → 完结 ✅
```

---

> 本文档基于 novel-weaver v1.35.3 的 SKILL.md + 8 个 references/*.md + 18 个核心脚本综合分析整理。
