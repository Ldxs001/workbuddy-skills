# everything-search-breadmemory

基于 Everything (es.exe) 的本地文件搜索引擎，附带面包屑知识管理系统和艾宾浩斯遗忘曲线复习引擎。

## 适用场景

- 在本地海量文件中快速搜索指定关键词/模式的文件
- 将搜索到的文件自动解析、归纳，提炼为知识条目
- 建立"面包屑小本本"（breadcrumb notebook），长期积累知识碎片
- 基于艾宾浩斯遗忘曲线，每日自动轮询复习已有知识

## 前置条件

技能首次使用时，会自动检测 Everything/es.exe 是否可用：
- **已安装**：直接使用
- **未安装**：引导下载 Everything 便携版，自动放置 es.exe 到技能目录

## 核心能力

### 1. Everything 本地搜索

```bash
python {SKILL_DIR}/scripts/es_search.py search "<搜索关键词>" [--max 50] [--path "C:/限定路径"]
```

输出结构化 JSON，包含：文件路径、名称、大小、修改日期。

### 2. 面包屑小本本（知识存储）

```bash
# 添加知识条目
python {SKILL_DIR}/scripts/breadcrumb.py add --title "标题" --content "知识内容" --source "/path/to/file" [--tags "标签1,标签2"]

# 列出所有条目
python {SKILL_DIR}/scripts/breadcrumb.py list [--tag "标签"] [--limit 20]

# 搜索条目
python {SKILL_DIR}/scripts/breadcrumb.py search "关键词"

# 删除条目
python {SKILL_DIR}/scripts/breadcrumb.py delete --id <条目ID>

# 查看条目详情
python {SKILL_DIR}/scripts/breadcrumb.py show --id <条目ID>
```

### 3. 艾宾浩斯复习引擎

```bash
# 获取今日应复习的条目列表（自动按艾宾浩斯曲线计算）
python {SKILL_DIR}/scripts/ebbinghaus.py daily-review [--count 5]

# 标记某条目已完成复习
python {SKILL_DIR}/scripts/ebbinghaus.py mark-reviewed --id <条目ID>

# 查看复习统计
python {SKILL_DIR}/scripts/ebbinghaus.py stats
```

**艾宾浩斯复习间隔**（天）：1, 2, 4, 7, 14, 30, 60, 120

每条知识记录自动追踪：
- `created_at`: 首次创建日期
- `review_count`: 已复习次数
- `last_reviewed_at`: 上次复习日期
- `next_review_at`: 下次应复习日期

### 4. 拓扑甜甜圈关联引擎

自动发现面包屑间的逻辑关联，形成"甜甜圈"知识图谱。不强迫闭环，只建立有逻辑的关联。

```bash
# 生成/更新拓扑甜甜圈（需 ≥ 2 条面包屑）
python {SKILL_DIR}/scripts/topology_donut.py generate

# 查看所有甜甜圈
python {SKILL_DIR}/scripts/topology_donut.py show-donut

# 查看指定甜甜圈详情（含节点和关联逻辑）
python {SKILL_DIR}/scripts/topology_donut.py show-donut --id donut_001

# 查看某条目所属的甜甜圈
python {SKILL_DIR}/scripts/topology_donut.py show-donut --entry-id <条目ID>

# 复习扩展：获取与某条目关联的所有面包屑及关联逻辑
python {SKILL_DIR}/scripts/topology_donut.py expand --id <条目ID>

# 甜甜圈统计
python {SKILL_DIR}/scripts/topology_donut.py stats
```

**5 种关联类型：**

| 类型 | 说明 | 检测条件 |
|------|------|---------|
| `tag_cluster` | 标签聚类 | 共享 ≥ 2 个标签 |
| `content_bridge` | 内容桥接 | 标题/内容共现 ≥ 2 个关键词 |
| `source_family` | 同源家族 | 来源文件在同一目录 |
| `sequential_chain` | 序贯链接 | 通过 auto_source 引用链 |
| `conceptual_hierarchy` | 概念层级 | 标题含包含关系 或 标签是子集 |

**4 种甜甜圈类型：**

| 类型 | 说明 |
|------|------|
| `closed` | 闭合环路 —— 知识形成完整闭环 |
| `nested` | 嵌套结构 —— 小甜甜圈完全包含在大甜甜圈内 |
| `branching` | 分支发散 —— 一个中心节点辐射多个子节点 |
| `chain` | 线性链条 —— 知识沿序贯路径演进 |

**艾宾浩斯复习 + 拓扑扩展：**

```bash
# 今日复习（含拓扑甜甜圈关联扩展）
python {SKILL_DIR}/scripts/ebbinghaus.py daily-review-expand [--count 5]

# 或使用 --expand 标志
python {SKILL_DIR}/scripts/ebbinghaus.py daily-review --expand [--count 5]

# 对指定条目进行拓扑扩展
python {SKILL_DIR}/scripts/ebbinghaus.py expand-topology --id <条目ID>
```

## 完整工作流

### 流程 A：搜索 → 解析 → 入库

当用户说"搜索本地关于XX的文件，提取要点保存"时：

1. **调用 es_search.py search** 找到匹配文件
2. **读取文件内容**（Read tool 或其他可用工具）
3. **解析归纳**要点，形成知识摘要
4. **调用 breadcrumb.py add** 将知识 + 原文路径存入面包屑
5. **汇总报告**搜索结果和入库情况

### 流程 B：每日复习

当用户说"今日复习"或"今天有什么知识需要回顾"时：

1. **调用 ebbinghaus.py daily-review** 获取今日应复习条目
2. **展示条目**给用户阅读
3. 用户确认后，**调用 ebbinghaus.py mark-reviewed** 更新复习记录

## 自动化/定时任务设定

> 以下为 Agent 语义指引。各 AI 平台根据自身能力实现。

### 定时任务 1：命题搜索 + 入库

**触发频率建议**：每天 1 次，凌晨执行

**Agent 执行逻辑**：
1. 调用 `es_search.py search "<命题关键词>"` 获取文件列表
2. 读取匹配文件，提取核心知识
3. 调用 `breadcrumb.py add` 将新知识入库

### 定时任务 2：每日艾宾浩斯复习

**触发频率建议**：每天 1 次，早晨执行

**Agent 执行逻辑**：
1. 调用 `ebbinghaus.py daily-review` 获取今日待复习条目
2. 向用户展示条目内容
3. 用户确认复习后，调用 `ebbinghaus.py mark-reviewed --id <ID>` 更新状态

### 定时任务 3：拓扑甜甜圈更新

**触发频率建议**：每天 1 次 或 每周 1 次

**Agent 执行逻辑**：
1. 调用 `topology_donut.py generate` 重新分析面包屑关联
2. 新关联发现时向用户报告变更摘要
3. 配合 `daily-review-expand` 在复习时自动利用拓扑扩展

### 跨平台调度指南

脚本本身是平台无关的纯 Python CLI，可由任意调度器触发：

| 平台 | 实现方式 | 命令示例 |
|------|---------|---------|
| **Linux/macOS cron** | `crontab -e` 添加定时任务 | `0 2 * * * python3 ~/.workbuddy/skills/everything-search-breadmemory/scripts/topology_donut.py generate` |
| **Windows 任务计划** | `schtasks` 命令行或 GUI | `schtasks /create /tn "拓扑甜甜圈更新" /tr "python topology_donut.py generate" /sc daily /st 02:00` |
| **macOS Launchd** | 创建 `.plist` 到 `~/Library/LaunchAgents/` | 配置 StartCalendarInterval 和 ProgramArguments |
| **WorkBuddy** | `automation_update` 工具 | prompt: "调用 topology_donut.py generate" |
| **Claude Code** | `.claude/settings.json` hooks | 同 cron 语法 |
| **GitHub Actions** | `.github/workflows/` YAML | `on: schedule: - cron: '0 2 * * *'` |
| **通用（手动）** | 用户手动执行 | `python topology_donut.py generate` |

## Agent 行为规范

使用本技能时，Agent 必须遵循：

1. **搜索结果先展示**：列出文件路径、大小、日期，让用户确认后再解析
2. **解析结果需归纳**：不是简单复制文件内容，而是提炼核心知识点
3. **面包屑条目须关联原文**：每条知识必须附带 `--source` 指向原文文件路径
4. **复习结果需反馈**：每日复习后，告知用户本次复习的条目数和下次复习时间
5. **复习结果需反馈**：每日复习后，告知用户本次复习的条目数和下次复习时间
6. **拓扑扩展需说明关联逻辑**：复习扩展时，明确展示关联类型（标签聚类/内容桥接等）和学习建议，而非仅列条目名
7. **自动化任务可信赖**：定时任务出错时需记录并向用户报告

## 数据存储

所有数据存储在 `~/.everything_search/`：

```
~/.everything_search/
├── breadcrumb.json         # 面包屑知识条目
├── donuts.json             # 拓扑甜甜圈关联图谱（独立存储）
├── config.json             # 配置（es.exe路径、艾宾浩斯参数等）
├── review_log.jsonl        # 复习历史日志
├── breadcrumb_backup_01~09.bat  # 容灾备份（循环覆盖）
└── breadcrumb_backup_01~09.py   # 容灾恢复脚本
```

---

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/es_search.py` | Everything 搜索封装，检测/安装/搜索 |
| `scripts/breadcrumb.py` | 面包屑小本本 CRUD + 容灾备份 |
| `scripts/ebbinghaus.py` | 艾宾浩斯引擎 + 每日复习 + 拓扑扩展 |
| `scripts/topology_donut.py` | 拓扑甜甜圈关联引擎 —— 5种关联检测 + 4种甜甜圈类型 |
