# 更新日志

## [1.1.1] - 2026-06-08

### 修复
- SKILL.md 完整示例中 `calc_lod_loq` 参数签名对齐实际代码（`curve` → `calibration_data=curve`，`method="pharmacopoeia"` → `standard="gbt27417"`）
- 统一示例导入路径 `analysis_toolkit.scenarios` → `scripts.scenarios`
- `references/regression-validation.md` 输出表 key 名 `r²` → `r2` 对齐代码

## [1.1.0] - 2026-06-08

### 新增
- 新增 `scripts/output/` 标准化输出模块：markdown 表格 / HTML 报告 / 强制输出钩子
- 所有 14 个场景函数接入 `publish()`，计算后强制输出 markdown 表格
- 5 个可视化函数生成自包含 HTML 报告（质控图 / Youden 图 / 标准曲线 / 监控看板 / Prophet 预测）
- HTML 产出物存入数据目录 `.standardization/analysis-toolkit/data/reports/`

### 变更
- `scripts/report/` → `scripts/docgen/`（规避产出物路径误判）
- SKILL.md 遵循 skill-standardization R-01~R-25 规范（24/25 PASS）
- 数据目录迁移至 `.standardization/analysis-toolkit/`
- 创建 `references/antipatterns.md`、`references/faq.md`、`references/permissions.md`

### 修复
- Prophet 预测在 Windows 中文环境下编码问题（PYTHONUTF8=0）
- `forecast_alert` 返回类型错误（tuple 解包）
