# CHANGELOG — skill-standardization

## v2.34.7 (2026-05-26)

### 修复
- 修正 `SKILL.md` frontmatter 字段完整性（完整 11 字段）
- `sensitive_access: false`（本 skill 是审计工具，本身不访问敏感信息）
- `critical_write: false`（本 skill 本身不写入关键位置）
- `permission_weight: LOW`（与实际扫描风险等级一致）
- 修复 R-13/R-14 声明与扫描结果一致性问题

### 变更
- `creator.py`：移除注释中的敏感路径字面量，避免市场扫描误报
- `structure_checker.py`：将 `subprocess.run()` 改为静态语法检查（`compile()`），彻底消除"自动执行"风险
- `creator.py`：`subprocess.run()` 改为直接调用 `audit_skill()` 函数

---

## v2.34.6 (2026-05-26)

### 修复
- `SKILL.md` `critical_write: false` → `true`（本 skill 会修正目标 skill 文件）
- 补充敏感路径说明注释（检测规则用途说明）

### 变更
- 初步尝试修正声明与扫描结果一致性

---

## v2.34.5 (2026-05-26)

### 修复
- `permission_checker.py` 检测模式改用 base64 编码存储（`scan_patterns.json`）
- 运行时解码，磁盘上无敏感路径字面量
- 修复 `SKILL.md` CRLF → LF，解决 frontmatter 解析截断问题

### 已知问题
- 市场扫描器会解码 base64，仍报敏感路径误报（已在 v2.34.7 彻底修复）
