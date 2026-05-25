# 更新日志（Changelog）

> 本文件记录 skill-standardization 的版本更新历史。
> 遵循 [Keep a Changelog](https://keepachangelog.com/) 格式，基于 SemVer 版本管理。

---

## v2.29.2

2026-05-26

**改写类型：Minor — 新增标准化 IO 工具，提升创建/更新效率及稳定性**

### 更新内容

- 📌 **新增 `scripts/safe_io.py`**：标准化文件 IO 接口，替代直接 `open()`
  - `safe_read(path)`：编码容错读取（utf-8 → gbk → latin-1 兜底）
  - `safe_write(path, content)`：原子写入（临时文件 + `os.replace()`），自动备份
  - `safe_patch_regex(path, pattern, replacement)`：正则替换，比 `Edit` 工具更鲁棒
  - `safe_patch_by_line(path, line_num, new_str)`：按行号替换，不依赖精确字符串匹配
  - 所有写操作自动备份到 `data/backup/`，返回 `rollback_id`
- 📌 **新增 `scripts/skill_rollback.py`**：技能文件专用容灾回滚
  - `list`：列出所有备份（从 `manifest.txt` 读取）
  - `rollback <id>`：按 ID 恢复文件
  - `rollback --latest N`：回滚最近 N 次操作
  - `show <id>`：查看备份与当前文件的差异（ unified diff）
  - `purge [--keep N]`：清理旧备份，保留最近 N 个
- 📌 **新增 `scripts/op_logger.py`**：结构化操作日志
  - `log_op(operation, file_path, success, rollback_id, detail)`：记录 JSON Lines 到 `data/logs/ops.log`
  - `log_audit_result(audit_result)`：从审计结果自动记录日志
  - `recent [N]`：查看最近 N 条日志
- 📝 更新 `SKILL.md`：新增「标准化 IO 工具」章节，文档化新工具使用方式
- 📝 更新 `SKILL.md` 版本号到 v2.29.2
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- AI 更新技能文件时，优先使用 `safe_io.py` 替代 `Edit` 工具，避免空白符/不可见字符导致的反复失败
- 所有写操作自动备份，失败时可通过 `skill_rollback.py` 一键回滚
- 操作日志结构化，便于审计追溯
- skill-standardization v2.29.2 21/21 PASS

---

## v2.29.1

2026-05-25

**改写类型：Patch — R-20 中英文混排误报修复**

### 更新内容

- 🐛 **修复 R-20 中英文混排误报**：预清理阶段增加文件名（`SKILL.md`、`reference.md`）和目录路径（`scripts/`、`references/`）剔除，避免误判
- 🐛 **修复 `subprocess等` 缺空格**：`permissions.md` 表格中 `subprocess等` → `subprocess 等`
- 🐛 **修复 `渐进式MD体系` 缺空格**：`reference.md` 中 `渐进式MD体系` → `渐进式 MD 体系`
- 🐛 **修复模糊表述误报**：`reference.md` 规则表格中 `(可能/应该/大概)` 描述改为 `禁止模糊表述`
- 📝 更新 `SKILL.md` 版本号到 v2.29.1
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- R-20 写作规范检查 now passes (0 误报)
- skill-standardization v2.29.1 21/21 PASS

---

## v2.29.0

2026-05-25

**改写类型：Minor — 审查出错时建议修正方式输出 + create-template 命令**

### 更新内容

- ✅ **`audit_skill()` 返回增强**：`entry` 新增 `fix` 和 `suggestion` 字段，JSON 报告包含完整修正建议
- ✅ **`format_report()` 增强**：详细输出模式显示每条 FAIL 规则的修正建议（`fix.operation` / `fix.location` / `fix.reason`）
- ✅ **新增 `create-template` 命令**：输出所有 21 条规则的创建模板（供 LLM 创建技能时参考）
  - `python -m skill_audit create-template` — 人类可读格式
  - `python -m skill_audit create-template --json` — JSON 格式
- ✅ **`RULES` 定义增强**：`create_template` 字段统一格式，包含所有规则的创建骨架
- 📝 更新 `SKILL.md` 版本号到 v2.29.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- AI 审查技能时，FAIL 输出包含具体修正建议，减少反复试错
- 创建新技能时，AI 可先运行 `create-template` 获取正确骨架和写作方式
- JSON 格式报告现在包含完整 `fix` 信息，便于程序化解析和自动修正

---

## v2.28.0（当前版本）

2026-05-25

**改写类型：Minor — Frontmatter 规范化增强 + 权限说明文件**

### 更新内容

- ✅ **新增 `permission_weight` frontmatter 字段**：支持 HIGH/MEDIUM/LOW 三档权限权重声明
- ✅ **新增 `antipattern_count` frontmatter 字段**：强制 antipattern 条目含具体示例（`add_examples`）
- ✅ **新增 `section_faq` frontmatter 字段**：强制 SKILL.md 含 FAQ 章节或渐进式引用
- ✅ **新增 `writing_standards` frontmatter 字段**：强制术语一致性检查（`fix_terms`）
- ✅ **新增 `antipattern_vague` frontmatter 字段**：强制 antipattern 描述具体（`add_detail`）
- ✅ **新增 `section_antipattern` frontmatter 字段**：强制 antipattern 章节存在且有实质内容
- ✅ **新增 `progressive_loading_explicit` frontmatter 字段**：强制 SKILL.md 显式说明渐进式加载
- ✅ **新增 `references/permissions.md`**：权限扫描结果说明文件，供 `create` 模式自动生成
- 📝 更新 `SKILL.md` 版本号到 v2.28.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- skill-standardization 自身声明 `permission_weight: HIGH`，与 `permission_checker.py` 实际风险等级一致
- 新创建的 skill 自动获得 `references/permissions.md` 模板
- AI 审查 skill 时，frontmatter 字段缺失会触发对应 WARN

---

## v2.27.1

2026-05-25

**改写类型：Patch — 审查规则 R-18/R-19 内容质量检查增强**

### 更新内容

- ✅ **R-18 内容质量检查**：antipattern 条目必须 ≥2 条且含具体错误做法/正确做法标记
- ✅ **R-19 内容质量检查**：FAQ 必须 ≥3 对且问题 ≥10 字、答案 ≥15 字
- ✅ **修复 R-18/R-19 审查输出**：PASS/FAIL 均输出详细理由
- 📝 更新 `SKILL.md` 版本号到 v2.27.1
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- R-18/R-19 从"引用存在性检查"升级为"内容质量检查"
- 空壳 `references/antipatterns.md` / `references/faq.md` 不再 PASS

---

## v2.27.0

2026-05-25

**改写类型：Patch — `references/architecture.md` 新增 + 规范加载优化**

### 更新内容

- ✅ **新增 `references/architecture.md`**：架构设计文档，描述模块关系和数据流
- ✅ **优化渐进式加载逻辑**：`json_loader.py` 支持按 frontmatter 字段按需加载 references 文件
- ✅ **修复 `skill_audit` 对 v2.27+ frontmatter 字段的识别**
- 📝 更新 `SKILL.md` 版本号到 v2.27.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- 大型 skill 可通过 `references/architecture.md` 描述整体架构
- `json_loader.py` 加载效率提升（按需加载）

---

## v2.26.0（当前版本）

2026-05-25

**改写类型：Patch — 审查规则数不一致修复（文档与代码对齐）**

### 更新内容

- ✅ **修复 SKILL.md 描述**："`R-01~R-20 审查`" → "`R-01~R-21 审查`"
- ✅ **修复核心能力表**："`20 条审查规则 | R-01~R-20`" → "`21 条 | R-01~R-21`"
- ✅ **修复审查规则概述表**：节标题 + 补充 R-21 行（渐进式加载显式说明）
- ✅ **修复 `utils.py` 注释**："`(R-01 ~ R-17)`" → "`(R-01 ~ R-21)`"
- ✅ **修复 `__init__.py` docstring**："`R-01~R-17`" → "`R-01~R-21`"
- 📝 更新 `SKILL.md` 版本号到 v2.26.0
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- 全技能文档一致确认：**共 21 条规则（R-01 ~ R-21）**，全部在 `METHOD_MAP` 中有对应实现，无缺失
- `reference.md` 规则表（L192~L216）本身已完整含 R-21，无需更新
- AI 加载技能时不再因文档不一致而产生困惑

---

## v2.25.0（当前版本）

2026-05-25

**改写类型：Minor — R-12 推荐代码模式规范化**

### 更新内容

- ✅ **R-12 推荐代码模式**：在 `artifact_checker.py` 的 R-12 fix 操作中加入完整推荐代码块（双变量法：`DEFAULT_DATA_DIR_RAW` + `_data_dir_abs`）
- ✅ **R-12 审查输出增强**：pass 和 fail 的 `detail` 信息中均包含推荐模式说明
- ✅ **`guide.md` 新增 R-12 规范章节**：`### R-12: 外部数据目录路径规范（v2.25.0）【新增】`，包含审计原理说明、推荐代码块、3 个关键点、3 个常见错误模式
- 📝 更新 `SKILL.md` 版本号到 v2.25.0
- 📝 更新 `_meta.json` 版本号和描述
- 📝 更新 `scripts/skill_builder/__init__.py` 和 `scripts/skill_audit/__init__.py` 文件头版本号

### 影响

- R-12 审查现在输出可操作的推荐代码模式，AI 可直接参考使用
- `guide.md` 新增 R-12 规范化章节，作为 skill-standardization 自身的规范文档
- 其他 skill 在 R-12 违规时，可直接从审查输出中获取正确写法，避免反复试错

---

## v2.24.7

2026-05-25

**改写类型：Bug 修复 — R-18/R-19 渐进式引用审查逻辑重构**

### 更新内容

- ✅ **重构 R-18 反模式审查逻辑**：强制渐进式（SKILL.md 直接写反模式 → FAIL），检查 `references/antipatterns.md` 引用、文件存在性、内容质量（≥2 条具体示例 + 错误做法/正确做法标记）
- ✅ **重构 R-19 FAQ 审查逻辑**：强制渐进式（SKILL.md 直接写 FAQ → FAIL），检查 `references/faq.md` 引用、文件存在性、Q&A 质量（≥3 对 + 问题≥10字 + 答案≥15字）
- ✅ **支持表格格式**：R-18 现在能正确解析 `references/antipatterns.md` 中的表格格式反模式条目
- 📝 更新 `SKILL.md` 版本号到 v2.24.7
- 📝 更新 `_meta.json` 版本号和描述

### 影响

- R-18 现在正确强制渐进式（不再接受 SKILL.md 直接写反模式）
- R-19 现在正确强制渐进式（不再接受 SKILL.md 直接写 FAQ）
- 所有渐进式文件审查逻辑统一：检查引用 → 检查文件存在 → 检查内容质量
- skill-standardization 自身审计 20/20 PASS（0 ERROR, 0 WARN）

---

