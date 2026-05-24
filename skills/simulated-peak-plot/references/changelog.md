# 更新日志（Changelog）

> 本文件记录 simulated-peak-plot 的版本变更历史。

---

## v2.6.0（当前版本）

2026-05-25

**改写类型：中文化改造**

### 变更内容

- ✅ `SKILL.md` 全中文翻译（移除所有英文段落）
- ✅ `references/parameters.md` 全中文翻译（218行）
- ✅ `description` 中文化（SKILL.md frontmatter 和 _meta.json）
- 📝 更新版本号：2.5.0 → 2.6.0

### 影响

- 技能文档全中文，符合中文用户使用习惯
- 代码块、JSON、技术术语保留英文（符合行业标准）
- 审计 17/17 PASS

---

## v2.5.0（当前版本）

2026-05-25

**改写类型：Bug 修复 — 数据路径规范化**

### 变更内容

- ✅ 新增 `get_skill_data_dir()` 函数（返回 `.standardization/simulated-peak-plot/data/` 路径）
- ✅ 修改 `generate_peak_plot()` 函数，让 `output_file` 使用 `get_skill_data_dir()` 返回的路径
- ✅ 修改 `generate_plot_from_csv()` 函数，让 `output_file` 使用正确路径
- ✅ 修改 `export_csv_file()` 函数，让 `csv_file` 使用正确路径
- 📝 更新版本号：2.4.0 → 2.5.0

### 影响

- 输出文件（PNG/CSV）现在统一保存到 `.standardization/simulated-peak-plot/data/` 下
- 符合 `skill-standardization` 规范（数据/产出物路径统一到 `.standardization/<skill>/` 下）
- 审计 17/17 PASS

---

## v2.4.0

2026-05-25

**改写类型：标准化改造 — refactor 模式**

### 变更内容

- ✅ 执行 `skill-standardization refactor` 标准化改造
- ✅ 创建备份：`simulated-peak-plot_bak_refactor_20260525_001409`
- ✅ 生成 `references/permission.md`（风险 low，无需授权）
- 📝 更新版本号：2.3.2 → 2.4.0

### 影响

- 技能目录结构符合标准化规范
- 权限扫描完成，无高风险操作
- 审计 17/17 PASS

---

## v2.3.2

2026-05-19

**改写类型：功能增强 — 复合峰支持**

### 变更内容

- ✅ 支持复合峰（N 个子峰组合）
- ✅ 支持 M-型、馒头型、泊松型等复杂峰形
- ✅ 新增 `generate_composite_peak()` 函数
- ✅ 交互式配置支持子峰数量设置

### 影响

- 可模拟更复杂的真实色谱/光谱峰形
- 复合峰注释显示子峰数量

---

## v2.0.0

2026-05-10

**改写类型：架构重构 — 配置驱动**

### 变更内容

- ✅ 改为配置字典驱动（替代硬编码参数）
- ✅ 支持 JSON 配置文件导入
- ✅ 支持 CSV 数据导入（设备导出格式）
- ✅ 新增 `import_csv_data()` 函数
- ✅ 新增 `generate_plot_from_csv()` 函数

### 影响

- 用户可通过配置文件复用参数
- 可直接可视化实验数据
- 输出支持 PNG + CSV 双格式

---

## v1.0.0

2026-05-01

**改写类型：初始版本**

### 变更内容

- ✅ 基础高斯峰生成
- ✅ 噪声模拟
- ✅ 基线设置
- ✅ Matplotlib 可视化
- ✅ Markdown 表格输出

### 影响

- 最小可用版本（MVP）
