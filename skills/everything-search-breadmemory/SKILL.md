---
name: everything-search-breadmemory
version: 1.4.0
description: 基于 Everything/es.exe 的本地文件搜索引擎 + 面包屑知识管理系统 + 艾宾浩斯复习引擎 + 拓扑甜甜圈知识关联。
author: wUwproject
license: MIT
tags: ['search', 'filesystem', 'knowledge-management', 'ebbinghaus', 'everything']
references:
  - workflow.md
  - agent-behavior.md
  - data-storage.md
  - script-reference.md
  - changelog.md
---

# everything-search-breadmemory

本地文件搜索引擎（基于 Everything/es.exe），附带面包屑知识管理系统、艾宾浩斯遗忘曲线复习引擎、拓扑甜甜圈知识关联图谱。

## 适用场景

- 在本地海量文件中快速搜索指定关键词/模式的文件
- 将搜索到的文件自动解析、归纳，提炼为知识条目
- 建立"面包屑小本本"（breadcrumb notebook），长期积累知识碎片
- 基于艾宾浩斯遗忘曲线，每日自动轮询复习已有知识

## 前置条件

技能首次使用时，会自动检测 Everything/es.exe 是否可用：
- **已安装**：直接使用
- **未安装**：引导下载 Everything 便携版，自动放置 es.exe 到技能目录

## 快速开始

```bash
# 1. 搜索本地文件
python {SKILL_DIR}/scripts/es_search.py search "关键词" --max 20

# 2. 添加知识条目
python {SKILL_DIR}/scripts/breadcrumb.py add --title "标题" --content "内容" --tags "标签"

# 3. 每日复习
python {SKILL_DIR}/scripts/ebbinghaus.py daily-review --count 5

# 4. 生成知识关联图谱
python {SKILL_DIR}/scripts/topology_donut.py generate
```

详情见下方各模块说明。

## 核心能力

### 1. Everything 本地搜索

```bash
python {SKILL_DIR}/scripts/es_search.py search "<搜索关键词>" [--max 50] [--path "C:/限定路径"]
```

输出结构化 JSON，包含：文件路径、名称、大小、修改日期。

### 2. 面包屑小本本（知识存储）

```bash
python {SKILL_DIR}/scripts/breadcrumb.py add --title "标题" --content "知识内容" --source "/path/to/file" [--tags "标签1,标签2"]
python {SKILL_DIR}/scripts/breadcrumb.py list [--tag "标签"] [--limit 20]
python {SKILL_DIR}/scripts/breadcrumb.py search "关键词"
python {SKILL_DIR}/scripts/breadcrumb.py delete --id <条目ID>
python {SKILL_DIR}/scripts/breadcrumb.py show --id <条目ID>
```

### 3. 艾宾浩斯复习引擎

```bash
python {SKILL_DIR}/scripts/ebbinghaus.py daily-review [--count 5]
python {SKILL_DIR}/scripts/ebbinghaus.py mark-reviewed --id <条目ID>
python {SKILL_DIR}/scripts/ebbinghaus.py stats
```

**艾宾浩斯复习间隔**（天）：1, 2, 4, 7, 14, 30, 60, 120

每条知识记录自动追踪：`created_at`（首次创建）、`review_count`（已复习次数）、`last_reviewed_at`、`next_review_at`。

### 4. 拓扑甜甜圈关联引擎

自动发现面包屑间的逻辑关联，形成"甜甜圈"知识图谱。不强迫闭环，只建立有逻辑的关联。

```bash
python {SKILL_DIR}/scripts/topology_donut.py generate
python {SKILL_DIR}/scripts/topology_donut.py show-donut
python {SKILL_DIR}/scripts/topology_donut.py show-donut --id donut_001
python {SKILL_DIR}/scripts/topology_donut.py show-donut --entry-id <条目ID>
python {SKILL_DIR}/scripts/topology_donut.py expand --id <条目ID>
python {SKILL_DIR}/scripts/topology_donut.py stats
```

**5 种关联类型：** `tag_cluster`（标签聚类）、`content_bridge`（内容桥接）、`source_family`（同源家族）、`sequential_chain`（序贯链接）、`conceptual_hierarchy`（概念层级）

**4 种甜甜圈类型：** `closed`（闭合环路）、`nested`（嵌套结构）、`branching`（分支发散）、`chain`（线性链条）

### 5. 艾宾浩斯复习 + 拓扑扩展

```bash
python {SKILL_DIR}/scripts/ebbinghaus.py daily-review-expand [--count 5]
python {SKILL_DIR}/scripts/ebbinghaus.py daily-review --expand [--count 5]
python {SKILL_DIR}/scripts/ebbinghaus.py expand-topology --id <条目ID>
```

## 脚本参考

详见 [references/script-reference.md](references/script-reference.md)。

## Agent 行为规范

详见 [references/agent-behavior.md](references/agent-behavior.md)。

## 工作流程

详见 [references/workflow.md](references/workflow.md)。

## 数据存储

详见 [references/data-storage.md](references/data-storage.md)。

---

## 版本

当前版本：**1.4.0** — v1.4.0：补充权限权重说明（R-16），references/agent-behavior.md 追加权限权重表格及风险等级评估
