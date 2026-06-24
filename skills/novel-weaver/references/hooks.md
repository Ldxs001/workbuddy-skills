# 钩子系统

| 钩子 | 触发时机 | 类型 | 行为 | 脚本 |
|------|---------|------|------|------|
| 大纲确认 | 阶段1完成时 | 阻断式 | 未确认则禁止进入阶段2 | — |
| 初始化状态文件 | 阶段1完成后 | 阻断式+阶段门禁 | novel_state_manager.py init → phase=init，禁止重复 | `scripts/novel_state_manager.py` |
| **大纲因果链验证** | 用户确认大纲前 | **阻断式钩子** | novel_causality_check.py chapter-outline 逐链节检查章概述因果递进，PASS 后才可确认（v1.2.1 新增） | `scripts/novel_causality_check.py` |
| 子结构先行规划 | 每章写作前 | **代码级硬约束** | workflow_engine.py plan-chapter 批量注册子结构（含情绪 tone）→ context_loader 要求子结构已存在 | `scripts/novel_workflow_engine.py` |
| **子结构因果链验证** | plan-chapter 后、写作前 | **阻断式钩子** | novel_causality_check.py sub-structure 检查 S01→S02→… 概述因果递进，PASS 后才可写作（v1.2.1 新增） | `scripts/novel_causality_check.py` |
| 子结构存在性验证 | 每段写作前 | **代码级硬约束** | novel_context_loader.py 读 sub_structures[s_key].title，为空则报错退出（v1.2 新增） | `scripts/novel_context_loader.py` |
| 写作前加载上下文 | 每段写作前 | 阻断式+阶段门禁 | novel_context_loader.py（需 phase≥stage1_done + 子结构已注册） | `scripts/novel_context_loader.py` |
| 写后即存 | 每段写作完成后 | 阻断式+原子 | novel_atomic_writer.py 按行 fsync + 正文禁止标记行检测（v1.2 新增） + finalize 编号标记 | `scripts/novel_atomic_writer.py` |
| 更新进度 | 每个子结构完成后 | 阻断式+阶段门禁 | novel_state_manager.py update-sub | `scripts/novel_state_manager.py` |
| 角色登记 | 新角色出场时 | 阻断式+阶段门禁 | novel_state_manager.py add-char | `scripts/novel_state_manager.py` |
| 时间线记录 | 每章完成后 | 阻断式+阶段门禁 | novel_timeline.py add（需 phase≥stage1_done） | `scripts/novel_timeline.py` |
| 连通性补充 | 子结构/章节完成后 | 阻断式+阶段门禁+auto-fix | novel_continuity.py generate（需 phase≥writing），--auto-fix 生成 `_transitions.json` | `scripts/novel_continuity.py` |
| 风格一致性校验 | 每章完成后 | 自动式+阶段门禁 | novel_style_check.py（需 phase≥writing） | `scripts/novel_style_check.py` |
| 逻辑一致性检查 | 每章完成后 | 自动式+阶段门禁 | novel_logic_check.py（人物行为/时间线/内容匹配度，v1.2 新增） | `scripts/novel_logic_check.py` |
| 一章完结 | 全部检查通过后 | 阻断式+前置条件检查 | set-phase chapter_done 前检查 continuity/style/logic 报告是否存在（v1.2 新增） | `scripts/novel_state_manager.py` |
| 一键完结章节 | 替代手动三步 | 编排式 | workflow_engine.py finalize-chapter 运行连通性+风格+逻辑+set-phase 全自动 | `scripts/novel_workflow_engine.py` |
| 大纲忠实度报告 | 全文完成后 | 自动式+阶段门禁 | novel_fidelity.py（需 phase≥stage3_ready，已修复 dict/list 兼容） | `scripts/novel_fidelity.py` |
