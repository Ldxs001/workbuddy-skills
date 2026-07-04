---
name: color-toolkit-turn
data_dir: ../.standardization/color-toolkit/
license: MIT
description: 专业颜色工具集，支持颜色编码转换、对比度计算、智能颜色推荐、HTML预览生成。适用于UI设计、无障碍开发、配色方案生成等场景。
author: wUwproject
version: 3.4.1
tags: ['color', 'color-conversion', 'contrast', 'accessibility', 'design', 'wcag']
trigger: ['颜色转换', '对比度计算', '颜色推荐', '配色方案', '色彩空间', 'HEX.*RGB', 'HSL', 'HSV', 'CMYK', '色差', 'WCAG']
trigger_negative: ['不触发', '不需要颜色工具', '与其他无关']
sensitive_access: false
critical_write: false
permission_weight: LOW
external_data_dir: true
meta_field_sync: true
faq_unparsable: reformat
create_permissions_md: true
data_dir_compliance: true
trigger_quality: refine_triggers
---
# Color Toolkit - 专业颜色工具集

## 触发条件

**正向触发：**
- "把这个颜色转换一下" — 颜色编码转换（HEX/RGB/HSL/HSV/CMYK）
- "计算这个颜色的对比度" — 对比度计算（WCAG/APCA/CIELAB/CIEDE2000）
- "给我推荐一个配色方案" — 配色方案生成
- "这个颜色对盲人友好吗" — 无障碍（WCAG 合规性检查）
- "生成这个颜色的预览页面" — HTML 预览生成
- "帮我推荐一个科技感的颜色" — 智能颜色推荐
- "随机生成几个颜色" — 随机颜色生成

**否定条件：**
- 简单问答、闲聊、问候（不需要本技能）
- 单步任务（不需要结构化执行）

## 核心能力

> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。

### 渐进式文件索引

| 文件名 | 分类 | 包含内容 | 审计关联 |
| -------- |------| ---------- |----------|
| `references/examples.md` | 输出示例 | 各功能输出格式示例 | R-25 |
| `references/faq.md` | 常见问题 | 常见疑问与解答 | R-19 |
| `references/antipatterns.md` | 规范指南 | 反模式与注意事项 | R-18 |
| `references/changelog.md` | 版本管理 | 更新日志 | R-24 |
| `references/features.md` | 功能说明 | 详细功能参数和输出示例 | R-17 |
| `references/permissions.md` | 权限说明 | 权限风险与安全声明 | R-15, R-16 |
| `references/LICENSE.md` | 许可协议 | MIT 开源许可证 | R-26 |

Color Toolkit 是一个通用的颜色处理工具包，提供：
- **颜色编码转换**：HEX ↔ RGB ↔ HSL ↔ HSV ↔ CMYK 全支持
- **对比度计算**：WCAG 2.1、APCA、CIELAB ΔE*ab、CIEDE2000 四种算法
- **无障碍推荐**：固定背景色推荐文字色，或固定文字色推荐背景色，按字号/字重/目标等级筛选（上限25种）
- **调色板生成**：互补色（2色）、三色组（120°）、矩形四色组（90°）、类似色（30°间隔）
- **互补色详情**：返回原色+互补色的完整编码信息
- **随机颜色生成**：自动生成饱和度和亮度适中的随机颜色
- **颜色格式验证**：校验字符串是否为合法颜色格式
- **多颜色比较**：同时对比多个颜色的色系、色温、亮度
- **智能颜色推荐**：根据用户描述生成完整配色方案
- **HTML预览生成**：单色/多色 HTML 预览，含色块、渐变、对比度、UI组件

## 核心功能

### 1. 颜色编码转换

```text
输入格式支持：
- HEX: #FF5733, #F53
- RGB: rgb(255, 87, 51), 255, 87, 51
- HSL: hsl(11, 100%, 60%), 11, 100, 60
- HSV: 11, 100, 60
- CMYK: 0, 66, 100, 0

输出格式：
- HEX: #FF5733
- RGB: RGB(r=255, g=87, b=51)
- HSL: HSL(h=11.0, s=100.0, l=60.0)
- HSV: HSV(h=11, s=100, v=60)
- CMYK: CMYK(c=0, m=66, y=100, k=0)
```

### 2. 对比度计算（四种算法）

| 算法 | 用途 | 评估标准 |
| ------ |------| ---------- |
| WCAG 2.1 | 无障碍标准 | ≥4.5:1 (AA) / ≥7:1 (AAA) |
| APCA | 现代对比度 | ≥45 Lc (可读) / ≥75 Lc (优秀) |
| CIELAB ΔE*ab | 精确色差 | ≤2 (不可辨) / ≤10 (微小) |
| CIEDE2000 | 专业色差 | ≤1 (完美) / ≤2 (接近) |

### 3. 调色板生成（色彩和谐方案）

基于色相环角度间隔生成色彩和谐方案，所有颜色继承主色的饱和度和明度：

| 类型 | 间隔 | 颜色数 | 说明 |
| ------ |------| -------- |------|
| 互补色 (Complementary) | 180° | 2色 | 色环正对面，对比最强烈 |
| 三色组 (Triadic) | 120° | 3色 | 等边三角形分布，均衡和谐 |
| 矩形四色组 (Tetradic) | 90° | 4色 | 矩形四点分布，丰富多变 |
| 类似色 (Analogous) | 30° | 3色 | 相邻色阶，温和统一 |


### 4~10. 更多功能

> 详细说明、参数列表和输出示例 → 详见核心能力的渐进式文件索引

## 使用方式

直接描述需求即可，AI 会自动调用颜色转换、对比度计算、调色板生成等核心功能。

> 输出格式详情 → 详见 渐进式文件索引表

## 技术实现

- **依赖**：Python 3.8+，仅标准库（math, re, random, dataclasses, typing）
- **文件结构**：`SKILL.md` + `references/`（examples/faq/antipatterns/changelog）

## 使用限制

| 约束项 | 说明 |
| -------- |------|
| **输入范围** | HEX 支持 3/6 位格式；RGB 值自动裁剪 0-255；HSL/HSV 角度 0-360 |
| **性能** | 颜色转换无外部依赖，毫秒级响应 |
| **环境要求** | Python ≥ 3.8，仅标准库，无额外依赖 |

> 常见使用误区 → 详见核心能力的渐进式文件索引


```text
用户：#FF5733 是什么颜色？
助手：
- **HEX**: #FF5733
- **RGB**: RGB(r=255, g=87, b=51)
- **HSL**: HSL(h=11, s=100%, l=60%)
- **色系**: 暖色 / 橙红系
- **亮度**: 0.384（较高）
- **预览**: [生成HTML预览]

用户：计算这个颜色和白色的对比度
助手：
- **WCAG 2.1**: 3.97:1 (大文本AA级) ⚠️
- **APCA**: 58.2 Lc (良好)
- **结论**: 小文本可能不符合AA标准，建议增加对比度

用户：给我一套春天主题的配色
助手：
- **主色**: #4CAF50 (生机绿)
- **辅助**: #E8F5E9 (浅芽绿), #FF9800 (迎春黄)
- **强调**: #E91E63 (桃花粉)
- **预览**: [生成春意盎然的HTML预览]

用户：给我一个蓝色的矩形四色组方案
助手：基于 #3498db 生成 90° 间隔的四色组：
- #3498DB (蓝) → #34DBDB (青) → #DB6F34 (橙红) → #DB346F (紫红)
- **预览**: [生成四色组HTML]

用户：#FF5733 的互补色是什么？
助手：
- **原色**: #FF5733 (橙红)
- **互补色**: #335CFF (靛蓝)
- **对比度**: WCAG 3.97:1 (大文本AA级)

用户：帮我随机生成5个颜色看看
助手：随机生成 5 个颜色：
- #E8574A | 红橙系 | 暖色
- #4AB89D | 青绿系 | 冷色
- #B84AC4 | 紫系 | 冷色
- #C4A84A | 橙黄系 | 暖色
- #4A6BC4 | 蓝色系 | 冷色
- **预览**: [生成随机色HTML]

用户：比较一下 #FF0000 #00FF00 #0000FF
助手：
- #FF0000 | 红色系 | 暖色 | 亮度 0.213
- #00FF00 | 绿色系 | 中性 | 亮度 0.715
- #0000FF | 蓝色系 | 冷色 | 亮度 0.072
- **预览**: [生成对比HTML]

用户：#FFFFFF 背景下我该用什么文字颜色？
助手：基于白色背景 (#FFFFFF)，推荐以下 AA 级文字色（16px）：
- #943838 | 红 | 7.29:1 AAA
- #59804d | 绿 | 4.55:1 AA
- #4d7380 | 蓝绿 | 5.15:1 AA
- ...共推荐 25 种，已按色相分散选取
- **预览**: [生成 HTML 效果展示]

用户：我有固定文字色 #333，帮我推荐背景色
助手：基于深灰文字 (#333333)，推荐以下 AA 级背景色（16px）：
- #FFF5E6 | 浅橙 | 14.5:1 AAA
- #E6FFE6 | 浅绿 | 14.8:1 AAA
- #E6F0FF | 浅蓝 | 14.2:1 AAA
- ...共推荐 25 种，已按色相分散选取
```

## CLI 快速参考

| 子命令 | 功能 | 示例 |
| -------- |------| ------ |
| `convert` | 颜色转换 | `python cli.py convert "#3498db"` |
| `contrast` | 对比度 | `python cli.py contrast "#000" "#fff"` |
| `complementary` | 互补色详情 | `python cli.py complementary "#FF5733"` |
| `palette` | 调色板 | `python cli.py palette "#3498db" --type tetradic` |
| `preview` | HTML预览 | `python cli.py preview "#3498db" --output color.html` |
| `recommend` | 智能推荐 | `python cli.py recommend "科技感蓝色" --preview` |
| `random` | 随机颜色 | `python cli.py random --count 5 --preview` |
| `validate` | 格式验证 | `python cli.py validate "#3498db"` |
| `compare` | 多色比较 | `python cli.py compare "#FF0000" "#00FF00"` |
| `accessible` | 无障碍推荐 | `python cli.py accessible "#FFF" --mode fg --font-size 16 --target AA` |

> 详见核心能力的渐进式文件索引
