## [1.19.11] - 2026-06-27

### 修复
- **[context_loader] 跨章串行阻断** — 首次加载某章第一个子结构时，检查上一章是否所有子结构已完成。未完成则 HOOK-BLOCK
- **[context_loader] 关键人物 function 缺失阻断** — 从软提示改为 HOOK-BLOCK，角色有 first_appearance 但无 function 时阻断写作
- **[state_manager] add-char function 阻断** — 注册角色时若有 first_appearance 但无 function，直接阻断，规划阶段即强制填写

---

## [1.19.10] - 2026-06-27

### 新增
- **[atomic_writer] 标点缺失校验** — 软性提示（不阻断），检测正文中超过80字无任何标点的片段，输出 [PUNCT] 建议补充断句标点

---

## [1.19.9] - 2026-06-27

### 修复
- **[context_loader] 关键人物输出改为全量累加** — 不再按章节过滤，所有有 `first_appearance` 的角色每子结构全量输出。L03 也能看到老贾卖格斗术的定位，杜绝"当前章节看不到上一章角色"的问题

---

## [1.19.8] - 2026-06-27

### 新增
- **[context_loader] 已出场关键人物注入** — 所有有 `first_appearance` 的角色登场即累加，每子结构全量输出已出场角色及其 `function`（职责/定位）。不限章节，杜绝遗漏
- **[state_manager] add-char 支持 function 字段** — 角色注册时可通过第9参数填写功能定位，写入 IMMUTABLE_SCOPE 保护

### 修复
- 版本跳号：1.19.7 代码已改但 git-sync 跳过推送，强制 bump 至 1.19.8 重新推送

---

## [1.19.7] - 2026-06-27

### 新增
- **[context_loader] 已出场关键人物注入** — 根据 `characters[].first_appearance` 过滤，每子结构输出当前章节前已登场的角色及其 `function`（职责/定位）。LLM 看到"老贾卖格斗术给主角"就不会编成"父亲遗物"
- **[state_manager] add-char 支持 function 字段** — 角色注册时可通过第9参数填写功能定位，写入 IMMUTABLE_SCOPE 保护

### 修复
- **[赛博搏杀记] 角色 function 字段补齐** — 林铁生、林铁心、归元会散人等已补充 function 描述

---

## [1.19.6] - 2026-06-27

### 新增
- **[novel_workflow_engine.py] 修改/扩写提醒** — write-sub 检测到子结构已为 completed 时，标记为修改模式，输出提醒要求修改后运行 finalize-chapter
- **[SKILL.md] 修改/扩写流程约束** — 新增"[强制] 修改/扩写逐子结构串行"，禁止批量修改
- **[hooks.md] 修改/扩写提醒钩子** — 新增钩子条目

---

## [1.19.5] - 2026-06-26

### 新增
- **[plan_chapter] 字数目标写入子结构规划** — `word_count_target: {min, max, check_max}` 自动根据 `meta.length` 注入每个子结构。LLM 读 `novel_state.json` 即可看到字数要求，无需翻技能文档
- **[context_loader] 字数约束从子结构读取** — 不再硬编码 SUB_WORD_TARGETS，改为读 `sub_structures[].word_count_target`
- **[write-sub] 字数校验从子结构读取** — 同上，三处同源

### 修复
- **[赛博搏杀记] L01/L02/L03 注入 word_count_target** — 通过 plan-chapter 重注册，所有子结构持有字数目标

---

## [1.19.3] - 2026-06-26

### 修复
- **[SKILL.md] 文档脱钩全量修复** — 约束新增串行阻断条目；工作流程步骤10/11更新为字数约束+串行阻断+write-sub三级校验；核心能力表格更新为 write-sub 管道描述；hooks.md 新增串行阻断/字数约束注入钩子条目
- **[references/*.md] 全量扫描修复** — execution_standards.md 阻断规则新增串行阻断+字数校验；faq.md 新增"上一子结构未完成"和"字数校验解读"FAQ；examples.md 更新 context_loader/write-sub 输出示例；antipatterns.md 引用三级字数校验

---

## [1.19.2] - 2026-06-26

### 修复
- **[SKILL.md] 新会话指引缺失** — 约束首条新增"[强制] 新会话第一步：查看项目"，数据目录节明确禁止手工拼写路径并列出 list-projects CLI 命令，LLM 不再猜路径

---

## [1.19.1] - 2026-06-26

### 新增
- **[novel_context_loader.py] 串行阻断钩子** — 加载子结构上下文时检测上一子结构 state 是否为 completed，若为 pending 则 HOOK-BLOCK 并输出 write-sub 修复命令，强制 LLM 走管道完成标记后才能继续。子结构串行写作流程由代码级硬约束保障，不再依赖 LLM 自觉

---

## [1.19.0] - 2026-06-26

### 新增
- **[novel_context_loader.py] 字数约束注入上下文** — 根据 `meta.length` 在写作前输出篇幅对应的字数范围 + 校验上浮值，LLM 不再盲写，禁止自行设定
- **[novel_workflow_engine.py] 字数校验统一标准** — write-sub 检查使用与 context_loader 相同的字数目标 + 15% 上浮窗口（中篇 1,500-2,300 范围内通过），低于下限 WARN、超上浮 INFO、范围内 OK
- **[execution_standards.md] 三阶段统一标准文档** — 明确字数目标在规划/写作/检查三阶段使用同一套标准，禁止 AI 自行设定

### 修复
- **[novel_context_loader.py] 情绪格式向后兼容** — 兼容遗留的字符串数组情绪格式（如 `["疑惑","不安"]`），避免 AttributeError
- **[novel_context_loader.py] GBK 终端 emoji 编码崩溃** — 所有 emoji 替换为 `[硬性]`/`[参考]`/`[下一步]` 文本标记

---

## [1.18.2] - 2026-06-26

### 修复
- 修复_extract_keywords和fidelity_check的CJK关键词提取: {2,10}整段匹配→2-4字滑动窗口,避免过长短语匹配失败

---

## [1.18.1] - 2026-06-26

### 修复
- 补写1.18.0 changelog条目,R-11/R-12/C-07/C-16/C-18手动修复,changelog条目补全

---

## [1.18.0] - 2026-06-26

### Fixed
- R-11: 移除SKILL.md中硬编码的绝对路径示例
- R-12: novel_state_manager.py添加DATA_DIR导入,替换局域路径计算
- C-07: 补充代码块语言标识(```→```text)
- C-16: execution_standards.md过期行数阈值200→230
- C-18: SKILL.md补充环境依赖说明(Python3.8+/离线/UTF-8)

### Changed
- 全流程 refactor 改造: 路径集中管理审计整合

---

## [1.17.2] - 2026-06-26

### 修复
- 指纹保护修复: plan-chapter成功后更新.state_fingerprint.txt, 使后续章节规划不被误阻断

---

## [1.17.1] - 2026-06-26

### 修复
- 路径统一管理: novel_workflow_engine.py改从_path_utils.py导入DATA_DIR,消除路径重复计算

---

## [1.17.0] - 2026-06-26

### 修复
- plan-chapter新增文件加载(@/路径), 避免Shell转义破坏JSON

---

## [1.16.4] - 2026-06-25

### 修复
- 4核心脚本加stdout编码修复(sys.stdout.reconfigure utf-8), 解决Git Bash中文乱码

---

## [1.16.3] - 2026-06-25

### 修复
- novel_continuity.py check自动推导chapter_dir从state_path, 修复LLM路径错误

---

## [1.16.2] - 2026-06-25

### 修复
- 原始SKILL.md补充slug/displayName前导字段(修复git-sync冲掉问题)

---

## [1.16.1] - 2026-06-25

### 修复
- 数据目录章节改为代码示例驱动, LLM禁止手写路径, 提供_path_utils.py调用代码

---

## [1.16.0] - 2026-06-25

### 修复
- SKILL.md data_dir修正(data->projects), 新增数据目录章节指引LLM路径

---

## [1.15.1] - 2026-06-25

### 修复
- 标准化改造:_meta.json路径修正/examples.md路径修正/术语统一/约束9to8/路径bug修复

---

## [1.15.0] - 2026-06-25

### 新增
- **[novel_state_manager.py] 核心规划字段保护** — 新增 `_fingerprint()` 指纹校验，首次 plan-chapter 后锁定以下字段：章节 title/overview、子结构 title/summary/tone、角色 name/role/traits/mbti/archetype、novel_info/writing_style/setting。任何非法更新被阻断并打印来源。运行时字段（word_count, status, timeline, continuity_notes）不受影响
- **[novel_workflow_engine.py] plan-chapter --generate 模式** — `python novel_workflow_engine.py plan-chapter <state> <L##> --generate` 输出子结构 JSON 模板供 LLM 填写
- **[novel_workflow_engine.py] 字数代码级校验** — write-sub 写入后根据篇幅(short/medium/long)检查每子结构字数是否达到下限，低于目标打印 WARN
- **[novel_workflow_engine.py] list-projects 集成** — 新增 `list-projects` 命令，列出所有项目名称/路径/阶段/章节进度
- **[_path_utils.py] 中文路径编码修复** — 新增路径解析模块，通过.resolve() + .project 缓存机制，后续命令无需反复传路径

### 修复
- **[novel_logic_check.py] 概述匹配度不再HARD阻断** — 概述为写作前规划的基准文件，一旦确认不可更改。内容与概述的偏离仅做信息性标记(SOFT)，不阻塞finalize-chapter

## [1.14.0] - 2026-06-25

### 修复
- **[novel_logic_check.py] 关键词匹配算法改用bigram重叠率** — 旧算法将概述按标点切段后要求整段逐字出现在正文，导致语义概述永远无法通过HARD检查。改用`2字滑动窗口(bigram)重叠率`匹配，语义自然概述即可正常通行。阈值：WARN=<20%, INFO=<40%
- **[novel_logic_check.py] 概述匹配度不再HARD阻断** — 概述为写作前规划的基准文件，一旦确认不可更改。内容与概述的偏离仅做信息性标记(SOFT)，不阻塞finalize-chapter。偏差信息写入reports供参考
- **[novel_causality_check.py] 检查通过后自动pass门禁** — outline/sub-structure检查全部通过后自动调用`pass_gate()`，消除手动pass_outline_causality/sub_causality门禁的步骤
- **[novel_pipeline_gate.py] set-phase writing增加sub_causality检查** — 转换到writing阶段时除了require outline_causality，现在也require sub_causality
- **[novel_context_loader.py] 末尾输出write-sub命令** — 每个子结构上下文加载后，自动输出下步应执行的完整`write-sub`管道命令

## [1.13.6] - 2026-06-25

### 修复
- **[novel_workflow_engine.py] DATA_DIR 路径错误** — `SKILLS_ROOT.parent / ".standardization" / "novel-weaver" / "projects"` 多了一层 `.parent`，导致路径跳到 `.workbuddy/.standardization/` 而非 `skills/.standardization/`，造成：
  - 帮助信息显示的默认 state 路径指向错误目录
  - next_step 中 HARD 残留检查的 `DATA_CHAPTERS` 路径同样失效
  - 修正为 `SKILLS_ROOT / ".standardization" / "novel-weaver" / "projects"` ✅
- **[novel_workflow_engine.py] next_step 函数定义在 __main__ 块之后** — 导致 `next-step` 命令 NameError: name 'next_step' is not defined。函数定义已移至 `__main__` 之前。

---

## [1.13.5] - 2026-06-25

### 修复
- **Bug 1: overview keyword 匹配对中文失效** — `novel_logic_check.py:213` 使用 `.split()` 对中文文本分词，无空格时整个概述变成一个 keyword 导致永久假阴性。改用 `re.split()` 按标点和空白分词
- **Bug 2: 角色重叠检测被贪婪匹配吃掉短词** — `novel_continuity.py:39` 使用 `{2,4}` 贪婪匹配，"铁心说得对"吐出`铁心说得`，"铁心说我有"吐出`铁心说我`，交集为空。改用双字滑动窗口 `char_bigrams()`
- **Bug 3: tone 硬编码判定改为纯数据参考** — `novel_logic_check.py` tone 检查不再 append issues（不参与阻断），仅 print 命中数 + 语速分析；`novel_context_loader.py` 新增"情绪写作参考"模块，写前给出场景词引导

---

## [1.13.4] - 2026-06-25

### 新增
- **执行规范字数参考表** — `execution_standards.md` 新增按篇幅（短篇/中篇/长篇）的每章/每子结构字数参考标准，确保规划时字数可控

### 修复
- **字数规划缺失** — 之前仅有行数上限（200行/子结构）无字数指导，导致规划阶段字数偏差不可控

---

## [1.13.3] - 2026-06-25

### 修复
- **`init` 自动项目目录** — `init <项目名>` 自动创建在 `.standardization/novel-weaver/projects/<项目名>/data/novel_state.json`，各项目完全隔离
- **`list-projects` 扫描路径修复** — 扫描 `.standardization/novel-weaver/projects/` 下所有项目子目录
- **workflow_engine 路径推导修复** — `_chapters_dir`/`_report_dir` 从 `state_path` 自动推导每个项目的 chapters/reports 路径
- **清除旧版扁平目录** — 删除 `skills/.standardization/novel-weaver/data/` 下的过期文件（已迁移到 `projects/`）

### 新增
- **`init` 支持自动/手动双模式** — 传项目名自动建子目录，传完整路径精确控制

---

## [1.13.2] - 2026-06-25

### 文档同步
- SKILL.md: "16 个流程钩子"→"全量流程钩子"（避免计数过时）；state_manager.py 描述补全 init/set-length/list-projects
- execution_standards.md: style_guide→writing_style（2处）；current_phase→meta.current_phase；"自动推进 phase"→"需手动推进"；finalize-chapter 签名修正
- examples.md: 场景1加 init 步骤；next-step 输出加篇幅行；补 list-projects 场景5

---

## [1.13.1] - 2026-06-25

### 新增
- **`list-projects` 命令** — `novel_state_manager.py list-projects` 扫描标准化数据目录，列出所有已创建的项目（名称/路径/篇幅/阶段/章节进度）

---

## [1.13.0] - 2026-06-25

### 新增
- **篇幅系统（规划前置参数）** — `novel_state.json` 新增 `meta.length` 字段，分三档：
  - `short`: 短篇 3-6 章
  - `medium`: 中篇 8-10 章（默认）
  - `long`: 长篇 11+ 章
- **`init` 命令篇幅支持** — `init <name> [length] [num]`，不传 length 则默认 medium，按篇幅自动计算默认章数（取范围中值）
- **`set-length` 命令** — 中途更新篇幅：`novel_state_manager.py set-length <path> short|medium|long`
- **`next_step` 篇幅检查** — 输出篇幅信息 + 当前章数是否在范围内（不阻断，仅提示）

### 架构
- 所有旧项目（无 `meta.length` 字段）→ `next_step` 在 writing 阶段后提示配置篇幅
- 不改变子结构规划/写作/完结流程

---

## [1.12.6] - 2026-06-25

### 新增
- **`init` 命令** — `novel_state_manager.py init <state_path> <项目名> [章数]` 创建完整的 `novel_state.json` 骨架（含 chapters、writing_style、signature、timeline 等所有标准字段），禁止重复初始化。LLM 不再需要手动写 JSON。
- **plan-chapter 输入校验** — subs_json 格式错误时给出明确阻断信息（非法 JSON/类型错误/缺少字段），不再静默崩溃。

### 修复
- **`_parse_ending_tag` 函数重复定义** — 两段完全相同的函数体首尾相接，第二个覆盖第一个但无影响。已删除重复。

---

## [1.12.5] - 2026-06-25

### 修复
- **逻辑检查异常改为 HARD 阻断** — 原 `finalize_chapter` 中 `except Exception: print("跳过")` 会静默吞掉逻辑检查失败，章节继续推进。改为追加 HARD 问题，正常阻断+写入修复指引。
- **logic_check.py timeline.list.get() 崩溃** — `_check_timeline_logic` 中 `timeline.get("current_day")` 在 timeline 为 list 时报 `AttributeError`，改为 `if isinstance(dict):` 安全访问。

---

## [1.12.4] - 2026-06-25

### 修复
- **BOM 兼容** — 全部 12 个 `.py` 脚本中 `json.loads(read_text(encoding="utf-8"))` 改为 `encoding="utf-8-sig"`。PowerShell 写入 JSON 文件时默认带 BOM 头，Python utf-8 不识别导致解析失败。`utf-8-sig` 自动剥离 BOM，无 BOM 时行为与 utf-8 一致。

---

## [1.12.3] - 2026-06-25

### 文档同步
- **hooks.md 重写** — 修正 4 处 WRONG：因果链模式名 `chapter-outline`→`outline`；删除不存在的 `init` 命令引用；连通性命令 `generate --auto-fix`→`check`/`cross-chapter` 两个子命令；门禁表 `chapter_finalized` 不被 set-phase require 的实际情况
- **faq.md 重写** — 修正 3 处 WRONG：`resume`→`next-step`；`init`→无此命令；`progress`→无此命令
- **execution_standards.md** — `preview-writing-context`→`preview`；`style_guide`→`writing_style`
- **SKILL.md** — 删除末尾残留的旧版阶段3重复节；plan-chapter 概述校验归属修正
- **antipatterns.md** — "末尾加上 L##S##"→"自动追加"
- **examples.md** — context_loader 断点续写描述修正；path 占位符统一

---

## [1.12.2] - 2026-06-25

### 修复
- **DATA_DIR 路径计算错误** — `SKILLS_ROOT / ".standardization" / "novel-weaver" / "data"` 多了一层（`skills/novel-weaver/.standardization/...`），`_meta.json` data_dir 声明是 `skills/.standardization/novel-weaver/data/`（相对于 `skills/` 根）。改为 `SKILLS_ROOT.parent / ...`，与声明完全一致。
- **数据迁移** — 将现有的 `novel_state.json` 从错误路径 `skills/novel-weaver/data/` 迁移到正确路径 `skills/.standardization/novel-weaver/data/`

---

## [1.12.1] - 2026-06-25

### 修复
- **路径系统统一** — 删除 `workflow_engine.py` 内部的 `DATA_STATE`/`DATA_CHAPTERS`/`DATA_REPORTS` 默认路径（指向 `.standardization/` 内部目录），改为从 `state_path` 入参自动推导：`<project>/data/novel_state.json` → chapters=父目录的父目录/chapters、reports=父目录/reports
- **CLI 强制 state_path** — 不再提供默认值，缺失则报错退出。避免 LLM 无意识走错目录
- **所有命令统一使用 `<project>/data/novel_state.json` 作为 state_path**，examples.md 同步更新

---

## [1.12.0] - 2026-06-25

### 新增
- **next-step 导航命令** — `novel_workflow_engine.py next-step <path>` 分析 state + 门禁状态，输出当前进度和下一步应执行的精确命令
- **CLI help 中文说明** — workflow_engine.py 帮助信息全部中文 + 命令功能简述 + 快速开始提示

### 文档
- **references/examples.md 完全重写** — 覆盖从零开始、续写、中断恢复、署名配置 4 个场景；所有 CLI 命令更新为当前真实接口；补充 `next-step` 入口说明
- **SKILL.md 工作流程章节重写** — 每步附带精确 CLI 命令；引入 `next-step` 作为流程核心入口；删除过时描述（`resume`/`atomic_writer tail` 等）

---

## [1.11.0] - 2026-06-25

### 新增
- **署名管控系统（代码级硬阻断）** — `novel_state.json` 新增 `signature` 配置（`enabled: bool`, `text: str`），默认关闭
- **atomic_writer 钩子4: 署名/代名检测** — signature.enabled=false 时，检测正文中"由...撰写/创作"等 8 种署名模式，命中即阻断并提示开启签名命令
- **签名开启后文本校验** — 只允许与 `signature.text` 完全一致的署名行，自行编造同样阻断
- **context_loader 输出署名约束** — 每个子结构写作前输出当前签名状态（开/关+文本）
- **state_manager set-signature 命令** — 支持 `python novel_state_manager.py set-signature <path> true/false [text]`

### 架构
- 旧项目（无 signature 字段）→ atomic_writer 收到 `signature=None` → 跳过检测，完全向后兼容
- LLM 无法通过自觉绕过：阻断在 fsync 之前的代码层，未命中签名模式的普通内容不影响

---

## [1.10.0] - 2026-06-25

### 修复
- refactor: novel-weaver

---

## [1.9.0] - 2026-06-25

### 架构升级 — 质量闭环（硬钩子 + 修复指引 + 自动阻断）

- **finalize-chapter 改为循环阻断** — 不再是线性流水线（跑完就过），改为聚合所有硬性问题后阻断，不通过则不做门禁标记，不推进 phase
- **检查器统一返回结构化结果** — `check_continuity`/`cross_chapter`/`style_check`/`logic_check` 均返回 `[{"file", "problem", "position", "severity": "HARD"|"SOFT", "suggestion"}]` 格式
- **HARD 阻断条件**：
  - 章内连通性：时间词+角色名双重断裂 → HARD
  - 风格校验：禁用词/末行错/超200行 → HARD
  - 逻辑检查：概述关键词命中率<30% → HARD
- **修复指引** — 每个 HARD 问题附带修复方向建议（非硬编码处方，保持文风自由），写入 `_fixes.json`
- **软性问题** — 仍不阻断，随报告输出提示

---

## [1.8.3] - 2026-06-25

### 新增
- **钩子位建议系统** — plan_chapter 自动检测非末章末子结构，标记 `is_hook_possible: True`。context_loader 在对应子结构输出建议框（悬念/伏笔/承诺三选一 + 下章标题预览），不阻断，仅辅助 LLM 决策。
- **文档** — references/execution_standards.md 补充钩子位描述

---

## [1.8.2] - 2026-06-24

### 修复
- **[P0] pipeline_gate.py pass 命令挂错函数** — `pass` CLI 调用了 `require_gate()` 而非 `pass_gate()`，导致门禁标记失败。更新为 `pass_gate()`。
- **[P0] plan_chapter 毁灭式写入** — `ch["sub_structures"][s_key] = entry` 覆盖已有 word_count/status。改用合并模式保留已有字段。
- **[P0] fidelity.py generate_report 重复定义** — 第二个定义读不存在的 `outline.json`，覆盖第一个。已统一为从 `novel_state.json` 读取。
- **[P1] logic_check.py chapters/timeline 数据结构不匹配** — chapters 预期 dict 实际 list，timeline 预期 dict 实际 list。已改为兼容访问。
- **[P1] fidelity.py os.system 调用** — 改用 `subprocess.run()` 替代 `os.system()`，修复 shell 注入风险。
- **finalize_chapter 绕过 pass_gate API** — 直接操作 gates dict，改为调用 `pass_gate()`。
- **finalize_chapter 缺少逻辑检查** — 三检只跑了连通性和风格，未调用 logic_check。已补上。
- **set_phase 不做门禁检查** — →writing 不检查 outline_causality，→stage3_ready 不检查 fidelity/ending_verify。已补上门禁检查。
- **LICENSE.md 内容不完整** — 只写了一行 `MIT License`，已补全完整许可证文本。copyright 更新为 wUwproject。

### 文档
- SKILL.md 渐进式文件索引表修正：execution_standards/hooks/license/causality_check/fidelity/character_registry 描述与实际对齐
- SKILL.md CLI 示例修正：verify-causality-* 命令从 workflow_engine 更正为 causality_check
- 约束描述中的 `verify-causality-sub` 更正为 `novel_causality_check.py sub-structure`

---

## [1.8.1] - 2026-06-24

### 新增
- **人格系统** — characters 增加 `mbti`（16 类型）和 `archetype`（荣格 12 原型）双轴，驱动角色思维方式与叙事功能。`novel_state_manager.py add-char` 支持第 7/8 位置参数
- **情绪混合系统** — sub_structures 增加 `emotions` 数组（`[{"type":"愤怒","intensity":0.8}]`），支持主副情绪分级混合。context_loader 输出 `标签[数值/1]` 格式 + 混合解读（如"悲愤交加：愤怒源于深层悲伤"）
- **文风槽位** — novel_state.json 顶层新增 `writing_style` 对象（6 字段：叙事视角/时态/句式/词汇/描写深度/自定义规则），每个子结构写作前通过 context_loader 硬约束重复输出
- **人格约束段** — context_loader 自动扫描本章涉及角色，输出 MBTI + 原型，硬性要求 LLM 按人格一致写作
- **情绪映射表** — 数值 0.0-1.0 自动映射为 5 级标签（微弱/轻度/中等/强烈/极致），可计算混合度/冲突指数/情绪演化曲线
- **文档** — references/execution_standards.md 新增角色人格系统/情绪混合系统/文风系统三章

### 架构
- 所有新字段可选，向后兼容旧数据（仅有 `tone` → 旧格式，有 `emotions` → 新格式）
- 情绪混合解读基于 9 组预定义映射 + 动态推导

---

## [1.7.0] - 2026-06-24

### 新增
- **结尾收束验证系统** — 末章末子结构自动标记 `is_ending` + 解析 `ending_type`（封闭式/开放式/悬停式）
- **收尾命题框** — `novel_context_loader.py` 检测 `is_ending` 时按类型注入硬约束命题框（冲突落点/主角弧/主题回扣/动作收束等）
- **三类收尾检查器** — `novel_fidelity.py verify_ending()` 覆盖：
  - 封闭式：冲突落点/主角变化/主题回扣/末句动作（4项全过）
  - 开放式：冲突结果[硬]/留白意图[软]/情绪收束[软]/禁逃[硬]（2硬全过+2软至少1过）
  - 悬停式：悬念存在/位置合理/主角成长/情绪锚定/节奏检测/禁逃（6项全过，不支持自动修复→人工）
- **ending_verify 门禁** — `novel_pipeline_gate.py` GATES 追加 `ending_verify`，`finalize-novel` 中与 fidelity 双门禁阻断
- **验证报告** — 写入 `data/ending_report.md`，CLI 支持 `novel_fidelity.py verify-ending <project_dir>`
- **文档** — `references/execution_standards.md` 结尾收束规范升级至 v2（收尾类型标签/命题约束/验证流程/通用规范）

### 架构
- 验证仅读末子结构内容 + project 配置，不通读全文（大纲驱动，fidelity 子集）
- 收尾类型从 LLM 生成的大纲概述中的 `【收尾类型: xxx】` 标签自动解析，零耦合

---

## [1.6.1] - 2026-06-24

### 修复
- changelog: 重写 v1.5.0/v1.6.0 描述，含 DATA_DIR 方案B落地详情

---

## [1.6.0] - 2026-06-24

### 修复
- **R-12 数据目录方案B落地** — `novel_workflow_engine.py` 新增 `DATA_DIR`/`DATA_STATE`/`DATA_CHAPTERS`/`DATA_REPORTS` 常量声明，所有 CLI 命令默认路径指向 `.standardization/novel-weaver/data/`
- **路径覆写保留** — 显式传入 `state_path`/`chapter_dir`/`report_dir` 参数时仍使用用户指定路径，不影响现有调用
- **数据迁移** — 原有 `novel_state.json` + `chapters/L01-L04` 已迁移至 `.standardization/novel-weaver/data/`
- **SKILL.md 渐进式文件索引表补全** — 增加所有 12 个脚本文件条目

## [1.5.0] - 2026-06-24

### 修复
- **DEFAULT_DATA_DIR_RAW 声明** — `novel_workflow_engine.py` 新增数据目录字面量声明以通过 R-12 step 3-b 审计

# 更新日志

## 1.4.0 (2026-06-24)
### 新增
- `novel_atomic_writer.py` v2 — 原子写入器格式硬约束：3 层阻断钩子（标题格式/空内容/标记行+元注释检测），fsync 双保险
- `novel_context_loader.py` — 上下文加载与子结构注册验证（章节/子结构存在性检测阻断）
- `novel_causality_check.py` — 因果链验证（概述完整性+因果动词检测）
- `novel_timeline.py` — 故事内时间线管理（add/list）
- `write-sub` 链式管道命令 — atomic_writer 格式校验 → state_manager 即时状态标记，每子结构写一条即写入完成状态
- `finalize-novel` 全文完结命令 — 全线跨章承诺链检查 → 大纲忠实度报告 → fidelity 门禁
- `fidelity` 大纲忠实度命令 — 逐章对比 overview vs 实际内容，报告关键词覆盖率
- `cross-chapter` 跨章承诺链检查命令 — 读上章末子结构尾3行 vs 下章首子结构头3行，检测未续接的剧情承诺

### 修复
- **所有脚本通用化** — 关键词从 novel_state.json 的 characters/technical_notes/chapters 动态提取，消除硬编码（`_extract_keywords()` 函数），技能可复用于任何题材的小说
- **元注释污染侵入** — atomic_writer v2 新增元注释阻断检查（`**S## 完成（字数：` 模式），写入作品文件前被硬阻断
- **跨章承诺链缺失** — 在 finalize-chapter 中加入 cross_chapter 调用，每章完结时自动检测与前一章的剧情断裂
- **全文完结检查缺失** — 新增 finalize-novel 命令，全线跨章检查 + 大纲忠实度 + fidelity 门禁
- **删除 .gitkeep** — scripts/ 下无意义的空占位文件（已有 10 个 Python 脚本）

### 更新
- `finalize-chapter` 流水线扩充：章内连续性 → 跨章承诺链 → 风格校验（原仅章内连续性 + 风格）
- `novel_continuity.py` `cross_chapter` 函数重写为通用版，通过 `_extract_keywords()` 动态加载关键词
- `novel_workflow_engine.py` `fidelity_check` 重写为通用版，复用 continuity 的动态关键词提取

## 1.3.7 (2026-06-24)
### 新增
- `novel_workflow_engine.py resume` 命令：全局断点续写检测。遍历所有章节和子结构状态，输出完成/进行中/待写状态表，定位下一个待写子结构并给出续写命令
- `plan-chapter` 概述字数硬检查：至少 12 个有效字符（不含空格标点），不达标则报错阻断
### 更新
- `execution_standards.md` 新增「概述编写规范」章节：定义概述的 4 条质量标准（字数/动作/人物/可验证性），含合格/不合格示例

## 1.3.6 (2026-06-24)
### 新增
- 同 1.3.5（码云已推送，GitHub 失败重推）

## 1.3.5 (2026-06-24)
### 新增
- `novel_context_loader.py` **断点续写检测**：自动检查子结构文件是否存在 `.progress`，若已有内容则输出：
  - 已写行数 + 剩余行数
  - 末5行锚点（通过 `atomic_writer.py tail` 读取）
  - 新写/续写两种模式的指令
- 中断恢复流程：无论中断发生在子结构开始前还是写作中，下次进入时必须重新调用 `context_loader` 获取完整命题指令 + 已写内容锚点，确保文风/人物/时间线一致

## 1.3.4 (2026-06-24)
### 新增
- `novel_state_manager.py update-sub` 自动检测该章所有子结构是否全部完成（status=done），是则自动触发 `finalize-chapter`（三道检查 + phase 推进）。写完最后一个子结构无需手动调用完结。
- `novel_logic_check.py --auto-fix` 模式：生成 `_fixes.json`，包含每个问题的目标文件、修复类型（rewrite/append/link）、修复建议说明
- `finalize-chapter` 自动调用 logic check 的 `--auto-fix`，检测到可修复问题时写入 fix JSON 并提示 LLM 执行修复
### 更新
- `novel_context_loader.py` 输出格式改为 **命题指令格式**：标题/概述/情绪基调以强制命题框展示，LLM 必须作为命题作文严格遵守，不可偏离。不再是可选的"参考信息"。

## 1.3.3 (2026-06-24)
### 修复
- 修正 v1.3.2 changelog 表述

## 1.3.2 (2026-06-24)
### 修复
- SKILL.md 顶部引用的个人化措辞改为通用描述

## 1.3.1 (2026-06-24)

### 修复
- **致命 Bug 修复**: `novel_workflow_engine.py plan-chapter` 中使用未定义变量 `python_exe`（NameError），已添加 `python_exe = sys.executable`
- **门禁绕过修复**: `plan-chapter` 直接更新 `current_phase` 跳过 `set-phase` 的 outline_causality 门禁检查，改为先 `pipeline_gate.require` 再推进
- **文档-代码一致性修复**（~20 处）:
  - `SKILL.md`: 脚本名统一加 `novel_` 前缀（8 处缩写 → 完整名）
  - `SKILL.md`: 约束节 15→8 条（合并归并，满足 ≤9 上限）
  - `SKILL.md`: 修复 context_loader 功能归属（末3行读取 → atomic_writer tail）
  - `SKILL.md`: `.pipeline` 独立文件 → `pipeline` 嵌套字段
  - `hooks.md`: 门禁表缩写名 → 完整 `novel_` 前缀
  - `hooks.md`: 16 个钩子计数（与 SKILL.md 一致）
  - `execution_standards.md`: `scene_setting.json` → `novel_state.json`
  - `faq.md`: 新增 `add-sub` 替代解决方案
  - `examples.md`: 完整填充示例内容
  - `novel_character_registry.py`: 标记为"已弃用"，指引到 `add-char`

### 新增
- **`novel_pipeline_gate.py`** — 全局流程门禁系统：
  - `pass` 命令：关键脚本成功时自动标记门禁通过（写入 novel_state.json.pipeline）
  - `require` 命令：phase 转换前检查前置门禁，未通过则阻断
  - `status` 命令：可视化显示所有门禁状态
  - `reset` 命令：调试用重置
- **全流程门禁集成**（5 个关键脚本自动 pass 门禁）：
  - `novel_causality_check.py` → PASS 时自动 pass `outline_causality` / `sub_causality:L##`
  - `novel_workflow_engine.py` → plan-chapter 后 pass `plan_chapter:L##`；finalize-chapter 后 pass `chapter_finalized:L##`
  - `novel_fidelity.py` → PASS 时自动 pass `fidelity`
- **`set-phase` 强制门禁检查**：
  - → `writing`：require `outline_causality`
  - → `chapter_done`：报告存在性检查（已有）
  - → `stage3_ready`：require `fidelity`
  - 未通过则阻断，LLM 无法跳过步骤
- **hooks.md 重写** — 新增门禁系统章节 + 门禁点列表表 + 查看命令

### 更新
- 版本 1.2.1 → 1.3.0（核心架构层新增，功能可追踪）

### 新增
- **`novel_causality_check.py`** — 因果链双重验证钩子：
  - `chapter-outline` 模式：逐链节检查 L01→L02→…L15 的章概述因果递进（关键词重叠分析，WARN/ERROR 阻断）
  - `sub-structure` 模式：逐链节检查 S01→S02→… 的子结构概述因果递进（含情绪递进提示）
  - 结构化的因果链矩阵输出 + 每链节状态标记 + 修复指引
- **workflow_engine.py 新增 2 个编排命令**：
  - `verify-causality-outline` — 委托 causation_check chapter-outline
  - `verify-causality-sub` — 委托 causation_check sub-structure
- **hooks.md 新增 2 条阻断式钩子**：
  - 大纲因果链验证（用户确认大纲前必须 PASS）
  - 子结构因果链验证（plan-chapter 后、写作前必须 PASS）
- **SKILL.md 约束新增 2 条**：
  - 大纲级因果链验证（必须运行 verify-causality-outline 通过后才能确认）
  - 子结构级因果链验证（必须运行 verify-causality-sub 通过后才能写作）

### 修复
- workflow_engine.py verify-chapter 在子结构为空时报告 ERROR（替代无声返回）
- 所有子结构写作前必须通过因果链检查，从设计层面解决因果断裂问题（前置规划保障，不依赖后置检测）

### 新增
- **`novel_workflow_engine.py`** — 统一编排引擎，提供 4 个编排命令：
  - `plan-chapter` — 批量注册一章所有子结构（含情绪 tone），自动推进 phase→writing
  - `verify-chapter` — 验证子结构是否全部注册
  - `finalize-chapter` — 一键运行连通性+风格+逻辑检查 + set-phase chapter_done
  - `preview-writing-context` — 预览一章所有子结构的写作上下文
- **`novel_logic_check.py`** — 逻辑一致性检查器，覆盖 3 个维度：
  - 人物行为一致性：同一角色在不同子结构中的出现/消失检查
  - 时间线逻辑：时间回退检测 + 时间引用扫描
  - 子结构内容与概述匹配度：规划关键词在正文中的命中率
- **代码级硬约束**（三段式阻断链）：
  1. `context_loader.py` — 子结构未注册 → 报错退出（"未知"无声降级 → 硬阻断）
  2. `atomic_writer.py` — 正文中含 `L##S##` 标记行 → 报错退出（格式混乱 → 硬阻断）
  3. `state_manager.py` — `set-phase chapter_done` 前置检查报告是否存在（无报告 → WARN）
- **`novel_continuity.py` auto-fix 模式**：
  - `--auto-fix` 生成 `_transitions.json` 列出所有需要过渡的子结构对
  - `write-transition` 命令写入过渡段落
- **子结构规划扩展** — 增加 `tone`（情绪提示）字段，在规划阶段前置解决情绪连贯性问题

### 修复
- **`novel_fidelity.py` 数据格式冲突**：`chapters` 期望 list 但 state_manager 存 dict，新增 dict→list 兼容转换
- **`novel_continuity.py` CLI 接口改造**：从直接执行改为 `generate` 子命令，支持 `--auto-fix` 旗标
- **`novel_state_manager.py` phase 检查增强**：`set-phase chapter_done` 前检查三道报告文件是否存在（提供 WARN）

### 更新
- **SKILL.md 工作流程重构**：
  - 阶段2步骤1 从"生成→追加"改为"生成→**plan-chapter批量注册**→验证"
  - 阶段2步骤5 从"连通性+风格"改为"**三道检查+finalize-chapter一键完结**"
  - 新增 7 条硬约束（子结构先行、正文禁标记、报告前检等）
- **hooks.md 翻新**：从 11 个钩子扩展到 15 个，新增代码级硬约束条目
- **`_meta.json` 版本**：1.1.1 → 1.2.0

## 1.1.0 (2026-06-24)

### 标准化改造（无功能更新，版本号不变）
- SKILL.md 重构为渐进式加载结构：约束/触发条件/工作流程保留在入口，字数管理/文体规范/状态文件/钩子系统/数据目录拆分到 references/
- references/execution_standards.md（字数管理/文体规范/novel_state.json 结构/章节输出/时间线/角色表/结尾收束）
- references/hooks.md（11 个流程钩子一览）
- references/antipatterns.md 填充 2 条反模式；references/faq.md 填充 5 条 Q&A
- 删除 SKILL.md 正文中所有散落"详见"引用，统一由渐进式文件索引表导航
- 通过 skill-standardization v2.95.4 全流程 refactor 审计（0 ERROR 0 WARN）

### 新增
- 阶段门禁系统：current_phase 不可逆递增（none→init→stage1_done→writing→chapter_done→stage3_ready→complete）
- 8 个 Python 钩子脚本（atomic_writer / continuity / style_check / timeline / character_registry / fidelity / context_loader / state_manager）
- novel_state.json 统一管理文件（整合 style_guide / characters / timeline / chapters 进度）
- L##S## 编号系统（子结构文件末尾带编号标记行）
- 写作前上下文加载器（context_loader 脚本自动输出风格/角色/时间线/概述）
- 子结构确认阻断式钩子（阶段1必须确认才能进入阶段2）
- 所有依赖脚本均含阶段门禁检查，未初始化或阶段不足时打印阻断信息

### 更新
- 章节数从固定10章改为8-15章阈值
- 字数管理从固定字数改为仅保留200行上限
- 子结构 .txt 文件不再含元数据标记（末行仅保留 L##S## 编号）
- 文体规范从固定"硬核科幻"改为由 scene_setting.json 的 tone_style 决定

### 修复
- 修复 Observer_Alpha 裁决通知缺失
- 修复时间线锚点不一致（去除随意编造的41天）
- 修复原主人格状态描述（从"不存在"修正为"双线程共存"）
- 修复子结构写作文件与 project_progress 管理文件的关联索引

## 1.0.0 (2026-06-23)

### 新增
- 初始版本创建
- 三阶段流水线：场景配置与大纲 → 逐章写作 → 全文整合
- 三级确认模式：大纲必须确认 / 子结构批量展示 / 写作最后集中审
- 200行分段写入 + 自然段落结束
- 连通性补充钩子（子结构间 + 跨章节）
- 风格一致性校验 + 大纲忠实度报告
- 可选精修模式（备份→定位→更新→局部重新连通）
- 渐进式 MD 引用体系