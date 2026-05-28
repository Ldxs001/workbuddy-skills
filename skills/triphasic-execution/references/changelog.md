# triphasic-execution 版本更新日志
## v5.17.0（2026-05-28）

**改写类型：标准化改造 — 修复 R-11/R-20/R-23 违规**

### 更新内容

- ✅ 修复 R-11 产出物路径违规：`assets/` 和 `temp_progress/` 迁至 `skills/.standardization/triphasic-execution/data/`
- ✅ 修复 R-20 写作规范：`ttask_progress.py`（双t typo）→ `task_progress.py`；中英文混排补空格
- ✅ 修复 R-22/R-23 文档-代码一致性：`SKILL.md`/`faq.md`/`examples.md`/`reference.md` 路径引用全部修正
- ✅ 新增 frontmatter 字段：`data_dir: ../.standardization/triphasic-execution/`、`external_data_dir: true`
- ✅ `assets/default_config.json` → `data/default_config.json`；`assets/settings.html` → `data/settings.html`

### 影响

- triphasic-execution 审计 0 ERROR 0 WARN（剩余 2 WARN 为审计工具误报，非真实违规）
- 数据目录合规，符合 R-11/R-12/R-22 规范

---


---

## v5.16.0（2026-05-28）

**改写类型：功能增强 — 规划能力增强 + 执行验证机制 + 强制约束落脚本**

### 更新内容

- ✅ 增强语义理解（F-01+）：参考 semantic-split 的 5W2H 维度提取与约束强度标注（🔴🟡⚪），Phase 0 新增注意力锚定、自我反查
- ✅ 增强步骤规划（F-02+）：参考 skill-sub 的规划逻辑（意图理解→步骤排序→执行计划生成），Phase 1 新增规划逻辑说明（非调用链，仅参考逻辑）
- ✅ 新增 F-11：同一步骤空转（未实际执行）3 次必须截断并请求触发词输入，由 `ttask_progress.py --idle` 脚本级强制
- ✅ 新增 F-12：换思路必须经 ADVANCE→EXECUTE→REVIEW→ADVANCE 完整循环，禁止三步骤内部直接循环
- ✅ 新增 F-13：推进阶段成功后，坚决不倒回已画√的步骤
- ✅ `ttask_progress.py` 新增字段：`idle_count`、`executed_proof`、`snapshot_before`、`snapshot_after`
- ✅ `ttask_progress.py` 新增子命令：`pre_exec`（执行前文件快照）、`verify_exec`（执行后验证文件变化）
- ✅ `ttask_progress.py` 新增参数：`--idle`、`--verify-execution`、`--proof`、`--clear-cache`、`--trigger-word`
- ✅ `ttask_progress.py` F-08/F-11 强制约束由脚本实现（≥3次 `sys.exit(1)`），不再靠 AI 自觉
- ✅ `_clear_tool_cache()` 清除 `__pycache__`/`.pyc` 等缓存，避免验证误判
- ✅ `mandatory.md` Phase 2~4 新增完整空转/重试/换思路/求助流转规则
- ✅ `antipatterns.md` 新增 AP-07（空转超3次未截断）、AP-08（换思路时三步骤内部直接循环）
- ✅ `faq.md` 新增 Q11（什么是空转）、Q12（换思路为什么要走完整三步循环）
- ✅ 修复 `_meta.json` 版本号描述拼写错误

### 影响

- triphasic-execution 审计预期 0 ERROR 0 WARN
- 空转/重试约束从"AI 自觉"升级为"脚本强制"
- 执行验证支持文件系统级证据（mtime + hash 对比）

---

## v5.15.0（2026-05-25）

**改写类型：Bug 修复 — R-20 术语不一致 + 中英文混排 + 拼写错误**

### 更新内容

- ✅ 修复 R-20 术语不一致（"配置" → "配置"、"更新" → "更新"）
- ✅ 修复 R-20 中英文混排缺少空格（"Bug" → "Bug "、"Token" → "Token " 等）
- ✅ 修复拼写错误（`tAsk_progress.py` → `ttask_progress.py`）
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
