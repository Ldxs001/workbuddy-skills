---
name: skill-standardization
version: 2.80.1
author: wUwproject
license: MIT
description: Skill 标准化规范引擎。支持 R-01~R-26 规范审查（audit/refactor/create 三模式），含权限扫描、数据目录合规检查、渐进式加载、更新日志渐进加载强制、_meta.json 字段规范性、LICENSE 声明合规。R-07 增强：frontmatter trigger/trigger_negative 与正文一致性。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/skill-standardization/
tags: ['standardization', 'skill-builder', 'skill-audit', 'validation', 'json-loader', 'refactor', 'version-bump', 'changelog-auto', 'data-dir']
external_data_dir: true
trigger: ['帮我看看这个技能写得怎么样', '检查这个技能是否规范', '审计 skill', '创建新技能', '更新 skill', '重构技能', 'skill 规范', 'R-规则', '这个 skill 质量怎么样', '帮我检查一下这个 skill 的格式', '看看这个 skill 有没有问题', '给这个 skill 做个体检', '规范一下这个 skill', '标准化这个项目- 帮我看看这个技能写得怎么样', '检查这个技能是否规范', '审计 skill', '创建新技能', '更新 skill', '重构技能', 'skill 规范', 'R-规则']
trigger_negative: 当用户仅闲聊或问你有什么技能时不触发；单步任务如查看文件不触发
meta_field_sync: true
h1_position: true
data_dir_compliance: true
create_permissions_md: true
---
# skill-standardization

## 约束

- **`.md` 文件禁止使用 Write/Edit 工具更新** — 必须用 `scripts/` 下的 Python 脚本原子写入
- **版本号三端一致** — 更新时同步 `SKILL.md` / `_meta.json` / `CHANGELOG.md`
- **0 ERROR 0 WARN 铁律强制** — 更新后用 `audit --verify` 验证，非误报项必须全部修复，exit(0) 方可提交
- **`--fix` 自动修正后** — 将 fix_details 转化为可读 changelog 并用 safe_io 写入

## 触发场景

当用户提出以下类型请求时，应触发本技能：

**自然语言（推荐）**：
- [帮我看看这个技能写得怎么样 / 这个技能规范吗 / 质量怎么样]
- [检查/审查/评估一下这个 skill / 跑一遍规范 / 做个体检]
- [给这个 skill 做个检查 / 看看有没有问题 / 格式对吗]
- [创建/生成一个新技能 / 把 xxx 做成 skill / 标准化这个项目]
- [更新/改造一下这个 skill / 重构这个技能 / 升级一下]
- [这个 skill 的 frontmatter/描述/规则怎么写 / 怎么优化]

**技术关键词**：
- [用 skill-standardization 审计/改造某技能]
- [检查某技能的 SKILL.md 是否规范]
- [创建/更新/重构一个 skill]
- [skill 的 frontmatter 怎么写]
- [R-xx 规则是什么意思]

**不触发**（以下情况不应触发本技能）：

- 用户只是问[你有什么技能]——这是闲聊，不是真的要审计/改造
- 用户要求执行某个 skill 的常规功能——应直接调用该 skill 本身，而不是先审计它
- 用户只是提到[skill]这个词，但没有明确的审计/创建/改造意图

## 能力与限制

本技能能做什么、不能做什么，一目了然：

| 能力 | 说明 | 限制 |
|------|------|------|
| **审计现有 skill** | R-01~R-26 全量检查，输出 PASS/WARN/FAIL 逐条明细及上下文行 | 仅检查 SKILL.md + _meta.json + scripts/ 文件结构和代码静态分析，不检查 Python 运行时行为 |
| **创建新 skill** | 从模板生成标准骨架（SKILL.md / _meta.json / references/ / scripts/） | 只生成结构模板和占位符，功能代码需要手动填充 |
| **改造非标 skill** | 自动迁移文件到正确位置、补充 permissions.md、修复格式问题 | 不处理跨技能依赖、不自动生成功能代码 |
| **批量审计** | `--audit-all` 参数扫描 skills/ 下多个 skill | 仅支持 skills/ 目录下的一级子目录（不支持嵌套目录） |
| **自动修复** | `--fix` 自动修正 SKILL.md frontmatter / 版本号 / 数据目录 / 触发词 / 反模式 / FAQ / 写作规范等格式问题，覆盖 R-01~R-26 共 20+ 条规则 | 仅修复格式/结构/路径/生成类问题，**不修复代码逻辑错误**。<br>修复后需运行 `--verify` + `--show-fix` 两阶段验证确认 |
| **权限安全扫描** | 自动检测脚本中的文件删除/网络请求/subprocess 调用 | 扫描基于 AST 静态分析，无法检测动态代码执行的权限需求 |

> 触发本技能后立即可见的能力输出：读取目标 SKILL.md 中的 frontmatter/正文/references/scripts → 执行 R-01~R-26 规则审查 → 输出审查报告（含每条规则的 PASS/WARN/FAIL 状态 + 详细原因 + 附近代码上下文）。

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
|--------|------|----------|----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/architecture.md` | 架构设计 | skill-standardization 整体架构。包含：模块关系、数据流、核心设计决策。 | 无 |
| `references/blueprint_flow.md` | 参考文档 | > 定义蓝皮书（Blueprint）、审计（Audit）、修复循环（Fix Loop）三者的关系与流程。 | 无 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、变更类型、修复项、升级说明。 | R-24 |
| `references/data_dir_map.md` | 路径参考 | 数据目录路径对照表。包含：安装目录、标准化目录、备份目录及用途。 | 无 |
| `references/examples.md` | 使用示例 | 各场景完整执行示例。包含：CLI 命令、执行过程、输出结果。 | R-25 C-17 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/guide.md` | 使用指南 | 三种执行模式操作教程。包含：audit/create/refactor 流程、参数说明、注意事项。 | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `references/reference.md` | 命令参考 | CLI 完整命令参考。包含：所有参数、子命令、选项、示例用法。 | 无 |
| `references/rules.md` | 审计规则 | R-01~R-26 审计规则定义。包含：检查逻辑、修复指引、设计背景。 | R-01~R-26 |
## 工作流程

### 【流程门禁】Step 0：模式识别（强制）

**本技能有五个模式，各自对应不同的命令和流程。执行前必须按以下规则识别用户意图，不可跳过此步骤直接执行。**

1. 读取用户的原始请求
2. 对照下表，匹配关键词：

| 用户请求包含 | → 模式 | → 执行命令 |
|-------------|--------|-----------|
| 仅审查/仅检查/看结果/不要改任何东西 | **audit** | `python -m scripts.skill_audit audit <skill_dir>` |
| 创建/生成/创建/把 xxx做成skill | **create** | `python -m scripts.skill_builder create <name> --desc "描述"` |
| 审计/检查/审查/评估/更新/修复/升级/跑一遍规范/做个体检 | **update** | `python -m scripts.skill_audit audit <skill_dir> --fix` |
| 改造/重构/迁移/大改/标准化/规范化 | **refactor** | `python -m scripts.skill_audit refactor <skill_dir>` |
| 升版本/版本号更新（内部流程自动触发，非用户主动请求） | **bump** | `python -m scripts.skill_audit bump <skill_dir>` |

3. 匹配到关键词 → 走对应模式流程
4. 未匹配到任何关键词 → **询问用户具体意图**，不得自行猜测

---

### audit 模式（仅审查）
1. **语义确认** — 输出模式描述，LLM 确认模式是否正确
2. 读取目标 skill 的 SKILL.md
3. 执行 R-01~R-26 规则检查
4. 输出审查报告（PASS/WARN/FAIL），逐条列出通过/失败/跳过
5. **`--fix` 自动修复** — 自动修正可修复项（frontmatter/版本号/数据目录/反模式/FAQ 等 20+ 条规则）
6. **`--verify` 验证** — 输出编号 FAIL 条目 `[#ID]`，每条含独立问题描述
7. **`--show-fix ID1,ID2`** — 筛选真问题后获取对应修复指引

→ 修复指引获取：`python -m scripts.skill_audit audit <skill_dir> --show-fix 1,3,4`

**create 模式**（创建新技能——从零开始生成骨架）：
- **适用场景**：用户说"创建/生成/创建一个技能，把 xxx 做成 skill"
- **不适用**：用户说"审查/改造/更新已有技能"
- 流程：骨架生成 → 填充内容 → audit 验证 → cleanup
- 命令：`python -m scripts.skill_builder create <name> --desc "描述"`

**update 模式**（轻量更新——技能结构已标准，只需审计修复）：
- **适用场景**：用户说"审计/检查/更新/修复/升级某个技能"
- **不适用**：用户说"改造/迁移/重构/大改/标准化"
- **流程**：
  1. 语义确认
  2. 蓝皮书扫描 [1/7]
  3. 变更声明（流程钩子，LLM 输出 `{"changed_files": [...], "description": "..."}`）[2/7]
  4. 针对性审计（仅跑 changed_files 相关规则）[3/7]，内部含 **★★★ 细碎修复循环 ★★★** [4/7]：
     - 自动修复可修复项
     - LLM 修复后通过 `--fixed-rules R-23,R-26` 声明修了哪些规则
     - 代码自动跑针对性审计确认
     - 还有 FAIL → 继续修；全部 PASS → 退出循环
  5. 全量审计确认（双 0 验证）[5/7]
  6. 针对性一致性审查 + 修复循环 [6/7] — 含细碎钩子，LLM 需对比流程描述与代码是否一致
  7. bump (PATCH) + 最终报告 [7/7]
- 命令：`python -m scripts.skill_audit audit <skill_dir> --confirmed`（先审计拿报告，LLM 筛查后再执行后续步骤）

**refactor 模式**（全量改造——技能非标准/结构混乱/需要迁移）：
- **适用场景**：用户说"改造/重构/迁移/大改/标准化/规范化某个技能"
- **不适用**：用户说"简单审计/检查一下"（应走 update）
- **流程**：
  1. 语义确认 → LLM 检查目录结构，识别并排除非技能目录
  2. 蓝皮书扫描（跳过已排除目录）[1/8]
  3. 备份（zip 到 `.standardization/<skill>/backup/`）+ 启动 cleanup session [2/8]
  4. 全量审计 [3/8]
  5. **★★★ 细碎修复循环 ★★★** [4/8] — 代码级强制：
     - 自动修复可修复项（`--fix` 自动修 frontmatter/版本号/数据目录等）
     - LLM 手动修复后通过 `--fixed-rules R-23,R-26` 声明
     - 代码自动跑针对性审计确认
     - 还有 FAIL → 继续修；全部 PASS → 退出循环
  6. 全量审计确认（双 0 验证）[5/8]
  7. 全量一致性审查 + 修复循环 [6/8] — 含细碎钩子，LLM 需对比流程描述与代码是否一致
  8. bump (FEATURE) + 最终报告 [7/8] + cleanup（`end_session()` 驱动）[8/8]
- 命令：`python -m scripts.skill_audit refactor <skill_dir> --confirmed`（先走蓝皮书+备份+审计，LLM 筛查后再执行后续步骤）

> **⚠️ 关于细碎循环的关键认知**：
> - 循环是**代码级强制**的，不是"LLM 自觉"——`_run_audit_loop()` 在 `cmd_update()` 和 `cmd_refactor()` 中硬编码调用
> - LLM 的角色是：修复问题 → 通过 `--fixed-rules` 声明修了什么 → 等代码自动确认
> - LLM **不需要**手动判断"要不要继续循环"，代码会自动跑审计并决定继续或退出
> - 循环上限：update 10 轮，refactor 20 轮，超限 exit(1) 阻断
> - 不要在循环中做不相关的事（如改版本号、写 changelog），这些是 bump 步骤的职责

> **⚠️ 关键约束**：audit 输出的报告包含 PASS/WARN/FAIL 三类。`--fix` 仅修复格式类问题（frontmatter/版本号/数据目录），**文档一致性（R-23）等问题需要 LLM 阅读报告后逐条判断并手动处理**。`--fixed` 不等于"已处理完毕"。
>
> **关于细碎循环**：update/refactor 模式中，`_run_audit_loop()` 是代码级强制的修复循环。LLM 修完问题后通过 `--fixed-rules` 声明，代码自动跑针对性审计确认。LLM 不需要自行判断"循环该不该继续"，代码会处理。详见 update/refactor 流程描述。

## 快速开始

### 场景 1：审计（仅检查）

```bash
python -m scripts.skill_audit audit /path/to/target-skill --confirmed
# → PASS (25/25 通过)
```

### 场景 2：审计+修复

```bash
python -m scripts.skill_audit audit /path/to/target-skill --fix --confirmed
# → 修正后 PASS
```

### 场景 3：全流程改造

```bash
python -m scripts.skill_audit refactor /path/to/target-skill --confirmed
# → 1/7 蓝皮书 → 2/7 备份 → 3/7 审计 → 4/7 修复 → 5/7 验证 → 6/7 bump → 7/7 清理
```

## 数据目录说明

本技能的数据文件（审查缓存、进度文件、备份、日志等）存放在：

```text
../.standardization/skill-standardization/
```

> 安装目录 `skills/skill-standardization/` 只保留 SKILL.md 和 scripts/，数据文件不越位。