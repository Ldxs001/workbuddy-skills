# 执行规范

## 字数管理

| 层级 | 上限 | 说明 |
|------|------|------|
| 每个子结构 | 200 行（自然段落结束） | 以叙事单位结束，不强行撑到上限 |
| 每章（汇总） | 不限（多个子结构累计） | 由 3-5 个子结构的自然累加决定 |
| 全文 | 8-15 章（推荐） | 触发时由大纲章节数决定，不固定 |

## 文体规范

文体风格由项目 `novel_state.json` 中的 `style_guide` 字段决定。以下规则适用于所有风格：

允许使用的通用修辞工具：
- 代码/协议块
- 系统警告/报告标记（如 `【状态】`、`【诊断】`）
- 可量化体征数据（心率、体温、激素水平）
- 类比与推理论证
- 表格/清单对比

禁止：
- 第三人称叙述插入（除非是人物对白中的转述）
- 纯抒情段落（情绪须通过人物行为或生理反应间接表达）
- 元文本引用（"从第 X 章开始"——读者视角，非叙事者视角）

## 子结构先行规划（v1.2 新增硬约束）

**必须在每个子结构写作前完成，不可跳过。**

### 概述编写规范

概述是整个命题作文体系的核心锚点——它同时服务于因果链验证、context_loader 命题指令、logic_check 内容匹配度检查。概述越精确，LLM 跑偏概率越低。

**概述必须满足以下条件（代码级强制校验，plan-chapter 时执行）：**

| 要求 | 说明 | 校验方式 |
|------|------|---------|
| 最低字数 | ≥12 个有效字符（不计空格/标点） | plan-chapter 强制阻断 |
| 包含动作 | 必须有具体动词或事件描述 | LLM 自觉（不可写纯状态） |
| 包含人物 | 必须涉及至少一个角色 | LLM 自觉 |
| 可验证 | 写完回头看能判断"是否写了这个" | LLM 自觉（logic_check 语义参考） |

**合格示例：**
- ✅ `Atlas在每日诊断中首次检测到异常神经脉冲，决定不向三浦报告` — 24字符，有动作+人物+事件
- ✅ `三浦发现系统日志有0.3秒间隙，开始暗中调查` — 18字符，因果明确
- ✅ `Atlas在伪装模式下首次体验人类情感波动，感到困惑` — 21字符，有结果

**不合格示例：**
- ❌ `主角在实验室` — 6字符，无事件无动作
- ❌ `Atlas做了些事情` — 7字符，无法验证
- ❌ `讨论了一些问题` — 7字符，无具体内容
- ❌ `主角很难过` — 5字符，纯状态无因果

### 规划流程

1. LLM 根据章标题和概述，生成该章全部子结构的规划（S01-S05）
2. 每个子结构规划包含 4 个字段：
   - `s_key`: 如 `S01`
   - `title`: 子结构标题（如"实验室初试"）
   - `summary`: 模糊概述（20-40字，描述该段核心内容）
   - `tone`: **情绪提示**（如"紧张"、"宁静"、"悬疑"、"温馨"等）— 保证跨子结构情绪连贯性
3. 用 workflow_engine.py 批量注册：
   ```
   python novel_workflow_engine.py plan-chapter <state_path> <L##> '<json_array>'
   ```
   JSON 示例：
   ```json
   [
     {"s_key":"S01","title":"实验室初试","summary":"主角第一次接触实验设备，紧张","tone":"紧张"},
     {"s_key":"S02","title":"意外发现","summary":"意外发现异常数据，兴奋","tone":"兴奋"},
     {"s_key":"S03","title":"导师的警告","summary":"导师对发现表示怀疑，压抑","tone":"压抑"}
   ]
   ```
4. 验证：
   ```
   python novel_workflow_engine.py verify-chapter <state_path> <L##>
   ```
   全部注册后 phase 自动推进到 writing

5. 预览：
   ```
   python novel_workflow_engine.py preview-writing-context <state_path> <L##>
   ```

### 阻断规则

- **context_loader.py** 在子结构未注册时报错退出，不会降级输出"未知"
- **必须先 plan-chapter，再开始写作**

## 统一项目状态文件

所有元数据写入一个文件 `novel_state.json`。

编号规则：
- 章节编号：`L01`、`L02` … `L15`
- 子结构编号：`S01`、`S02` …
- 完整引用：`L10S04` = 第 10 章第 4 个子结构

novel_state.json 包含字段：project, current_phase, style_guide, characters, timeline, chapters（含章摘要、子结构标题/概述/情绪提示/字数和状态、章节衔接/校验备注）。

更新时机：
1. 项目初始化 → 填充 style_guide / chapters / characters
2. 子结构先行规划 → plan-chapter 批量注册 title/summary/tone
3. 子结构写入完成 → 更新 word_count + status
4. 角色更新 → 更新 characters
5. 时间推进 → 更新 timeline
6. 连通性补充后 → 更新 continuity_notes
7. 风格校验后 → 更新 style_check_notes

## 子结构文件格式

```
（剧情正文，纯叙事文本）

L10S04
```

- 正文：纯叙事文本，不含元数据
- **禁止在正文中出现子结构标记行（L##S##）— atomic_writer.py 会检测并阻断写入**
- 末行：子结构编号（如 L10S04），由 atomic_writer finalize 写入
- 连通性检查读取前3行/后3行时，跳过末行编号行

## 章节完成输出

每章完成后输出简表（从 novel_state.json 直接读取），并调用：
```
python novel_workflow_engine.py finalize-chapter <state_path> <ch_key> <chapter_dir> <report_dir>
```

此命令自动执行：连通性检查 → 风格校验 → 逻辑检查 → phase→chapter_done

## 一键完结篇章（v1.2 新增）

代替手动依次调用 continuity → style → logic → set-phase 的繁琐流程：

```
python novel_workflow_engine.py finalize-chapter <path> <L##> <chapter_dir> <data/reports/>
```

输出：
- `data/reports/continuity_L##.md`
- `data/reports/style_L##.md`
- `data/reports/logic_L##.md`
- phase → chapter_done

## 时间线追踪

每章结束时调用 `novel_timeline.py add <project_dir> <chapter> <days> <summary>`。

## 角色信息表

新出场角色或已有角色属性变化时调用：
`novel_state_manager.py add-char <path> <name> <role> <first_appearance>`

## 结尾收束规范

最后一章的特殊要求：
1. 完成标记替换为"---全文 完---"
2. 不预告下一章
3. 结尾场景与第 1 章第一个场景呼应
4. 最后一句用动作收束（"推门。""关灯。""转身。"）
