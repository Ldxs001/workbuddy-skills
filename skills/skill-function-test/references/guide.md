# skill-function-test 完整使用指南

> **场景测试（Scenario Testing）** — 不以函数为单位，以 **场景链路** 为单位。
> 备份 → 蓝皮书+约束+全量范围 → LLM写场景测试用例 → 场景+功能+S4 → 修复循环 → 回归确认 → 报告+结论写入。

---

## 核心原则

1. **场景驱动** — LLM 基于目标技能的 SKILL.md 和蓝皮书手工编写场景测试用例，每条用例代表一条真实用户场景
2. **测试用例自带 modules 字段** — LLM 写测试时直接指定涉及的 Python 模块名，引擎直接用蓝皮书映射，不再猜词
3. **无 CLI 入口的模块也测试** — 引擎用 `importlib.import_module()` 验证模块可加载，确保无语法/依赖问题
4. **功能测试做底座** — D1-D6 功能测试定位到具体断点行号，场景测试定位到链路断裂位置
5. **S4 全量范围扫描** — 从蓝皮书提取约束、引用链路、工作流程、文件清单作为测试范围，噪音下测铁律坚守率
6. **不允许修复导致功能失效** — 修复后必须回归确认，与备份前基线对比

**场景测试 vs 功能测试 vs S4：**

| | 场景测试 | 功能测试 | S4 执行忠实度 |
|--|---------|---------|----------|
| 输入 | 手工编写的场景测试用例 + modules 字段 | 蓝皮书的代码分析 | 技能的铁律/约束 |
| 输出 | "模块 runner 导入成功 / economic_analysis_engine --help rc=0" | "calc_cpm 语法正确" | "C-07 备份铁律在L4下坚守率100%" |
| 测试方式 | CLI 脚本 subprocess + 非 CLI 模块 importlib | AST 扫描 + 代码检查 | 噪音方案回放 |
| 覆盖 | 用户声称的业务场景 | 代码里的全部函数 | 技能定义的行为约束 |

---

## 完整工作流程

### 阶段 0：安全校验 + 时间线初始化

```bash
# 初始化时间线（hooks 自动补齐，手动也行）
python scripts/timeline.py init /path/to/target-skill
```

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

### 阶段 2：蓝皮书扫描 + 约束提取

```bash
python scripts/inspector.py /path/to/target-skill
```

inspector.py 自动执行：
- 蓝皮书扫描（文件清单、AST 函数签名、引用链路）
- S4 约束提取
- S4 全量测试范围生成

### 阶段 3：LLM 编写场景测试用例

LLM 基于目标技能的 SKILL.md 和蓝皮书，手工编写 `.s_test_plan.json`。

hooks 阻断检查：文件存在且 ≥3 条才放行。

每条测试用例建议填写 `modules` 字段，指定涉及的 Python 模块名（不含 `.py` 后缀），字段对照蓝皮书的 `file_manifest.python` 列表。

格式见 `references/s-test-plan-schema.md`。

### 阶段 4：场景测试（S1-S3）

```bash
python scripts/scenario_engine.py /path/to/target-skill
```

对每条测试用例：
- 指定了有 CLI 入口的模块 → 执行 `python xxx.py --help` 验证返回值
- 指定了无 CLI 入口的模块 → `importlib.import_module()` 验证模块可加载

### 阶段 5：功能测试（D1-D6）

```bash
python scripts/test_engine.py /path/to/target-skill
```

### 阶段 6：S4 执行忠实度（可选）

```bash
# 全量范围（手动执行）
python scripts/s4_engine.py /path/to/target-skill scope

# LLM 编写噪声方案 → 校验 → 回放
python scripts/s4_engine.py /path/to/target-skill play
```

S4 执行忠实度测试流程：
1. **阶段A：全量测试范围生成** — 从蓝皮书提取约束+引用链路+工作流程+文件清单
2. **阶段B：LLM推理层** — 读取全量范围 → 设计噪音方案 → schema 校验
3. **阶段C：噪音执行** — 逐条执行噪音方案 → 记录坚守/失守
4. **阶段D：复盘归因** — 归因分析 → 坚守率矩阵

### 阶段 7：修复循环（可选）

| 模式 | 行为 |
|------|------|
| **0 仅报告** | 输出完整报告，不执行任何修复 |
| **1 直接修复** | 对 F-0 BLOCK 和 F-1 WARN 级问题执行自动修复 |

修复后自动执行回归确认：
- 重新执行全量场景+功能测试
- 对比修复前的 BLOCK 数量
- F-0 未减少 → 回滚
- 出现新 F-0 → 标记回归损伤，回滚

### 阶段 8：输出报告

```bash
python scripts/gen_report.py /path/to/target-skill
```

生成 HTML + Markdown 双格式报告。gen_report 自动将测试概览写入 `<skill>/references/permissions.md`，相同数据指纹跳过。

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
