# 架构设计

> 本文件描述 skill-standardization v2 的整体架构、模块关系和数据流。
> 适合需要深入理解内部实现或进行二次开发的读者。

---

## 目录

1. [系统概览](#系统概览)
2. [目录结构](#目录结构)
3. [模块架构图](#模块架构图)
4. [核心模块详解](#核心模块详解)
5. [数据流](#数据流)
6. [规范定义体系](#规范定义体系)
7. [设计原则与决策](#设计原则与决策)

---

## 系统概览

skill-standardization 是一个 **Skill 全生命周期标准化管理工具集**，围绕「规范定义 → 创建 → 检查 → 改造 → 审查」的闭环构建。

```
┌─────────────────────────────────────────────────────┐
│                skill-standardization v2              │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ 规范定义  │→ │ 构建器   │→ │    审查器        │   │
│  │ spec/*.json│  │ builder  │  │    auditor       │   │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │                  │             │
│       ▼              ▼                  ▼             │
│  ┌──────────┐  ┌──────────┐     ┌──────────────┐    │
│  │ 加载器   │  │ create   │     │ R-01 ~ R-10  │    │
│  │ loader   │  │ update   │     │  审查规则引擎  │    │
│  └──────────┘  │ refactor │     └──────────────┘    │
│                └──────────┘                          │
└─────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   ┌──────────┐        ┌──────────┐
   │ 目标 Skill │        │ (独立)   │
   │ (输入/输出)│        │  (集成)  │
   └──────────┘        └──────────┘
```

---

## 目录结构

```
skill-standardization/                 # Skill 根目录
│
├── SKILL.md                           # 主文件（v2，≤200行核心版）
├── _meta.json                         # 五字段元数据
│
├── references/                              # 渐进式 MD 辅助文档
│   ├── guide.md                       # 使用指南（详细教程）
│   ├── examples.md                    # 示例集合
│   ├── reference.md                   # API/命令参考手册
│   ├── faq.md                         # 常见问题
│   ├── changelog.md                   # 版本更新日志
│   └── architecture.md                # 本文件 — 架构设计
│
└── scripts/                           # 核心脚本与规范定义
    ├── skill_builder/                 # [v2.13.0重构] 构建器包（面向对象）
    │   ├── __init__.py              #   主入口 + argparse 解析
    │   ├── __main__.py              #   支持 python -m skill_builder 执行
    │   ├── creator.py               #   SkillCreator 类（create 模式）
    │   ├── updater.py               #   SkillUpdater 类（update 模式）
    │   ├── refactor.py              #   SkillRefactor 类（refactor 模式）
    │   ├── version_manager.py       #   VersionManager 类（版本号管理）
    │   └── utils.py                 #   工具函数（备份、模板等）
    │
    ├── skill_audit/                  # [v2.13.0重构] 审查器包（面向对象）
    │   ├── __init__.py            #   主入口 + argparse + audit_skill()
    │   ├── __main__.py            #   支持 python -m skill_audit 执行
    │   ├── frontmatter_checker.py  #   R-01~R-05 检查函数
    │   ├── structure_checker.py    #   R-06~R-09 检查函数
    │   ├── artifact_checker.py     #   R-11~R-12 检查函数
    │   ├── permission_checks.py   #   R-13~R-17 检查函数
    │   └── utils.py               #   工具函数（常量、辅助函数）
    │
    ├── permission_checker.py                 # 权限检查器
    ├── authorization_manager.py             # 授权管理器
    ├── json_loader.py                 # 渐进式 JSON 加载器
    │                                 #   ├─ load/list/show/refs 子命令
    │                                 #   └─ 从 _index.json 发现模块
    │
    └── spec/                          # 规范定义（JSON Schema）
        ├── _index.json                # [v2] 模块注册索引
        ├── frontmatter.json           # Frontmatter 字段规范
        ├── body.json                  # 正文章节结构规范
        ├── rules.json                 # 审查规则完整定义
        ├── structure.json             # [v2] 目录结构规范
        └── progressive_md.json        # [v2] 渐进式 MD 体系规范
```

### 文件依赖关系

```
SKILL.md ← 引用 → references/*.md（渐进式文档）
                     ↑
skill_builder/ ──读取──→ spec/*.json（规范定义）
  ├─ __init__.py       主入口 + argparse
  ├─ creator.py        SkillCreator 类
  ├─ updater.py        SkillUpdater 类
  ├─ refactor.py        SkillRefactor 类
  ├─ version_manager.py  VersionManager 类
  └─ utils.py           工具函数
-m scripts.skill_audit   ──读取──→ spec/rules.json（审查规则）
json_loader.py   ──读取──→ spec/_index.json → spec/*.json
```

---

## 模块架构图

### 三层架构

```
┌─────────────────────────────────────────────────┐
│                  表现层 (Presentation)            │
│                                                  │
│   SKILL.md + references/*.md          CLI (--help)     │
│   (人类可读文档)                 (参数说明)       │
├─────────────────────────────────────────────────┤
│                  业务层 (Business)                │
│                                                  │
│   -m scripts.skill_builder              -m scripts.skill_audit   │
│   ┌──────────┬──────────┐      ┌──────────────┐ │
│   │ create   │ update   │      │ 规则匹配引擎  │ │
│   │ (模板生成)│ (检查修复)│      │ R-01~R-25    │ │
│   ├──────────┴──────────┤      └──────────────┘ │
│   │ refactor (迁移引擎)  │                      │
│   └─────────────────────┘                       │
├─────────────────────────────────────────────────┤
│                  数据层 (Data)                    │
│                                                  │
│   json_loader.py              spec/*.json        │
│   ┌──────────┬──────────┐    ┌────────────────┐ │
│   │ load     │ list/show│    │ frontmatter    │ │
│   │ (按需加载)│ (元信息) │    │ body           │ │
│   └──────────┴──────────┘    │ rules           │ │
│                             │ structure       │ │
│                             │ progressive_md  │ │
│                             │ _index          │ │
│                             └────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## 核心模块详解

### 1. -m scripts.skill_builder（构建器）

职责：Skill 的创建、更新和改造。

**类/函数结构：**

| 函数 | 行数 | 职责 | 输入 | 输出 |
|------|------|------|------|------|
| `cmd_create()` | ~50 | 从模板创建新 skill | name, desc, tags, dir | 标准目录结构 |
| `cmd_update()` | ~120 | 增量检查+可选修复 | skill_dir, fix, backup | 检查报告 |
| `cmd_refactor()` | ~150 | 整体结构改造 | skill_dir, dry_run, backup | 迁移映射表 |
| `load_spec()` | ~6 | 加载单个 spec JSON | module_name | dict or None |
| `_scan_all_files()` | ~12 | 递归扫描目录 | directory | {path: {size,mtime}} |
| `_create_backup()` | ~14 | 时间戳备份 | skill_dir, operation | 备份路径 |
| `_write_json()` | ~4 | 写 JSON 文件 | filepath, data | — |
| `_print_refactor_plan()` | ~35 | 输出 dry-run 计划 | all_files, loose_files | 控制台输出 |
| `main()` | ~48 | CLI 入口+参数解析 | sys.argv | 分派到子命令 |

**关键常量：**

| 常量 | 类型 | 说明 |
|------|------|------|
| `SPEC_DIR` | Path | spec/ 目录的绝对路径 |
| `SKILL_TEMPLATE` | str | create 使用的 SKILL.md 模板 |
| `META_TEMPLATE` | str | create 使用的 _meta.json 模板 |
| `REQUIRED_SECTIONS` | list[tuple] | update 检查的必填章节及同义词 |
| `SPLITTABLE_KEYWORDS` | dict | refactor 判断可拆分章节的关键词 |

### 2. -m scripts.skill_audit（审查器）

职责：基于 R-01~R-25 对 SKILL.md 执行自动化审查。

**执行流程：**
```
1. 读取目标 SKILL.md
   ↓
2. 解析 Frontmatter（提取 --- 包裹的 YAML 块）
   ↓
3. 逐条执行 R-01 ~ R-10 规则
   ↓
4. 收集 PASS / FAIL 结果
   ↓
5. 生成报告（人类可读 或 JSON 格式）
   ↓
6. 返回退出码（默认0，--strict 时 ERROR>0 则 1）
```

**规则分类：**
- **ERROR 级 (R-01~R-04)**: 结构性问题（frontmatter 缺失、关键字段缺失等）
- **WARN 级 (R-05~R-10)**: 质量性建议（命名一致、章节完整性、版本同步）

### 3. json_loader.py（加载器）

职责：按需加载 spec/ 下的 JSON 规范定义。

**设计模式：懒加载（Lazy Loading）**

```python
# 仅在用户请求时才读取对应文件
def load_spec(module_name):
    spec_file = SPEC_DIR / f"{module_name}.json"
    if spec_file.exists():
        with open(spec_file, "r", encoding="utf-8") as f:
            return json.load(f)   # 只在此时才读磁盘
    return None
```

**模块发现机制：**
```
用户执行: python json_loader.py load <module_name>
  ↓
读取: spec/_index.json（模块注册表，始终加载）
  ↓
查找: modules 数组中匹配 module_name 的条目
  ↓
加载: spec/<module_name>.json 的实际内容
  ↓
输出: 格式化打印到标准输出
```

**特殊命令 `all`:**
- 遍历 _index.json 中所有已注册模块
- 依次加载并合并输出
- 用于需要全量规范的场景

---

## 数据流

### Create 数据流

```
CLI 参数 (name/desc/tags/dir)
  ↓
cmd_create(args)
  ↓
SKILL_TEMPLATE.format(name=..., description=..., tags=...)
  ↓                                    ↓
写入 SKILL.md                    META_TEMPLATE.format(...)
  ↓                                    ↓
写入 _meta.json
  ↓
创建 references/.gitkeep + scripts/.gitkeep
  ↓
输出结果摘要
```

### Update 数据流

```
skill_dir 参数
  ↓
cmd_update(args)
  ↓
┌──────────────────────────────────────┐
│ 检查 1: _meta.json                   │
│   读取 → 解析 JSON → 验证五字段      │
│   → 缺失? --fix 则补充              │
├──────────────────────────────────────┤
│ 检查 2: SKILL.md                     │
│   读取 → 检测 frontmarker → 提取 H2  │
│   → 匹配必填章节关键词               │
│   → 统计行数(>200则警告)             │
├──────────────────────────────────────┤
│ 检查 3: 目录结构                     │
│   扫描根目录文件 → 对比预期集合       │
│   → 非常规文件列出建议               │
└──────────────────────────────────────┘
  ↓
格式化输出报告 (ERROR/WARN/PASS 计数)
```

### Refactor 数据流

```
skill_dir + [--dry-run] + [--no-backup]
  ↓
cmd_refactor(args)
  ↓
[阶段1] _scan_all_files(skill_dir)
  → 递归遍历（排除 __pycache__/.git）
  → 生成 {rel_path: {size, mtime}} 清单
  → 分析根目录散落文件
  ↓
[--dry-run?] → 是 → _print_refactor_plan() → 结束
  ↓ 否
[阶段2] _create_backup(skill_dir, "refactor")
  → 时间戳命名的完整副本
  ↓
[阶段3] 遍历清单，逐文件判断:
  ├── SKILL.md / _meta.json     → keep (standard)
  ├── _skillhub_meta.json       → keep (legacy)
  ├── .git*                     → keep (git)
  ├── __pycache__/*             → skip (cache)
  ├── .py/.sh/.bat/.ps1         → move → scripts/
  ├── .md (非 SKILL.md)         → move → references/
  ├── .png/.jpg/.gif/.svg       → move → assets/
  ├── .txt/.cfg/.ini/.yaml      → move → scripts/
  └── 其他                       → keep (unknown)
  ↓
[阶段4] 验证:
  → 再次扫描目录
  → 对比迁移前后文件总大小
  → ≥99%? 通过 | <99%? 警告可能丢失
  ↓
输出迁移映射表 + 后续建议
```

### Audit 数据流

```
skill_dir [--json] [--strict]
  ↓
-m scripts.skill_audit audit ...
  ↓
读取: <skill_dir>/SKILL.md
  ↓
解析 Frontmatter:
  ┌────────────────────────────────┐
  │ 提取 --- ... --- 块            │
  │ 解析为 key: value 字典         │
  └────────────────────────────────┘
  ↓
逐规则检查:
  R-01: re.match(r'^---', content)? → PASS/FAIL
  R-02: 'name' in parsed_fm?         → PASS/FAIL
  R-03: re.match(SemVer, version)?   → PASS/FAIL
  R-04: 'description' in parsed_fm?  → PASS/FAIL
  R-05: name == dirname?             → PASS/FAIL
  R-06: has '# ' line?               → PASS/FAIL
  R-07: trigger keywords in H2s?     → PASS/FAIL
  R-08: core capability keywords?    → PASS/FAIL
  R-09: workflow keywords?           → PASS/FAIL
  R-10: version == manifest_version? → PASS/FAIL(N/A)
  ↓
汇总结果:
  results[] = [{id, level, status, detail}]
  summary = {error, warn, pass, total}
  ↓
输出:
  --json? → JSON.dump(results)
  else   → 人类可读表格
  ↓
退出码:
  --strict 且 error > 0? → exit(1)
  else                 → exit(0)
```

---

## 规范定义体系

### Spec JSON 结构约定

每个 spec/*.json 遵循统一的结构模板：

```json
{
  "_version": "2.0.0",
  "_description": "一句话描述此规范的内容和用途",
  "_depends_on": [],           // 可选：依赖的其他模块
  // ... 具体规范内容
}
```

### 各模块职责边界

| 模块 | 职责范围 | 不包含 | 使用者 |
|------|---------|--------|--------|
| `frontmatter.json` | 定义字段名/类型/必须性 | 不含验证逻辑 | create 模板 + audit R-01~R-04 |
| `body.json` | 定义章节名/层级/必须性 | 不含写作指导 | SKILL.md 编写 + audit R-06~R-09 |
| `rules.json` | 完整规则定义（ID/级别/逻辑） | 不含执行引擎 | -m scripts.skill_audit |
| `structure.json` | 目录结构规范 + 迁移规则 | 不含移动逻辑 | create + refactor |
| `progressive_md.json` | MD 拆分方案 + 加载协议 | 不含文件操作 | references/ 创建 + 加载协议 |
| `_index.json` | 模块注册表 + 依赖关系 | 不含具体规范 | json_loader.py |

### 模块间依赖关系

```
_index.json (中心注册)
    ├── frontmatter.json (独立)
    ├── body.json (独立)
    ├── rules.json (依赖 frontmatter — 需要字段定义来检查)
    ├── structure.json (独立)
    └── progressive_md.json (依赖 structure + body — 需要知道拆分什么)
```

---

## 设计原则与决策

### D1: 零外部依赖

**决策**: 所有脚本仅使用 Python 标准库。

**原因:**
- 降低安装门槛（无需 pip install）
- 提高跨平台兼容性
- 减少供应链风险

**代价:**
- JSON 操作使用 stdlib json（功能足够）
- 路径处理使用 pathlib（Python 3.4+）
- 无高级 CLI 框架（使用 argparse 已足够）

### D2: 纯警告模式

**决策**: 审查结果不阻断工作流。

**原因:**
- Skill 开发是迭代过程，初期不规范是正常的
- 阻断会导致开发者关闭审查功能
- 警告信息足以引导改进

**更新点:** v1.x 中 ERROR 级导致 exit(1)，v2.0 改为始终 exit(0)。

### D3: 信息零遗漏

**决策**: refactor 模式绝不删除任何文件。

**原因:**
- Skill 包含用户自定义的非标但有价值的文件（即使不符合规范）
- 删除不可逆，风险太高
- 移动后可通过备份回滚

**保障措施:**
1. 强制备份
2. 全量扫描记录原始状态
3. 仅 move 不 delete
4. 移动后字节一致性验证

### D4: 渐进式加载

**决策**: 规范定义按需加载，非全量导入。

**原因:**
- 不同场景需要的规范子集不同（create 需要 structure，audit 需要 rules）
- 减少内存占用
- 支持未来扩展更多规范模块而不影响现有流程

**实现:** json_loader.py 的 load 命令 + _index.json 模块注册。

### D5: 模板驱动

**决策**: create 使用硬编码字符串模板。

**当前选择理由:**
- 简单直接，无额外抽象
- 模板内容稳定，不需要运行时更新
- 易于理解和自定义（更新源码即可）

**未来演进方向:**
- 外部模板文件（Jinja2 或简单 format）
- 用户自定义模板目录
- 多语言模板支持

---

*本文件由 skill-standardization v2.0.0 维护。*
*最后更新：2026-05-22*
