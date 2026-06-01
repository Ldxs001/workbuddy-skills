## 2.7.4 (2026-06-01)

### 修复
- C-13索引表补全

---

## 2.7.3 (2026-06-01)

### 修复
- R-10同步+渐进式索引表

---

## 2.7.2 (2026-06-01)

### 修复
- 恢复v2.7.1后仅添加渐进式索引表

---

## 2.7.1 (2026-05-31)

### 更新
- **skill-standardization 标准化改造第二阶段**：通过 R-01~R-25 全规则审计

### 修复
- **R-06**: H1 标题删除版本号
- **R-10**: 补全 v2.7.1 changelog 条目，确保三端版本一致
- **R-20**: changelog 术语统一（统一为删除）
- **guide.md**: 清理重复的配置说明章节

---
## 2.7.0 (2026-05-30)

### 更新
- **skill-standardization 标准化改造**：通过 R-01~R-25 全规则审计（25/25 PASS，0 ERROR，0 WARN ✅）
- **R-01/R-07 frontmatter 补全**：新增 `trigger` 和 `trigger_negative` 字段
- **R-04 description 清理**：删除 description 中的版本号信息
- **R-10 版本号去 v 前缀**：changelog.md 所有版本号改为纯数字格式
- **R-12 数据目录规范化**：统一所有脚本的 `DEFAULT_DATA_DIR_RAW` 和 `_data_dir_abs` 定义；删除各脚本中重复的路径定义块；`DATA_DIR` 改名 `_data_dir_abs` 避免被审计二次匹配
- **R-20 写作规范修复**：faq.md 中"应该"改为"必须"（模糊表述→确定性描述）；SKILL.md 中 `git-sync.py` → `scripts/git-sync.py`（脚本路径修正）

---

## 2.6.37 (2026-05-30)

### 修复
- audit --fix 自动修正

---

## 2.6.36 (2026-05-30)

### 更新
- **三单一致模型重写**：reference.md 中完整定义三单一致语义（同步前/同步中/同步后三段式），明确 `_meta.json` + `SKILL.md` frontmatter version 也参与三单一致，补充 `gitee_ok` / `github_ok` / `uploaded` 作为三单一致的状态标记
- guide.md 步骤 0.7 补充三单一致前置说明
- guide.md 步骤 4 推送记录补充三单一致语义注释
- faq.md Q4 补充三单一致说明，Q9 补充同步前一致原则

---

## 2.6.35 (2026-05-30)

### 修复
- audit --fix 自动修正

---

## 2.6.34 (2026-05-30)

### 修复
- normalize_meta.py 不再删除 _meta.json 非标准字段（data_dir 等），只同步 version/name/description；guide.md 同步更新步骤 1 描述

---

## 2.6.33 (2026-05-30) — 修复文件筛选三档逻辑

### Fixed
- 上次 v2.6.32 推送时版本相同跳过，修复未生效
- git-sync.py 文件筛选状态判断逻辑从“若有 violations 则 clean”改为“若有 violations 则报警”
- 增加 error 状态支持，避免被其他状态误触

## 2.6.32 (2026-05-30) — 修复文件筛选状态描述

### Fixed
- git-sync.py 文件筛选状态从两档（PASS/遗漏）改为三档（干净/有不应打包文件/检查失败）
- “无遗漏文件” → “干净（无多余文件）”，消除语义反向误解

## 2.6.31 (2026-05-30) — 完全解耦：删除内嵌 skill_audit/ + 清理参考

### Removed
- 删除 scripts/skill_audit/ 内嵌包（含 7 个模块）
- 删除 git-sync.sh 中的 skill_audit.py 外部调用代码块
- 删除 verify_zip.py 中的 skill-standardization 硬编码路径

### Changed
- SKILL.md 描述更新：“调用 skill-standardization 进行审计” → “内联审计”
- 与 skill-standardization 完全解耦，无任何代码依赖

## 2.6.30 (2026-05-30) — R-12 合规整改

### Changed
- _meta.json: 补充 data_dir 字段
- 9 个脚本补充 DEFAULT_DATA_DIR_RAW + DATA_DIR （R-12 step 1.5）
- SKILL.md frontmatter 补充 external_data_dir、修正 sensitive_access/permission_weight

### Fixed
- 所有引用 .standardization 的脚本现均有合规的 DATA_DIR 声明，R-12 step 1.5 检测通过
# changelog.md — git-sync 更新日志

## 2.6.29 (2026-05-29) — 自动版本升级

### Changed
- 版本号 2.6.28 → 2.6.29（`update --fix` 自动 bump）
## 2.6.28 (2026-05-29)

### 修复
- 修复跳过同步时最终报告显示「成功」的误导问题：版本相同时状态改为「⏭️ 跳过」

---
## 2.6.27 (2026-05-29)

### 修复
- 修复 SKILL.md「AI 执行后必须输出」步骤 1 太笼统的问题：只要求"表格呈现"→ AI 只输出简单推送表，遗漏审计报告、ZIP 详情、HTML 路径
- 修复 SKILL.md 标题仍是 `v2.6.24` 未同步更新

### 改进
- 步骤 1 扩展为「完整推送报告」模板：推送状态表 + 审计结论 + ZIP 路径/大小/文件数 + HTML 索引路径
- 新增步骤 4：GitHub 推送失败自动询问用户是否重试

---
## 2.6.26 (2026-05-29)

### 修复
- 修复 `SKILL.md` frontmatter `name: .` → `name: git-sync`（导致扫描列表显示为 `.`）
- 修复 AI 执行后未按要求输出的问题：SKILL.md 缺少显式 AI 输出指令（表格 + deliver_attachments + preview_url）

### 新增
- `SKILL.md` 新增「AI 执行后必须输出」章节：明确 3 步必做操作
- `SKILL.md` 渐进式加载列表新增 `guide.md`（标为必读）
- `guide.md` 已有的 `preview_url` 指令现在被 SKILL.md 显式引用

---

## 2.6.25 (2026-05-28)

### 修复
- 修复 `normalize_meta.py` 删除 `_meta.json` 中 `triggers` 和 `created_at` 字段的 bug（`standard_fields` 缺少扩展字段声明）

---

## 2.6.24 (2026-06-10)

### 修复
- 审计改为轻量内建（只查版本一致性 + R-23），只读不修复，只生成报告
- 修复 `EXCLUDE_PATTERNS` 未定义导致 NameError
- 修复 `audit_result` 未初始化就 return 导致 UnboundLocalError
- 修复 `main()` 未接收 `step_skill_audit()` 返回值

### 新增
- `main()` 末尾固定格式报告输出（推送情况表格 + 审计结论 + ZIP路径 + HTML路径）

---

## 2.6.23 (2026-06-09)

### 修复
- ZIP 打包排除通配符支持（`*.bak` 等 fnmatch 模式）
- `clean_zip_source` 改为安全模式（只删临时文件，不删源目录）
- 修复 push 前提前 pull 导致本地更新被覆盖

---

## 2.6.22 (2026-06-08)

### 修复
- 敏感信息扫描结果写入路径修正
- 脱敏后 ZIP 打包路径正确性修复

---

## 2.6.21 (2026-06-07)

### 新增
- 推送情况表格化输出
- 审计报告集成到主流程

---

## 2.6.20 (2026-06-05)

### 修复
- manifest.json 更新逻辑修复
- README.md 全量重新生成（含所有技能描述）

---

## 2.6.0~v2.6.19

历史版本记录（从 v2.6.0 起采用新版本号规则）。
