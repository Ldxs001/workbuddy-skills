#!/usr/bin/env python3
# module_assembler.py — Grid-aware 模块组装器 v2.0.0
# 用法:
#   python module_assembler.py --list-modules        # 列出所有模块
#   python module_assembler.py --list-templates      # 列出所有模板
#   python module_assembler.py --spec <path> -o <out> # 从 grid spec 生成
#   python module_assembler.py --create-spec -o <out>  # 交互式创建 grid spec
#   python module_assembler.py --save-modules        # 保存模块库到 disk

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent

# Import from grid_builder for shared module definitions
sys.path.insert(0, str(SKILL_DIR / "scripts"))
from grid_builder import (
    BASE_MODULES, COMPOSITE_MODULES, BUILTIN_TEMPLATES,
    generate_html, list_modules as gb_list_modules,
    list_templates as gb_list_templates,
    load_grid_spec, css_dict_to_str,
)

# R-12 审计锚点
DEFAULT_DATA_DIR_RAW = "skills/.standardization/hug-html/data/"
DATA_DIR = SKILL_DIR.parent / ".standardization" / "hug-html" / "data"
MODULES_DIR = DATA_DIR / "modules"
TEMPLATES_DIR = DATA_DIR / "templates"
OUTPUT_DIR = DATA_DIR / "output"


def interactive_create_spec(output_path):
    """Interactive grid spec creator"""
    print("=== Interactive Grid Spec Creator ===")
    print()

    rows = int(input("Rows: ") or "3")
    cols = int(input("Cols: ") or "3")
    gap = input("Gap (e.g. 8px): ") or "8px"
    card_width = input("Card max-width (e.g. 600px): ") or "600px"

    cells = []
    for r in range(rows):
        for c in range(cols):
            print(f"\n--- Cell [{r+1},{c+1}] ---")
            have_cell = input(f"  Include this cell? (Y/n): ").strip().lower()
            if have_cell == "n":
                continue

            cell_id = input(f"  Cell ID (default: cell-{r+1}-{c+1}): ") or f"cell-{r+1}-{c+1}"
            colspan = int(input(f"  Colspan (default 1): ") or "1")
            rowspan = int(input(f"  Rowspan (default 1): ") or "1")

            print("  Available composite modules:")
            for mname in COMPOSITE_MODULES:
                print(f"    composite:{mname} — {COMPOSITE_MODULES[mname]['desc']}")
            print("    (custom) — Custom HTML")

            module = input("  Module (composite:xxx or 'custom'): ").strip()
            cell_bg = input("  Background color: ").strip() or "transparent"
            cell_pad = input("  Padding: ").strip() or "8px"

            cell = {
                "id": cell_id,
                "row": r, "col": c,
                "rowspan": rowspan, "colspan": colspan,
                "bg": cell_bg,
                "padding": cell_pad,
            }

            if module.startswith("composite:"):
                cell["module"] = module
            else:
                raw_html = input("  Custom HTML content: ")
                cell["html"] = raw_html

            cells.append(cell)

    spec = {
        "name": input("\nTemplate name: ") or "Custom Grid",
        "desc": "交互式创建的网格规格",
        "card_style": {
            "max_width": card_width,
            "width": "100%",
            "bg": "#ffffff",
            "border_radius": "20px",
            "shadow": "0 10px 30px rgba(0,0,0,0.08)",
            "padding": "16px",
        },
        "grid": {"rows": rows, "cols": cols, "gap": gap},
        "cells": cells,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Grid spec saved: {out}")
    return str(out)


def main():
    ap = argparse.ArgumentParser(description="Grid-aware HTML Module Assembler v2")
    ap.add_argument("--list-modules", action="store_true", help="List all modules (base + composite)")
    ap.add_argument("--list-templates", action="store_true", help="List all built-in templates")
    ap.add_argument("--save-modules", action="store_true", help="Save module library to disk")
    ap.add_argument("--spec", help="Path to grid spec JSON or built-in template name")
    ap.add_argument("--output", "-o", help="Output HTML file path")
    ap.add_argument("--create-spec", "-c", help="Interactive grid spec creation, save to path")
    ap.add_argument("--json-output", help="Output as JSON instead of HTML (for debugging)")

    args = ap.parse_args()

    if args.list_modules:
        gb_list_modules()
        return

    if args.list_templates:
        gb_list_templates()
        return

    if args.save_modules:
        from gen_test_grids import save_modules_json
        save_modules_json()
        return

    if args.create_spec:
        interactive_create_spec(args.create_spec)
        return

    if args.spec:
        spec = load_grid_spec(args.spec)
        if args.json_output:
            Path(args.json_output).write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] Spec JSON saved: {args.json_output}")
            return

        out_path = args.output or str(OUTPUT_DIR / "assembled.html")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        html = generate_html(spec)
        Path(out_path).write_text(html, encoding="utf-8")
        print(f"[OK] Assembled HTML: {out_path}")
        print(f"  Template: {spec.get('name','Custom')}")
        cells = spec.get("cells", []) or spec.get("grid", {}).get("cells", [])
        print(f"  Grid: {spec.get('grid',{}).get('rows','?')}×{spec.get('grid',{}).get('cols','?')}, {len(cells)} cells")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
