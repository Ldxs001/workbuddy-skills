#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Color Toolkit — 原子组件架构 HTML 报告生成器 v2

架构:
  算法层 → 原子组件(atom_*, 1:1数据记录) + 固定组合(comp_*, 固定数量)
        → LLM建议插槽(tips, 唯一token点) → 组装引擎(compose/assemble)

用法:
  # 1. 单条对比一条: 1个 atom_contrast_card
  # 2. 3个对比: 3个 atom_contrast_card
  # 3. 颜色转换: 1个 comp_color_info (包含1个色块+8个属性卡片)
  # 4. 完整报告: assemble_report(..., atoms=[...], composites=[...], tips=[...])

向后兼容: generate_full_preview_html, generate_palette_page_html
"""
import os
from typing import List, Dict, Any, Optional
from color_toolkit import (
    ColorCore, convert_color, get_contrast, get_palette,
    get_complementary, find_accessible,
)


# ═══════════════════════════════════════════════════════════════
# 1. 骨架 + CSS
# ═══════════════════════════════════════════════════════════════

# 原子化 CSS: 按组件类型命名空间，统一视觉系统
ATOM_CSS = """
:root {
  --primary:#3498db; --complementary:#db6f34;
  --text-dark:#1a1a1a; --text-light:#fff;
  --bg-light:#f8f9fa; --border:#e8e8e8;
  --card-shadow:0 2px 8px rgba(0,0,0,0.08);
  --radius:10px; --radius-sm:6px;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Roboto,sans-serif;
  line-height:1.6;color:var(--text-dark);
  background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
  min-height:100vh;padding:20px;
}
.atom-container{
  max-width:1000px;margin:0 auto;background:white;
  border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.3);overflow:hidden;
}
.atom-body{padding:30px;}
.atom-header{
  padding:40px;text-align:center;
  text-shadow:0 2px 4px rgba(0,0,0,0.2);
}
.atom-header h1{font-size:2.5rem;margin-bottom:10px;}
.atom-header .sub{font-size:1.2rem;opacity:0.9;}

/* ─── 统一卡片基类 ─── */
.atom-card{
  background:#fff;border-radius:var(--radius);
  box-shadow:var(--card-shadow);overflow:hidden;
}

/* ─── 统一容器 ─── */
.atom-grid{
  display:grid;gap:16px;margin:14px 0;
}
.atom-grid.cols-2{grid-template-columns:repeat(auto-fill,minmax(280px,1fr));}
.atom-grid.cols-3{grid-template-columns:repeat(auto-fill,minmax(200px,1fr));}
.atom-grid.cols-4{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));}
@media(max-width:640px){
  .atom-grid.cols-2,.atom-grid.cols-3,.atom-grid.cols-4{grid-template-columns:1fr;}
}
.atom-flex{
  display:flex;flex-wrap:wrap;gap:16px;margin:14px 0;
}

/* ─── 节标题 ─── */
.atom-section-title{
  font-size:1.25rem;font-weight:600;margin:28px 0 14px;
  padding-bottom:8px;border-bottom:2px solid var(--primary);color:var(--text-dark);
}

/* ─── 元信息条 ─── */
.atom-meta{
  display:flex;gap:24px;margin:12px 0;padding:14px 18px;
  background:var(--bg-light);border-radius:var(--radius-sm);flex-wrap:wrap;
}
.atom-meta-item{text-align:center;}
.atom-meta-item .lbl{font-size:0.75rem;color:#999;}
.atom-meta-item .val{font-size:1rem;font-weight:600;font-family:monospace;}

/* atom:swatch — 单个色块 */
.atom-swatch{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  border-radius:var(--radius);box-shadow:var(--card-shadow);
  width:200px;height:150px;position:relative;overflow:hidden;
  transition:transform .15s;
}
.atom-swatch:hover{transform:translateY(-3px);}
.atom-swatch .hex-lbl{
  font-size:1.05rem;font-weight:700;font-family:monospace;
  background:rgba(0,0,0,0.15);padding:4px 12px;border-radius:var(--radius-sm);
  backdrop-filter:blur(2px);
}
.atom-swatch .tag{
  position:absolute;top:8px;right:8px;
  font-size:11px;padding:2px 8px;border-radius:8px;
  background:rgba(0,0,0,0.2);color:#fff;
}
.atom-swatch.full{width:100%;height:80px;border-radius:var(--radius-sm);flex-direction:row;gap:12px;}

/* atom:value-card — 单条属性卡片 */
.atom-value-card{
  background:var(--bg-light);padding:12px 14px;border-radius:var(--radius-sm);
  border-left:3px solid var(--primary);min-width:140px;flex:1;
}
.atom-value-card .lbl{font-size:0.8rem;color:#888;margin-bottom:4px;}
.atom-value-card .val{
  font-size:1rem;font-weight:600;font-family:"SF Mono",Monaco,monospace;color:#333;
}
.atom-value-grid{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:10px;margin:14px 0;
}

/* atom:contrast-card — 单条对比度卡片 */
.atom-contrast-card{
  background:#fff;border-radius:var(--radius);overflow:hidden;
  box-shadow:var(--card-shadow);
}
.atom-contrast-card .cc-preview{display:flex;height:56px;}
.atom-contrast-card .cc-preview>div{
  flex:1;display:flex;align-items:center;justify-content:center;
  font-size:20px;font-weight:700;font-family:monospace;
}
.atom-contrast-card .cc-body{padding:10px 14px;}
.atom-contrast-card .cc-row{
  display:flex;justify-content:space-between;padding:3px 0;font-size:0.85rem;
}
.atom-contrast-card .cc-row .alg{color:#888;}
.atom-contrast-card .cc-row .scr{font-weight:600;font-family:monospace;}

/* atom:gradient-bar — 单条渐变条 */
.atom-gradient-bar{
  height:52px;border-radius:var(--radius-sm);
  display:flex;align-items:center;justify-content:center;
  color:#fff;font-weight:500;font-size:0.85rem;
  text-shadow:0 1px 3px rgba(0,0,0,0.3);flex:1;
}

/* atom:palette-card — 单色调色板卡 */
.atom-palette-card{
  background:#fff;border-radius:var(--radius);overflow:hidden;
  box-shadow:var(--card-shadow);
}
.atom-palette-card .pc-swatch{height:80px;display:flex;align-items:center;justify-content:center;}
.atom-palette-card .pc-body{padding:10px 12px;}
.atom-palette-card .pc-row{display:flex;justify-content:space-between;padding:2px 0;font-size:0.8rem;}
.atom-palette-card .pc-row .k{color:#999;}
.atom-palette-card .pc-row .v{font-family:monospace;color:#333;}

/* atom:accessible-card — 单条无障碍推荐 */
.atom-accessible-card{
  padding:18px;border-radius:var(--radius);text-align:center;
  box-shadow:var(--card-shadow);flex:1;min-width:180px;
}
.atom-accessible-card .title-lg{font-size:24px;font-weight:700;margin-bottom:6px;}
.atom-accessible-card .body-md{font-size:14px;margin-bottom:4px;}
.atom-accessible-card .sm{font-size:11px;opacity:0.8;}

/* atom:compare-card */
.atom-compare-card{
  background:#fff;padding:12px 16px;border-radius:var(--radius);
  display:flex;align-items:center;gap:12px;
  box-shadow:var(--card-shadow);flex:1;min-width:200px;
}
.atom-compare-card .dot{width:26px;height:26px;border-radius:var(--radius-sm);flex-shrink:0;border:1px solid rgba(0,0,0,0.08);}
.atom-compare-card .info{display:flex;flex-direction:column;gap:2px;}
.atom-compare-card .info .hex{font-weight:600;font-family:monospace;font-size:0.95rem;}
.atom-compare-card .info .meta{font-size:0.8rem;color:#888;}

/* atom:validation-card */
.atom-validation-card{
  padding:24px;background:var(--bg-light);border-radius:var(--radius);
  text-align:center;
}
.atom-validation-card .status{font-size:1.4rem;font-weight:700;}
.atom-validation-card .input{font-family:monospace;margin-top:6px;font-size:1rem;color:#666;}

/* ─── atom:tip-card — 实用建议卡片（增强版）──── */
.atom-tip-card{
  padding:14px 20px;margin:10px 0;
  background:#fafafa;border-radius:var(--radius);
  border-left:4px solid #ffd700;
  line-height:1.7;
}
.atom-tip-card .tip-label{
  display:inline-block;background:#ffd700;color:#1a1a1a;
  padding:1px 10px;border-radius:4px;font-size:11px;font-weight:700;
  margin-bottom:6px;
}
.atom-tip-card .tip-label.red{background:#f44336;color:#fff;}
.atom-tip-card .tip-label.green{background:#4caf50;color:#fff;}
.atom-tip-card .tip-label.blue{background:#2196f3;color:#fff;}
.atom-tip-card .tip-label.orange{background:#ff9800;color:#fff;}
.atom-tip-card .tip-content{font-size:0.95rem;color:#333;}
.atom-tip-card .tip-content strong{color:#1a1a1a;}
.atom-tip-card .tip-content .color-ref{
  font-family:monospace;font-weight:600;padding:1px 4px;
  background:#eee;border-radius:3px;font-size:0.9rem;
}
.atom-tip-card .tip-code{
  background:#1e1e2e;color:#cdd6f4;padding:12px 16px;
  border-radius:var(--radius-sm);font-family:monospace;font-size:0.85rem;
  line-height:1.7;overflow-x:auto;margin-top:8px;
}

/* atom:button-card — 单按钮预览 */
.atom-button-card{
  display:inline-block;padding:10px 22px;
  border:none;border-radius:var(--radius-sm);font-size:0.95rem;
  cursor:default;box-shadow:var(--card-shadow);
}
.atom-button-card.outline{background:transparent;border:2px solid;}

/* atom:text-preview-card — 文字效果预览 */
.atom-text-preview-card{
  padding:18px;border-radius:var(--radius);text-align:center;
  flex:1;min-width:200px;box-shadow:var(--card-shadow);
}
.atom-text-preview-card .t-title{font-size:24px;font-weight:700;margin-bottom:4px;}
.atom-text-preview-card .t-body{font-size:14px;margin-bottom:3px;}
.atom-text-preview-card .t-small{font-size:11px;margin-bottom:8px;}
.atom-text-preview-card .t-footnote{font-size:0.8rem;}

/* atom:private-tip — 每条数据记录的私有化建议插槽 */
.atom-private-tip{
  font-size:0.82rem;color:#888;line-height:1.5;
  padding:5px 10px;margin-top:4px;
  border-top:1px dashed #eee;text-align:center;
  min-height:1.4em;
}
.atom-private-tip:empty::before{content:"⚡ LLM私有建议";opacity:0.2;}
.atom-private-tip:not(:empty){color:#555;font-style:italic;}

.atom-footer{text-align:center;padding:20px;color:#999;font-size:0.85rem;}
"""


# ═══════════════════════════════════════════════════════════════
# 2. 原子组件 (atom_*) — 每个组件渲染一条数据记录
# ═══════════════════════════════════════════════════════════════

def _tc(hex_color: str, luminance: float = None) -> str:
    """决定文字色: 亮度 >= 0.5 用黑底, <0.5 用白底"""
    if luminance is None:
        info = convert_color(hex_color)
        luminance = float(info["luminance"])
    return "#000" if luminance >= 0.5 else "#fff"


def atom_swatch(hex_color: str, label: str = None, size: str = "md", extra_tag: str = "") -> str:
    """单个色块。size: sm(120x120) / md(160x130) / full(100%宽80px高)"""
    info = convert_color(hex_color) if extra_tag or not label else {}
    lbl = label or hex_color.upper()
    tc = _tc(hex_color)
    tag_html = f'<span class="tag">{extra_tag}</span>' if extra_tag else ""
    lum = info.get("luminance", "") if info else ""
    style_attr = f";{lum and f'--lum:{lum}'}" if lum else ""
    return (
        f'<div class="atom-swatch {size}" style="background:{hex_color};color:{tc}{style_attr}">'
        f'{tag_html}'
        f'<span class="hex-lbl">{lbl}</span>'
        f'</div>'
    )


def atom_value_card(label: str, value: str, extra_classes: str = "") -> str:
    """单条属性卡片 (HEX/RGB/HSL等)"""
    return (
        f'<div class="atom-value-card {extra_classes}">'
        f'<div class="lbl">{label}</div>'
        f'<div class="val">{value}</div>'
        f'</div>'
    )


def _private_tip_html(text: str = None) -> str:
    """私有建议插槽: 传入text渲染填充状态, 否则空占位(始终存在)"""
    content = f'>{text}</div>' if text else '></div>'
    return f'<div class="atom-private-tip"{content}'


def atom_contrast_card(c1: str, c2: str, contrast_data: dict = None,
                       show_detail: bool = True, private_tip: str = None) -> str:
    """单条对比度卡片: 上半部色块预览, 下半部4算法分数 + 私有建议插槽"""
    if contrast_data is None:
        contrast_data = get_contrast(c1, c2, "all")
    cd = contrast_data
    tc1, tc2 = _tc(c1), _tc(c2)
    preview_html = (
        f'<div class="cc-preview">'
        f'<div style="background:{c1};color:{tc1};">{c1.upper()}</div>'
        f'<div style="background:{c2};color:{tc2};">{c2.upper()}</div>'
        f'</div>'
    )
    if not show_detail:
        return f'<div class="atom-contrast-card">{preview_html}{_private_tip_html(private_tip)}</div>'

    rows = ""
    for alg_key, alg_label in [("wcag2", "WCAG"), ("apca", "APCA"),
                                ("cielab", "CIELAB"), ("ciede2000", "CIEDE2000")]:
        a = cd.get(alg_key, {})
        val = a.get("value", "—")
        pass_ = a.get("pass")
        if pass_ is not None:
            rows += (f'<div class="cc-row">'
                     f'<span class="alg">{alg_label}</span>'
                     f'<span class="scr">{val} {pass_ and "✅" or "⚠️"}</span></div>')
        else:
            rows += (f'<div class="cc-row">'
                     f'<span class="alg">{alg_label}</span>'
                     f'<span class="scr">{val}</span></div>')
    return f'<div class="atom-contrast-card">{preview_html}<div class="cc-body">{rows}</div>{_private_tip_html(private_tip)}</div>'


def atom_gradient_bar(colors: list, gradient_type: str = "linear") -> str:
    """单条渐变条。gradient_type: linear / reverse / radial"""
    if len(colors) < 2:
        return ""
    if gradient_type == "linear":
        bg = f"linear-gradient(135deg,{','.join(colors)})"
        lbl = "135° 线性渐变"
    elif gradient_type == "reverse":
        bg = f"linear-gradient(135deg,{','.join(reversed(colors))})"
        lbl = "反向渐变"
    elif gradient_type == "radial":
        bg = f"radial-gradient(circle,{','.join(colors)})"
        lbl = "径向渐变"
    else:
        bg = f"linear-gradient(135deg,{','.join(colors)})"
        lbl = "渐变"
    return f'<div class="atom-gradient-bar" style="background:{bg};">{lbl}</div>'


def atom_palette_card(hex_color: str, info: dict = None, private_tip: str = None) -> str:
    """单个调色板色卡: 色块 + RGB/HSL/CMYK/亮度 + 私有建议插槽"""
    if info is None:
        info = convert_color(hex_color)
    tc = _tc(hex_color)
    rgb, hsl, cmyk = info["rgb"], info["hsl"], info["cmyk"]
    card = (
        f'<div class="atom-palette-card">'
        f'<div class="pc-swatch" style="background:{hex_color};color:{tc};">'
        f'<span class="hex-lbl">{hex_color.upper()}</span></div>'
        f'<div class="pc-body">'
        f'<div class="pc-row"><span class="k">RGB</span><span class="v">rgb({rgb["r"]},{rgb["g"]},{rgb["b"]})</span></div>'
        f'<div class="pc-row"><span class="k">HSL</span><span class="v">hsl({hsl["h"]},{hsl["s"]}%,{hsl["l"]}%)</span></div>'
        f'<div class="pc-row"><span class="k">CMYK</span><span class="v">cmyk({cmyk["c"]}%,{cmyk["m"]}%,{cmyk["y"]}%,{cmyk["k"]}%)</span></div>'
        f'<div class="pc-row"><span class="k">亮度</span><span class="v">{info["luminance"]}</span></div>'
        f'</div>{_private_tip_html(private_tip)}</div>'
    )
    return card


def atom_accessible_card(bg_hex: str, fg_hex: str, ratio: str, level: str, private_tip: str = None) -> str:
    """单条无障碍推荐: 预览文字效果 + 私有建议插槽"""
    level_color = "#4CAF50" if level == "AAA" else "#8BC34A" if level == "AA" else "#FFC107"
    tc = _tc(fg_hex)
    level_display = f'<span class="badge" style="background:{level_color};color:#fff;padding:2px 8px;border-radius:8px;font-size:11px;">{level}</span>' if level else ""
    return (
        f'<div class="atom-accessible-card" style="background:{bg_hex};">'
        f'<div class="title-lg" style="color:{fg_hex};">Aa 标题</div>'
        f'<div class="body-md" style="color:{fg_hex};">正文展示效果</div>'
        f'<div class="sm" style="color:{fg_hex};">小号 12px</div>'
        f'<div class="t-footnote" style="margin-top:8px;color:{tc};">{fg_hex} · {ratio} · {level_display}</div>'
        f'{_private_tip_html(private_tip)}</div>'
    )


def atom_compare_card(hex_color: str, info: dict = None, private_tip: str = None) -> str:
    """单条多色比较卡片 + 私有建议插槽"""
    if info is None:
        info = convert_color(hex_color)
    return (
        f'<div class="atom-compare-card">'
        f'<div class="dot" style="background:{hex_color};"></div>'
        f'<div class="info">'
        f'<div class="hex">{hex_color.upper()}</div>'
        f'<div class="meta">{info["family"]} · {info["temperature"]} · 亮度 {info["luminance"]}</div>'
        f'</div>{_private_tip_html(private_tip)}</div>'
    )


def atom_validation_card(status: str, color_str: str, is_valid: bool) -> str:
    """单条验证结果卡片"""
    color = "#4CAF50" if is_valid else "#F44336"
    icon = "✅" if is_valid else "❌"
    return (
        f'<div class="atom-validation-card">'
        f'<div class="status" style="color:{color};">{icon} {status}</div>'
        f'<div class="input">{color_str}</div>'
        f'</div>'
    )


def atom_tip_card(label: str, content: str, code: str = None, label_color: str = "") -> str:
    """单条实用建议卡片。LLM填充的唯一插槽。"""
    lbl_class = f" {label_color}" if label_color else ""
    code_html = f'<pre class="tip-code">{code}</pre>' if code else ""
    return (
        f'<div class="atom-tip-card">'
        f'<span class="tip-label{lbl_class}">{label}</span>'
        f'<div class="tip-content">{content}</div>'
        f'{code_html}'
        f'</div>'
    )


def atom_readability_card(bg_hex: str, fg_hex: str, text: str = "Aa 示例",
                          score: str = "", pass_fail: bool = None,
                          sub_text: str = "", private_tip: str = None) -> str:
    """
    文字可读性演示卡片。上半: 颜色效果演示(bg底+fg文字); 下半: 固定黑白信息栏。
    """
    badge = ""
    if pass_fail is True:
        badge = f'<span style="display:inline-block;background:#4CAF50;color:#fff;padding:2px 10px;border-radius:8px;font-size:12px;font-weight:700;">{score} ✅</span>'
    elif pass_fail is False:
        badge = f'<span style="display:inline-block;background:#F44336;color:#fff;padding:2px 10px;border-radius:8px;font-size:12px;font-weight:700;">{score} ❌</span>'
    elif score:
        badge = f'<span style="display:inline-block;background:#888;color:#fff;padding:2px 10px;border-radius:8px;font-size:12px;font-weight:700;">{score}</span>'
    sub = f'<div style="font-size:13px;color:{fg_hex};margin-top:2px;">{sub_text}</div>' if sub_text else ""
    # 下半: 固定浅底深字信息栏
    pt_html = _private_tip_html(private_tip) if private_tip else ""
    return (
        f'<div class="atom-readability-card" style="border-radius:var(--radius);overflow:hidden;box-shadow:var(--card-shadow);">'
        # 上半: 颜色效果演示区
        f'<div style="padding:22px 16px;background:{bg_hex};text-align:center;">'
        f'<div style="font-size:22px;font-weight:700;color:{fg_hex};line-height:1.3;">{text}</div>'
        f'{sub}'
        f'</div>'
        # 下半: 固定白底信息栏
        f'<div style="padding:10px 14px;background:#fafafa;border-top:1px solid #eee;text-align:center;font-size:11px;color:#555;">'
        f'<span style="font-family:monospace;">{fg_hex}</span> 在 <span style="font-family:monospace;">{bg_hex}</span>'
        f' · {badge}'
        f'{pt_html}'
        f'</div></div>'
    )


def atom_text_preview_card(bg_hex: str, fg_hex: str, level: str = "", ratio: str = "", private_tip: str = None) -> str:
    """单条文字预览卡片(多字号) + 私有建议插槽"""
    level_color = "#4CAF50" if level == "AAA" else "#8BC34A" if level == "AA" else "#FFC107"
    level_html = f'<span class="badge" style="background:{level_color};color:#fff;padding:2px 8px;border-radius:8px;font-size:10px;">{level}</span>' if level else ""
    footnote_tc = _tc(bg_hex)
    return (
        f'<div class="atom-text-preview-card" style="background:{bg_hex};">'
        f'<div class="t-title" style="color:{fg_hex};">Aa 标题</div>'
        f'<div class="t-body" style="color:{fg_hex};">正文示例文字</div>'
        f'<div class="t-small" style="color:{fg_hex};">小号 12px</div>'
        f'<div class="t-footnote" style="color:{footnote_tc};">{fg_hex} · {ratio} · {level_html}</div>'
        f'{_private_tip_html(private_tip)}</div>'
    )


def atom_button_card(hex_color: str, label: str, style_type: str = "solid") -> str:
    """单个按钮预览。style_type: solid / outline / complement"""
    comp = get_complementary(hex_color)["complementary"]
    style_attr = f'background:{hex_color};color:#fff;' if style_type == "solid" else \
                 f'background:transparent;border:2px solid {hex_color};color:{hex_color};' if style_type == "outline" else \
                 f'background:{comp};color:#fff;'
    return f'<div class="atom-button-card {style_type}" style="{style_attr}">{label}</div>'


# ═══════════════════════════════════════════════════════════════
# 3. 固定组合 (comp_*) — 固定数量的原子组件分组
# ═══════════════════════════════════════════════════════════════

def comp_color_info(hex_color: str = None, info: dict = None, hex: str = None) -> str:
    """颜色编码展示: 1个色块 + 8个属性卡片 (固定)"""
    hex_color = hex if hex is not None else hex_color
    if info is None:
        info = convert_color(hex_color)
    rgb, hsl, hsv, cmyk = info["rgb"], info["hsl"], info["hsv"], info["cmyk"]
    swatch = atom_swatch(hex_color, label=hex_color.upper(), size="full")
    cards = (
        atom_value_card("HEX", hex_color.upper()) +
        atom_value_card("RGB", f'rgb({rgb["r"]},{rgb["g"]},{rgb["b"]})') +
        atom_value_card("HSL", f'hsl({hsl["h"]},{hsl["s"]}%,{hsl["l"]}%)') +
        atom_value_card("HSV", f'hsv({hsv["h"]},{hsv["s"]}%,{hsv["v"]}%)') +
        atom_value_card("CMYK", f'cmyk({cmyk["c"]}%,{cmyk["m"]}%,{cmyk["y"]}%,{cmyk["k"]}%)') +
        atom_value_card("亮度", str(info["luminance"])) +
        atom_value_card("灰度", f'Gray({info["grayscale"]})') +
        atom_value_card("色系", f'{info["family"]} · {info["temperature"]}')
    )
    return (
        f'<div class="atom-section-title">🎨 颜色信息</div>'
        f'{swatch}'
        f'<div class="atom-value-grid">{cards}</div>'
    )


def comp_gradient_set(colors: list) -> str:
    """渐变三件套: 线性 + 反向 + 径向 (固定3条)"""
    if len(colors) < 2:
        return ""
    bars = (
        atom_gradient_bar(colors, "linear") +
        atom_gradient_bar(colors, "reverse") +
        atom_gradient_bar(colors, "radial")
    )
    return f'<div class="atom-section-title">🌈 渐变效果</div><div class="atom-flex">{bars}</div>'


def comp_palette_set(colors: list, title: str = "配色方案", private_tips: list = None) -> str:
    """调色板色卡组: N个 palette-card (N由数据决定, 保证数据完整性)"""
    cards = "".join(
        atom_palette_card(c, private_tip=private_tips[i] if (private_tips and i < len(private_tips)) else None)
        for i, c in enumerate(colors)
    )
    return f'<div class="atom-section-title">🎨 {title}</div><div class="atom-grid cols-3">{cards}</div>'


def comp_contrast_set(contrast_pairs: list, private_tips: list = None) -> str:
    """对比度组: N个 contrast-card (N由数据决定, 保证数据完整性)"""
    cards = "".join(
        atom_contrast_card(
            p["c1"], p["c2"], p.get("data"),
            private_tip=private_tips[i] if (private_tips and i < len(private_tips)) else None
        )
        for i, p in enumerate(contrast_pairs)
    )
    return f'<div class="atom-section-title">♿ 对比度</div><div class="atom-grid cols-2">{cards}</div>'


def comp_accessible_set(bg_hex: str = None, recommendations: list = None, meta: dict = None, private_tips: list = None, hex: str = None) -> str:
    """无障碍推荐组: meta + N个 accessible-card (N由数据决定, 保证数据完整性)"""
    bg_hex = hex if hex is not None else bg_hex
    meta_html = ""
    if meta:
        meta_html = '<div class="atom-meta">' + "".join(
            f'<div class="atom-meta-item"><div class="lbl">{k}</div><div class="val">{v}</div></div>'
            for k, v in meta.items()
        ) + '</div>'
    cards = "".join(
        atom_accessible_card(
            bg_hex, r["hex"], r["contrast_ratio"], r["level"],
            private_tip=private_tips[i] if (private_tips and i < len(private_tips)) else None
        )
        for i, r in enumerate(recommendations)
    )
    return (
        f'<div class="atom-section-title">♿ 无障碍颜色推荐</div>'
        f'{meta_html}'
        f'<div class="atom-grid cols-3">{cards}</div>'
    )


def comp_compare_set(colors: list, private_tips: list = None) -> str:
    """多色比较组: N个 compare-card (N由颜色数决定, 保证数据完整性)"""
    cards = "".join(
        atom_compare_card(c, private_tip=private_tips[i] if (private_tips and i < len(private_tips)) else None)
        for i, c in enumerate(colors)
    )
    return f'<div class="atom-section-title">🔍 多色比较</div><div class="atom-grid cols-3">{cards}</div>'


def comp_ui_preview_set(hex_color: str = None, hex: str = None) -> str:
    """UI组件预览组: 3个 button-card + 1个card (固定)"""
    hex_color = hex or hex_color
    card_html = (
        f'<div style="background:#fff;border:1px solid var(--border);border-radius:12px;padding:20px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,0.05);">'
        f'<div style="background:{hex_color};color:#fff;padding:14px;margin:-20px -20px 20px -20px;'
        f'border-radius:10px 10px 0 0;font-weight:600;">卡片标题</div>'
        f'<p style="color:#666;font-size:0.9rem;">主色作为卡片标题背景的示例。</p></div>'
    )
    btns = (
        atom_button_card(hex_color, "主要按钮", "solid") +
        atom_button_card(hex_color, "描边按钮", "outline") +
        atom_button_card(hex_color, "强调按钮", "complement")
    )
    return (
        f'<div class="atom-section-title">🧩 UI组件预览</div>'
        f'<div style="display:flex;flex-direction:column;gap:14px;">{card_html}'
        f'<div class="atom-flex">{btns}</div></div>'
    )


def comp_text_preview_set(bg_hex: str = None, recommendations: list = None, private_tips: list = None, hex: str = None) -> str:
    """文字效果预览组: N个 text-preview-card (N由数据决定, 保证数据完整性)"""
    bg_hex = hex if hex is not None else bg_hex
    cards = "".join(
        atom_text_preview_card(
            bg_hex, r["hex"], r["level"], r["contrast_ratio"],
            private_tip=private_tips[i] if (private_tips and i < len(private_tips)) else None
        )
        for i, r in enumerate(recommendations)
    )
    return (
        f'<div class="atom-section-title">📝 文字效果预览</div>'
        f'<p style="margin-bottom:12px;color:#666;">以下展示推荐文字色在背景 {bg_hex} 上的效果：</p>'
        f'<div class="atom-grid cols-2">{cards}</div>'
    )


def comp_readability_set(items: list, title: str = "文字可读性演示", private_tips: list = None) -> str:
    """
    文字可读性演示组: N个 readability-card (N由数据决定)。
    items = [{"bg":"#FFF","fg":"#FFFF00","text":"黄色小二号字","score":"1.07:1","pass":False,...}]
    """
    cards = "".join(
        atom_readability_card(
            it["bg"], it["fg"],
            text=it.get("text", "Aa 示例"),
            score=it.get("score", ""),
            pass_fail=it.get("pass"),
            sub_text=it.get("sub", ""),
            private_tip=private_tips[i] if (private_tips and i < len(private_tips)) else None,
        )
        for i, it in enumerate(items)
    )
    return f'<div class="atom-section-title">{title}</div><div class="atom-grid cols-2">{cards}</div>'
# ═══════════════════════════════════════════════════════════════

def comp_tips_section(tip_items: list = None, items: list = None) -> str:
    """
    实用建议插槽。tip_items/items=[{"label":"...","content":"...","code":"...可省","color":"...可省"}]
    """
    tip_items = items if items is not None else tip_items
    if not tip_items:
        # 空容器占位 — LLM 填充用
        return (
            f'<div class="atom-section-title">📖 实用建议</div>'
            f'<div class="atom-tip-placeholder" style="padding:20px;background:#fafafa;'
            f'border:2px dashed #ddd;border-radius:8px;text-align:center;color:#bbb;'
            f'font-size:0.9rem;">建议插槽 — LLM填充区域（≥3条，覆盖3种信息角色）</div>'
        )
    cards = "".join(
        atom_tip_card(
            t["label"], t["content"],
            code=t.get("code"),
            label_color=t.get("color", ""),
        )
        for t in tip_items
    )
    return f'<div class="atom-section-title">📖 实用建议</div>{cards}'


# ═══════════════════════════════════════════════════════════════
# 5. 组装引擎
# ═══════════════════════════════════════════════════════════════

_COMPOSITE_REGISTRY = {
    "color-info":     comp_color_info,
    "gradient-set":   comp_gradient_set,
    "palette-set":    comp_palette_set,
    "contrast-set":   comp_contrast_set,
    "accessible-set": comp_accessible_set,
    "compare-set":    comp_compare_set,
    "ui-preview":     comp_ui_preview_set,
    "text-preview":   comp_text_preview_set,
    "readability-set": comp_readability_set,
    "tips":           comp_tips_section,
}

_ATOM_REGISTRY = {
    "swatch":         atom_swatch,
    "value-card":     atom_value_card,
    "contrast-card":  atom_contrast_card,
    "gradient-bar":   atom_gradient_bar,
    "palette-card":   atom_palette_card,
    "accessible-card": atom_accessible_card,
    "compare-card":   atom_compare_card,
    "validation-card": atom_validation_card,
    "tip-card":       atom_tip_card,
    "text-preview-card": atom_text_preview_card,
    "button-card":    atom_button_card,
}


def _validate_output(html: str, composites: list) -> list:
    """
    输出验证: 检查组件声明中的数量一致性。
    返回错误列表, 空列表 = 通过。

    注意: 验证的是 spec 声明层面的完整性,
    HTML 渲染层面的计数由复合组件内部的遍历逻辑保证。
    """
    errors = []

    if not composites:
        return errors

    # 数据字段 → CSS类名映射 (用于 spec 声明检查)
    DATA_KEYS = {
        "contrast-set":   ("contrast_pairs", "private_tips"),
        "palette-set":    ("colors", "private_tips"),
        "compare-set":    ("colors", "private_tips"),
        "accessible-set": ("recommendations", "private_tips"),
        "text-preview":   ("recommendations", "private_tips"),
        "readability-set":("items", "private_tips"),
        "tips":           ("items",),
    }

    for cs in composites:
        ct = cs.get("type")
        if ct not in DATA_KEYS:
            continue

        keys = DATA_KEYS[ct]
        data_key = keys[0]
        data_val = cs.get(data_key)
        if data_val is None:
            continue

        data_len = len(data_val)

        # 基础检查: private_tips 长度须与数据记录数一致
        if len(keys) > 1:
            pt_key = keys[1]
            pt_val = cs.get(pt_key)
            if pt_val is not None and len(pt_val) != data_len:
                errors.append(
                    f"[{ct}] 数据{data_key} {data_len}条, "
                    f"但{pt_key}仅传入{len(pt_val)}条, 两者必须一致。"
                )

    return errors


def _build_header(hex_color: str, title_text: str = "颜色预览", subtitle: str = "") -> str:
    """生成页面标题横幅（固定 1 个）"""
    comp = get_complementary(hex_color)["complementary"]
    return (
        f'<div class="atom-header" style="background:linear-gradient(135deg,{hex_color} 0%,{comp} 100%);color:white;">'
        f'<h1>{title_text}</h1>'
        f'<div class="sub">{subtitle}</div></div>'
    )


def compose(body_parts: list) -> str:
    """
    组装 body 片段列表 -> HTML 字符串。
    body_parts 是 HTML 片段列表，直接拼接。
    """
    return "".join(body_parts)


def assemble_report(
    color_input: str,
    *,
    atoms: list = None,
    composites: list = None,
    tips: list = None,
    header_title: str = None,
    header_subtitle: str = None,
    output_path: str = None,
    raise_on_fail: bool = True,
) -> str:
    """
    原子化组装引擎 - 完整 HTML 报告。

    Parameters
    ----------
    color_input : str
        输入的源颜色 (HEX/RGB/HSL)
    atoms : list[dict], optional
        原子组件声明。每条 dict:
        {"type": "swatch", "hex": "#fff", "size": "md", ...}
        {"type": "contrast-card", "c1": "#fff", "c2": "#000", ...}
        {"type": "tip-card", "label":"核心法则", "content":"...", "code":"可选"}
    composites : list[dict], optional
        固定组合声明。每条 dict:
        {"type": "color-info", "hex": "#fff"}
        {"type": "gradient-set", "colors": ["#fff","#000"]}
        {"type": "tips", "items": [...]}
    tips : list[dict], optional
        快捷方式: 直接传 tips 数组给 tips 组件
    header_title : str, optional
        自定义标题
    header_subtitle : str, optional
        自定义副标题
    output_path : str, optional
        输出文件路径
    raise_on_fail : bool, optional
        验证不通过时是否抛异常。True=抛ValueError, False=只打印警告

    Returns
    -------
    str — 完整 HTML (若指定 output_path 则写入文件)
    验证失败时抛出 ValueError("ColorToolkitValidationError: ...")
    """
    # 解析颜色
    info = convert_color(color_input)
    hex_color = info["hex"]

    # 标题
    title = header_title or f"颜色报告 — {hex_color}"
    subtitle = header_subtitle or f'{info.get("name","")} — {info.get("temperature","")} / {info.get("family","")}'

    # 收集 body 片段
    body_parts = [_build_header(hex_color, title, subtitle)]

    # tips快捷参数 → 转composite
    if isinstance(tips, list) and tips:
        composites = (composites or []) + [{"type": "tips", "items": tips}]

    # 标记是否已有tips复合组件
    _has_tips = any(cs.get("type") == "tips" for cs in (composites or []))

    # 渲染固定组合
    if composites:
        for cs in composites:
            ct = cs.get("type")
            fn = _COMPOSITE_REGISTRY.get(ct)
            if fn:
                try:
                    html = fn(**{k: v for k, v in cs.items() if k != "type"})
                except TypeError:
                    html = ""
                if html:
                    body_parts.append(html)

    # tips全局钩子: 只要有任何有效内容输出且没有显式传入tips, 自动追加空占位
    if not _has_tips and len(body_parts) > 1:
        body_parts.append(comp_tips_section(None))

    # 渲染原子组件（每个原子=1条数据记录）
    if atoms:
        for at in atoms:
            at_type = at.get("type")
            fn = _ATOM_REGISTRY.get(at_type)
            if fn:
                atom_args = {k: v for k, v in at.items() if k != "type"}
                # 支持 count: N，重复渲染 N 次
                count = atom_args.pop("count", 1)
                for _ in range(count):
                    try:
                        html = fn(**atom_args)
                    except TypeError:
                        html = ""
                    if html:
                        body_parts.append(html)

    # 构建完整 HTML
    body = compose(body_parts)
    html = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        f'<title>{title}</title>\n<style>\n{ATOM_CSS}\n</style>\n</head>\n<body>\n'
        f'<div class="atom-container">\n<div class="atom-body">\n{body}\n'
        '<div class="atom-footer">由 Color Toolkit (原子架构 v2) 自动生成</div>\n'
        '</div>\n</div>\n</body>\n</html>'
    )

    # 输出验证
    errors = _validate_output(html, composites)
    if errors:
        msg = "ColorToolkitValidationError: " + " | ".join(errors)
        if raise_on_fail:
            raise ValueError(msg)
        else:
            import warnings
            warnings.warn(msg)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path
    return html


# ═══════════════════════════════════════════════════════════════
# 6. 向后兼容接口
# ═══════════════════════════════════════════════════════════════

def generate_full_preview_html(color_input: str,
                                title: str = "颜色预览",
                                show_complementary: bool = True,
                                show_contrast: bool = True,
                                output_path: str = None) -> str:
    """兼容旧接口: 生成完整颜色预览"""
    info = convert_color(color_input)
    hex_color = info["hex"]
    comp_colors = [hex_color, get_complementary(hex_color)["complementary"]] if show_complementary else [hex_color]
    composites = [
        {"type": "color-info", "hex": hex_color},
    ]
    if show_complementary:
        composites.append({"type": "palette-set", "colors": comp_colors, "title": "互补色"})
    if show_contrast:
        composites.append({
            "type": "contrast-set",
            "contrast_pairs": [{"c1": hex_color, "c2": "#888888", "data": get_contrast(hex_color, "#888888", "all")}],
        })
    return assemble_report(
        color_input,
        composites=composites,
        header_title=title,
        output_path=output_path,
    )


def generate_palette_page_html(colors: list,
                                palette_title: str = "配色方案",
                                output_path: str = None) -> str:
    """兼容旧接口: 调色板预览"""
    if not colors:
        return ""
    return assemble_report(
        colors[0],
        composites=[
            {"type": "color-info", "hex": colors[0]},
            {"type": "palette-set", "colors": colors, "title": palette_title},
        ],
        header_title=palette_title,
        output_path=output_path,
    )


# ═══════════════════════════════════════════════════════════════
# 7. 模块注册 (兼容旧版 assemble_report 的模块名)
# ═══════════════════════════════════════════════════════════════

_LEGACY_MODULES = {
    "color-info":      lambda d, **kw: comp_color_info(d["hex"], d.get("info")),
    "tetradic":        lambda d, **kw: comp_palette_set(get_palette(d["input"], "tetradic")["colors"], "矩形四色组"),
    "triadic":         lambda d, **kw: comp_palette_set(get_palette(d["input"], "triadic")["colors"], "三色组"),
    "analogous":       lambda d, **kw: comp_palette_set(get_palette(d["input"], "analogous")["colors"], "类似色"),
    "complementary":   lambda d, **kw: comp_palette_set(get_palette(d["input"], "complementary")["colors"], "互补色"),
    "四项对比色":       lambda d, **kw: comp_palette_set(get_palette(d["input"], "tetradic")["colors"], "矩形四色组"),
    "三色组":           lambda d, **kw: comp_palette_set(get_palette(d["input"], "triadic")["colors"], "三色组"),
    "类似色":           lambda d, **kw: comp_palette_set(get_palette(d["input"], "analogous")["colors"], "类似色"),
    "互补色":           lambda d, **kw: comp_palette_set(get_palette(d["input"], "complementary")["colors"], "互补色"),
    "tetradic-detail": lambda d, **kw: comp_palette_set(get_palette(d["input"], "tetradic")["colors"], "矩形四色组"),
    "triadic-detail":  lambda d, **kw: comp_palette_set(get_palette(d["input"], "triadic")["colors"], "三色组"),
    "analogous-detail": lambda d, **kw: comp_palette_set(get_palette(d["input"], "analogous")["colors"], "类似色"),
    "gradient":        lambda d, **kw: comp_gradient_set(get_palette(d["input"], "triadic")["colors"]),
    "contrast-pair":   lambda d, **kw: comp_contrast_set([{"c1": d.get("color1", d["hex"]), "c2": d.get("color2", "#888888"), "data": kw.get("contrast_data")}]),
    "text-preview":    lambda d, **kw: comp_text_preview_set(d["hex"], find_accessible(d["hex"], mode="fg", font_size=d.get("font_size","小四"), font_weight=d.get("font_weight","normal"), target=d.get("target","AA"), max_results=6)["recommendations"]),
    "文字效果":         lambda d, **kw: comp_text_preview_set(d["hex"], find_accessible(d["hex"], mode="fg", font_size=d.get("font_size","小四"), font_weight=d.get("font_weight","normal"), target=d.get("target","AA"), max_results=6)["recommendations"]),
    "accessible-fg":   lambda d, **kw: comp_accessible_set(d["hex"], find_accessible(d["hex"], mode="fg", font_size=d.get("font_size","小四"), font_weight=d.get("font_weight","normal"), target=d.get("target","AA"), max_results=25)["recommendations"]),
    "accessible-bg":   lambda d, **kw: comp_accessible_set(d["hex"], find_accessible(d["hex"], mode="bg", font_size=d.get("font_size","小四"), font_weight=d.get("font_weight","normal"), target=d.get("target","AA"), max_results=25)["recommendations"]),
    "ui-preview":      lambda d, **kw: comp_ui_preview_set(d["hex"]),
    "compare":         lambda d, **kw: comp_compare_set(d.get("compare_colors", [d["hex"]])),
    "validate":        lambda d, **kw: f'<div class="atom-section-title">🔍 格式验证</div>{atom_validation_card("有效" if ColorCore.is_valid_hex(d.get("validate_input", d["input"])) else "无效", d.get("validate_input", d["input"]), ColorCore.is_valid_hex(d.get("validate_input", d["input"])))}',
    "random":          lambda d, **kw: comp_palette_set([ColorCore.generate_random_color() for _ in range(d.get("random_count", 5))], "随机颜色"),
    "code-list":       lambda d, **kw: "",  # 已废弃，由 palette-set 替代
    "tips":            lambda d, **kw: comp_tips_section(None),  # 空占位容器
}

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

_FUNCTION_HOOKS = {
    "convert_color":         ["color-info"],
    "get_contrast":          ["contrast-pair"],
    "get_complementary":     ["color-info"],
    "find_accessible":       ["accessible-fg", "text-preview"],
    "get_palette":           None,
    "generate_random_color": ["random"],
    "recommend_color":       ["color-info"],
}

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


def resolve_modules(
    color_input: str = None,
    modules: list = None,
    template: str = None,
    hooks: list = None,
    scene: str = None,
) -> list:
    """兼容旧版模块解析逻辑"""
    if modules is not None:
        return modules
    if template is not None:
        base = list(_BUILTIN_TEMPLATES.get(template, ["color-info"]))
    elif scene is not None:
        import re
        matched = None
        for pattern, tmpl in _SCENE_TEMPLATES.items():
            if re.search(pattern, scene):
                matched = tmpl
                break
        base = list(_BUILTIN_TEMPLATES.get(matched, ["color-info"]))
    else:
        base = []
    if hooks:
        for fn_name in hooks:
            hook_modules = _FUNCTION_HOOKS.get(fn_name)
            if hook_modules:
                for m in hook_modules:
                    if m not in base:
                        base.append(m)
        # tips 是全局通用模块: 任何算法被调用时都自动跟随
        if "tips" not in base:
            base.append("tips")
    return base if base else ["color-info"]


# 旧版 assemble_report (兼容)
def assemble_report_legacy(
    color_input: str,
    modules: list = None,
    template: str = None,
    hooks: list = None,
    scene: str = None,
    title: str = None,
    output_path: str = None,
    **extra,
) -> str:
    """旧版通用报告组装器 - 通过模块名列表组合报告（已迁移为原子架构底层）"""
    info = convert_color(color_input)
    hex_color = info["hex"]
    subtitle = f'{info.get("name","")} — {info.get("temperature","")} / {info.get("family","")}'
    final_modules = resolve_modules(
        color_input=color_input,
        modules=modules,
        template=template,
        hooks=hooks,
        scene=scene,
    )
    if title is None:
        if template: title = f"Color Toolkit — {template} 模板"
        elif scene: title = f"Color Toolkit — {scene}"
        else: title = f"颜色报告 — {hex_color}"

    data = {"input": color_input, "hex": hex_color, "info": info, **extra}

    body_parts = [_build_header(hex_color, title, subtitle)]
    for mod in final_modules:
        fn = _LEGACY_MODULES.get(mod)
        if fn:
            html = fn(data, **extra)
            if html:
                body_parts.append(html)

    body = compose(body_parts)
    html = (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        f'<title>{title}</title>\n<style>\n{ATOM_CSS}\n</style>\n</head>\n<body>\n'
        f'<div class="atom-container">\n<div class="atom-body">\n{body}\n'
        '<div class="atom-footer">由 Color Toolkit (原子架构 v2) 自动生成</div>\n'
        '</div>\n</div>\n</body>\n</html>'
    )
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path
    return html


# 确保旧版 assemble_report 可用
assemble_report.__doc__ += "\n\n（旧版 assemble_report 仍可通过 assemble_report_legacy 调用）"


# ═══════════════════════════════════════════════════════════════
# 8. 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    outdir = r"C:\Users\sm001\WorkBuddy\2026-06-17-17-24-24"

    def test(desc, html, filename):
        with open(f"{outdir}/{filename}", 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ {desc}: {len(html)} chars -> {filename}")

    # ── 1. 原子组件演示: 自由组合 ──
    test("原子: 2个对比色swatch + tips",
         assemble_report("#FFFF00",
             atoms=[
                 {"type": "swatch", "hex": "#FFFF00", "size": "md", "extra_tag": "主色"},
                 {"type": "swatch", "hex": "#1A1A2E", "size": "md", "extra_tag": "深蓝"},
             ],
             composites=[
                 {"type": "tips", "items": [
                     {"label": "核心法则", "content": "黄色(#FFFF00)亮度0.928极高，必须搭配深色背景（亮度≤0.3）才能清晰展示。"},
                     {"label": "最佳拍档", "content": "纯黑(#000)19.56:1 | 深蓝(#1A1A2E)15.89:1 | 藏蓝(#0A1628)18.22:1，均为AAA级。"},
                     {"label": "绝对禁忌", "content": "白底上纯黄做文字必定失败！WCAG仅1.07:1，不可读。", "color": "red"},
                     {"label": "进阶技巧", "content": "白底上无法避开时，用暗色描边补救：", "color": "blue",
                      "code": "color: #FFD700;\ntext-shadow: 0 0 4px #000, 0 0 12px rgba(0,0,0,0.6);"},
                     {"label": "替代方案", "content": "白底场景改用深黄 #D4A017（AA 4.68:1）或 #B8860B（AA 5.68:1）。", "color": "orange"},
                 ]},
             ],
             header_title="黄色显眼展示方案"
         ),
         "v2_atom_yellow.html")

    # ── 2. 对比度: 5个背景 vs 黄色 ──
    bg_colors = ["#000000","#1A1A2E","#2D2D2D","#2D1B4E","#0A1628"]
    contrast_pairs = [{"c1":"#FFFF00", "c2":bg} for bg in bg_colors]
    test("原子: 5条对比度卡片 (N=5) + 私有建议",
         assemble_report("#FFFF00",
             composites=[
                 {"type": "color-info", "hex": "#FFFF00"},
                 {"type": "contrast-set",
                  "contrast_pairs": contrast_pairs,
                  "private_tips": [
                      "19.56:1 顶级对比度，标题首选",
                      "15.89:1 AAA级，高级感视觉",
                      "12.83:1 AAA级，柔和阅读体验",
                      "16.27:1 AAA级，华丽醒目",
                      "18.22:1 AAA级，科技感十足",
                  ]},
                 {"type": "tips", "items": [{"label":"结论","content":"黄色在深色背景上表现优异，全部AAA级。"}]},
             ],
             header_title="黄色 vs 5种深色背景对比度"
         ),
         "v2_contrast_5.html")

    # ── 3. 旧版兼容: 模板 ──
    test("旧兼容: full模板",
         assemble_report_legacy("#3498db", template="full"),
         "v2_legacy_full.html")
    test("旧兼容: 无障碍",
         assemble_report_legacy("#FFFFFF", template="accessibility"),
         "v2_legacy_accessible.html")
    test("旧兼容: 中文场景",
         assemble_report_legacy("#E91E63", scene="算对比度"),
         "v2_legacy_scene.html")

    # ── 4. 验证机制: 验证不通过 → 抛异常 ──
    try:
        assemble_report("#FFFF00",
            composites=[{
                "type": "contrast-set",
                "contrast_pairs": contrast_pairs,  # 5条数据
                "private_tips": ["只传了1条"],      # 故意只传1条
            }],
            raise_on_fail=True,
        )
        print("❌ 验证未生效: 应拦截但通过了")
    except ValueError as e:
        if "private_tips" in str(e):
            print(f"✅ 验证拦截成功: {e}")
        else:
            print(f"❌ 验证异常: {e}")

    try:
        assemble_report("#FFFF00",
            composites=[{
                "type": "contrast-set",
                "contrast_pairs": contrast_pairs,     # 5条数据
                "private_tips": [f"#{i}_建议" for i in range(5)],  # 5条私有建议，正确
            }],
            raise_on_fail=True,
        )
        print("✅ 验证通过: 正确数据")
    except ValueError as e:
        print(f"❌ 误拦截: {e}")

    # ── 5. 验证: 故意少传 data + tips 数量不匹配 ──
    try:
        assemble_report("#FFFF00",
            composites=[{
                "type": "contrast-set",
                "contrast_pairs": contrast_pairs,  # 5条数据
                "private_tips": ["只传了1条"],
            }],
            raise_on_fail=True,
        )
        print("❌ 验证未生效: 应拦截但通过了")
    except ValueError as e:
        print(f"✅ 验证拦截成功: {e}")

    try:
        assemble_report("#FFFF00",
            composites=[{
                "type": "contrast-set",
                "contrast_pairs": contrast_pairs,  # 5条数据
                "private_tips": [None] * 5,  # 5个None = 0填充，但长度正确
            }],
            raise_on_fail=True,
        )
        print("✅ 验证通过: 5条空私有建议长度正确")
    except ValueError as e:
        print(f"❌ 误拦截: {e}")

    print("\n🎉 原子架构 v2 测试完成")
