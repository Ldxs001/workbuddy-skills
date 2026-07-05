## [3.3.2] - 2026-07-03

### 修复
- 移除 frontmatter 中重复的 displayName 字段（原有一条残留的"SVG 拼接工具"）

## [3.3.1] - 2026-07-03

### 修复
- 修正 displayName 为 svg-composer（原为"SVG 拼接工具"）

## [3.3.0] - 2026-07-02

### 修复
- refactor: svg-composer

---

# SVG 拼接工具 (svg-composer) 版本更新日志

## [3.2.2] - 2026-06-23

### 修复
- 标准化改造：补全 SKILL.md YAML frontmatter、references/ 体系、data_dir 字段

## [3.2.0] - 2026-06-23

### 新增
- 新增 `generate_preview_html()` 函数：生成带超链接的预览 HTML
- 新增 `batch_mode_compose_with_preview()` 函数：批量生成 + 自动生成预览
- 预览页面包含：下载链接、文件夹路径链接（file:///）、SVG 预览图

## [3.1.0] - 2026-06-23

### 更新
- SVG 输出添加 Font Awesome 许可证注释（CC BY 4.0）

## [3.0.0] - 2026-06-23

### 更新
- 明确仅支持 `0-9`、`A-Z` 字符集
- 添加黑白双色支持（仅 `black` / `white`）
- 添加四种拼接模式：`compose_sequence`、`compose_permutations`、`compose_combinations`、`compose_limited`
- 自动小写转大写处理
- 移除 `currentColor` 支持

## [2.0.0] - 2026-06-23

### 更新
- 默认字符集从 @tscircuit/alphabet 改为 @fortawesome/fontawesome-free

## [1.0.0] - 2026-06-23

### 新增
- 初始版本，支持横向/纵向拼接
