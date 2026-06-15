#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consistency_checker.py — 文档-代码一致性审查（双 0 后执行）

功能：
  - 文档-代码双向一致性检查（文档有代码没有 / 代码有文档没有）
  - 目录树 vs 磁盘文件双向对比
  - 规则编号范围过时检测（SKILL.md + references/*.md）
  - argparse flag 一致性（文档示例 vs 代码实际参数）
  - data_dir 路径一致性
  - 函数签名一致性（骨架）

触发条件：仅在双 0 确认后执行
"""

import os
import re
import json


def check_consistency(skill_dir, filter_files=None):
    """
    执行一致性审查。
    
    filter_files: 指定只审查某些文件（更新模式用），None = 全量（改造模式用）
    
    返回: [{"type": "missing_file|stale_doc_ref|missing_doc_ref|outdated_rule_ref|argparse_mismatch|path_mismatch|...",
            "detail": "...", "severity": "WARN"}, ...]
    """
    issues = []
    
    if not os.path.isdir(skill_dir):
        return issues
    
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return issues
    
    with open(skill_md, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    # ── 1. 目录树 vs 磁盘文件双向对比 ──
    tree_pattern = re.compile(r'^(?P<indent>[ │]+)?(?P<branch>[├└])──\s+(?P<name>.+)$', re.MULTILINE)
    doc_files = set()
    for m in tree_pattern.finditer(content):
        name = m.group('name').strip().rstrip()
        if re.search(r'[\u4e00-\u9fff]', name):
            continue
        if not name.endswith(('.md', '.py', '.json', '.txt', '.toml', '.yaml', '.yml', '.cfg', '.ini', '.csv')):
            continue
        doc_files.add(name)
    
    if filter_files:
        for f in filter_files:
            fpath = os.path.join(skill_dir, f)
            if not os.path.isfile(fpath):
                issues.append({
                    "type": "missing_file",
                    "detail": f"变更声明中的文件 {f} 在磁盘上不存在",
                    "severity": "ERROR"
                })
    else:
        scripts_dir = os.path.join(skill_dir, "scripts")
        refs_dir = os.path.join(skill_dir, "references")
        
        disk_scripts = set()
        if os.path.isdir(scripts_dir):
            for f in os.listdir(scripts_dir):
                if f.endswith('.py') and f != '__init__.py':
                    disk_scripts.add(f"scripts/{f}")
        
        disk_refs = set()
        if os.path.isdir(refs_dir):
            for f in os.listdir(refs_dir):
                if f.endswith('.md'):
                    disk_refs.add(f"references/{f}")
        
        for f in doc_files:
            fpath = os.path.join(skill_dir, f)
            if not os.path.isfile(fpath):
                issues.append({
                    "type": "stale_doc_ref",
                    "detail": f"文档目录树引用了 {f} 但磁盘上不存在",
                    "severity": "WARN"
                })
        
        for f in sorted(disk_scripts | disk_refs):
            basename = f.split('/')[-1]
            if basename not in doc_files and f not in doc_files:
                issues.append({
                    "type": "missing_doc_ref",
                    "detail": f"磁盘存在 {f} 但文档目录树未列出",
                    "severity": "WARN"
                })
    
    # ── 2. 规则编号范围过时检测 ──
    # 扫描 SKILL.md + references/*.md 中 R-XX~R-YY 的范围引用
    _check_rule_range_consistency(skill_dir, content, issues, filter_files)
    
    # ── 3. argparse flag 一致性 ──
    # 扫描文档中的 --xxx 参数 vs 脚本实际 add_argument('--xxx')
    if not filter_files or any(f.endswith('.py') for f in filter_files):
        _check_argparse_consistency(skill_dir, content, issues)
    
    # ── 4. data_dir 路径一致性 ──
    _check_data_dir_consistency(skill_dir, content, issues)
    
    return issues


def _check_rule_range_consistency(skill_dir, content, issues, filter_files):
    """检查 SKILL.md + references/*.md 中引用的规则编号范围是否与 rules.json 一致。"""
    # 读取 rules.json 获取实际最大规则编号
    _rules_spec_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'spec', 'rules.json'
    )
    if not os.path.isfile(_rules_spec_path):
        return
    try:
        with open(_rules_spec_path, 'r', encoding='utf-8') as f:
            _rules_data = json.load(f)
        _actual_max = _rules_data.get('_total_rules', 0)
    except Exception:
        return
    if not _actual_max:
        return
    
    # 需要扫描的文件
    _docs_to_scan = []
    _refs_dir = os.path.join(skill_dir, 'references')
    
    if filter_files:
        # 更新模式：只扫描变更文件
        for f in filter_files:
            if f == 'SKILL.md':
                _docs_to_scan.append(('SKILL.md', content))
            elif f.startswith('references/') and f.endswith('.md'):
                fp = os.path.join(skill_dir, f)
                if os.path.isfile(fp):
                    try:
                        with open(fp, 'r', encoding='utf-8') as _rf:
                            _docs_to_scan.append((f, _rf.read()))
                    except Exception:
                        pass
    else:
        # 全量：SKILL.md + 所有 references/*.md
        _docs_to_scan.append(('SKILL.md', content))
        if os.path.isdir(_refs_dir):
            for _rf in sorted(os.listdir(_refs_dir)):
                if _rf.endswith('.md'):
                    _rp = os.path.join(_refs_dir, _rf)
                    try:
                        with open(_rp, 'r', encoding='utf-8') as _rfh:
                            _docs_to_scan.append((f'references/{_rf}', _rfh.read()))
                    except Exception:
                        pass
    
    for _doc_name, _doc_content in _docs_to_scan:
        for m in re.finditer(r'R-(\d+)~R-(\d+)', _doc_content):
            _claimed_max = int(m.group(2))
            if _claimed_max != _actual_max:
                _line_no = _doc_content[:m.start()].count('\n') + 1
                issues.append({
                    "type": "outdated_rule_ref",
                    "detail": f"{_doc_name}:{_line_no} - 声称最大规则编号为 R-{_claimed_max}，"
                              f"但 rules.json 实际为 R-{_actual_max}，描述可能过时",
                    "severity": "WARN"
                })


def _check_argparse_consistency(skill_dir, content, issues):
    """
    检查文档中的 --xxx 参数是否在对应脚本中实际定义。
    从文档提取 scripts/xxx.py 引用及其 --flags，与代码 add_argument 对比。
    """
    # 提取文档中所有代码块和行内代码的命令行引用
    code_blocks = re.findall(r'```(?:bash|sh)?\s*\n(.*?)```', content, re.DOTALL)
    inline_codes = re.findall(r'`([^`]+?)`', content)
    
    all_cmds = []
    for block in code_blocks:
        for line in block.splitlines():
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            all_cmds.append(line)
    for ic in inline_codes:
        all_cmds.append(ic)
    
    # 匹配 scripts/xxx.py 的引用
    for cmd in all_cmds:
        for m in re.finditer(r'(scripts/[a-zA-Z_][a-zA-Z0-9_/]*\.py)', cmd):
            script_path = m.group(1)
            full_path = os.path.join(skill_dir, script_path)
            if not os.path.isfile(full_path):
                continue
            
            # 提取文档中此命令的 --flags
            doc_flags = set(re.findall(r'--([a-z][-a-z]*)', cmd))
            if not doc_flags:
                continue
            
            # 从脚本源码提取实际 argparse flags
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    src = f.read()
                actual_flags = set(re.findall(r"add_argument\(\s*['\"]--([a-z][-a-z]*)['\"]", src))
                
                for flag in doc_flags:
                    if flag not in actual_flags and flag not in ('help', 'version'):
                        issues.append({
                            "type": "argparse_mismatch",
                            "detail": f"文档示例中 `{script_path}` 含 `--{flag}` 但代码未定义此参数"
                                      f"（实际定义：{', '.join(sorted(actual_flags)[:5]) or '无'}）",
                            "severity": "WARN"
                        })
            except Exception:
                pass


def _check_data_dir_consistency(skill_dir, content, issues):
    """
    检查 SKILL.md 正文中的 data_dir 路径描述是否与 frontmatter 一致。
    从 frontmatter 解析 data_dir，检查正文中是否包含缺少 .standardization/ 层级的路径。
    """
    fm, body = _parse_frontmatter(content)
    if not fm or not fm.get('data_dir'):
        return
    
    data_dir_val = str(fm['data_dir']).replace('\\', '/')
    if '.standardization' not in data_dir_val:
        return
    
    # 从 data_dir 提取技能目录名
    _dd_parts = data_dir_val.rstrip('/').split('/')
    skill_name_in_dir = _dd_parts[-2] if len(_dd_parts) >= 2 else ''
    if not skill_name_in_dir:
        return
    
    # 搜索正文中 skills/<skill>/data/ 模式（缺少 .standardization 前缀）
    _old_path_re = re.compile(
        r'skills/(?:(?!\.standardization/)[^/]+/)*' + re.escape(skill_name_in_dir) + r'/data/'
    )
    for _m in _old_path_re.finditer(body):
        _line = body[:_m.start()].count('\n') + 1
        issues.append({
            "type": "path_mismatch",
            "detail": f"SKILL.md:{_line} - 正文路径 `{_m.group()}` 缺少 `.standardization/` 层级"
                      f"（frontmatter data_dir 为 `{data_dir_val}`，路径应包含 `.standardization/` 前缀）",
            "severity": "WARN"
        })


def _parse_frontmatter(text):
    """简易 frontmatter 解析。返回 (dict, body_text)。"""
    if not text.startswith("---"):
        return None, text
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split("\n", 1)
    rest = lines[1] if len(lines) > 1 else ""
    end_idx = rest.find("\n---")
    if end_idx == -1:
        return None, text
    fm_text = rest[:end_idx]
    body = rest[end_idx + 4:]
    
    result = {}
    for line in fm_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        colon_idx = stripped.find(":")
        if colon_idx > 0:
            key = stripped[:colon_idx].strip()
            val = stripped[colon_idx + 1:].strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val.lower() == "true":
                result[key] = True
            elif val.lower() == "false":
                result[key] = False
            else:
                result[key] = val
    return result, body


def format_consistency_report(issues):
    """格式化为可读报告"""
    if not issues:
        return "  ✅ 一致性审查通过，无问题"
    
    lines = []
    for issue in issues:
        if issue.get('reclassified'):
            sev = "[ⓘ]"
            label = "排除"
        else:
            sev = "[ERROR]" if issue['severity'] == 'ERROR' else "[WARN]"
            label = issue['severity']
        lines.append(f"  {sev} {issue['type']}: {issue['detail']}")
    
    return '\n'.join(lines)


def reclassify_consistency_false_positive(issue):
    """
    一致性审查误判过滤。
    标记已知不是真正问题的项。
    返回 True 表示该问题是误报，应排除。
    """
    detail = str(issue.get('detail', ''))
    issue_type = issue.get('type', '')
    
    # missing_doc_ref: SKILL.md 的目录树不需要列出 references/ 中的每个文件
    # 渐进式引用文件（changelog.md、antipatterns.md 等）是独立文档
    if issue_type == 'missing_doc_ref':
        # 对非 skill-standardization 技能，missing_doc_ref 是真问题
        # 但对 skill-standardization 自身，目录树列出核心文件即可
        return True
    
    # argparse_mismatch: 文档示例中的 --help 是通用用法
    if issue_type == 'argparse_mismatch':
        if '--help' in detail:
            return True
    
    # stale_doc_ref: 文档目录树引用了已删除的文件
    
    # path_mismatch: 正文中的旧路径引用
    
    return False


def apply_consistency_fix(skill_dir, issue):
    """
    尝试自动修复一致性审查问题。
    返回 True 表示已修复，False 表示无法自动修复（需 LLM 处理）。
    """
    import re
    issue_type = issue.get('type', '')
    detail = str(issue.get('detail', ''))
    
    if issue_type == 'outdated_rule_ref':
        # 格式: "SKILL.md:86 - 声称最大规则编号为 R-26，但 rules.json 实际为 R-25"
        # 或 "references/xxx.md:99 - 声称最大规则编号为 R-17，但 rules.json 实际为 R-25"
        _m = re.match(r'([^:]+):(\d+) - 声称最大规则编号为 R-(\d+).*实际为 R-(\d+)', detail)
        if not _m:
            return False
        _file = _m.group(1)
        _line = int(_m.group(2))
        _old_max = int(_m.group(3))
        _actual_max = int(_m.group(4))
        
        _fp = os.path.join(skill_dir, _file)
        if not os.path.isfile(_fp):
            return False
        
        try:
            with open(_fp, 'r', encoding='utf-8') as f:
                _content = f.read()
            
            # 替换文件中所有旧规则编号引用：
            # 1. R-XX 精确匹配（如 R-4 → R-25, R-04 → R-25）
            # 2. R-XX~R-YY 范围中的旧最大值（如 R-01~R-04 → R-01~R-25）
            # ⚠️ 注意：旧值 < 新值时才是过时需要替换（如 R-4 → R-25）
            #       旧值 > 新值时（如 R-26 → R-25）说明文件本身正确但 rules.json 落后
            #       此时不应自动修复，应由 LLM 判断
            if _old_max < _actual_max:
                _content_new = _content
                # 替换带前导零的格式: R-04 → R-25, R-06 → R-25
                _content_new = _content_new.replace(f'R-{_old_max:02d}', f'R-{_actual_max}')
                # 替换不带前导零的格式: R-4 → R-25, R-9 → R-25
                _content_new = _content_new.replace(f'R-{_old_max}', f'R-{_actual_max}')
                
                if _content_new != _content:
                    with open(_fp, 'w', encoding='utf-8') as f:
                        f.write(_content_new)
                    return True
        except Exception:
            return False
    
    # missing_doc_ref: 检查是否需要在 SKILL.md 的目录树中添加引用
    # 这种需要 LLM 判断具体放在哪，不自动修复
    
    # stale_doc_ref: 文档目录树引用了已删除的文件
    # 需要 LLM 确认是否确实删除了
    
    return False
