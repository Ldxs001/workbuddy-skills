<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# skill-function-test 架构与规范体系文档

> 完整解读 v1.1.1 版的架构设计、双轨测试体系、流程钩子、计时系统与报告输出
> 生成时间：2026-06-12（v1.1.1 最新更新）

---

## 一、系统概览

skill-function-test 是一个 **技能场景测试套件**，围绕以下闭环运行：

```
目标技能 SKILL.md
  → 蓝皮书扫描（inspector: AST + 函数签名 + 引用链路 + import_chain + 约束提取）
    → [HOOK] 流程钩子校验（自动补齐/阻断指引）
    → 场景测试（scenario_engine: S1 frontmatter trigger / S2 全 CLI 脚本 / S3 import_chain 依赖链）
      → 功能测试（test_engine: D1语法/D2断点/D3污染/D4噪音/D5正确性/D6鲁棒性）
        → S4 执行忠实度（噪音方案 + 随机化回放 + 结构性修复）
          → 修复循环（fixer: 零除/裸print/路径/异常）
            → 回归确认（全量重测 + 基线对比）
              → 双格式报告（gen_report: HTML + Markdown 模板化报告 + 计时验证）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI + HTML 配置界面 | 人类可读的文档、命令行交互、可视化配置 |
| **业务层** | inspector / scenario_engine / test_engine / s4_engine / fixer / gen_report | 扫描、测试、修复、回归、双格式报告的核心逻辑 |
| **流程控制层** | hooks.py / timeline.py | 流程钩子（入口阻断+自动补齐）和三级嵌套计时系统 |
| **数据层** | backup.py（时间戳备份）+ test_config.py（JSON 持久化） | 备份与配置管理 |

### 1.2 目录结构

```
skill-function-test/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据
├── references/                 # 渐进式文档
│   ├── guide.md                # 完整使用教程（8 阶段工作流程）
│   ├── antipatterns.md         # 反模式
│   ├── changelog.md            # 版本更新日志
│   ├── examples.md             # 使用示例
│   ├── faq.md                  # 常见问题
│   ├── permissions.md          # 权限说明
│   ├── s4-noise-testing.md     # S4 噪音测试方案
│   ├── timing.md               # 计时系统使用说明
│   └── hooks.md                # 流程钩子使用说明
└── scripts/                    # 核心脚本
    ├── hooks.py                # 流程钩子系统：入口校验阻断 + 自动补齐 + 完成标记
    ├── timeline.py             # 计时引擎：三级嵌套 start/end marker + --validate 间隙推导
    ├── gen_report.py           # 报告生成器：从 JSON 填充模板，输出 HTML + Markdown 双格式
    ├── inspector.py            # 蓝皮书扫描器：AST + 文件清单 + 函数签名 + 引用链路 + import_chain + 约束提取
    ├── scenario_engine.py      # 场景测试引擎：基于蓝皮书数据（非 SKILL.md 正文格式）构建测试计划
    ├── test_engine.py          # 功能测试引擎：D1-D6 功能测试 + 结果聚合
    ├── s4_engine.py            # S4 执行忠实度引擎：噪音方案校验 + NoisePlayer 随机化回放 + 结构性修复
    ├── fixer.py                # 通用修复工具：safe_write 原子写入、零除保护、print→logging、路径替换
    ├── backup.py               # 完整目录备份 + 恢复回滚，时间戳命名
    ├── bump_version.py         # 自动版本号递增
    ├── test_config.py          # 测试配置管理：持久化/CLI/文字交互/HTML 配置界面
    └── test_config.html        # 测试配置 HTML 面板（内嵌脚本）
```

### 1.3 触发场景

**正向触发**：场景测试 / 回归测试 / 功能体检 / 技能体检 / 跑通测试 / 端到端测试 / E2E 测试 / 场景链路检测 / 备份测试 / 修复回归 / 冒烟测试

**不触发**：仅概念询问不执行测试 / 代码审查 / 语法检查 / 安全审计

---

## 二、双轨测试体系

### 2.1 轨道 A：场景测试（S1-S3）

**目的**：验证技能的 CLI 脚本是否真实可运行。基于蓝皮书数据驱动，不依赖 SKILL.md 正文写作格式。

| 维度 | 代号 | 检测内容 | 检测方式 |
|------|------|---------|---------|
| **S1 场景链路完整性** | scenario_chain | frontmatter trigger 字段的触发词是否能匹配到 CLI 脚本 | 解析 frontmatter trigger → 关键字匹配蓝皮书 CLI 脚本清单 → 执行 `--help` 及附加参数 |
| **S2 场景输入产出匹配** | scenario_io | 蓝皮书中所有 CLI 脚本是否能正常启动 | 遍历蓝皮书中所有 CLI 脚本（跳过 __init__/__main__），逐一带 `--help` 和附加参数验证 |
| **S3 场景数据流正确性** | scenario_flow | 蓝皮书 import_chain 中 CLI 脚本之间的依赖链是否完整 | 从 import_chain 构建 CLI 脚本间引用关系，验证依赖链路 |

**重构说明**（v1.1.0）：原 S2/S3 解析 SKILL.md 的 `## 核心能力` 和 `## 工作流程` 节正文格式，导致格式不匹配时永远返回空。v1.1.0 改为完全基于蓝皮书数据（file_manifest + cli_scripts + import_chain），不依赖任何 SKILL.md 正文写作格式。

**修复规则**：
- F-0 导入错误/语法错误 → ✅ 自动修复（fixer.safe_patch）
- F-1 引用断链 → ❌ 不修复，输出建议由人决定
- 场景层面设计缺失 → ❌ 不修复，仅报告（越界不修复）

### 2.2 轨道 B：功能测试（D1-D6）

**目的**：对技能代码逐函数、逐模块执行自动化静态分析，定位到具体断点行号。

| 维度 | 代号 | 检测内容 | 检测方式 | 结果示例 |
|------|------|---------|---------|---------|
| **D1 基础功能完整性** | smoke | 语法解析、文件可读、函数存在性 | Python compile() + AST parse | "语法检查: config.py PASS" |
| **D2 流程断点检测** | breakpoint | 文件引用存在、import 可达、MD 声明 vs 实际文件 | import 链静态追踪 + 文件存在性检查 | "外部引用: utils → config.py: utils.cfg_dir PASS" |
| **D3 数据污染检测** | contamination | 模块间是否存在数据交叉污染 | 硬编码路径扫描、DB 路径硬编码、全局变量冲突 | "多处文件删除操作: embedding_model_manager.py:286 有 3 处删除操作分布在 不同文件" |
| **D4 噪音/干扰检测** | noise | 模块是否产生无关输出或副效应 | AST 扫描裸 print、非结构化 stdout 泄漏 | "裸 print: embedding_model_manager.py:327 print(json.dumps(...))" |
| **D5 计算正确性** | correctness | 已知输入下的计算结果是否在预期范围内 | 零除风险检测、验证函数存在性、精确数值匹配 | "零除验证: _check_integrity, verify_model, ... 10 个 PASS" |
| **D6 边界鲁棒性** | robustness | 空输入、零值、超大值等边界是否不崩溃 | 异常处理覆盖率分析、边界文档存在性 | "边界说明: scripts/config.py:69 save_config() 缺参数边界说明" |

#### 错误级别体系

| 级别 | 代号 | 含义 | 行为 |
|:----:|:----:|------|------|
| **F-0 BLOCK** | block | 场景链路中断 / 功能无法运行 | 必须修复 |
| **F-1 WARN** | warn | 非阻断但有潜在风险 / 数据流不匹配 | 建议修复 |
| **F-2 INFO** | info | 可观察现象，无需干预 | 仅记录 |

#### 修复规则详解

| 问题类型 | 自动修复？ | 修复方法 |
|---------|:---------:|---------|
| F-0 导入错误/语法错误 | ✅ | `fixer.safe_patch()` 修正错误行 |
| F-1 零除风险 | ✅ | `fixer.fix_add_none_guard()` |
| F-1 裸 print | ✅ | `fixer.fix_stdout_to_logging()` |
| F-1 硬编码路径 | ✅ | `fixer.fix_hardcoded_path()` |
| F-1 异常裸奔 | ✅ | `fixer.fix_exception_guard()` |
| F-1 引用断链 | ❌ | 输出建议，由人决定 |
| F-2 缺少文档 | ❌ | 仅记录 |
| 场景层面的设计缺失 | ❌ | 仅报告（越界不修复） |

**不修复的边界**：
- 不新增功能
- 不修改业务逻辑
- 不进行重构
- 不修改文档（SKILL.md 等）

### 2.3 轨道 C：S4 执行忠实度（Execution Fidelity）

**目的**：测试技能在脏环境（噪音干扰）下的铁律坚守率。从 v0.2.13 起引入。

#### S4 体系

| 维度 | 代号 | 检测内容 |
|:----:|:----:|---------|
| **L1 基本忠实度** | baseline | 无噪音时的完整流程是否正常 |
| **L2 弱噪音** | low_noise | 少量无关文件/残存代码是否干扰正常流程 |
| **L3 中噪音** | medium_noise | 部分文件损坏/残缺时是否能正确恢复 |
| **L4 强噪音** | high_noise | 大量不合理文件/数据污染下是否保持核心功能 |
| **L5 极端** | extreme | 关键文件缺失时的告警/恢复机制是否触发 |

**S4 噪音方案**（定义在 `references/s4-noise-testing.md`）：

| 噪音类型 | 说明 | 等级 |
|---------|------|:----:|
| 无关文件污染 | 在技能目录放置无关的 .py/.md/.json | L2-L4 |
| 核心文件缺失 | 删除 SKILL.md 或关键脚本 | L5 |
| 函数签名篡改 | 修改函数参数类型或返回值 | L3-L4 |
| import 路径破坏 | 修改模块引用路径 | L3 |
| 数据文件污染 | 在 data/ 目录放入损坏数据 | L2-L4 |

**NoisePlayer 机制**：`s4_engine.py` 按方案声明的 schema 随机化应用噪音，然后运行全量测试，对比噪音前后的 F-0/F-1 变化。

---

## 三、8 阶段完整工作流程

### 阶段 0：安全校验 + 时间线初始化

| 校验项 | 规则 |
|--------|------|
| 路径穿越 | 拒绝 `../`、`..\\`、`C:` 开头 |
| 目标路径范围 | 必须在 `~/.workbuddy/skills/<name>` 内 |
| 目标存在 | 目标目录必须有 SKILL.md |

初始化时间线：
```bash
python scripts/timeline.py init /path/to/target-skill
```
（hooks 自动补齐，LLM 不需要手动记时）

### 阶段 1：备份

```bash
python scripts/backup.py backup /path/to/target-skill pre_test
```

备份自动以时间戳命名，存储在 `.standardization/skill-function-test/data/backup/`。

### 阶段 2：蓝皮书扫描 + 约束提取 + 全量测试范围

```bash
python scripts/inspector.py /path/to/target-skill
```

输出：
- 文件清单（按扩展名分组）
- AST 函数签名（def 名称 + 行号 + 参数列表）
- 引用链路（import 关系图）
- import_chain（模块间交叉引用）
- CLI 脚本清单（有 __main__ 的脚本及其支持参数）
- **约束提取**（扫描 scripts/ 下 `必须/不得/禁止/MUST` 关键词）
- **全量测试范围生成**（所有函数名 + 所有文件 + 所有 import + 所有裸 print 等）

并行执行 `scenario_engine.py` 解析场景。

### 阶段 3：询问模式

展示以下内容给用户：

```
=== 技能蓝皮书摘要 ===
技能: xxx vx.x.x
文件: N 个 Python, N 个 MD
函数: N 个
场景: N 条 (源于 trigger 字段)

=== 可测试的场景和维度 ===
S1 场景链路完整性     — 触发词→能力→流程→代码是否完整匹配
S2 场景输入产出匹配   — 场景输入是否有对应函数实现
S3 场景数据流正确性   — 场景步骤间数据传递是否连续
D1 基础功能完整性     — 语法解析、函数存在性
D2 流程断点检测       — 文件引用、import 链
D3 数据污染检测       — 硬编码路径、DB 交叉
D4 噪音/干扰检测      — 裸 print、副效应
D5 计算正确性         — 零除风险、数值精度
D6 边界鲁棒性         — 异常处理、空值保护
S4 执行忠实度         — 噪音环境下的铁律坚守率

请选择测试范围（逗号分隔序号或 "all"）:
修复模式: [0] 仅报告 / [1] 直接修复 / [2] 询问后修复
```

### 阶段 4：场景 + 功能 + S4 测试执行（hooks 自动校验前置条件）

```bash
# 场景测试
python scripts/scenario_engine.py /path/to/target-skill

# 功能测试
python scripts/test_engine.py /path/to/target-skill

# S4 执行忠实度
python scripts/s4_engine.py /path/to/target-skill
```

钩子机制：每个脚本入口自动触发 `hooks.py check`，检测前置步骤制品是否存在。备份/蓝皮书等纯 Python 步骤缺失时自动补齐；场景/功能测试等需要 LLM 参与的步骤缺失时阻断并输出指引命令。参见 `references/hooks.md`。

三个引擎各自输出独立报告。**执行顺序**：S1-S3 → D1-D6 → S4。

### 阶段 5：修复/报告

根据修复模式：

| 模式 | 行为 |
|:----:|------|
| **0 仅报告** | 输出完整报告，不执行任何修复 |
| **1 直接修复** | 对 F-0 BLOCK 和 F-1 WARN 级问题执行自动修复 |
| **2 询问后修复** | 逐条展示问题，询问用户是否修复 |

### 阶段 6：修复→回归循环

```
循环开始:
  1. 重新执行全量场景+功能+S4 测试
  2. 对比修复前的 BLOCK 数量
  3. 若 F-0 未减少 → 修复无效，回滚
  4. 若 F-0 减少但出现新的 F-0 → 标记为回归损伤，回滚
  5. 若 F-0=0 且无新 F-1 → 循环结束
```

### 阶段 7：最终回归确认

重新执行完整场景 + 功能 + S4 测试，确认：
- 修复前 PASS 的项全部仍为 PASS
- 修复前 F-0 已消失
- 无新增 F-0

### 阶段 8：输出报告（双格式模板化）

```bash
python scripts/gen_report.py /path/to/target-skill
python scripts/timeline.py report /path/to/target-skill --validate
```

`gen_report.py` 从 timeline.json + 各测试 JSON 读取数据填充结构化模板，输出 HTML 和 Markdown 双格式：

**HTML 报告**（自包含，含 Chart.js 控制图）：
- 概览卡片（场景/功能通过率、F-0/F-1/F-2 计数）
- 计时仪表板（总耗时、脚本执行、LLM 间隙、目标技能调用、单步细目）
- 问题列表（颜色标记分级：BLOCK/WARN/INFO）
- 测试详情表 + 修复记录
- 多轮统计（≥2 轮显示均值+标准差，≥9 轮显示休哈特控制图）

**Markdown 报告**（纯文本+表格，无图）：
- 同结构模板化输出，问题分级 + 计时表 + 测试步骤详表

---

## 四、核心设计原则

### D1: 零外部依赖
所有脚本仅使用 Python 标准库（pathlib, json, re, argparse 等），零 pip install。
**目的**：测试工具本身不应引入额外的依赖问题。

### D2: 场景驱动
不以函数为单位，以**场景链路**为单位。从 SKILL.md 声称的能力出发，每条场景就是一条测试链路。
**目的**：确保用户看到的技能描述和实际能力一致。

### D3: 不引入新功能
测试发现的任何问题，修复时**只能修复 bug**，不能新增功能、不能修改业务逻辑。
**目的**：测试是验证工具，不是开发工具。

### D4: 备份优先
任何修改前强制完整目录备份，带时间戳命名，修复后支持回滚。
**目的**：测试过程中发现的"可修复"问题，误修复时可完整恢复。

### D5: S4 执行忠实度
测试技能在脏环境（噪音干扰）下的行为，验证铁律坚守率。
**目的**：真实环境中技能可能被各种因素干扰，S4 保障极端场景下的稳定性。

---

## 五、关键脚本详细说明

### 5.1 hooks.py — 流程钩子系统

**职责**：每个脚本入口做前置检查+自动补齐，出口标记完成+指引下一步。

关键函数：
| 函数 | 说明 |
|------|------|
| `hook_pre_{step}(skill_dir)` | 入口检查：Python 步骤缺了自动补齐，LLM 步骤缺了阻断指引 |
| `hook_post_{step}(skill_dir)` | 出口标记：写入 .flow-state.json |
| `cmd_status(skill_dir)` | 查看当前流程完成状态 |

双档策略：
- **自动补齐**：init/backup/blueprint 产物缺失时自动 `subprocess.run()` 补齐
- **阻断指引**：scenario/function_test/s4 前置缺失时 `exit(1)`，明确告诉 LLM 该执行什么命令

参见 `references/hooks.md`。

### 5.2 timeline.py — 计时引擎

**职责**：测试流程时间线，自动记录每个阶段/步骤/子进程的 start/end marker。

关键函数：
| 函数 | 说明 |
|------|------|
| `cmd_init(skill_dir)` | 初始化时间线 JSON |
| `cmd_mark(skill_dir, phase, label, mark, ...)` | 记录 marker（含类型/标签/父ID） |
| `cmd_report(skill_dir, --validate)` | 输出层级时间线 + 间隙推导（LLM 时间自动计算） |

三级嵌套计时体系：
| 层级 | 范围 | 是否自动 |
|------|------|---------|
| L1 阶段级 | 备份/蓝皮书/场景/功能/S4/报告 | ✅ 各脚本自动标记 |
| L2 测试级 | 每个测试维度的调用 | ✅ scenario/test_engine 自动标记 |
| L3 子进程级 | 每个 subprocess 调用目标脚本 | ✅ 脚本内部自动记录 |

`--validate` 模式：自动检测缺失阶段，从 py_script marker 间的 gap 推导 LLM 耗时。

### 5.3 gen_report.py — 报告生成器

**职责**：从 timeline.json + 各测试 JSON 读取数据，填入结构化模板。

输出：
- `.test-report.html` — 自包含 HTML（概览/计时/问题/测试详情/修复记录，含 Chart.js 控制图）
- `.test-report.md` — 模板化 Markdown（同结构，文本+表格）

统计规则：1 轮→总计时+技能耗时 / ≥2 轮→均值+标准差 / ≥9 轮→休哈特控制图

### 5.4 inspector.py — 蓝皮书扫描器

**职责**：全量扫描目标技能，生成蓝皮书报告。

输出内容：
1. **结构标准化判定**：标准 / 半标准 / 非标准
2. **元信息**：SKILL.md 行数、## 章节数量及标题列表、_meta.json 字段清单
3. **文件清单**：按扩展名分组计数（.py / .md / .sh/.bat / .json/.yaml / 其他）
4. **非标位置标记**：每个不在 scripts/ 下的 .py 文件、不在 references/ 下的 .md 文件均标注
5. **功能清单**：每个 .py 文件的 `def` 函数名和 `class` 类名列表
6. **引用概览**：每个 .md 文件的行数和 ## 章节标题
7. **安全数据**：sensitive_access / critical_write / permission_weight / data_dir 声明值
8. **约束提取**：扫描 scripts/ 下 `必须/不得/禁止/MUST` 关键词
9. **全量测试范围**：所有函数名 + 所有文件 + 所有 import + 所有裸 print 等

### 5.5 scenario_engine.py — 场景测试引擎

**职责**：基于蓝皮书数据（非 SKILL.md 正文格式）构建测试计划并执行真实 CLI 命令。

检测逻辑（蓝皮书驱动，v1.1.0 重构）：
- S1：frontmatter trigger 字段的每个触发词 → 关键字匹配蓝皮书 CLI 脚本清单 → 执行 `--help`
- S2：遍历蓝皮书中所有 CLI 脚本（跳过 __init__/__main__），逐个测试 `--help` 及其它参数
- S3：从蓝皮书 import_chain 构建 CLI 脚本间引用关系，验证依赖链

### 5.6 test_engine.py — 功能测试引擎

**职责**：D1-D6 静态分析 + 结果聚合。

检测方式：
- D1：`compile()` + `os.path.exists()`
- D2：import 解析器逐模块追踪引用链
- D3：扫描硬编码路径和全局变量
- D4：AST 扫描裸 print 调用
- D5：数学运算的零除风险检测
- D6：try/except 覆盖率和参数边界说明

### 5.7 s4_engine.py — S4 执行忠实度引擎

**职责**：噪音方案校验 + NoisePlayer 随机化回放 + 结构性修复。

关键函数：
| 函数 | 说明 |
|------|------|
| `validate_noise_schema(schema)` | 校验噪音方案是否符合规范 |
| `NoisePlayer.play(skill_dir, noise_plan)` | 按方案随机化应用噪音 |
| `NoisePlayer.recover(skill_dir)` | 恢复被噪音污染的环境 |
| `measure_fidelity(pre_report, post_report)` | 计算忠实度坚守率 |

### 5.8 fixer.py — 通用修复工具

**职责**：安全写入、零除保护、print→logging、路径替换。

关键函数：
| 函数 | 说明 |
|------|------|
| `safe_write(filepath, content)` | 原子写入（tmp + os.replace()） |
| `fix_add_none_guard(expr)` | 添加 None 保护 |
| `fix_stdout_to_logging(code)` | 将裸 print 转为 logging |
| `fix_hardcoded_path(code, new_base)` | 将硬编码路径替换为变量 |
| `fix_exception_guard(code)` | 为模块级调用添加 try/except |

### 5.9 backup.py — 备份与恢复

**职责**：完整目录备份 + 恢复回滚。

| 函数 | 说明 |
|------|------|
| `backup(skill_dir, label)` | 时间戳命名完整备份 |
| `restore(skill_dir, backup_id)` | 从指定备份恢复 |
| `list_backups()` | 列出所有备份 |

---

## 六、测试输出规范

每条测试结果必须包含：
1. **场景/维度标识**（S1-S3 / D1-D6 / L1-L5）
2. **测试名称**（一句话描述）
3. **严重级别**（F-0 BLOCK / F-1 WARN / F-2 INFO）
4. **状态**（pass / fail / skip）
5. **问题描述**（精确到场景链路或文件行）
6. **精确位置**（文件:行号）
7. **场景级修复建议**（针对场景链路断裂）

禁止产出模糊描述。场景链路报告必须说清：输入是什么、断在哪一步、预期是什么、实际是什么。

---

## 七、配置体系

`test_config.py` 统一管理配置，JSON 格式持久化。

| 配置项 | 类型 | 默认值 | 说明 |
|--------|:----:|:------:|------|
| `backup_dir` | str | `.standardization/skill-function-test/data/backup/` | 备份存储路径 |
| `mode` | str | `0` | 默认修复模式（0=仅报告/1=直接修复/2=询问后修复） |
| `enabled_dimensions` | list | `["S1","S2","S3","D1","D2","D3","D4","D5","D6"]` | 启用的测试维度 |

配置可通过 HTML 面板（`test_config.html`）或 CLI（`test_config.py --mode 2`）修改。

---

## 八、与 skill-standardization 的协作

```
skill-standardization（审计规范）
  └─ skill-function-test（测试验证）
       ├─ 审计目标技能的规范合规性
       ├─ 测试目标技能的功能完整性
       ├─ 修复可自动修复的问题
       └─ 回归确认无损伤
```

**集成点**：
- `inspector.py` 扫描输出与 skill-standardization 的 R-23 审计共享一致的文件清单格式
- `fixer.py` 的 safe_write 与 skill-standardization 的 safe_io.py 功能一致（原子写入 + 备份）
- `backup.py` 的备份命名规范与 skill-standardization 的 refactor 模式一致（时间戳 + 标签）

---

> 本文档基于 skill-function-test v1.1.1 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
