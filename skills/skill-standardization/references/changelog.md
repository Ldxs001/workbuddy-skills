## [2.102.4] - 2026-07-03

### 修复
- 修复: `structure_checker.py` R-23 路径解析使用源文件目录而非 skill_dir（`references/` 下的路径应相对 source file 目录解析，而不是从 skill_dir 解析）

---

## [2.102.4] - 2026-07-03

### 修复
- 修复: `structure_checker.py` R-23 路径解析使用源文件目录而非 skill_dir（`references/` 下的路径应相对 source file 目录解析，而不是从 skill_dir 解析）
- 修复: `fix.py` `fix_section_workflow()` 在 ## 工作流程 已有自定义内容时跳过覆盖（避免每次 refactor --continue 销毁已有的工作流表格和门禁表）

## [2.102.6] - 2026-07-03

### 修复
- 修复: `structure_checker.py` R-07 正则过于激进，所有以"用户需要"开头的触发词均被标记为模板式，包括 auto-fix 自己生成的 `用户需要[具体动作]` 描述。改为仅当"用户需要"后紧跟 ≤8 字或含"功能/工具/能力"泛词时才拒，打破 auto-fix 非收敛循环

---

## [2.102.5] - 2026-07-03

### 修复
- 修复: `body.json` 在 约束 章节同义词中添加「能力边界」「能力边界与限制」「能力与边界」，使 C-11 不再误报这些常用章节名

---

### 修复
- 修复: `fix_progressive_index_table()` 在替换索引表时会丢失 SKILL.md 中已有的人工填写内容。新增 `existing_rows` 保留机制：先读取现有表格行内容，仅对新文件调用 STANDARDIZED 或 auto-generate，已有行保持原有 4 列内容不变。

---

## [2.102.2] - 2026-07-01

### 修复
- 修复: `_write_fp_classify()` 现在同步从 `.remaining_llm.json` 移除已分类项，防止 `refactor --continue` 循环死锁（根因：--classify 只写 verify_fp，不更新 remaining_llm，导致每次 --continue 仍加载全部未分类项）

---

## [2.102.1] - 2026-06-30

### 修复
- 修复: C-14 在工作流已确认后不再循环警告（检测 .structure_workflow.json 存在即跳过）

---

## [2.102.0] - 2026-06-30

### 修复
- 修复: _blocked_fix_keys 允许 LLM 完成结构化数据后分类（_read_struct存在即放行）; C-XX classify 新增 _filter_false_positives 第二层过滤

---

## [2.101.11] - 2026-06-30

### 修复
- 修复: --classify 支持 C-XX 格式匹配 R-25 子检查项（C-08/C-12/C-14等）

---

## [2.101.10] - 2026-06-30

### 修复
- 脱敏：SKILL.md + guide.md 中的真实用户路径替换为占位符 ~/dev/skills/

---

## [2.101.9] - 2026-06-30

### 修复
- 文档同步 + C-17/C-18 内容补全

---

## [2.101.8] - 2026-06-30

### 修复
- **[R-12] _find_shared_path_file 选错共享路径文件** — 当业务文件（如 grid_builder.py）import 数量超过 _paths.py 时被误选为路径定义来源，导致 DATA_DIR 变量未扫描到。新增后备逻辑：当选中的文件不含路径变量声明且 _paths.py 存在时优先改选。
- **[R-12] pathlib 路径推导式误报** — `DATA_DIR = STD_DIR / "data"` 等 pathlib 链式赋值因值中不含 ".standardization" 字面量被误判为路径违规。新增推导式放行：同一文件有变量包含 `.standardization` 字面量时，派生变量不再触发 R-12。

## [2.101.7] - 2026-06-30

### 修复
- **[P0] auto-fix 在手动修复周期中不应执行** — `_run_audit_loop()` 检测到 `.manual_wait` 存在时跳过 auto-fix 阶段，避免覆盖 LLM 手动修改的内容。此前每次 `--continue` 都重新全量审计 + auto-fix，手动修的内容被覆盖，导致 9 条 WARN 循环不收敛。

## [2.101.6] - 2026-06-30

### 修复
- **[P0] mtime 校验阻断 LLM 跳过修复循环** — `_run_audit_loop()` 检测 `.manual_done` 时，比对 `wait_files` 中每个文件的 mtime 与 `.manual_done` 的 mtime。文件 mtime 早于 `.manual_done` 说明 LLM 未实际修改即标记完成 → HARD-BLOCK（`sys.exit(1)`）。此前只检查文件是否存在，LLM 可写 `.manual_done` 后不改任何文件直接通过。
- **[P0] _fix_key_map 缺 C-05/C-07/C-13 映射** — 这三个本应是 auto-fixable 的机械格式化问题，因无 fix key 被归入 LLM 手动范畴。已补 mapping 到 `writing_standards`/`trigger_format`/`section_reorder`。

## [2.101.5] - 2026-06-30

### 修复
- **[P0] 指纹快照加固** — 新增 `_update_snapshot()` + `_verify_snapshot()` 机制，对三份信号文件（.verify_fp.json / .remaining_llm.json / .manual_wait）做 SHA256 指纹快照。
  - 写入点：`_write_fp_classify()`、`_save_remaining_llm()`、`_signal_manual_wait()` 完成后自动更新指纹
  - 校验点：`_load_fp_ids()`、`--continue` 入口、`_run_audit_loop()` 入口自动校验
  - 指纹不匹配或文件被删 → HARD-BLOCK（`sys.exit(1)`），阻止 LLM 绕过管道直接写信号文件

## [2.101.4] - 2026-06-30

### 修复
- **[P0] fix.py:1463 external_data_dir 空值导致 audit 误报** — `external_data_dir:`（YAML null）改为 `external_data_dir: true`。修复 auto-fix 与 audit R-01 之间的不一致。根因：FM_REQUIRED 含 `external_data_dir`，但 fix_frontmatter 写入的是空值，二次审计时报"缺失必填字段"，形成 fix→audit→fix 死循环。

## [2.101.3] - 2026-06-28

### 修复
- 补全剩余 6 处 `_reclassify_false_positive` 传 `skill_dir`：
  - `audit_skill` 内 false-positive 计数（影响 summary）
  - `format_report` 内逐行 ⓘ 标记
  - `generate_html_report` 内 before-table 行标记 + 误报计数 + after-table 误报计数
  - `cmd_audit_all` 内 fp_status 显示
- 至此全部 18 处 `_reclassify_false_positive` 调用均已正确传 `skill_dir`

## [2.101.2] - 2026-06-28

### 修复
- `format_report()` 缺少 `skill_dir` 参数导致文本报告从不展示 LLM 二筛结果，看起来"双0验证没有 LLM 二次筛除"
- `generate_html_report()` 内 3 处 `_reclassify_false_positive` 未传 `skill_dir`，导致 HTML 报告的修复前计数/误报排除计数失准
- 修改：`format_report` 加 `skill_dir` 参数，9 个调用点全部传值；`generate_html_report` 内 3 处补传 `skill_dir`
- 注明：写/读 `.verify_fp.json` 的路径一致，不存在路径穿透问题

## [2.101.1] - 2026-06-28

### 修复
- `_clean_stale_state`: 正确的根因——不是清理列表的问题，是之前的修复错误地保留了 `.verify_fp.json`。
  实际根因：`_clean_stale_state` 曾在 LLM 二次筛除循环内部被调用，导致刚分类写入的 `.verify_fp.json` 被立即清除。
  本次修正：
  - `.verify_fp.json` 加回清理列表（它是 session 级状态文件，新 refactor 应清理）
  - docstring 写明时序规则：只在 Step 0（蓝皮书前，仅首次 refactor）和 Step 9（一致性审查后）调用
  - 确认 `_run_audit_loop` 内部无 `_clean_stale_state` 调用
  - Step 0 有 `--continue` 守卫，`refactor --continue` 不触发清理

## [2.101.0] - 2026-06-28

### 变更
- `_clean_stale_state` 移除 `.verify_fp.json` 清理（临时方案，v2.101.1 已修正为正确方案）

### 变更
- fix_writing_standards: 新增中英文混排正则空格修复（`[\u4e00-\u9fff][A-Za-z]{2,}`），`--fix` 可自动修混排空格
- C-12 约束计数条件修正：`items_c > 5` → `items_c > 9`，与消息"超过上限 9 条"一致
- 步骤 4 二次筛除加锁：拒绝未完成全部 classify 就进入细碎循环，修复清单冻结不可边修边改
- `section_names` 移出 `_blocked_fix_keys`：C-12 9=9 超上限是引擎 bug，非标章节/流程步数可用 subtype 分类
- refactor 启动/结束时清理旧会话状态文件（`_clean_stale_state`）
- 修复 `_clean_stale_state` 属性名（`continue_run` → `refactor_continue`）

---

## [2.99.1] - 2026-06-27

### 修复
- C-17: 正则 `用户...：...` 后匹配 `推荐|结果|报告|输出` 未加 `re.DOTALL`，导致多行示例格式（用户请求和系统输出在不同行）无法匹配
- structure_checker.py:2036 加 `re.DOTALL` 标志，支持多行示例内容

---

## [2.99.0] - 2026-06-27

### 新增
- _path_detector._find_shared_path_file(): 自动检测共享路径文件（不限于 _paths.py）
- C-20: 检测所有非从共享文件导入的路径构造，全部输出（不再只输出重复定义）
- C-20: 支持自动识别共享文件名（_paths.py / _config.py / _paths_module.py 等）
- C-20 P3/P4: 新增局域路径推导 + 硬编码路径字面量检测

### 修改
- R-11/R-12: 只检查共享文件中的声明（有共享文件时不再扫所有脚本）
- 二次筛除统一走审计报告：已分类项显示为"PASS (LLM 二筛通过)"而非被过滤

---

## [2.98.8] - 2026-06-26

### 修复
- C-17 regex 用户[：:]→用户[^：:]*?[：:], 修复hug-html示例误报
- _render_examples_section 补回缺失的return
- 修复_name_dir→_name_dir_path(skill_dir) 变量作用域bug

---

## [2.98.7] - 2026-06-26

### 修复
- HTML饼图stroke-dasharray改为根据周长归一化, 修复齿轮图
- C-12 "编号列表"clue增加circled-number和bullet检测, 修复工作流程图误报
- C-12语义规则检查改为匹配sec_body而非guideline文本

---

## [2.98.6] - 2026-06-26

### 修复
- C-12 "列表"clue 从字面量匹配改为检测 [-] 前缀列表项, 修复限制章节误报

---

## [2.98.5] - 2026-06-26

### 修复
- 一致性审查同步.manual_wait信号; 文档更新描述

---

## [2.98.4] - 2026-06-26

### 修复
- .manual_done后增量审计逐项打√, 修好的从备查单移除, 还有剩就继续等, 全清完才进双0

---

## [2.98.3] - 2026-06-26

### 修复
- .manual_done 确认后跳过审计/修复循环, 不再重新发现同一批问题导致死循环

---

## [2.98.2] - 2026-06-26

### 修复
- 一致性审查同步: cmd_refactor/cmd_update 中所有 sys.exit(2) 改为 _signal_manual_wait
- 剩余 4 处退出点统一走 .manual_wait/.manual_done 信号，脚本不退出

---

## [2.98.1] - 2026-06-26

### 修复
- 修复2个控制漏洞: 退出信号+增量审计
- 漏洞2: 修复循环内sys.exit(2)→.manual_wait信号机制, LLM修完写.manual_done脚本自动继续
- 漏洞3: 修复循环内全量审计→增量审计(只查修改过的文件)

---

## [2.98.0] - 2026-06-26

### 修复
- 4项修复: _llm_only_fix_keys禁止分类绕过; _path_detector.py统一路径检测; R-23排除.standardization/路径; R-20移除R-23重复引用

---

## [2.97.2] - 2026-06-26

### 修复
- Fix1: format_report()改show_fix_hint参数,refactor/update/--fix不再误导LLM; Fix2: cmd_audit --fix加_llm_only_fix_keys过滤; Fix3: sys.exit前强制生成HTML报告

---

## [2.97.1] - 2026-06-26

### 修复
- 文档修复: CHANGELOG.md→references/changelog.md; 创建能力描述更新; 流程步骤对齐9步; 模式映射表归入约束; guide.md措辞修正

---

## [2.97.0] - 2026-06-26

### 修复
- 创建模式增强: 模板章节名修正+示例值替代占位符+新增_paths.py模板+新增数据目录路径指引

---

## [2.96.2] - 2026-06-26

### 修复
- 创建模式修复: 移除技能根目录data/改用.standardization/; 补antipatterns.md+faq.md; 迁changelog到references/; 索引表更新

---

## [2.96.1] - 2026-06-26

### 修复
- 修复_check_path_centralization Windows路径分隔符(反斜杠→正斜杠),确保format_report上下文提取正常

---

## [2.96.0] - 2026-06-26

### 修复
- 新增R-25 C-20路径集中管理审计(path_centralization), 含auto-fix创建_paths.py+替换重复定义为import

---

## [2.95.11] - 2026-06-25

### 修复
- 修复_dname双写bug, 增加入口门禁_check_pending_fix

---

## [2.95.10] - 2026-06-24

### 修复
- **`__init__.py` create-template LICENSE 截断** — `_refs_content['LICENSE.md']` 只写了 `Permission is hereby granted...`（含字面 `...`），改为完整 MIT 许可证文本 + `{year}`/`{author}` 占位符
- **`__init__.py` 写入未替换占位符** — `f.write(_rc)` 不做 `.replace()`，`{year}`/`{author}` 留在文件里。已补 `.replace()` + `import datetime`
- **`fix.py` license 模板含 `[username-redacted]`** — copyright 行为 `[username-redacted]`（敏感扫描脱敏产物），改回 `your-name-here`
- **创建 master `skills/LICENSE.txt`** — 供 fix 工具 `fix_license_compliance` 复制使用，含 `{year}`/`{author}` 占位符

---

## [2.95.9] - 2026-06-24

### 修复
- changelog: 重写 v2.95.6/v2.95.7/v2.95.8 描述

---

## [2.95.8] - 2026-06-24

### 修复
- R-12 step 3-b: 移除方案A修复方向（不可通过移除 data_dir 声明规避），仅保留方案B（声明 DATA_DIR 指向 .standardization/）

## [2.95.7] - 2026-06-24

### 新增
- R-12 step 3-b: 写入路径按三种模式分类输出——硬编码字面量 / CLI参数(sys.argv) / 变量路径(运行时确定)
- CLI 参数模式特有: 附加三层修复指引——(1) 声明 DATA_DIR 常量 (2) CLI 默认值指向 DATA_DIR (3) 保留覆写能力

## [2.95.6] - 2026-06-24

### 新增
- R-12 step 3-b: `meta_has_data_dir=True` 且脚本无 `.standardization` 引用时，扫描所有写操作并输出路径清单 + 方案B修复方向

## [2.95.5] - 2026-06-24

### 修复
- `--json` 输出污染：`_semantic_precheck()` 检测到 `--json` 参数时将门禁文字写入 stderr 而非 stdout，确保 JSON 流可解析

### 更新
- `.standardization/skill-standardization/` 数据目录文档修正为 per-skill 子目录结构，移除不存在的 `logs/ops.log`，backup 格式修正为 `.bak`
- `audit-all` 能力边界描述修正：从"仅支持一级子目录"改为"遍历所有子目录，不自动排除"

## [2.95.4] - 2026-06-24

### 修复
- fix 循环无限循环根因：`fixes_applied == 0` 时 fix key 不清除（原逻辑 `fix_key in fix_details` 因 fix_details 为空永远不成立），改为无条件 `del res["fix"]`
- fix 循环 R-25 fix key 反复注入：加 `loop_count == 1` 条件，仅首轮注入，避免 auto-fix 死循环
- `_run_audit_loop()` 修复指引：`apply_fix()` → "手动编辑 SKILL.md 或 references/"
- 移除循环内所有 `--classify` 出口文案（误判标记仅在前置 LLM 二次筛查阶段进行）

### 更新
- `.standardization/skill-standardization/` 数据目录结构说明：调整为 per-skill 子目录结构，移除不存在的 `logs/ops.log`，backup 格式修正为 `.bak`（原文档写 `.zip`）
- `audit-all` 能力边界描述：从"仅支持一级子目录"改为"遍历所有子目录，不自���排除"
- 修复 `--json` 模式输出污染：`_semantic_precheck()` 在 `--json` 请求时将门禁文字输出到 stderr 而非 stdout，确保 JSON 流纯净
- R-17 修复指引：从"添加「→ 详见 references/xxx.md」散落引用"改为"优先使用渐进式文件索引表，禁止正文散落引用"，解决与 C-13 的矛盾
- C-12 约束上限：从 5 条改为 9 条（适应多钩子技能的需求）
- `.fix_loop_check.json` 循环检测改用动态技能名路径（原硬编码为 novel-weaver）

## [2.95.3] - 2026-06-22

### 修复
- `_run_audit_loop()` 锁函数名 typo：`_create_refactor_lock()` → `_lock_refactor()`
  - 之前 NameError 导致 `.refactor_locked.lock` 从未被创建，`sys.exit(2)` 也跑不到
  - 剩余 LLM 修复项时 exit code=1（崩溃）而非 2（强制锁定），LLM 可绕过循环
- `_semantic_precheck()` 模式锁：refactor 模式下允许 `audit --classify` 通过（二次筛除是 refactor 流程的内置步骤）

### 新增
- `--classify --category engine_cant_judge` 的 `--reason` 改为**必填**，且必须包含文件路径/行号证据
- 纯嘴说"引擎无法理解"不再被接受，须提供如 `permissions.md:91 YYYY 是年份通配符` 的具体定位

## [2.95.2] - 2026-06-21

### 修复
- SKILL.md 能力与限制表：`--audit-all` 参数形式修正为 `audit-all` 子命令
- references/guide.md：`audit --verify` 示例补齐缺失的 `--confirmed` 参数；`update --continue` 改为 `refactor --continue`（update 实际不支持 --continue）
- references/reference.md：从"部分内容已过时"模糊状态改为明确的已废弃声明，指向 guide.md 和 rules.md
- references/faq.md：删除无关的 `_skillhub_meta.json` 历史遗留 QA
- SKILL.md + _meta.json：description 精简，去除旧 changelog 残留文字

---

## [2.95.1] - 2026-06-21

### 修复
- C-12 触发条件格式检查：`"**正向触发**" in sec_body` 字符串精确匹配不支持冒号变体，改为 `r'\*\*正向触发(：)?\*\*'` 正则，兼容 `**正向触发**` / `**正向触发：**` / `**正向触发**：` 三种写法
- 一致性审查 missing_doc_ref 死循环：auto-fix 不可修复时循环 20 轮才终止，改为首次发现即保存 `.remaining_llm.json` 后 `sys.exit(0)` 清爽退出，由 LLM `--classify` 处理误报后 `--continue`

---

## [2.95.0] - 2026-06-20

### 修复
- 文档同步更新: --classify 改为必须带 --category; --mode 改为必传; _llm_only_fix_keys 新增 section_names; guide.md 命令示例全部加 --category

---

## [2.94.0] - 2026-06-20

### 修复
- --category 误判类别强制 + --mode 必传 + 修复循环 exit(2) 阻断 + body.json 合法化 + C-11 三层 instruction + 一致性审查嵌套目录修复 + OMP 硬编码泛化

---

## [2.93.2] - 2026-06-20

### 修复
- 修复: _run_audit_loop 前置LLM二次筛阻断点被 refactor --continue 绕过（skip_llm_prefilter=True）。移除该跳参，改为无条件检查 --classify 数据是否存在

---

## [2.93.1] - 2026-06-19

### 修复
- 修复: 重构锁机制(_lock/_unlock/_is_locked) + classify自动验证 + R-XX误判ID支持 + step5误报过滤 + 报告生成锁阻断

---

## [2.93.0] - 2026-06-18

### 修复
- 修复 _run_audit_loop 细碎循环分离策略（规则ID→fix-key粒度）、新增停滞检测（_fixes_applied+_prev_sig）、修复 _struct_dir 路径硬编码、统一文档描述

---

## [2.92.0] - 2026-06-18

### 修复
- v2.91.0 最终改造：文档更新+架构修复+创建骨架升级

---

## [2.91.0] - 2026-06-18

### 修复
- v2.90.0: 前置LLM二次筛阻断点钩子

---

## [2.90.0] - 2026-06-18

### 新增
- `_run_audit_loop()` 新增**前置 LLM 二次筛除阻断点**：
  - 流程: ①审计 → ②报告展示 → **③★LLM二次筛** → ④_filter_false_positives → ⑤细碎循环
  - 首次进入时检查 `--classify` 文件，无数据则阻断，输出 3 步操作指引
  - `--continue` 标志跳过阻断点，支持 LLM 标记误报后重新进入修复循环
  - 阻断点保存 `.remaining_llm.json`，`--continue` 时恢复

### 修复
- skill-standardization 自身标准化改造：模式-命令映射锁代码级强制 + SyntaxError 修复

---

## [2.88.2] - 2026-06-18

### 修复
- 修复 `structure_checker.py:254` f-string 内嵌 ASCII 双引号导致 SyntaxError

### 改进
- `_semantic_precheck()` 新增 `llm_mode` 参数，代码级校验语义自检闸门输出模式与当前子命令是否一致（模式-命令映射锁）
- 4 个子命令（audit/refactor/create/update）新增 `--mode` CLI 参数
- SKILL.md 新增「★ 模式-命令映射锁（代码级强制）」铁律，快速开始命令补上 `--mode` 参数

---

## [2.88.1] - 2026-06-18

### 修复
- R-07: 触发条件正/否定区域分离，仅计正向区域的 bullet，修正否定条件 bullet 被充作正向触发计数的缺陷
- R-07: 新增正向触发词内容质量检测，识别模板式/泛化话术
- C-13b/C-15: 扩展正则支持 Markdown 链接格式引用检测 + 残缺引用检测
- 规则 check 描述: 移除"必须修复""建议修复"等程度判断语，仅保留客观检查描述
- R-20 输出格式: 移除"🔴 必须修/🟡 需修/⚪ 可选择修"程度标签
- `_llm_only_rules`: 删除静态白名单，改为 fix key 自声明 auto-fix 能力
- references/faq.md: 审计报告分类表移除程度判断，改由 LLM 二次筛归类的客观描述

---

## [2.88.0] - 2026-06-17

### 修复
- refactor: skill-standardization

---


## [2.87.4] - 2026-06-17

### 修复
- 展示报告强制: 审计/改造完成后LLM必须用present_files打开报告给用户查看。

---
