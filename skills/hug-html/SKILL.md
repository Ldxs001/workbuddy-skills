---
name: hug-html
version: 
author: Ldxs
license: MIT
description: >
sensitive_access: false
critical_write: false
permission_weight: LOW
data_dir: ../.standardization/hug-html/data/
external_data_dir: true
faq_quality: improve_qa
antipattern_detail: add_detail
writing_standards: fix_terms
---


















# hug-html

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

## 触发场景

当用户提到以下内容时触发本技能：

- "生成 HTML 模板" / "HTML template" / "hug html"
- "编辑 HTML" / "可视化编辑 HTML" / "visual edit HTML"
- "HTML 模块" / "HTML module library"
- "填充 HTML 内容" / "fill HTML content"
- 输出格式：自包含 HTML 文件（粉紫→蓝绿渐变风格）

**不触发**：
- 用户仅询问 HTML 语法概念，无文件生成需求
- 用户明确请求其他特定技能

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

## 核心能力

| # | 能力 | 说明 |
|---|------|------|
| 1 | 生成 HTML 模板 | Python 生成带标准接口的 HTML 模板（通过 CSS 类名标识可编辑区域） |
| 2 | 可视化编辑界面 | Python 生成纯前端可编辑 HTML 界面（JS 处理所有编辑逻辑，无需后端） |
| 3 | 模块库组装 | 可复用 HTML 模块（颜色/字体/图片/布局）通过标准接口组合 |
| 4 | 内容填充 | 根据需求同时生成模板并填充内容 |

## 快速开始

```bash
python scripts/template_generator.py --output "../.standardization/hug-html/data/output/template.html" --type promo
python scripts/visual_editor.py --template "../.standardization/hug-html/data/output/template.html" --output "../.standardization/hug-html/data/output/editor.html"
python scripts/module_assembler.py --modules "gradient-purple,title-large,img-cover" --output "../.standardization/hug-html/data/output/assembled.html"
python scripts/content_filler.py auto --template "../.standardization/hug-html/data/output/template.html" --output "../.standardization/hug-html/data/output/filled.html"
```

## 工作流程

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

1. **解析需求** — 理解用户需要的 HTML 类型（宣传面板/产品介绍/技术说明/流程图）
2. **生成模板** — 调用 `template_generator.py` 生成带标准接口的 HTML 模板
3. **生成编辑界面**（可选）— 调用 `visual_editor.py` 生成纯前端可编辑 HTML 界面
4. **模块组装**（可选）— 调用 `module_assembler.py` 组合可复用模块
5. **内容填充**（可选）— 调用 `content_filler.py` 填充具体内容
6. **输出结果** — 将最终 HTML 写入 `../.standardization/hug-html/data/output/`，生成摘要

## 权限说明

本技能需要以下权限才能正常工作：

| 工具 | 访问级别 | 用途 |
|------|----------|------|
| Read | 只读 | 读取输入文件、模块库、样式预设 |
| Write | 写入 | 将输出 HTML 文件写入 `../.standardization/hug-html/data/output/` |
| Bash | 受限 | 运行内部处理脚本（限制在 `scripts/` 目录内） |

- **不会**访问系统敏感路径或凭证文件
- **不会**向外部网络发送数据
- **不会**执行用户 Shell 配置文件（`.bashrc` / `.zshrc`）

## 主要工作流程

本技能使用三阶段执行框架（执行 → 审查 → 推进）：

### 阶段 1：执行
- 读取用户输入参数（模板类型、样式预设、模块列表等）
- 调用 `scripts/` 目录中的脚本进行处理
- 捕获执行结果和错误

### 阶段 2：审查
- 验证输出 HTML 文件已生成
- 检查 HTML 格式合规性（自包含，无外部依赖）
- 将执行日志记录到 `../.standardization/hug-html/data/logs/`

### 阶段 3：推进
- 向用户输出最终结果（文件路径或 HTML 预览）
- 更新进度文件（如有）
- 若发生错误，进入错误处理流程

---

## 附录：详细文档索引

| 文档 | 内容 |
|------|------|
| `references/guide.md` | 完整使用教程和参数说明 |
| `references/permissions.md` | 权限扫描报告和风险说明 |
| `references/examples.md` | 使用示例和输出样本 |
| `references/module-library.md` | 可复用模块库说明 |
| `references/style-presets.md` | 样式预设系统说明 |
| `references/call-chains.md` | 调用链定义（skill-sub） |
| `references/antipatterns.md` | 反模式手册 |
| `references/faq.md` | 常见问题解答 |

> 本文档由 `skill-standardization v2.38.6` 生成，遵循 R-01~R-24 规范。
