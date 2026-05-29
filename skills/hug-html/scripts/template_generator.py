#!/usr/bin/env python3
# template_generator.py — Grid-aware HTML模板生成器 v2.0.0
# 用法:
#   python template_generator.py --type <模板名> -o <输出HTML>
#   python template_generator.py --list-types
#   python template_generator.py --spec <grid_spec.json> -o <输出HTML>

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent

sys.path.insert(0, str(SKILL_DIR / "scripts"))
from grid_builder import (
    BUILTIN_TEMPLATES, generate_html, load_grid_spec,
    list_templates as gb_list_templates,
)

OUTPUT_DIR = SKILL_DIR.parent / ".standardization" / "hug-html" / "data" / "output"


def generate(template_type, output_path, content=None):
    """Generate HTML from a built-in template type, with optional content fill"""
    try:
        spec = load_grid_spec(template_type)
    except SystemExit:
        return None
    html = generate_html(spec)

    # Fill content if provided
    if content:
        for field, value in content.items():
            # Replace content in data-field elements
            html = html.replace(
                f'data-field="{field}">',
                f'data-field="{field}">{value}',
                1
            )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[OK] Template generated: {out}")
    print(f"  Type: {template_type} ({spec.get('name', '?')})")
    grid = spec.get("grid", {})
    n_cells = len(grid.get("cells", []))
    print(f"  Grid: {grid.get('rows','?')}×{grid.get('cols','?')}, {n_cells} cells")
    return str(out)


def list_types():
    """List all available template types"""
    gb_list_templates()


def main():
    ap = argparse.ArgumentParser(description="Grid-aware HTML Template Generator v2")
    ap.add_argument("--type", help="Template type name")
    ap.add_argument("--list-types", action="store_true", help="List all available template types")
    ap.add_argument("--output", "-o", required=False, help="Output HTML file path")
    ap.add_argument("--spec", help="Path to custom grid spec JSON")
    ap.add_argument("--content", help="JSON file to fill content")

    args = ap.parse_args()

    if args.list_types:
        list_types()
        return

    if args.spec:
        # Generate from custom grid spec
        spec = load_grid_spec(args.spec)
        out_path = args.output or str(OUTPUT_DIR / "custom-template.html")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        html = generate_html(spec)
        Path(out_path).write_text(html, encoding="utf-8")
        print(f"[OK] Custom template generated: {out_path}")
        return

    if args.type:
        content_data = None
        if args.content:
            with open(args.content, "r", encoding="utf-8") as f:
                content_data = json.load(f)
        out_path = args.output or str(OUTPUT_DIR / f"{args.type}.html")
        generate(args.type, out_path, content_data)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
