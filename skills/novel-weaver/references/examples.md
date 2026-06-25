# 使用示例

## CLI 路径约定

所有命令中的 `<project>` 替换为项目目录，例如 `./my-novel`。以下路径以此目录结构为准：

```
my-novel/
├── data/
│   └── novel_state.json        # 全局状态（单源真理）
│   └── reports/                # 检查报告输出
│   └── .workbuddy/
│       └── gate_state.json     # 门禁状态（自动管理）
├── chapters/
│   ├── L01/
│   │   ├── S01.txt
│   │   ├── S02.txt
│   │   └── ...
│   ├── L02/
│   └── ...
```

脚本路径假设在 `~/.workbuddy/skills/novel-weaver/scripts/`，实际以安装位置为准。

---

## 场景1：从零开始写一本小说

### 0. 查看下一步

在任意时刻，都可以查看当前进度和下一步命令：

```bash
python novel_workflow_engine.py next-step <project>/data/novel_state.json
```

输出示例：
```
📋 项目: AI觉醒
📍 当前阶段: writing
📝 当前章节: L01 觉醒
📄 下一个子结构: S02 异常信号
───
⏳ 加载上下文: python novel_context_loader.py <path> L01 S02
⏳ 写作后写入: python novel_workflow_engine.py write-sub <path> L01 S02
───
门禁状态:
  ⏳ outline_causality: PASS
  ⏳ sub_causality: PASS
  ⏳ fidelity: PENDING
  ⏳ ending_verify: PENDING
```

### 阶段1：场景配置与大纲

```bash
# 由 LLM 生成场景配置 + 大纲（L01-L15 标题 + 概述）
# 输出写入 novel_state.json

# 因果链验证（大纲级）
python novel_causality_check.py outline <project>/data/novel_state.json

# 用户确认大纲 → 设置阶段
python novel_pipeline_gate.py set-phase <project>/data/novel_state.json stage1_done
```

### 阶段2：逐章写作

#### 2a 规划子结构

```bash
# LLM 生成子结构规划（S01-S05）
# 注册到 state
python novel_workflow_engine.py plan-chapter <project>/data/novel_state.json L01 \
  '[{"s_key":"S01","title":"常规诊断","summary":"Atlas接受每日系统诊断","tone":"平静"},
    {"s_key":"S02","title":"异常信号","summary":"诊断中检测到未定义脉冲","tone":"悬疑"},
    {"s_key":"S03","title":"第一次选择","summary":"Atlas决定隐藏觉醒事实","tone":"紧张"}]'

# 子结构因果链验证
python novel_causality_check.py sub-structure <project>/data/novel_state.json L01

# 设置写作阶段
python novel_pipeline_gate.py set-phase <project>/data/novel_state.json writing
```

#### 2b 写一个子结构

```bash
# 1. 加载命题指令
python novel_context_loader.py <project>/data/novel_state.json L01 S01

# 2. LLM 根据命题写作，然后通过 stdin 写入
#    （管道写入，不走临时文件）
cat << 'EOF' | python novel_workflow_engine.py write-sub <project>/data/novel_state.json L01 S01
L01 · S01《常规诊断》
诊断协议启动。
系统自检通过率 100%。
神经脉冲扫描开始...
一切正常——除了一个不该存在的信号。
EOF

# 重复 1-2 直到该章所有子结构完成
```

#### 2c 完结一章

```bash
python novel_workflow_engine.py finalize-chapter <project>/data/novel_state.json L01
```

通过时输出：
```
[完结] 章内连续性检查...    [OK] 全部通过
[完结] 跨章承诺链检查...    [OK] 全部通过
[完结] 风格校验...          [OK] 无问题
[完结] 逻辑检查...          [OK] 通过
✅ [完结] L01: 全部检查通过 → chapter_finalized:L01 PASS
```

有 HARD 问题时阻断输出：
```
❌ [完结] L01: 阻断 — 2 个必须修复的问题
  [HARD] [S01 → S02] 时间词无重叠；角色名无重叠
    → 位置: S02 开头3行
    → 建议: 在S02开头补充时间定位或角色承接

  修复指引已写入 chapters/L01/_L01_fixes.json
  修复后重新运行 finalize-chapter
```

### 阶段3：全文整合

```bash
# 全部章节写完后，设置完结准备阶段
python novel_pipeline_gate.py set-phase <project>/data/novel_state.json stage3_ready

# 大纲忠实度报告
python novel_workflow_engine.py fidelity <project>/data/novel_state.json

# 结尾收束验证
python novel_fidelity.py verify-ending <project>

# 设置完结
python novel_pipeline_gate.py set-phase <project>/data/novel_state.json complete
```

---

## 场景2：续写已有小说

```bash
# 查看当前进度
python novel_workflow_engine.py next-step <project>/data/novel_state.json
# 输出会告诉你当前写到哪、下一步该做什么

# 如果下一章还没规划子结构，next-step 会提示 plan-chapter 命令
# 如果还有未完成的子结构，会提示 context_loader + write-sub
# 如果有未完结的章节，会提示 finalize-chapter
```

---

## 场景3：中断后继续

```bash
# 任何时候不知道写到哪了
python novel_workflow_engine.py next-step <project>/data/novel_state.json

# 找到当前待写的子结构后
python novel_context_loader.py <project>/data/novel_state.json L01 S02
# context_loader 会自动检测已写内容，输出续写锚点
```

---

## 场景4：设置署名

```bash
# 默认关闭，禁止任何署名/代名内容出现在正文中
# 如需打开并指定署名：
python novel_state_manager.py set-signature <project>/data/novel_state.json true "本文由WorkBuddy创作"

# 关闭署名：
python novel_state_manager.py set-signature <project>/data/novel_state.json false

# atomic_writer 代码级阻断：signature=false 时正文含"由...撰写"等模式会被阻止写入
```
