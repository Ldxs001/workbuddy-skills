---
name: local-rag-builder
version: 0.1.0
author: your-name-here
license: MIT
description: >
  本地 RAG 系统搭建技能，支持环境检测、嵌入模型管理、多种切分策略、向量知识库管理
tags: []
data_dir: ../.standardization/local-rag-builder/
external_data_dir:
sensitive_access: false
critical_write: false
permission_weight: LOW
trigger:
trigger_negative:

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

## 触发场景

当用户提到以下意图时触发本技能：
- `"/local-rag-builder"` 直接调用
- 用户描述任务包含：<!-- 填写核心触发动词，如"生成XX"、"分析XX" -->
- 用户要求输出格式为：<!-- 填写预期输出类型 -->

**不触发**：
- 用户仅询问概念、定义，不要求执行操作
- 用户明确要求使用其他指定技能

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | 主功能名称 | <!-- 一句话描述核心功能 --> |
| 2 | 辅助功能 | <!-- 可选 --> |
| 3 | 输出格式 | <!-- Markdown / HTML / JSON 等 --> |

### 渐进式文件索引

| 文件名 | 位置 | 说明 |
|--------|------|------|
| `references/guide.md` | 完整使用教程 | 参数说明和完整工作流 |
| `references/permissions.md` | 权限说明 | 权限扫描报告和风险说明 |
| `references/examples.md` | 示例集合 | 使用示例和输出样例 |

## 约束

<!-- 本技能特有的操作约束，每条一句话，最多 5 条 -->
- <!-- 例：`.md` 文件禁止使用 Write/Edit 工具更新 -->
- <!-- 例：更新后必须自审 0 ERROR 0 WARN -->

## 快速开始

```bash
# 最简用法
skill-sub local-rag-builder --input <input-file> --output <output-dir>
```

## 工作流程

1. **解析输入** — 读取用户输入文件或参数，验证格式
2. **执行核心逻辑** — 调用 `scripts/` 目录下的脚本进行处理
3. **输出结果** — 将结果写入输出目录，并生成摘要报告

> [R-06 渐进式加载] 详细工作流程见 `references/guide.md`

## 权限说明

本技能需要以下权限才能正常工作：

| 工具 | 访问级别 | 用途 |
|------|----------|------|
| Read | read-only | 读取输入文件和配置 |
| Write | write | 写入输出结果 |
| Bash | restricted | 运行内部处理脚本（仅限 `scripts/` 目录） |

- **不会**访问系统敏感路径或凭证文件
- **不会**向外部网络发送数据
- **不会**执行用户 Shell 配置文件（`.bashrc` / `.zshrc`）

---

> 反模式详见 `references/antipatterns.md`，常见问题详见 `references/faq.md`

> 本文档由 `skill-standardization` 生成，遵循 R-01~R-25 规范。
