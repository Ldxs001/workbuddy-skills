# SVG 拼接工具 — 内置字符集

> **加载时机**：当用户需要了解字符集详情、许可证信息或拼接模式对比时加载。

## Font Awesome Free（默认）

**来源**：`@fortawesome/fontawesome-free` v7.2.0
**许可**：CC BY 4.0 + SIL OFL 1.1 + MIT
**支持字符**：`0-9`、`A-Z`（共36个）
**输入处理**：小写字母自动转为大写

**特性**：
- viewBox 高度统一为 512，宽度各异（256/320/384/448/576）
- 每个字符有独立的 advance_ratio，间距计算精确
- Y=0 在顶部（标准 SVG 坐标系）

**许可证说明**：
所有生成的 SVG 文件内部包含归属声明注释：
```xml
<!-- Icons provided by Font Awesome Free (CC BY 4.0) https://fontawesome.com/license/free -->
```

## 四种拼接模式对比

| 模式 | 函数 | 输入 "ABC" 示例 | 数量 |
|------|------|-----------------|------|
| 模式1 | `compose_sequence` | ABC | 1 |
| 模式2 | `compose_permutations` | ABC, ACB, BAC, BCA, CAB, CBA | 6 |
| 模式3 | `compose_combinations` | AAA, AAB, AAC... CCC (27个) | 27 |
| 模式4 | `compose_limited` | A, B, C, AB, AC, BA, BC, CA, CB | 9 |

## 字符集对比

| 字符集 | 0-9 | A-Z | a-z | 来源 |
|--------|-----|-----|-----|------|
| **FA Free（默认）** | ✅ | ✅ | ✅（自动转大写） | @fortawesome/fontawesome-free |
