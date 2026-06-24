# FAQ / 常见问题

## 一、参数错误

### Q: 运行脚本时报 "用法: ..." 错误

**原因：** 命令行参数数量或顺序不对。

**修复：** 查阅脚本的 docstring 或用 `--help` 查看正确用法。
```bash
python novel_workflow_engine.py --help
python novel_state_manager.py --help  # 显示所有子命令
```

### Q: `plan-chapter` 报 "subs_json 格式错误"

**原因：** 传入的 JSON 字符串格式不正确（少引号、多逗号等）。

**修复：**
- 确保 JSON 是合法的数组格式：`[{"s_key":"S01",...}]`
- Windows 下注意转义双引号或使用单引号包裹整个 JSON
- 先验证 JSON 格式：`echo '<json>' | python -m json.tool`

### Q: `context_loader` 报 "子结构未注册"

**原因：** 尝试加载的子结构尚未通过 `plan-chapter` 或 `add-sub` 注册到 `novel_state.json`。

**修复：**
```bash
# 方式一：批量注册（推荐）
python novel_workflow_engine.py plan-chapter <state_path> <L##> '<subs_json>'
# 方式二：单个注册
python novel_state_manager.py add-sub <state_path> <L##> <S##> <title> <summary>
```
然后重新运行 context_loader。

## 二、依赖错误

### Q: 运行脚本时报 "ModuleNotFoundError"

**原因：** 缺少 Python 依赖模块。

**修复：** 本技能所有脚本仅依赖 Python 标准库（json/os/sys/re/subprocess），不需要 pip install。如果确实缺少某模块：
```bash
pip install <模块名>
```

### Q: context_loader 报 "子结构已完成，禁止重复写作"

**原因：** 尝试加载一个已经写完（status=done）的子结构。

**修复：** 用 resume 命令查找下一个待写的子结构：
```bash
python novel_workflow_engine.py resume <state_path>
```
系统会输出当前进度表，标明已完成/待写的子结构，并给出续写命令。

### Q: 提示 "novel_state.json not found"

**原因：** 项目未初始化或路径不对。

**修复：**
```bash
python novel_state_manager.py init <path> <project_name> '<style_json>' '<chapters_json>'
```

## 三、环境错误

### Q: Windows 下运行报编码错误（gbk 相关）

**原因：** Python 默认编码与 UTF-8 文件不兼容。

**修复：**
```bash
# 设置环境变量
set PYTHONUTF8=1
# 或使用 PowerShell
$env:PYTHONUTF8=1
```

### Q: 子结构写入时断电，文件会丢吗？

**不会。** `novel_atomic_writer.py` 每写入一行就调用 `os.fsync()`，确保数据落盘。恢复后：
```bash
python novel_atomic_writer.py progress <filepath>
# 返回已成功写入的行数
```
从断点继续写入即可。

## 四、流程异常

### Q: `set-phase` 报 "拒绝推进"

**原因：** pipeline 门禁检查未通过，前置步骤尚未完成。

**修复：**
```bash
# 查看当前门禁状态
python novel_pipeline_gate.py status <state_path>
# 确认缺失的门禁后按顺序完成：
# outline_causality → plan_chapter → sub_causality → chapter_finalized → fidelity
```

### Q: 写作时 context_loader 输出了 "未知" 标题

**原因：** 子结构未通过 `add-sub` 或 `plan-chapter` 注册。v1.2+ 此情况已改为报错退出（不再输出"未知"）。

**修复：** 先运行 `verify-chapter` 确认所有子结构已注册。

### Q: 想知道当前写作进度

```bash
python novel_pipeline_gate.py status <state_path>
python novel_state_manager.py get-phase <state_path>
```
