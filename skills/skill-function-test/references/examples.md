# skill-function-test — 使用示例

本文档提供本技能的常见使用场景和完整示例。

## 目录

1. [示例 1：基本用法](#示例-1基本用法)
2. [示例 2：批量处理](#示例-2批量处理)
3. [示例 3：自定义配置](#示例-3自定义配置)
4. [示例 4：错误处理](#示例-4错误处理)

---

## 示例 1：基本用法

### 场景描述

<!-- 描述一个简单的使用场景 -->

### 输入

`input.txt`:
```
<!-- 示例输入内容 -->
```

### 执行命令

```bash
python scripts/skill-function-test_main.py --input input.txt --output output/
```

### 预期输出

`output/summary.md`:
```markdown
<!-- 示例输出内容 -->
```

---

## 示例 2：批量处理

### 场景描述

<!-- 描述批量处理多个文件的场景 -->

### 输入

`inputs/` 目录包含多个文件：
```
inputs/
  ├── file1.txt
  ├── file2.txt
  └── file3.txt
```

### 执行命令

```bash
for file in inputs/*.txt; do
  python scripts/skill-function-test_main.py --input "$file" --output output/
done
```

### 预期输出

```
output/
  ├── file1_summary.md
  ├── file2_summary.md
  └── file3_summary.md
```

---

## 示例 3：自定义配置

### 场景描述

<!-- 描述使用自定义配置文件的场景 -->

### 配置文件

`references/config.json`:
```json
{
  "param1": "value1",
  "param2": 42,
  "enabled": true
}
```

### 执行命令

```bash
python scripts/skill-function-test_main.py --input input.txt --config references/config.json
```

---

## 示例 4：错误处理

### 场景描述

输入文件格式错误，查看错误处理和恢复流程。

### 输入（错误格式）

`bad_input.txt`:
```
<!-- 错误格式的内容 -->
```

### 执行命令

```bash
python scripts/skill-function-test_main.py --input bad_input.txt --output output/
```

### 预期错误输出

```
[ERROR] E002: 输入格式错误
  期望格式: <!-- 正确格式描述 -->
  实际内容: <!-- 错误内容描述 -->
  
建议: 请参考 `references/guide.md` 的"输入格式"章节
```

### 修复后重试

```bash
# 修复输入文件后重试
python scripts/skill-function-test_main.py --input fixed_input.txt --output output/ --retry
```

---

## 输出样例

### 样例 1：成功结果

```json
{
  "status": "success",
  "input_file": "input.txt",
  "output_dir": "output/",
  "result": {
    // 结果数据
  }
}
```

### 样例 2：部分成功（有警告）

```json
{
  "status": "partial_success",
  "input_file": "input.txt",
  "warnings": [
    "第 42 行数据格式异常，已跳过"
  ],
  "result": {
    // 部分结果数据
  }
}
```

---

> 更多示例欢迎通过 PR 贡献到本文件的后续章节。
