# 流程钩子系统 — 使用说明

## 双档策略

| 档位 | 适用步骤 | 行为 |
|------|---------|------|
| **自动补齐** | init / backup / blueprint | 产物缺失时 Python 自动执行，LLM 不需要管 |
| **阻断指引** | scenario / function_test / s4 / gen_report | 前置缺失时 exit(1)，明确告诉 LLM 该执行什么命令 |

## 三步校验机制

| 校验点 | 时机 | 检查内容 | 阻断 |
|--------|------|---------|------|
| **入口** | 脚本启动时 | 前置步骤的制品存在性 | auto 补齐或 exit(1) |
| **中间钩** | 校验 LLM 产出 | `.test-config.json` / `.s4_noise_plan.json` | exit(1) "请先..." |
| **出口** | 脚本完成时 | 标记 done + 指引下一步 | 写入 .flow-state.json |

## 查看流程状态

```
python scripts/hooks.py status <skill-dir>
```
