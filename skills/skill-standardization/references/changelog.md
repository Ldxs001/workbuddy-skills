## 2.43.1 (2026-05-30)

### 更新
- **R-20 自审粒度修正**：`body_check_writing_standards` 中删除基于 skill_dir 的全局 `self_audit` 判断。之前错误地让整个 skill-standardization 技能的所有文档文件（SKILL.md、references/*.md）都跳过了术语一致性检查，实际上应该只跳过审计代码文件（structure_checker.py）自身。`body_check_writing_standards` 检查的是文档文件而非审计代码，所以 `self_audit` 始终为 False（审计自审审核的是除审核之外的自己是否符合规定）
- **自审通过**：25/25 PASS，0 ERROR，0 WARN ✅

---

## 2.43.0 (2026-05-30)

### 更新
- **R-20 自审排除（v1 错误实现）**：使用 `skill_dir basename` 全局跳过整个技能的所有文档文件。后被修正为只跳过审计代码自身
- **自审通过**：25/25 PASS，0 ERROR，0 WARN ✅

---

## 2.42.1 (2026-05-30)

### 更新
- **版本号格式规范：纯数字 x.y.z 强制**：所有版本号统一为纯数字格式（如 2.42.0），禁止 v 前缀（v2.42.0）
- **R-10 增强：版本号格式检测**：`version_matches_manifest` 新增版本号纯数字格式检测，含 `v` 前缀报 ERROR 并提供自动修复（去 v 前缀）；比较逻辑增加 `_strip_v` 函数统一去 v 前缀后再比较
- **自身版本号修正**：`_meta.json` version 从 `"v2.42.0"` → `"2.42.0"`，`SKILL.md` frontmatter 从 `v2.42.0` → `2.42.0`，`changelog.md` 当前版本标题从 `## v2.42.0` → `## 2.42.0`
- **spec 规范更新**：`frontmatter.json` v2.6.0 增加 version 字段纯数字格式说明；`structure.json` v2.6.0 增加 version 纯数字格式说明
- **修复 git-sync 版本号兼容**：`_strip_v` 确保纯数字版本号在 git-sync 中正确比较（之前已修复）
- **R-20 changelog 历史术语问题修复**：`_check_writing_standards_text` 渐进式文件检查中跳过 changelog.md（历史记录不改），消除 R-20 术语不一致 WARN
- **自审通过**：25/25 PASS，0 ERROR，0 WARN ✅

---

## 2.42.0 (2026-05-30)

### 更新
- **_meta.json 非标字段处理逻辑修正**：不再仅标记输出，改为直接删除（_meta.json 是机器元数据，不应存在非标准字段），同时输出提示供人工判断是否需要迁移
- **frontmatter 非标字段处理逻辑修正**：从自动删除改为仅 WARN 提醒、不删除（frontmatter 允许自定义字段，如 home_url、category 等）
- **R-01 审计提示优化**：frontmatter 非标字段提示从"应清理"改为"仅提醒，不阻断"
- **structure.json v2.5.0**：增加 _meta.json 严格 7 字段说明和 frontmatter 可含自定义字段的对比说明
- **frontmatter.json v2.5.0**：增加非标字段处理策略说明（仅 WARN 提醒不删除）
- **删除 restore_from_gitee.py**：删除远程下载恢复脚本及 reference.md 中的全部引用（历史遗留手动工具，不自动执行，删除以消除安全审查噪音）
- **R-04 增强：description 禁止含版本号**：新增版本号正则检测（`vX.Y.Z`），description 是功能摘要不应含版本号；`fix.py` 新增 `fix_h1_version` 修复函数
- **R-06 增强：H1 正文标题禁止含版本号**：`body_has_h1` 增加 H1 版本号检测，标题含版本号报 ERROR（版本号由 version 字段管理）
- **修复自身 skill-standardization**：`_meta.json` 和 `SKILL.md` 的 description 删除 `v2.40.0` 版本号，SKILL.md 正文 H1 从 `# skill-standardization v2.38.7` 改为 `# skill-standardization`
- **creator 模板清理**：`scripts/skill_builder/creator.py` 和 `scripts/creator.py` 中 3 处写死的版本号引用全部改为纯 skill 名
- **spec 规范更新**：`frontmatter.json` 的 description constraint 增加"不含版本号"；`structure.json` 增加 H1 不得含版本号的规范
- **RULES 描述更新**：R-04 check 增加"不含版本号"说明，R-06 改为"正文含一级标题（不得含版本号）"

