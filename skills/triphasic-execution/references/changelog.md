# triphasic-execution 版本更新日志

---

## v5.15.0（2026-05-25）

**改写类型：Bug 修复 — R-20 术语不一致 + 中英文混排 + 拼写错误**

### 更新内容

- ✅ 修复 R-20 术语不一致（"设置" → "配置"、"修改" → "更新"）
- ✅ 修复 R-20 中英文混排缺少空格（"Bug" → "Bug "、"Token" → "Token " 等）
- ✅ 修复拼写错误（`tAsk_progress.py` → `task_progress.py`）
- ✅ 修复 `## 核心能力` 章节渐进式加载说明（通过 R-21 检查）
- ✅ 修复触发条件否定条件（添加单步任务不触发的说明）
- 📦 更新 `_meta.json` 和 `SKILL.md` 版本号至 v5.15.0

### 影响

- triphasic-execution 审计 21/21 PASS（0 ERROR）
- R-20 写作规范全面符合
- 渐进式加载说明显式化

---

## v5.14.0（2026-05-24）

**改写类型：skill-standardization refactor 正确改造**

### 更新内容
- ✅ 使用 `refactor` 模式正确改造（先 `--dry-run` 再实际执行）
- ✅ 自动备份：`triphasic-execution_bak_refactor_20260524_230726`
- ✅ 调用 `permission_checker.py` 扫描脚本权限（8 文件 / 3219 行）
- ✅ 权限扫描结果：风险等级 MEDIUM，权重 50%，28 个问题（27 HIGH + 1 MEDIUM）
- ✅ 生成 `references/permission.md`（基于扫描报告，非手写）
- ✅ 生成 `references/permission_report.json`（机器可读）

### 权限扫描摘要
| 权限类型 | 次数 |
|---------|------|
| `subprocess_call` | 21 |
| `file_delete` | 6 |
| `network_access` | 1 |
| `sensitive_access` | 0 |
| `critical_write` | 0 |

### 标准化审查结果
- ERROR=0, WARN=0, PASS=16（全规则通过）

---

## v5.10.1（2026-05-23）

**改写类型：skill-standardization 标准化审查**

### 更新内容
- 标准化审查通过，无需更新（R-01~R-11 全部合规）

### 标准化审查结果
- ERROR=0, WARN=0, PASS=5

---

## 版本历史

> 详细版本历史参见 git 提交记录。
> 标准化审查前的版本信息由 SKILL.md frontmatter `version` 和 git tag 追溯。
