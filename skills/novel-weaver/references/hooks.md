# 钩子系统

## 🚨 流程门禁系统（v1.3.0 新增）

每个钩子成功完成后自动调用 `pipeline_gate.py pass` 更新全局状态。`set-phase` 在 phase 转换前自动调用 `pipeline_gate.py require` 检查前置步骤是否全部完成。**未通过门禁检查的 phase 转换会被阻断。**

门禁状态查看：`python novel_pipeline_gate.py status <state_path>`

| 钩子 | 触发时机 | 类型 | 行为 | 脚本 |
|------|---------|------|------|------|
| 大纲确认 | 阶段1完成时 | 阻断式 | 未确认则禁止进入阶段2 | — |
| 初始化状态文件 | 阶段1完成后 | 阻断式+阶段门禁+**门禁** | novel_state_manager.py init → phase=init，禁止重复 | `scripts/novel_state_manager.py` |
| **大纲因果链验证** | 用户确认大纲前 | **阻断式钩子+门禁** | novel_causality_check.py chapter-outline → PASS 时自动 pass outline_causality 门禁 | `scripts/novel_causality_check.py` |
| 子结构先行规划 | 每章写作前 | **代码级硬约束+门禁** | novel_workflow_engine.py plan-chapter 批量注册后自动 pass plan_chapter:L## 门禁 | `scripts/novel_workflow_engine.py` |
| **子结构因果链验证** | plan-chapter 后、写作前 | **阻断式钩子+门禁** | novel_causality_check.py sub-structure → PASS 时自动 pass sub_causality:L## 门禁 | `scripts/novel_causality_check.py` |
| 子结构存在性验证 | 每段写作前 | **代码级硬约束** | novel_context_loader.py 读 sub_structures[s_key].title，为空则报错退出 | `scripts/novel_context_loader.py` |
| 写作前加载上下文 | 每段写作前 | 阻断式+阶段门禁 | novel_context_loader.py（需 phase≥stage1_done + 子结构已注册） | `scripts/novel_context_loader.py` |
| 写后即存 | 每段写作完成后 | 阻断式+原子 | novel_atomic_writer.py 按行 fsync + 正文禁止标记行检测 + finalize 编号标记 | `scripts/novel_atomic_writer.py` |
| 更新进度 | 每个子结构完成后 | 阻断式+阶段门禁 | novel_state_manager.py update-sub | `scripts/novel_state_manager.py` |
| 角色登记 | 新角色出场时 | 阻断式+阶段门禁 | novel_state_manager.py add-char | `scripts/novel_state_manager.py` |
| 时间线记录 | 每章完成后 | 阻断式+阶段门禁 | novel_timeline.py add（需 phase≥stage1_done） | `scripts/novel_timeline.py` |
| 连通性补充 | 子结构/章节完成后 | 阻断式+阶段门禁+auto-fix | novel_continuity.py generate（需 phase≥writing），--auto-fix 生成 `_transitions.json` | `scripts/novel_continuity.py` |
| 风格一致性校验 | 每章完成后 | 自动式+阶段门禁 | novel_style_check.py（需 phase≥writing） | `scripts/novel_style_check.py` |
| 逻辑一致性检查 | 每章完成后 | 自动式+阶段门禁+auto-fix | novel_logic_check.py（人物行为/时间线/内容匹配度） | `scripts/novel_logic_check.py` |
| 一键完结章节 | 全部检查后 | **编排式+门禁+HARD阻断循环** | novel_workflow_engine.py finalize-chapter → 章内连通性+跨章承诺链+风格+逻辑 → HARD阻断决策：有HARD问题则写入`_{chapter}_fixes.json`并阻断，不标记门禁；全部通过才pass `chapter_finalized:L##` | `scripts/novel_workflow_engine.py` |
| 大纲忠实度报告 | 全文完成后 | 自动式+阶段门禁+门禁 | novel_fidelity.py（需 phase≥stage3_ready）→ PASS 时自动 pass fidelity 门禁 | `scripts/novel_fidelity.py` |

## 门禁点列表（有序、不可逆）

| 门禁 | 在读什么 | 由谁 pass | 被谁 require | 阻断后果 |
|------|---------|-----------|-------------|---------|
| `outline_causality` | 章概述因果链 | novel_causality_check.py | set-phase → writing | LLM 无法开始写作 |
| `plan_chapter:L##` | 子结构注册状态 | novel_workflow_engine.py | — | 间接阻断（无子结构会触发 context_loader 报错） |
| `sub_causality:L##` | 子结构因果链 | novel_causality_check.py | — | 间接阻断（写作流程无此门禁会触发写作混乱） |
| `chapter_finalized:L##` | 章完结报告 | novel_workflow_engine.py | set-phase → stage3_ready | LLM 无法结束全书 |
| `fidelity` | 大纲忠实度 | novel_fidelity.py | set-phase → complete | LLM 无法完结项目 |

## 查看门禁状态

```bash
python novel_pipeline_gate.py status <state_path>
```

输出示例：
```
[门禁状态] 当前阶段: writing
  outline_causality    ✅ PASS
  plan_chapter:L01     ✅ PASS
  sub_causality:L01    ✅ PASS
  chapter_finalized:L01 ⬜ PENDING
  fidelity             ⬜ PENDING
```
