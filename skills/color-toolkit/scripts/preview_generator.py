#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Color Toolkit — 三层架构 HTML 报告生成器

架构:
  算法层 (color_toolkit.py)  →  渲染层 (本文件)  →  骨架 (HTML 模板)
  
  算法函数提供数据，render_* 模块渲染为 <section>，骨架组合为完整页面。

用法:
  assemble_report("#3498db", modules=["color-info", "tetradic", "contrast-pair"])
  assemble_report("#FFF", modules=["accessible-fg", "text-preview"], font_size="小四")
"""
import os
from typing import List, Dict, Any, Optional
from color_toolkit import (
    ColorCore, convert_color, get_contrast, get_palette,
    get_complementary, find_accessible,
)


# ═══════════════════════════════════════════════════════════════
# 1. 骨架 (HTML 模板)
# ═══════════════════════════════════════════════════════════════

HTML_SKELETON = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
:root {{ --primary:{primary};--complementary:{comp};--text-dark:#1a1a1a;--text-light:#fff;--bg-light:#f8f9fa;--border:#dee2e6; }}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.6;color:var(--text-dark);background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;}}
.container{{max-width:1000px;margin:0 auto;background:white;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.3);overflow:hidden;}}
.content{{padding:30px;}}
h2{{color:var(--text-dark);margin:30px 0 20px;padding-bottom:10px;border-bottom:2px solid var(--primary);font-size:1.5rem;}}
h3{{color:var(--text-dark);margin:20px 0 15px;font-size:1.2rem;}}
section{{background:white;border-radius:12px;padding:25px;margin-bottom:25px;box-shadow:0 2px 10px rgba(0,0,0,0.05);}}
.color-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;}}
.color-item{{border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);}}
.color-preview{{height:100px;display:flex;align-items:center;justify-content:center;}}
.hex-label{{font-size:1.2rem;font-weight:bold;text-shadow:0 1px 2px rgba(0,0,0,0.2);}}
.color-details{{background:white;padding:15px;}}
.detail-row{{display:flex;justify-content:space-between;padding:5px 0;font-size:0.85rem;}}
.detail-label{{color:#888;}}
.detail-value{{font-family:monospace;color:#333;}}
.swatches-row{{display:flex;gap:15px;flex-wrap:wrap;justify-content:center;}}
.color-swatch{{display:inline-flex;align-items:center;justify-content:center;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);}}
.swatch-info{{text-align:center;padding:10px;}}
.swatch-info .hex{{font-weight:bold;font-size:1rem;}}
.color-values{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:20px 0;}}
.value-card{{background:var(--bg-light);padding:15px;border-radius:8px;border-left:4px solid var(--primary);}}
.value-card .label{{font-size:0.85rem;color:#666;margin-bottom:5px;}}
.value-card .value{{font-size:1.1rem;font-weight:600;font-family:"SF Mono",Monaco,monospace;}}
.gradient-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px;}}
.gradient-box{{height:60px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-weight:500;text-shadow:0 1px 3px rgba(0,0,0,0.3);}}
.contrast-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin:20px 0;}}
.contrast-box{{padding:20px;border-radius:8px;text-align:center;}}
.contrast-box .box-label{{font-size:0.8rem;opacity:0.7;margin-bottom:5px;}}
.contrast-box .box-sample{{font-size:1.2rem;font-weight:bold;margin-top:10px;}}
.contrast-table,.accessible-table{{width:100%;border-collapse:collapse;margin:20px 0;}}
.contrast-table th,.contrast-table td,.accessible-table th,.accessible-table td{{padding:10px 14px;text-align:left;border-bottom:1px solid var(--border);}}
.contrast-table th,.accessible-table th{{background:var(--bg-light);font-weight:600;}}
.contrast-table .value{{font-family:"SF Mono",Monaco,monospace;font-weight:bold;}}
.badge{{display:inline-block;padding:4px 10px;border-radius:12px;color:white;font-size:0.85rem;font-weight:500;}}
.gradient-preview{{margin:20px 0;}}
.ui-preview{{display:flex;flex-direction:column;gap:15px;margin:20px 0;}}
.ui-button{{display:inline-block;padding:12px 24px;background:var(--primary);color:white;border:none;border-radius:8px;font-size:1rem;cursor:pointer;}}
.ui-button.outline{{background:transparent;border:2px solid var(--primary);color:var(--primary);}}
.ui-button.complement{{background:var(--complementary);color:white;}}
.ui-card{{background:white;border:1px solid var(--border);border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.05);}}
.ui-card-header{{background:var(--primary);color:white;padding:15px;margin:-20px -20px 20px -20px;border-radius:10px 10px 0 0;}}
.accessible-swatch{{display:inline-block;width:16px;height:16px;border-radius:3px;vertical-align:middle;margin-right:8px;border:1px solid rgba(0,0,0,0.1);}}
.accessible-meta{{display:flex;gap:30px;margin:15px 0;padding:15px;background:var(--bg-light);border-radius:8px;flex-wrap:wrap;}}
.accessible-meta-item{{text-align:center;}}
.accessible-meta-item .label{{font-size:0.8rem;color:#888;}}
.accessible-meta-item .value{{font-size:1.2rem;font-weight:600;font-family:monospace;}}
.text-card{{padding:25px;border-radius:12px;text-align:center;}}
.text-card .title{{font-size:28px;font-weight:bold;margin-bottom:10px;}}
.text-card .body{{font-size:16px;margin-bottom:5px;}}
.text-card .small{{font-size:12px;}}
.text-card .footnote{{margin-top:12px;font-size:0.85rem;}}
@media(max-width:600px){{.swatches-row{{flex-direction:column;align-items:center;}}}}
</style>
</head>
<body>
<div class="container">
{header}
<div class="content">
{body}
<div style="text-align:center;padding:20px;color:#666;font-size:0.9rem;">由 Color Toolkit 自动生成</div>
</div>
</div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# 2. 渲染模块 (每个模块 = 一个算法功能的 HTML 呈现)
# ═══════════════════════════════════════════════════════════════

def _header_html(hex_color: str, subtitle: str = "", title_text: str = "Color Toolkit") -> str:
    """生成页面标题横幅。"""
    comp = get_complementary(hex_color)["complementary"]
    return f'<div class="header" style="background:linear-gradient(135deg,{hex_color} 0%,{comp} 100%);padding:40px;text-align:center;color:white;"><h1 style="font-size:2.5rem;margin-bottom:10px;text-shadow:0 2px 4px rgba(0,0,0,0.2);">{title_text}</h1><div style="font-size:1.2rem;opacity:0.9;">{subtitle}</div></div>'


def _render(module_name: str, data: dict) -> str:
    """通过模块名查找并执行对应的渲染函数。"""
    fn = _MODULE_REGISTRY.get(module_name)
    if fn is None:
        return f"<!-- 未知模块: {module_name} -->"
    return fn(data)


# ── 模块: color-info (颜色编码转换) ──

def _color_info(data: dict) -> str:
    c = data["info"]
    hex_color = c["hex"]
    comp = get_complementary(hex_color)["complementary"]
    rgb = c["rgb"]
    hsl = c["hsl"]
    tc = "#fff" if float(c["luminance"]) < 0.5 else "#000"
    return f'''
<section><h2>🎨 颜色编码转换</h2>
<div style="display:flex;gap:20px;margin:20px 0;">
<div class="color-swatch" style="flex:1;height:150px;border-radius:12px;background:{hex_color};flex-direction:column;color:{tc};box-shadow:0 4px 15px rgba(0,0,0,0.2);">
<div style="font-size:0.9rem;opacity:0.8;margin-bottom:5px;">主色</div>
<div style="font-size:1.5rem;font-weight:bold;">{hex_color.upper()}</div>
</div>
</div>
<div class="color-values">
<div class="value-card"><div class="label">HEX</div><div class="value">{hex_color.upper()}</div></div>
<div class="value-card"><div class="label">RGB</div><div class="value">rgb({rgb["r"]},{rgb["g"]},{rgb["b"]})</div></div>
<div class="value-card"><div class="label">HSL</div><div class="value">hsl({hsl["h"]},{hsl["s"]}%,{hsl["l"]}%)</div></div>
<div class="value-card"><div class="label">HSV</div><div class="value">hsv({c["hsv"]["h"]},{c["hsv"]["s"]}%,{c["hsv"]["v"]}%)</div></div>
<div class="value-card"><div class="label">CMYK</div><div class="value">cmyk({c["cmyk"]["c"]}%,{c["cmyk"]["m"]}%,{c["cmyk"]["y"]}%,{c["cmyk"]["k"]}%)</div></div>
<div class="value-card"><div class="label">亮度</div><div class="value">{c["luminance"]}</div></div>
<div class="value-card"><div class="label">灰度</div><div class="value">Gray({c["grayscale"]})</div></div>
<div class="value-card"><div class="label">色系</div><div class="value">{c["family"]}</div></div>
<div class="value-card"><div class="label">色温</div><div class="value">{c["temperature"]}</div></div>
</div></section>'''


# ── 模块: contrast-pair (指定两色的对比度评测) ──

def _contrast_pair(data: dict) -> str:
    c1 = data.get("color1", data["hex"])
    c2 = data.get("color2", "#888888")
    label = data.get("contrast_label", "")
    cd = get_contrast(c1, c2, "all")
    wp = cd["wcag2"]["pass"]
    ap = cd["apca"]["pass"]
    return f'''
<section><h2>♿ 对比度评测</h2>
<h3>{label or f"{c1.upper()} vs {c2.upper()}"}</h3>
<div class="contrast-grid">
<div class="contrast-box" style="background:{c1};color:{c2};"><div class="box-label">背景: {c1.upper()}</div><div class="box-sample" style="font-size:24px;">Aa</div><div class="box-sample" style="font-size:16px;">前景: {c2.upper()}</div></div>
<div class="contrast-box" style="background:{c2};color:{c1};"><div class="box-label">背景: {c2.upper()}</div><div class="box-sample" style="font-size:24px;">Aa</div><div class="box-sample" style="font-size:16px;">前景: {c1.upper()}</div></div>
<div class="contrast-box" style="background:{c1};color:{c2};"><div class="box-sample" style="font-size:24px;">大号 24px</div><div class="box-sample" style="font-size:16px;">正文 16px</div></div>
</div>
<table class="contrast-table"><thead><tr><th>算法</th><th>数值</th><th>等级</th><th>无障碍</th></tr></thead>
<tbody>
<tr><td>WCAG 2.1</td><td class="value">{cd["wcag2"]["value"]}</td><td><span class="badge" style="background:{cd["wcag2"]["color"]}">{cd["wcag2"]["level"]}</span></td><td>{"✅ 通过" if wp else "❌ 未通过"}</td></tr>
<tr><td>APCA</td><td class="value">{cd["apca"]["value"]} Lc</td><td><span class="badge" style="background:{cd["apca"]["color"]}">{cd["apca"]["level"]}</span></td><td>{"✅ 通过" if ap else "❌ 未通过"}</td></tr>
<tr><td>CIELAB ΔE*ab</td><td class="value">{cd["cielab"]["value"]}</td><td><span class="badge" style="background:{cd["cielab"]["color"]}">{cd["cielab"]["level"]}</span></td><td>-</td></tr>
<tr><td>CIEDE2000</td><td class="value">{cd["ciede2000"]["value"]}</td><td><span class="badge" style="background:{cd["ciede2000"]["color"]}">{cd["ciede2000"]["level"]}</span></td><td>-</td></tr>
</tbody></table></section>'''


# ── 模块: palette-xxx (调色板, 四个类型共用) ──

def _palette_render(data: dict) -> str:
    pt = data.get("palette_type", "tetradic")
    title = data.get("palette_title", "")
    colors = get_palette(data["input"], pt)["colors"]
    cards = ""
    for c in colors:
        info = convert_color(c)
        rgb = info["rgb"]
        tc = "#fff" if float(info["luminance"]) < 0.5 else "#000"
        cards += f'<div class="color-item"><div class="color-preview" style="background:{c};color:{tc};"><div class="hex-label">{c.upper()}</div></div><div class="color-details"><div class="detail-row"><span class="detail-label">RGB</span><span class="detail-value">rgb({rgb["r"]},{rgb["g"]},{rgb["b"]})</span></div><div class="detail-row"><span class="detail-label">HSL</span><span class="detail-value">hsl({info["hsl"]["h"]},{info["hsl"]["s"]}%,{info["hsl"]["l"]}%)</span></div><div class="detail-row"><span class="detail-label">CMYK</span><span class="detail-value">cmyk({info["cmyk"]["c"]}%,{info["cmyk"]["m"]}%,{info["cmyk"]["y"]}%,{info["cmyk"]["k"]}%)</span></div><div class="detail-row"><span class="detail-label">亮度</span><span class="detail-value">{info["luminance"]}</span></div></div></div>'
    return f'<section><h2>🎨 {title}</h2><div class="color-grid">{cards}</div></section>'


def _palette_swatch_row(data: dict) -> str:
    pt = data.get("palette_type", "tetradic")
    title = data.get("palette_title", "")
    colors = get_palette(data["input"], pt)["colors"]
    swatches = ""
    for c in colors:
        info = convert_color(c)
        tc = "#fff" if float(info["luminance"]) < 0.5 else "#000"
        swatches += f'<div class="color-swatch" style="background:{c};width:120px;height:120px;flex-direction:column;"><div class="swatch-info" style="color:{tc};"><div class="hex">{c.upper()}</div></div></div>'
    return f'<section><h2>🎨 {title}</h2><div class="swatches-row">{swatches}</div></section>'


# ── 模块: gradient (渐变预览) ──

def _gradient(data: dict) -> str:
    colors = data.get("gradient_colors") or get_palette(data["input"], "triadic")["colors"]
    if len(colors) < 2:
        return ""
    lg = "linear-gradient(135deg," + ",".join(colors) + ")"
    lgr = "linear-gradient(135deg," + ",".join(reversed(colors)) + ")"
    rg = "radial-gradient(circle," + ",".join(colors) + ")"
    return f'''<section><h2>🌈 渐变效果</h2><div class="gradient-row">
<div class="gradient-box" style="background:{lg};">135° 线性渐变</div>
<div class="gradient-box" style="background:{lgr};">反向渐变</div>
<div class="gradient-box" style="background:{rg};">径向渐变</div>
</div></section>'''


# ── 模块: ui-preview (UI组件预览) ──

def _ui_preview(data: dict) -> str:
    hex_color = data["hex"]
    comp = get_complementary(hex_color)["complementary"]
    return f'''<section><h2>🧩 UI组件预览</h2><div class="ui-preview">
<div class="ui-card"><div class="ui-card-header" style="background:{hex_color};">卡片标题</div><p>主色作为卡片标题背景的示例。</p></div>
<div><button class="ui-button" style="background:{hex_color};">主要按钮</button>
<button class="ui-button outline" style="border:2px solid {hex_color};color:{hex_color};">描边按钮</button>
<button class="ui-button complement" style="background:{comp};">强调按钮</button></div>
</div></section>'''


# ── 模块: text-preview (文字效果预览，基于 find_accessible) ──

def _text_preview(data: dict) -> str:
    """文字效果预览：基于无障碍推荐算法，在背景上展示推荐文字色的可读性。"""
    bg = data["hex"]
    fs = data.get("font_size", "小四")
    fw = data.get("font_weight", "normal")
    target = data.get("target", "AA")
    result = find_accessible(bg, mode="fg", font_size=fs, font_weight=fw, target=target, max_results=6)
    recs = result["recommendations"]

    cards = ""
    for r in recs:
        tc = r["hex"]
        level_badge = "AAA" if r["level"] == "AAA" else "AA"
        cards += f'''
<div class="text-card" style="background:{bg};">
<div class="title" style="color:{tc};">Aa 标题</div>
<div class="body" style="color:{tc};">正文示例文字，展示可读性效果。</div>
<div class="small" style="color:{tc};">小号标注 12px</div>
<div class="footnote" style="color:{tc if float(convert_color(tc)["luminance"]) > 0.5 else "#000" if float(convert_color(bg)["luminance"]) > 0.5 else "#fff"};">{tc} · {r["contrast_ratio"]} · <span class="badge" style="background:{"#4CAF50" if level_badge=="AAA" else "#8BC34A"};">{level_badge}</span></div>
</div>'''

    meta = ""
    meta += f'<div class="accessible-meta-item"><div class="label">背景色</div><div class="value">{bg}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">字号</div><div class="value">{fs}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">字重</div><div class="value">{fw}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">目标</div><div class="value">{target}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">推荐数</div><div class="value">{result["total_found"]}</div></div>'

    return f'''<section><h2>📝 文字效果预览</h2>
<div class="accessible-meta">{meta}</div>
<p style="margin-bottom:15px;">以下展示基于对比度算法自动推荐的前景色在</p><p style="font-weight:500;margin-bottom:15px;">背景色 {bg} 上的实际呈现效果：</p>
<div class="contrast-grid">{cards}</div></section>'''


# ── 模块: accessible-fg / accessible-bg (无障碍颜色推荐列表) ──

def _accessible_list(data: dict) -> str:
    mode = data.get("accessible_mode", "fg")
    bg = data["hex"]
    fs = data.get("font_size", "小四")
    fw = data.get("font_weight", "normal")
    target = data.get("target", "AA")
    result = find_accessible(bg, mode=mode, font_size=fs, font_weight=fw, target=target, max_results=25)
    recs = result["recommendations"]

    rows = ""
    for r in recs:
        swatch = f'<span class="accessible-swatch" style="background:{r["hex"]};"></span>'
        level_color = "#4CAF50" if r["level"] == "AAA" else "#8BC34A" if r["level"] == "AA" else "#FFC107"
        rows += f'<tr><td>{swatch}{r["hex"]}</td><td>{r["name"]}</td><td>{r["contrast_ratio"]}</td><td><span class="badge" style="background:{level_color};">{r["level"]}</span></td></tr>'

    mode_label = "推荐前景/文字色" if mode == "fg" else "推荐背景色"
    meta = ""
    meta += f'<div class="accessible-meta-item"><div class="label">固定色</div><div class="value">{result["fixed_color"]}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">模式</div><div class="value">{mode_label}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">字号</div><div class="value">{fs}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">字重</div><div class="value">{fw}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">目标</div><div class="value">{result["target"]}</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">最低对比度</div><div class="value">{result["min_ratio"]}:1</div></div>'
    meta += f'<div class="accessible-meta-item"><div class="label">推荐总数</div><div class="value">{result["total_found"]}</div></div>'

    return f'''<section><h2>♿ 无障碍颜色推荐</h2>
<div class="accessible-meta">{meta}</div>
<table class="accessible-table"><thead><tr><th>颜色</th><th>色名</th><th>对比度</th><th>等级</th></tr></thead>
<tbody>{rows}</tbody></table></section>'''


# ── 模块: compare (多色比较) ──

def _compare(data: dict) -> str:
    colors = data.get("compare_colors", [data["hex"]])
    rows = ""
    for c in colors:
        info = convert_color(c)
        tc = "#fff" if float(info["luminance"]) < 0.5 else "#000"
        rows += f'<tr><td><span class="accessible-swatch" style="background:{c};"></span>{c.upper()}</td><td>{info["family"]}</td><td>{info["temperature"]}</td><td>{info["luminance"]}</td></tr>'
    return f'''<section><h2>🔍 多色比较</h2>
<table class="accessible-table"><thead><tr><th>颜色</th><th>色系</th><th>色温</th><th>亮度</th></tr></thead>
<tbody>{rows}</tbody></table></section>'''


# ── 模块: validate (格式验证) ──

def _validate(data: dict) -> str:
    color_str = data.get("validate_input", data["input"])
    valid = ColorCore.is_valid_hex(color_str)
    status = "✅ 有效" if valid else "❌ 无效"
    color = "#4CAF50" if valid else "#F44336"
    return f'''<section><h2>🔍 格式验证</h2>
<div style="padding:20px;background:var(--bg-light);border-radius:8px;text-align:center;">
<div style="font-size:1.5rem;color:{color};font-weight:bold;">{status}</div>
<div style="font-size:1rem;margin-top:8px;font-family:monospace;">{color_str}</div>
</div></section>'''


# ── 模块: random (随机颜色) ──

def _random(data: dict) -> str:
    count = data.get("random_count", 5)
    colors = [ColorCore.generate_random_color() for _ in range(count)]
    swatches = ""
    for c in colors:
        info = convert_color(c)
        tc = "#fff" if float(info["luminance"]) < 0.5 else "#000"
        swatches += f'<div class="color-swatch" style="background:{c};width:120px;height:120px;flex-direction:column;"><div class="swatch-info" style="color:{tc};"><div class="hex">{c.upper()}</div><div class="rgb" style="font-size:0.75rem;opacity:0.8;">{info["family"]}</div></div></div>'
    return f'<section><h2>🎲 随机颜色</h2><div class="swatches-row">{swatches}</div></section>'


# ── 模块: code-list (颜色代码列表) ──

def _code_list(data: dict) -> str:
    colors = data.get("code_colors", [data["hex"]])
    items = "".join(f"{i+1}. {c.upper()}\n" for i, c in enumerate(colors))
    return f'<section><h2>📋 颜色代码</h2><pre style="background:#1a1a1a;color:#a9dc76;padding:20px;border-radius:8px;overflow-x:auto;font-family:monospace;">{items}</pre></section>'


# ═══════════════════════════════════════════════════════════════
# 3. 模块注册表
# ═══════════════════════════════════════════════════════════════

_MODULE_REGISTRY = {
    # ── 颜色编码 ──
    "color-info":        _color_info,
    # ── 调色板（简名/中文别名） ──
    "tetradic":          lambda d: _palette_swatch_row({**d, "palette_type":"tetradic", "palette_title":"矩形四色组 (Tetradic)"}),
    "triadic":           lambda d: _palette_swatch_row({**d, "palette_type":"triadic", "palette_title":"三色组 (Triadic)"}),
    "analogous":         lambda d: _palette_swatch_row({**d, "palette_type":"analogous", "palette_title":"类似色 (Analogous)"}),
    "complementary":     lambda d: _palette_swatch_row({**d, "palette_type":"complementary", "palette_title":"互补色 (Complementary)"}),
    "四项对比色":         lambda d: _palette_swatch_row({**d, "palette_type":"tetradic", "palette_title":"矩形四色组 (Tetradic)"}),
    "三色组":            lambda d: _palette_swatch_row({**d, "palette_type":"triadic", "palette_title":"三色组 (Triadic)"}),
    "类似色":            lambda d: _palette_swatch_row({**d, "palette_type":"analogous", "palette_title":"类似色 (Analogous)"}),
    "互补色":            lambda d: _palette_swatch_row({**d, "palette_type":"complementary", "palette_title":"互补色 (Complementary)"}),
    # 带详情版的调色板
    "tetradic-detail":   lambda d: _palette_render({**d, "palette_type":"tetradic", "palette_title":"矩形四色组 (Tetradic)"}),
    "triadic-detail":    lambda d: _palette_render({**d, "palette_type":"triadic", "palette_title":"三色组 (Triadic)"}),
    "analogous-detail":  lambda d: _palette_render({**d, "palette_type":"analogous", "palette_title":"类似色 (Analogous)"}),
    # ── 渐变 ──
    "gradient":          _gradient,
    # ── 对比度 ──
    "contrast-pair":     _contrast_pair,
    # ── 文字效果 ──
    "text-preview":      _text_preview,
    "文字效果":           _text_preview,
    # ── 无障碍推荐 ──
    "accessible-fg":     _accessible_list,
    "accessible-bg":     lambda d: _accessible_list({**d, "accessible_mode":"bg"}),
    # ── UI 组件 ──
    "ui-preview":        _ui_preview,
    # ── 多色比较 ──
    "compare":           _compare,
    # ── 格式验证 ──
    "validate":          _validate,
    # ── 随机颜色 ──
    "random":            _random,
    # ── 代码列表 ──
    "code-list":         _code_list,
}


# ═══════════════════════════════════════════════════════════════
# 4. 内置模板 + 流程钩子
# ═══════════════════════════════════════════════════════════════

# 内置模板 = 预定义的模块组合
_BUILTIN_TEMPLATES = {
    "full":        ["color-info", "tetradic", "triadic", "analogous", "complementary", "gradient", "contrast-pair", "ui-preview"],
    "quick":       ["color-info", "tetradic"],
    "color-info":  ["color-info"],
    "accessibility": ["accessible-fg", "text-preview"],
    "palettes":    ["tetradic", "triadic", "analogous", "complementary", "gradient"],
    "contrast":    ["color-info", "contrast-pair"],
    "preview":     ["color-info", "triadic", "analogous", "gradient", "ui-preview"],
    "validator":   ["validate"],
    "explore":     ["color-info", "tetradic", "triadic", "analogous", "complementary", "gradient", "contrast-pair", "ui-preview", "random"],
}

# 流程钩子: 算法函数名 → 对应的渲染模块名
# 当某个函数被调用时，自动注入其对应的 HTML 模块
_FUNCTION_HOOKS = {
    "convert_color":         ["color-info"],
    "get_contrast":          ["contrast-pair"],
    "get_complementary":     ["color-info"],
    "find_accessible":       ["accessible-fg", "text-preview"],
    "get_palette":           None,  # 由模板或手动 modules 决定具体哪种调色板
    "generate_random_color": ["random"],
    "recommend_color":       ["color-info"],
}

# 中文场景关键词 → 推荐模板
_SCENE_TEMPLATES = {
    "转换": "color-info",
    "对比": "contrast",
    "无障碍": "accessibility",
    "推荐.*色": "accessibility",
    "调色": "palettes",
    "预览": "preview",
    "四色|矩形": "quick",
    "验证|是否有效": "validator",
    "随机": "random",
    "全.*功能|所有|全部|完整": "full",
}


# ═══════════════════════════════════════════════════════════════
# 5. 组装器
# ═══════════════════════════════════════════════════════════════

def resolve_modules(
    color_input: str = None,
    modules: Optional[List[str]] = None,
    template: Optional[str] = None,
    hooks: Optional[List[str]] = None,
    scene: Optional[str] = None,
) -> List[str]:
    """
    解析最终模块列表。优先级: modules > template > scene > hooks > full

    Parameters
    ----------
    modules : list[str], optional
        手动指定的模块列表（优先级最高）
    template : str, optional
        内置模板名
    hooks : list[str], optional
        已调用的算法函数名列表，自动注入对应模块
    scene : str, optional
        中文场景描述，自动匹配模板

    Returns
    -------
    list[str] — 最终模块名列表，去重保留顺序
    """
    # 优先级1: 手动 modules（最优先）
    if modules is not None:
        return modules

    # 优先级2: 指定模板
    if template is not None:
        base = list(_BUILTIN_TEMPLATES.get(template, ["color-info"]))
    elif scene is not None:
        # 中文场景自动匹配
        import re
        matched = None
        for pattern, tmpl in _SCENE_TEMPLATES.items():
            if re.search(pattern, scene):
                matched = tmpl
                break
        base = list(_BUILTIN_TEMPLATES.get(matched, ["color-info"]))
    else:
        # 默认
        base = []

    # 优先级3: hooks 注入
    if hooks:
        for fn_name in hooks:
            hook_modules = _FUNCTION_HOOKS.get(fn_name)
            if hook_modules:
                for m in hook_modules:
                    if m not in base:
                        base.append(m)

    return base if base else ["color-info"]


def assemble_report(
    color_input: str,
    modules: Optional[List[str]] = None,
    template: Optional[str] = None,
    hooks: Optional[List[str]] = None,
    scene: Optional[str] = None,
    title: Optional[str] = None,
    output_path: Optional[str] = None,
    **extra,
) -> str:
    """
    通用报告组装器 — 任意组合原子模块。

    架构: 算法层提供数据 → 渲染层渲染<section> → 骨架层组合为完整HTML

    Parameters
    ----------
    color_input : str
        颜色值 (HEX/RGB/HSL)
    modules : list[str], optional
        手动指定模块列表（优先级最高，覆盖 template/hooks/scene）
    template : str, optional
        内置模板名: full / quick / color-info / accessibility / palettes / contrast / preview / validator / explore
    hooks : list[str], optional
        已调用的算法函数名列表（如 ["convert_color","find_accessible"]），自动注入对应模块
    scene : str, optional
        中文场景描述（如 "帮我转换颜色"），自动匹配内置模板
    title : str, optional
        页面标题，默认自动生成
    output_path : str, optional
        输出路径
    **extra : 
        color1/color2/contrast_label — 对比度评测用
        font_size/font_weight/target — 无障碍/文字预览用
        compare_colors — 多色比较用
        validate_input — 格式验证用
        random_count — 随机颜色数量
        code_colors — 代码列表用
        gradient_colors — 渐变用

    Returns
    -------
    str — 完整 HTML
    """
    info = convert_color(color_input)
    hex_color = info["hex"]
    subtitle = f'{info.get("name","")} — {info.get("temperature","")} / {info.get("family","")}'

    # 解析最终模块列表
    final_modules = resolve_modules(
        color_input=color_input,
        modules=modules,
        template=template,
        hooks=hooks,
        scene=scene,
    )

    # 自动生成标题
    if title is None:
        if template:
            title = f"Color Toolkit — {template} 模板"
        elif scene:
            title = f"Color Toolkit — {scene}"
        else:
            title = f"颜色报告 — {hex_color}"

    # 构造数据上下文
    data = {
        "input": color_input,
        "hex": hex_color,
        "info": info,
        **extra,
    }

    # 渲染每个模块
    body_parts = [_header_html(hex_color, subtitle, title)]
    for mod in final_modules:
        part = _render(mod, data)
        if part:
            body_parts.append(part)

    # 插入骨架
    html = HTML_SKELETON.format(
        title=title,
        primary=hex_color,
        comp=get_complementary(hex_color)["complementary"],
        header="",
        body="".join(body_parts),
    )

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path
    return html


# ═══════════════════════════════════════════════════════════════
# 5. 向后兼容
# ═══════════════════════════════════════════════════════════════

def generate_full_preview_html(color_input: str,
                                title: str = "颜色预览",
                                show_complementary: bool = True,
                                show_contrast: bool = True,
                                output_path: Optional[str] = None) -> str:
    """（兼容旧接口）生成完整的颜色预览HTML页面"""
    return assemble_report(color_input, template="full", title=title, output_path=output_path)


def generate_palette_page_html(colors: List[str],
                                palette_title: str = "配色方案",
                                output_path: Optional[str] = None) -> str:
    """（兼容旧接口）调色板预览。"""
    if not colors:
        return ""
    return assemble_report(colors[0], modules=["color-info", "tetradic", "triadic", "analogous", "complementary", "gradient", "code-list"],
                           title=palette_title, output_path=output_path, code_colors=colors)


if __name__ == "__main__":
    outdir = r"C:\Users\sm001\WorkBuddy\2026-06-17-14-19-03"

    def test(desc, html, filename):
        with open(f"{outdir}/{filename}", 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ {desc}: {len(html)} chars -> {filename}")

    # ── 用模板 ──
    test("模板: full",        assemble_report("#3498db", template="full"), "tmpl_full.html")
    test("模板: palettes",    assemble_report("#E91E63", template="palettes"), "tmpl_palettes.html")
    test("模板: accessibility", assemble_report("#FFFFFF", template="accessibility"), "tmpl_accessibility.html")
    test("模板: contrast",    assemble_report("#FF5733", template="contrast"), "tmpl_contrast.html")
    test("模板: quick",       assemble_report("#4CAF50", template="quick"), "tmpl_quick.html")
    test("模板: explore",     assemble_report("#9C27B0", template="explore"), "tmpl_explore.html")

    # ── hooks 注入 ──
    test("hooks: convert_color",  assemble_report("#3498db", hooks=["convert_color"], color2="#FFFFFF"), "hook_convert.html")
    test("hooks: find_accessible", assemble_report("#FFF", hooks=["find_accessible"], font_size="小四"), "hook_accessible.html")
    test("hooks: 多个函数",       assemble_report("#3498db", hooks=["convert_color","get_contrast","generate_random_color"], color2="#FFF", contrast_label="#3498db vs #FFF"), "hook_multi.html")

    # ── 中文场景 ──
    test("场景: 转换颜色",  assemble_report("#3498db", scene="帮我转换颜色"), "scene_convert.html")
    test("场景: 对比色",    assemble_report("#E91E63", scene="算对比度"), "scene_contrast.html")
    test("场景: 调色方案",  assemble_report("#4CAF50", scene="调色方案"), "scene_palette.html")
    test("场景: 随机",      assemble_report("#888", scene="随机颜色"), "scene_random.html")

    # ── 自定义 modules ──
    test("自定义: 四项对比色+文字效果", assemble_report("#3498db", modules=["四项对比色", "文字效果"]), "custom_tetradic_text.html")
    test("自定义: 单个模块",          assemble_report("#FF5733", modules=["contrast-pair"], color2="#FFF"), "custom_single.html")

    # 旧接口
    generate_full_preview_html("#3498db", output_path=f"{outdir}/tmpl_compat.html")
    print("✅ 旧接口兼容")

    print(f"\n🎉 内置模板: {list(_BUILTIN_TEMPLATES.keys())}")
    print(f"   流程钩子: {list(_FUNCTION_HOOKS.keys())}")
    print(f"   场景匹配: {list(_SCENE_TEMPLATES.keys())}")

