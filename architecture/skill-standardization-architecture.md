<!--
SPDX-License-Identifier: CC-BY-SA-4.0
Copyright (c) 2026 wUwproject
Licensed under Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).
See https://creativecommons.org/licenses/by-sa/4.0/ for details.
-->

# skill-standardization 架构与规范体系文档

> 完整解读 v2.101.8 版的架构设计、审查规则体系、标准化执行流程与修复体系  
> 更新：2026-06-30（v2.95.0 → v2.101.8，含 7 个版本迭代的变更同步）

---

## 一、系统概览

skill-standardization 是一个 **Skill 全生命周期标准化管理工具集**，围绕以下闭环运行：

```
规范定义（spec/*.json）
  → 构建器（skill_builder: create / update / refactor）
    → 审查器（skill_audit: R-01 ~ R-26）
      → 修复器（fix.py: 35+ 自动修复函数（含 code_block_markers/list_mixing/code_block_lang/section_completeness/error_handling_faq））
        → 验证（--verify 铁律阻断 + --classify --category --subtype 误判分类）
```

### 1.1 三层架构

| 层 | 组件 | 职责 |
|---|------|------|
| **表现层** | SKILL.md + references/*.md + CLI | 人类可读的文档和命令行交互 |
| **业务层** | skill_builder / skill_audit / fix.py / safe_io | 创建/更新/改造/审查/修复/安全写入的核心逻辑 |
| **数据层** | spec/*.json | 按需加载的标准化规范定义；数据存储在 `skills/.standardization/<skill>/` |

### 1.2 目录结构

```
skill-standardization/
├── SKILL.md                    # 主文件（≤230行，渐进式入口）
├── _meta.json                  # 7 字段元数据（name/version/description/author/tags/data_dir/triggers）
├── references/                 # 渐进式文档
│   ├── guide.md                # 完整使用教程
│   ├── architecture.md         # 架构设计（本文件）
│   ├── reference.md            # API/命令参考手册
│   ├── rules.md                # 铁律 1~9 与完整规则说明
│   ├── blueprint_flow.md       # 蓝皮书扫描流程定义
│   ├── antipatterns.md         # 反模式速查
│   ├── data_dir_map.md         # 数据目录路径引用对照表
│   ├── examples.md             # 使用示例
│   ├── faq.md                  # 常见问题
│   ├── changelog.md            # 版本更新日志
│   ├── permissions.md          # 权限声明
│   └── LICENSE.md              # MIT 许可证（R-26 要求）
└── scripts/                    # 核心脚本
    ├── skill_audit/            # 审计引擎包（重构后统一入口）
    │   ├── __init__.py         # 主入口 + cmd_xxx() + audit_skill() + _run_audit_loop
    │   ├── __main__.py         # python -m 支持
    │   ├── fix.py              # 自动修复函数（35+ fix key，含新增 code_block_markers 等5个）
    │   ├── structure_checker.py    # R-06~R-09, R-18~R-25 正文结构 + 质量 + R-26
    │   ├── artifact_checker.py     # R-11~R-12 产出物 + 数据目录（v2.101.8: 支持 pathlib 推导式放行）
    │   ├── data_dir_checker.py     # R-22 数据目录合规
    │   ├── consistency_checker.py  # 一致性审查（含嵌套目录树路径重建）
    │   ├── _path_detector.py       # 共享路径文件检测（v2.101.8: 优先改选 _paths.py）
    │   ├── _tree_scanner.py        # 目录树扫描器（R-23 辅助）
    │   ├── progress_manager.py     # 进度管理器
    │   └── utils.py            # 常量定义（RULES 列表、关键词映射等）
    ├── safe_io.py              # 安全文件写入（原子写入 + 备份 + Windows 重试）
    ├── cleanup_manager.py      # Manifest 驱动清理（备份注册 + 收尾清理）
    ├── permission_checker.py   # 权限检查器（AST 扫描风险操作）
    ├── skill_inspector.py      # 结构扫描器（输出技能蓝皮书）
    └── spec/                   # 规范定义（JSON Schema）
        ├── body.json           # 正文章节结构规范 v2.6.0
        └── ...
```

**变化说明（v2.82.0 → v2.95.0）**：
- ✅ **新增** `--category` 误判类别强制参数（engine_mistake / engine_cant_judge）
- ✅ **新增** 模式门禁 `--mode` 必传（移除"不传则不校验"向后兼容）
- ✅ **新增** 修复循环 `sys.exit(2)` 强制阻断（不再 `break` 放行）
- ✅ **修复** `body.json` 合法化（移除导冗余顶层键，section_synonyms 现在正确加载）
- ✅ **修复** C-11 非标章节三层优先级 instruction（重命名→归并子节→拆分）
- ✅ **新增** `section_names` 加入 `_llm_only_fix_keys`
- ✅ **修复** 一致性审查嵌套目录树路径重建（旧版只提取扁平文件名）
- ✅ **修复** C-17/C-18 OMP 硬编码泛化（`O=3/M=6/P=15` → 通用数值参数检查）
- ✅ **修复** `.verify_fp.json` 格式升级（纯 ID 列表 → `{id: {category, reason}}` 字典）
- ❌ **已删除** `body.json` 中冗余顶层键（`"触发条件"/"核心能力"/"工作流程"` 三组重复定义导致 JSON 非法）

### 1.3 三层章节体系（section_tiers）

SKILL.md 的 `##` 章节分为三个层级，决定其存留行为和拆分优先级：

| 层级 | 包含章节 | 行为 |
|------|---------|------|
| **① must_have** | H1 / 约束 / 触发条件 / 核心能力 / 工作流程 | 永远留在 SKILL.md，必须有标题+内容 |
| **② whitelist.optional_progressive** | 快速开始 / 强制约束 / 铁律 / 规范 / 反模式 / FAQ / 配置 / API / 示例 / 限制 / 数据目录说明 / 权限说明 / 临时文件与备份管理 / 注意事项 | 可留，超230行时优先拆到 references/ |
| **②' whitelist.always_progressive** | 版本日志 / 更新日志 / Changelog | 强制在 references/，SKILL.md 只能有引用（R-24） |
| **③ nonstandard** | 不在①②的所有H2 | LLM 按三层优先级处理：内容匹配 must_have → 重命名；部分匹配 → ### 子节；完全非标 → 拆分 references/ |

**非标章节处理优先级**（v2.95.0 C-11 增强）：
```
第1优先 — 内容属于 must_have 章节职责范围？改标题为标准名
第2优先 — 内容属于 whitelist 章节职责范围？改标题为对应标准名
第3优先 — 与某标准章节部分相关？降级为 ### 子节归入该章节
第4优先 — 完全不匹配？拆分到 references/<slug>.md
⚠️ must_have 章节不可空不可删
⚠️ always_progressive 章节不可出现在 SKILL.md 正文
```

### 1.4 能力与限制章节

| 能力 | 说明 | 限制 |
|------|------|------|
| **审计现有 skill** | R-01~R-26 全量检查，输出 PASS/WARN/FAIL 逐条明细及上下文行 | 仅检查 SKILL.md + _meta.json + scripts/ 文件结构和代码静态分析，不检查 Python 运行时行为 |
| **创建新 skill** | 从模板生成标准骨架（含目录结构预览） | 只生成结构模板和占位符，功能代码需要手动填充 |
| **改造非标 skill** | 自动迁移文件到正确位置 | 不处理跨技能依赖、不自动生成功能代码 |
| **批量审计** | `--audit-all` 参数扫描多个 skill | 仅支持一级子目录（不支持嵌套） |
| **自动修复** | `--fix` 自动修正格式/结构/路径/生成类问题，覆盖 R-01~R-26 共 20+ 条规则 | 仅修格式/结构/路径/生成类问题，**不修复代码逻辑错误**。<br>修复后需运行 `--verify` + `--show-fix` 两阶段验证确认 |
| **权限安全扫描** | 自动检测脚本中的删除/网络/subprocess 调用 | 基于 AST 静态分析，无法检测动态执行 |

### 1.5 六种执行模式（v2.95.0）

| 模式 | 命令 | 作用 | 风险等级 |
|------|------|------|---------|
| **audit** | `python -m scripts.skill_audit audit <dir> --confirmed --mode audit` | 独立全量审计 | 🟢 只读 |
| **create** | `python -m scripts.skill_audit create <name> --confirmed --mode create` | 从模板创建标准的 skill 骨架 | 🟢 无害 |
| **update** | `python -m scripts.skill_audit update <dir> --confirmed --mode update` | 增量检查 + 可选修复 | 🟡 轻度修改 |
| **refactor** | `python -m scripts.skill_audit refactor <dir> --confirmed --mode refactor` | 全流程改造（蓝皮书→备份→审计→修复→验证→bump→清理） | 🟡 有备份保障 |
| **bump** | `python -m scripts.skill_audit bump <dir> --type fix --desc "..." --confirmed --mode bump` | 版本号三端同步升级 | 🟢 无害 |
| **readonly** | `python -m scripts.skill_audit rules --confirmed --mode readonly` | 只读查询（列出规则/模板） | 🟢 只读 |

> **语义门禁 + 模式-命令映射锁**（v2.94.0+）：所有模式入口必须传 `--confirmed` + `--mode` 参数。`--mode` 值必须与子命令一致（如 `audit --mode audit`），不一致则 `exit(1)` 阻断。不再有"不传则不校验"的向后兼容。

---

## 二、完整审查规则体系（R-01 ~ R-26）

### 2.1 类别 A：Frontmatter 结构（R-01 ~ R-05）

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-01** | ERROR | YAML frontmatter 存在性 + 11 required + 2 conditional 字段 + _meta.json 7 字段完整性 | 文件以 `---` 开头并包含闭合 `---`；11 required + 2 conditional 字段分层检查；_meta.json 含 7 标准字段 |
| **R-02** | ERROR | `name` 字段 | frontmatter 含 `name:`，值非空，且与目录名一致 |
| **R-03** | ERROR | `version` 字段（SemVer + 变更语义规则） | 值符合纯数字 x.y.z 格式（禁止 v 前缀） |
| **R-04** | ERROR | `description` 字段 | 含 `description:`，值非空 |
| **R-05** | WARN | name = 目录名 | frontmatter 的 name 与所在目录名一致 |

### 2.2 类别 B：正文结构（R-06 ~ R-10）

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-06** | WARN | 一级标题 | 正文包含 `# ` 开头的 H1 标题 |
| **R-07** | **ERROR** | 触发条件章节 | 含触发场景章节，≥3 个触发词，≥1 个否定条件 |
| **R-08** | WARN | 核心能力章节 | 含核心能力/功能章节 |
| **R-09** | WARN | 工作流程章节 | 含工作流程/步骤章节 |
| **R-10** | **ERROR** | 版本三端一致性 + 共享字段同步 | SKILL.md version == _meta.json version == changelog 最新版本号 |

### 2.3 类别 C：产出物与数据目录（R-11 ~ R-12）

| 规则 | 严重度 | 检查内容 | 通过条件 |
|------|:------:|---------|---------|
| **R-11** | ERROR | 产出物路径 + 风险检测 | 产出物符合 `skills/.standardization/<skill>/` 规范 |
| **R-12** | ERROR | 外部数据目录 + 风险检测 | 路径符合规范，_meta.json 含 data_dir |

### 2.4 类别 D：安全与权限（R-13 ~ R-17）

| 规则 | 严重度 | 检查内容 |
|------|:------:|---------|
| **R-13** | WARN | 敏感信息访问声明 |
| **R-14** | WARN | 关键位置写入声明 |
| **R-15** | ERROR | 高权限操作风险说明 |
| **R-16** | WARN | 权限权重说明 |
| **R-17** | ERROR | 渐进加载引用（强制）|

### 2.5 类别 E：质量规范（R-18 ~ R-21）

| 规则 | 严重度 | 检查内容 |
|------|:------:|---------|
| **R-18** | WARN | 反模式具体性（≥2条，含错误做法/正确做法标记）|
| **R-19** | WARN | FAQ 有意义性（≥3对 Q&A）|
| **R-20** | WARN | 写作规范（术语统一、无模糊词、中英文混排空格）|
| **R-21** | WARN | 渐进式加载说明（固定模板句）|

### 2.6 类别 F：合规与维护（R-22 ~ R-24）

| 规则 | 严重度 | 检查内容 |
|------|:------:|---------|
| **R-22** | WARN | 数据目录合规 |
| **R-23** | WARN | 文档-代码一致性（含嵌套目录树路径匹配，v2.95.0）|
| **R-24** | WARN | 更新日志渐进加载 |

### 2.7 类别 G：文档写作格式（R-25，含 C-01~C-19 十九项子检查）

| 编号 | 级别 | 检查项 | 说明 |
|:----:|:----:|--------|------|
| C-01 | ERROR | H1 标题格式 | 必须为 `# <技能名>`，不得含版本号 |
| C-02 | WARN | 标题层级 | 限制在 `##` 和 `###` |
| C-03 | WARN | 表格使用 | 结构化信息应使用表格展示 |
| C-04 | WARN | 引用块使用 | 提示/注意/警告使用 `>` 引用块 |
| C-05 | WARN | 列表区分 | 有序→步骤，无序→选项 |
| C-06 | WARN | 加粗使用 | 关键术语/约束用 `**加粗**` |
| C-07 | WARN | 语言标识 | 代码块应带语言标识 |
| C-08 | WARN | Checklist | 操作前自检使用 `- [ ]` |
| C-09 | WARN | 渐进引用 | 统一使用 `→ 详见 references/` |
| C-10 | WARN | 空行规范 | frontmatter 闭合后 ≤2 空行 |
| C-11 | WARN | 章节顺位 + 非标章节处理 | section_order 一致性 + 三层优先级 instruction（v2.95.0）|
| C-12 | WARN | 格式合规 | 章节格式与 content_format 定义一致 |
| C-13 | WARN | 渐进式索引表完整性 | 所有 references/ 文件是否在索引表中列出 |
| C-14 | WARN | 工作流步骤完整性 | 工作流程步骤是否覆盖实际代码功能 |
| C-15 | WARN | 内容冗余检测 | 索引表的引用 vs 正文直接的引用 |
| C-16 | WARN | references/ 文档过时 | 磁盘存在但 SKILL.md 未引用 |
| C-17 | WARN | 使用示例质量 | 示例是否包含输入→输出的完整交互（v2.95.0 泛化修复，移除 OMP/CPM 硬编码）|
| C-18 | WARN | 能力边界质量 | 是否量化阈值、说明参数约束、环境要求 |
| C-19 | WARN | 错误处理质量 | FAQ 是否包含错误修复指导 |

**C-17/C-18 修复建议泛化**（v2.94.0）：原检查逻辑硬编码了 activity-duration-estimation 的 OMP 术语（`O=3/M=6/P=15`、`CPM分析`），现改为通用数值参数检查。所有技能不再收到领域不相关的修复建议。

### 2.8 类别 H：文档声明规范（R-26，含 C-01~C-08 八项子检查）

| 编号 | 级别 | 检查项 |
|:----:|:----:|--------|
| C-01 | ERROR | references/LICENSE.md 存在 |
| C-02 | ERROR | SKILL.md 正文无独立 license 章节 |
| C-03 | ERROR | 根目录无 LICENSE 文件 |
| C-04 | WARN | scripts/ 下无 LICENSE 文件 |
| C-05 | WARN | 渐进式索引表含 LICENSE.md 引用 |
| C-06 | ERROR | references/LICENSE.md 非空 |
| C-07 | ERROR | 根目录无 README.md |
| C-08 | ERROR | SKILL.md 正文 README 章节拆分 |

### 2.9 规则汇总统计

| 类别 | 包含规则 | ERROR | WARN | 目的 |
|------|---------|:-----:|:----:|------|
| A. Frontmatter | R-01~R-05 | 4 | 1 | 技能身份标识 + _meta.json |
| B. 正文结构 | R-06~R-10 | 3 | 2 | 文档结构和质量 |
| C. 产出物与目录 | R-11~R-12 | 2 | 0 | 目录隔离和数据安全 |
| D. 安全与权限 | R-13~R-17 | 2 | 3 | 权限声明和风险控制 |
| E. 质量规范 | R-18~R-21 | 0 | 4 | 内容质量和可读性 |
| F. 合规与维护 | R-22~R-24 | 0 | 3 | 长期维护一致性 |
| G. 写作格式 | R-25 | 0 | 1 | 文档排版建议（19 项子检查） |
| H. 文档声明 | R-26 | 0 | 1 | LICENSE + README 声明 |
| **合计** | **R-01~R-26** | **11** | **15** | |

---

## 三、核心设计原则

### D1: 零外部依赖
### D2: 铁律验证阻断模式
### D3: 信息零遗漏
### D4: 渐进式加载
### D5: 模板驱动
### D6: 备份优先 + Inspect 先读全
### D7: Manifest 驱动清理
### D8: 脚本级强制（非 AI 自觉）

（详见 SKILL.md 独立章节，此处不再重复）

---

## 四、误报分类机制（v2.94.0 重写）

> 这是 v2.94.0 最大变化。旧版 `--classify` 无类别约束，LLM 可随意标记任何 FAIL 为误判。新版引入两类固定类别。

### 4.1 两级误报分类

LLM 对每条 FAIL 只能选以下两类之一标记为误判：

| 类别 | 含义 | 适用场景示例 |
|------|------|-------------|
| `engine_mistake` | 引擎技术性错误 | BOM 导致 frontmatter 正则未匹配、注释被当实际操作、概念图路径被当文件引用、专有名词被当缺空格 |
| `engine_cant_judge` | 引擎语义不足，LLM 确认后放行 | `__init__.py` 无需列文档树、反模式内容格式引擎没认出但 LLM 确认合规、body.json 模板预期与实际域差异 |

### 4.2 命令格式

```bash
# ✅ 合法
python -m scripts.skill_audit audit <dir> --classify 42 --category engine_mistake --reason "BOM字符" --mode audit --confirmed
python -m scripts.skill_audit audit <dir> --classify C-stale_doc_ref --category engine_mistake --reason "概念图路径" --mode audit --confirmed

# ❌ 拒绝
--classify 42                              # 缺 --category
--classify 42 --category i_dont_like_it    # 非法类别
```

### 4.3 一致性审查误报

一致性审查的 `C-missing_doc_ref` 和 `C-stale_doc_ref` 复用同一类别机制。v2.95.0 修复了旧版只提取扁平文件名的 bug，嵌套目录树路径现可正确匹配（`references/antipatterns.md` 不再被误判为根目录的 `antipatterns.md`）。

### 4.4 向后兼容

旧格式 `.verify_fp.json`（纯 ID 列表）被忽略。每次审计和审查都是全新的一次性任务，不继承历史误判。

---

## 五、审计后自动修复体系（fix.py）

### 5.1 fix key 与 LLM 手动修复分界

修复循环根据 fix key 类型自动分流：

| 路径 | 条件 | 行为 |
|------|------|------|
| **auto-fix** | fix key 不在 `_llm_only_fix_keys` 中 | Python 自动执行 |
| **LLM 手动** | fix key 在 `_llm_only_fix_keys` 中 | 阻断等待 LLM 修复 |
| **LLM 手动** | 无 fix key | 阻断等待 LLM 修复 |

**_llm_only_fix_keys**（v2.95.0，新增 `section_names`）：
```python
_BLOCKED_FIX_KEYS = {
    "workflow_completeness",  # C-14: 需要 LLM 读代码写工作流 → 输出3步指引
    "example_quality",        # C-17: 需要 LLM 读代码创建示例 → 输出3步指引
    "capability_boundary",    # C-18: 需要 LLM 理解能力边界 → 输出3步指引
    "section_names",          # C-11: 非标章节归类需 LLM 判断内容语义
}
```
BLOCKED 的 3 个 key（C-14/17/18）被阻断时输出结构化指引：
1. 读取 `scripts/` 下的 Python 代码理解功能
2. 按 JSON 模板写入结构化数据文件
3. 重新 `--fix` 自动渲染为 SKILL.md 章节

### 5.2 修复循环退出机制（v2.94.0 重写）

旧版：auto-fix 耗尽后 `break` 退出循环，LLM 可以跳过剩余项。
新版：auto-fix 耗尽后剩余项 > 0 → `sys.exit(2)` + 创建重构锁，强制阻断。

```python
# 旧版（可跳过）
if remaining:
    print("剩余 N 项需 LLM 修复")
_save_html_report()
break  # ← 不管 remaining 是否为空都 break

# 新版（强制阻断）
if remaining:
    _save_remaining_llm(skill_dir, remaining)
    _create_refactor_lock(skill_dir)
    sys.exit(2)  # ★ 强制退出，LLM 无法继续
else:
    print("双 0 达成")
    break  # 只有 0 remaining 才放行
```

### 5.3 修复函数清单（35+）

| 函数 | 对应规则 | 修复内容 |
|------|---------|---------|
| `fix_name` | R-01 | 修复 name 字段 |
| `fix_description` | R-04 | 修复 description 字段 |
| `fix_version` | R-03 | 修复 version 字段 |
| `fix_author` | R-02 | 修复 author 字段 |
| `fix_h1` / `fix_h1_version` / `fix_h1_position` | R-06 | H1 标题处理 |
| `fix_section_trigger` / `fix_section_core` / `fix_section_workflow` | R-07~R-09 | 章节创建 |
| `fix_progressive_loading` | R-21 | 渐进式加载模板句 |
| `fix_antipattern_progressive` | R-18 | 反模式文档 |
| `fix_faq_progressive` | R-19 | FAQ 文档 |
| `fix_writing_standards` | R-20 | 写作规范 |
| `fix_data_dir_compliance` | R-22 | 数据目录声明 |
| `fix_split_nonstandard` | R-17 | 非标章节拆分 |
| `fix_section_order` | R-25 C-11 | 章节重排 |
| `fix_progressive_index_table` | C-13 | 渐进式索引表 |
| `fix_reclassify_section(action)` | R-17 Phase 3 | 通用非标归类 |
| `fix_frontmatter_fields` | R-01 | 补全 frontmatter |
| `fix_license_compliance` | R-26 | LICENSE 规范 |
| `apply_consistency_fix` | 一致性审查 | outdated_rule_ref 修复 |
| **`fix_code_block_markers`** | **R-22(写作标准)** | **缩进代码块→围栏 ``` 块（v2.101.7 新增）** |
| **`fix_list_mixing`** | **C-05** | **同章节混排列表统一为多数方样式（v2.101.7 新增）** |
| **`fix_code_block_lang`** | **C-07** | **裸 ``` 补语言标识（v2.101.7 新增）** |
| **`fix_section_completeness`** | **C-12** | **空章节补充格式线索（v2.101.7 新增）** |
| **`fix_faq_error_handling`** | **C-19** | **创建/补充 FAQ 错误处理章节（v2.101.7 新增）** |

---

## 六、关键流程

### 6.1 refactor 模式完整步骤（v2.101.8）

```
[1/8] 蓝皮书扫描 → inspect_skill(skill_dir)
[2/8] 备份 → .zip 到 .standardization/<skill>/backup/
[3/8] 全量审计 → R-01~R-26 全量跑
[4/8] ★★★ 细碎修复循环 ★★★
  ┌─ auto-fix 修复可自动修复项
  ├─ 停滞检测（2 轮无变化 → 清除 fix key）
  ├─ 剩余 LLM 手动项 → sys.exit(2) + 重构锁
  └─ LLM 修复后 --continue
[5/8] 全量审计确认 → 双 0 验证 + _llm_only_fix_keys 二次筛
[6/8] 全量一致性审查 + 修复 → 文档-代码一致性
[7/8] bump (feature) + 报告
[8/9] cleanup → end_session() 清理临时文件
→ ✅ refactor 全流程完成
```

### 6.2 `--verify` 二次筛查指令（v2.94.0 更新）

```
★★★ LLM 二次筛查指令 ★★★
判断每条 FAIL 是否属于以下两种误报：

【engine_mistake】引擎技术性错误
  → --classify ID --category engine_mistake --reason "..."

【engine_cant_judge】引擎能力不足，LLM 确认后放行
  → --classify ID --category engine_cant_judge --reason "..."

【真问题】以上两类均不满足 → 必须修复，不得标记为误判
  → 记下 #ID，运行 --show-fix ID 获取修复指引
```

---

## 七、关键版本变更摘要（v2.82.0 → v2.95.0）

| 版本 | 核心变更 |
|------|---------|
| **2.94.0** | **--category 误判类别强制 + --mode 必传 + 修复循环 exit(2) 阻断 + body.json 合法化 + C-11 三层 instruction + 一致性审查嵌套目录修复 + OMP 硬编码泛化** |
| **2.95.0** | 文档同步更新（--classify --category、--mode 必传、section_names 加入 _llm_only_fix_keys、guide.md 命令示例更新）|

---

> 本文档基于 skill-standardization v2.101.8 的 SKILL.md + references/*.md + 核心脚本综合分析整理。
