---
name: skill-function-test
version: 0.2.2
author: wUwproject
license: MIT
description: 技能场景测试套件 —— 备份 → 蓝皮书 → 场景+功能双轨测试 → 修复循环 → 回归确认 → 分级报告。场景驱动：从 SKILL.md 解析触发场景和核心能力，构造端到端场景测试链路。包含 D1-D6 功能测试作为底座。
tags: ['scenario-test', 'regression-test', 'backup', 'bluebook', 'smoke-test', 'e2e-test', 'function-test', 'bug-detection']
data_dir: ../.standardization/skill-scenario-test/
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
---
# skill-function-test — 技能场景测试套件

> 备份 → 蓝皮书 → 场景+功能双轨测试 → 修复循环 → 回归确认 → 分级报告

> 本技能以 **场景驱动**：从目标技能的 SKILL.md 中解析其声称的触发场景、核心能力和工作流程，
> 针对每条场景链路构造端到端测试用例。**功能测试（D1-D6）作为底座**，定位到具体断点。

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

### 渐进式文件索引

| 文件 | 位置 | 说明 |
|------|------|------|
| `references/guide.md` | 完整使用指南 | 10 阶段工作流程 + 备份/恢复说明 + 场景解析规则 |
| `references/antipatterns.md` | 反模式 | 常见错误和注意事项 |
| `references/faq.md` | FAQ | 常见问题 |
| `references/examples.md` | 示例集合 | 完整执行示例 |
| `scripts/backup.py` | 备份与恢复 | 完整目录备份 + 时间戳 + 恢复回滚 |
| `scripts/inspector.py` | 蓝皮书扫描器 | AST + 文件清单 + 函数签名 + 引用链路 + 场景解析 |
| `scripts/scenario_engine.py` | 场景测试引擎 | 从 SKILL.md 解析场景，构造场景级测试用例 |
| `scripts/test_engine.py` | 功能测试引擎 | D1-D6 功能测试 + 结果聚合 |
| `scripts/fixer.py` | 通用修复工具 | 安全写入、零除保护、print→logging、路径替换 |

---

## 工作流程

**8 阶段标准流程（严格按顺序执行）：**

1. **备份** — 对目标技能完整目录做时间戳备份，记录备份路径
2. **蓝皮书扫描** — 扫描文件清单 + AST 函数签名 + 引用链路 + **SKILL.md 场景解析**
3. **询问模式** — 展示场景摘要 → 用户选择测试范围 + 修复策略（直接修复/询问后修复/仅报告）
4. **场景+功能测试** — 先执行 S1-S3 场景测试，再执行 D1-D6 功能测试
5. **修复/报告** — 根据模式：直接修复→执行修复→跳第6步；询问模式→输报告等人确认
6. **修复→回归循环** — 修复后重新执行全量测试，确认 F-0 不增、已有通过项不退步；循环直到无新 F-0 出现
7. **最终回归确认** — 完整场景+功能测试一遍，与备份前的基线对比：无功能损伤
8. **输出报告** — 分级报告 + 修复记录 + 回归对比表

> → 详见 `references/guide.md`

## 约束

- `.md` 文件更新必须使用 `scripts/fixer.py` 的 `safe_write()` 原子写入
- **修改目标技能前必须先备份**（`scripts/backup.py` 自动执行）
- 测试后必须执行回归确认，否则报告标记为「未回归确认」
- 修复不得引入新的 F-0 BLOCK 级别错误

## 快速开始

```bash
# 完整场景测试
python scripts/scenario_engine.py /path/to/target-skill

# 仅功能测试（快速模式）
python scripts/test_engine.py /path/to/target-skill
```

---

> 反模式详见 `references/antipatterns.md`，常见问题详见 `references/faq.md`

## 版本

当前版本 **v0.2.0** — 详见 `CHANGELOG.md`
