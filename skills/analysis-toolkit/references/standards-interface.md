# 标准接口与模板管理

## 概述

analysis-toolkit 从 v1.3.0 引入了**标准注册表 + 模板管理**机制，让计算函数不再硬编码公式，而是通过查标准注册表获取参数。

## 架构

```
LLM/智能体（从标准文档提取字段）
  ↓ 调用 register() ───┐
                        ▼
               ┌─────────────────┐
               │   标准注册表     │ ← JSON 持久化 (.standardization/.../standards.json)
               │ (StandardRegistry)│
               └────────┬────────┘
                        │ get_lod_loq_params(standard)
                        ▼
               ┌─────────────────┐
               │  计算函数        │
               │ (calc_lod_loq)  │
               └─────────────────┘

               ┌─────────────────┐
               │   模板管理器     │ ← JSON 持久化 (.standardization/.../templates.json)
               │ (TemplateManager)│
               └────────┬────────┘
                        │ apply(template_id)
                        ▼
               ┌─────────────────┐
               │  默认配置 + 标准列表│
               └─────────────────┘
```

## 标准注册表

### 标准数据模型

| 字段 | 类型 | 必需 | 说明 |
|------|------|:----:|------|
| `standard_id` | str | ✅ | 唯一标识，如 `gbt27417` |
| `name` | str | ✅ | 标准简称，如 `GB/T 27417-2017` |
| `full_name` | str | ✅ | 标准全称 |
| `industry` | list[str] | ✅ | 适用行业 |
| `applicable_functions` | list[str] | ✅ | 适用函数列表 |
| `parameters` | dict | ✅ | 公式参数键值对 |
| `formulas` | dict | ✅ | 公式描述 |
| `sigma_sources_supported` | list[str] | | 支持的 sigma 来源 |
| `notes` | str | | 补充说明 |

### LLM 注册接口

智能体/LLM 需要从标准文档中提取以下信息用于注册：

1. **standard_id** — 标准号去符号，如 `GB/T 27417-2017` → `gbt27417`
2. **name** — 标准号原样
3. **full_name** — 标准封面标题
4. **industry** — 从"适用范围"章节提取
5. **applicable_functions** — 根据公式类型判断（如 LOD 公式 → `calc_lod_loq`）
6. **parameters** — 公式中的系数
7. **formulas** — 标准原文公式
8. **sigma_sources_supported** — 标准中规定的 sigma 测定方法

**Python 注册代码：**
```python
from scripts.standards.registry import get_registry
reg = get_registry()
reg.register({
    "standard_id": "gbt5009_295",
    "name": "GB 5009.295-2023",
    "full_name": "食品安全国家标准 化学分析方法验证通则",
    "industry": ["食品检测", "理化检验"],
    "applicable_functions": ["calc_lod_loq"],
    "parameters": {"lod_factor": 3, "loq_factor": 10},
    "formulas": {"lod": "LOD = 3σ/b", "loq": "LOQ = 10σ/b"},
})
```

**CLI 注册（从 JSON 文件）：**
```bash
python scripts/standards/registry.py register my_standard.json
```

### 查询

```bash
# 列出所有标准
python scripts/standards/registry.py list

# 按行业查询
python scripts/standards/registry.py list-by-industry 食品检测

# 按函数查询
python scripts/standards/registry.py list-by-function calc_lod_loq

# 查看标准详情
python scripts/standards/registry.py get gbt27417
```

## 模板管理

### 模板数据模型

| 字段 | 类型 | 必需 | 说明 |
|------|------|:----:|------|
| `template_id` | str | ✅ | 唯一标识，如 `food-testing` |
| `name` | str | ✅ | 模板名称 |
| `industry` | str | ✅ | 所属行业 |
| `description` | str | ✅ | 模板用途说明 |
| `standards` | list[str] | ✅ | 引用的标准 ID 列表 |
| `default_config` | dict | | 默认计算参数 |
| `applicable_scenarios` | list[str] | | 适用分析场景 |
| `notes` | str | | 补充说明 |

### LLM 创建模板接口

创建模板需从用户需求提取：
1. **template_id** — 行业英文简写
2. **name** — 中文模板名称
3. **industry** — 所属行业
4. **description** — 模板覆盖的业务范围
5. **standards** — 该行业常用的标准 ID 列表
6. **default_config** — 最常用的参数默认值
7. **applicable_scenarios** — 该行业做哪些分析

**示例：**
```python
from scripts.standards.template_manager import get_manager
tm = get_manager()
tm.create({
    "template_id": "food-testing",
    "name": "食品检验检测标准体系",
    "industry": "食品检测",
    "description": "适用于食品理化检验的常用国家标准体系",
    "standards": ["gbt27417"],
    "default_config": {"lod_loq_standard": "gbt27417"},
    "applicable_scenarios": ["方法验证", "标准曲线"],
})
```

### 模板操作

```bash
# 列出所有模板
python scripts/standards/template_manager.py list

# 查看模板详情
python scripts/standards/template_manager.py get food-testing

# 搜索模板
python scripts/standards/template_manager.py search 食品

# 应用模板（获取配置）
python scripts/standards/template_manager.py apply food-testing

# 删除模板
python scripts/standards/template_manager.py delete food-testing
```

## 内置数据

### 已注册标准

| standard_id | 名称 | 适用行业 |
|:-----------:|------|----------|
| `gbt27417` | GB/T 27417-2017 | 化学分析、食品检测、环境监测、药品检测 |
| `ich` | ICH Q2(R1) / 中国药典 2020版 | 药品检测、生物制品、化学药品 |

### 内置模板

| template_id | 名称 | 行业 | 引用标准 | 适用场景 |
|:-----------:|------|:----:|:--------:|:--------:|
| `food-testing` | 食品检验检测标准体系 | 食品检测 | gbt27417 | 室内质控、方法验证、标准曲线、回收率 |
| `pharmaceutical-testing` | 药品检验检测标准体系 | 药品检测 | ich | 方法验证、标准曲线、LOD/LOQ |
