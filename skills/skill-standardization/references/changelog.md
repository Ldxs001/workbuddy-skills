# 更新日志（Changelog）

> 本文件记录 skill-standardization 的版本变更历史。
> 遵循 [Keep a Changelog](https://keepachangelog.com/) 格式，基于 SemVer 版本管理。

---

## 目录

- [v2.3.0（当前版本）](#230-当前版本)
- [v2.1.0](#210)
- [v2.0.1](#201)
- [v2.0.0（重大升级）](#200-重大升级)
- [v1.0.0（初始版本）](#100-初始版本)

---

### v2.3.0（当前版本）

**发布日期：2026-05-23**
**类型：Minor（Bug 修复 + 版本号同步）**

### 新增/修正内容

#### Bug 修复
- `scripts/skill_audit.py`：修复 `yaml_has_description` 在 `fm=None` 时崩溃的问题（`AttributeError: 'NoneType' object has no attribute 'get'`）
  - 根因：`fm` 为 `None` 时直接调用 `fm.get()`
  - 修复：增加 `if has_desc else ""` 守卫

#### 版本号同步
- `scripts/skill_audit.py` 文件头 `v2.2.0` → `v2.3.0`
- `scripts/skill_builder.py` 文件头 `v2.1.0` → `v2.3.0`（之前遗漏未同步）
- SKILL.md `version:` `2.2.0` → `2.3.0`
- `_meta.json` `"version"` `2.2.0` → `2.3.0`

#### SKILL.md 行数控制
- 精简空行，将文件控制在 200 行以内（R-04 渐进式要求）

### 技术细节

| 项目 | v2.2.0 | v2.3.0 |
|------|--------|--------|
| SKILL.md 行数 | 188~203 行（波动） | 200 行（≤200 ✅） |
| skill_audit.py bug | 有（fm=None 崩溃） | 已修复 ✅ |
| skill_builder.py 版本字符串 | v2.1.0（遗漏） | v2.3.0（同步）✅ |

---

## v2.2.0

**发布日期：2026-05-23**
**类型：Minor（功能增强 + 规范完善）**

### 新增/修正内容

#### SKILL.md 结构完善
- 补充 `## 工作流程` 章节（含 AI 执行节奏流程图 + 三模式对照表），R-09 修正为 ✅
- 一级标题加入"渐进式加载示范"语义
- description 更新，体现渐进式加载特性
- tags 新增 `"progressive-loading"`

#### 版本号管理规范化
- **版本号更新文件映射表彻底重做** — 原表只覆盖 SKILL.md/_meta.json/manifest.json，严重不完整
- 新映射表覆盖所有含版本号位置：SKILL.md `version:`、`_meta.json` `"version"`、`scripts/spec/*.json` `"_version"`、`scripts/*.py` 文件头版本字符串
- **铁律 2 重写** — 原规则"不确定就问"与更新器/修改器逻辑冲突，按用户要求改为：
  - 规范内明确定义的文件/字段 → **直接更新，无需询问**
  - 规范未覆盖的文件/字段 → **必须询问用户**

#### 脚本版本号同步
- `scripts/skill_audit.py` 文件头 `v1.0.0` → `v2.2.0`
- `scripts/skill_builder.py` 文件头 `v1.0` → `v2.2.0`

#### 渐进式 MD 体系示范
- SKILL.md 缩减至 188 行（≤200），超标内容拆分至 `references/`
- 移除 `## 版本更新日志`（已拆分至 `references/changelog.md`）
- 新增"本 skill 自身的文件拆分示范"表格
- 所有详细内容正确指向 `references/*.md`

### 技术细节

| 项目 | v2.1.0 | v2.2.0 |
|------|--------|--------|
| SKILL.md 行数 | ~230 行（超标） | 188 行（≤200 ✅） |
| R-09 通过 | ❌ | ✅ |
| 版本号映射覆盖 | 3 个文件 | 全链路（SKILL.md + _meta + spec/*.json + *.py） |
| 铁律 2 逻辑 | "不确定就问"（有误） | "规范内有规定直接更新，无规定必须询问" |

---

## v2.1.0

**发布日期：2026-05-22**
**类型：Minor（功能增强）**

### 新增功能

#### skill_audit.py 独立副本
- skill-standardization 现在包含**自有**的 `skill_audit.py` 副本（522行）
- 与 git-sync 的审查脚本**完全隔离**，各自维护各自的生命周期
- 消除了"与 git-sync 共享"的跨 skill 依赖
- 支持独立执行：`python scripts/skill_audit.py audit <skill_dir>`

### 变更内容

#### Skill 隔离化
- SKILL.md 移除"与 git-sync 共享"措辞，明确各 skill 脚本独立性
- 规范文件结构说明更新，标注 skill_audit.py 为 `[v2.1新增]`

### 技术细节

| 项目 | v2.0.1 | v2.1.0 |
|------|--------|--------|
| 脚本数量 | 3 (builder + json_loader) | 4 (+audit 独立副本) |
| 跨 skill 依赖 | 有 (audit 来自 git-sync) | 无 (完全自包含) |

---

## v2.0.1

**发布日期：2026-05-22**
**类型：Patch（修复）**

### 变更内容

#### 目录重命名
- `docs/` → `references/` — 对齐标准规范中的渐进式 MD 目录命名
- 更新所有内部引用路径

---

## v2.0.0（重大升级）

**发布日期：2026-05-22**
**类型：Major（重大升级）**

### 新增功能

#### skill_builder.py 构建器
- **create 命令** — 从模板初始化完全符合标准的 skill 目录结构
  - 自动生成 SKILL.md（含 frontmatter + TODO 占位符模板）
  - 自动生成 _meta.json（五字段标准元数据）
  - 创建 references/ 和 scripts/ 占位目录
  - 支持 `--desc`、`--dir`、`--tags` 参数自定义

- **update 命令** — 对已有 skill 进行增量规范化检查
  - 检查 _meta.json 存在性和字段完整性（可自动修复）
  - 检查 SKILL.md frontmatter 和必填章节
  - 文件大小合理性提示（>200 行建议拆分）
  - 根目录规范性检查
  - 支持 `--fix` 自动修复和 `--backup` 备份

- **refactor 命令** — 非标 skill 整体结构改造
  - 全量扫描文件生成清单（路径+大小+时间）
  - 按 M-01~M-06 规则自动归类移动文件
  - 强制备份机制（时间戳命名）
  - 信息零丢失验证（字节一致性检查，允许 1% 容差）
  - 完整迁移映射表输出
  - 支持 `--dry-run` 预览模式

#### 标准目录结构规范
- 新增 `spec/structure.json` — 目录结构规范定义
- 定义三级复杂度模型（minimal / standard / full）
- 明确根目录仅允许 SKILL.md + _meta.json
- 规范子目录用途：references/（渐进式MD）、scripts/（脚本）、assets/（资源）、tests/（测试）

#### 渐进式 MD 文件体系
- 新增 `spec/progressive_md.json` — 渐进式MD体系规范
- 定义主文件 vs 辅助文档的拆分边界
- 明确加载协议（SKILL.md 独立可用 → 复杂任务按需加载 references/）
- 标准化引用语法（→ 语法指向渐进式文件）
- 注册 6 个标准渐进式文件名

#### spec/_index.json 模块索引
- 新增集中式模块注册表
- 支持依赖声明（_depends_on）
- 统一版本号管理（_version）
- 为 json_loader.py 提供模块发现能力

### 变更内容

#### 审查策略升级
- **git-sync 集成模式变更**: ERROR 级问题不再导致 exit(1)
- **纯警告模式**: skill_audit.py 始终返回退出码 0
- **不阻断同步**: git-sync 收到退出码 0 后继续执行后续步骤
- **向后兼容**: 保留 --strict 参数支持严格模式（可选）

#### SKILL.md 结构重构
- 主文件从单一大文档精简为 ≤200 行核心版
- 详细内容拆分到 references/ 渐进式 MD 文件
- 新增三种执行模式详解章节（create/update/refactor）
- 新增标准目录结构规范章节
- 新增渐进式 MD 文件体系章节
- 新增规范文件结构说明章节

### 技术细节

| 项目 | v1.0 | v2.0 |
|------|------|------|
| 脚本数量 | 2 (audit + json_loader) | 4 (audit + json_loader + builder) |
| Spec 文件数 | 3 (frontmatter + body + rules) | 6 (+ structure + progressive_md + _index) |
| CLI 命令数 | 2 (audit + load/list/show) | 8 (create/update/refactor + audit + load/list/show/refs) |
| 文档文件数 | 1 (SKILL.md) | 7 (SKILL.md + 6个references/*.md) |
| 迁移规则数 | 0 | 6 (M-01 ~ M-06) |

### 已知限制

1. create 模板目前硬编码在源码中（未来计划支持外部模板）
2. update --fix 仅能修复 _meta.json 相关问题
3. refactor 不处理文件内容的修改（仅移动位置）
4. 审查规则暂不支持外部自定义规则文件
5. 无单元测试套件（v2.1 计划补充）

---

## v1.0.0（初始版本）

**发布日期：2025-xx-xx**
**类型：初始发布**

### 新增功能

#### 核心 Skill 结构
- 基于 **SKILL.md 标准化规范草案 v0.1** 创建完整 skill
- 实现 **R-01 ~ R-10** 共 10 条自动审查规则
  - R-01: Frontmatter 存在性检查
  - R-02: name 字段检查
  - R-03: version SemVer 格式检查
  - R-04: description 字段检查
  - R-05: name 与目录名一致性检查
  - R-06: 正文一级标题检查
  - R-07: 触发条件章节检查
  - R-08: 核心能力章节检查
  - R-09: 工作流程章节检查
  - R-10: version 一致性检查

#### 工具脚本
- **skill_audit.py** — 独立审查工具
  - `audit` 子命令：对指定 skill 目录执行全量审查
  - `--json` 参数：输出结构化 JSON 结果
  - `--strict` 参数：严格模式（ERROR 级 exit(1)）
  - 同义词模糊匹配支持
  - 人类可读 + 机器可读双格式输出

- **json_loader.py** — 渐进式 JSON 加载器
  - `load` 子命令：按需加载指定 spec JSON
  - `list` 子命令：列出所有可用模块
  - `show` 子命令：显示模块详细信息
  - 从 `_index.json` 读取模块注册信息

#### Spec 规范定义
- **spec/frontmatter.json** — 字段规范（3必须 + 7可选）
- **spec/body.json** — 正文章节规范（5必须 + 4推荐 + N可选）
- **spec/rules.json** — 审查规则完整定义

#### Git-Sync 集成
- 提供 git-sync 步骤 3.5 自动审查入口
- 双模式运行：独立 CLI / git-sync 子进程调用
- ERROR 级默认退出非零码（v2.0 已改为纯警告模式）

### 设计原则
- 零外部依赖（纯 Python 标准库）
- 跨平台兼容（Windows/Linux/macOS）
- UTF-8 编码统一
- 人类优先的可读性设计

---

## 版本路线图（Roadmap）

### v2.1.0（计划中）

- [ ] 单元测试套件（覆盖 create/update/refactor/audit 全路径）
- [ ] create 外部模板文件支持
- [ ] update --fix 增强（frontmeter 补充、章节模板插入）
- [ ] 版本号自动同步工具（一键更新所有位置）

### v2.3.0（计划中）

- [ ] 审查规则外置配置（支持 .skillrc 或 rules_custom.json）
- [ ] refactor 内容感知移动（根据文件内容智能判断目标目录）
- [ ] 多语言 SKILL.md 支持（i18n 模板）
- [ ] 交互式 create 向导模式

### v3.0.0（远期规划）

- [ ] Skill 间依赖关系管理
- [ ] Schema 校验增强（JSON Schema 验证）
- [ ] Web UI 管理界面
- [ ] 插件系统（第三方规则扩展）

---

*本文件由 skill-standardization v2.2.0 维护。*
*最后更新：2026-05-23*
