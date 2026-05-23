#!/usr/bin/env python3
"""
skill_builder.py — Skill 标准化构建器 v2.6.0

支持三种模式：
  create   — 从模板初始化新的标准 skill
  update   — 对已有 skill 进行增量规范化更新
  refactor — 对非标 skill 进行整体改造（信息零遗漏）

基于 SKILL.md 标准化规范草案 v0.1 + 目录结构规范 + 渐进式 MD 体系。

用法：
  python skill_builder.py create <name> --desc "描述" [--dir <path>] [--tags tag1,tag2]
  python skill_builder.py update <skill_dir> [--fix] [--backup] [--workspace <path>]
  python skill_builder.py refactor <skill_dir> [--backup] [--dry-run] [--workspace <path>]

作者：[username-redacted]
许可：MIT
零外部依赖，仅使用 Python 标准库。
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────

__version__ = "2.6.0"

SPEC_DIR = Path(__file__).parent / "spec"
SKILL_TEMPLATE = """---
name: {name}
version: 0.1.0
author: your-name-here
license: MIT
description: >
  {description}
tags: [{tags}]
---

# {name} — {title}

{description}

## 触发场景

当用户提到以下意图时触发本技能：
- <!-- TODO: 填写触发条件 -->

## 核心能力

| # | 功能 | 说明 |
|---|------|------|
| 1 | <!-- TODO --> | <!-- TODO --> |

## 快速开始

```bash
# 最简用法示例
```

## 主要流程

<!-- 在此描述主要工作流程 -->

→ 详见 `references/guide.md` 完整教程（按需创建）
"""

META_TEMPLATE = '{{"name": "{name}", "version": "0.1.0", "description": "{description}", "author": "your-name-here", "tags": [{tags_json}]}}'

# 主 SKILL.md 必须包含的章节（用于 update/refactor 检查）
REQUIRED_SECTIONS = [
    ("触发场景", ["触发条件", "触发场景", "适用场景", "触发"]),
    ("核心能力", ["核心功能", "核心能力", "概述", "核心概念", "Overview", "技能概述"]),
    ("快速开始", ["快速开始", "快速上手", "Quick Start"]),
]

# 可选拆分到 references/ 的章节关键词（用于 refactor 拆分判断）
SPLITTABLE_KEYWORDS = {
    "详细教程": ["详细教程", "使用指南", "完整指南", "逐步指南"],
    "示例集合": ["示例", "examples", "用例", "案例"],
    "参考文档": ["参考文档", "API 参考", "命令参考", "参数说明"],
    "常见问题": ["常见问题", "FAQ", "faq", "疑难解答"],
    "版本日志": ["更新日志", "changelog", "版本历史", "变更记录"],
    "架构设计": ["架构", "architecture", "设计", "模块说明"],
}


def load_spec(module_name):
    """加载 spec/ 下的 JSON 规范文件"""
    spec_file = SPEC_DIR / f"{module_name}.json"
    if spec_file.exists():
        with open(spec_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ═══════════════════════════════════════════════════════
# CREATE 命令：从模板初始化新 skill
# ═══════════════════════════════════════════════════════

def cmd_create(args):
    """创建新的标准 skill 目录结构"""
    name = args.name
    description = args.desc or f"{name} skill"
    tags = args.tags or []
    base_dir = Path(args.dir) if args.dir else Path.cwd()

    skill_dir = base_dir / name

    # 检查是否已存在
    if skill_dir.exists():
        print(f"❌ 目录已存在: {skill_dir}")
        sys.exit(1)

    # 创建目录结构
    skill_dir.mkdir(parents=True)
    (skill_dir / "references").mkdir(exist_ok=True)
    (skill_dir / "scripts").mkdir(exist_ok=True)

    # 写入 SKILL.md
    tags_str = ", ".join(f'"{t}"' for t in tags) if tags else '"todo"'
    tags_simple = ", ".join(tags) if tags else "todo"

    skill_content = SKILL_TEMPLATE.format(
        name=name,
        title=name.replace("-", " ").replace("_", " ").title(),
        description=description,
        tags=tags_simple,
    )
    with open(skill_dir / "SKILL.md", "w", encoding="utf-8") as f:
        f.write(skill_content)

    # 写入 _meta.json
    meta_content = META_TEMPLATE.format(
        name=name,
        description=description,
        tags_json=tags_str,
    )
    with open(skill_dir / "_meta.json", "w", encoding="utf-8") as f:
        f.write(meta_content)

    # 创建 .gitkeep 保持空目录
    (skill_dir / "references" / ".gitkeep").write_text("", encoding="utf-8")
    (skill_dir / "scripts" / ".gitkeep").write_text("", encoding="utf-8")

    print(f"✅ Skill 已创建: {skill_dir}")
    print(f"   ├── SKILL.md      (主文件)")
    print(f"   ├── _meta.json    (元数据)")
    print(f"   ├── references/         (渐进式 MD)")
    print(f"   └── scripts/      (脚本目录)")
    print(f"\n下一步:")
    print(f"   1. 编辑 SKILL.md 填写 TODO 占位符")
    print(f"   2. 如需脚本，放入 scripts/")
    print(f"   3. 如需辅助文档，放入 references/")


# ═══════════════════════════════════════════════════════
# UPDATE 命令：增量规范化更新
# ═══════════════════════════════════════════════════════

def cmd_update(args):
    """对已有的 skill 进行增量规范化检查和可选修复"""
    skill_dir = Path(args.skill_dir)
    if not skill_dir.exists():
        print(f"❌ Skill 目录不存在: {skill_dir}")
        sys.exit(1)

    name = skill_dir.name
    backup_dir = None
    if args.backup:
        backup_dir = _create_backup(skill_dir, "update", args.workspace)

    results = {"checks": [], "fixes": [], "warnings": []}

    # 检查 1: _meta.json 是否存在且标准
    meta_file = skill_dir / "_meta.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            required_meta_keys = ["name", "version", "description", "author", "tags"]
            missing = [k for k in required_meta_keys if k not in meta]
            if missing:
                results["warnings"].append(f"_meta.json 缺少字段: {missing}")
                if args.fix:
                    for k in missing:
                        meta[k] = "" if k != "tags" else []
                    _write_json(meta_file, meta)
                    results["fixes"].append(f"补充 _meta.json 缺失字段: {missing}")
            else:
                results["checks"].append("✅ _meta.json 结构正常")
        except json.JSONDecodeError as e:
            results["warnings"].append(f"_meta.json JSON 格式错误: {e}")
    else:
        results["warnings"].append("⚠️  _meta.json 不存在")
        if args.fix:
            _write_json(meta_file, {
                "name": name,
                "version": "0.1.0",
                "description": f"{name} skill",
                "author": "your-name-here",
                "tags": [],
            })
            results["fixes"].append("创建 _meta.json")

    # 检查 2: SKILL.md 是否存在
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        results["warnings"].append("⚠️  SKILL.md 不存在")
    else:
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查 frontmatter
        if content.startswith("---"):
            results["checks"].append("✅ SKILL.md 有 frontmatter")
        else:
            results["warnings"].append("⚠️  SKILL.md 缺少 frontmatter")
            if args.fix:
                # 不自动添加 frontmare（需要用户提供信息）
                results["warnings"].append("   → 需要手动添加 frontmatter（请用 refactor 或手动编辑）")

        # 检查必填章节
        lines = content.split("\n")
        h2_lines = [l.strip().strip("#").strip() for l in lines if l.strip().startswith("## ")]

        for section_name, keywords in REQUIRED_SECTIONS:
            found = any(any(kw.lower() in h.lower() for kw in keywords) for h in h2_lines)
            if found:
                results["checks"].append(f"✅ 包含章节: {section_name}")
            else:
                results["warnings"].append(f"⚠️  SKILL.md 可能缺少章节: {section_name}（关键词: {keywords}）")

        # 检查文件大小
        line_count = len(lines)
        if line_count > 200:
            results["warnings"].append(
                f"💡 SKILL.md 共 {line_count} 行，超过 200 行建议拆分到 references/"
            )

    # 检查 3: 目录结构规范性
    root_files = [f.name for f in skill_dir.iterdir() if f.is_file()]
    expected_root = {"SKILL.md", "_meta.json"}
    unexpected_root = set(root_files) - expected_root - {".gitignore"}

    if unexpected_root:
        results["warnings"].append(
            f"💡 根目录有非常规文件: {sorted(unexpected_root)}（建议移入对应子目录）"
        )

    # 检查 4: 产出物路径规范性（铁律4）
    artifact_violations = _check_artifact_paths(skill_dir)
    if artifact_violations:
        results["warnings"].append(
            f"🔍 产出物路径违规（铁律4）— 发现 {len(artifact_violations)} 处："
        )
        for v in artifact_violations:
            results["warnings"].append(f"   {v}")

    # 输出报告
    print(f"\n{'='*50}")
    print(f"📋 Skill 更新检查报告: {name}")
    print(f"{'='*50}")

    if results["checks"]:
        print("\n✅ 通过项:")
        for c in results["checks"]:
            print(f"   {c}")

    if results["warnings"]:
        print("\n⚠️  警告/建议:")
        for w in results["warnings"]:
            print(f"   {w}")

    if args.fix and results["fixes"]:
        print("\n🔧 已修复:")
        for f in results["fixes"]:
            print(f"   ✅ {f}")

    if backup_dir:
        print(f"\n📦 备份位置: {backup_dir}")

    error_count = len([w for w in results["warnings"] if w.startswith("❌") or w.startswith("⚠️  ")])
    warn_count = len(results["warnings"]) - error_count

    print(f"\n结论: ERROR={error_count} WARN={warn_count} PASS={len(results['checks'])}")

    # 保存报告到标准化工作区
    report_lines = [f"Skill 更新检查报告: {name}", "=" * 50, ""]
    report_lines.append("通过项:")
    for c in results["checks"]:
        report_lines.append(f"  {c}")
    if results["warnings"]:
        report_lines.append("\n警告/建议:")
        for w in results["warnings"]:
            report_lines.append(f"  {w}")
    if results.get("fixes"):
        report_lines.append("\n已修复:")
        for f in results["fixes"]:
            report_lines.append(f"  {f}")
    report_lines.append(f"\n结论: ERROR={error_count} WARN={warn_count} PASS={len(results['checks'])}")
    if backup_dir:
        report_lines.append(f"\n备份位置: {backup_dir}")

    report_path = _save_report(skill_dir, "update", "\n".join(report_lines), args.workspace)
    print(f"📄 报告位置: {report_path}")


# ═══════════════════════════════════════════════════════
# REFACTOR 命令：整体改造非标 skill（信息零遗漏）
# ═══════════════════════════════════════════════════════

def cmd_refactor(args):
    """
    整体改造非标 skill 到标准结构。

    信息完整性保障机制：
    1. 执行前必须备份（除非 --no-backup）
    2. 全量扫描所有文件，生成清单
    3. 仅做移动操作（move），不做删除操作
    4. 移动后对比原始清单确保零丢失
    5. 输出完整映射报告
    """
    skill_dir = Path(args.skill_dir).resolve()
    if not skill_dir.exists():
        print(f"❌ Skill 目录不存在: {skill_dir}")
        sys.exit(1)

    name = skill_dir.name

    # 阶段 1：全量扫描
    print(f"\n🔍 阶段 1: 全量扫描 {name}")
    print("-" * 40)

    all_files = _scan_all_files(skill_dir)
    original_count = len(all_files)

    print(f"  发现 {original_count} 个文件:")
    for rel_path in sorted(all_files.keys()):
        info = all_files[rel_path]
        size_str = f"{info['size']}B" if info['size'] < 1024 else f"{info['size']/1024:.1f}KB"
        print(f"    {rel_path:<40} {size_str:>8}")

    # 分析根目录散落文件
    root_loose_files = [p for p in all_files if "/" not in p and p not in ("SKILL.md", "_meta.json")]
    has_old_meta = any(p.endswith("_skillhub_meta.json") for p in all_files)

    print(f"\n  📊 分析结果:")
    print(f"    根目录散落文件: {len(root_loose_files)} 个")
    if root_loose_files:
        for f in root_loose_files:
            print(f"      - {f}")
    if has_old_meta:
        print(f"    ⏳ 发现旧版 _skillhub_meta.json（建议保留或迁移后删除）")

    if args.dry_run:
        print(f"\n🏁 DRY RUN 模式 — 不会执行任何实际操作")
        _print_refactor_plan(skill_dir, all_files, root_loose_files)
        return

    # 阶段 2：备份（强制）
    backup_dir = None
    if not args.no_backup:
        backup_dir = _create_backup(skill_dir, "refactor", args.workspace)

    # 阶段 3：构建迁移计划并执行
    print(f"\n🔧 阶段 2: 执行标准化迁移")
    print("-" * 40)

    migration_log = []  # (src_rel, dst_rel, action)

    # 确保目标子目录存在
    references_dir = skill_dir / "references"
    scripts_dir = skill_dir / "scripts"
    references_dir.mkdir(exist_ok=True)
    scripts_dir.mkdir(exist_ok=True)

    moved_count = 0
    skipped_count = 0

    for rel_path in sorted(all_files.keys()):
        abs_path = skill_dir / rel_path
        if not abs_path.exists():
            continue

        target_rel = None
        action = "keep"

        # 跳过标准根目录文件
        if rel_path in ("SKILL.md", "_meta.json"):
            skipped_count += 1
            migration_log.append((rel_path, rel_path, "keep (standard)"))
            continue

        # 跳过旧版 meta 文件（保留在原位）
        if rel_path == "_skillhub_meta.json":
            skipped_count += 1
            migration_log.append((rel_path, rel_path, "keep (legacy)"))
            continue

        # 跳过 .git 相关
        if rel_path.startswith(".git") or rel_path == ".gitignore":
            skipped_count += 1
            migration_log.append((rel_path, rel_path, "keep (git)"))
            continue

        # 跳过 __pycache__
        if "__pycache__" in rel_path:
            skipped_count += 1
            migration_log.append((rel_path, rel_path, "skip (cache)"))
            continue

        # 判断移动目标
        ext = Path(rel_path).suffix.lower()
        parent = Path(rel_path).parent.name if "/" in rel_path else ""

        # 文件类型 → 目标目录规则
        if ext in (".py", ".sh", ".bat", ".ps1"):
            target_rel = f"scripts/{Path(rel_path).name}"
            action = f"move → scripts/"
        elif ext == ".json" and "spec" not in rel_path and "meta" not in rel_path:
            target_rel = f"scripts/{Path(rel_path).name}"
            action = f"move → scripts/"
        elif ext == ".md" and rel_path != "SKILL.md":
            target_rel = f"references/{Path(rel_path).name}"
            action = f"move → references/"
        elif ext in (".txt", ".cfg", ".ini", ".toml") and rel_path != ".gitignore":
            target_rel = f"scripts/{Path(rel_path).name}"
            action = f"move → scripts/"
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"):
            target_rel = f"assets/{Path(rel_path).name}"
            action = f"move → assets/"
            (skill_dir / "assets").mkdir(exist_ok=True)
        elif ext in (".yaml", ".yml"):
            target_rel = f"scripts/{Path(rel_path).name}"
            action = f"move → scripts/"
        else:
            # 未知类型，保留原位
            skipped_count += 1
            migration_log.append((rel_path, rel_path, f"keep (unknown type: {ext})"))
            continue

        # 执行移动
        if target_rel:
            target_abs = skill_dir / target_rel

            # 目标已存在则重命名
            if target_abs.exists():
                stem = Path(target_rel).stem
                suffix = Path(target_rel).suffix
                target_rel = f"{Path(target_rel).parent}/{stem}_orig{suffix}"
                target_abs = skill_dir / target_rel
                action += " (renamed)"

            try:
                shutil.move(str(abs_path), str(target_abs))
                moved_count += 1
                migration_log.append((rel_path, target_rel, action))
            except Exception as e:
                print(f"  ❌ 移动失败: {rel_path} → {target_rel}: {e}")
                migration_log.append((rel_path, rel_path, f"FAILED: {e}"))

    # 阶段 4：验证零丢失
    print(f"\n✅ 阶段 3: 验证信息完整性")
    print("-" * 40)

    after_files = _scan_all_files(skill_dir)
    after_count = len(after_files)

    # 排除 __pycache__ 后比较
    original_clean = {k: v for k, v in all_files.items() if "__pycache__" not in k}
    after_clean = {k: v for k, v in after_files.items() if "__pycache__" not in k}

    lost_files = set(original_clean.keys()) - {
        k for k in after_clean.keys()
        # 排除已成功移动的源路径
        if not any(m[0] == k and "move →" in m[2] for m in migration_log)
    }

    # 更精确的检查：统计所有有内容的文件
    original_total_size = sum(v["size"] for v in original_clean.values())
    after_total_size = sum(v["size"] for v in after_clean.values())

    print(f"  迁移前: {len(original_clean)} 个文件, 总大小 {original_total_size:,} 字节")
    print(f"  迁移后: {len(after_clean)} 个文件, 总大小 {after_total_size:,} 字节")
    print(f"  移动了: {moved_count} 个文件")
    print(f"  保留了: {skipped_count} 个文件")

    if after_total_size >= original_total_size * 0.99:  # 允许 1% 的误差（换行符等）
        print(f"  ✅ 信息完整性验证通过（文件总大小一致）")
    else:
        print(f"  ⚠️  文件总大小不一致！差异: {abs(after_total_size - original_total_size):,} 字节")
        print(f"  🔴 请检查是否有文件丢失！")

    # 输出迁移映射表
    print(f"\n📋 迁移映射表:")
    print("-" * 60)
    for src, dst, act in migration_log:
        if "move →" in act:
            print(f"  {src:<35} → {dst:<35}")
        elif "keep" in act:
            print(f"  {src:<35}   ({act})")

    if backup_dir:
        print(f"\n📦 备份位置: {backup_dir}")
        print(f"   如需回滚: mv \"{backup_dir}\" \"{skill_dir}\"")

    # 输出后续建议
    print(f"\n📝 后续建议:")
    print(f"   1. 检查 SKILL.md 是否需要更新（添加渐进式引用等）")
    print(f"   2. 检查 references/ 下拆分的文件是否合理归类")
    print(f"   3. 如有旧版 _skillhub_meta.json，确认是否可删除")
    print(f"   4. 运行 `python skill_audit.py audit {skill_dir}` 验证")

    # 保存迁移报告到标准化工作区
    report_lines = [f"Skill 改造报告: {name}", "=" * 60, ""]
    report_lines.append(f"迁移前: {len(original_clean)} 个文件, 总大小 {original_total_size:,} 字节")
    report_lines.append(f"迁移后: {len(after_clean)} 个文件, 总大小 {after_total_size:,} 字节")
    report_lines.append(f"移动了: {moved_count} 个文件")
    report_lines.append(f"保留了: {skipped_count} 个文件")
    report_lines.append("\n迁移映射表:")
    report_lines.append("-" * 60)
    for src, dst, act in migration_log:
        report_lines.append(f"  {src:<35} → {dst if dst else '—':<35} ({act})")
    if backup_dir:
        report_lines.append(f"\n备份位置: {backup_dir}")

    report_path = _save_report(skill_dir, "refactor", "\n".join(report_lines), args.workspace)
    print(f"📄 报告位置: {report_path}")


# ── 辅助函数 ──────────────────────────────────────────

# -- 产出物路径检测（铁律4） --

_ARTIFACT_DIR_NAMES = [
    "outputs", "output", "artifacts", "results", "exports",
    "reports", "report", "backups", "backup", "generated",
    "dumps", "dump", "build", "dist", "logs", "log",
    "data", "cache", "temp", "tmp", "out",
]

_ARTIFACT_DIR_RE = "|".join(_ARTIFACT_DIR_NAMES)

_ARTIFACT_WRITE_PATTERNS = [
    re.compile(rf'__file__\s*\)\s*\.\s*parent\s*/\s*"({_ARTIFACT_DIR_RE})"'),
    re.compile(rf'os\.path\.dirname\s*\(\s*__file__\s*\)\s*,\s*"({_ARTIFACT_DIR_RE})"'),
    re.compile(rf'os\.path\.join\s*\(\s*os\.path\.dirname\s*\(\s*__file__\s*\)\s*,\s*"({_ARTIFACT_DIR_RE})"'),
    re.compile(rf'open\s*\(\s*["\'](?:\./)?({_ARTIFACT_DIR_RE}/[^"\']+)["\']\s*,\s*["\']w["\']'),
    re.compile(rf'Path\s*\(\s*["\']\.?({_ARTIFACT_DIR_RE})["\']'),
    re.compile(r'open\s*\(\s*["\']([^"\']+\.(json|csv|html|png|jpg|pdf|txt|ics))["\']\s*,\s*["\']w["\']'),
]

_ARTIFACT_CLASSIFY = {
    "data": "data", "backup": "data", "backups": "data", "dump": "data", "dumps": "data",
    "cache": "cache", "tmp": "temp", "temp": "temp",
    "output": "outputs", "outputs": "outputs", "out": "outputs",
    "result": "outputs", "results": "outputs", "export": "outputs", "exports": "outputs",
    "report": "outputs", "reports": "outputs", "log": "outputs", "logs": "outputs",
    "build": "outputs", "dist": "outputs", "generated": "outputs",
    "artifact": "outputs", "artifacts": "outputs",
}

_TEXT_EXTS = {".md", ".json", ".yaml", ".yml", ".txt", ".cfg", ".toml", ".ini", ".html"}


def _extract_path_literal(line_text, matched_target):
    """从违规行中提取完整的路径字面量（引号内的内容）。"""
    quoted = re.findall(r"""["']([^"']+)["']""", line_text)
    for q in quoted:
        if matched_target in q:
            return q
    return matched_target


def _check_artifact_paths(skill_dir):
    """扫描 scripts/ 下脚本，检测违反铁律4的产出物路径。
    
    同时反向搜索整个 skill 目录找出引用同一路径的关联文件。
    
    Returns:
        list: 违规描述字符串列表（含交叉引用信息），空列表表示无违规
    """
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []
    
    violations = []  # {source, path_literal, suggestion}
    for fpath in sorted(scripts_dir.iterdir()):
        ext = fpath.suffix.lower()
        if ext not in (".py", ".sh", ".bat", ".ps1"):
            continue
        if not fpath.is_file():
            continue
        
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").split("\n")
        except Exception:
            continue
        
        rel = f"scripts/{fpath.name}"
        
        if ext == ".py":
            for i, line in enumerate(lines, 1):
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("import ") or s.startswith("from "):
                    continue
                for pat in _ARTIFACT_WRITE_PATTERNS:
                    m = pat.search(s)
                    if m and "standardization" not in s.lower() and '"r"' not in s and "'r'" not in s:
                        target = m.group(1)
                        path_literal = _extract_path_literal(s, target)
                        # 根据 target 结构确定分类和建议
                        if "/" in target:
                            dir_part = target.split("/")[0]
                            cat = _ARTIFACT_CLASSIFY.get(dir_part.lower(), "outputs")
                            filename = target.split("/")[-1]
                            if "." in filename:
                                suggestion = f"<workspace>/standardization/<skill>/{cat}/{filename}"
                            else:
                                suggestion = f"<workspace>/standardization/<skill>/{cat}/{target}"
                        elif "." in target:
                            cat = _ARTIFACT_CLASSIFY.get(target.lower(), "outputs")
                            suggestion = f"<workspace>/standardization/<skill>/{cat}/{target}"
                        else:
                            cat = _ARTIFACT_CLASSIFY.get(target.lower(), "outputs")
                            suggestion = f"<workspace>/standardization/<skill>/{cat}/"
                        
                        violations.append({
                            "source": f"{rel}:{i}",
                            "path_literal": path_literal,
                            "suggestion": suggestion,
                        })
                        break
        elif ext in (".sh", ".bat", ".ps1"):
            for i, line in enumerate(lines, 1):
                s = line.strip()
                if not s or s.startswith("#") or s.startswith("::"):
                    continue
                m = re.search(rf'[>]+\s*["\']?\.?({_ARTIFACT_DIR_RE})/', s)
                if m and "standardization" not in s.lower():
                    target = m.group(1)
                    path_literal = _extract_path_literal(s, target) or f"{target}/"
                    cat = _ARTIFACT_CLASSIFY.get(target.lower(), "outputs")
                    violations.append({
                        "source": f"{rel}:{i}",
                        "path_literal": path_literal,
                        "suggestion": f"<workspace>/standardization/<skill>/{cat}/",
                    })
    
    # ── 交叉引用追踪 ──
    if violations:
        _trace_cross_refs(skill_dir, violations)
    
    # 格式化为输出字符串
    result = []
    for v in violations:
        line = f"{v['source']}  产出 \"{v['path_literal']}\" — 应迁至 {v['suggestion']}"
        if v.get("cross_refs"):
            line += f"\n      ⚠️ 关联引用 ({len(v['cross_refs'])}处): {', '.join(v['cross_refs'])}"
        result.append(line)
    
    return result


def _trace_cross_refs(skill_dir, violations):
    """反向搜索整个 skill 目录，找出引用每个违规路径的关联文件。"""
    search_patterns = list(set(v["path_literal"] for v in violations))
    
    # 收集搜索目标文件
    searchable_files = []
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        rel_root = os.path.relpath(root, skill_dir).replace("\\", "/")
        if rel_root == ".":
            rel_root = ""
        if rel_root.startswith("scripts") or rel_root == "scripts":
            continue
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _TEXT_EXTS:
                continue
            fpath = os.path.join(root, fname)
            rel_f = os.path.join(rel_root, fname).replace("\\", "/") if rel_root else fname
            searchable_files.append((rel_f, fpath))
    
    pattern_to_refs = {}
    for rel, fpath in searchable_files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                file_lines = f.readlines()
        except Exception:
            continue
        for i, line in enumerate(file_lines, 1):
            for pattern in search_patterns:
                if pattern in line:
                    pattern_to_refs.setdefault(pattern, []).append(f"{rel}:{i}")
    
    for v in violations:
        refs = pattern_to_refs.get(v["path_literal"], [])
        refs = [r for r in refs if r != v["source"]]
        if refs:
            v["cross_refs"] = refs


# -- 文件扫描 --

def _scan_all_files(directory):
    """递归扫描目录下所有文件，返回 {相对路径: {size, mtime}}"""
    result = {}
    directory = Path(directory)
    for root, dirs, files in os.walk(directory):
        # 排除 __pycache__ 和 .git
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fname in files:
            fpath = Path(root) / fname
            rel = str(fpath.relative_to(directory)).replace("\\", "/")
            try:
                result[rel] = {"size": fpath.stat().st_size, "mtime": fpath.stat().st_mtime}
            except OSError:
                result[rel] = {"size": 0, "mtime": 0}
    return result


def _get_workspace_dir(skill_dir, workspace_arg=None):
    """解析标准化工作区根目录。

    优先级：
    1. --workspace 参数显式指定
    2. 当前工作目录 (Path.cwd())

    返回工作区根路径（Path 对象）。
    工作区标准化路径为：<workspace>/standardization/<skill_name>/
    """
    if workspace_arg:
        ws = Path(workspace_arg).resolve()
    else:
        ws = Path.cwd()
    return ws


def _get_standardization_dir(skill_dir, workspace_arg=None):
    """获取标准化产出物根目录：<workspace>/standardization/<skill_name>/"""
    ws = _get_workspace_dir(skill_dir, workspace_arg)
    return ws / "standardization" / skill_dir.name


def _create_backup(skill_dir, operation, workspace_arg=None):
    """创建时间戳备份到标准化工作区（铁律4：持久化数据 → data/）。

    备份路径：<workspace>/standardization/<skill_name>/data/<skill_name>_bak_<op>_<timestamp>/
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{skill_dir.name}_bak_{operation}_{timestamp}"
    std_dir = _get_standardization_dir(skill_dir, workspace_arg)
    backup_base = std_dir / "data"
    backup_base.mkdir(parents=True, exist_ok=True)
    backup_path = backup_base / backup_name

    if backup_path.exists():
        shutil.rmtree(backup_path)
    shutil.copytree(str(skill_dir), str(backup_path))

    # 排除 __pycache__ 以减小备份体积
    for pcp in backup_path.rglob("__pycache__"):
        shutil.rmtree(pcp, ignore_errors=True)

    return backup_path


def _save_report(skill_dir, operation, report_text, workspace_arg=None):
    """保存标准化报告到工作区（铁律4：生成产物 → outputs/）。

    报告路径：<workspace>/standardization/<skill_name>/outputs/<skill_name>_<op>_<timestamp>.txt
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"{skill_dir.name}_{operation}_{timestamp}.txt"
    std_dir = _get_standardization_dir(skill_dir, workspace_arg)
    report_base = std_dir / "outputs"
    report_base.mkdir(parents=True, exist_ok=True)
    report_path = report_base / report_name
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def _write_json(filepath, data):
    """写入 JSON 文件（带缩进）"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _print_refactor_plan(skill_dir, all_files, loose_files):
    """输出 dry-run 重构计划"""
    print(f"\n  📋 重构计划:")
    moves = []
    keeps = []

    for rel_path in sorted(all_files.keys()):
        if rel_path in ("SKILL.md", "_meta.json"):
            keeps.append((rel_path, "standard root file"))
        elif rel_path == "_skillhub_meta.json":
            keeps.append((rel_path, "legacy meta (keep)"))
        elif "__pycache__" in rel_path:
            keeps.append((rel_path, "cache (skip)"))
        elif "/" not in rel_path:  # 根目录散落文件
            ext = Path(rel_path).suffix.lower()
            if ext in (".py", ".sh", ".json", ".txt", ".yaml", ".yml"):
                target = "scripts/" + rel_path
                moves.append((rel_path, target))
            elif ext == ".md":
                target = "references/" + rel_path
                moves.append((rel_path, target))
            elif ext in (".png", ".jpg", ".gif", ".svg"):
                target = "assets/" + rel_path
                moves.append((rel_path, target))
            else:
                keeps.append((rel_path, f"unknown type ({ext})"))

    if moves:
        print(f"\n  将要移动的文件 ({len(moves)}):")
        for src, dst in moves:
            print(f"    {src:<30} → {dst}")

    if keeps:
        print(f"\n  保持在原位的文件 ({len(keeps)}):")
        for src, reason in keeps:
            print(f"    {src:<30}   ({reason})")


# ═══════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Skill 标准化构建器 — create/update/refactor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s create my-skill --desc "我的技能" --tags test,tool
  %(prog)s update ./my-skill --fix
  %(prog)s update ./my-skill --backup --workspace /path/to/project
  %(prog)s refactor ./old-skill --dry-run
  %(prog)s refactor ./old-skill --backup --workspace /path/to/project
""",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # create 子命令
    p_create = subparsers.add_parser("create", help="从模板创建新 skill")
    p_create.add_argument("name", help="Skill 名称（将用作目录名和 name 字段）")
    p_create.add_argument("--desc", "-d", default="", help="技能描述")
    p_create.add_argument("--dir", default=None, help="父目录（默认当前目录）")
    p_create.add_argument("--tags", nargs="*", default=[], help="标签列表")

    # update 子命令
    p_update = subparsers.add_parser("update", help="增量规范化检查/修复已有 skill")
    p_update.add_argument("skill_dir", help="Skill 目录路径")
    p_update.add_argument("--fix", action="store_true", help="自动修复可修复的问题")
    p_update.add_argument("--backup", action="store_true", help="修改前自动备份")
    p_update.add_argument("--workspace", "-w", default=None, help="工作区根目录（默认当前目录），产出物将存至 <workspace>/standardization/<skill>/")

    # refactor 子命令
    p_refactor = subparsers.add_parser("refactor", help="整体改造非标 skill 到标准结构")
    p_refactor.add_argument("skill_dir", help="要改造的 Skill 目录路径")
    p_refactor.add_argument("--no-backup", action="store_true", help="不创建备份（不推荐）")
    p_refactor.add_argument("--dry-run", action="store_true", help="仅输出计划不执行")
    p_refactor.add_argument("--workspace", "-w", default=None, help="工作区根目录（默认当前目录），产出物将存至 <workspace>/standardization/<skill>/")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "create":
        cmd_create(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "refactor":
        cmd_refactor(args)


if __name__ == "__main__":
    main()
