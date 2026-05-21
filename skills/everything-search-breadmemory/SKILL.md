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

**艾宾浩斯复习间隔**（天）：1, 2, 4, 7, 15, 30, 60, 120

每条知识记录自动追踪：
- `created_at`: 首次创建日期
- `review_count`: 已复习次数
- `last_reviewed_at`: 上次复习日期
- `next_review_at`: 下次应复习日期

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

### 各平台实现参考

| 平台 | 实现方式 |
|------|---------|
| **WorkBuddy** | 使用 `automation_update` 工具创建定时任务，调用对应脚本 |
| **Claude Code** | 使用 cron 定时调度 Python 脚本 |
| **Cursor** | 在 `.cursor/tasks.json` 中添加定时任务 |
| **通用（cron）** | `crontab -e` 添加定时 Python 调用 |
| **通用（手动）** | 用户每日手动触发"复习" |

## Agent 行为规范

使用本技能时，Agent 必须遵循：

1. **搜索结果先展示**：列出文件路径、大小、日期，让用户确认后再解析
2. **解析结果需归纳**：不是简单复制文件内容，而是提炼核心知识点
3. **面包屑条目须关联原文**：每条知识必须附带 `--source` 指向原文文件路径
4. **复习结果需反馈**：每日复习后，告知用户本次复习的条目数和下次复习时间
5. **自动化任务可信赖**：定时任务出错时需记录并向用户报告

## 数据存储

所有数据存储在 `~/.everything_search/`：

```
~/.everything_search/
├── breadcrumb.json      # 面包屑知识条目
├── config.json          # 配置（es.exe路径、艾宾浩斯参数等）
└── review_log.jsonl     # 复习历史日志
```

---

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `scripts/es_search.py` | Everything 搜索封装，检测/安装/搜索 |
| `scripts/breadcrumb.py` | 面包屑小本本 CRUD |
| `scripts/ebbinghaus.py` | 艾宾浩斯引擎 + 每日复习入口 |
