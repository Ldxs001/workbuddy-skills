---
name: novel-weaver
version: 1.2.1
author: wUwproject
license: MIT
description: 结构化小说写作辅助技能。场景配置 → 大纲生成与逐级细化 → 因果链双重验证（章级+子结构级）→ workflow_engine 强制子结构先行规划（含情绪提示）→ 基于大纲的200行分段写作 → 子结构连通性补充（含 auto-fix）→ 跨章节融合 → 风格一致性校验 + 逻辑一致性检查（人物/时间线/概述匹配度）→ 大纲忠实度报告。全流程硬约束：context_loader 阻断未注册子结构，atomic_writer 禁止正文标记行，set-phase 前置检查报告存在。
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

> 本文档由 WorkBuddy 在主人 wUwproject 的指导下撰写和维护。

## 约束

- **[必须] 场景配置和大纲必须经用户确认后才能进入写作阶段** — 跳过确认视为未完成
- **[必须] 大纲级因果链验证** — 用户确认大纲前，必须运行 workflow_engine.py verify-causality-outline，逐链节检查 L01→L02→… 的因果递进，全部 PASS 后才可确认
- **[必须] 子结构级因果链验证** — plan-chapter 完成后、写作开始前，必须运行 workflow_engine.py verify-causality-sub，逐链节检查 S01→S02→… 的因果递进，全部 PASS 后才可开始写作
- **[必须] 子结构必须先规划再写作** — 调用 workflow_engine.py plan-chapter 批量注册所有子结构（含情绪提示 tone），然后 context_loader 才能通过硬检查
- **[必须] 写作分段最多200行，以自然叙事段落结束**
- **[必须] 每段写完后立即 atomic write（scripts/novel_atomic_writer.py 按行 fsync + .progress 标记）**
- **[必须] 正文中禁止出现子结构标记行（L##S##）— atomic_writer 会阻断**
- **[必须] 新角色出场时用 novel_state_manager.py add-char 更新角色信息表**
- **[必须] 每章结束时用 novel_timeline.py 记录故事内时间线**
- **[必须] 连通性补充不可跳过（用 novel_continuity.py）**
- **[必须] 每章完成后用 novel_style_check.py 生成风格校验报告**
- **[必须] 每章完成后用 novel_logic_check.py 生成逻辑一致性报告**
- **[必须] 全文完成后用 novel_fidelity.py 生成大纲忠实度报告**
- **[必须] 阶段门禁：set-phase chapter_done 前会检查各报告是否存在**

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
| references/hooks.md | 11 个流程钩子一览（类型/行为/脚本/阶段门禁） |
| references/antipatterns.md | 常见反模式与正确做法 |
| references/faq.md | 常见问题与排除 |
| references/changelog.md | 版本更新日志 |
| references/examples.md | 使用示例 |
| references/permissions.md | 权限说明 |
| references/LICENSE.md | MIT 许可证 |

## 工作流程

### 阶段1：场景配置与大纲

输入：用户模糊的想法

1. LLM生成完整场景配置（人物/时代/地点/风土人情/核心冲突）
2. LLM生成一级大纲（L01-L15 编号 + 标题 + 每章模糊概述）
3. **因果链验证（v1.2.1 新增阻断式钩子）**
   ```
   workflow_engine.py verify-causality-outline <state_path>
   ```
   逐链节检查 L01→L02→…L15 的因果递进。每节的概述必须显式承载"上一章的果 → 下一章的因"。全部 PASS 后才可进入下一步。
4. 输出给用户确认
5. 钩子：用户确认/修正（阻断式）→ 未确认不得进入阶段2
6. 输出：初始化 novel_state.json（style_guide / chapters / characters / timeline）

### 阶段2：逐章写作

输入：当前一级标题 + 模糊概述

0. **写作前加载上下文** — 从 novel_state.json 读取风格/角色/时间线/当前子结构概述

1. **子结构先行规划（v1.2 新增硬约束）**
   a. LLM生成子结构细化（S01-S05 编号 + 标题 + 模糊概述 + **情绪提示 tone**）
   b. 展示给用户（可选确认）
   c. **调用 workflow_engine.py plan-chapter 批量注册所有子结构到 novel_state.json**
   d. **因果链验证（v1.2.1 新增）**
      ```
      workflow_engine.py verify-causality-sub <state_path> <L##>
      ```
      逐链节检查 S01→S02→… 的因果递进，全部 PASS 后才可开始写作。
   e. 验证：workflow_engine.py verify-chapter 检查全部注册
   f. **此时 phase 自动推进到 writing**

2. **逐子结构写作循环（硬约束：context_loader 会检查子结构必须已注册）**
   a. 调用 novel_context_loader.py 加载上下文（无子结构 → 报错阻断）
   b. 读上一个子结构的末3行（跳过编号标记）作为连接锚点
   c. 写作 ≤200 行，自然段落结束
   d. 用 atomic_writer.py 写入（正文含标记行 L##S## → 报错阻断）
   e. 用 state_manager.py update-sub 更新字数 / 状态

3. **本章完成 → 自动执行三道检查**
   a. 连通性补充（novel_continuity.py + auto-fix）
   b. 风格校验（novel_style_check.py）
   c. 逻辑检查（novel_logic_check.py — 人物行为一致性 / 时间线逻辑 / 内容-概述匹配度）

4. **阶段推进** — 调用 workflow_engine.py finalize-chapter 一键完成检查+set-phase chapter_done

**阶段3：全文整合**

输入：全部章节完成

1. 跨章节连通性补充（每章末3行 + 下章首3行）
2. 大纲忠实度报告（novel_fidelity.py — 逐章对比概述 vs 实际内容）
3. 可选精修（用户触发）：备份 → 定位 → 更新 → 局部重新连通
