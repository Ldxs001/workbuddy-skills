---
name: novel-weaver
<<<<<<< HEAD
version: 1.7.0
=======
version: 1.8.0
>>>>>>> f725864 (feat: sync novel-weaver v1.8.0)
author: wUwproject
license: MIT
description: 结构化小说写作辅助技能。场景配置→大纲生成→因果链双重验证→pipeline流程门禁→子结构先行规划→情绪混合系统→文风约束→人格驱动→分段写作→连通性补充→风格校验+逻辑检查+大纲忠实度+结尾收束验证。全流程硬约束+门禁跟踪，含MBTI+荣格原型人格、数值化混合情绪、文风槽位。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/novel-weaver/data
tags: ['novel', 'writing', 'story', 'outline', 'scene-setting', 'character', 'narrative', 'workflow']
trigger: 写小说/写故事/写文章/长文写作/故事大纲/场景配置/我想写个故事
trigger_negative: 翻译/改写/润色/校对/简洁回答/做PPT/画图
h1_position: true
meta_field_sync: true
create_permissions_md: true
trigger_quality: add_triggers
faq_unparsable: reformat
antipattern_count: add_examples
external_data_dir: true
---
# novel-weaver — 结构化小说写作辅助技能

> 本文档由 skill-standardization 自动化审计与维护。

## 约束

- 🔴 **[强制] 流程门禁系统** — 每步完成后自动记录到 `novel_state.json` 的 `pipeline` 字段。`set-phase` 在 phase 转换前检查前置门禁，未通过则阻断。`novel_pipeline_gate.py status` 查看状态
- **[必须] 先确认再写作** — 场景配置和大纲必须经用户确认后才能进入写作阶段
- **[必须] 先规划再写作** — 每章必须先 `plan-chapter`（含情绪 tone + 可选 emotions）→ `verify-causality-sub`（因果链验证）→ `context_loader` 通过子结构存在性检查，才可开始写作
- **[必须] 写作规范** — 每段 ≤200行（自然段落结束），atomic write 逐行 fsync，正文禁止 `L##S##` 标记行（会被阻断）
- **[必须] 写作中登记** — 新角色出场时 `novel_state_manager.py add-char`，每章结束时 `novel_timeline.py add`
- **[必须] 每章三检** — 完成后必须运行：连通性检查（novel_continuity.py）、风格校验（novel_style_check.py）、逻辑检查（novel_logic_check.py），然后 `novel_workflow_engine.py finalize-chapter` 推进 phase
- **[必须] 全文两检** — 全文完成后必须 `novel_fidelity.py`（大纲忠实度）+ `set-phase stage3_ready`
- **[必须] 阶段门禁** — `set-phase` 在 →writing（检查 outline_causality 门禁）和 →stage3_ready（检查 fidelity 门禁）时自动调用 `novel_pipeline_gate.py require` 阻断

## 触发条件

**正向触发：**
- 「我想写个故事/小说/文章」→ 触发完整流程
- 「帮我生成故事大纲和场景配置」→ 触发阶段1
- 「根据大纲写下一章」→ 触发阶段2（续写模式）
- 「帮我检查文章前后是否一致」→ 触发风格校验
- 「把这几段串起来」→ 触发连通性补充
- 「检查文章是否偏离了大纲」→ 触发大纲忠实度报告

**否定条件：**
- 用户只是说「改写/润色」——不是本技能范畴
- 用户要求翻译/简洁回答——不触发

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

本技能采用渐进式 MD 体系，SKILL.md 为入口（≤230行），详细内容拆分到 references/。

| 文件 | 内容 |
| ------ |------|
| references/execution_standards.md | 字数管理 / 文体规范 / novel_state.json 结构 / 子结构文件格式 / 章节输出 / 时间线 / 角色表 / 结尾收束 |
| references/hooks.md | 16 个流程钩子 + 门禁系统一览（类型/行为/脚本） |
| references/antipatterns.md | 常见反模式与正确做法 |
| references/faq.md | 常见问题与排除 |
| references/changelog.md | 版本更新日志 |
| references/examples.md | 使用示例 |
| references/permissions.md | 权限说明 |
| references/LICENSE.md | MIT 许可证 |

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
|--------|------|----------|----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、变更类型、修复项、升级说明。 | R-24 |
| `references/examples.md` | 使用示例 | 各场景完整执行示例。包含：CLI 命令、执行过程、输出结果。 | R-25 C-17 |
| `references/execution_standards.md` | 参考文档 | / 层级 / 上限 / 说明 / | 无 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/hooks.md` | 参考文档 | 每个钩子成功完成后自动调用 `pipeline_gate.py pass` 更新全局状态。`set-phase` 在 phase 转换前自动调用 `pipeli | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |
| `scripts/novel_workflow_engine.py` | 主入口 | `plan-chapter`/`write-sub`/`finalize-chapter` 等命令的入口调度器，含 DATA_DIR 声明 | 无 |
| `scripts/novel_state_manager.py` | 状态管理 | `add-char`/`update-sub`/`complete-sub` 状态文件管理 | 无 |
| `scripts/novel_atomic_writer.py` | 写入校验 | `validate_and_write()` 原子写入 + 格式阻断 | 无 |
| `scripts/novel_context_loader.py` | 上下文加载 | 命题指令输出 + 中断恢复检测 | 无 |
| `scripts/novel_continuity.py` | 连通性检查 | `check`(章内)/`cross-chapter`(跨章)/`auto-fix` | 无 |
| `scripts/novel_pipeline_gate.py` | 门禁系统 | `pass`/`require`/`status` 三状态门禁 | 无 |
| `scripts/novel_style_check.py` | 风格校验 | `check-chapter` 风格一致性检查 | 无 |
| `scripts/novel_causality_check.py` | 因果链验证 | `verify-sub` 子结构因果递进检查 | 无 |
| `scripts/novel_character_registry.py` | 角色登记 | 新角色注册 + 属性变更 | 无 |
| `scripts/novel_fidelity.py` | 忠实度检查 | 逐章对比 overview 与实际内容 | 无 |
| `scripts/novel_logic_check.py` | 逻辑检查 | 内容逻辑一致性校验 | 无 |
| `scripts/novel_timeline.py` | 时间线 | `add` 时间事件登记 | 无 |
## 工作流程

### 阶段1：场景配置与大纲

输入：用户模糊的想法

1. LLM生成完整场景配置（人物/时代/地点/风土人情/核心冲突）
2. LLM生成一级大纲（L01-L15 编号 + 标题 + 每章模糊概述）
3. **因果链验证**
   ```
   novel_workflow_engine.py verify-causality-outline <state_path>
   ```
   逐链节检查 L01→L02→…L15 的因果递进。每节的概述必须显式承载"上一章的果 → 下一章的因"。全部 PASS 后才可进入下一步。
4. 输出给用户确认
5. 钩子：用户确认/修正（阻断式）→ 未确认不得进入阶段2
6. 输出：初始化 novel_state.json（style_guide / chapters / characters / timeline）

### 阶段2：逐章写作

输入：当前一级标题 + 模糊概述

0. **写作前加载上下文（命题指令）** — novel_context_loader.py 输出硬性命题指令（标题/概述/情绪基调），LLM 必须作为命题作文严格遵守，不可偏离

1. **子结构先行规划（v1.2 新增硬约束）**
   a. LLM生成子结构细化（S01-S05 编号 + 标题 + 模糊概述 + **情绪提示 tone** + **可选 emotions 数组**）
   b. 展示给用户（可选确认）
   c. **调用 novel_workflow_engine.py plan-chapter 批量注册所有子结构到 novel_state.json**
      — 自动校验每条概述 ≥12 有效字符，不达标则阻断
      — 若通过 outline_causality 门禁，自动推进 phase 到 writing
      — 注册成功后自动写入 pipeline 门禁
   d. **因果链验证**
      ```
      novel_workflow_engine.py verify-causality-sub <state_path> <L##>
      ```
      逐链节检查 S01→S02→… 的因果递进，全部 PASS 后才可开始写作。
      — PASS 时自动写入 pipeline 门禁
   e. 验证：novel_workflow_engine.py verify-chapter 检查全部注册

2. **逐子结构写作循环（硬约束：context_loader 双重阻断）**
   a. 调用 novel_context_loader.py 加载上下文
      — 子结构未注册 → 报错阻断
      — 子结构已完成（status=done）→ 报错阻断，提示用 resume 找下一步
      — 新写模式：输出命题指令框（标题+概述+情绪基调）+ 背景参考
      — **续写模式（中断恢复）**：检测到 .progress 文件，输出已写行数 + 末5行锚点
   b. 用 novel_atomic_writer.py tail 读上一个子结构的末3行（跳过编号标记）作为连接锚点
   c. 写作 ≤200 行，自然段落结束（命题指令框约束，无硬强制）
   d. 用 novel_atomic_writer.py 写入（正文含标记行 L##S## → 报错阻断）
   e. 用 novel_state_manager.py update-sub 更新字数 / 状态（status=done）
      — **自动触发**：该章全部子结构 done → 自动调用 finalize-chapter
        （连通性检查 + 风格校验 + 逻辑检查 + set-phase chapter_done）
      — 逻辑检查发现问题时生成 _fixes.json，LLM 修复后重新跑 finalize-chapter
   > **中断恢复**：下次进入时先运行 resume <state_path> 找到续写点，再调 context_loader 获取命题指令 + 已写内容锚点

**阶段3：全文整合**

输入：全部章节完成

1. 跨章节连通性补充（每章末3行 + 下章首3行）
2. 大纲忠实度报告（novel_fidelity.py — 逐章对比概述 vs 实际内容）
3. 可选精修（用户触发）：备份 → 定位 → 更新 → 局部重新连通
