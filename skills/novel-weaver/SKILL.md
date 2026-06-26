---
name: novel-weaver
slug: novel-weaver
displayName: Novel Weaver
version: 1.19.1
author: wUwproject
license: MIT
description: 结构化小说写作辅助技能。场景配置→大纲生成→因果链双重验证→pipeline流程门禁→子结构先行规划→情绪混合系统→文风约束→人格驱动→分段写作→连通性补充→风格校验+逻辑检查+大纲忠实度+结尾收束验证。全流程硬约束+门禁跟踪，含MBTI+荣格原型人格、数值化混合情绪、文风槽位。
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/novel-weaver/projects
tags: ['novel', 'writing', 'story', 'outline', 'scene-setting', 'character', 'personality', 'emotion', 'writing-style', 'narrative', 'workflow']
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

- **[强制] 流程门禁系统** —  在阶段转换时自动 require 前置门禁：→writing 检查 outline_causality + sub_causality；→stage3_ready 检查 fidelity + ending_verify。门禁状态存于 ， 查看
- 🔴 **[强制] 核心规划字段保护** — `novel_state_manager.py` 对 `chapters[].title/overview`、`sub_structures[].title/summary/tone`、`characters[].name/role/traits/mbti/archetype`、`novel_info/writing_style/setting` 做 MD5 指纹校验，**LLM 不可更新**。仅 `word_count/status/timeline/notes` 等运行时字段可更新
- **[必须] 先确认再写作** — 场景配置和大纲必须经用户确认后才能进入写作阶段
- **[必须] 先规划再写作** — 每章必须先 `plan-chapter`（含情绪 tone + 可选 emotions）→ `novel_causality_check.py sub-structure`（因果链验证）→ `context_loader` 通过子结构存在性检查，才可开始写作
- **[必须] 写作规范** — 每段 ≤200行（自然段落结束），atomic write 逐行 fsync，正文禁止 `L##S##` 标记行（会被阻断）
- **[必须] 写作中登记** — 新角色出场时 `novel_state_manager.py add-char`，每章结束时 `novel_timeline.py add`
- **[必须] 每章四检 + 阻断循环** — 完成后运行 `finalize-chapter`：章内连通性 → 跨章承诺链 → 风格校验 → 逻辑检查 → 聚合硬性问题并阻断（不通过则不标记门禁，不推进 phase），通过后自动推进 phase
- **[必须] 全文三检** — 全文完成后必须：`novel_fidelity.py`（大纲忠实度）+ `verify-ending`（结尾收束验证）+ `set-phase stage3_ready`

## 数据目录

⚠️ **LLM 禁止手工拼写路径！** 以下代码可自动获取正确路径：

**列出所有项目：**
```python
import sys; sys.path.insert(0, r'~/.workbuddy/skills/novel-weaver/scripts')
from _path_utils import list_projects, resolve_state_path, DATA_DIR
projects = list_projects()
# DATA_DIR = ~/.workbuddy/skills/.standardization/novel-weaver/projects/
```

**读取项目状态：**
```python
# 通过 _path_utils 自动解析（优先）
state_path = resolve_state_path()
if state_path:
    import json; state = json.loads(open(state_path, encoding='utf-8').read())

# 或直接用完整路径（如已知项目名）
from _path_utils import DATA_DIR
proj = DATA_DIR / '项目名' / 'data' / 'novel_state.json'
```

**目录结构（代码推导，仅供理解）：**
```text
{DATA_DIR}/<项目名>/
├── data/novel_state.json          ← 状态文件
├── data/.workbuddy/gate_state.json ← 门禁状态
├── data/reports/                   ← 检查报告
├── chapters/L##/S##.txt          ← 章节正文（每子结构一个文件）
└── .project                       ← 路径缓存
```

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
| references/hooks.md | 参考文档 | 全量流程钩子 + 门禁系统一览（类型/行为/脚本） |
| references/antipatterns.md | 常见反模式与正确做法 |
| references/faq.md | 常见问题与排除 |
| references/changelog.md | 版本更新日志 |
| references/examples.md | 使用示例 |
| references/permissions.md | 权限说明 |
| references/LICENSE.md | MIT 许可证 |

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
| -------- |------| ---------- |----------|
| `references/LICENSE.md` | 许可协议 | 开源许可证声明（MIT）。包含：MIT 许可证完整文本。 | R-26 |
| `references/antipatterns.md` | 规范指南 | skill 编写中的常见反模式。包含：错误做法示例、正确做法示例、避坑指引。 | R-18 |
| `references/changelog.md` | 版本管理 | 版本更新日志。包含：版本号、更新类型、修复项、升级说明。 | R-24 |
| `references/examples.md` | 使用示例 | 各场景完整执行示例。包含：CLI 命令、执行过程、输出结果。 | R-25 C-17 |
| `references/execution_standards.md` | 参考文档 | / 层级 / 上限 / 说明 / | 无 |
| `references/faq.md` | 常见问题 | 常见疑问与解答。包含：问题分类、原因分析、解决方案。 | R-19, R-25 C-19 |
| `references/hooks.md` | 参考文档 | 门禁状态查看：`python novel_pipeline_gate.py status <state_path>` | 无 |
| `references/permissions.md` | 权限与测试 | 权限扫描说明与测试结论。包含：风险等级、高权限操作说明、测试概览、计时统计。 | R-15, R-16 |

| 能力 | 说明 | 限制 |
| ------ |------| ------ |
| **初始化小说项目** | 创建novel_state.json骨架，支持短篇/中篇/长篇 | 仅生成JSON骨架，不自动填充剧情内容 |
| **章节子结构规划** | 为每章注册3-5个子结构，配置标题/概述/情绪基调 | 概述需≥12有效字符；规划字段写入后MD5锁定不可更改 |
| **子结构原子写入** | 逐子结构写入正文，自动校验格式/字数/署名/行号 | 每子结构≤200行；正文禁止L##S##标记行 |
| **因果链验证** | 章级和子结构级双模式因果递进验证 | 仅检查关键词重叠和因果递进，无法验证剧情合理性 |
| **四合一章节完结检查** | 章内连通性+跨章承诺链+风格校验+逻辑检查 | HARD问题阻断并生成_fixes.json，需人工修复 |
| **全文收束验证** | 大纲忠实度报告+结尾封闭式/开放式/悬停式验证 | 仅验证末章末子结构，之前的章节需独立检查 |

**不支持：**
- 生成AI绘画/Mermaid/UML图表：novel-weaver仅处理文本和JSON
- 跨会话自动续写：不主动保存会话状态，需用户手动通过novel_state.json恢复
- 多语言翻译：仅支持中文写作，不提供翻译功能
- 自动纠错：不检查拼写/语法错误，仅校验结构和逻辑

**环境要求：**
- **Python** 3.8+，依赖标准库（json/pathlib/hashlib/sys）
- **网络**：完全离线运行，不依赖任何外部API
- **输入**：novel_state.json 文件和 stdin 文本输入
- **输出**：TXT 章节文件和 JSON 状态文件
- **编码**：所有文件使用 UTF-8 编码


| 能力 | 说明 | 限制 |
|------|------|------|
| **初始化小说项目** | 创建novel_state.json骨架，支持短篇/中篇/长篇 | 仅生成JSON骨架，不自动填充剧情内容 |
| **章节子结构规划** | 为每章注册3-5个子结构，配置标题/概述/情绪基调 | 概述需≥12有效字符；规划字段写入后MD5锁定不可更改 |
| **子结构原子写入** | 逐子结构写入正文，自动校验格式/字数/署名/行号 | 每子结构≤200行；正文禁止L##S##标记行 |
| **因果链验证** | 章级和子结构级双模式因果递进验证 | 仅检查关键词重叠和因果递进，无法验证剧情合理性 |
| **四合一章节完结检查** | 章内连通性+跨章承诺链+风格校验+逻辑检查 | HARD问题阻断并生成_fixes.json，需人工修复 |
| **全文收束验证** | 大纲忠实度报告+结尾封闭式/开放式/悬停式验证 | 仅验证末章末子结构，之前的章节需独立检查 |

**不支持：**
- 生成AI绘画/Mermaid/UML图表：novel-weaver仅处理文本和JSON
- 跨会话自动续写：不主动保存会话状态，需用户手动通过novel_state.json恢复
- 多语言翻译：仅支持中文写作，不提供翻译功能
- 自动纠错：不检查拼写/语法错误，仅校验结构和逻辑

## 工作流程

1. **LLM生成场景配置** → 输入 用户模糊想法 → 输出 novel_info/setting — 生成人物/时代/地点/风土人情/核心冲突
2. **LLM生成一级大纲** → 输入 场景配置 → 输出 chapters[] title/overview — L01-L15编号+标题+每章概述
3. **因果链验证(outline)** → 输入 chapters[] overview → 输出 outline_causality门禁 — 逐链节检查L01→L02→...因果递进
4. **用户确认** → 输入 大纲 → 输出 确认/修正 — 钩子阻断式，未确认不得进入阶段2
5. **初始化novel_state.json** → 输入 大纲 → 输出 novel_state.json — chapters/characters/timeline骨架
6. **规划章子结构** → 输入 章节标题+概述 → 输出 sub_structures[] — S01-S05+标题+概述+tone+可选emotions
7. **注册子结构到state** → 输入 subs_json → 输出 novel_state更新 — MD5指纹锁定+标记is_ending/is_hook
8. **子结构因果链验证** → 输入 sub_structures → 输出 sub_causality门禁 — 逐子结构因果递进检查
9. **set-phase writing** → 输入 outline+sub门禁 → 输出 phase=writing — require双门禁，不通过则阻断
10. **加载命题指令** → 输入 chapter+sub_key → 输出 context_loader输出 — 子结构规划+情绪混合+人格+文风约束
11. **LLM写作+管道写入** → 输入 命题指令 → 输出 S##.txt — atomic_writer代码级校验格式/字数/署名
12. **重复10-11** → 输入 下一子结构 → 输出 全部子结构完成 — 直到该章全部子结构写完
13. **完结一章(finalize-chapter)** → 输入 章内容 → 输出 四合一检查报告 — 章内连通性→跨章→风格→逻辑
14. **全文整合(fidelity)** → 输入 全部章节 → 输出 大纲忠实度报告 — 检查是否偏离大纲
15. **结尾收束验证** → 输入 末章末子结构 → 输出 ending_report.md — 封闭式/开放式/悬停式三选一验证
