#!/usr/bin/env python3
# module_assembler.py - Reusable HTML module library
# Usage: python module_assembler.py --modules <csv> --output <path>
#         python module_assembler.py --list
#         python module_assembler.py --add <category> <name> <html_file>

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
MODULES_DIR = SKILL_DIR / "data" / "modules"

# Module library - keyed by category -> name -> html snippet
MODULE_LIB = {
    "color": {
        "gradient-purple": {
            "desc": "粉紫渐变背景",
            "html": '<div style="background:linear-gradient(135deg,#6C63FF 0%,#FF6584 100%);padding:40px;border-radius:12px;color:white;text-align:center;">\n  <h2 style="margin:0 0 8px 0;">渐变面板</h2>\n  <p style="opacity:0.9;">可编辑内容区域</p>\n</div>',
            "editable": True,
        },
        "gradient-blue": {
            "desc": "蓝绿渐变背景",
            "html": '<div style="background:linear-gradient(135deg,#00B894 0%,#00CEC9 100%);padding:40px;border-radius:12px;color:white;text-align:center;">\n  <h2 style="margin:0 0 8px 0;">蓝绿渐变</h2>\n  <p style="opacity:0.9;">内容区域</p>\n</div>',
            "editable": True,
        },
        "solid-primary": {
            "desc": "主色实心面板",
            "html": '<div style="background:#6C63FF;color:white;padding:24px;border-radius:10px;">\n  <h3 style="margin:0 0 8px 0;">主色面板</h3>\n  <p style="margin:0;opacity:0.9;">内容</p>\n</div>',
            "editable": True,
        },
        "transparent-card": {
            "desc": "透明卡片（白底半透明）",
            "html": '<div style="background:rgba(255,255,255,0.85);padding:24px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">\n  <h3 style="margin:0 0 8px 0;color:#6C63FF;">透明卡片</h3>\n  <p style="margin:0;color:#333;">内容区域</p>\n</div>',
            "editable": True,
        },
    },
    "font": {
        "title-large": {
            "desc": "大标题（2.8em，加粗，主色）",
            "html": '<h1 style="font-size:2.8em;font-weight:bold;color:#6C63FF;margin:0 0 12px 0;line-height:1.2;">大标题文字</h1>',
            "editable": True,
        },
        "title-medium": {
            "desc": "中标题（1.6em，主色）",
            "html": '<h2 style="font-size:1.6em;font-weight:bold;color:#6C63FF;margin:0 0 10px 0;">中标题文字</h2>',
            "editable": True,
        },
        "body-text": {
            "desc": "正文（1em，行高1.8）",
            "html": '<p style="font-size:1em;line-height:1.8;color:#333;margin:0 0 12px 0;">正文内容，行高宽松易读。</p>',
            "editable": True,
        },
        "caption": {
            "desc": "说明文字（0.9em，灰色）",
            "html": '<p style="font-size:0.9em;color:#888;margin:0;">说明文字或注释</p>',
            "editable": True,
        },
        "mono-code": {
            "desc": "代码样式文字（Consolas）",
            "html": '<code style="font-family:Consolas,monospace;background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:0.9em;">code_snippet()</code>',
            "editable": True,
        },
    },
    "image": {
        "img-circle": {
            "desc": "圆形裁剪图片（头像/Logo）",
            "html": '<img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27150%27 height=%27150%27%3E%3Crect fill=%27%23ddd%27 width=%27150%27 height=%27150%27 rx=%2775%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 dominant-baseline=%27middle%27 text-anchor=%27middle%27 fill=%27%23999%27%3E头像%3C/text%3E%3C/svg%3E" class="img-circle" style="width:150px;height:150px;object-fit:cover;border-radius:50%;display:block;margin:0 auto;">',
            "editable": False,
        },
        "img-logo": {
            "desc": "Logo图片（左上角，固定80px宽）",
            "html": '<img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2780%27 height=%2740%27%3E%3Crect fill=%27%236C63FF%27 width=%2780%27 height=%2740%27 rx=%276%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 dominant-baseline=%27middle%27 text-anchor=%27middle%27 fill=%27white%27 font-size=%2714%27%3ELOGO%3C/text%3E%3C/svg%3E" style="position:absolute;top:12px;left:12px;width:80px;height:auto;">',
            "editable": False,
        },
        "img-cover": {
            "desc": "封面图（宽100%，高200px，cover裁剪）",
            "html": '<img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27600%27 height=%27200%27%3E%3Crect fill=%27%23e0e0e0%27 width=%27600%27 height=%27200%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 dominant-baseline=%27middle%27 text-anchor=%27middle%27 fill=%27%23999%27%3E封面图片%3C/text%3E%3C/svg%3E" style="width:100%;height:200px;object-fit:cover;border-radius:8px;">',
            "editable": False,
        },
        "img-contain": {
            "desc": "完整显示图片（contain，不变形）",
            "html": '<img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27400%27 height=%27300%27%3E%3Crect fill=%27%23f0f0f0%27 width=%27400%27 height=%27300%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 dominant-baseline=%27middle%27 text-anchor=%27middle%27 fill=%27%23999%27%3E完整图片%3C/text%3E%3C/svg%3E" style="width:100%;height:auto;border-radius:8px;">',
            "editable": False,
        },
    },
    "layout": {
        "two-col": {
            "desc": "两栏布局（左文右图）",
            "html": '<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:center;">\n  <div>\n    <h3 style="color:#6C63FF;margin:0 0 8px 0;">标题</h3>\n    <p>左侧文字内容。</p>\n  </div>\n  <div>\n    <img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27200%27%3E%3Crect fill=%27%23e0e0e0%27%27/%3E%3C/svg%3E" style="width:100%;border-radius:8px;">\n  </div>\n</div>',
            "editable": True,
        },
        "three-col-cards": {
            "desc": "三栏卡片布局",
            "html": '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">\n  <div style="background:#f8f9fa;padding:20px;border-radius:10px;border-top:3px solid #6C63FF;">\n    <h4 style="margin:0 0 8px 0;">卡片1</h4>\n    <p style="font-size:0.9em;color:#666;margin:0;">描述文字</p>\n  </div>\n  <div style="background:#f8f9fa;padding:20px;border-radius:10px;border-top:3px solid #FF6584;">\n    <h4 style="margin:0 0 8px 0;">卡片2</h4>\n    <p style="font-size:0.9em;color:#666;margin:0;">描述文字</p>\n  </div>\n  <div style="background:#f8f9fa;padding:20px;border-radius:10px;border-top:3px solid #00B894;">\n    <h4 style="margin:0 0 8px 0;">卡片3</h4>\n    <p style="font-size:0.9em;color:#666;margin:0;">描述文字</p>\n  </div>\n</div>',
            "editable": True,
        },
        "centered": {
            "desc": "居中单栏布局",
            "html": '<div style="max-width:700px;margin:0 auto;text-align:center;padding:20px;">\n  <h2 style="color:#6C63FF;">居中标题</h2>\n  <p style="color:#555;">居中内容区域，适合简短说明。</p>\n</div>',
            "editable": True,
        },
    },
    "effect": {
        "fade-in": {
            "desc": "淡入动画包装器",
            "html": '<div style="animation:fadeIn 0.6s ease-out;@keyframes fadeIn{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}">\n  <p>淡入内容</p>\n</div>',
            "editable": True,
        },
        "hover-scale": {
            "desc": "悬停放大效果（卡片用）",
            "html": '<div style="transition:transform 0.3s;cursor:pointer;" onmouseover="this.style.transform=\'scale(1.03)\'" onmouseout="this.style.transform=\'scale(1)\'">\n  <p>悬停我放大</p>\n</div>',
            "editable": True,
        },
        "divider": {
            "desc": "分割线",
            "html": '<hr style="border:none;border-top:1px solid #eee;margin:24px 0;">',
            "editable": False,
        },
        "spacer": {
            "desc": "空白间隔（20px）",
            "html": '<div style="height:20px;"></div>',
            "editable": False,
        },
    },
    "template": {
        "promo-panel": {
            "desc": "宣传面板完整模板（含标题/内容/按钮）",
            "html": '<div style="background:linear-gradient(135deg,#6C63FF,#3F51B5);padding:48px 24px;border-radius:14px;color:white;text-align:center;margin-bottom:24px;">\n  <h1 style="font-size:2.4em;margin:0 0 12px 0;" class="edit-text" data-field="promo_title">活动宣传标题</h1>\n  <p style="font-size:1.1em;opacity:0.9;margin:0 0 20px 0;" class="edit-text" data-field="promo_sub">活动副标题描述</p>\n  <button style="background:white;color:#6C63FF;border:none;padding:12px 36px;border-radius:8px;font-size:1em;cursor:pointer;font-weight:bold;">了解更多</button>\n</div>',
            "editable": True,
        },
        "product-intro": {
            "desc": "产品介绍面板（图文左右）",
            "html": '<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:center;background:white;padding:32px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);">\n  <div>\n    <h2 style="color:#00B894;margin:0 0 12px 0;" class="edit-text" data-field="prod_name">产品名称</h2>\n    <p class="edit-text" data-field="prod_desc">产品核心卖点描述...</p>\n    <button style="background:#00B894;color:white;border:none;padding:10px 28px;border-radius:6px;cursor:pointer;margin-top:12px;">立即咨询</button>\n  </div>\n  <div>\n    <img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27200%27%3E%3Crect fill=%27%23e0e0e0%27%27/%3E%3C/svg%3E" style="width:100%;border-radius:8px;">\n  </div>\n</div>',
            "editable": True,
        },
        "tech-block": {
            "desc": "技术说明块（代码样式）",
            "html": '<div style="background:#f8f9fa;border-left:4px solid #2D3436;padding:20px;font-family:Consolas,monospace;border-radius:0 8px 8px 0;">\n  <h3 style="font-family:Microsoft YaHei;color:#2D3436;margin:0 0 10px 0;">技术要点</h3>\n  <pre style="background:#2D3436;color:#dfe6e9;padding:14px;border-radius:6px;overflow-x:auto;font-size:0.85em;"><code class="edit-text" data-field="tech_code"># 代码示例\ndef solution():\n    return True</code></pre>\n</div>',
            "editable": True,
        },
        "flow-step": {
            "desc": "流程步骤卡片（含步骤编号）",
            "html": '<div style="background:white;padding:20px;border-radius:12px;border-top:4px solid #E17055;position:relative;">\n  <div style="background:#E17055;color:white;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;">N</div>\n  <h4 class="edit-text" data-field="step_title" style="margin:10px 0 8px 0;">步骤标题</h4>\n  <p class="edit-text" data-field="step_desc" style="font-size:0.9em;color:#555;margin:0;">步骤描述...</p>\n</div>',
            "editable": True,
        },
    },
    "style": {
        "business": {
            "desc": "商务风格预设（深蓝/灰色系）",
            "html": '<div style="font-family:\'Microsoft YaHei\',sans-serif;color:#1a2a4a;background:#f0f4f8;padding:24px;border-radius:8px;">\n  <h3 style="color:#1a2a4a;margin:0 0 10px 0;">商务风格面板</h3>\n  <p style="color:#4a5568;margin:0;">深色文字配合浅蓝灰背景，适合商务报告。</p>\n</div>',
            "editable": True,
        },
        "academic": {
            "desc": "科研风格预设（白底/宋体感/严谨边框）",
            "html": '<div style="font-family:SimSun,serif;color:#222;background:white;padding:24px;border:1px solid #ccc;border-radius:4px;">\n  <h3 style="color:#333;margin:0 0 10px 0;border-bottom:2px solid #333;padding-bottom:8px;">科研说明面板</h3>\n  <p style="line-height:2;margin:0;">正文采用宋体风格，行距宽松，适合论文或技术报告。</p>\n</div>',
            "editable": True,
        },
        "festive": {
            "desc": "喜庆风格预设（红金配色）",
            "html": '<div style="background:linear-gradient(135deg,#c0392b,#e74c3c);color:#FFD700;padding:32px;border-radius:12px;text-align:center;font-family:SimSun,serif;">\n  <h2 style="margin:0 0 10px 0;font-size:1.8em;">🎊 喜庆标题</h2>\n  <p style="color:rgba(255,215,0,0.9);margin:0;">红金配色，适合婚庆、节日、庆典场景。</p>\n</div>',
            "editable": True,
        },
        "mourning": {
            "desc": "丧事风格预设（黑白灰素雅）",
            "html": '<div style="background:#f5f5f5;color:#333;padding:28px;border-radius:8px;text-align:center;border:1px solid #ddd;font-family:SimSun,serif;">\n  <h3 style="color:#333;margin:0 0 10px 0;">悼念说明</h3>\n  <p style="color:#555;margin:0;line-height:1.8;">素雅黑白灰色系，适合讣告、悼念等正式场合。</p>\n</div>',
            "editable": True,
        },
    },
}


def save_modules():
    """Persist module library to data/modules/modules.json"""
    MODULES_DIR.mkdir(parents=True, exist_ok=True)
    out = MODULES_DIR / "modules.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(MODULE_LIB, f, ensure_ascii=False, indent=2)
    print("[OK] Module library saved to: " + str(out))


def load_modules():
    """Load module library from disk"""
    mod_file = MODULES_DIR / "modules.json"
    if mod_file.exists():
        with open(mod_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return MODULE_LIB


def list_modules():
    """Print all available modules"""
    lib = load_modules()
    print("=== 可用模块库 ===")
    for cat, modules in lib.items():
        print("\n[" + cat + "]")
        for name, info in modules.items():
            editable = "✅可编辑" if info.get("editable") else "🔒固定"
            print("  " + name + " — " + info["desc"] + " (" + editable + ")")


def assemble(modules_list, output_path):
    """Assemble selected modules into one HTML file"""
    lib = load_modules()
    parts = []
    missing = []

    for item in modules_list:
        # Support "category:name" or just "name" (search all categories)
        if ":" in item:
            cat, name = item.split(":", 1)
            if cat in lib and name in lib[cat]:
                parts.append(lib[cat][name]["html"])
            else:
                missing.append(item)
        else:
            # Search all categories
            found = False
            for cat, modules in lib.items():
                if item in modules:
                    parts.append(modules[item]["html"])
                    found = True
                    break
            if not found:
                missing.append(item)

    if missing:
        print("[WARN] Missing modules: " + ", ".join(missing))
        print("  Run --list to see all available modules")

    # Wrap in standard HTML shell
    body = '\n  <div style="display:flex;flex-direction:column;gap:20px;padding:20px;">\n' + '\n'.join(parts) + '\n  </div>'
    html = ('<!DOCTYPE html>\n'
             '<html lang="zh-CN">\n<head>\n'
             '<meta charset="UTF-8">\n'
             '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
             '<title> assembled by hug-html</title>\n'
             '<style>\n'
             '* { margin:0; padding:0; box-sizing:border-box; }\n'
             'body { font-family:"Microsoft YaHei",sans-serif; background:#f5f7fa; }\n'
             '.edit-text { border:1px dashed transparent; padding:2px 4px; }\n'
             '.edit-text:hover { border-color:#888; }\n'
             '</style>\n'
             '</head>\n<body>\n' + body + '\n</body>\n</html>')

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("[OK] Assembled HTML: " + str(out))
    print("  Modules used: " + str(len(parts)) + "/" + str(len(modules_list)))
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="List all available modules")
    ap.add_argument("--modules", help="Comma-separated module names (or category:name)")
    ap.add_argument("--output", help="Output HTML file path")
    ap.add_argument("--save", action="store_true", help="Save module library to disk")
    args = ap.parse_args()

    if args.save:
        save_modules()
    elif args.list:
        list_modules()
    elif args.modules and args.output:
        mods = [m.strip() for m in args.modules.split(",")]
        assemble(mods, args.output)
    else:
        ap.print_help()
