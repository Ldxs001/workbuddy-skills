#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/artifact_checker.py — 产出物路径检查函数 (R-11, R-12)
"""

import os
import re
import json
from pathlib import Path

from .utils import (
    _KNOWN_ROOT_FILES, _KNOWN_STANDARD_DIRS, _ARTIFACT_DIR_CLASSIFY,
    _ARTIFACT_EXTS_COMPREHENSIVE, _ROOT_ARTIFACT_EXTS, _ROOT_EXT_CLASSIFY,
    _ARTIFACT_WRITE_PATTERNS, _HARDCODED_PATH_RE, _PATH_EXCLUDE_RE,
    _is_hardcoded_path, _classify_artifact, _classify_artifact_by_ext,
    _extract_path_literal,
)


def check_artifact_paths(filepath, content, fm, body, skill_dir=None, **kw):
    """R-11: 全面产出物路径检测（铁律4）。"""
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "跳过：无法确定技能目录", "skip": True}

    violations = []
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

    # ── 3. 非标准子目录扫描 ──
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
                line += f"\n    [!] 关联引用 ({len(v['cross_refs'])}处): {', '.join(v['cross_refs'])}"
            detail_lines.append(line)
        return {
            "passed": False,
            "detail": "\n".join(detail_lines),
            "violations": [{"source": v["source"], "path": v["path_literal"],
                           "suggestion": v["suggestion"], "cross_refs": v.get("cross_refs", [])}
                          for v in violations],
            "fix": {"key": "artifact_paths", "value": True,
                     "location": f"{skill_dir} (scripts/ 及根目录)",
                     "operation": "将所有违规产出物路径迁移至 skills/.standardization/<skill>/{outputs,data,cache,temp}/ 目录，并更新所有交叉引用",
                     "verification": "重新运行 audit_skill()，确认 R-11 passed"},
        }
    else:
        return {"passed": True, "detail": "未发现产出物路径违规（scripts/ + 根目录 + 子目录均通过）"}


def _check_root_artifact_files(skill_dir, violations):
    """根目录产出物文件检测"""
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
    """非标准子目录扫描"""
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
            continue

        classification = _ARTIFACT_DIR_CLASSIFY.get(entry.lower())
        if classification:
            cat, desc = classification
            _scan_dir_recursive(skill_dir, entry, entry_path, cat, violations)
        else:
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
    """递归扫描一个产出物目录"""
    try:
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d != "__pycache__"]

            for fname in sorted(files):
                if fname in (".gitkeep", ".gitignore"):
                    continue

                violations.append({
                    "source": f"DIR/{rel_dir}/{fname}",
                    "path_literal": f"{rel_dir}/{fname}",
                    "suggestion": f"skills/.standardization/<skill>/{category}/{fname}",
                })
    except OSError:
        return


def _scan_unknown_dir(skill_dir, entry, entry_path, violations):
    """扫描未知目录名"""
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
        return

    if artifact_files:
        cat = "outputs"
        for sub in artifact_files:
            violations.append({
                "source": f"DIR/{entry}/{sub}",
                "path_literal": f"{entry}/{sub}",
                "suggestion": f"skills/.standardization/<skill>/{cat}/{sub}",
            })


def _check_python_artifact_paths_v2(rel_path, script_lines, violations):
    """[v2.11.0] Check Python script for artifact path violations"""
    for i, line in enumerate(script_lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue

        for pat in _ARTIFACT_WRITE_PATTERNS:
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

        # Generic hardcoded path detection
        for m in _HARDCODED_PATH_RE.finditer(stripped):
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

        # Legacy artifact dir check（已合并到上方 _ARTIFACT_WRITE_PATTERNS 检查，跳过）
        continue  # noqa: 296 遗留死代码，变量已废弃


def _trace_cross_references(skill_dir, violations):
    """反向搜索整个 skill 目录，找出引用每个违规路径的关联文件。"""
    search_patterns = list(set(v["path_literal"] for v in violations))

    text_exts = {".md", ".json", ".yaml", ".yml", ".txt", ".cfg", ".toml", ".ini", ".html"}
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
            if ext not in text_exts:
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.join(rel_root, fname).replace("\\", "/") if rel_root else fname
            searchable_files.append((rel, fpath))

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
        refs = [r for r in refs if r != v["source"] and r != v["source"].replace("ROOT/", "")]
        if refs:
            v["cross_refs"] = refs


def _verify_standardization_paths(skill_dir, violations):
    """[v2.10.0] 验证脚本中声称的 skills/.standardization/ 路径在磁盘上真实存在。"""
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return

    skills_dir = _find_skills_dir(skill_dir)
    std_re = re.compile(r'\.standardization/([^"\')\s,。，；：！？、…—）】」』%]+)')

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


def check_external_data_dir(filepath, content, fm, body, skill_dir=None, **kw):
    """R-12: External data directory path validation."""
    if not skill_dir or not os.path.isdir(skill_dir):
        return {"passed": True, "detail": "skip: cannot determine skill dir", "skip": True}

    dirname = os.path.basename(os.path.abspath(skill_dir))
    violations = []
    expected_pattern = ".standardization/" + dirname + "/"

    # 1. scan scripts/ for data dir definitions
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

    # 2. check paths conform to standardization/<skill-name>/ convention
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
                "detail": var_name + "=" + path_val + " violates skills/.standardization/<skill>/ convention (same as R-11). "
                       "【推荐写法】变量名含 DATA 的那行直接赋值合规字面量，"
                       "再用另一个不含关键词的变量（如 _data_dir_abs）计算绝对路径。",
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

    # 5. [v2.10.0] disk existence check
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
    refs_dir = os.path.join(skill_dir, "references")
    if os.path.isdir(refs_dir):
        _REFS_PATH_RE = re.compile(
            r'(?:~|/home/\w+|/Users/\w+|C:\\Users\\\w+|/c/Users/\w+)?'
            r'(?:/|\\)(?:\.?workbuddy(?:/|\\)(?:skills(?:/|\\))?)?'
            r'([\w.-]+(?:/|\\)data(?:/|\\))'
        )
        for fname in sorted(os.listdir(refs_dir)):
            if fname == "changelog.md":
                continue
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
                        if not stripped or stripped.startswith('#') or stripped.startswith('<!--'):
                            continue
                        if '.standardization/' in stripped:
                            continue
                        for m in _REFS_PATH_RE.finditer(stripped):
                            matched_path = m.group(1)
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
            "fix": {"key": "external_data_dir", "value": True,
                     "location": f"{skill_dir}/_meta.json 及 scripts/ 中的数据目录变量",
                     "operation": (
                         "在 _meta.json 中添加 data_dir 字段，"
                         "确保 scripts/ 中数据目录路径符合 skills/.standardization/<skill>/data/ 规范。\n"
                         "【推荐写法】（同时满足审计静态检查和运行时正确性）:\n"
                         "  # 审计锚点：存放合规字面量，变量名含 DATA 被审计匹配\n"
                         '  DEFAULT_DATA_DIR_RAW = "skills/.standardization/<skill-name>/data/"\n'
                         "  SKILL_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
                         "  _data_dir_abs   = os.path.normpath(os.path.join(SKILL_ROOT, '..', DEFAULT_DATA_DIR_RAW))\n"
                         "  BACKUP_DIR = os.path.join(_data_dir_abs, 'backup')\n"
                         "  LOGS_DIR  = os.path.join(_data_dir_abs, 'logs')\n"
                         "要点：① 第一行变量名必须含 DATA/STORAGE/DB/CACHE/CONFIG 才会被审计匹配；"
                         "② 值必须是 skills/.standardization/<skill>/data/ 字面量；"
                         "③ 运行时用另一个不含上述关键词的变量（如 _data_dir_abs）存放绝对路径，避免被审计二次匹配。"
                     ),
                     "verification": "重新运行 audit_skill()，确认 R-12 passed"},
        }
    else:
        if data_dir_vars:
            return {"passed": True,
                    "detail": (
                        "External data dir paths conform to standard, "
                        "_meta.json data_dir declared and consistent.\n"
                        "【推荐写法参考】（同时满足审计+运行时正确性）:\n"
                        "  DEFAULT_DATA_DIR_RAW = 'skills/.standardization/<skill>/data/'\n"
                        "  _data_dir_abs = os.path.normpath(os.path.join(SKILL_ROOT, '..', DEFAULT_DATA_DIR_RAW))\n"
                        "  BACKUP_DIR = os.path.join(_data_dir_abs, 'backup')\n"
                        "要点：① 变量名含 DATA 的行存合规字面量（审计匹配）；"
                        "② 用另一个不含 DATA/STORAGE 等关键词的变量（如 _data_dir_abs）存绝对路径（运行时使用）。"
                    )}
        else:
            return {"passed": True, "detail": "No external data dir variables defined in scripts/ (nothing to check)", "skip": True}


def _extract_path_value(val_expr):
    """Extract path string from Python assignment expression."""
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
    m = re.match(r'''^['"](.+?)['"]$''', val_expr.strip())
    if m:
        return m.group(1)
    return val_expr.strip()


def _find_skills_dir(skill_dir):
    """向上查找 skills 目录（最多 5 层）。"""
    p = os.path.abspath(skill_dir)
    for _ in range(5):
        if os.path.basename(p) == "skills" and os.path.isdir(p):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return os.path.dirname(os.path.abspath(skill_dir))


def fix_artifact_paths(skill_dir):
    """
    R-11 自动修复：将 scripts/*.py 中的硬编码产出物路径
    替换为 skills/.standardization/<skill>/ 规范路径。
    返回修复数量。
    """
    import re, os
    if not skill_dir or not os.path.isdir(skill_dir):
        return 0

    skill_name = os.path.basename(os.path.abspath(skill_dir))
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return 0

    # 调用检查函数获取违规列表
    from .artifact_checker import check_artifact_paths
    import tempfile, json
    tmp = tempfile.mktemp(suffix=".json")
    result = check_artifact_paths(
        os.path.join(skill_dir, "SKILL.md"),
        open(os.path.join(skill_dir, "SKILL.md"), "r", encoding="utf-8").read(),
        {}, "", skill_dir=skill_dir
    )
    if result.get("passed"):
        return 0

    violations = result.get("violations", [])
    fixed = 0

    for v in violations:
        src = v.get("source", "")
        # src 格式： "scripts/foo.py:42" 或 "ROOT/foo.html"
        if not src.startswith("scripts/"):
            continue
        parts = src.split(":")
        if len(parts) != 2:
            continue
        fname = parts[0].replace("scripts/", "", 1)
        try:
            lineno = int(parts[1]) - 1  # 0-based
        except ValueError:
            continue

        fpath = os.path.join(scripts_dir, fname)
        if not os.path.isfile(fpath):
            continue

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            continue

        if lineno < 0 or lineno >= len(lines):
            continue

        old_line = lines[lineno]
        suggestion = v.get("suggestion", "")
        # suggestion 格式： "skills/.standardization/<skill>/outputs/foo.html"
        if not suggestion:
            continue

        # 提取规范路径的组件
        sug_parts = suggestion.replace("skills/.standardization/", "").split("/")
        if len(sug_parts) < 2:
            continue

        category = sug_parts[1]  # outputs / data / cache / temp
        filename = sug_parts[-1] if "/" in suggestion else ""

        # 构造替换行：将路径替换为 Path 拼接形式
        # 旧：".../outputs/foo.html" 或 Path.home() / "..."
        # 新：SKILL_ROOT / ".standardization" / skill_name / category / filename
        # 在 get_*_home() 函数中：default = Path.home() / ".workbuddy" / "skills" / ".standardization" / skill_name / category
        if "default" in old_line and "Path.home()" in old_line:
            indent = old_line[:len(old_line) - len(old_line.lstrip())]
            new_line = indent + 'default = Path.home() / ".workbuddy" / "skills" / ".standardization" / "' + skill_name + '" / "' + category + '"\n'
            if filename:
                new_line = indent + 'default = Path.home() / ".workbuddy" / "skills" / ".standardization" / "' + skill_name + '" / "' + category + '"\n'
            lines[lineno] = new_line
            with open(fpath, "w", encoding="utf-8") as f:
                f.writelines(lines)
            fixed += 1

    return fixed


def fix_external_data_dir(skill_dir):
    """
    R-12 自动修复：
    1. 更新 _meta.json 添加 data_dir 字段
    2. 更新 scripts/*.py 中的数据目录变量
    返回修复数量。
    """
    import re, os, json
    if not skill_dir or not os.path.isdir(skill_dir):
        return 0

    skill_name = os.path.basename(os.path.abspath(skill_dir))
    fixed = 0

    # 1. 更新 _meta.json
    meta_file = os.path.join(skill_dir, "_meta.json")
    meta = {}
    if os.path.isfile(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    expected = "skills/.standardization/" + skill_name + "/data/"
    if meta.get("data_dir") != expected:
        meta["data_dir"] = expected
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.write("\n")
        fixed += 1
        print("    [OK] 更新 _meta.json: data_dir = " + expected)

    # 2. 更新 scripts/*.py 中的数据目录变量
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return fixed

    for fname in sorted(os.listdir(scripts_dir)):
        fpath = os.path.join(scripts_dir, fname)
        if not os.path.isfile(fpath) or not fname.endswith(".py"):
            continue

        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue

        original = content
        # 匹配：VAR_NAME = Path.home() / "..." / "..."
        pattern = re.compile(
            r'^(s*)([A-Za-z_]+w*(?:DATA|STORAGE|DB|CACHE|CONFIG)[A-Za-z_]*)(s*=\s*Path\.home(s*)((?:\s*/\s*"[^"]+")+))',
            re.MULTILINE
        )
        for m in pattern.finditer(content):
            indent = m.group(1)
            var_name = m.group(2)
            path_parts = re.findall(r'["\']([^"\']*)["\']', m.group(4))
            if not path_parts:
                continue
            # 替换为标准路径
            new_value = 'Path.home() / ".workbuddy" / "skills" / ".standardization" / "' + skill_name + '" / "data"'
            new_line = indent + var_name + " = " + new_value
            content = content[:m.start()] + new_line + content[m.end():]
            fixed += 1
            print("    [OK] 更新 " + fname + ": " + var_name + " → 标准路径")
            break  # 每个文件只修第一个匹配

        if content != original:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)

    return fixed
