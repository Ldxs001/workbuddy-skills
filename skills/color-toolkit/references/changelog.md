## [3.2.0] - 2026-06-17

### 修复
- refactor: color-toolkit

---

## 3.1.0 (2026-06-17)

### 改造
- skill-standardization 全流程审计修复：
  - R-11: 删除根目录违规产出物文件（.test-report.html等）
  - R-15: 补全 permissions.md 权限说明头部
  - R-17: SKILL.md 从 320 行精简至 206 行（≤230 行），详细功能描述拆分到 references/features.md
  - R-20: 修复 references/features.md 及 permissions.md 中英文混排空格
  - 双0验证通过（26/26 PASS, 0 ERROR 0 WARN）

---

## 3.0.0 (2026-06-17)

### 架构重构 (MAJOR)
- preview_generator.py 完全重写为**三层架构**：

  算法层 (color_toolkit.py) → 渲染层 (preview_generator.py) → 骨架 (HTML_SKELETON)

  | 层 | 职责 | 文件 |
  |---|------|------|
  | 算法层 | 提供数据 (convert/get_contrast/find_accessible 等) | color_toolkit.py |
  | 渲染层 | 每个算法对应一个独立 render 模块，返回 `<section>` | preview_generator.py |
  | 骨架层 | 组合 sections 为完整 HTML 页面 | HTML_SKELETON 模板 |

- **19 个原子模块**可通过 `assemble_report(color, modules=[...])` 任意组合
- **text-preview 模块**：内部调用 `find_accessible` 获取真实推荐文字色，在背景上展示效果
- **中文别名**支持：`四项对比色`、`三色组`、`互补色`、`类似色`、`文字效果`
- 旧接口 `generate_full_preview_html()` / `generate_palette_page_html()` 完全兼容

---

## 2.1.0 (2026-06-17)

### 重构
- preview_generator.py 完全重写为模块化架构：
  - 14 个独立 `render_*()` 组件函数，每个返回 HTML 片段
  - 3 个构建器函数 `build_color_report()` / `build_palette_report()` / `build_accessible_report()` 按需组合
  - 用户可通过 `sections=["info","contrast"]` 精确控制输出内容
  - 旧接口 `generate_full_preview_html()` / `generate_palette_page_html()` 保持完全兼容

---

## 2.0.0 (2026-06-17)

### 新增
- 无障碍颜色推荐功能：`find_accessible()`
  - 固定背景色推荐文字色 (mode="fg")
  - 固定文字色推荐背景色 (mode="bg")
  - 支持字号/字重判定大小文本（AA 3:1 vs 4.5:1）
  - 支持 AA/AAA 目标等级
  - 自动限制最多 25 种推荐，色相分散保证多样性
- CLI 新增 `accessible` 子命令

### 修复
- 补全 SKILL.md / examples.md 中遗漏的 6 项功能文档

---

## 1.2.0 (2026-06-17)

### 修复
- examples.md 补全可视化输出示例（四色矩形色块布局 / 转换预览 / 对比度预览），修正文档与实际 HTML 输出脱节的问题

---

## 1.1.0 (2026-06-10)

### 修复
- 全流程 refactor：修复 12 项 FAIL，标准化改造

---


## 1.0.4 (2026-06-05) — 自动版本升级

### Changed
- 版本号 1.0.3 → 1.0.4（`update --fix` 自动 bump）
## 1.0.3 (2026-06-05)

### 修复
- audit --fix 自动修正: frontmatter_fields, version, artifact_paths, external_data_dir, antipattern_progressive, writing_standards, progressive_loading_explicit

---

## v1.0.2 (2026-05-30)

### 修复
- audit --fix 自动修正
