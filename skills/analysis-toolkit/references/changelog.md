## 1.3.1 (2026-06-08)

### 修复
- audit --fix 自动修正: artifact_paths, writing_standards

---

# 更新日志

## [1.3.0] - 2026-06-08

### 新增
- **标准注册表**（`scripts/standards/registry.py`）：Standard 数据模型 + 注册/注销/查询接口 + CLI，支持 LLM/智能体注册新标准
- **模板管理系统**（`scripts/standards/template_manager.py`）：Template CRUD（创建/更新/删除/查询/应用）+ CLI
- **标准搜索链**（`scripts/standards/searcher.py`）：5级降级搜索（ISO/GB → 行标 → 团标 → 文献 → 技术文档），每级独立可替换钩子，支持 explicit/start_level 覆盖
- **`references/standards-interface.md`**：LLM 提取标准字段的完整指南 + 搜索链配置文档
- 内置标准：`gbt27417`（GB/T 27417-2017）、`ich`（ICH Q2(R1)）
- 内置模板：`food-testing`（食品检验检测）、`pharmaceutical-testing`（药品检验检测）

### 更新
- `calc_lod_loq()` 改为通过标准注册表查询参数，支持动态扩展新标准

## [1.2.0] - 2026-06-08

### 新增
- 所有场景入口函数添加数据质量前置校验 `_warn_on_data_quality()`（不阻断，warn 提示）：NaN 检测、数据量不足、方差为 0、列不存在等
- FAQ 补充 8 个常见报错场景及排查步骤

### 更新
- SKILL.md 触发词按主要/辅助/不触发三级分类标注优先级
- `references/faq.md` 全面重写：按数据相关/功能相关/安装兼容分组，每个场景含排查步骤+解决建议

### 修复
- `method_validation.py`、`validation.py`、`time_series.py` 的 ValueError 消息改为带原因+建议的上下文友好提示

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

### 更新
- `scripts/report/` → `scripts/docgen/`（规避产出物路径误判）
- SKILL.md 遵循 skill-standardization R-01~R-25 规范（24/25 PASS）
- 数据目录迁移至 `.standardization/analysis-toolkit/`
- 创建 `references/antipatterns.md`、`references/faq.md`、`references/permissions.md`

### 修复
- Prophet 预测在 Windows 中文环境下编码问题（PYTHONUTF8=0）
- `forecast_alert` 返回类型错误（tuple 解包）
