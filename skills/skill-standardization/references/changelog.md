## 2.63.4 (2026-06-05)

### 修复
- update/refactor 流程末尾增加版本号三端一致验证钩子

---

## 2.63.3 (2026-06-05)

### 修复
- 铁律8: 明确定义误判判定边界，禁止LLM修改/放宽规则；增加二段筛查输出格式模板(强制逐条填写)

---

## 2.63.2 (2026-06-05)

### 修复
- 强制脚本钩子：蓝皮书前置扫描 + LLM二段筛查(exit(1)截断) + fix后二次二段筛查 + artifact_paths文件匹配修复

---

## 2.63.0 (2026-06-04)

### 改进
- SKILL.md create 模式新增生成后目录结构预览（开箱即用度 4.3→预估 4.5）
- 能力与限制「自动修复」行明确 --fix 和 R-23 的能力边界：仅修格式/结构/路径，不修代码逻辑错误

---

## 2.62.2 (2026-06-04)

### 改进
- SKILL.md 新增「能力与限制」章节（能力边界定义 3.8→预估 4.5+）
  - 明确列出 6 项核心能力的适用范围和限制条件
  - 审计/创建/改造/批量审计/自动修复/权限安全扫描 各一条
  - 触发后立即可见的输出内容说明
- 错误消息人性化改进（异常处理 4.0→预估 4.3+）
  - `_meta.json` 未找到：给出可能原因和解决步骤
  - `--fix` 无自动修复项：提示查看 FAIL 报告和 --verify
  - 版本号解析失败：给出期望格式和检查建议

---

## 2.62.1 (2026-06-04)

### 修复
- audit --fix 自动修正: writing_standards

---

## 2.62.0 (2026-06-04)

### 重构
- **`--verify` 删除白名单预筛**：`_reclassify_false_positive()` 不再影响 exit code，所有 FAIL 项全量输出给 LLM
  - 之前：白名单匹配的误报提前过滤，LLM 只看"剩余项"（可能漏看边界误报）
  - 之后：LLM 逐条审查所有 FAIL 项（含上下文），语义判断即误报依据，无需匹配白名单
- `rules.md` 铁律 8 删除"新误报"概念，改为 LLM 全量审查
- `rules.md` 铁律 9 同步更新 `--verify` 逻辑说明
- `_reclassify_false_positive()` 降级为仅报告显示标记（ⓘ），不影响决策流程

---

## 2.61.2 (2026-06-04)

### 修复
- `scripts/skill_audit/_tree_scanner.py` `_check_directory_tree()`: 目录树扫描中添加非文件路径条目筛选
  - 根因：R-23 的目录树一致性检查将概念图条目（如 `├── 联网搜索（参见 search-integration.md）`）误判为文件路径
  - 修复：扫描时跳过含中文文字、中文括号、无扩展名非目录的条目，避免概念图/流程图误报
- `scripts/skill_audit/__init__.py` `_reclassify_false_positive()`:
  - 同步为 R-20 风格建议（术语偏好、模糊表述）添加误判标记
  - 为 R-23 中文目录树模式保留双保险规则
- `SKILL.md` 工作流程：
  - audit 模式：新增 LLM 二段误判筛查步骤（铁律 8），位于输出审查报告之后
  - update/refactor 模式：将"再次审计确认"改为具体命令 `audit --verify` + exit(0) 达标条件 + 修复循环

---

## 2.61.1 (2026-06-03)

### 修复
- `updater.py` / `refactor.py` / `skill_builder/updater.py` / `skill_builder/refactor.py`:
  删除 `--inject-auth` 条件门控，update/refactor 模式默认执行权限扫描和 permissions.md 写入
  （原行为：不传 --inject-auth 则跳过权限扫描；现行为：默认执行）

---

## 2.61.0 (2026-06-02)

### 改进
- C-17/C-18/C-19 质量审计输出升级：新增章节定位 + LLM执行指令
  - 输出格式从笼统描述改为「【章节名】问题描述 → LLM执行：具体操作指令」
  - 示例：【快速开始】示例缺少完整交互流程 → LLM执行：在用户输入之后补充系统推荐/计算结果/输出内容的描述
- 新增 C-17 示例章节自动定位（从 H2 标题中匹配示例/快速/使用章节名）
- 质量审计不再只是发现问题，而是直接告诉 LLM 去哪里、做什么（增删改替）
- 修复方式说明明确指向 LLM 自主修复（非 fix.py 替换），与铁律8全报告LLM细筛衔接

---

## 2.60.0 (2026-06-02)

### 改进
- C-17/C-18/C-19 从存在性检查升级为质量检查：
  - C-17：不再只检查"有无示例"，而是检查示例是否覆盖完整交互流程、是否有具体数值参数、是否覆盖多种场景
  - C-18：不再只检查"有无边界章节"，而是检查阈值是否量化具体、是否覆盖参数约束、是否覆盖环境/依赖要求
  - C-19：不再只检查"有无错误处理问答"，而是检查是否有具体修复步骤、是否分类说明不同错误场景
- 修复所有中文引号冲突导致的 SyntaxError（U+201C/U+201D 被 Python 解析为字符串定界符）

---

## 2.59.0 (2026-06-02)

### 新增
- R-25 新增 C-17（使用示例检查）、C-18（能力边界检查）、C-19（错误处理检查）

### 改进
- 更新 SemVer 更新语义规则：明确 PATCH 不含新功能、多更新不得打包为 PATCH、新增审计规则属于 MINOR
- 新增 SemVer 示例表格（MAJOR/MINOR/PATCH 三种级别+示例+核心约束4条）
- 更新 bump --type fix 的描述为"单处bug修复/文档错别字/参数拼写(不含新功能)"

---

## 2.58.1 (2026-06-02)

### 修复
- 铁律9: LLM不得跳过未处理WARN

---

## 2.58.0 (2026-06-02)

### 修复
- 新增 --verify 强制验证模式；新增铁律8：audit --verify exit(1) 替代 AI 自觉；约束条款同步更新

---

## 2.57.1 (2026-06-02)

### 修复
- body.json: 新增「权限说明」到 allowed_sections/optional_sections/section_order，消除 R-17 与 R-13~R-17 冲突

---

## 2.57.0 (2026-06-02)

### Fixed
- **R-17**: 阈值 200→230、删除松散引用检测(超限即 ERROR)、非标章节输出ⓘ→🟡 WARN

---

## 2.56.0 (2026-06-01)

### 新增

- **目录树扫描器**：新增 `_tree_scanner.py`，自动检测文档中 `├──/└──` 目录树格式，还原完整路径与磁盘核对。可发现 `.tex`→`.txt`、文件改名或缺失等树结构过时问题，不限语言
- **行内代码误抓过滤**：step 1/1b 增加过滤，避免 `` ```json `` 等三连反引号被行内代码正则误解析为代码块头碎片
- **误报分类扩展**：`_reclassify_false_positive` 新增 JSON 示例路径（`"file": "`）和占位符名（`my_package`）误报模式

---

## 2.55.0 (2026-06-01)

### 修复

- **R-23 误报过滤增强**：step 2 新增示例输出行跳过（含 →、[CREATE] 等标记）、占位符路径过滤（<xxx>、xxx、...、/path/、./、扩展名列表、~ 家目录、编码损坏字符）；`_reclassify_false_positive` 新增 R-23 step 3 示例脚本引用误报模式、R-20 R-23 关联误报模式

---

## 2.54.0 (2026-06-01)

### 新增

- **R-23 文件引用存在性检查**：step 2 从仅匹配 .py 扩展为匹配所有文件路径，新增 step 4b 检查文档引用的非 .py 文件是否真实存在。自动递归搜索 scripts/ 下同名文件（不同扩展名），降低误报
- **R-23 修复工具**：新增 `_fix_md_file_refs` + `_find_actual_file`，自动修复文档中不存在的文件路径引用（同目录查找 + 递归 scripts/ 搜索）
- **误报分类泛化**：`_reclassify_false_positive` 识别系统命令/工具名被误检为函数名的场景

---

## 2.53.0 (2026-06-01)

### 新增

- **R-22 联动 _is_asset_dir**：`data_dir_checker.py` 的 os.walk 扫描跳过被脚本引用的功能数据目录，不再误报 components/manifest.json 等文件
- **`_is_asset_dir` 迁移至 utils.py**：从 artifact_checker.py 抽出到 skill_audit/utils.py，供 R-11/R-22 共享
- **审计报告误报分类**：新增 `_reclassify_false_positive()` 后处理，已知误报（如系统工具名 lualatex 被误检为函数名）显示为 ⓘ 已排除，不与真实 WARN/ERROR 混排

---

## 2.52.0 (2026-06-01)

### 新增

- **R-11 交叉引用检查**：新增 `_is_asset_dir()` 函数，在 `_scan_unknown_dir` 和 `_check_root_artifact_files` 判定产出物前，扫描 scripts/ 下脚本是否有硬编码引用。被引用的目录视为功能数据而非产出物，不再误报
- **隐藏目录不再盲目放过**：`.cache/`、`.tmp/` 等隐藏目录如果含产出物且未被脚本引用，仍报违规；只有被引用的隐藏目录才放过
- **根目录白名单扩展**：`_KNOWN_ROOT_FILES` 补充 Makefile、Dockerfile、Cargo.toml、package.json、pyproject.toml 等 40+ 构建工具和项目配置文件

---

## 2.51.1 (2026-06-01)

### 修复
- 修复 C-15 15c 增加 markdown 链接语法检测

---

## 2.51.0 (2026-06-01)

### 修复
- 补全5个缺失fix函数: version_con/sanitize/data_dir/section_antipattern/section_faq

---

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
- **create 模板清理**: 删除硬编码权限说明章节（应由 AI 按需生成）
- **C-07/C-08 输出增强**: 代码块缺语言标识和 checklist 检测现在包含行号 + 触发文本
- **C-08 正则收紧**: 避免"确认无异常后"等非 checklist 文本误报
- **R-20 输出增强**: changelog 术语一致性检查的 fix 描述不再自触发 WARN
- **审计输出格式统一**: 所有 WARN 项均包含 filepath:line_number + 上下文片段
- **术语统一**: changelog.md 统一使用"更新"一词
- **SKILL.md 清理**: 多余空行收敛、独立渐进式加载说明合并到核心能力
- **section_order**: 补充 数据目录说明、临时文件与备份管理 条目
- **C-14 工作流程步骤完整性**: 新增 WARN 级审计，检测工作流程步骤数 + 混入的版本标记内容（类似更新日志的行文应移至 changelog.md）
- **C-14 审计输出全部可见**: R-25 汇总显示上限从 4→20 条，LLM 不再需要翻文件查看被截断的 WARN
- **工作流程清理**: 删除混入的更新日志内容（v2.38.2/v2.38.5 版本标注 + 排错止损规则），改为 `→ 详见 references/guide.md`，仅保留 5 步核心流程
- **根目录垃圾文件**: 清理 8 个 0 字节残留文件
- **_record_backup**: 改为调用 cleanup_manager.register_backup()，放弃 manifest.txt
- **skill_rollback.py**: load_manifest() 从 data/manifests/*.json 读取 + 兼容旧 manifest.txt
- **渐进式索引表**: ## 核心能力 末尾添加 ### 渐进式文件索引 表格（文件名|位置|说明），C-13 通过
- **自审 0 ERROR 0 WARN**: 全量通过

---

## 2.44.8 (2026-05-27)

### 修复
- 三层章节体系 + manifest 清理 + 修复工具扩展
