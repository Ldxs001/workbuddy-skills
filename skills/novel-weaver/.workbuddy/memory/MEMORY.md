# novel-weaver 项目记忆

## 结尾收束验证系统（v1.7.0 新增）

### 架构
- **三要素**：plan_chapter 标记 → context_loader 命题框 → verify_ending 验证
- **验证原则**：只读末子结构内容 + project 配置，不通读全文
- **收尾类型标签**：末章末子结构概述以 `【收尾类型: 封闭式|开放式|悬停式】` 结尾，LLM 生成，plan_chapter 自动解析

### 三类检查
| 类型 | 项数 | 硬性通过要求 |
|------|------|-------------|
| 封闭式 | 4 | 全部通过 |
| 开放式 | 4（2硬+2软） | 2硬全过 + 2软至少1过 |
| 悬停式 | 6 | 全部通过（不支持自动修复→人工） |

### 门禁
- `ending_verify` 门禁在 `finalize-novel` 中与 `fidelity` 双阻断
- 报告写入 `data/ending_report.md`
