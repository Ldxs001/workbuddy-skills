# 常见问题（FAQ）

---

**Q: 如何确保重复执行不会破坏文件？**

A: 所有写操作（create overwrite、update、delete、move、copy overwrite）执行前会自动备份原文件到 `skills/.standardization/universal-file-ops/data/backup/`，且脚本支持幂等执行（重复执行结果一致）。如果出错，可用 `python scripts/rollback.py --id <rollback_id>` 回滚。读操作（read）天然幂等，多次执行无副作用。

---

**Q: 可以并行执行多个文件操作吗？**

A: 可以。`scripts/orchestrator.py` 支持并行模式（`--parallel`），适合相互无依赖的批量任务。但同一文件路径的操作会串行排队（通过任务队列保证），避免读写冲突。如果任务间有依赖关系（如任务 2 读任务 1 写的文件），应使用默认串行模式（`--parallel` 不指定）。

---

**Q: `text_crud.py` 和 `office_crud.py` 应该如何选择？**

A: 根据文件格式判断：
- `.txt`, `.py`, `.html`, `.md`, `.csv`, `.json`, `.yaml`, `.xml`, `.css`, `.js`, `.ts` → 使用 `text_crud.py`（按文本读写）
- `.docx` → 使用 `office_crud.py`（需要 `python-docx` 依赖）
- `.xlsx` → 使用 `office_crud.py`（需要 `openpyxl` 依赖）

如果依赖缺失，`office_crud.py` 会返回明确的错误提示，引导安装对应包。

---

**Q: 批量操作失败时，如何快速定位是哪个任务出错？**

A: 有两种方式：
1. **看 orchestrator 返回的 JSON 数组**——每项对应一个任务，按 `success` 字段判断是否成功，`error` 字段包含错误详情。
2. **查看操作日志**——所有操作记录在 `skills/.standardization/universal-file-ops/data/logs/ops.log`，按时间戳和状态（OK/FAIL）过滤。

建议：批量执行前加 `--dry-run` 先验证配置正确性，再实际执行。

---

**Q: 我想在自己的项目里用类似的文件操作逻辑，可以直接改 `scripts/` 里的脚本吗？**

A: 不建议直接改原始脚本。正确做法是：将 `scripts/` 下的原始脚本作为参考基线，创建一个新的适配副本（如 `my_text_crud.py`），在副本中更新。这样原始脚本保持只读，你可以随时回滚到基线版本，也方便后续合并本技能的更新。

---

**Q: `data/backup/` 目录下的备份文件会一直累积吗？需要手动清理吗？**

A: 当前版本不会自动清理备份文件。如果备份较多占用空间，可以：
1. 手动删除 `data/backup/` 下不再需要的 `.bak` 文件
2. 通过 `python scripts/rollback.py --list` 查看所有备份及其对应的原始文件，按需删除

后续版本计划加入备份保留策略（如保留最近 N 天）。

---

**Q: 为什么 `office_crud.py` 的 update 操作是全文覆盖，而不是局部更新？**

A: 当前 v0.1.0 的 `office_crud.py` 采用简化实现（docx 清空所有段落再重写），主要是为了避免复杂的格式保留逻辑。如果你需要局部更新 docx 内容，建议：
1. 先用 `office_crud.py --action read` 读取全文
2. 在 LLM 中处理文本（插入/替换/删除段落）
3. 再用 `--action create` 全覆盖写入

后续版本计划支持基于段落索引的局部更新。
