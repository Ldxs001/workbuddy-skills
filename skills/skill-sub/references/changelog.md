## v1.22.0 (2026-05-26)

### 面向对象（OO）改造
- **chain_executor.py** — 全面 OO 改造，拆分为 7 个类：
  - `Config` — 配置管理（加载默认配置 + 用户配置合并）
  - `PathManager` — 路径管理（技能目录、调用链目录、技能查找）
  - `Validator` — 验证器（里程碑判断、retry_policy/failure_mode 验证）
  - `TopoSorter` — 拓扑排序器（子步骤依赖排序、递归处理 loop/branch）
  - `ExecutionPlanBuilder` — 执行计划构建器（构建执行计划、收集技能名称、生成 AI 指令）
  - `InstructionGenerator` — AI 指令生成器（独立类，处理 loop/branch 步骤的指令渲染）
  - `CLIHandler` — CLI 处理器（plan/quick/validate 命令处理）
- **chain_manager.py** — 全面 OO 改造，拆分为 7 个类：
  - `ConfigManager` — 配置管理器（加载/保存用户配置）
  - `PathManager` — 路径管理器（调用链目录、索引文件、技能目录、状态/日志目录）
  - `ChainValidator` — 调用链验证器（里程碑判断、调用链数据验证）
  - `BackupManager` — 备份管理器（自动备份、备份列表、备份恢复）
  - `ChainManager` — 调用链管理器（加载/保存索引、加载/保存/删除调用链、列表）
  - `ChainEditor` — 调用链编辑器（创建/更新/删除调用链、添加/删除步骤）
  - `CLIHandler` — CLI 命令处理器（init/create/list/show 命令处理）
- **可维护性提升** — 原 1000+ 行函数式代码拆分为职责单一的类方法，便于单元测试和后续扩展
- **SKILL.md 更新** — 修正快速开始代码块中的文件名引用（`chain_manager_oo.py` → `chain_manager.py`、`chain_executor_oo.py` → `chain_executor.py`）

---

## v1.21.0 (2026-05-26)

### 新增功能（build_execution_plan 子步骤处理）
- **子步骤拓扑排序** — `_topo_sort_substeps(steps)` 递归对 loop/branch 内的子步骤按 depends_on 依赖关系进行拓扑排序，替代原来的数组顺序执行
- **递归步骤计数** — `_count_all_steps(steps)` 递归统计所有步骤数（含 loop 子步骤 for_each 迭代次数、while 预估、branch 最大分支），total_steps 计算现在准确
- **build_execution_plan() 接入** — 在生成执行计划时自动对 loop/branch 子步骤进行拓扑排序，并调用 _count_all_steps() 计算准确的 total_steps

---

### 修复

---

# skill-sub 更新日志
## v1.20.0 (2026-05-26)

### 新增功能（高级编排）
- **循环步骤（Loop Step）** — `type: "loop"` 支持 `for_each` / `while` 两种模式，可嵌套子步骤
- **分支步骤（Branch Step）** — `type: "branch"` 支持 `if_steps` / `else_steps` 条件分支，可嵌套子步骤
- **递归渲染引擎** — `loop_branch_renderer.py` 独立模块，支持 `skill` / `loop` / `branch` 步骤的递归 AI 指令渲染
- **`chain_schema.md` 扩展** — 新增 `type` 字段定义，支持三种步骤类型及其子结构（`loop.*` / `branch.*`）
- **`chain_executor.py` 接入** — `generate_ai_instructions()` 改为调用 `render_plan_with_loop_branch()`，完整支持循环/分支渲染

---

### 修复
- `calc_intent_similarity()` 分词 bug：`chain_words` 未做 `re.findall` 分词导致永远匹配不上；加入 `user_intent` 字段参与相似度计算
- `cmd_error_stats()` 日志目录路径错误：`log_dir` 手工拼路径改为使用 `LOGS_DIR`；文件读取改 `with open()` 上下文管理器

---

## v1.19.1 (2026-05-25)

### 修复（v1.19.0 虚假 DONE 项实际实现）
- 里程碑影响分析（milestones）— 真正实现并注册到 parser
- 动态里程碑（--dynamic）— 真正实现并注册到 parser
- 里程碑统计（milestone-stats）— 真正实现并注册到 parser
- 标签系统增强（list-tags）— 真正实现并注册到 parser
- v1.19.0 仅标记 DONE 但未实现上述四项，v1.19.1 修复

---

## v1.19.0 (2026-05-24)

### 新增功能
- 链标签系统增强（Chain Tag System Enhancement）— `list-tags`
- 链导入/导出（Chain Import/Export）— `import` / `export`
- 步骤摘取器：参数提取（Parameter Extraction）
- 步骤摘取器：兼容性检查（Compatibility Check）
- 执行计划生成器：资源分析（Resource Analysis）
