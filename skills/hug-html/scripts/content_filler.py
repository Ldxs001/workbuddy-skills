#!/usr/bin/env python3
# content_filler.py — Grid-aware 内容填充器 v2.0.0
# 用法:
#   python content_filler.py fill --template <path> --content <json> --output <path>
#   python content_filler.py auto --template <path> --output <path>
#   python content_filler.py extract --input <html> --output <json>

import argparse
import json
import re
import sys
from pathlib import Path

# Style presets
STYLE_PRESETS = {
    "business": {
        "primary": "#1a2a4a",
        "secondary": "#4a5568",
        "bg": "#f0f4f8",
        "font": "'Microsoft YaHei', sans-serif",
        "border_radius": "8px",
        "gradient": "linear-gradient(135deg, #1a2a4a 0%, #4a5568 100%)",
    },
    "academic": {
        "primary": "#333333",
        "secondary": "#666666",
        "bg": "#ffffff",
        "font": "SimSun, serif",
        "border_radius": "4px",
        "gradient": "linear-gradient(135deg, #333 0%, #666 100%)",
    },
    "festive": {
        "primary": "#c0392b",
        "secondary": "#e74c3c",
        "bg": "linear-gradient(135deg, #c0392b 0%, #e74c3c 100%)",
        "font": "SimSun, serif",
        "border_radius": "12px",
        "gradient": "linear-gradient(135deg, #c0392b 0%, #e74c3c 100%)",
    },
    "mourning": {
        "primary": "#333333",
        "secondary": "#666666",
        "bg": "#f5f5f5",
        "font": "SimSun, serif",
        "border_radius": "8px",
        "gradient": "linear-gradient(135deg, #333 0%, #666 100%)",
    },
    "tech": {
        "primary": "#2D3436",
        "secondary": "#636E72",
        "bg": "#f8f9fa",
        "font": "Consolas, 'Courier New', monospace",
        "border_radius": "4px",
        "gradient": "linear-gradient(135deg, #2D3436 0%, #636E72 100%)",
    },
}


def fill_template(template_path, content_data, output_path):
    """Fill template with content data (replaces data-field content)"""
    tpl = Path(template_path)
    if not tpl.exists():
        print(f"[X] Template not found: {tpl}")
        sys.exit(1)

    html = tpl.read_text(encoding="utf-8")

    for field, value in content_data.items():
        pattern = (
            r'(<[^>]+data-field="' + re.escape(field) + r'"[^>]*>)'
            r'(.*?)'
            r'(</[^>]+>)'
        )
        replacement = r'\1' + str(value) + r'\3'
        html = re.sub(pattern, replacement, html, count=1, flags=re.DOTALL)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[OK] Content filled: {out}")
    return str(out)


def auto_fill(template_path, output_path):
    """Auto-fill template with smart sample content based on field names"""
    tpl = Path(template_path)
    html = tpl.read_text(encoding="utf-8")
    fields = re.findall(r'data-field="([^"]+)"', html)

    samples = {
        # Titles
        r'title|name|header': "主标题文字（可编辑）",
        r'subtitle|sub\b': "副标题或简短描述",
        # Descriptions
        r'desc|detail|intro': "这里是详细描述内容，可以根据需要修改此文字。",
        r'note|caption|hint': "注释说明文字",
        r'footer': "© 2026 版权所有 | 联系我们",
        r'badge|tag|label': "标签名称",
        r'hint|qr-hint|platform': "平台说明",
        # Features
        r'feature-text|feature-icon': "特性描述文字 ✨",
        r'qr-label|qr-image': "扫码体验",
        # Communication
        r'device|protocol|arrow': "设备/协议标注",
        # Entity
        r'entity-name|app-name|service-name': "名称",
        r'entity-badge|app-badge|service-badge': "标签",
        r'main-title': "主标题",
        r'main-sub': "副标题",
        # Default
        r'.*': "可编辑内容",
    }

    content = {}
    for field in fields:
        val = "可编辑内容：" + field
        for pattern, sample in samples.items():
            if re.search(pattern, field, re.IGNORECASE):
                val = sample
                break
        content[field] = val

    for field, value in content.items():
        pattern = (
            r'(<[^>]+data-field="' + re.escape(field) + r'"[^>]*>)'
            r'(.*?)'
            r'(</[^>]+>)'
        )
        replacement = r'\1' + str(value) + r'\3'
        html = re.sub(pattern, replacement, html, count=1, flags=re.DOTALL)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[OK] Auto-filled: {out}")
    print(f"  Fields filled: {len(content)}")
    return str(out)


def extract_content(html_path):
    """Extract data-field content from HTML"""
    html = Path(html_path).read_text(encoding="utf-8")
    fields = re.findall(r'data-field="([^"]+)"', html)
    content = {}
    for field in fields:
        pattern = (
            r'<[^>]+data-field="' + re.escape(field) + r'"[^>]*>'
            r'(.*?)'
            r'</[^>]+>'
        )
        match = re.search(pattern, html, re.DOTALL)
        if match:
            content[field] = match.group(1).strip()
    return content


def main():
    ap = argparse.ArgumentParser(description="Grid-aware HTML Content Filler v2")
    sub = ap.add_subparsers(dest="command")

    p_extract = sub.add_parser("extract")
    p_extract.add_argument("--input", required=True)
    p_extract.add_argument("--output", required=True)

    p_auto = sub.add_parser("auto")
    p_auto.add_argument("--template", required=True)
    p_auto.add_argument("--output", required=True)

    p_fill = sub.add_parser("fill")
    p_fill.add_argument("--template", required=True)
    p_fill.add_argument("--content", required=True)
    p_fill.add_argument("--output", required=True)

    p_preset = sub.add_parser("preset")
    p_preset.add_argument("--template", required=True)
    p_preset.add_argument("--name", required=True, choices=list(STYLE_PRESETS.keys()))
    p_preset.add_argument("--output", required=True)

    args = ap.parse_args()

    if args.command == "extract":
        content = extract_content(args.input)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        print(f"[OK] Content extracted: {out}")

    elif args.command == "auto":
        auto_fill(args.template, args.output)

    elif args.command == "fill":
        with open(args.content, "r", encoding="utf-8") as f:
            data = json.load(f)
        fill_template(args.template, data, args.output)

    elif args.command == "preset":
        html = Path(args.template).read_text(encoding="utf-8")
        preset = STYLE_PRESETS[args.name]
        for key, val in preset.items():
            css_var = "--" + key.replace("_", "-") + ":"
            html = html.replace(css_var, css_var + " " + val + ";")
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"[OK] Preset applied: {args.name}")

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
