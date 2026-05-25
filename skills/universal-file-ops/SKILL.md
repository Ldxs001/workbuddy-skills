---
name: universal-file-ops
version: 0.1.0
author: ['username-redacted']
license: MIT
description: 通用文件操作技能：支持常用文件（txt/py/html/md/docx/xlsx）增删查改，以及文件拷贝、移动、删除、重命名。含标准化 IO 接口、统一调度器、容灾回溯机制。
tags: ['file', 'operations', 'crud', 'copy', 'move', 'delete', 'rename', 'robust']
trigger_negative: true
section_workflow: true
artifact_paths: true
external_data_dir: true
sensitive_access: false
critical_write: false
permission_weight: MEDIUM
antipattern_reference: true
faq_reference: true
writing_standards: fix_terms
progressive_loading_explicit: true
antipattern_progressive: true
faq_progressive: true
---

# universal-file-ops

通用文件操作技能：支持常用文件增删查改与文件管理操作，标准化 IO 接口，统一调度，鲁棒可回溯。

## 触发场景

当用户提出以下意图时触发本技能：
- 创建/读取/更新/删除文件（txt、py、html、md、docx、xlsx 等）
- 拷贝、移动、重命名、删除文件或目录
- 批量文件操作（多文件同时处理）
- 要求对文件操作具备容灾回溯能力

**否定条件**（以下情况不触发）：
- 仅询问文件操作理论知识，不实际执行
- 涉及敏感路径（系统目录、凭证文件）的操作
- 用户明确说「不要使用 universal-file-ops」

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

| # | 功能 | 说明 |
|---|------|------|
| 1 | **文件 CRUD** | 支持 txt/py/html/md/docx/xlsx 增删查改，标准化 JSON IO 接口 |
| 2 | **文件管理操作** | 拷贝、移动、重命名、删除，支持单文件与批量 |
| 3 | **统一调度器** | `scripts/orchestrator.py` 支持串行/并行多任务编排 |
| 4 | **容灾回溯** | 操作前自动备份、支持回滚、操作日志审计 |
| 5 | **鲁棒性设计** | 重复执行稳定、异常自动恢复、幂等性保证 |

## 快速开始

```bash
# 查看所有可用操作
python scripts/orchestrator.py --list

# 读取文件内容
python scripts/text_crud.py --action read --file path/to/file.txt

# 写入文件内容（自动备份原文件）
python scripts/text_crud.py --action create --file path/to/file.txt --content "Hello"

# 拷贝文件（支持批量）
python scripts/file_ops.py --action copy --src path/to/src --dst path/to/dst

# 多操作串行执行（通过 orchestrator）
python scripts/orchestrator.py --batch batch_config.json

# batch_config.json 格式示例：
# {
#   "tasks": [
#     {"op": "text_crud", "args": {"action": "create", "file": "a.txt", "content": "Hello"}},
#     {"op": "file_ops",  "args": {"action": "copy",  "src": "a.txt",  "dst": "b.txt"}}
#   ],
#   "parallel": false,
#   "stop_on_error": true
# }
```

→ 完整 API 参考详见 `references/guide.md`

## 工作流程

1. **解析请求** → 识别操作类型（CRUD/管理）、目标文件、参数
2. **预检查** → 验证文件存在性、权限、路径合法性
3. **备份（如需要）** → 对写操作自动创建备份至 `skills/.standardization/universal-file-ops/data/backup/`
4. **执行操作** → 调用对应 `scripts/*.py`，标准化 JSON IO
5. **验证结果** → 检查操作是否成功、输出标准化结果
6. **记录日志** → 写入 `skills/.standardization/universal-file-ops/data/logs/ops.log`，支持审计回溯

**异常处理**：任何步骤失败 → 自动回滚（如已备份）→ 返回标准化错误 JSON

→ 详细工作流程详见 `references/guide.md`

→ 更多反模式详见 `references/antipatterns.md`

→ 更多常见问题详见 `references/faq.md`

## 权限说明

本技能权限权重：**MEDIUM**
- 仅操作用户明确指定的文件路径
- 不访问网络、不读取凭证/Token
- 备份目录限于 `skills/.standardization/universal-file-ops/data/backup/`
- 所有高风险操作（删除、覆盖）需显式确认

→ 详细权限说明详见 `references/permissions.md`
