# changelog.md — git-sync 更新日志

## v2.6.29 (2026-05-29) — 自动版本升级

### Changed
- 版本号 2.6.28 → 2.6.29（`update --fix` 自动 bump）
## v2.6.28 (2026-05-29)

### 修复
- 修复跳过同步时最终报告显示「成功」的误导问题：版本相同时状态改为「⏭️ 跳过」

---
## v2.6.27 (2026-05-29)

### 修复
- 修复 SKILL.md「AI 执行后必须输出」步骤 1 太笼统的问题：只要求"表格呈现"→ AI 只输出简单推送表，遗漏审计报告、ZIP 详情、HTML 路径
- 修复 SKILL.md 标题仍是 `v2.6.24` 未同步更新

### 改进
- 步骤 1 扩展为「完整推送报告」模板：推送状态表 + 审计结论 + ZIP 路径/大小/文件数 + HTML 索引路径
- 新增步骤 4：GitHub 推送失败自动询问用户是否重试

---
## v2.6.26 (2026-05-29)

### 修复
- 修复 `SKILL.md` frontmatter `name: .` → `name: git-sync`（导致扫描列表显示为 `.`）
- 修复 AI 执行后未按要求输出的问题：SKILL.md 缺少显式 AI 输出指令（表格 + deliver_attachments + preview_url）

### 新增
- `SKILL.md` 新增「AI 执行后必须输出」章节：明确 3 步必做操作
- `SKILL.md` 渐进式加载列表新增 `guide.md`（标为必读）
- `guide.md` 已有的 `preview_url` 指令现在被 SKILL.md 显式引用

---

## v2.6.25 (2026-05-28)

### 修复
- 修复 `normalize_meta.py` 删除 `_meta.json` 中 `triggers` 和 `created_at` 字段的 bug（`standard_fields` 缺少扩展字段声明）

---

## v2.6.24 (2026-06-10)

### 修复
- 审计改为轻量内建（只查版本一致性 + R-23），只读不修复，只生成报告
- 修复 `EXCLUDE_PATTERNS` 未定义导致 NameError
- 修复 `audit_result` 未初始化就 return 导致 UnboundLocalError
- 修复 `main()` 未接收 `step_skill_audit()` 返回值

### 新增
- `main()` 末尾固定格式报告输出（推送情况表格 + 审计结论 + ZIP路径 + HTML路径）

---

## v2.6.23 (2026-06-09)

### 修复
- ZIP 打包排除通配符支持（`*.bak` 等 fnmatch 模式）
- `clean_zip_source` 改为安全模式（只删临时文件，不删源目录）
- 修复 push 前提前 pull 导致本地修改被覆盖

---

## v2.6.22 (2026-06-08)

### 修复
- 敏感信息扫描结果写入路径修正
- 脱敏后 ZIP 打包路径正确性修复

---

## v2.6.21 (2026-06-07)

### 新增
- 推送情况表格化输出
- 审计报告集成到主流程

---

## v2.6.20 (2026-06-05)

### 修复
- manifest.json 更新逻辑修复
- README.md 全量重新生成（含所有技能描述）

---

## v2.6.0~v2.6.19

历史版本记录（从 v2.6.0 起采用新版本号规则）。
