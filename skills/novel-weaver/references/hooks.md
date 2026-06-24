# 钩子系统

| 钩子 | 触发时机 | 类型 | 行为 | 脚本 |
|------|---------|------|------|------|
| 大纲确认 | 阶段1完成时 | 阻断式 | 未确认则禁止进入阶段2 | — |
| 初始化状态文件 | 阶段1完成后 | 阻断式+阶段门禁 | novel_state_manager.py init → phase=init，禁止重复 | `scripts/novel_state_manager.py` |
| 推进阶段 | 每步完成后 | 阻断式+阶段门禁 | novel_state_manager.py set-phase（不可回退） | `scripts/novel_state_manager.py` |
| 写作前加载上下文 | 每段写作前 | 阻断式+阶段门禁 | novel_context_loader.py（需 phase≥stage1_done） | `scripts/novel_context_loader.py` |
| 写后即存 | 每段写作完成后 | 阻断式+原子 | novel_atomic_writer.py 按行 fsync + finalize 编号标记 | `scripts/novel_atomic_writer.py` |
| 更新进度 | 每个子结构完成后 | 阻断式+阶段门禁 | novel_state_manager.py update-sub | `scripts/novel_state_manager.py` |
| 角色登记 | 新角色出场时 | 阻断式+阶段门禁 | novel_state_manager.py add-char | `scripts/novel_state_manager.py` |
| 时间线记录 | 每章完成后 | 阻断式+阶段门禁 | novel_timeline.py add（需 phase≥stage1_done） | `scripts/novel_timeline.py` |
| 连通性补充 | 子结构/章节完成后 | 阻断式+阶段门禁 | novel_continuity.py（需 phase≥writing） | `scripts/novel_continuity.py` |
| 风格一致性校验 | 每章完成后 | 自动式+阶段门禁 | novel_style_check.py（需 phase≥writing） | `scripts/novel_style_check.py` |
| 大纲忠实度报告 | 全文完成后 | 自动式+阶段门禁 | novel_fidelity.py（需 phase≥stage3_ready） | `scripts/novel_fidelity.py` |
