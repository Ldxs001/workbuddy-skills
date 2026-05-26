---
name: universal-file-ops
author: ['eniuswei']
version: 
description: 为普通大模型/智能体用户提供一站式文件操作与 Python 代码质量保障能力。v1.1.0：重建 python_env.py，修复 _log() 输出到 stderr，修复 utils.py VENV_DIR 定义顺序，18/18 功能测试通过。
tags: ['file', 'operations', 'crud', 'copy', 'move', 'delete', 'rename', 'robust', 'python', 'code-quality', 'sandbox-testing', 'error-codes', 'network-retry', 'llm-agent']
data_dir: ../.standardization/universal-file-ops/
license: MIT
trigger_negative: true
external_data_dir: true
audience: llm-agent
sensitive_access: false
critical_write: false
permission_weight: MEDIUM
writing_standards: fix_terms
---








# universal-file-ops

> **受众**：本技能专为**普通大模型/智能体用户**设计，非专业开发者。目标是让智能体能规范地使用 Python 创造工具脚本，输出即正确，无需反复调试。

## 触发场景

**正向触发词**（满足任一即触发）：
- 「帮我规范地处理文件…」「检查 Python 脚本规范」「生成测试」
- 「帮我搭建 Python 环境」「安装 Python 包」「切换 Python 版本」
- 「这个脚本有什么问题」「帮我 OO 化这个 Python 文件」

**否定条件**（满足任一项即不触发）：
- 用户明确说「只用系统 Python，不用技能」
- 任务仅需单次文件读取，无需规范化/质量保证

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

1. **通用文件操作** — 标准化 IO、原子写入、自动备份、错误码输出
2. **Python 代码质量保障** — 规范化（`scripts/py_tools.py normalize`）、代码审查（`review`）、OO 化建议（`oo-ify`）、测试生成（`gen-test`）
3. **Python 环境管理** — 版本安装/切换/包管理/干净重装（`scripts/python_env.py`，含网络重试）
4. **脚本类型区分** — 自动识别临时脚本 vs 正式工具，临时脚本豁免 600 行 OO 化限制
5. **沙箱测试** — 生成的测试在临时 venv 中自动执行验证，确保可用

→ 详见 [references/guide.md](references/guide.md) 完整使用指南  
→ 反模式参见 [references/antipatterns.md](references/antipatterns.md)  
→ 常见问题参见 [references/faq.md](references/faq.md)

## 工作流程

1. **理解需求** — 读取用户输入，判断是文件操作还是 Python 代码任务
2. **选择工具** — 文件操作使用内置函数；Python 任务调用 `scripts/py_tools.py` 或 `scripts/python_env.py`
3. **执行前检查** — 检查路径合法性、Python 环境就绪状态、脚本类型
4. **执行操作** — 调用对应脚本，捕获标准化错误码（UFO-XXXX）
5. **输出结果** — 成功返回结构化数据；失败返回通俗易懂错误提示（含脚本名称、行号、错误码）
6. **沙箱验证**（Python 任务）— 测试生成后在沙箱内执行验证，确保可用

## 错误输出规范

所有错误均返回标准化 JSON 格式：

```json
{
  "error_code": "UFO-2001",
  "script": "scripts/py_tools.py",
  "line": 173,
  "message": "这个 Python 文件用了 Tab 缩进，标准写法是用 4 个空格",
  "suggestion": "运行 scripts/py_tools.py normalize 自动修复，或把 Tab 改成 4 个空格"
}
```

→ 完整错误码手册参见 [references/error_codes.md](references/error_codes.md)  
→ Python 编码规范参见 [references/py_standards.md](references/py_standards.md)
