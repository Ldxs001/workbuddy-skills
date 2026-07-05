# 详细功能说明

> 本文件包含 color-toolkit 各核心功能的详细描述、参数说明和输出示例。

## 4. 无障碍颜色推荐

**函数**：`find_accessible(fixed_color, mode="fg"|"bg", font_size=16, font_weight="normal", target="AA", max_results=10)`

根据 WCAG 2.1 标准，自动推荐符合对比度要求的颜色。支持两种方向：

| 模式 | 固定色 | 推荐 | 典型场景 |
|------|--------|------|---------|
| `mode="fg"` | 背景色 | 文字色 | 已有背景颜色，选文字色 |
| `mode="bg"` | 文字色 | 背景色 | 已有文字颜色，选背景色 |

参数控制：
- **font_size**：支持 int（像素 px）、中文字号名（"小四"/"五号"/"小二"等）、pt 单位（"12pt"）、px 单位（"16px"）
- **font_weight**：自动配合字号判断大小文本（"小二"+加粗 = 大文本，AA 降至 3:1）
- **target**："AA"（默认 4.5:1）或 "AAA"（7:1）
- **max_results**：最大返回数（上限 **25**，防止穷举）
- 算法在 HSL 色相环上均匀采样，保证推荐色在色相上有多样性

```json
{
  "fixed_color": "#FFFFFF",
  "mode": "fg",
  "font_size": 16,
  "font_weight": "normal",
  "target": "AA",
  "is_large_text": false,
  "min_ratio": 4.5,
  "recommendations": [
    {"hex": "#943838", "name": "红", "contrast_ratio": "7.29:1", "level": "AAA"},
    {"hex": "#80664d", "name": "橙红", "contrast_ratio": "5.35:1", "level": "AA"}
  ],
  "total_candidates": 186,
  "total_found": 25
}
```

## 5. 互补色详情

**函数**：`get_complementary("#3498db")`
**输出**：返回原色和互补色的 HEX、RGB 完整编码，比 `get_palette("complementary")` 信息更全（含 RGB 分量表）。

```json
{
  "original": "#3498db",
  "complementary": "#db6f34",
  "original_rgb": {"r": 52, "g": 152, "b": 219},
  "complementary_rgb": {"r": 219, "g": 111, "b": 52}
}
```

## 6. 随机颜色生成

**函数**：`ColorCore.generate_random_color()`
**说明**：自动生成饱和度（50~90%）和亮度（40~70%）适中的随机颜色，避免过暗或过艳。支持批量生成并预览。

## 7. 颜色格式验证

**函数**：`ColorCore.is_valid_hex("#3498db")`
**说明**：校验字符串是否为合法 HEX 颜色（3 位或 6 位），不合法返回 False，不抛异常。

## 8. 多颜色比较

**说明**：同时比较多个颜色的色系、色温、亮度，并生成 HTML 对比预览。适用于选色阶段的横向对比。

## 9. 智能颜色推荐

**输入**：用户描述（中文/英文）
**处理**：LLM 解析语义 → 提取关键词 → 映射到色彩空间
**输出**：
- 主色（1个）
- 辅助色（2-3个）
- 强调色（1个）
- 背景/文字色建议

## 10. HTML 预览生成

生成的 HTML 包含：
- 颜色色块展示
- 渐变效果预览
- 对比度示例
- 文本可读性测试
- 无障碍合规提示
