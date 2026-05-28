#!/usr/bin/env python3
# content_filler.py - Fill HTML template with content
# Usage: python content_filler.py --template <path> --content <json> --output <path>
#         python content_filler.py --auto --template <path> --output <path>
#         python content_filler.py --extract <html> --output <json>

import argparse
import json
import re
import sys
from pathlib import Path

# Style presets for different scenarios
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
    """Fill template with content data"""
    tpl = Path(template_path)
    if not tpl.exists():
        print("[X] Template not found: " + str(tpl))
        sys.exit(1)

    html = tpl.read_text(encoding="utf-8")

    # Fill data-field elements
    for field, value in content_data.items():
        # Match element with data-field="field" and replace its content
        pattern = (
            r'(<[^>]+data-field="' + re.escape(field) + r'"[^>]*>)'
            r'(.*?)'
            r'(</[^>]+>)'
        )
        replacement = r'\1' + str(value) + r'\3'
        html = re.sub(pattern, replacement, html, count=1, flags=re.DOTALL)

    # Write output
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("[OK] Content filled: " + str(out))
    return str(out)


def apply_style_preset(html, preset_name):
    """Apply style preset to HTML"""
    if preset_name not in STYLE_PRESETS:
        print("[WARN] Unknown preset: " + preset_name)
        return html

    preset = STYLE_PRESETS[preset_name]

    # Replace CSS variables in style blocks
    for key, val in preset.items():
        css_var = "--" + key.replace("_", "-") + ":"
        html = html.replace(css_var, css_var + " " + val + ";")

    return html


def auto_fill(template_path, output_path):
    """Auto-fill template with sample content based on data-field attributes"""
    tpl = Path(template_path)
    if not tpl.exists():
        print("[X] Template not found: " + str(tpl))
        sys.exit(1)

    html = tpl.read_text(encoding="utf-8")

    # Find all data-field attributes
    fields = re.findall(r'data-field="([^"]+)"', html)

    # Generate sample content for each field
    sample_content = generate_sample_content(fields)

    # Fill with sample content
    for field, value in sample_content.items():
        pattern = (
            r'(<[^>]+data-field="' + re.escape(field) + r'"[^>]*>)'
            r'(.*?)'
            r'(</[^>]+>)'
        )
        replacement = r'\1' + str(value) + r'\3'
        html = re.sub(pattern, replacement, html, count=1, flags=re.DOTALL)

    # Write output
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("[OK] Auto-filled with sample content: " + str(out))
    print("  Fields filled: " + str(len(sample_content)))
    return str(out)


def generate_sample_content(fields):
    """Generate sample content based on field names"""
    samples = {}
    for field in fields:
        field_lower = field.lower()
        if "title" in field_lower:
            samples[field] = "📢 标题文字（可编辑）"
        elif "subtitle" in field_lower or "sub" in field_lower:
            samples[field] = "在这里填写副标题或简短描述"
        elif "name" in field_lower:
            samples[field] = "名称 / 产品名"
        elif "desc" in field_lower or "description" in field_lower:
            samples[field] = "这里是详细描述文字，可以根据需要修改此内容。"
        elif "price" in field_lower:
            samples[field] = "￥999"
        elif "time" in field_lower or "date" in field_lower:
            samples[field] = "2026年X月X日 14:00-16:00"
        elif "location" in field_lower or "addr" in field_lower:
            samples[field] = "深圳市南山区XX大厦"
        elif "contact" in field_lower:
            samples[field] = "联系人：张先生 138-XXXX-XXXX"
        elif "footer" in field_lower:
            samples[field] = "© 2026 版权所有 | 联系我们"
        elif "step" in field_lower and "title" in field_lower:
            num = re.search(r'(\d+)', field)
            n = num.group(1) if num else "1"
            samples[field] = "第" + n + "步：操作说明"
        elif "step" in field_lower and "desc" in field_lower:
            samples[field] = "请在此描述本步骤的详细操作内容..."
        else:
            samples[field] = "可编辑内容：「" + field + "」"
    return samples


def extract_content(html_path):
    """Extract content from HTML (for saving user edits)"""
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


def cmd_extract(args):
    """Extract content from HTML and save to JSON"""
    content = extract_content(args.extract)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    print("[OK] Content extracted to: " + str(out_path))


def cmd_auto(args):
    """Auto-fill with sample content"""
    auto_fill(args.template, args.output)


def cmd_fill(args):
    """Fill with content from JSON file"""
    with open(args.content, "r", encoding="utf-8") as f:
        content_data = json.load(f)
    fill_template(args.template, content_data, args.output)


def cmd_preset(args):
    """Apply style preset"""
    tpl = Path(args.template)
    if not tpl.exists():
        print("[X] Template not found: " + str(tpl))
        sys.exit(1)

    html = tpl.read_text(encoding="utf-8")
    html = apply_style_preset(html, args.preset)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("[OK] Style preset applied: " + args.preset)
    print("  Output: " + str(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fill HTML template with content")
    sub = ap.add_subparsers(dest="command")

    # extract command
    p_extract = sub.add_parser("extract", help="Extract content from HTML to JSON")
    p_extract.add_argument("--input", required=True, help="Input HTML file path")
    p_extract.add_argument("--output", required=True, help="Output JSON file path")

    # auto-fill command
    p_auto = sub.add_parser("auto", help="Auto-fill with sample content")
    p_auto.add_argument("--template", required=True, help="Input template HTML path")
    p_auto.add_argument("--output", required=True, help="Output HTML file path")

    # fill command
    p_fill = sub.add_parser("fill", help="Fill with content from JSON file")
    p_fill.add_argument("--template", required=True, help="Input template HTML path")
    p_fill.add_argument("--content", required=True, help="JSON file with content to fill")
    p_fill.add_argument("--output", required=True, help="Output HTML file path")

    # preset command
    p_preset = sub.add_parser("preset", help="Apply style preset")
    p_preset.add_argument("--template", required=True, help="Input template HTML path")
    p_preset.add_argument("--name", required=True, choices=list(STYLE_PRESETS.keys()), help="Preset name")
    p_preset.add_argument("--output", required=True, help="Output HTML file path")

    args = ap.parse_args()

    if args.command == "extract":
        content = extract_content(args.input)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        print("[OK] Content extracted to: " + str(out_path))
    elif args.command == "auto":
        auto_fill(args.template, args.output)
    elif args.command == "fill":
        with open(args.content, "r", encoding="utf-8") as f:
            content_data = json.load(f)
        fill_template(args.template, content_data, args.output)
    elif args.command == "preset":
        cmd_preset(args)
    else:
        ap.print_help()
