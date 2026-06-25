# 钩子系统

## 流程门禁系统

门禁状态查看：`python novel_pipeline_gate.py status <state_path>`

| 钩子 | 触发时机 | 类型 | 行为 | 脚本 |
|------|---------|------|------|------|
| 大纲确认 | 阶段1完成时 | 阻断式 | 未确认则禁止进入阶段2 | — |
| **大纲因果链验证** | 用户确认大纲前 | **阻断式** | novel_causality_check.py outline — 验证每章概述因果递进 | `scripts/novel_causality_check.py` |
| 子结构先行规划 | 每章写作前 | **代码级硬约束** | novel_workflow_engine.py plan-chapter 批量注册子结构 | `scripts/novel_workflow_engine.py` |
| **子结构因果链验证** | plan-chapter 后 | **阻断式** | novel_causality_check.py sub-structure — 验证子结构因果递进 | `scripts/novel_causality_check.py` |
| 子结构存在性验证 | 每段写作前 | **代码级硬约束** | novel_context_loader.py 读 sub_structures，未注册则报错退出 | `scripts/novel_context_loader.py` |
| 写作前加载上下文 | 写作前 | 阻断式+阶段约束 | novel_context_loader.py 输出命题指令框 | `scripts/novel_context_loader.py` |
| 写后即存 | 每段写作完成后 | 阻断式+原子写入 | novel_atomic_writer.py 格式校验 + fsync + 编号标记 | `scripts/novel_atomic_writer.py` |
| 署名检测 | 每段写入时 | **代码级硬阻断** | atomic_writer 检测"由...撰写"等8种署名模式；signature=off 时阻断 | `scripts/novel_atomic_writer.py` |
| 更新进度 | 每个子结构完成后 | 阻断式 | novel_state_manager.py update-sub | `scripts/novel_state_manager.py` |
| 角色登记 | 新角色出场时 | 阻断式 | novel_state_manager.py add-char | `scripts/novel_state_manager.py` |
| 时间线记录 | 每章完成后 | 阻断式 | novel_timeline.py add | `scripts/novel_timeline.py` |
| 章内连通性检查 | finalize-chapter 时 | **软性（不阻断）** | novel_continuity.py check — 子结构间时间/角色断链检测 | `scripts/novel_continuity.py` |
| 跨章承诺链检查 | finalize-chapter 时 | **软性（不阻断）** | novel_continuity.py cross-chapter — 关键词续接检测 | `scripts/novel_continuity.py` |
| 风格校验 | finalize-chapter 时 | **HARD（阻断）** | novel_style_check.py — 禁用词/末行编号/超200行阻断 | `scripts/novel_style_check.py` |
| 逻辑检查 | finalize-chapter 时 | **HARD（阻断）** | novel_logic_check.py — 人物/时间线/概述匹配度，命中<30%阻断 | `scripts/novel_logic_check.py` |
| **一键完结章节（阻断循环）** | 子结构全部完成后 | **编排式+HARD阻断** | finalize-chapter：聚合上述检查→有HARD问题写入`_fixes.json`并阻断，不标记门禁；全部通过才pass `chapter_finalized:L##` | `scripts/novel_workflow_engine.py` |
| 大纲忠实度报告 | 全文完成后 | 自动式+阶段门禁 | novel_fidelity.py generate-report（需≥stage3_ready）→ pass fidelity 门禁 | `scripts/novel_fidelity.py` |
| 结尾收束验证 | 全文完成后 | **阻断式+门禁** | novel_fidelity.py verify-ending — 封闭/开放/悬停类型专项检查 | `scripts/novel_fidelity.py` |

## 门禁点列表（有序、不可逆）

| 门禁 | 在读什么 | 由谁 pass | 被谁 require | 阻断后果 |
|------|---------|-----------|-------------|---------|
| `outline_causality` | 章概述因果链 | 手动（代码未自动标记） | set-phase → writing | LLM 无法开始写作 |
| `sub_causality:L##` | 子结构因果链 | 手动（代码未自动标记） | — | 间接阻断 |
| `chapter_finalized:L##` | 章完结检查 | finalize-chapter（HARD全过时） | — | 不阻断 phase，只标记完成 |
| `fidelity` | 大纲忠实度 | novel_fidelity.py generate-report | set-phase → stage3_ready | LLM 无法推进到完结阶段 |
| `ending_verify` | 结尾收束验证 | novel_fidelity.py verify-ending | set-phase → stage3_ready | LLM 无法推进到完结阶段 |

## 查看门禁状态

```bash
python novel_pipeline_gate.py status <state_path>
```

输出示例：
```
[门禁状态] 当前阶段: writing
  outline_causality    ⬜ PENDING
  sub_causality:L01    ⬜ PENDING
  chapter_finalized:L01 ⬜ PENDING
  fidelity             ⬜ PENDING
  ending_verify        ⬜ PENDING
```
