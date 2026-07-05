## [2.6.2] - 2026-07-04

### 基础设施
- 合并: 前身技能 drawio-diagram v2.0.0 的历史修复记录，保持溯源完整
- 删除: drawio-diagram 技能目录（已归档，旧版不再维护）
- 溯源: drawiodo 的前身是 drawio-diagram v2.0.0（agent_created），参见下方「前身：drawio-diagram v2.0.0」记录

---

## [2.6.1] - 2026-06-19

### 修复
- 修复: drawio_agent.py 硬编码钩子调用(PRE_THINK/POST_THINK/PRE_ITERATE/POST_ITERATE) + 版本自动备份集成

---

## [2.6.0] - 2026-06-19

### 修复
- refactor: drawiodo

---

## [2.5.0] - 2026-06-19

### 修复
- refactor: drawiodo

---

## 2.4.1 (2026-06-10)

### 修复
- 修复FAQ排错章节格式 + changelog反斜杠引用清理

---


## 2.4.0 (2026-06-10)

### 新增
- **钩子系统强制约束**：12 个内置钩子全部 Python 端执行，0 个依赖 LLM 自觉
  - `preview_trigger` 钩子：直接调用 subprocess.Popen 打开 draw.io 预览
  - `shortcut_detector` 钩子：快捷模式时直接清除 confirm_options，LLM 无法 AskUserQuestion
  - `auto_backup` 钩子：迭代前直接调用 VersionManager.save_version() 自动备份
  - `limit_checker` 钩子：版本超限时直接删除最旧版本
- 新增 `references/hooks.md`：钩子系统完整参考文档

### Changed
- 输出路径标准化：`{workspace}` → `skills/.standardization/drawiodo/outputs/`（铁律 4）
- 创建 outputs/ 和 temp/ 标准化目录
- SKILL.md 正文冗余路径清理（删 8 行）
- 生成图表章节拆分到 `references/generation.md`（247→194 行）

### 修复
- trigger 字段反斜杠损坏修复：--fix 将触发词中的 `draw.io` 反复转义为大量反斜杠，已恢复
- 版本号三端一致：SKILL.md = _meta.json = changelog = 2.4.0
- _meta.json description 与 SKILL.md frontmatter 同步

---

## 2.3.2 (2026-06-10)

### 标准化
- skill-standardization v2 全量审计（R-01~R-26），25/25 PASS，0 ERROR 0 WARN
- 修复 R-10：三端版本号一致（SKILL.md = _meta.json = changelog = 2.3.2）
- 修复 R-17：生成图表章节拆分到 references/generation.md，SKILL.md 从 247 行降至 196 行
- 修复 _meta.json description 与 SKILL.md frontmatter 不一致
- 修复 changelog.md 旧版 v 前缀
- 更新 `references/generation.md`：从 SKILL.md 拆分，保持渐进加载
## 2.3.0 (2026-06-10)

### 新增
- **钩子系统**：在 Think→Confirm→Iterate→VC 四阶工作流中植入 8 个 Hook Point
- 新增 `scripts/drawio_hooks.py`：钩子引擎（注册/注销/执行/历史/自检），含 12 个内置钩子
- 新增 `references/hooks.md`：钩子系统完整参考文档
- `pre_think` 钩子：输入校验 + 上下文补全
- `post_think` 钩子：分析输出完整性校验
- `pre_confirm` 钩子：选项校验 + 快捷模式检测
- `post_confirm` 钩子：用户选择解析
- `pre_iterate` 钩子：文件存在性检查 + 备份触发
- `post_iterate` 钩子：输出校验 + 自动预览触发
- `pre_vc` 钩子：版本上限检查
- `post_vc` 钩子：版本状态报告
- 反模式新增：跳过钩子校验、篡改钩子注册表

### 强制约束机制
- **`auto_backup` 钩子**：迭代更新前直接调用 `VersionManager.save_version()` 自动备份，**不依赖 LLM 自觉**
- **`output_validator` 钩子**：首次生成后直接调用 `VersionManager.init()` 自动初始化版本管理，**不依赖 LLM 自觉**
- **`limit_checker` 钩子**：版本数超限时直接删除最旧版本目录，**不依赖 LLM 自觉**
- **`preview_trigger` 钩子**：直接调用 `subprocess.Popen()` 打开 draw.io 预览，**不依赖 LLM 自觉**（升级前为 flag 模式）
- **`shortcut_detector` 钩子**：快捷模式时直接清除 `confirm_options`，LLM 无法展示 AskUserQuestion（升级前为 flag 模式）
- `file_checker` 钩子：输出目录不存在时自动 `os.makedirs()` 创建
- 废弃 `backup_trigger`（flag 模式），替换为 `auto_backup`（Python 执行模式）
- 所有相关文档同步更新：hooks.md/SKILL.md/guide.md/antipatterns.md

---

## 2.2.2 (2026-06-04)

### 修复
- audit --fix 自动修正: frontmatter_fields, h1, version, external_data_dir
- 修复 H1 不含技能名（# drawiodo: draw.io 自动做图 Skill）
- 补充 frontmatter trigger 字段（4 条触发规则）
- 修复 _meta.json description 与 SKILL.md 不一致
- 修复 SKILL.md data_dir 路径与 _meta.json 统一
- 修复 changelog.md 旧版本 v 前缀（v2.2.1 → 2.2.1）
- 删除 drawio.py 硬编码 LIB_DIR 路径，改用脚本所在目录
- 修复 drawio_templates.py import math 在文件末尾问题

---


---

## 前身：drawio-diagram v2.0.0（2026-05-13）

> drawiodo 的前身 skill，由 agent_created 生成的原型版本。以下修复记录保留自 drawio-diagram 的 SKILL.md「已知问题与修复记录」章节。

### 2026-05-13 思维导图布局修复

**问题**：子节点使用极坐标计算位置，导致：
1. 子节点坐标超出画布（负坐标或大于1169/827）
2. 子节点间距不足，3个以上时重叠
3. 文本宽度固定（100px），中文字符被截断
4. 连线交叉混乱

**修复**：
1. 重写 `_sub_layout()` 函数，改为笛卡尔坐标系
2. 子节点排列方向与分支方向垂直（上下分支→水平排列，左右分支→垂直排列）
3. 节点宽度根据文本自适应：`_text_width()` 中文字符1.8倍宽度
4. 子节点间距最小30px，根据数量动态调整
5. 所有坐标限制在画布范围内

**验证**：AI技术思维导图（4分支×3子节点）测试通过。

### 2026-05-13 思维导图连线修复

**问题**：连线混乱，交叉、方向不对

**根因**：
1. `build_xml()` 没有将 `source_port`/`target_port` 写入 XML
2. `create_mindmap()` 没有根据分支方向指定连接点

**修复**：
1. `drawio_gen.py build_xml()`：Edge 生成时添加 `sourcePort`/`targetPort` 属性
2. `drawio_templates.py create_mindmap()`：根据分支/子节点方向指定正确的 sourcePort/targetPort

### 2026-05-13 连线端口传递方式修复

**问题**：`sourcePort`/`targetPort` XML 属性被 draw.io 完全忽略，连线依然乱

**根因**：draw.io 不识别 mxCell 的 `sourcePort="0"` 属性，只认 style 字符串里的 `exitX`/`exitY`/`entryX`/`entryY`

**修复**：`build_xml()` 中将端口映射为坐标，写入 edge style 字符串：
- port 0 (顶部) → `exitX=0.5;exitY=0;`
- port 1 (右侧) → `exitX=1;exitY=0.5;`
- port 2 (底部) → `exitX=0.5;exitY=1;`
- port 3 (左侧) → `exitX=0;exitY=0.5;`

### 2026-05-13 思维导图连线路由修复

**问题**：连线到处拐直角，非常丑

**根因**：默认 EdgeStyle 使用 `orthogonalEdgeStyle`（正交路由），思维导图不适合

**修复**：思维导图所有连线改用 `edgeStyle=none`（直线连接）
