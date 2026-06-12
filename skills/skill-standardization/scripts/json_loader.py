#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
json_loader.py — SKILL.md 标准化规范渐进式 JSON 加载器 (v2.0.0)

按需加载规范定义模块，支持级联引用解析。
用法:
    python json_loader.py load <module>          # 加载指定模块
    python json_loader.py list                   # 列出可用模块
    python json_loader.py show <module>          # 展示模块内容（美化输出）
    python json_loader.py refs <module>          # 展示模块的依赖关系图
"""

import sys
import logging

logger = logging.getLogger(__name__)
import os
import json
import argparse

# ── 路径配置 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPEC_DIR = os.path.join(SCRIPT_DIR, "spec")
INDEX_FILE = os.path.join(SPEC_DIR, "_index.json")


def load_index():
    """加载规范索引"""
    if not os.path.isfile(INDEX_FILE):
        print(f"❌ 索引文件不存在: {INDEX_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_module(module_name, _loaded=None, depth=0):
    """递归加载模块及其依赖。

    Args:
        module_name: 模块名（frontmatter / body / rules / all）
        _loaded: 已加载模块集合（防止循环依赖）
        depth: 递归深度（用于缩进）

    Returns:
        dict: 合并后的模块数据
    """
    if _loaded is None:
        _loaded = set()

    index = load_index()
    modules = index.get("modules", {})

    if module_name not in modules:
        available = ", ".join(modules.keys())
        print(f"❌ 未知模块: '{module_name}'，可用: {available}", file=sys.stderr)
        sys.exit(1)

    mod_info = modules[module_name]

    # 特殊处理 'all'：合并所有依赖模块
    if module_name == "all":
        result = {"_merged": True, "_modules_loaded": [], "parts": {}}
        for dep_name in mod_info.get("depends_on", []):
            if dep_name not in _loaded:
                part_data = load_module(dep_name, _loaded | {dep_name}, depth + 1)
                result["parts"][dep_name] = part_data
                result["_modules_loaded"].append(dep_name)
        return result

    # 普通模块：从 JSON 文件加载
    mod_file = mod_info.get("file")
    if not mod_file:
        print(f"⚠️  模块 '{module_name}' 无关联文件（虚拟模块）", file=sys.stderr)
        return {"_module": module_name, "_virtual": True}

    file_path = os.path.join(SPEC_DIR, mod_file)
    if not os.path.isfile(file_path):
        print(f"❌ 模块文件不存在: {file_path}", file=sys.stderr)
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 加载依赖项并合并
    depends_on = mod_info.get("depends_on", [])
    if depends_on:
        data["_dependencies"] = {}
        for dep_name in depends_on:
            if dep_name not in _loaded:
                dep_data = load_module(dep_name, _loaded | {dep_name}, depth + 1)
                data["_dependencies"][dep_name] = dep_data

    _loaded.add(module_name)
    return data


# ── CLI 命令 ────────────────────────────────────────────────


def cmd_list():
    """列出所有可用模块"""
    index = load_index()
    modules = index.get("modules", {})
    version = index.get("_version", "?")

    print(f"\nSKILL.md 标准化规范 v{version}")
    print(f"{'模块':<16} {'文件':<20} 描述")
    print("-" * 70)
    for name, info in modules.items():
        f = info.get("file") or "(虚拟)"
        deps = ", ".join(info.get("depends_on", []))
        dep_str = f" [依赖: {deps}]" if deps else ""
        print(f"  {name:<14} {f:<18} {info.get('description', '')}{dep_str}")


def cmd_load(args):
    """加载指定模块并输出 JSON"""
    module_name = args.module
    data = load_module(module_name)

    if args.json or not sys.stdout.isatty():
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # 美化输出
        print(f"\n{'='*60}")
        mod = data.get("_module", module_name)
        ver = data.get("_version", "?")
        desc = data.get("_description", "")
        print(f"  模块: {mod} v{ver}")
        if desc:
            print(f"  描述: {desc}")
        print(f"{'='*60}")

        # 输出关键字段
        for key in ["required_fields", "optional_fields", "required_sections",
                     "recommended_sections", "optional_sections",
                     "format_rules", "rules", "section_synonyms"]:
            if key in data:
                items = data[key]
                count = len(items) if isinstance(items, list) else "?"
                print(f"\n  📋 {key}: {count} 项")
                if isinstance(items, list) and count <= 15:
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("name", item.get("id", item.get("heading_level", "?")))
                            desc = item.get("description", item.get("check_description", ""))
                            print(f"     - {name}: {desc[:60]}")

        # 显示依赖
        if "_dependencies" in data:
            print(f"\n  🔗 已加载依赖: {', '.join(data['_dependencies'].keys())}")

        if "_merged" in data and data["_merged"]:
            loaded = data.get("_modules_loaded", [])
            print(f"\n  📦 全量合并模式，已加载 {len(loaded)} 个子模块: {', '.join(loaded)}")


def cmd_show(args):
    """展示模块完整内容（原始 JSON）"""
    module_name = args.module
    data = load_module(module_name)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_refs(args):
    """展示模块依赖关系"""
    module_name = args.module
    index = load_index()
    modules = index.get("modules", {})

    if module_name == "all":
        print("\n📊 全量依赖关系图:")
        print("   all")
        for m in modules.get("all", {}).get("depends_on", []):
            info = modules[m]
            deps = info.get("depends_on", [])
            dep_str = f" → {', '.join(deps)}" if deps else ""
            print(f"   ├── {m}{dep_str}")
        return

    if module_name not in modules:
        print(f"❌ 未知模块: {module_name}", file=sys.stderr)
        sys.exit(1)

    info = modules[module_name]
    deps = info.get("depends_on", [])

    print(f"\n📋 模块: {module_name}")
    print(f"   文件: {info.get('file') or '(虚拟)'}")
    print(f"   描述: {info.get('description', '')}")
    if deps:
        print(f"   依赖 ({len(deps)}):")
        for d in deps:
            d_info = modules.get(d, {})
            d_deps = d_info.get("depends_on", [])
            d_dep_str = f" [→ {', '.join(d_deps)}]" if d_deps else ""
            print(f"     ├─ {d}{d_dep_str}")
    else:
        print(f"   依赖: 无（叶子节点）")


def main():
    parser = argparse.ArgumentParser(
        description="SKILL.md 标准化规范渐进式 JSON 加载器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # load 子命令
    p_load = subparsers.add_parser("load", help="加载指定模块（默认美化输出）")
    p_load.add_argument("module", help="模块名: frontmatter / body / rules / all")
    p_load.add_argument("--json", action="store_true", help="JSON 原始输出")

    # list 子命令
    subparsers.add_parser("list", help="列出所有可用模块")

    # show 子命令
    p_show = subparsers.add_parser("show", help="展示模块完整内容（JSON）")
    p_show.add_argument("module", help="模块名")

    # refs 子命令
    p_refs = subparsers.add_parser("refs", help="展示模块依赖关系")
    p_refs.add_argument("module", nargs="?", default="all", help="模块名（默认 all）")

    args = parser.parse_args()

    if args.command == "load":
        cmd_load(args)
    elif args.command == "list":
        cmd_list()
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "refs":
        cmd_refs(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
