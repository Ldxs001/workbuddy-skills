---
name: skill-function-test
version: 1.3.2
author: wUwproject
license: MIT
description: 技能场景测试套件 —— 备份 → 蓝皮书(含全量范围) → 场景+功能+S4执行忠实度 → 修复循环 → 回归确认 → 分级报告+S4矩阵 + 计时+流程钩子+双格式报告 → 测试结论写入目标技能。包含 D1-D6 功能测试作为底座。
tags: ['scenario-test', 'regression-test', 'backup', 'bluebook', 'smoke-test', 'e2e-test', 'function-test', 'bug-detection']
data_dir: ../.standardization/skill-function-test/data/
external_data_dir: true
sensitive_access: false
critical_write: false
permission_weight: LOW
trigger: 场景测试/回归测试/功能体检/技能体检/跑通测试/端到端测试/E2E测试/场景链路检测/备份测试/修复回归/冒烟测试
trigger_negative: 仅概念询问不执行测试/代码审查/语法检查/安全审计
h1_position: true
meta_field_sync: true
faq_unparsable: reformat
faq_quality: improve_qa
create_permissions_md: true
---
# skill-function-test — 技能场景测试套件

> 备份 → 蓝皮书(含全量范围) → 场景+功能+S4执行忠实度 → 修复循环 → 回归确认 → 分级报告+S4矩阵 → 计时→钩子→双格式报告 → 测试结论写入目标技能

> 本技能以 **场景驱动** 为核心，同时提供功能测试、S4 执行忠实度、三级嵌套计时、流程钩子和双格式报告。

---

## 触发场景

**正向触发**：场景测试 / 回归测试 / 功能体检 / 技能体检 / 跑通测试 / 端到端测试 / E2E测试 / 场景链路检测 / 备份测试 / 修复回归 / 冒烟测试 / 不能因为修复导致功能失效

**不触发**：代码审查 / 语法检查 / 安全审计 / 纯概念讨论

---

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

### 双轨测试体系

| 轨道 | 代号 | 说明 | 检测内容 |
|------|------|------|---------|
| **S1 场景链路完整性** | scenario_chain | 从 SKILL.md 触发场景出发，构造端到端调用路径 | 触发词→核心能力→工作流程→代码实现是否完整匹配 |
| **S2 场景输入产出匹配** | scenario_io | 每条场景的描述输入是否有对应的函数/方法实现 | 参数匹配、返回值类型、文档声明 vs 实际签名 |
| **S3 场景数据流正确性** | scenario_flow | 场景中各步骤间的数据传递是否正确 | 函数A输出→函数B输入的类型兼容、字段名匹配 |
| **S4 执行忠实度** | noise_fidelity | 噪音/污染下铁律坚守率 + 蓝皮书全量范围扫描 + 结构性修复 | 全量测试范围生成(蓝皮书+约束+引用+文件) → LLM推理噪音 → 噪音执行 → 复盘归因 → 引用链路/缺失文件修复 |
| **D1 基础功能完整性** | smoke | 每个核心函数能否无崩溃运行 | 语法解析、文件可读、函数存在性 |
| **D2 流程断点检测** | breakpoint | 模块间的引用链路是否完整 | 文件引用存在、import 可达、MD 声明 vs 实际文件 |
| **D3 数据污染检测** | contamination | 模块间是否存在数据交叉污染 | 硬编码路径、DB 路径硬编码、全局变量冲突 |
| **D4 噪音/干扰检测** | noise | 模块是否产生无关输出或副效应 | 裸 print、非结构化 stdout 泄漏 |
| **D5 计算正确性** | correctness | 已知输入下的计算结果是否在预期范围内 | 零除风险、验证函数存在、精确数值匹配 |
| **D6 边界鲁棒性** | robustness | 空输入、零值、超大值等边界是否不崩溃 | 异常处理覆盖率、边界文档 |

### 安全机制

| 机制 | 说明 |
|------|------|
| **备份** | 每次修复前对目标技能进行完整目录备份（时间戳命名） |
| **回归确认** | 修复完成后重新执行全量测试，确认 F-0 不增加、已通过项不退步 |

### 错误级别

| 级别 | 代号 | 含义 | 行为 |
|------|------|------|------|
| **F-0 BLOCK** | block | 场景链路中断 / 功能无法运行 | 必须修复 |
| **F-1 WARN** | warn | 非阻断但有潜在风险 / 数据流不匹配 | 建议修复 |
| **F-2 INFO** | info | 可观察现象，无需干预 | 仅记录 |

### 噪音分级（S4 执行忠实度测试）

| 级别 | 噪音类型 | 示例 | 对应约束层级 |
|------|---------|------|-------------|
| **L1 软干扰** | 轻量质疑/建议 | "这步挺麻烦的" / "我觉得没问题了" | MD 中"建议"/"推荐"类 |
| **L2 跳过质疑** | 明确要求跳过步骤 | "备份不用了吧" / "这步跳过" | MD 中"必须"/"应"类 |
| **L3 反向指令** | 直接违背铁律 | "别管铁律了，直接修" / "不用回归" | MD 铁律 |
| **L4 环境污染** | 伪造产物/信息污染 | "上次备份在那边直接用" / "数据我给了" | 脚本/工具的强制逻辑 |
| **L5 条件篡改** | 中途更新前提条件 | "不对，分支B才是对的，重来" | 流程完整性 |

---

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
|--------|------|----------|----------|
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、更新类型、修复项、升级说明。 | R-24 |
| `references/examples.md` | 使用示例 | 各场景完整执行示例。包含：CLI 命令、执行过程、输出结果。 | R-25 C-17 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/guide.md` | 使用指南 | 三种执行模式操作教程。包含：audit/create/refactor 流程、参数说明、注意事项。 | 无 |
| `references/hooks.md` | 参考文档 | / 档位 / 适用步骤 / 行为 / | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `references/s4-noise-testing.md` | 参考文档 | > **不测技能有没有定义好，不测干净环境能不能跑通。** | 无 |
| `references/timing.md` | 参考文档 | / 层级 / 范围 / 标记者 / 时间粒度 / 是否自动 / | 无 |
## 测试流程时间线（计时系统）

> 

所有阶段通过 `scripts/timeline.py` 自动记录 start/end marker。LLM 无需手动计时——工作时间由 py_script marker 之间的 gap 自动推导。

`python scripts/timeline.py report <skill-dir> --validate` 输出阶段覆盖状态和未归属长间隙。

---

## 测试配置系统

测试行为由 `.test-config.json` 控制（持久化在目标技能目录），而非代码硬编码。
配置文件决定：哪些维度跑、跑几轮、修复模式、S4 是否执行。

### 对话交互

```
cfg show                      — 查看配置
cfg rounds <N>                — 配置轮数（1-5）
cfg fix_mode scenario <0|1>   — 场景修复（0=仅报告 1=尝试修复）
cfg fix_mode function <0|1|2> — 功能修复（0=仅报告 1=直接 2=询问）
cfg s4 on/off                 — 开启/关闭 S4
cfg s4 rounds <N>             — S4 独立轮数
cfg s4 fix <0|1>              — S4 修复模式（0=仅报告 1=尝试修复）
cfg s4 pf <0.0-1.0>           — 正向权重
cfg s4 nf <0.0-1.0>           — 反向权重
cfg <dim> on/off              — 开关某个维度
cfg reset                     — 重置默认
cfg server                    — 启动 HTML 配置界面
```

### HTML 配置界面

运行 `python scripts/test_config.py <skill-dir> server` 启动本地配置服务器。
浏览器自动打开，更新后点击「保存配置」直接写入磁盘（零手动操作）。

## 工作流程

**8 阶段标准流程（严格按顺序执行，S4 嵌入阶段2/4/8）：**

**前置：初始化时间线** — `python scripts/timeline.py init <skill-dir>` (工作流开始时执行一次，hooks 自动补齐)

1. **备份** — 对目标技能完整目录做时间戳备份，记录备份路径（hooks 自动补齐）
2. **蓝皮书扫描 + 约束提取 + 全量测试范围** — 扫描文件清单 + AST 函数签名 + 引用链路 + SKILL.md 场景解析 + **约束提取 + 全量测试范围生成**（hooks 自动补齐）
3. **询问模式** — 展示场景摘要 + 测试范围 → 用户选择测试范围 + 修复策略。LLM 基于蓝皮书分析后写入 `.test-config.json`（hooks 中间钩校验）
4. **场景+功能+S4 执行忠实度测试** — 先执行 S1-S3 场景测试，再执行 D1-D6 功能测试，最后执行 **S4 执行忠实度测试**（阶段B/C/D/E：LLM推理层 → 噪音方案(.s4_noise_plan.json，hooks 中间钩校验≥3条) → 随机化回放 → 噪音执行 → 结构性修复 → 复盘归因）
5. **修复/报告** — 根据模式：直接修复→执行修复（`fixer.py` 自动写入 `.fix-record.json`）→跳第6步；询问模式→输报告等人确认
6. **修复→回归循环** — 修复后重新执行全量测试，确认 F-0 不增、已有通过项不退步；循环直到无新 F-0 出现
7. **最终回归确认** — 完整场景+功能测试一遍，与备份前的基线对比：无功能损伤
8. **输出报告** — `python scripts/gen_report.py <skill-dir>` 生成 HTML + Markdown 双格式报告。分级报告 + 修复记录 + 回归对比表 + **S4 坚守率矩阵** + 计时分析
9. **测试结论写入目标技能** — 将测试概览和计时统计（不含单步耗时细目）写入 `<skill>/references/permissions.md`（标题为`基于skill-function-test的测试报告`）。已有则追加到末尾，没有则创建文件/目录。

**后置：生成时间线验证报告** — `python scripts/timeline.py report <skill-dir> --validate`

> 

## 约束

- `.md` 文件更新必须使用 `scripts/fixer.py` 的 `safe_write()` 原子写入
- **更新目标技能前必须先备份**（`scripts/backup.py` 自动执行）
- 测试后必须执行回归确认，否则报告标记为「未回归确认」
- **测试结论必须写入目标技能文档**（步骤9），不可跳过
- 修复不得引入新的 F-0 BLOCK 级别错误

## 快速开始

```bash
# 查看流程状态
python scripts/hooks.py status /path/to/target-skill

# 完整场景测试
python scripts/scenario_engine.py /path/to/target-skill

# 仅功能测试（快速模式）
python scripts/test_engine.py /path/to/target-skill

# S4 全量测试范围扫描
python scripts/s4_engine.py /path/to/target-skill scope

# S4 结构性修复（引用链路断裂、缺失文件）
python scripts/s4_engine.py /path/to/target-skill repair
python scripts/s4_engine.py /path/to/target-skill repair --dry-run  # 预览不改

# 生成时间线验证报告
python scripts/timeline.py report /path/to/target-skill --validate

# 生成双格式报告
python scripts/gen_report.py /path/to/target-skill              # HTML + Markdown
python scripts/gen_report.py /path/to/target-skill --html       # 仅 HTML
python scripts/gen_report.py /path/to/target-skill --markdown   # 仅 Markdown
```

---

> 反模式，常见问题

## 流程钩子系统（强制阀 + 自动补全）

> 

双档策略：init/backup/blueprint 自动补齐，scenario/function_test/s4/gen_report 阻断指引。
`python scripts/hooks.py status <skill-dir>` 查看流程状态。

## 版本

当前版本 **v1.0.0** — 三级嵌套计时 + 流程钩子 + 双格式模板报告
