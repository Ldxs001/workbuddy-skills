## v1.5.0（2026-05-27）

### 修复
- 补全 v1.4.0 变更日志——实际新增功能未在 changelog 中体现

### 新增
- `scripts/export_excel.py`：2026年排班表 Excel 导出脚本（带格式）
- `scripts/generate_schedule.py`：2026年排班表生成脚本（白班/晚班/接样人员轮转）
- `scripts/schedule_2026.html`：2026年排班表 HTML 可视化
- `scripts/schedule_2026.md`：2026年排班表 Markdown 格式
- `scripts/schedule_2026.xlsx`：2026年排班表 Excel 文件
- `scripts/workday_calendar.py`：核心模块增强（假日区间、补班日、周末规则、工作日计算）

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
