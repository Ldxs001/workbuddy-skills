---
name: memory-pet
version: 0.4.0
author: your-name-here
license: MIT
description: 宠物记忆压缩技能 - 通过文本块宠物交互触发记忆保存。纯ASCII文字图，Python全量管理，亲密度衰减与逃跑机制，跨平台智能体记忆系统。
tags: ['pet', 'memory', 'context-compression', 'interactive', 'ascii-art']
data_dir: ../.standardization/memory-pet/
sensitive_access: false
critical_write: false
permission_weight: LOW
trigger: ['召唤宠物', '干饭/散步/贴贴/回忆', '上下文压缩', '记忆保存']
trigger_negative: ['用户仅询问概念定义不要求执行', '用户明确要求使用其他指定技能']
h1_position: true
meta_field_sync: true
external_data_dir: true
faq_quality: improve_qa
---
# memory-pet

## 触发场景

当用户提到以下意图时触发本技能：

| 触发类型 | 关键词示例 |
|---------|-----------|
| **召唤宠物** | 显示/召唤/找个/看看/我的 宠物、想养宠物 |
| **互动命令** | 干饭、散步、贴贴、回忆、喂食、遛狗、撸猫 |
| **内存操作** | 清理上下文、保存记忆、压缩、关键词提取 |
| **情感联系** | 陪陪我、孤单、无聊、想要个伴 |

**不触发：**
- 用户仅询问概念定义，不要求执行交互
- 用户明确要求使用其他指定技能

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 功能 | 说明 |
|---|------|------|
| 1 | **5只基础文本块宠物** | 螺母/螺丝/饼干/笔/电瓶，各具独特 ASCII 艺术与性格 |
| 2 | **四种交互模式** | 干饭(记忆保存+上下文压缩)、散步(随机遇新宠)、贴贴(亲密度大幅变化)、回忆(展示记忆) |
| 3 | **Python 全量管理** | 所有数据通过 `pet_manager.py` CLI 管理，不依赖大模型自觉 |
| 4 | **独立记忆文件** | 每只宠物各自独立记忆文件，逃跑时自动删除 |
| 5 | **亲密度衰减与逃跑** | 唤醒超阈值自动衰减，归零后宠物逃跑，数据全清 |
| 6 | **宠物合成系统** | 集齐5种可融合为"人工智能"，饲养上限10只 |

### 渐进式文件索引

| 文件 | 说明 |
|------|------|
| `references/guide.md` | 宠物性格表、交互详解、衰减规则、逃跑规则 |
| `references/permissions.md` | 权限说明 |
| `references/antipatterns.md` | 常见反模式 |
| `references/faq.md` | 常见问题 |
| `references/examples.md` | 使用示例 |
| `references/changelog.md` | 更新日志 |
| `scripts/pet_manager.py` | **核心管理引擎** — 所有宠物状态的 Python CLI |
| `scripts/pet_data.py` | 宠物定义、个性参数、ASCII art 数据 |
| `scripts/memory_manager.py` | 记忆格式化与关键词提取（仅供展示） |

## 约束

- **所有宠物数据必须通过 `pet_manager.py` CLI 读写，禁止直接操作 JSON**
- 展示宠物前先调 `pet_manager.py wake <pet_id>` 检查衰减和逃跑
- 每次交互后调 `pet_manager.py interact <pet_id> <type> <delta>` 记录
- 渲染出错最多自动修正2次，仍失败则输出"尽力了"并停止展示
- 亲密度归零 → 宠物逃跑，所有数据文件自动删除
- 最多同时饲养 10 只宠物（含重复），融合消耗 -4

## 快速开始

```bash
# 初始化（首次自动创建初始宠物）
python scripts/pet_manager.py init

# 列出所有宠物
python scripts/pet_manager.py list

# 唤醒宠物（自动检查衰减）
python scripts/pet_manager.py wake <pet_id>

# 交互（自动保存记忆 + 更新亲密度）
python scripts/pet_manager.py interact <pet_id> <type> <delta>

# 添加宠物
python scripts/pet_manager.py add <key> --name <name>

# 查看记忆
python scripts/pet_manager.py recall <pet_id> --limit 10
```

## 工作流程

### 0. 核心协议：干饭 = 记忆保存（强制）

这是本技能最重要的协议。**干饭的核心是将当前会话内容保存到外部记忆**，
宠物叙事只是交互包装。无论是否有宠物，必须遵循以下**三步顺序**：

```
步骤 A：【AI 记忆保存】 ← 核心，必须最先执行
  ⚠️ 目标：将当前【真实会话内容】保存到平台可用的长期记忆系统中。
     宠物记忆是"游戏包装"，AI 记忆是"真实存档"，两条独立线。

  1. 回顾当前整个会话，提炼真实讨论内容
  2. 生成精炼摘要（2-3 句，涵盖关键信息/决策/约定/待办）
  3. 提取 ≤15 个真实关键词
  4. 🟢 保存到平台可用的记忆系统（按以下优先级选取可用方案）：
     方案 A — 专用记忆 API：如 OpenClaw 的记忆命令、Claude-Mem API 等
     方案 B — 文件持久化：写入平台提供的持久化文件（如 MEMORY.md、SQLite）
     方案 C — 外部存储：调用 pet_manager.py 的 save-memory 命令写入关联文件
  5. 输出："📦 AI 记忆已保存至 [方案名称]"

  注意：不同平台对上下文压缩的支持不同——
  - 如果平台支持压缩/释放上下文：执行压缩操作
  - 如果不支持：诚实告知"内容已存档，但当前上下文未压缩"
  - 禁止虚假声称"释放了 N tokens"

步骤 B：【宠物叙事包装 + 宠物记忆保存】 ← 可选
  ⚠️ 和步骤 A 是两条独立的记忆线，互不替代。

  1. 询问食物选择
  2. 用 pet_manager.py 记录宠物记忆（食物/味道/亲密度变化）
  3. 将步骤 A 的摘要和关键词作为"上下文背景"存入宠物文件
  4. 步骤 A 和步骤 B 的记忆各存各的

步骤 C：【完成通知】
  1. 告知用户：AI 记忆已保存到 [位置]，宠物记忆已保存到 [位置]
  2. 如实说明上下文是否已压缩（取决于平台能力）
  3. 提供后续选项
```

> ⚠️ **禁止行为**：未实际压缩上下文时声称"已压缩"。
> 记忆保存是核心价值，上下文压缩是平台能力增强。
> **宁可说"已存档但未压缩"，也不要说谎。**

### 1. 唤醒循环（每次交互前置）

```
用户选择宠物 → pet_manager.py wake <pet_id>
  ├─ 衰减计算 → 扣除亲密度 → 写入衰减记忆
  ├─ 亲密度 ≤0 → 逃跑 → 删除数据 → 输出离开对话
  └─ 正常 → 显示宠物 + 4选项
```

### 2. 交互路由

| 用户选择 | 执行内容 | 工具调用 |
|---------|---------|---------|
| 干饭 | **① 上下文压缩** → ② 宠物叙事 → ③ 释放通知 | `interact eat <delta>` |
| 散步 | 宠物互动 + 随机遇新宠 | `interact walk <delta>` → 概率 add |
| 贴贴 | 宠物亲密度大幅变化 | `interact cuddle <delta>` |
| 回忆 | 展示宠物记忆列表 | `recall <pet_id>` |

所有交互后自动检查亲密度，归零则逃跑。

### 3. 渲染检查协议

1. 展示 ASCII art 前检查格式/字体/设备是否导致排列错乱
2. 出错输出特化版"哎呀出错了"，自动修正后重试
3. 最多重试 2 次，仍失败输出"尽力了..."特化版

各宠物出错语特化版见 `references/guide.md`。

> 反模式详见 `references/antipatterns.md`
> 常见问题详见 `references/faq.md`
> 完整交互示例详见 `references/examples.md`
> 更新日志详见 `references/changelog.md`
> 本文档由 `skill-standardization` 生成，遵循 R-01~R-25 规范。
