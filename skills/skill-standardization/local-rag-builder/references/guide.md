# local-rag-builder — 完整使用教程

本地 RAG 系统搭建技能，支持环境检测、嵌入模型管理、多种切分策略、向量知识库管理

## 目录

1. [安装与依赖](#安装与依赖)
2. [快速开始](#快速开始)
3. [参数说明](#参数说明)
4. [工作流程详解](#工作流程详解)
5. [输出格式](#输出格式)
6. [常见问题](#常见问题)
7. [错误处理](#错误处理)

---

## 安装与依赖

### 依赖项

| 依赖 | 版本要求 | 用途 |
|------|----------|------|
| Python | >=3.8 | 运行脚本 |
| <!-- 其他依赖 --> | <!-- 版本 --> | <!-- 用途 --> |

### 安装步骤

1. 确保本技能已通过 `skill-standardization` 创建
2. 安装依赖：`pip install -r requirements.txt`（如有）
3. 验证安装：运行 `python scripts/local-rag-builder_main.py --help`

## 快速开始

```bash
# 最简用法
python scripts/local-rag-builder_main.py --input input.txt --output output/

# 带可选参数
python scripts/local-rag-builder_main.py --input input.txt --output output/ --verbose
```

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | path | 是 | - | 输入文件路径 |
| `--output` | path | 否 | `data/output/` | 输出目录 |
| `--verbose` | flag | 否 | `False` | 输出详细日志 |
| `--config` | path | 否 | `references/config.json` | 配置文件路径 |

## 工作流程详解

### 阶段 1：输入解析

- 读取 `--input` 指定的文件
- 验证文件格式和内容完整性
- 解析参数为内部数据结构

### 阶段 2：核心处理

- 调用核心算法/逻辑进行处理
- 支持的处理模式：
  - 模式 A：<!-- 描述 -->
  - 模式 B：<!-- 描述 -->

### 阶段 3：输出生成

- 将处理结果写入 `--output` 目录
- 生成摘要报告 `summary.md`
- 记录执行日志到 `data/logs/`

## 输出格式

### 输出文件列表

| 文件 | 格式 | 说明 |
|------|------|------|
| `summary.md` | Markdown | 处理摘要 |
| `result.json` | JSON | 结构化结果 |
| `details.csv` | CSV | 详细数据（可选） |

### 输出示例

```json
{
  "status": "success",
  "input_file": "input.txt",
  "output_dir": "output/",
  "processed_items": 42,
  "errors": []
}
```

## 常见问题

### Q: 输入文件格式不正确怎么办？
A: 技能会输出明确的错误信息，指出格式问题和期望的格式。请参考本文档"输入格式"章节。

### Q: 如何处理大文件？
A: 对于超过 10MB 的文件，建议使用流式处理模式，添加 `--stream` 参数。

## 错误处理

### 错误代码

| 代码 | 含义 | 处理方式 |
|------|------|----------|
| E001 | 输入文件不存在 | 检查文件路径 |
| E002 | 输入格式错误 | 参考"输入格式"章节 |
| E003 | 输出目录不可写 | 检查权限或换用 `--output` |
| E004 | 依赖缺失 | 运行 `pip install -r requirements.txt` |

### 错误恢复

- 所有错误都会记录到 `data/logs/error.log`
- 支持 `--retry` 参数进行自动重试（最多 3 次）
- 严重错误会生成 `data/rollback/` 目录用于回滚

---

> 本文档遵循 R-06 渐进式加载规范，由 `skill-standardization` 生成。
