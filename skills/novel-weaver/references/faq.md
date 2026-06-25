# FAQ / 常见问题

## 一、参数错误

### Q: 运行脚本时报 "用法: ..." 错误

**原因：** 命令行参数数量或顺序不对。

**修复：** 查阅脚本的 docstring 或用 `--help` 查看正确用法。
```bash
python novel_workflow_engine.py --help
python novel_state_manager.py --help
```

### Q: `plan-chapter` 报 "subs_json 格式错误"

**原因：** 传入的 JSON 字符串格式不正确（少引号、多逗号等）。

**修复：**
- 确保 JSON 是合法的数组格式：`[{"s_key":"S01",...}]`
- Windows 下注意转义双引号或使用单引号包裹整个 JSON
- 先验证 JSON 格式：`echo '<json>' | python -m json.tool`

### Q: `context_loader` 报 "子结构未注册"

**原因：** 尝试加载的子结构尚未通过 `plan-chapter` 注册到 `novel_state.json`。

**修复：**
```bash
python novel_workflow_engine.py plan-chapter <state_path> <L##> '<subs_json>'
```
然后重新运行 context_loader。

## 二、依赖错误

### Q: 运行脚本时报 "ModuleNotFoundError"

**原因：** 缺少 Python 依赖模块。

**修复：** 本技能所有脚本仅依赖 Python 标准库（json/os/sys/re/subprocess），不需要 pip install。

### Q: context_loader 报 "子结构已完成，禁止重复写作"

**原因：** 尝试加载一个已经写完（status=done）的子结构。

**修复：** 用 next-step 命令查找下一个待写的子结构：
```bash
python novel_workflow_engine.py next-step <state_path>
```

### Q: 提示 "novel_state.json not found"

**原因：** 数据目录未初始化或路径不对。

**修复：** 确保 `<state_path>` 指向正确的路径：
```
<skill_install_dir>/.standardization/novel-weaver/data/novel_state.json
```

## 三、环境错误

### Q: Windows 下运行报编码错误（gbk 相关）

**原因：** Python 默认编码与 UTF-8 文件不兼容。

**修复：**
```bash
set PYTHONUTF8=1
```

### Q: 子结构写入时断电，文件会丢吗？

**不会。** `novel_atomic_writer.py` 每写入一行就调用 `os.fsync()`，确保数据落盘。
```bash
# 写入完成后自动追加编号标记，可通过文件内容恢复进度
cat <chapter_dir>/<sub_key>.txt | wc -l
```

## 四、流程异常

### Q: `set-phase` 报 "拒绝推进"

**原因：** pipeline 门禁检查未通过，前置步骤尚未完成。

**修复：**
```bash
# 查看当前门禁状态
python novel_pipeline_gate.py status <state_path>
# 确认缺失的门禁后按顺序完成
# fidelity → ending_verify → complete
```

### Q: 写作时 context_loader 输出了 "未知" 标题

**原因：** 子结构未通过 `plan-chapter` 注册。此情况已改为报错退出。

**修复：** 先运行 `verify-chapter` 确认所有子结构已注册。

### Q: 想知道当前写作进度

```bash
python novel_workflow_engine.py next-step <state_path>
```
