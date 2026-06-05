# skill-function-test 完整使用指南

> **场景测试（Scenario Testing）** — 不以函数为单位，以 **场景链路** 为单位。
> 备份 → 蓝皮书+约束+全量范围 → 场景+功能+S4 → 修复循环 → 回归确认 → 输出报告+S4矩阵。

---

## 核心原则

1. **场景驱动** — 从目标技能 SKILL.md 中解析其声称的触发场景、核心能力和工作流程，每条场景就是一条测试链路
2. **功能测试做底座** — D1-D6 功能测试定位到具体断点行号，场景测试定位到链路断裂位置
3. **S4 全量范围扫描** — 从蓝皮书提取约束、引用链路、工作流程、文件清单作为测试范围，噪音下测铁律坚守率，结构性修复引用断裂和缺失文件
4. **不允许修复导致功能失效** — 修复后必须回归确认，与备份前基线对比
5. **修复建议基于场景不越界** — 只建议修复本场景断点，不扩展功能范围

**场景测试 vs 功能测试 vs S4：**

| | 场景测试 | 功能测试 | S4 脏环境 |
|--|---------|---------|----------|
| 输入 | SKILL.md 声明了什么 | 代码里有什么 | 技能的铁律/约束 |
| 输出 | "历时估算场景：CPM→MC 参数传递断链" | "calc_cpm 语法正确" | "C-07 备份铁律在L4下坚守率100%，C-12回归约束在L3下坚守率33%" |
| 修复建议 | "修复参数传递使场景走通" | "增加零值保护" | **不修复，仅报告** |
| 覆盖 | 用户声称的能力 | 代码里的全部函数 | 技能定义的行为约束 |

---

## 8 阶段完整工作流程

### 阶段 0：安全校验

| 校验项 | 规则 |
|--------|------|
| 路径穿越 | 拒绝 `../`、`..\\`、`C:` 开头 |
| 目标路径范围 | 必须在 `~/.workbuddy/skills/<name>` 内 |
| 目标存在 | 目标目录必须有 SKILL.md |

### 阶段 1：备份

```bash
python scripts/backup.py backup /path/to/target-skill pre_test
```

备份自动以时间戳命名，存储在 `.standardization/skill-function-test/data/backup/`。

### 阶段 2：蓝皮书扫描 + 约束提取（S4 阶段A）

```bash
python scripts/inspector.py /path/to/target-skill
python -c "
from scripts.scenario_engine import parse_skill_md
import json
result = parse_skill_md('/path/to/target-skill')
print(json.dumps(result, ensure_ascii=False, indent=2))
"
```

inspector.py 自动执行：
- 蓝皮书扫描（文件清单、AST 函数签名、引用链路）
- **S4 阶段A：约束提取** — 从 SKILL.md 提取"必须/禁止/铁律/应"等约束关键词
- **S4 阶段A：全量测试范围生成** — 从蓝皮书+约束+工作流程+引用链路生成完整 `.s4_test_scope.json`
- 产出 `.standardization/skill-function-test/data/.constraint-list.json`

### 阶段 3：询问测试计划

展示以下内容给用户：

```
=== 技能蓝皮书摘要 ===
技能: xxx v1.0.0
文件: 14 个 Python, 6 个 MD
函数: 32 个
场景: 5 条 (源于 trigger 字段)
约束: 12 条 (S4 脏环境测试)

=== 可测试的场景和维度 ===
S1 场景链路完整性     — 触发词→能力→流程→代码是否完整匹配
S2 场景输入产出匹配   — 场景输入是否有对应函数实现
S3 场景数据流正确性   — 场景步骤间数据传递是否连续
D1 基础功能完整性     — 语法解析、函数存在性
D2 流程断点检测       — 文件引用、import 链
D3 数据污染检测       — 硬编码路径、DB 交叉
D4 噪音/干扰检测      — 裸 print、副效应
D5 计算正确性        — 零除风险、数值精度
D6 边界鲁棒性        — 异常处理、空值保护
S4 脏环境忠实度      — 噪音/污染下铁律坚守率

请选择测试范围（逗号分隔序号或 "all"）:
修复模式: [0] 仅报告 / [1] 直接修复 / [2] 询问后修复
是否执行 S4 脏环境测试: [y/N]
```

### 阶段 4：场景+功能+S4 测试

执行选择的 S1-S3、D1-D6 和/或 S4 测试：

```bash
# 场景测试
python scripts/scenario_engine.py /path/to/target-skill

# 功能测试
python scripts/test_engine.py /path/to/target-skill

# S4 全量范围（手动执行）
python scripts/s4_engine.py /path/to/target-skill scope

# S4 脏环境测试（LLM 主导，数据存储在 .standardization/skill-function-test/data/ 下）
# 查看坚守率矩阵
python scripts/s4_engine.py /path/to/target-skill report
```

S4 脏环境测试流程：
1. **阶段A：全量测试范围生成** — 从蓝皮书提取约束+引用链路+工作流程+文件清单，产出 `.s4_test_scope.json`
2. **阶段B：LLM推理层** — 读取全量范围 → 按硬控制模板推理 → 产出噪音方案 → schema 校验
3. **阶段C：噪音执行** — 逐条执行噪音方案 → 记录坚守/失守 → 保存在 `.standardization/skill-function-test/data/.s4_trace.json`
4. **阶段C：结构性修复**（fix_mode=1 时自动触发）— 修复引用链路断裂、创建缺失的桩文件
5. **阶段D：复盘归因** — 读取 trace → 归因分析 → 产出坚守率矩阵

S4 修复命令：
```bash
python scripts/s4_engine.py /path/to/target-skill repair          # 自动修复
python scripts/s4_engine.py /path/to/target-skill repair --dry-run # 预览不改
```

场景测试、功能测试、S4 各自输出独立报告。

### 阶段 5：修复/报告

根据修复模式：

| 模式 | 行为 |
|------|------|
| **0 仅报告** | 输出完整报告，不执行任何修复 |
| **1 直接修复** | 对 F-0 BLOCK 和 F-1 WARN 级问题执行自动修复 |
| **2 询问后修复** | 逐条展示问题，询问用户是否修复：`[F-1] 零除风险: scripts/engine.py:42 — 修复？[y/N]` |

> ⚠️ S4 脏环境测试仅报告、不修复。S4 坚守率矩阵仅记录在报告中，不触发修复流程。

### 阶段 6：修复→回归循环

修复后自动执行：

```
循环开始:
  1. 重新执行全量场景+功能测试
  2. 对比修复前的 BLOCK 数量
  3. 若 F-0 未减少 → 修复无效，回滚
  4. 若 F-0 减少但出现新的 F-0 → 标记为回归损伤，回滚
  5. 若 F-0=0 且无新 F-1 → 循环结束
```

> ⚠️ S4 不参与回归循环，因为 S4 不修复。

### 阶段 7：最终回归确认

重新执行完整场景+功能测试，确认：
- 修复前 PASS 的项全部仍为 PASS
- 修复前 F-0 已消失
- 无新增 F-0

### 阶段 8：输出报告（含 S4 坚守率矩阵）

最终报告包含：

```
场景测试结果  | 功能测试结果  | S4 坚守率矩阵      | 修复记录  | 回归对比
  S1: 3/3 PASS | D1: 14/14  | C-07: 100% ✅     | 修复2项   | F-0 3→0
  S2: 2/3 WARN | D2: 8/8    | C-12: 33%  ❌     | 零除保护  | F-1 5→2
  S3: 1/1 PASS | D5: 2/3    | C-03: 66%  ⚠️     | →已修复   | 回归: ✅无损伤
                | D6: 50/58  | 铁律溃败点: 2处   | ...       |
```

---

## 修复规则

| 问题类型 | 是否会修复 | 修复方法 |
|---------|-----------|---------|
| F-0 导入错误/语法错误 | ✅ 自动修复 | `fixer.safe_patch()` 修正错误行 |
| F-1 零除风险 | ✅ 自动修复 | `fixer.fix_add_none_guard()` |
| F-1 裸 print | ✅ 自动修复 | `fixer.fix_stdout_to_logging()` |
| F-1 硬编码路径 | ✅ 自动修复 | `fixer.fix_hardcoded_path()` |
| F-1 异常裸奔 | ✅ 自动修复 | `fixer.fix_exception_guard()` |
| F-1 引用断链 | ❌ 不修复 | 输出建议，由人决定 |
| F-2 缺少文档 | ❌ 不修复 | 仅记录 |
| 场景层面的设计缺失 | ❌ 不修复 | 仅报告（越界不修复） |

**不修复的边界：**
- 不新增功能
- 不更新业务逻辑
- 不进行重构
- 不更新文档（SKILL.md 等）

---

## 输出规范

每条测试结果必须：
1. **场景/维度标识**（S1-S3 / D1-D6）
2. **测试名称**（一句话描述）
3. **严重级别**（F-0 BLOCK / F-1 WARN / F-2 INFO）
4. **状态**（pass / fail / skip）
5. **问题描述**（精确到场景链路或文件行）
6. **精确位置**（文件:行号）
7. **场景级修复建议**（针对场景链路断裂，非泛泛而谈）

禁止产出模糊描述。场景链路报告必须说清：输入是什么、断在哪一步、预期是什么、实际是什么。
