#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit.py — SKILL.md 规范化审查工具 (v2.12.2)
集成到 git-sync 流程，在同步前自动检查 SKILL.md 合规性。

基于 SKILL.md 标准化规范草案 v0.1 的 R-01~R-12 规则。
支持独立运行（CLI）和被 git-sync.sh 调用（--json 模式）。

用法:
    python skill_audit.py audit <skill_dir> [--json] [--manifest-version VER]
    python skill_audit.py audit-all <skills_dir> [--manifest FILE] [--json]
    python skill_audit.py rules                          # 列出所有规则
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path

# ── 规则定义 (R-01 ~ R-12) ──────────────────────────────────────

RULES = [
    {
        "id": "R-01",
        "name": "Frontmatter 存在性",
        "severity": "ERROR",
        "check": "存在 YAML frontmatter（--- 包裹）",
        "method": "regex_frontmatter_exists",
    },
    {
        "id": "R-02",
        "name": "name 字段",
        "severity": "ERROR",
        "check": "frontmatter 含 name 字段",
        "method": "yaml_has_name",
    },
    {
        "id": "R-03",
        "name": "version 字段 (SemVer)",
        "severity": "ERROR",
        "check": "frontmatter 含 version 字段且符合 SemVer",
        "method": "yaml_has_semver_version",
    },
    {
        "id": "R-04",
        "name": "description 字段",
        "severity": "ERROR",
        "check": "frontmatter 含 description 字段",
        "method": "yaml_has_description",
    },
    {
        "id": "R-05",
        "name": "name 与目录名一致",
        "severity": "WARN",
        "check": "frontmatter name 与目录名一致",
        "method": "name_matches_dirname",
    },
    {
        "id": "R-06",
        "name": "正文含一级标题",
        "severity": "WARN",
        "check": "正文含 # 开头的一级标题",
        "method": "body_has_h1",
    },
    {
        "id": "R-07",
        "name": "触发条件章节",
        "severity": "WARN",
        "check": "正文含 ## 触发条件 或同义章节标题",
        "method": "body_has_trigger_section",
    },
    {
        "id": "R-08",
        "name": "核心能力章节",
        "severity": "WARN",
        "check": "正文含核心功能/能力/概述章节",
        "method": "body_has_core_section",
    },
    {
        "id": "R-09",
        "name": "工作流程/使用方式章节",
        "severity": "WARN",
        "check": "正文含工作流/使用方式/Workflow 章节",
        "method": "body_has_workflow_section",
    },
    {
        "id": "R-10",
        "name": "version 与 manifest 一致",
        "severity": "WARN",
        "check": "SKILL.md 中 version 与 manifest.json 记录一致",
        "method": "version_matches_manifest",
    },
    {
        "id": "R-11",
        "name": "产出物路径规范性",
        "severity": "WARN",
        "check": "scripts/ + 根目录 + 非标子目录 产出路径规范 + 全目录交叉引用追踪（铁律4：skills/.standardization/<skill>/）",
        "method": "check_artifact_paths",
    },
    {
        "id": "R-12",
        "name": "外部数据目录规范性",
        "severity": "WARN",
        "check": "scripts/ 中外部数据目录（DATA_DIR等）路径符合 skills/.standardization/<skill-name>/ 约定（与铁律4同一目录，非框架绑定），_meta.json 含 data_dir 字段且一致",
        "method": "check_external_data_dir",
    },
]

# 同义章节关键词映射
TRIGGER_KEYWORDS = ["触发条件", "触发场景", "适用场景", "触发"]
CORE_KEYWORDS = ["核心功能", "核心能力", "概述", "核心概念", "Overview", "技能概述"]
WORKFLOW_KEYWORDS = ["工作流程", "使用方式", "Workflow", "完整执行流程", "核心指令", "完整工作流"]

# R-11: 产出物路径检测 — 违规模式关键词（长名在前防止部分匹配）
ARTIFACT_DIR_NAMES = [
    "outputs", "output", "artifacts", "results", "exports",
    "reports", "report", "backups", "backup", "generated",
    "dumps", "dump", "build", "dist", "logs", "log",
    "data", "cache", "temp", "tmp", "out",
]

# ─────────── R-11 产出物全面定义（v2.7.0 扩展）───────────

# 已知标准目录（非产出物 — 属于技能本身结构的一部分）
_KNOWN_STANDARD_DIRS = {
    "scripts",      # 脚本代码
    "references",   # 参考文档
    "assets",       # 静态资源（图标、图片等技能自身资源）
    "__pycache__",  # Python 编译缓存
    ".git",         # Git 版本控制
}

# 产出物目录名 → 产出物分类 映射
# key: 目录名（小写），value: (分类, 描述)
_ARTIFACT_DIR_CLASSIFY = {
    # data 类 — 持久化/结构化数据
    "data":      ("data", "持久化数据目录"),
    "database":  ("data", "数据库目录"),
    "db":        ("data", "数据库目录"),
    "storage":   ("data", "存储目录"),
    "backup":    ("data", "备份目录"),
    "backups":   ("data", "备份目录"),
    "dump":      ("data", "数据转储目录"),
    "dumps":     ("data", "数据转储目录"),
    # cache 类 — 缓存/临时计算
    "cache":     ("cache", "缓存目录"),
    "caches":    ("cache", "缓存目录"),
    ".cache":    ("cache", "隐藏缓存目录"),
    "temp_cache": ("cache", "临时缓存目录"),
    # outputs 类 — 输出/生成产物
    "outputs":   ("outputs", "输出产物目录"),
    "output":    ("outputs", "输出产物目录"),
    "out":       ("outputs", "输出产物目录"),
    "results":   ("outputs", "结果目录"),
    "result":    ("outputs", "结果目录"),
    "exports":   ("outputs", "导出目录"),
    "export":    ("outputs", "导出目录"),
    "reports":   ("outputs", "报告目录"),
    "report":    ("outputs", "报告目录"),
    "generated": ("outputs", "生成产物目录"),
    "build":     ("outputs", "构建产物目录"),
    "dist":      ("outputs", "分发包目录"),
    "artifacts": ("outputs", "产出物目录"),
    # temp 类 — 临时/日志
    "temp":      ("temp", "临时文件目录"),
    "tmp":       ("temp", "临时文件目录"),
    ".tmp":      ("temp", "隐藏临时目录"),
    "logs":      ("temp", "日志目录"),
    "log":       ("temp", "日志目录"),
}

# 全面产出物文件扩展名（按分类）
_ARTIFACT_EXTS_COMPREHENSIVE = {
    # data — 数据文件
    ".json":    "data",   ".csv":   "data",   ".yaml":  "data",
    ".yml":     "data",   ".db":    "data",   ".sqlite": "data",
    ".sqlite3": "data",   ".pkl":   "data",   ".pickle": "data",
    ".parquet": "data",   ".feather": "data", ".h5":    "data",
    ".hdf5":    "data",   ".npy":   "data",   ".npz":   "data",
    # outputs — 输出/展示文件
    ".html":    "outputs", ".pdf":  "outputs", ".png":  "outputs",
    ".jpg":     "outputs", ".jpeg": "outputs", ".svg":  "outputs",
    ".gif":     "outputs", ".ico":  "outputs", ".txt":  "outputs",
    ".log":     "outputs", ".ics":  "outputs", ".xlsx": "outputs",
    ".xls":     "outputs", ".pptx": "outputs", ".docx": "outputs",
    ".md":      "outputs",  # 非 SKILL.md / references 的 md 文件
    # temp — 临时/缓冲文件
    ".tmp":     "temp",   ".bak":   "temp",   ".swp":  "temp",
    ".lock":    "temp",   ".pid":   "temp",   ".cache": "temp",
    # config — 配置快照（仅根目录或非标准目录下才视为产出物）
    ".env":     "data",   ".cfg":   "data",   ".ini":  "data",
    ".toml":    "data",
}

# 根目录已知白名单文件（非产出物）
_KNOWN_ROOT_FILES = {"SKILL.md", "_meta.json", ".gitignore", ".gitkeep"}

# 旧版兼容：产出物扩展名集合（用于根目录文件扫描）
_ROOT_ARTIFACT_EXTS = set(_ARTIFACT_EXTS_COMPREHENSIVE.keys())

# 根目录文件 → 分类映射（旧版兼容）
_ROOT_EXT_CLASSIFY = _ARTIFACT_EXTS_COMPREHENSIVE.copy()

# ─────────── R-11 常量定义结束 ───────────

# 构建产出目录名的正则 alternation（用于 scripts/ 正则扫描）
_ARTIFACT_DIR_PATTERN = "|".join(ARTIFACT_DIR_NAMES)

ARTIFACT_WRITE_PATTERNS = [
    # Path(__file__).parent / "data_dir" — 产出到脚本同目录
    re.compile(rf'__file__\s*\)\s*\.\s*parent\s*/\s*"({_ARTIFACT_DIR_PATTERN})"'),
    re.compile(rf'os\.path\.dirname\s*\(\s*__file__\s*\)\s*,\s*"({_ARTIFACT_DIR_PATTERN})"'),
    re.compile(rf'os\.path\.join\s*\(\s*os\.path\.dirname\s*\(\s*__file__\s*\)\s*,\s*"({_ARTIFACT_DIR_PATTERN})"'),
    # open("output/report.html", "w") — 捕获完整路径（目录+文件名）
    re.compile(rf'open\s*\(\s*["\'](?:\./)?({_ARTIFACT_DIR_PATTERN}/[^"\']+)["\']\s*,\s*["\']w["\']'),
    # Path("output_dir").mkdir() — 创建产出目录
    re.compile(rf'Path\s*\(\s*["\']\.?({_ARTIFACT_DIR_PATTERN})["\']'),
    # with open("file.json", "w") — 直接写入 JSON/CSV 到工作目录
    re.compile(r'open\s*\(\s*["\']([^"\']+\.(json|csv|html|png|jpg|pdf|txt|ics))["\']\s*,\s*["\']w["\']'),
]

# [v2.11.0] 通用硬编码路径检测：匹配所有引号包裹的路径字符串
# 覆盖：~/.xxx/、/home/、/Users/、C:/Users/、D:/ 等绝对/用户路径
_HARDCODED_PATH_RE = re.compile(
    r'["\']'
    r"((?:~|/home/|/Users/|[A-Za-z]:[\/]Users|[A-Za-z]:[\/]home|[A-Za-z]:[\/])[^\"' \t]*?)"
    r'["\']'
)

# 排除的合法模式（.standardization/ 路径、模板占位符、URL、shell变量）
_PATH_EXCLUDE_RE = re.compile(
    r'^(?:\.standardization/|<[^>]+>|\{[^}]+\}|https?://|ftp://|file://|\$\{|\$\w+)$'
)
def _is_hardcoded_path(s):
    """判断字符串是否是硬编码路径（需要改为 skills/.standardization/ 结构）"""
    if not s or len(s) < 5:
        return False
    if _PATH_EXCLUDE_RE.search(s):
        return False
    # 含有 .standardization/ 的路径视为合法标准化路径
    if '.standardization/' in s.replace('\\', '/'):
        return False
    # 必须包含路径分隔符或 ~ 或盘符
    if '/' in s or '\\' in s or s.startswith('~'):
        return True
    return False


# ── 轻量 YAML 解析器（零依赖） ──────────────────────────────────

def parse_simple_yaml_frontmatter(text):
    """从 Markdown 文本中提取并解析 YAML frontmatter。
    返回 (dict, body_text) 或 (None, text) 如果没有 frontmatter。"""
    if not text.startswith("---"):
        return None, text

    lines = text.split("\n", 1)
    rest = lines[1] if len(lines) > 1 else ""

    end_idx = rest.find("\n---")
    if end_idx == -1:
        return None, text

    fm_text = rest[:end_idx]
    body = rest[end_idx + 4:]

    result = {}
    current_key = None

    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if stripped.startswith("- ") and current_key:
            arr_key = current_key
            if arr_key not in result or not isinstance(result.get(arr_key), list):
                existing = result.get(arr_key, "")
                if isinstance(existing, str) and existing:
                    result[arr_key] = [existing]
                else:
                    result[arr_key] = []
            result[arr_key].append(stripped[2:].strip().strip("'\""))
            continue

        colon_idx = stripped.find(":")
        if colon_idx > 0:
            key = stripped[:colon_idx].strip()
            val = stripped[colon_idx + 1:].strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if inner:
                    result[key] = [item.strip().strip("'\"") for item in inner.split(",")]
                else:
                    result[key] = []
            elif val:
                result[key] = val
            current_key = key

    return result, body


# ── 审查方法实现 ────────────────────────────────────────────────

def regex_frontmatter_exists(filepath, content, fm, body, **kw):
    passed = fm is not None
    return {"passed": passed,
            "detail": "发现 YAML frontmatter" if passed else "缺少 YAML frontmatter"}


def yaml_has_name(filepath, content, fm, body, **kw):
    has_name = fm is not None and "name" in fm
    return {"passed": has_name,
            "detail": f"name = {fm['name']}" if has_name else "缺少 name 字段"}


def yaml_has_semver_version(filepath, content, fm, body, **kw):
    has_ver = fm is not None and "version" in fm
    if not has_ver:
        return {"passed": False, "detail": "缺少 version 字段"}
    ver = str(fm["version"])
    semver_ok = bool(re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$', ver))
    return {"passed": semver_ok,
            "detail": f"version = {ver}" + (" ✓" if semver_ok else " ✗ 不符合 SemVer")}


def yaml_has_description(filepath, content, fm, body, **kw):
    has_desc = fm is not None and "description" in fm
    dv = str(fm.get("description", ""))[:60] if has_desc else ""
    return {"passed": has_desc,
            "detail": f"description = \"{dv}\"" if has_desc else "缺少 description 字段"}


def name_matches_dirname(filepath, content, fm, body, dirname=None, **kw):
    if fm is None or "name" not in fm:
        return {"passed": False, "detail": "无法检查：无 frontmatter/name", "skip": True}
    if not dirname:
        return {"passed": True, "detail": "跳过：未提供目录名", "skip": True}
    matched = fm["name"] == dirname
    return {"passed": matched,
            "detail": f"name({fm['name']}) {'==' if matched else '!='} dirname({dirname})"}


def body_has_h1(filepath, content, fm, body, **kw):
    m = re.search(r'^# ', body, re.MULTILINE)
    return {"passed": m is not None,
            "detail": f"发现一级标题: {m.group(0).strip()}" if m else "未找到一级标题 (# )"}


def _section_exists(body, keywords, label):
    """通用：检查是否包含任一关键词的 ## 级标题"""
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("## "):
            title = s[3:].strip()
            for kw in keywords:
                if kw.lower() in title.lower():
                    return True, f"发现章节: {title}"
    return False, f"未找到 [{label}] 章节（同义词: {', '.join(keywords)}）"


def body_has_trigger_section(filepath, content, fm, body, **kw):
    ok, detail = _section_exists(body, TRIGGER_KEYWORDS, "触发条件")
    return {"passed": ok, "detail": detail}


def body_has_core_section(filepath, content, fm, body, **kw):
    ok, detail = _section_exists(body, CORE_KEYWORDS, "核心能力")
    return {"passed": ok, "detail": detail}


def body_has_workflow_section(filepath, content, fm, body, **kw):
    ok, detail = _section_exists(body, WORKFLOW_KEYWORDS, "工作流程")
    return {"passed": ok, "detail": detail}


def version_matches_manifest(filepath, content, fm, body, manifest_version=None, **kw):
    if manifest_version is None:
        return {"passed": True, "detail": "跳过：未提供 manifest 版本号", "skip": True}
    if fm is None or "version" not in fm:
        return {"passed": False, "detail": "无 frontmatter/version，无法比对", "skip": True}
    matched = str(fm["version"]) == str(manifest_version)
    return {"passed": matched,
            "detail": f"SKILL.md({fm['version']}) {'==' if matched else '!='} manifest({manifest_version})"}


def check_artifact_paths(filepath, content, fm, body, skill_dir=None, **kw):
    """R-11: 全面产出物路径检测（铁律4）。
    
    四阶段扫描：
    1. scripts/ 扫描：检测脚本中的硬编码产出路径（写入操作）
    2. 根目录文件扫描：检测根目录中非 SKILL.md/_meta.json 的数据文件
    3. 非标准子目录扫描：检测根目录下明显是产出物的文件夹（data/cache/outputs/等）
    4. 交叉引用追踪：反向搜索关联文件
    """
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}
    
    violations = []  # list of {source, path_literal, suggestion}
    script_exts = {".py", ".sh", ".bat", ".ps1"}
    
    # ── 1. scripts/ 扫描 ──
    scripts_dir = os.path.join(skill_dir, "scripts")
    if os.path.isdir(scripts_dir):
        for fname in sorted(os.listdir(scripts_dir)):
            fpath = os.path.join(scripts_dir, fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in script_exts or not os.path.isfile(fpath):
                continue
            
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    script_lines = f.readlines()
            except Exception:
                continue
            
            rel_path = os.path.join("scripts", fname)
            
            if ext == ".py":
                _check_python_artifact_paths_v2(rel_path, script_lines, violations)
            elif ext in (".sh", ".bat", ".ps1"):
                _check_shell_artifact_paths_v2(rel_path, script_lines, violations)
    
    # ── 2. 根目录文件扫描 ──
    _check_root_artifact_files(skill_dir, violations)
    
    # ── 3. 非标准子目录扫描（v2.7.0 新增）──
    _check_artifact_directories(skill_dir, violations)
    
    # ── 4. 交叉引用追踪 ──
    if violations:
        _trace_cross_references(skill_dir, violations)

    # ── 5. [v2.10.0] 标准化路径磁盘验证 ──
    _verify_standardization_paths(skill_dir, violations)

    if violations:
        detail_lines = [f"发现 {len(violations)} 处产出物路径违规："]
        for v in violations:
            line = f"  {v['source']}  产出 \"{v['path_literal']}\" — 应迁至 {v['suggestion']}"
            if v.get("cross_refs"):
                line += f"\n    ⚠️ 关联引用 ({len(v['cross_refs'])}处): {', '.join(v['cross_refs'])}"
            detail_lines.append(line)
        return {
            "passed": False,
            "detail": "\n".join(detail_lines),
            "violations": [{"source": v["source"], "path": v["path_literal"],
                           "suggestion": v["suggestion"], "cross_refs": v.get("cross_refs", [])}
                          for v in violations],
        }
    else:
        return {"passed": True, "detail": "未发现产出物路径违规（scripts/ + 根目录 + 子目录均通过）"}


def _check_root_artifact_files(skill_dir, violations):
    """根目录产出物文件检测：扫描根目录中非标准数据文件。
    
    根目录只应有 SKILL.md、_meta.json、.gitignore。
    其他数据文件（.json/.csv/.db 等）视为违反铁律4的产出物。
    """
    try:
        root_entries = os.listdir(skill_dir)
    except OSError:
        return
    
    for fname in sorted(root_entries):
        fpath = os.path.join(skill_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if fname in _KNOWN_ROOT_FILES:
            continue
        
        ext = os.path.splitext(fname)[1].lower()
        if ext not in _ROOT_ARTIFACT_EXTS:
            continue
        
        cat = _classify_artifact_by_ext(fname)
        
        violations.append({
            "source": f"ROOT/{fname}",
            "path_literal": fname,
            "suggestion": f"skills/.standardization/<skill>/{cat}/{fname}",
        })


def _check_artifact_directories(skill_dir, violations):
    """非标准子目录扫描：检测根目录下的产出物目录及其内容。
    
    策略：
    1. 列出根目录所有子目录
    2. 排除已知标准目录（scripts/references/assets/__pycache__/.git）
    3. 对疑似产出物目录（名称匹配 _ARTIFACT_DIR_CLASSIFY），递归扫描全部文件
    4. 也检查 scripts/ 和 references/ 下的非标准子目录
    """
    try:
        root_entries = sorted(os.listdir(skill_dir))
    except OSError:
        return
    
    for entry in root_entries:
        entry_path = os.path.join(skill_dir, entry)
        if not os.path.isdir(entry_path):
            continue
        if entry in _KNOWN_STANDARD_DIRS:
            continue
        if entry.startswith(".") and entry not in _ARTIFACT_DIR_CLASSIFY:
            # 跳过非产出物的隐藏目录（如 .vscode, .idea 等IDE配置）
            continue
        
        # 检查是否匹配产出物目录名
        classification = _ARTIFACT_DIR_CLASSIFY.get(entry.lower())
        if classification:
            cat, desc = classification
            _scan_dir_recursive(skill_dir, entry, entry_path, cat, violations)
        else:
            # 非标准目录名但仍需扫描：可能是自定义数据目录
            # 检查目录内容判断是否为产出物
            _scan_unknown_dir(skill_dir, entry, entry_path, violations)
    
    # 深度扫描：检查 scripts/ 和 references/ 下的非标准子目录
    for parent_dir_name in ("scripts", "references"):
        parent_path = os.path.join(skill_dir, parent_dir_name)
        if not os.path.isdir(parent_path):
            continue
        try:
            sub_entries = sorted(os.listdir(parent_path))
        except OSError:
            continue
        for sub in sub_entries:
            sub_path = os.path.join(parent_path, sub)
            if not os.path.isdir(sub_path):
                continue
            if sub in _KNOWN_STANDARD_DIRS:
                continue
            classification = _ARTIFACT_DIR_CLASSIFY.get(sub.lower())
            if classification:
                cat, _desc = classification
                rel_parent = f"{parent_dir_name}/{sub}"
                _scan_dir_recursive(skill_dir, rel_parent, sub_path, cat, violations)


def _scan_dir_recursive(skill_dir, rel_dir, dir_path, category, violations):
    """递归扫描一个产出物目录，列出其中所有文件作为违规。
    
    Args:
        skill_dir: 技能根目录（用于计算相对路径）
        rel_dir: 在技能中的相对路径（如 "data"、"scripts/output"）
        dir_path: 目录的绝对路径
        category: 产出物分类（data/cache/outputs/temp）
    """
    try:
        for root, dirs, files in os.walk(dir_path):
            # 排除 __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            
            for fname in sorted(files):
                # 跳过 .gitkeep 等占位文件
                if fname in (".gitkeep", ".gitignore"):
                    continue
                
                # 建议路径：仅用分类 + 文件名，避免路径冗余
                violations.append({
                    "source": f"DIR/{rel_dir}/{fname}",
                    "path_literal": f"{rel_dir}/{fname}",
                    "suggestion": f"skills/.standardization/<skill>/{category}/{fname}",
                })
    except OSError:
        return


def _scan_unknown_dir(skill_dir, entry, entry_path, violations):
    """扫描未知目录名 — 检查其内容判断是否为产出物目录。
    
    如果目录内包含产出物类型文件（匹配 _ARTIFACT_EXTS_COMPREHENSIVE），
    则推断为产出物目录并标记。
    """
    # 检查第一层内容
    try:
        entries = sorted(os.listdir(entry_path))
    except OSError:
        return
    
    artifact_files = []
    is_script_dir = False
    
    for sub in entries:
        sub_path = os.path.join(entry_path, sub)
        if os.path.isfile(sub_path):
            ext = os.path.splitext(sub)[1].lower()
            if ext in _ARTIFACT_EXTS_COMPREHENSIVE:
                artifact_files.append(sub)
            if ext in (".py", ".sh", ".bat", ".ps1"):
                is_script_dir = True
    
    if is_script_dir and not artifact_files:
        # 可能是代码目录（如 tools/），跳过
        return
    
    if artifact_files:
        # 推断为产出物目录
        cat = "outputs"  # 默认分类
        for sub in artifact_files:
            violations.append({
                "source": f"DIR/{entry}/{sub}",
                "path_literal": f"{entry}/{sub}",
                "suggestion": f"skills/.standardization/<skill>/{cat}/{sub}",
            })


def _classify_artifact_by_ext(filename):
    """根据文件名扩展名推断产出物分类（data/cache/outputs/temp）"""
    ext = os.path.splitext(filename)[1].lower()
    cat = _ROOT_EXT_CLASSIFY.get(ext, "outputs")
    if cat == "temp":
        cat = "outputs"  # temp 类文件在根目录默认归为 outputs
    return cat


def _extract_path_literal(line_text, matched_target):
    """从违规行中提取完整的路径字面量（引号内的内容）。
    
    优先返回包含 matched_target 的完整引号字符串，
    降级返回 matched_target 本身。
    """
    # 匹配所有引号字符串
    quoted = re.findall(r"""["']([^"']+)["']""", line_text)
    for q in quoted:
        if matched_target in q:
            # 保留相对路径前缀（./ 等）
            return q
    return matched_target


def _check_python_artifact_paths_v2(rel_path, script_lines, violations):
    """[v2.11.0] Check Python script for artifact path violations (including generic hardcoded paths)."""
    for i, line in enumerate(script_lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue
        
        # Original logic: check artifact write patterns (preserved)
        for pat in ARTIFACT_WRITE_PATTERNS:
            m = pat.search(stripped)
            if m:
                target = m.group(1)
                if ".standardization" in stripped.lower() or "standardization" in stripped.lower():
                    continue
                if '"r"' in stripped or "'r'" in stripped:
                    continue
                
                path_literal = _extract_path_literal(stripped, target)
                if "/" in target:
                    dir_part = target.split("/")[0]
                    cat = _classify_artifact(dir_part)
                    filename = target.split("/")[-1]
                    if "." in filename:
                        suggestion = f"skills/.standardization/<skill>/{cat}/{filename}"
                    else:
                        suggestion = f"skills/.standardization/<skill>/{cat}/{target}"
                elif "." in target:
                    cat = _classify_artifact(target)
                    suggestion = f"skills/.standardization/<skill>/{cat}/{target}"
                else:
                    cat = _classify_artifact(target)
                    suggestion = f"skills/.standardization/<skill>/{cat}/"
                
                violations.append({
                    "source": f"{rel_path}:{i}",
                    "path_literal": path_literal,
                    "suggestion": suggestion,
                })
                break

        # [v2.11.0 KEY FIX] Generic hardcoded path detection
        # Catches paths like ~/.workbuddy/git-sync/manifest.json
        for m in _HARDCODED_PATH_RE.finditer(stripped):
            # 排除 sys.path.insert/append 所在行（import 路径，非产出物）
            if "sys.path" in stripped:
                continue
            path_str = m.group(1)
            if not _is_hardcoded_path(path_str):
                continue
            if ".standardization" in path_str.lower() or "standardization" in path_str.lower():
                continue
            basename = os.path.basename(path_str.rstrip("/\\"))
            if basename and "." in basename:
                cat = _classify_artifact(basename)
                suggestion = f"skills/.standardization/<skill>/{cat}/{basename}"
            else:
                cat = "data"
                suggestion = f"skills/.standardization/<skill>/{cat}/"
            violations.append({
                "source": f"{rel_path}:{i}",
                "path_literal": path_str,
                "suggestion": suggestion,
            })

def _check_shell_artifact_paths_v2(rel_path, script_lines, violations):
    """[v2.11.0] Check Shell scripts for all hardcoded paths."""
    for i, line in enumerate(script_lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("::") or not stripped:
            continue
        
        # [v2.11.0 KEY FIX] Generic hardcoded path detection (primary method)
        for m in _HARDCODED_PATH_RE.finditer(stripped):
            path_str = m.group(1)
            if not _is_hardcoded_path(path_str):
                continue
            if ".standardization" in path_str.lower() or "standardization" in path_str.lower():
                continue
            basename = os.path.basename(path_str.rstrip("/\\"))
            if basename and "." in basename:
                cat = _classify_artifact(basename)
                suggestion = f"skills/.standardization/<skill>/{cat}/{basename}"
            else:
                cat = "data"
                suggestion = f"skills/.standardization/<skill>/{cat}/"
            violations.append({
                "source": f"{rel_path}:{i}",
                "path_literal": path_str,
                "suggestion": suggestion,
            })
        
        # Legacy artifact dir check (backward compatibility)
        m = re.search(rf'[>]+\s*["\']?\\.?({_ARTIFACT_DIR_PATTERN})/', stripped)
        if m and ".standardization" not in stripped.lower() and "standardization" not in stripped.lower():
            target = m.group(1)
            path_literal = _extract_path_literal(stripped, target) or f"{target}/"
            cat = _classify_artifact(target)
            violations.append({
                "source": f"{rel_path}:{i}",
                "path_literal": path_literal,
                "suggestion": f"skills/.standardization/<skill>/{cat}/",
            })

def _trace_cross_references(skill_dir, violations):
    """反向搜索整个 skill 目录，找出引用每个违规路径的关联文件。
    
    搜索范围：SKILL.md、references/*.md、_meta.json 等文本文件。
    排除 scripts/ 目录（已由违规检测覆盖）。
    
    结果原地写入每个 violation 的 cross_refs 字段。
    """
    # 收集所有需要搜索的 path_literal（去重）
    search_patterns = list(set(v["path_literal"] for v in violations))
    
    # 收集所有可搜索的文件
    text_exts = {".md", ".json", ".yaml", ".yml", ".txt", ".cfg", ".toml", ".ini", ".html"}
    searchable_files = []
    
    for root, dirs, files in os.walk(skill_dir):
        # 排除 __pycache__、.git、scripts
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        rel_root = os.path.relpath(root, skill_dir).replace("\\", "/")
        if rel_root == ".":
            rel_root = ""
        
        # 跳过 scripts/ 目录
        if rel_root.startswith("scripts") or rel_root == "scripts":
            continue
        
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in text_exts:
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.join(rel_root, fname).replace("\\", "/") if rel_root else fname
            searchable_files.append((rel, fpath))
    
    # 对每个 path_literal，在所有搜索文件中查找引用
    pattern_to_refs = {}  # path_literal → [fname:line, ...]
    
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
    
    # 回填到 violations
    for v in violations:
        refs = pattern_to_refs.get(v["path_literal"], [])
        # 排除自身：脚本引用自身行号 / 根目录文件自身
        refs = [r for r in refs if r != v["source"] and r != v["source"].replace("ROOT/", "")]
        if refs:
            v["cross_refs"] = refs


def _verify_standardization_paths(skill_dir, violations):
    """[v2.10.0] 验证脚本中声称的 skills/.standardization/ 路径在磁盘上真实存在。"""
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return

    skills_dir = _find_skills_dir(skill_dir)
    std_re = re.compile(r'\.standardization/([^"\')\s,。，；：！？、…—]+)')

    for fname in sorted(os.listdir(scripts_dir)):
        fpath = os.path.join(scripts_dir, fname)
        ext = os.path.splitext(fname)[1].lower()
        if ext not in (".py", ".sh", ".bat", ".ps1"):
            continue
        if not os.path.isfile(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            continue

        rel = os.path.join("scripts", fname)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            matches = std_re.findall(stripped)
            for matched_path in matches:
                # 跳过模板占位符：<skill>, {name}, {cat}, ([^ 等
                if "<" in matched_path or "{" in matched_path or matched_path.startswith("([^"):
                    continue
                full_rel = ".standardization/" + matched_path
                dir_part = "/".join(full_rel.split("/")[:-1]) if "." in full_rel.split("/")[-1] else full_rel
                abs_dir = os.path.join(skills_dir, dir_part.replace("/", os.sep))
                if not os.path.exists(abs_dir):
                    violations.append({
                        "source": rel + ":" + str(i),
                        "path_literal": full_rel,
                        "suggestion": "directory missing: " + abs_dir + ", please create it",
                    })


def _classify_artifact(dirname):
    """根据目录名推断产出物分类（data/cache/outputs/temp）"""
    d = dirname.lower().rstrip("s")
    # 优先使用 _ARTIFACT_DIR_CLASSIFY
    if d in _ARTIFACT_DIR_CLASSIFY:
        return _ARTIFACT_DIR_CLASSIFY[d][0]
    mapping = {
        "data": "data", "backup": "data", "dump": "data",
        "cache": "cache", "tmp": "temp", "temp": "temp",
        "output": "outputs", "out": "outputs", "result": "outputs",
        "export": "outputs", "report": "outputs", "log": "outputs",
        "build": "outputs", "dist": "outputs", "generated": "outputs",
        "artifact": "outputs",
    }
    return mapping.get(d, "outputs")


# 方法分派表
def check_external_data_dir(filepath, content, fm, body, skill_dir=None, **kw):
    """R-12: External data directory path validation.
    
    1. scan scripts/ for data dir variable assignments (generalized detection)
    2. check paths conform to skills/.standardization/<skill-name>/ convention (same as R-11)
    3. check _meta.json declares data_dir field
    4. check _meta.json data_dir matches code path
    5. [v2.10.0] disk existence: verify skills/.standardization/<skill>/data/ actually exists
    """
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "skip: cannot determine skill dir", "skip": True}

    dirname = os.path.basename(os.path.abspath(skill_dir))
    violations = []
    expected_pattern = ".standardization/" + dirname + "/"

    # 1. scan scripts/ for data dir definitions (generalized variable detection)
    scripts_dir = os.path.join(skill_dir, "scripts")
    data_dir_vars = []
    _DATA_VAR_RE = re.compile(
        r'^([A-Za-z_]*?(?:DATA|STORAGE|DB|CACHE|CONFIG)[A-Za-z_]*(?:_DIR|_PATH))\s*=\s*(.+)$'
    )

    if os.path.isdir(scripts_dir):
        for fname in sorted(os.listdir(scripts_dir)):
            fpath = os.path.join(scripts_dir, fname)
            if not os.path.isfile(fpath):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in (".py", ".sh", ".bat", ".ps1"):
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for lineno, line in enumerate(f, 1):
                        stripped = line.strip()
                        m = _DATA_VAR_RE.match(stripped)
                        if m:
                            val = m.group(2).strip()
                            path_val = _extract_path_value(val)
                            data_dir_vars.append((
                                os.path.join("scripts", fname),
                                m.group(1),
                                path_val,
                                lineno
                            ))
            except Exception:
                continue

    # 2. check paths conform to standardization/<skill-name>/ convention (same as R-11)
    # [v2.10.1] Normalize both sides to handle cross-platform path separator differences
    expected_norm = os.path.normpath(".standardization/" + dirname + "/data/").lower()
    for rel_file, var_name, path_val, lineno in data_dir_vars:
        if not path_val:
            continue
        norm = os.path.normpath(path_val).lower()
        if expected_norm not in norm:
            violations.append({
                "source": rel_file + ":" + str(lineno),
                "var_name": var_name,
                "path_value": path_val,
                "expected": ".standardization/" + dirname + "/data/",
                "detail": var_name + "=" + path_val + " violates skills/.standardization/<skill>/ convention (same as R-11)",
            })

    # 3. check _meta.json has data_dir field
    meta_file = os.path.join(skill_dir, "_meta.json")
    meta_has_data_dir = False
    meta_data_dir = None
    if os.path.isfile(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if "data_dir" in meta:
                meta_has_data_dir = True
                meta_data_dir = meta["data_dir"]
        except Exception:
            pass

    if data_dir_vars and not meta_has_data_dir:
        violations.append({
            "source": "_meta.json",
            "var_name": "data_dir",
            "path_value": "(missing)",
            "expected": "should add data_dir field",
            "detail": "_meta.json missing data_dir field (scripts/ defines data dir variable)",
        })

    # 4. check _meta.json data_dir matches code path
    # [v2.12.2] Resolve both paths to absolute for fair comparison; strip trailing sep
    if meta_has_data_dir and data_dir_vars:
        skills_root = _find_skills_dir(skill_dir)
        meta_raw = os.path.join(skills_root, str(meta_data_dir))
        meta_abs = os.path.normpath(meta_raw).rstrip(os.sep).lower()
        for _, _, path_val, _ in data_dir_vars:
            if path_val:
                code_raw = os.path.join(skills_root, str(path_val))
                code_abs = os.path.normpath(code_raw).rstrip(os.sep).lower()
                if code_abs != meta_abs:
                    violations.append({
                        "source": "_meta.json vs " + data_dir_vars[0][0],
                        "var_name": "data_dir",
                        "path_value": meta_data_dir,
                        "expected": path_val,
                        "detail": "_meta.json data_dir=" + str(meta_data_dir) + " != code " + data_dir_vars[0][1] + "=" + path_val,
                    })
                    break

    # 5. [v2.10.0] disk existence: verify skills/.standardization/<skill>/data/ actually exists
    # 仅在 skill 实际使用外部数据时检查（有 data_dir 变量 或 _meta.json 声明了 data_dir）
    uses_external_data = bool(data_dir_vars) or meta_has_data_dir
    if uses_external_data:
        skills_dir = _find_skills_dir(skill_dir)
        expected_disk_path = os.path.join(skills_dir, ".standardization", dirname, "data")
        if not os.path.isdir(expected_disk_path):
            violations.append({
                "source": "DISK",
                "var_name": "disk",
                "path_value": expected_disk_path,
                "expected": "directory should exist: " + expected_disk_path,
                "detail": "标准化数据目录不存在: " + expected_disk_path,
            })

    # 6. [v2.12.2] references/*.md 中的数据目录路径检查
    # 检测 references/ 目录下 md 文件中出现的硬编码数据目录路径
    # （不含 .standardization/ 的路径都应报违规）
    refs_dir = os.path.join(skill_dir, "references")
    if os.path.isdir(refs_dir):
        _REFS_PATH_RE = re.compile(
            r'(?:~|/home/\w+|/Users/\w+|C:\\Users\\\w+|/c/Users/\w+)?'
            r'(?:/|\\)(?:\.?workbuddy(?:/|\\)(?:skills(?:/|\\))?)?'
            r'([\w.-]+(?:/|\\)data(?:/|\\))'
        )
        for fname in sorted(os.listdir(refs_dir)):
            fpath = os.path.join(refs_dir, fname)
            if not os.path.isfile(fpath):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext != ".md":
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    for lineno, line in enumerate(f, 1):
                        stripped = line.strip()
                        # 跳过标题行、注释行、空行
                        if not stripped or stripped.startswith('#') or stripped.startswith('<!--'):
                            continue
                        # 跳过含 .standardization/ 的行（合规路径）
                        if '.standardization/' in stripped:
                            continue
                        for m in _REFS_PATH_RE.finditer(stripped):
                            matched_path = m.group(1)  # e.g. "semantic-split/data/"
                            # 提取 skill name
                            path_parts = matched_path.replace('\\', '/').rstrip('/').split('/')
                            if len(path_parts) >= 2 and path_parts[-1] == 'data':
                                skill_name_in_path = path_parts[-2]
                                violations.append({
                                    "source": f"references/{fname}:{lineno}",
                                    "var_name": "path_text",
                                    "path_value": matched_path,
                                    "expected": f".standardization/{dirname}/data/",
                                    "detail": f"references/{fname}:{lineno} contains non-standard data path '{matched_path}' — should use .standardization/{dirname}/data/ (铁律4)",
                                })
            except Exception:
                continue

    if violations:
        detail_lines = ["Found " + str(len(violations)) + " external data dir violations:"]
        for v in violations:
            detail_lines.append("  " + v["source"] + ": " + v["detail"])
            detail_lines.append("    suggestion: " + v["expected"])
        return {
            "passed": False,
            "detail": "\n".join(detail_lines),
            "violations": violations,
        }
    else:
        if data_dir_vars:
            return {"passed": True, "detail": "External data dir paths conform to standard, _meta.json data_dir declared and consistent"}
        else:
            return {"passed": True, "detail": "No external data dir variables defined in scripts/ (nothing to check)", "skip": True}


def _extract_path_value(val_expr):
    """Extract path string from Python assignment expression."""
    # [v2.11.1] SKILL_DIR.parent / ".standardization" / ... pattern
    if "SKILL_DIR" in val_expr and ".standardization" in val_expr:
        frags = re.findall(r"""['"]([^'"]*)['"]""", val_expr)
        if frags:
            return "/".join(frags)
    if "Path.home()" in val_expr or "Path(" in val_expr:
        frags = re.findall(r"""['"]([^'"]*)['"]""", val_expr)
        if not frags:
            return val_expr
        if "Path.home()" in val_expr:
            return str(Path.home() / "/".join(frags))
        return "/".join(frags)
    m = re.match(r"""^['"](.+?)['"]$""", val_expr.strip())
    if m:
        return m.group(1)
    return val_expr.strip()


def _find_skills_dir(skill_dir):
    """向上查找 skills 目录（最多 5 层）。
    
    从 skill 目录向上遍历，找到名为 'skills' 的父目录。
    兜底返回 skill_dir 的父目录。
    """
    p = os.path.abspath(skill_dir)
    for _ in range(5):
        if os.path.basename(p) == "skills" and os.path.isdir(p):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return os.path.dirname(os.path.abspath(skill_dir))



METHOD_MAP = {
    "check_external_data_dir": check_external_data_dir,
    "regex_frontmatter_exists": regex_frontmatter_exists,
    "yaml_has_name": yaml_has_name,
    "yaml_has_semver_version": yaml_has_semver_version,
    "yaml_has_description": yaml_has_description,
    "name_matches_dirname": name_matches_dirname,
    "body_has_h1": body_has_h1,
    "body_has_trigger_section": body_has_trigger_section,
    "body_has_core_section": body_has_core_section,
    "body_has_workflow_section": body_has_workflow_section,
    "version_matches_manifest": version_matches_manifest,
    "check_artifact_paths": check_artifact_paths,
}


def audit_skill(skill_dir, manifest_version=None):
    """审查单个 skill 目录中的 SKILL.md。

    Args:
        skill_dir: skill 目录路径
        manifest_version: manifest.json 中记录的版本号（用于 R-10）

    Returns:
        dict: 完整审查结果
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    dirname = os.path.basename(os.path.normpath(skill_dir))

    # 检查文件是否存在
    if not os.path.isfile(skill_md):
        return {
            "skill": dirname,
            "path": skill_dir,
            "error": "SKILL.md 文件不存在",
            "results": [],
            "summary": {"total": 0, "pass": 0, "fail": 0, "skip": 0, "errors": 0, "warns": 0},
            "verdict": "ERROR — SKILL.md 不存在",
        }

    with open(skill_md, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    fm, body = parse_simple_yaml_frontmatter(content)

    results = []
    error_count = 0
    warn_count = 0
    pass_count = 0
    skip_count = 0

    for rule in RULES:
        method_fn = METHOD_MAP.get(rule["method"])
        if not method_fn:
            continue

        result = method_fn(
            filepath=skill_md,
            content=content,
            fm=fm,
            body=body,
            dirname=dirname,
            skill_dir=skill_dir,
            manifest_version=manifest_version,
        )
        passed = result.get("passed", False)
        skipped = result.get("skip", False)

        entry = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "severity": rule["severity"],
            "passed": passed,
            "skipped": skipped,
            "detail": result.get("detail", ""),
        }
        results.append(entry)

        if skipped:
            skip_count += 1
        elif passed:
            pass_count += 1
        elif rule["severity"] == "ERROR":
            error_count += 1
        else:
            warn_count += 1

    fail_count = error_count + warn_count
    total = len(results)

    # 综合判定
    if error_count > 0:
        verdict = f"FAIL ({error_count} ERROR{', ' + str(warn_count) + ' WARN' if warn_count > 0 else ''})"
    elif warn_count > 0:
        verdict = f"WARN ({warn_count} WARN)"
    else:
        verdict = "PASS"

    return {
        "skill": dirname,
        "path": skill_dir,
        "results": results,
        "summary": {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "skip": skip_count,
            "errors": error_count,
            "warns": warn_count,
        },
        "verdict": verdict,
    }


def format_report(audit_result, verbose=True):
    """格式化人类可读的审查报告"""
    lines = []
    r = audit_result

    if "error" in r:
        lines.append(f"❌ {r['skill']}: {r['error']}")
        return "\n".join(lines)

    lines.append(f"{'='*55}")
    lines.append(f"  审查结果: {r['skill']} — {r['verdict']}")
    lines.append(f"{'='*55}")

    s = r["summary"]
    lines.append(f"  总计: {s['total']} | 通过: {s['pass']} | 失败: {s['fail']} | 跳过: {s['skip']}")

    if verbose:
        lines.append("")
        lines.append(f"{'规则ID':<8} {'严重度':<7} {'状态':<6} 详情")
        lines.append(f"{'-'*8}-{'-'*7}-{'-'*6}-{'-'*30}")
        for res in r["results"]:
            status = "✅" if res["passed"] else ("⏭️" if res["skipped"] else ("🔴" if res["severity"]=="ERROR" else "🟡"))
            sev = res["severity"][0] if res["severity"] else "?"
            lines.append(f"{res['rule_id']:<8} {sev:<7} {status:<6} {res['detail']}")

    return "\n".join(lines)


# ── CLI 命令处理 ─────────────────────────────────────────────────

def cmd_rules():
    """列出所有审查规则"""
    print(f"\n{'ID':<8} {'严重度':<8} 名称  检查内容")
    print("-" * 65)
    for rule in RULES:
        sev_mark = "🔴" if rule["severity"] == "ERROR" else "🟡"
        print(f"  {rule['id']:<6} {sev_mark} {rule['severity']:<6} {rule['name']: <20} {rule['check']}")
    print(f"\n共 {len(RULES)} 条规则")


def cmd_audit(args):
    """审查单个 skill 目录"""
    skill_dir = args.skill_dir
    if not os.path.isdir(skill_dir):
        print(f"❌ 目录不存在: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    result = audit_skill(skill_dir, manifest_version=args.manifest_version)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))

    # 退出码：纯警告模式 — 始终返回 0，不阻断调用方流程
    # ERROR 和 WARN 仅在报告中体现严重度差异，不影响退出码
    # 调用方（如 git-sync.sh）可根据 summary.errors/summary.warns 自行决定行为
    # sys.exit(0)  # 显式注释：默认退出码即为 0，无需显式调用


def cmd_audit_all(args):
    """批量审查 skills 目录下所有 skill"""
    skills_dir = args.skills_dir
    manifest_file = args.manifest

    # 读取 manifest 获取版本号映射
    version_map = {}
    if manifest_file and os.path.isfile(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
            items = mdata.get("repos", {}).get("workbuddy-skills", {}).get("items", {})
            for name, info in items.items():
                if isinstance(info, dict) and "version" in info:
                    version_map[name] = info["version"]
        except Exception as e:
            print(f"⚠️  读取 manifest 失败: {e}", file=sys.stderr)

    # 发现所有 skill 目录
    entries = []
    for entry in sorted(os.listdir(skills_dir)):
        full_path = os.path.join(skills_dir, entry)
        if os.path.isdir(full_path) and os.path.isfile(os.path.join(full_path, "SKILL.md")):
            entries.append((entry, full_path))

    all_results = []
    total_errors = 0
    total_warns = 0

    for dirname, dirpath in entries:
        mv = version_map.get(dirname)
        result = audit_skill(dirpath, manifest_version=mv)
        all_results.append(result)
        total_errors += result["summary"]["errors"]
        total_warns += result["summary"]["warns"]

    if args.json:
        print(json.dumps({
            "audited_count": len(all_results),
            "total_errors": total_errors,
            "total_warns": total_warns,
            "results": all_results,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  批量审查报告 — 共 {len(entries)} 个 skill")
        print(f"  汇总: {sum(r['summary']['pass'] for r in all_results)} PASS / "
              f"{total_errors} ERROR / {total_warns} WARN")
        print(f"{'='*60}")

        for r in all_results:
            print(format_result := format_report(r, verbose=False))
            print()

        # 仅汇总行
        print(f"\n{'='*60}")
        print("  详细逐项结果:")
        print(f"{'='*60}")
        for r in all_results:
            if "error" not in r:
                print(format_report(r, verbose=True))
                print()


def main():
    parser = argparse.ArgumentParser(
        description="SKILL.md 规范化审查工具 (R-01~R-12)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python skill_audit.py audit ~/.workbuddy/skills/git-sync
  python skill_audit.py audit ~/.workbuddy/skills/svg-composer --json
  python skill_audit.py audit-all ~/.workbuddy/skills --manifest manifest.json
  python skill_audit.py rules
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # audit 子命令
    p_audit = subparsers.add_parser("audit", help="审查单个 skill")
    p_audit.add_argument("skill_dir", help="skill 目录路径")
    p_audit.add_argument("--json", action="store_true", help="JSON 格式输出")
    p_audit.add_argument("--manifest-version", metavar="VER", help="manifest 中记录的版本号（用于 R-10）")

    # audit-all 子命令
    p_all = subparsers.add_parser("audit-all", help="批量审查所有 skill")
    p_all.add_argument("skills_dir", help="skills 根目录")
    p_all.add_argument("--manifest", metavar="FILE", help="manifest.json 路径（用于 R-10 版本比对）")
    p_all.add_argument("--json", action="store_true", help="JSON 格式输出")

    # rules 子命令
    subparsers.add_parser("rules", help="列出所有审查规则")

    args = parser.parse_args()

    if args.command == "audit":
        cmd_audit(args)
    elif args.command == "audit-all":
        cmd_audit_all(args)
    elif args.command == "rules":
        cmd_rules()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
