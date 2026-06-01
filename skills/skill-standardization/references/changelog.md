## 2.50.1 (2026-06-01)

### 修复
- 新增 C-16 references/文档过时检测 + 修复4个文档8+处过时引用

---

## 2.50.0 (2026-06-01)

### 修复
- 文档优化：触发条件口语化增强 + FAQ过时描述修复 + guide 审计输出示例

---

## 2.49.0 (2026-06-01)

### 修复
- C-15 扩展为通用内容冗余检测（15a引用重复/15c H1后独立引用/15d章节重叠）

---

## 2.48.0 (2026-06-01)

### 修复
- 新增 C-15 索引表引用冗余检测 + R-25 子检查增至15项

---

## 2.47.4 (2026-06-01)

### 修复
- 自修 C-13 索引表补全 + R-10 trigger 同步 + fix_progressive_index_table references/ 前缀

---

## 2.47.3 (2026-06-01)

### 修复
- 修复 _load_body_spec 路径错误（spec/→scripts/spec/），导致 fix_section_order 失效

---

## 2.47.2 (2026-06-01)

### 修复
- 修复 _load_known_sections 残留引用导致的 R-17 崩溃

---

## 2.47.1 (2026-06-01)

### 修复
- fix_reclassify_section + fix_split_nonstandard 操作后自动同步渐进式索引表

---

## 2.47.0 (2026-06-01)

### 修复
- 新增 fix_reclassify_section 通用非标章节归类（merge/split/delete 三种模式，参数驱动不写死）

---

## 2.46.4 (2026-06-01)

### 修复
- 回退 known_sections 机制，改为正确合并非标章节到标准章节

---

## 2.46.3 (2026-06-01)

### 修复
- 修复 #B4 known_sections 机制缺失：R-17 Phase 2 合法章节无备案导致重复误报

---

## 2.46.2 (2026-06-01)

### 修复
- 修复 #B1 progressive_index_table 重复 bug #B2 section_constraint 过宽 regex

---

## 2.46.1 (2026-06-01)

### 修复
- fix_section_trigger/core/workflow 改为从目标技能脚本采集内容，不照抄模板

---

## 2.46.0 (2026-06-01)

### 修复
- 新增 fix_section_constraint + fix_progressive_index_table（从目标技能采集内容，不照抄模板）

---

## 2.45.4 (2026-06-01)

### 修复
- 工作流程新增 create 模式步骤

---

## 2.45.3 (2026-06-01)

### 修复
- 工作流程从5步扩至12步，匹配实际标准化流程

---

## 2.45.2 (2026-06-01)

### 修复
- 触发条件增加自然语言触发短语（提升触发友好度 4.3→目标5.0）

---

## 2.45.1 (2026-06-01)

### 修复
- 自改造：核心能力末尾添加渐进式文件索引表

---

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
- **C-14 工作流程步骤完整性**: 新增 WARN 级审计，检测工作流程步骤数 + 混入的版本标记内容（类似更新日志的行文应移至 changelog.md）
- **C-14 审计输出全部可见**: R-25 汇总显示上限从 4→20 条，LLM 不再需要翻文件查看被截断的 WARN
- **工作流程清理**: 移除混入的更新日志内容（v2.38.2/v2.38.5 版本标注 + 排错止损规则），改为 `→ 详见 references/guide.md`，仅保留 5 步核心流程
- **根目录垃圾文件**: 清理 8 个 0 字节残留文件
- **_record_backup**: 改为调用 cleanup_manager.register_backup()，放弃 manifest.txt
- **skill_rollback.py**: load_manifest() 从 data/manifests/*.json 读取 + 兼容旧 manifest.txt
- **渐进式索引表**: ## 核心能力 末尾添加 ### 渐进式文件索引 表格（文件名|位置|说明），C-13 通过
- **自审 0 ERROR 0 WARN**: 全量通过

---

## 2.44.8 (2026-05-27)

### 修复
- 三层章节体系 + manifest 清理 + 修复工具扩展
