# FAQ / 常见问题

Q: 写子结构时突然断电，文件会丢吗？
A: 不会。novel_atomic_writer.py 每写入一行后立即 os.fsync()，并在 .progress 文件中记录已写入行数。重启后用 progress 命令查询即可确认进度。

Q: 某章写完后发现和上一章的人物对不上了，怎么修复？
A: 使用"可选精修"模式。执行备份 → 定位到目标章节 → 用 novel_character_registry.py 更新角色属性 → 重新运行该章的风格一致性校验和连通性补充。

Q: 可以边写边改大纲吗？
A: 可以。在 novel_state.json 中更新对应章节的 summary 字段，然后按"可选精修"模式重新生成受影响的子结构。已完成的章节不受影响。

Q: stage 门禁报错了怎么办？
A: 用 `novel_state_manager.py get-phase <path>` 查看当前 phase，确认是否低于命令要求的门限。按顺序推进：init → stage1_done → writing → chapter_done → stage3_ready → complete。阶段不可回退。

Q: novel_state.json 和实际写作内容不一致怎么办？
A: 先运行 `novel_fidelity.py <project_dir>` 查看偏差报告，再用 `novel_state_manager.py update-sub <path> <L##S##> word_count=<实际字数> status=done` 同步状态。
