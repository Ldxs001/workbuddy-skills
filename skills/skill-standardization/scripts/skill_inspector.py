#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_inspector.py -- Skill 结构快速扫描（蓝皮书生成器）
输出结构化报告：元信息、目录树、章节、函数、引用、安全数据

用法：
    python -m scripts.skill_inspector <skill-dir>
    python -m scripts.skill_inspector <skill-dir> --json

v2.44.0: 初始版本；结构无关扫描适配标准和非标准 skill
"""

import os
import re
import sys
import json
from pathlib import Path


def inspect_skill(skill_dir, output_format="text"):
    """
    扫描 skill 目录，生成结构化蓝皮书。
    output_format: "text" (markdown, 默认) | "json"
    自适应标准（scripts/references/assets）和非标准（文件散落根目录）结构。
    """
    skill_path = Path(skill_dir).resolve()
    skill_name = skill_path.name

    # ---- 1. 读取 SKILL.md ----
    skill_md_path = skill_path / "SKILL.md"
    fm = {}
    body_lines = []
    h2_sections = []
    body_text = ""

    if skill_md_path.exists():
        with open(skill_md_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        m_fm = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if m_fm:
            for line in m_fm.group(1).split('\n'):
                if ':' in line:
                    k, _, v = line.partition(':')
                    fm[k.strip()] = v.strip()
            body_text = content[m_fm.end():]
        else:
            body_text = content
        body_lines = body_text.split('\n')
        for m in re.finditer(r'^##\s+(.+)$', body_text, re.MULTILINE):
            h2_sections.append(m.group(1).strip())

    # ---- 2. 读取 _meta.json ----
    meta = {}
    meta_path = skill_path / "_meta.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {"error": "parse_failed"}

    # ---- 3. 扫描所有文件（结构无关，按类型分组） ----
    # 递归扫全部，忽略隐藏文件和缓存
    all_files = []
    for entry in sorted(skill_path.rglob('*')):
        if entry.name.startswith('.'):
            continue
        rel = entry.relative_to(skill_path)
        rel_str = str(rel)
        if rel_str.startswith('__pycache__') or rel_str.startswith('.git'):
            continue
        all_files.append((rel_str, entry.is_dir()))

    # 按扩展名分类（不管文件在 scripts/ 还是根目录）
    py_files = sorted([f for f, is_d in all_files if f.endswith('.py')])
    md_files = sorted([f for f, is_d in all_files
                       if f.endswith('.md') and f != 'SKILL.md' and not f.startswith('_meta')])
    script_files = sorted([f for f, is_d in all_files
                           if f.endswith(('.sh', '.bat', '.ps1', '.js', '.ts'))])
    config_files = sorted([f for f, is_d in all_files
                           if f.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'))])
    other_files = sorted([f for f, is_d in all_files
                          if f not in py_files + md_files + script_files + config_files])

    # 非标位置标记
    root_py = [f for f in py_files if '/' not in f]
    root_md = [f for f in md_files if '/' not in f]

    # 按标准目录估算标准化程度
    has_scripts_dir = (skill_path / 'scripts').is_dir()
    has_refs_dir = (skill_path / 'references').is_dir()
    standard_score = sum([has_scripts_dir, has_refs_dir])
    if standard_score == 2:
        struct_label = "标准（scripts/ + references/）"
    elif standard_score == 1:
        struct_label = "半标准（has scripts/ or references/）"
    else:
        struct_label = "非标准（文件散落根目录）"

    # ---- 4. 扫描所有 .py 文件的函数/类 ----
    py_functions = {}
    for pf in py_files:
        pf_path = skill_path / pf
        try:
            with open(pf_path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
            funcs = re.findall(r'^\s*(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\(', src, re.MULTILINE)
            classes = re.findall(r'^\s*class\s+([a-zA-Z_]\w*)\s*[:\(]', src, re.MULTILINE)
            if funcs or classes:
                py_functions[pf] = funcs + [f"class {c}" for c in classes]
        except Exception:
            py_functions[pf] = ["[读取失败]"]

    # ---- 5. 扫描所有 .md 文件概要 ----
    md_summaries = {}
    for mf in md_files:
        mf_path = skill_path / mf
        try:
            with open(mf_path, "r", encoding="utf-8", errors="replace") as f:
                m_content = f.read()
            m_lines = m_content.count('\n') + 1
            m_sections = re.findall(r'^##\s+(.+)$', m_content, re.MULTILINE)
            md_summaries[mf] = {"lines": m_lines, "sections": m_sections[:10]}
        except Exception:
            md_summaries[mf] = {"lines": 0, "sections": []}

    # ---- 6. 安全 & 数据信息 ----
    sec_info = {
        "sensitive_access": fm.get("sensitive_access", "?"),
        "critical_write": fm.get("critical_write", "?"),
        "permission_weight": fm.get("permission_weight", "?"),
        "data_dir": fm.get("data_dir", meta.get("data_dir", "?"))
    }

    # ---- 组装报告 ----
    report = {
        "name": skill_name,
        "version": fm.get("version", meta.get("version", "?")),
        "description": fm.get("description", meta.get("description", "")),
        "structure": struct_label,
        "skill_md": {
            "exists": skill_md_path.exists(),
            "lines": len(body_lines),
            "h2_sections_count": len(h2_sections),
            "h2_sections": h2_sections,
            "frontmatter_fields": list(fm.keys()) if fm else [],
        },
        "meta_json": meta,
        "directory": {
            "py_files": len(py_files),
            "md_files": len(md_files),
            "script_files": len(script_files),
            "config_files": len(config_files),
            "other_files": len(other_files),
            "root_py": root_py,
            "root_md": root_md,
        },
        "python_functions": py_functions,
        "reference_summaries": md_summaries,
        "security": sec_info,
    }

    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2)

    return _format_text_report(report, skill_path)


def _format_text_report(report, skill_path):
    """格式化为可读的 Markdown 蓝皮书"""
    lines = []
    name = report["name"]
    ver = report["version"]

    lines.append(f"=== {name} v{ver} ===")
    lines.append("")

    # ---- 元信息 ----
    lines.append("|-- 元信息")
    smd = report["skill_md"]
    lines.append(f"|   |-- SKILL.md: {'[OK]' if smd['exists'] else '[MISS]'}"
                 f" ({smd['lines']}行, {smd['h2_sections_count']}个 ## 章节)")
    lines.append(f"|   |-- 结构: {report['structure']}")
    desc = report.get("description", "")
    if desc:
        lines.append(f"|   |-- 描述: {desc[:80]}{'...' if len(desc) > 80 else ''}")
    meta = report.get("meta_json", {})
    if meta and "error" not in meta:
        meta_fields = list(meta.keys())
        lines.append(f"|   +-- _meta.json: {len(meta_fields)} 字段 ({', '.join(meta_fields[:6])})")
    else:
        lines.append("|   +-- _meta.json: [MISS] 缺失或解析失败")
    lines.append("")

    # ---- 文件清单（按类型分组） ----
    lines.append("|-- 文件清单")
    d = report["directory"]
    lines.append(f"|   |-- Python: {d['py_files']} 个")
    if d['root_py']:
        for rp in d['root_py']:
            lines.append(f"|   |   [note] {rp} 在根目录（非标准），建议迁至 scripts/")
    lines.append(f"|   |-- Markdown: {d['md_files']} 个")
    if d['root_md']:
        for rm in d['root_md']:
            lines.append(f"|   |   [note] {rm} 在根目录（非标准），建议迁至 references/")
    lines.append(f"|   |-- 脚本(sh/bat/js): {d['script_files']} 个")
    lines.append(f"|   |-- 配置(json/yaml): {d['config_files']} 个")
    lines.append(f"|   +-- 其他: {d['other_files']} 个")
    lines.append("")

    # ---- 正文章节 ----
    sections = smd["h2_sections"]
    if sections:
        lines.append("|-- 正文章节 (##)")
        for sec in sections:
            lines.append(f"|   +-- {sec}")
        lines.append("")

    # ---- 功能清单 ----
    py_funcs = report.get("python_functions", {})
    if py_funcs:
        lines.append("|-- 功能清单 (Python)")
        py_items = list(py_funcs.items())
        for i, (fpath, funcs) in enumerate(py_items):
            marker = "+--" if i == len(py_items) - 1 else "|--"
            func_str = ", ".join(funcs[:8])
            if len(funcs) > 8:
                func_str += f" ... (共{len(funcs)}个)"
            lines.append(f"|   {marker} {fpath}: {func_str}")
        lines.append("")

    # ---- 引用文件概览 ----
    refs = report.get("reference_summaries", {})
    if refs:
        lines.append("|-- 引用文件概览")
        ref_items = list(refs.items())
        for i, (fname, info) in enumerate(ref_items):
            marker = "+--" if i == len(ref_items) - 1 else "|--"
            sec_str = f", {len(info['sections'])} sections" if info['sections'] else ""
            lines.append(f"|   {marker} {fname} ({info['lines']}行{sec_str})")
            for sec in info['sections'][:4]:
                lines.append(f"|       + {sec}")
        lines.append("")

    # ---- 安全 & 数据 ----
    sec = report["security"]
    lines.append("+-- 安全 & 数据")
    lines.append(f"    |-- sensitive_access: {sec['sensitive_access']}")
    lines.append(f"    |-- critical_write: {sec['critical_write']}")
    lines.append(f"    |-- permission_weight: {sec['permission_weight']}")
    lines.append(f"    +-- data_dir: {sec['data_dir']}")

    lines.append("")
    lines.append("-" * 40)
    lines.append("[tip] 将此报告用于 update/refactor 前了解技能全貌")
    lines.append(f"   python -m scripts.skill_inspector {skill_path} --json  (JSON format)")

    return "\n".join(lines)


def main():
    """CLI 入口"""
    if sys.stdout.encoding and sys.stdout.encoding.upper() not in ('UTF-8', 'UTF8'):
        sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, errors='replace')

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python -m scripts.skill_inspector <skill-dir> [--json]")
        print("Output skill blueprint for understanding full structure before update/refactor")
        sys.exit(1)

    skill_dir = sys.argv[1]
    fmt = "json" if "--json" in sys.argv else "text"

    if not os.path.isdir(skill_dir):
        print(f"[ERROR] Directory not found: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    result = inspect_skill(skill_dir, fmt)
    print(result)


if __name__ == "__main__":
    main()
