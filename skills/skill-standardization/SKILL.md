---
name: skill-standardization
version: 2.87.1
author: wUwproject
license: MIT
description: Skill 标准化规范引擎。支持 R-01~R-26 规范审查（audit/refactor/create 三模式），含权限扫描、数据目录合规检查、渐进式加载、更新日志渐进加载强制、_meta.json 字段规范性、LICENSE 声明合规。R-07 增强：frontmatter trigger/trigger_negative 与正文一致性。
sensitive_access: true
critical_write: false
permission_weight: HIGH
data_dir: ../.standardization/skill-standardization/data
tags: ['standardization', 'skill-builder', 'skill-audit', 'validation', 'json-loader', 'refactor', 'version-bump', 'changelog-auto', 'data-dir']
external_data_dir: true
trigger: ['帮我看看这个技能写得怎么样', '检查这个技能是否规范', '审计 skill', '创建新技能', '更新 skill', '重构技能', 'skill 规范', 'R-规则', '这个 skill 质量怎么样', '帮我检查一下这个 skill 的格式', '看看这个 skill 有没有问题', '给这个 skill 做个体检', '规范一下这个 skill', '标准化这个项目']
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
- **LLM 二次筛强制** — audit 输出全部原始问题后，LLM **必须**逐条审查每条 ERROR/WARN 并分类为真问题或误报。标记误报时 `--classify ID1,ID2,ID3`（如 `--classify 42,55,67`），不得跳过或笼统说"无需处理"
- **LLM 手动修不许退出循环** — 遇到 `.remaining_llm.json` 时，LLM **必须立即读取并手动修复**，然后重新审计直到 0 ERROR 0 WARN。**禁止询问用户**、禁止停止、禁止跳过
- **HTML 审计报告强制输出** — 每次 `audit` 执行完毕，**必须**确认 `.audit_report.html` 已生成
- **`--fix` 自动修正后** — 将 fix_details 转化为可读 changelog 并用 safe_io 写入

## 触发条件

**正向触发：**
- [帮我看看这个技能写得怎么样 / 这个技能规范吗 / 质量怎么样]
- [检查/审查/评估一下这个 skill / 跑一遍规范 / 做个体检]
- [创建/生成一个新技能 / 把 xxx 做成 skill / 标准化这个项目]
- [更新/改造一下这个 skill / 重构这个技能 / 升级一下]
- [这个 skill 的 frontmatter/描述/规则怎么写 / 怎么优化]
- [用 skill-standardization 审计/改造某技能]
- [检查某技能的 SKILL.md 是否规范]
- [创建/更新/重构一个 skill]
- [skill 的 frontmatter 怎么写]
- [R-xx 规则是什么意思]

**否定条件：**
- [给这个 skill 做个检查 / 看看有没有问题 / 格式对吗]
- 用户只是问[你有什么技能]——这是闲聊，不是真的要审计/改造
- 用户要求执行某个 skill 的常规功能——应直接调用该 skill 本身，而不是先审计它
- 用户只是提到[skill]这个词，但没有明确的审计/创建/改造意图

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
| -------- |------| ---------- |----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/architecture.md` | 架构设计 | skill-standardization 整体架构。包含：模块关系、数据流、核心设计决策。 | 无 |
| `references/blueprint_flow.md` | 参考文档 | > 定义蓝皮书（Blueprint）、审计（Audit）、修复循环（Fix Loop）三者的关系与流程。 | 无 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、更新类型、修复项、升级说明。 | R-24 |
| `references/data_dir_map.md` | 路径参考 | 数据目录路径对照表。包含：安装目录、标准化目录、备份目录及用途。 | 无 |
| `references/examples.md` | 使用示例 | 各场景完整执行示例。包含：CLI 命令、执行过程、输出结果。 | R-25 C-17 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/guide.md` | 使用指南 | 三种执行模式操作教程。包含：audit/create/refactor 流程、参数说明、注意事项。 | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `references/reference.md` | 命令参考 | CLI 完整命令参考。包含：所有参数、子命令、选项、示例用法。 | 无 |
| `references/rules.md` | 审计规则 | R-01~R-26 审计规则定义。包含：检查逻辑、修复指引、设计背景。 | R-01~R-26 |
## 能力与限制

本技能能做什么、不能做什么，一目了然：

| 能力 | 说明 | 限制 |
| ------ |------| ------ |
| **审计现有 skill** | R-01~R-26 全量检查，输出 PASS/WARN/FAIL 逐条明细及上下文行 | 仅检查 SKILL.md + _meta.json + scripts/ 文件结构和代码静态分析，不检查 Python 运行时行为 |
| **创建新 skill** | 从模板生成标准骨架（SKILL.md / _meta.json / references/ / scripts/） | 只生成结构模板和占位符，功能代码需要手动填充 |
| **改造非标 skill** | 自动迁移文件到正确位置、补充 permissions.md、修复格式问题 | 不处理跨技能依赖、不自动生成功能代码 |
| **批量审计** | `--audit-all` 参数扫描 skills/ 下多个 skill | 仅支持 skills/ 目录下的一级子目录（不支持嵌套目录） |
| **自动修复** | `--fix` 自动修正 SKILL.md frontmatter / 版本号 / 数据目录 / 触发词 / 反模式 / FAQ / 写作规范等格式问题，覆盖 R-01~R-26 共 20+ 条规则 | 仅修复格式/结构/路径/生成类问题，**不修复代码逻辑错误**。<br>修复后需运行 `--verify` + `--show-fix` 两阶段验证确认 |
| **权限安全扫描** | 自动检测脚本中的文件删除/网络请求/subprocess 调用 | 扫描基于 AST 静态分析，无法检测动态代码执行的权限需求 |

> 触发本技能后立即可见的能力输出：读取目标 SKILL.md 中的 frontmatter/正文/references/scripts → 执行 R-01~R-26 规则审查 → 输出审查报告（含每条规则的 PASS/WARN/FAIL 状态 + 详细原因 + 附近代码上下文）。

## 快速开始

**场景：审计单个 skill**
> 对 color-toolkit 执行全量 R-01~R-26 审计
```bash
python -m scripts.skill_audit audit ~/.workbuddy/skills/color-toolkit --confirmed
```
  - **输入**: color-toolkit
  - **输出**: R-01~R-26 逐条检查 → PASS/WARN/FAIL 报告 → 总计: 26 | 通过: 24 | 失败: 2

**场景：审计+修复**
> 审计并自动修复格式类问题
```bash
python -m scripts.skill_audit audit ~/.workbuddy/skills/color-toolkit --fix --confirmed
```
  - **输入**: color-toolkit（有若干 R-10/R-11 问题）
  - **输出**: 自动修正 → 重新审计 → 修复前后对比: 修复前 2 ERROR → 修复后 0 ERROR

**场景：全流程改造**
> 对非标准 skill 执行全流程改造
```bash
python -m scripts.skill_audit refactor ~/.workbuddy/skills/color-toolkit --confirmed
```
  - **输入**: color-toolkit（非标准结构）
  - **输出**: 蓝皮书 → 备份 → 审计 → 修复循环 → 双0验证 → bump feature → cleanup
## 快速开始

```bash
# 审计（仅检查）
python -m scripts.skill_audit audit <skill-dir> --confirmed
# 审计+修复
python -m scripts.skill_audit audit <skill-dir> --fix --confirmed
# 全流程改造
python -m scripts.skill_audit refactor <skill-dir> --confirmed
```

→ 详见 渐进式文件索引表 获取完整交互示例

## 工作流程

1. **模式识别** → 输入 用户请求 → 输出 匹配模式表 — LLM 对照关键词表确定 audit/create/update/refactor 模式
2. **蓝皮书扫描** → 输入 SKILL.md + scripts/ → 输出 蓝皮书 JSON — 提取技能结构：文件名、函数、依赖关系
3. **备份** → 输入 技能目录 → 输出 .zip 备份 — 备份到 .standardization/<skill>/backup/
4. **全量审计** → 输入 SKILL.md + references/ → 输出 审计报告 — R-01~R-26 逐条输出原始问题（ERROR + WARN 全部展示，工具不做自动排除）
5. **★ LLM 二次筛（强制，不可跳过）** →
   - 输入：审计报告中的全部非 PASS 项（ERROR + WARN）
   - 动作：LLM 逐条审查每条问题，判断为真问题或误报
     - 真误报 → **必须** `--classify ID1,ID2,ID3` 逐条标记（ID 从 `--verify` 输出获取）。禁止不带数字 ID
     - 真问题 → 保留在修复列表，不执行 `--classify`
   - 铁律：**逐条审查**，每次 `--classify ID1,ID2,ID3` **必须附带数字 ID**，不得合计笼统说"无需处理"
   - 输出：已分类的问题清单（误报 vs 真问题）
   - 验证：重新 audit 确认分类已完成，`--classify` 查看已标记列表
6. **细碎修复循环** → 输入 审计 FAIL 列表（真问题）→ 输出 修复后的文件 — auto-fix + LLM 手动修复，代码级确认循环
7. **双0验证** → 输入 修复后的技能 → 输出 verify 报告 — --verify 输出编号 FAIL，LLM 逐条判断
8. **一致性审查** → 输入 文档 + 代码 → 输出 一致性报告 — 对比流程描述与实际代码是否一致
9. **bump + cleanup** → 输入 审核通过的技能 → 输出 新版本 — 版本号三端同步 + 清理临时文件
## 数据目录说明

本技能的数据文件（审查缓存、进度文件、备份、日志等）存放在：

```text
../.standardization/skill-standardization/
├── data/
│   ├── .verify_fix_map.json  # --verify 输出的修复指引映射
│   ├── .verify_fp.json       # --classify 标记的误判列表
│   └── ...
├── backup/
│   └── <skill>_<timestamp>.zip  # refactor 自动备份
├── logs/
│   └── ops.log               # 操作日志
└── ...
```

> 安装目录 `skills/skill-standardization/` 只保留 SKILL.md 和 scripts/，数据文件不越位。