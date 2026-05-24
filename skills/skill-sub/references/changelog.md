# skill-sub 版本更新日志

---

## v1.12.0（2026-05-24）

**发布日期：2026-05-24**
**类型：Patch（修复 R-16 WARN + 版本 bump）**

### 修复
- **R-16 WARN**：`references/reference.md` 末尾追加"权限权重说明（R-16）"章节
  - 脚本权限分析表格（4个脚本 × 5个维度）
  - 授权方式说明（低/中/高权重对应静默/统一/即时）
  - 风险缓解措施
- **版本号统一**：`SKILL.md` / `_meta.json`：`1.11.0` → `1.12.0`

### 影响
- `skill_audit` 审查 `skill-sub` 时 R-16 将通过 ✅
- 权限权重透明化，便于安全审查

---

## v1.11.0（2026-05-23）

**改写类型：文档质量优化**

### 新增

- `references/faq.md` — 5条反模式（附正确做法）+ 6个FAQ + 使用技巧
- `references/examples.md` 末尾追加「使用技巧」章节（命名建议、里程碑设置经验、生命周期管理）

### 优化

- SKILL.md「不是什么」→「能力边界」：能做/不能做/不适合用 三档，新增3条不适合场景
- SKILL.md「触发方式」精确化：自动推荐改为表格（3种触发条件+示例）
- 渐进式加载表：新增 faq.md 映射行

### 变更文件

| 文件 | 变更 |
|------|------|
| `SKILL.md` | 能力边界重构、触发条件表格化、FAQ引用行、版本 1.10.1→1.11.0（197行，≤200）|
| `_meta.json` | version 1.10.1→1.11.0 |
| `references/faq.md` | **新建**（~130行）|
| `references/examples.md` | 末尾追加使用技巧（+28行）|
| `references/changelog.md` | 本条记录 |

---

## v1.10.1（2026-05-23）

**改写类型：Bug修复 + 版本号同步**

### 修复

- `chain_manager.py` `classify_milestones()` 中 `depends_on: null`（JSON null）导致 `TypeError: 'NoneType' object is not iterable`。修复：所有 `step.get("depends_on", [])` 改为 `(step.get("depends_on") or [])`，覆盖7处调用
- `SKILL.md` 第12行标题 `v1.9.0` 与 frontmatter `version: 1.10.0` 不一致，修正为 `v1.10.1`

### 变更

- `chain_manager.py` — 7处 `depends_on` 取值逻辑修复
- `SKILL.md` v1.10.0 → v1.10.1
- `_meta.json` v1.10.0 → v1.10.1

---

## v1.10.0（2026-05-23）

**改写类型：配合 skill-standardization v2.12.0 路径规范升级**

### 变更内容

- 产出物路径统一至 `skills/.standardization/skill-sub/` 下
- 配合 skill-standardization v2.12.0 路径规范升级，同步版本号

---

## v1.9.1（2026-05-23）

**改写类型：修正 _meta.json tags 残留**

### 变更内容

- `_meta.json` tags 中残留 `"reusable-template"`，修正为 `"reusable"`
- `SKILL.md` 大标题 `v1.7.0` 残留，修正为 `v1.9.1`

---

## v1.9.0（2026-05-23）

**改写类型：修复 cmd_create 双次保存问题**

### 变更内容

#### `scripts/chain_manager.py` — `cmd_create` 逻辑修复
- **问题**：原逻辑先 `save_chain`（含默认 `is_milestone=False`），再做里程碑分类，然后第二次 `save_chain` 覆盖
- **修复**：里程碑分类在首次 `save_chain` **之前**完成，合并为**一次保存**
- 修复后行为：步骤数据 + 里程碑标记在一次原子保存中完成

#### 验证
- 单次 `create` 后 `list` / `show` 均能正确读取数据
- 短链（≤2步）里程碑判断正确
- 含关键词步骤（"部署"、"推送"等）里程碑标记正确

---


## v1.8.0（2026-05-23）

**改写类型：修正"模板"错误描述 + 调用链真正保存**

### 变更内容

#### SKILL.md 描述修正
- 删除所有"模板"错误描述（调用链就是调用链，不是模板）
- 副标题：`拼接为可复用模板` → `拼接为调用链`
- 角色描述：`通用调用链模板` → `调用链`
- `tags`：`"reusable-template"` → `"reusable"`

#### _meta.json 同步
- `tags` 字段同步修正：`"reusable-template"` → `"reusable"`

#### 调用链真正保存
- 使用 `chain_manager.py create` 真正保存调用链 `skill-standardization-refactor`
- 之前只是往 `examples.md` 瞎写内容，未真正保存

#### examples.md 清理
- 删除瞎写的"示例 6"（"通用调用链模板"错误内容）
- 示例 4 标题/描述修正：`生成通用调用链模板` → `摘取步骤形成调用链`

### 技术细节

| 项目 | v1.7.0 | v1.8.0 |
|------|--------|--------|
| SKILL.md "模板"关键词 | 有（多处） | 无 ✅ |
| _meta.json tags | `"reusable-template"` | `"reusable"` ✅ |
| 调用链真正保存 | 否（只写在 examples.md） | 是（`chain_manager.py`）✅ |

---

## v1.7.0（2026-05-23）

**改写类型：修正 SKILL.md 标题/副标题描述**

### 变更内容

#### SKILL.md 标题修正
- 一级标题：`# skill-sub v1.6.0（渐进式加载示范）` → `# skill-sub v1.7.0`
- 副标题：移除"本文档示范渐进式 MD……"示范用语
- 副标题改为真实描述（从 `description` 字段提炼）

#### 版本号同步
- SKILL.md `version:` `1.6.0` → `1.7.0`
- `_meta.json` `"version"` `1.6.0` → `1.7.0`

---

## v1.6.0（2026-05-23）

**改写类型：补充 skill-sub 三角色定位 + 完善原有功能描述**

### 变更内容

1. **补充「三个角色」核心定位**（之前缺失）
   - **调用链编辑器** — 创建、编辑、保存、删除、列出调用链
   - **粗粒度规划器** — 理解用户意图，规划哪些 Skill 参与、执行顺序、依赖关系
   - **编排器** — 将规划结果拼接为调用链 JSON，本身不参与执行

2. **完善触发方式 — 意图自动匹配推荐**
   - 之前只有一句描述，现补充：匹配条件（`tags`/`description`/`user_intent` 重合度 > 50%）、
     匹配后行为（推荐给用户选择执行或编辑）

3. **完善工作流程 — 补全调用链管理操作**
   - 新增「编辑器角色」段落：新建（三阶段）→ 编辑（`add-step`/`remove-step`/`update-step`/`rename`）→ 管理（`list`/`show`/`delete`）
   - 之前这些 CLI 命令只在「快速开始」里列了，工作流程图里完全没体现

4. **升级版本号**
   - SKILL.md `version`：1.5.0 → 1.6.0
   - `_meta.json` `"version"`：1.5.0 → 1.6.0
   - `description` 更新为"skill-sub 调用链编辑器与粗粒度规划器"
   - `tags` 新增 `"planner"`、`"editor"`
   - `references/changelog.md` 补充本条目

5. **渐进式 MD 文件体系表格更新**
   - 本文件（SKILL.md）包含：新增「三角色定位」
   - `references/examples.md` 说明更新：补充编辑场景、意图推荐场景示例

---

## v1.5.0（2026-05-23）

**改写类型：补充阶段1「两个理解」逻辑**

### 变更内容

1. **阶段1 重写：明确「两个理解」缺一不可**
   - **理解①：用户要做什么** — 提取任务类型、预期产物、关键约束；判断是一次性的还是可复用的
   - **理解②：Skill 能做什么** — 明确 Skill 的能力边界，是摘取步骤的前提
   - 两个理解都完成，才能做好调用链

2. **明确 Skill 来源规则**
   - 用户明确指定了 Skill → 直接从用户给的列表操作，**不额外遍历**
   - 用户未指定 Skill → 从本地 skill 库（`~/.workbuddy/skills/` + `{workspace}/.workbuddy/skills/`）遍历挑选
   - 挑选依据：`description` 字段、`tags` 字段、用户描述关键词

3. **升级版本号**
   - SKILL.md `version`：1.4.0 → 1.5.0
   - `_meta.json` `"version"`：1.4.0 → 1.5.0
   - `references/changelog.md` 补充本条目

4. **同步更新工作流程流程图**
   - 阶段1 描述从「识别涉及哪些 Skill」改为「两个理解」

---

## v1.4.0（2026-05-23）

**改写类型：补充调用链生成逻辑三阶段定义**

### 变更内容

1. **明确定义调用链生成三阶段**（核心补充）
   - **阶段1：理解** — AI 理解用户自然语言描述，识别涉及 Skill、执行顺序、依赖关系、里程碑步骤
   - **阶段2：摘取** — 按顺序从各 Skill SKILL.md 摘取关键步骤（`skill_extractor.py` 或手工读取）
   - **阶段3：拼接** — 将摘取结果合成为调用链 JSON，调用 `chain_manager.py create` 保存

2. **修正调用链生成逻辑描述**（之前过于简略）
   - 明确：不是让 AI 自由发挥，而是"理解→摘取→拼接"确定性流程
   - 补充摘取方式表格（skill_extractor.py vs 手工读取，择优使用）
   - 补充拼接规则（Chain 级字段来源、Step 级字段来源）

3. **升级版本号**
   - SKILL.md `version`: 1.3.0 → 1.4.0
   - `_meta.json` `"version"`: 1.3.0 → 1.4.0
   - `references/changelog.md` 补充本条目

4. **SKILL.md 行数控制**
   - 三阶段详细表格和示例移入 `references/workflow.md`
   - 最终 SKILL.md：**197行**（符合 ≤200 行规范）

---

## v1.3.0（2026-05-23）

**改写类型：结构标准化 + 渐进式加载改造**

### 变更内容

1. **补写 YAML frontmatter**（R-01~R-04 修复）
   - 新增 `name: skill-sub`
   - 新增 `version: 1.3.0`
   - 新增 `author: [username-redacted]`
   - 新增 `license: MIT`
   - 新增 `description`
   - 新增 `tags`（含 `"progressive-loading"`）

2. **SKILL.md 从 509行压缩到 152行**（R-06 规范，≤200行）

3. **建立渐进式 MD 文件体系**
   - 新建 `references/workflow.md` — 详细执行流程、里程碑规则、设置界面
   - 新建 `references/reference.md` — 完整 CLI 速查、脚本清单、存储格式、流程图
   - 新建 `references/chain_schema.md` — Chain/Step/retry_policy/failure_mode 结构定义
   - 新建 `references/examples.md` — 完整使用示例集合
   - 新建 `references/changelog.md` — 本文件

4. **明确定位**（核心修正）
   - 在 SKILL.md 中新增「skill-sub 的定位」章节
   - 明确：skill-sub **不参与调用链**，只负责**生成通用调用链模板**
   - 调用链模板可复用，不绑定单次任务产物

5. **新增工作流程章节**（R-09 修复）
   - 新增 `## 工作流程` 章节，描述 AI 执行节奏

6. **新增审查规则自查表**（R-10 修复）
   - 新增 R-01~R-10 自查表格，确认本 skill 自身符合规范

7. **同步版本号**
   - `_meta.json` `"version"` 同步升级至 `1.3.0`

---

## v1.2.1（2026-05-21）

- 新增 HTML 设置界面（settings.py）
- 新增 `config.json` 用户配置支持
- 完善 CLI 速查表
- 修复里程碑判断逻辑

---

## v1.2.0（2026-05-20）

- 新增"意图关键词自动匹配"触发方式
- 新增 `skill_extractor.py` 脚本（从 SKILL.md 提取关键步骤）
- 完善三层回退执行策略
- 新增分级重试策略（file_locked/network_error/timeout/auth_error）

---

## v1.1.0（2026-05-18）

- 新增里程碑通用判断规则（自动判断 + 关键词匹配）
- 新增 `chain_executor.py` 执行引擎
- 支持调用链 CRUD 完整操作
- 新增环境变量配置（SKILL_SUB_HOME 等）

---

## v1.0.0（2026-05-15）

- 初始版本
- 支持创建、执行、调整、删除调用链
- 基础重试策略和失败处理模式
- `chain_manager.py` 基础 CRUD 功能
