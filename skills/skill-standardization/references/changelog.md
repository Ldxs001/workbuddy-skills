# Changelog — skill-standardization

## v2.38.7 (2026-05-28)

### Fixed
- `scripts/skill_audit/structure_checker.py`：修复 R-23 多行代码块误判 bug（`relevant_cmds` 混进整个 bash 代码块，导致 A 脚本的参数被误判给 B 脚本）；改为按行拆分，只保留真正调用该脚本的命令行
- `scripts/skill_builder/creator.py`：修复 `SKILL_TEMPLATE.format()` 调用传入不存在的 `title=`/`tags=` 参数导致 `KeyError` 的问题
- `scripts/skill_audit/structure_checker.py`：修复报错信息输出绝对路径误导模型的问题，改为提示相对路径
- `scripts/skill_audit/__init__.py`：`format_report()` 末尾添加固定 `--fix` 提示，避免模型不知道有自动修复功能而手写临时脚本

### Changed
- 版本号 `v2.38.6` → `v2.38.7`
