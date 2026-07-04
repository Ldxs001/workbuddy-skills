## [3.4.1] - 2026-07-04

### 基础设施
- 重命名: color-toolkit → color-toolkit-turn（统一ClawHub和本地名称）
- 合并: ClawHub上的color-toolkit和color-toolkit-turn两个slug归一到color-toolkit-turn

---

## [3.4.0] - 2026-06-18

### 修复
- v3.3.3 → v3.4.0: 完成 refactor + LLM二次筛阻断点适配

---

## [3.3.3] - 2026-06-18

### 修复
- skill-standardization 全流程 refactor 标准化改造：修复 R-06/R-07/R-20/R-25 C-07/C-13b/C-15，清理冗余触发场景段

---

## [3.3.2] - 2026-06-18

### 改造
- skill-standardization 全流程 refactor 标准化改造：
  - R-06: 修复 H1 距 frontmatter 空白行问题
  - R-07: 触发条件从泛化描述改为具体用户场景（9 个精确触发词 + 否定条件）
  - R-20: 修复 antipatterns.md 模糊表述「应该」+ changelog.md 中英文空格
  - R-25 C-07: 代码块补充语言标识（```text）
  - R-25 C-13b: 修复残缺渐进式引用
  - R-25 C-15: 内联引用改用渐进式文件索引表引用
  - 清理 --fix 自动生成的冗余 ## 触发场景 段
  - 双0验证通过（26/26 PASS, 0 ERROR 0 WARN）

---

## [3.3.1] - 2026-06-17

### 修复
- 修复antipatterns.md空模板占位符+清理permissions.md测试数据残留

---

## [3.3.0] - 2026-06-17

### 重构
- preview_generator.py 重写为**原子组件架构 v2**：
  - 11 个原子组件 (atom_*): 每个 1:1 映射到单条算法输出记录，N条输出=N个原子
  - 9 个固定组合 (comp_*): 预制分组，如 gradient-set(固定3条渐变)、color-info(1色块+8属性)
  - 建议插槽系统: 私有建议(逐条记录) + 公有建议(全局 tips, 结构化约束模板)
  - 组装引擎: `assemble_report(color, atoms=[...], composites=[...], tips=[...])`
- **私有化建议插槽**：每条算法输出的数据记录自带私有建议位，始终存在，空为占位
- **共有建议插槽**（tips）：结构化约束模板，≥3条覆盖结论/操作/警示/扩展四种信息角色，唯一消耗 token
- **数据完整性验证**：`_validate_output()` 检查组件数是否与声明一致，不匹配抛 ValueError
- **全局 tips 钩子**：任何算法被调用时自动追加 tips 空占位
- **参数别名机制**：除 tips 外修复 color-info/ui-preview/accessible-set/text-preview 参数名不匹配导致的静默失败
- **视觉统一系统**：所有卡片统一 border-radius:10px、box-shadow、间距、字体栈
- 新增 `atom_readability_card` + `comp_readability_set`: 在背景色上直接展示文字效果（上下分层：颜色演示+固定白底信息栏）
- 新增 `atom_contrast_card` 等原子组件，可用 `.atom-grid cols-2/3/4` 统一网格对齐
- 验证机制: `raise_on_fail=True` 时参数不匹配直接中断，不静默吞噬
- 旧接口 `generate_full_preview_html()` / `generate_palette_page_html()` 完全兼容
- 调用链: CLI → 算法计算(0 token) → 声明组件 → 填建议(唯一 token 点) → 组装输出
- 版本: 3.2.0 → 3.3.0 (MINOR, 功能级重构)

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
