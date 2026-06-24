---
name: novel-weaver
version: 1.1.0
author: wUwproject
license: MIT
description: 结构化小说写作辅助技能。场景配置 → 大纲生成与逐级细化 → 基于大纲的200行分段写作 → 子结构连通性补充 → 跨章节融合 → 风格一致性校验 → 大纲忠实度报告。支持用户确认/修正环节，确保每级产出符合预期。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/novel-weaver/data
tags: ['novel', 'writing', 'story', 'outline', 'scene-setting', 'character', 'narrative']
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
- **[必须] 写作分段最多200行，以自然叙事段落结束**
- **[必须] 每段写完后立即 atomic write（scripts/novel_atomic_writer.py 按行 fsync + .progress 标记）**
- **[必须] 每章开始时用 novel_character_registry.py 更新角色信息表**
- **[必须] 每章结束时用 novel_timeline.py 记录故事内时间线**
- **[必须] 连通性补充不可跳过（用 novel_continuity.py）**
- **[必须] 每章完成后用 novel_style_check.py 生成风格校验报告**
- **[必须] 全文完成后用 novel_fidelity.py 生成大纲忠实度报告**
- **[必须] 阶段门禁：novel_state.json 初始化前所有钩子均会报错阻断**

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
3. 输出给用户
4. 钩子：用户确认/修正（阻断式）→ 未确认不得进入阶段2
5. 输出：初始化 novel_state.json（style_guide / chapters / characters / timeline）

### 阶段2：逐章写作

输入：当前一级标题 + 模糊概述

0. **写作前加载上下文** — 从 novel_state.json 读取风格/角色/时间线/当前子结构概述
1. LLM生成子结构细化（S01-S05 编号 + 标题 + 模糊概述）
2. 展示给用户（可选确认）
3. 追加到 novel_state.json
4. 逐子结构写作循环：
   a. 读上一个子结构的末3行（跳过编号标记）作为连接锚点
   b. 写作 ≤200 行，自然段落结束
   c. 写入 [project]/chapters/[chapter]/[L##S##].txt，末行追加编号标记
   d. 更新 novel_state.json（字数 / 状态）
5. 本章完成 → 连通性补充 + 风格校验（自动）

**阶段3：全文整合**

输入：全部章节完成

1. 跨章节连通性补充（每章末3行 + 下章首3行）
2. 大纲忠实度报告（逐章对比概述 vs 实际内容）
3. 可选精修（用户触发）：备份 → 定位 → 更新 → 局部重新连通
