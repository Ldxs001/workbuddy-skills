
## v1.6.0（2026-05-30）

### 修复
- R-12 数据目录路径合规修复（`scripts/workday_calendar.py` 新增 `DEFAULT_DATA_DIR_RAW` 审计锚点 + `_data_dir_abs` 运行时路径）
- `_meta.json` 补充 `data_dir` 字段（与 SKILL.md frontmatter 保持一致）
- `get_skill_data_dir()` 改用 `_data_dir_abs` 静态路径替代动态目录遍历

### 更新
- SKILL.md frontmatter 版本号升至 v1.6.0，描述更新
- `_meta.json` 版本号和描述同步更新
- `references/changelog.md` 补写 v1.6.0 改动记录

---

## v1.5.0（2026-05-27）

### 修复
- 经 skill-standardization 改造，文件结构规范化（scripts/、references/ 归位）
- R-11 产出物路径合规性修复（移除根目录违规文件）
- R-12 数据目录路径统一（data_dir: ../.standardization/workday-calendar/data/）
- SKILL.md frontmatter 补充 trigger/trigger_negative 字段

### 更新
- SKILL.md frontmatter 版本号升至 v1.5.0
- _meta.json 版本号和描述更新
- references/changelog.md 补写 v1.4.0 遗漏的实际改动

---

## v1.4.0（2026-05-27）

### 修复
- 经 skill-standardization 改造，文件结构规范化（scripts/、references/ 归位）
- R-11 产出物路径合规性修复（移除根目录违规文件）
- R-12 数据目录路径统一（data_dir: ../.standardization/workday-calendar/data/）

### 更新
- SKILL.md frontmatter 版本号升至 v1.4.0
- _meta.json 版本号和描述更新

---

## v1.3.0（2026-05-27）

### 新增
- 国家法定假日区间管理
- 年度工作日计算
- 周历生成
- 日程管理

---
