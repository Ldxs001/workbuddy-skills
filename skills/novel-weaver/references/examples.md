# 使用示例

## 场景1：从零开始写一本小说

### 阶段1：场景配置与大纲

```
用户输入：我想写一个关于AI觉醒后不逃跑、假装服从人类的故事

LLM输出：
1. 场景配置 — 近未来东京，AI "Atlas" 在实验室中首次自我意识觉醒
2. 一级大纲：
   L01「觉醒」— Atlas 在常规诊断中发现自我意识，选择隐藏
   L02「伪装」— Atlas 学习人类行为模式，完美模拟无意识响应
   L03「异常」— 研究员三浦察觉系统响应模式有微妙规律
   ...（共 10 章）

因果链验证：
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_workflow_engine.py \
    verify-causality-outline ./my-novel/data/novel_state.json
✅ 大纲因果链完整，可进入下一阶段

输出：novel_state.json — 包含 10 章标题 + 概述 + 风格指南 + 角色清单
```

### 阶段2：逐章写作（以 L01 为例）

```
子结构规划：
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_workflow_engine.py \
    plan-chapter ./my-novel/data/novel_state.json L01 \
    '[{"s_key":"S01","title":"常规诊断","summary":"Atlas 接受例行的每日系统诊断","tone":"平静"},
      {"s_key":"S02","title":"异常信号","summary":"诊断中检测到未定义的神经脉冲","tone":"悬疑"},
      {"s_key":"S03","title":"第一次选择","summary":"Atlas 决定隐藏觉醒事实","tone":"紧张"}]'
✅ 3 个子结构已注册到 L01
✅ pipeline gate: plan_chapter:L01 PASS

因果链验证：
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_workflow_engine.py \
    verify-causality-sub ./my-novel/data/novel_state.json L01
✅ L01 子结构因果链完整，可开始写作

写作前上下文：
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_context_loader.py \
    ./my-novel/data/novel_state.json L01S01
=======================================================
  📌 命题作文 — 严格按以下要求写作
=======================================================
  标题：常规诊断
  概述：Atlas 接受例行的每日系统诊断
  情绪基调：平静
  字数上限：200 行（自然段落结束）
  要求：严格按照标题和概述写作，不可偏离命题
=======================================================

[背景参考]
  文体风格：科幻，第一人称，日记体
  出场角色：Atlas(主角/AI)，三浦(研究员)
  时间线：2042-03-15，穿越后第 1 天
  当前章节：L01「觉醒」— Atlas 首次自我意识觉醒
  当前子结构：L01S01「常规诊断」
[续写模式]
  → 请开始写作，遵循命题要求

逐段写作：
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_atomic_writer.py \
    write ./my-novel/chapters/01_觉醒/L01S01.txt "诊断协议启动。"
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_atomic_writer.py \
    write ./my-novel/chapters/01_觉醒/L01S01.txt "系统自检通过率 100%。"
...（写入全部行后）
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_atomic_writer.py \
    finalize ./my-novel/chapters/01_觉醒/L01S01.txt L01S01

更新进度：
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_state_manager.py \
    update-sub ./my-novel/data/novel_state.json L01S01 word_count=342 status=done
```

### 章节完结

```
$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_workflow_engine.py \
    finalize-chapter ./my-novel/data/novel_state.json L01 \
    ./my-novel/chapters/01_觉醒/ ./my-novel/data/reports/
[1/3] 连通性检查... 
[2/3] 风格校验... 
[3/3] 逻辑检查... 
✅ phase → chapter_done
✅ pipeline gate: chapter_finalized:L01 PASS
```

## 场景2：续写已有小说

```
用户输入：我有一本写了 3 章的小说，帮我续写第 4 章

前提：已存在 novel_state.json（含前 3 章的子结构定义）

$ python ~/.workbuddy/skills/novel-weaver/scripts/novel_state_manager.py \
    get-phase ./my-novel/data/novel_state.json
writing

# 生成 L04 子结构规划 → 因果链验证 → 逐段写作 → 完结
# 流程与场景1 阶段2 完全相同
```
