## 2.45.0 (2026-06-01)

### 新增
- **body.json v2.6.0 三层章节体系**: section_tiers (must_have/whitelist.optional_progressive/whitelist.always_progressive) + progressive_index_table 定义
- **classification_hints**: 所有标准章节新增供 LLM Phase 2 精筛的内容模式匹配字段
- **C-13 渐进式索引表审计**: 检查 ## 核心能力 末尾是否包含索引表及完整性
- **manifest 驱动清理**: cleanup_manager.py + safe_io 自动注册 + builder 强制清理
- **fix_split_nonstandard**: 非标章节拆分到 references/
- **fix_section_order**: 按 body.json section_order 重排章节

### 更新
- **R-17 阈值 200→230**: 放宽渐进式拆分行数限制
- **R-17 两阶段协议**: 非标章节改为 Phase 1 正则粗筛 → Phase 2 LLM 精筛
- **fix_section_trigger/core/workflow**: 对接 body.json content_format 生成规范内容
- **manifest 合并**: old backup/manifest.txt → new data/manifests/<id>.json 统一体系
- **快速开始**: 从 must_have 移至 whitelist.optional_progressive
- **约束章节**: 新增 must_have 层级的 ## 约束（简短操作约束清单），位于 H1 后首位
- **约束序位**: section_order 第2位（H1后），SKILL.md 相应调整

### 修复
- **C-12 升级为内容完整性检查**: 通过 classification_hints.format_clues 逐章节验证内容是否完整，含智能格式匹配（正向触发/否定条件→check literal、编号列表/简短列表→check regex）
- **C-12 语义检查 → Phase 2**: 从 content_format.guidelines 提取含"应/必须"的语义要求，输出为"需 LLM Phase 2 确认"项（如"工作流程每步应标注输入输出"）
- **R-23 描述过时检测**: 扫描 SKILL.md 中 R-XX~R-YY 引用，与 rules.json 实际规则数对比，不一致则标记
- **蓝皮书增强 (skill_inspector)**: AST 函数签名扫描（函数名+参数+docstring）+ 类结构 + CLI 子命令 + 关键常量 + 引用链路图（标记未引用文件）+ 文档-代码脱节检测
- **蓝皮书 Windows 兼容**: root_py/root_md 路径分隔符修复
- **C-07 代码块计数修正**: 排除闭合 ``` 被误计为"缺少语言标识"，改用成对算法
- **create 模板对齐新审计**: 新增 `## 约束` must_have 章节 + 渐进式索引表（替代旧附录）+ 清理过时引用
- **create 模板清理**: 移除硬编码权限说明章节（应由 AI 按需生成）
- **C-07/C-08 输出增强**: 代码块缺语言标识和 checklist 检测现在包含行号 + 触发文本
- **C-08 正则收紧**: 避免"确认无异常后"等非 checklist 文本误报
- **R-20 输出增强**: changelog 术语一致性检查的 fix 描述不再自触发 WARN
- **审计输出格式统一**: 所有 WARN 项均包含 filepath:line_number + 上下文片段
- **术语统一**: changelog.md 统一使用"更新"一词
- **SKILL.md 清理**: 多余空行收敛、独立渐进式加载说明合并到核心能力
- **section_order**: 补充 数据目录说明、临时文件与备份管理 条目
- **根目录垃圾文件**: 清理 8 个 0 字节残留文件
- **_record_backup**: 改为调用 cleanup_manager.register_backup()，放弃 manifest.txt
- **skill_rollback.py**: load_manifest() 从 data/manifests/*.json 读取 + 兼容旧 manifest.txt
- **自审 0 ERROR 0 WARN**: 全量通过

---

## 2.44.8 (2026-05-31)

### 修复
- **data_dir 格式修正**: frontmatter 的 data_dir 恢复为 ../ 相对路径格式（此前错误同步为 skills/ 格式）

---
## 2.44.7 (2026-05-31)

### 修复
- audit --fix 自动修正: meta_field_sync, artifact_paths

---

## 2.44.6 (2026-05-31)

### 修复
- audit --fix 自动修正: meta_field_sync, artifact_paths, writing_standards

---

## 2.44.5 (2026-05-31)

### 新增
- **R-06 H1 位置修复工具**: 新增 fix_h1_position，自动将 H1 移到 frontmatter 后首行

---
## 2.44.4 (2026-05-31)

### 修复
- **R-06 H1 不匹配技能名**: 新增 H1 内容与 skill name 一致性检查，避免 H1 与技能名无关仍通过审计

---
## 2.44.3 (2026-05-31)

### 修复
- **--fix changelog 机器名问题**: 收集 fix_details 替代硬编码空话，终端输出追加 AI 强制指令
- **changelog v 前缀**: _do_bump() 写入版本号时删除 v 前缀，符合 R-10
- **SKILL.md 检查清单**: 新增 --fix 后转化 changelog 的 checklist 项

---
## 2.44.2 (2026-05-31)

### 修复
- **R-06 代码块误判**： 不再将代码块内的  误判为 H1 标题

---
## 2.44.1 (2026-05-31)

### 修复
- **R-06 代码块误判**：不再将代码块内的 # 注释误判为 H1 标题
- **R-20/R-23 审计范围缺陷**：脚本调用验证（R-20）和文档-代码一致性检查（R-23）原仅扫描 SKILL.md 正文，不扫描 references/*.md，导致渐进式文件中的错误脚本路径从未被发现。改为同时扫描 SKILL.md 和 references/*.md。

---

## 2.44.0 (2026-05-31)

### 新增
- R-25 文档写作格式规范审计（10项子检查：C-01 H1格式ERROR + C-02~C-09 WARN建议 + C-10 空行规范 WARN）
- body.json: enhanced format_rules with R-25 C-01~C-10 references
- rules.json: R-25 规则定义 + create_template 参考模板
- structure_checker.py: body_check_document_format() 审计函数
- **skill_inspector.py**: 新增技能结构扫描工具（蓝皮书生成器），输出元信息/目录树/章节/函数清单/引用概览/安全数据
- **skill_builder 新增 inspect 子命令**: `python -m scripts.skill_builder inspect <skill-dir>`
- **update/refactor 流程增强**: 备份后自动运行 inspect 结构扫描，确保改造前了解技能全貌
- guide.md: update/refactor 工作流加入强制 inspect 步骤
- 冲突排除：不与 R-06/R-18/R-19/R-21/R-24 冲突
- 全部子检查仅作建议标准统一，不强制改造

### 修复
- R-01 合并 _meta.json 字段检查：新增 regex_frontmatter_and_meta() 组合函数
- update_skill_frontmatter.py / fix.py / __init__.py: 写 SKILL.md 前清理 body 前导空行（body.lstrip('\n')）
- 修复 frontmatter 闭合后多余空行问题


---

## 2.43.2 (2026-05-30)

### 修复
- **R-06 H1 版本号检测正则增强**：原正则只匹配版本号在 H1 标题末尾的情况（如 `# name v2.38.7`），无法检测版本号在标题中间的情况（如 `# git-sync v2.6.27 -- 描述`）。改为检测 H1 中任何位置的版本号模式

---


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

