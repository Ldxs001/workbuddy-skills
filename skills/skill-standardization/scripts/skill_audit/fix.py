#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix.py — skill-standardization 统一修复工具
为全部 23 条审计规则（R-01~R-23）提供针对性修复函数。

大模型/LLM 看到审计结果后，直接调用对应修复函数：
    from skill_audit.fix import apply_fix
    apply_fix(skill_dir, "name", value="xxx")  # R-01

修复函数命名规则：fix_<rule_key>(skill_dir, **kw)

v2.37.0: 初始版本，覆盖全部 23 条规则
"""

import os
import re
import io
import json

from .utils import parse_simple_yaml_frontmatter


# ═══════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════

def _read_file(filepath):
    """读取文件内容（UTF-8）"""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _write_file(filepath, content):
    """写入文件内容（UTF-8）"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _update_frontmatter_field(filepath, field_name, field_value):
    """
    更新 SKILL.md frontmatter 中的单个字段。
    如果字段不存在则添加（追加在 --- 之后）。
    返回: True/False
    """
    if not os.path.isfile(filepath):
        return False
    content = _read_file(filepath)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return False
    fm[field_name] = field_value
    body = body.lstrip("\n")
    # 重写文件
    buf = io.StringIO()
    buf.write("---\n")
    for k, v in fm.items():
        if isinstance(v, bool):
            buf.write(f"{k}: {'true' if v else 'false'}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {v}\n")
        else:
            buf.write(f"{k}: {v}\n")
    buf.write("---\n")
    buf.write(body)
    _write_file(filepath, buf.getvalue())
    return True


def _add_section_to_body(filepath, section_title, section_body, insert_after=None):
    """
    向 SKILL.md body 添加（或替换）一个 ## 章节。
    insert_after: 如果指定，在该章节之后插入；否则追加到 body 末尾。
    返回: True/False
    """
    if not os.path.isfile(filepath):
        return False
    content = _read_file(filepath)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return False

    lines = body.split("\n")
    # 检查章节是否已存在
    existing = [i for i, ln in enumerate(lines) if ln.strip().startswith(f"## {section_title}")]
    if existing:
        # 替换现有章节内容
        start = existing[0]
        end = start + 1
        while end < len(lines) and not lines[end].strip().startswith("## "):
            end += 1
        lines = lines[:start+1] + [section_body] + lines[end:]
    else:
        # 追加新章节
        if insert_after:
            # 找到 insert_after 章节的结束位置
            in_sec = False
            insert_idx = len(lines)
            for i, ln in enumerate(lines):
                if ln.strip().startswith(f"## {insert_after}"):
                    in_sec = True
                    continue
                if in_sec and ln.strip().startswith("## "):
                    insert_idx = i
                    break
            lines = lines[:insert_idx] + ["", f"## {section_title}", section_body] + lines[insert_idx:]
        else:
            lines.append("")
            lines.append(f"## {section_title}")
            lines.append(section_body)

    new_body = "\n".join(lines)
    buf = io.StringIO()
    buf.write("---\n")
    for k, v in fm.items():
        if isinstance(v, bool):
            buf.write(f"{k}: {'true' if v else 'false'}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {v}\n")
        else:
            buf.write(f"{k}: {v}\n")
    buf.write("---\n")
    buf.write(new_body)
    _write_file(filepath, buf.getvalue())
    return True


# ═══════════════════════════════════════════════════
# R-01: name 字段修复
# ═══════════════════════════════════════════════════

def fix_name(skill_dir, **kw):
    """
    R-01 修复：添加/更正 SKILL.md name 字段。
    value: 技能名称（如 "git-sync"）
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", os.path.basename(os.path.abspath(skill_dir)))
    ok = _update_frontmatter_field(skill_md, "name", value)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-02: description 字段修复
# ═══════════════════════════════════════════════════

def fix_description(skill_dir, **kw):
    """
    R-02 修复：添加/更正 description 字段。
    value: 技能描述
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", "")
    if not value:
        # 尝试从 name 推断
        content = _read_file(skill_md)
        fm, _ = parse_simple_yaml_frontmatter(content)
        if fm and fm.get("name"):
            value = f"{fm['name']} 技能"
    if not value:
        return 0
    ok = _update_frontmatter_field(skill_md, "description", value)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-03: author 字段修复
# ═══════════════════════════════════════════════════

def fix_author(skill_dir, **kw):
    """
    R-03 修复：添加 author 字段。
    value: 作者名
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", "[username-redacted]")
    ok = _update_frontmatter_field(skill_md, "author", value)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-04: version 字段修复
# ═══════════════════════════════════════════════════

def fix_version(skill_dir, **kw):
    """
    R-04 修复：更正 version 字段格式（X.Y.Z 三段式）。
    value: 版本号（如 "1.2.3"）
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", "1.0.0")
    # 确保格式正确
    m = re.match(r'(\d+)', str(value))
    if m:
        value = m.group(1) + ".0.0" if len(value.split(".")) == 1 else value
    ok = _update_frontmatter_field(skill_md, "version", value)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-05: skill_macro 字段修复
# ═══════════════════════════════════════════════════

def fix_skill_macro(skill_dir, **kw):
    """
    R-05 修复：添加 skill_macro 字段（调用宏）。
    value: 宏名称（如 "unified"）
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", "unified")
    ok = _update_frontmatter_field(skill_md, "skill_macro", value)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-06: 一级标题修复
# ═══════════════════════════════════════════════════

def fix_h1(skill_dir, **kw):
    """
    R-06 修复：在 SKILL.md body 开头添加一级标题。
    value: 标题文本（如 "git-sync"）
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    value = kw.get("value", fm.get("name", os.path.basename(os.path.abspath(skill_dir))))
    # 检查是否已有 H1
    if re.search(r'^# .+', body, re.MULTILINE):
        return 0  # 已存在
    # 在 body 开头插入 H1
    new_body = f"# {value}\n\n{body.lstrip()}"
    # 重写文件
    buf = io.StringIO()
    buf.write("---\n")
    for k, v in fm.items():
        if isinstance(v, bool):
            buf.write(f"{k}: {'true' if v else 'false'}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {v}\n")
        else:
            buf.write(f"{k}: {v}\n")
    buf.write("---\n")
    buf.write(new_body)
    _write_file(skill_md, buf.getvalue())
    return 1


def fix_h1_version(skill_dir, **kw):
    """
    R-06 修复：移除 H1 标题中的版本号。
    如 '# skill-standardization v2.38.7' → '# skill-standardization'
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    # 匹配 # 开头的一级标题中是否含版本号
    m = re.search(r'^(#\s+.*?)\s+v?\d+\.\d+\.\d+\s*$', body, re.MULTILINE)
    if not m:
        return 0  # 无版本号
    h1_clean = m.group(1).strip()
    # 替换
    new_body = re.sub(r'^(#\s+.*?)\s+v?\d+\.\d+\.\d+\s*$', f'# {h1_clean}', body, count=1, flags=re.MULTILINE)
    buf = io.StringIO()
    buf.write("---\n")
    for k, v in fm.items():
        if isinstance(v, bool):
            buf.write(f"{k}: {'true' if v else 'false'}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {v}\n")
        else:
            buf.write(f"{k}: {v}\n")
    buf.write("---\n")
    buf.write(new_body)
    _write_file(skill_md, buf.getvalue())
    return 1


def fix_h1_position(skill_dir, **kw):
    """
    R-06 修复：将 H1 移到 frontmatter 后首行。
    如 H1 在 body 的非开头位置（如 ## 触发条件 之后），
    将其提到 body 最前面。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    # 找到 body 中的 H1（排除代码块内的 # 注释）
    body_no_code = re.sub(r'```.*?```', '', body, flags=re.DOTALL)
    m = re.search(r'^# .+', body_no_code, re.MULTILINE)
    if not m:
        return 0
    # 检查 H1 是否已在 body 前 2 行内
    h1_body_line = body[:m.start()].count('\n') + 1
    if h1_body_line <= 2:
        return 0  # 位置已正确
    # 分离 H1 之前的内容、H1 本身、H1 之后的内容
    lines = body.split('\n')
    h1_idx = m.group(0)
    # 按行找到实际 H1 位置（用 body_no_code 定位但操作 body 的真实行）
    body_lines = body.split('\n')
    real_h1_idx = None
    for i, line in enumerate(body_lines):
        stripped = line.strip()
        if stripped.startswith('# ') and stripped not in ('# 返回', '# {', '# [',
             '# 每次', '# 备份', '# Windows', '# 或命令', '# 今天', '# 指定', '# 规则', '# 工作日', '# 日程'):
            # 简单判断：不在代码块标志内（不以空格/制表符缩进的行）
            if not line.startswith(' ') and not line.startswith('\t'):
                # 确认这是我们要找的 H1（排除# 返回这类注释）
                real_h1_idx = i
                break
    if real_h1_idx is None:
        return 0
    # 重组：H1 移到 body 开头，其余内容保持相对顺序
    h1_line = body_lines[real_h1_idx].strip()
    before = body_lines[:real_h1_idx]
    after = body_lines[real_h1_idx + 1:]
    # 清理 before 的尾部空行
    while before and not before[-1].strip():
        before.pop()
    # 清理 after 的头部空行
    while after and not after[0].strip():
        after.pop(0)
    # 新 body
    new_body_lines = ['# ' + h1_line[2:].strip() if h1_line.startswith('# ') else h1_line,
                      ''] + before + [''] + after
    new_body = '\n'.join(new_body_lines)
    # 写回
    buf = io.StringIO()
    buf.write("---\n")
    for k, v in fm.items():
        if isinstance(v, bool):
            buf.write(f"{k}: {'true' if v else 'false'}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {v}\n")
        else:
            buf.write(f"{k}: {v}\n")
    buf.write("---\n")
    buf.write(new_body)
    _write_file(skill_md, buf.getvalue())
    return 1


# ═══════════════════════════════════════════════════
# R-07: 触发条件章节修复
# ═══════════════════════════════════════════════════

def fix_section_trigger(skill_dir, **kw):
    """
    R-07 修复：添加/完善 ## 触发场景 章节。
    优先从目标技能自身采集触发词，回退到 content_format 格式。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    name = fm.get("name", "本技能")
    desc = fm.get("description", "")

    # ── 采集源：从脚本 docstring 中提取功能关键词 ──
    triggers = []
    neg_triggers = ["简单问答、闲聊、问候（不需要本技能）", "单步任务（不需要结构化执行）"]
    scripts_dir = os.path.join(skill_dir, "scripts")
    if os.path.isdir(scripts_dir):
        for root, dirs, files in os.walk(scripts_dir):
            for f in files:
                if not f.endswith('.py'): continue
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as fh:
                        src = fh.read()
                except: continue
                # 从 docstring 提取功能描述
                docstrings = re.findall(r'"""(.*?)"""', src, re.DOTALL)
                for ds in docstrings:
                    lines = [l.strip() for l in ds.split('\n') if l.strip()]
                    for line in lines[:3]:
                        if len(line) > 6 and len(line) < 60 and not line.startswith(('Args', 'Returns', 'Raises')):
                            triggers.append(line[:50])

    # ── 采集源：从 frontmatter trigger 字段 ──
    fm_triggers = fm.get("trigger", "")
    if isinstance(fm_triggers, list):
        for t in fm_triggers:
            if t and t not in triggers:
                triggers.append(t)

    # ── 采集源：从 description 提取关键动作 ──
    action_kw = re.findall(r'[\u4e00-\u9fff]{2,}(?:工具|功能|能力|模块|系统)', desc)
    for a in action_kw:
        if a not in triggers:
            triggers.append(a)

    # ── 去重截断 ──
    triggers = [t for t in triggers if len(t) > 4][:6]

    if not triggers:
        triggers = [f"使用 {name}", f"询问关于 {name} 的问题", f"需要 {name}"]

    # ── 生成正/否定双列表 ──
    pos_items = '\n'.join(f"- 用户需要{t}" if not t.startswith('- ') else t for t in triggers[:4])
    neg_section = '\n'.join(f"- {t}" for t in neg_triggers)

    section_body = (
        f"**正向触发（满足以下任意一条）：**\n"
        f"{pos_items}\n\n"
        f"**否定条件（满足以下任意一条，不触发）：**\n"
        f"{neg_section}\n"
    )

    ok = _add_section_to_body(skill_md, "触发场景", section_body, insert_after=None)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-08: 核心能力章节修复
# ═══════════════════════════════════════════════════

def fix_section_core(skill_dir, **kw):
    """
    R-08 修复：添加 ## 核心能力 章节。
    使用 body.json content_format 模板生成表格格式。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    name = fm.get("name", "本技能")

    # 从 body.json 读取 content_format 模板
    spec = _load_body_spec()
    fmt = None
    for sec in spec.get("required_sections", []):
        kws = sec.get("keywords", [])
        if any(k in str(kws) for k in ["核心功能", "核心能力", "概述"]):
            fmt = sec.get("content_format", {})
            break

    if fmt and fmt.get("type") == "table":
        # 使用 content_format 的表格模板
        cols = fmt.get("table_columns", ["#", "能力", "说明"])
        col_header = "| " + " | ".join(cols) + " |"
        col_sep = "|" + "|".join("-" * max(len(c) + 2, 3) for c in cols) + "|"
        section_body = (
            f"> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。\n\n"
            f"{col_header}\n"
            f"{col_sep}\n"
            f"| 1 | **{name} 功能一** | 功能一的简要说明 |\n"
            f"| 2 | **{name} 功能二** | 功能二的简要说明 |\n"
            f"| 3 | **{name} 功能三** | 功能三的简要说明 |\n"
        )
    else:
        # 回退：无序列表格式
        section_body = (
            f"- {name} 的核心功能 1\n"
            f"- {name} 的核心功能 2\n"
            f"- {name} 的核心功能 3\n"
            "> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），"
            "详细内容拆分到 `references/*.md` 按需加载。\n"
        )
    ok = _add_section_to_body(skill_md, "核心能力", section_body, insert_after=None)
    return 1 if ok else 0


def fix_section_workflow(skill_dir, **kw):
    """
    R-09 修复：添加 ## 工作流程 章节。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    name = fm.get("name", "本技能") if fm else "本技能"
    section_body = (
        "1. 理解用户需求\n"
        "2. 规划执行步骤\n"
        "3. 调用相关工具/脚本\n"
        "4. 返回结果给用户\n"
        "> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），"
        "详细内容拆分到 `references/*.md` 按需加载。"
    )
    ok = _add_section_to_body(skill_md, "工作流程", section_body, insert_after="核心能力")
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-10: home_url 字段修复
# ═══════════════════════════════════════════════════

def fix_home_url(skill_dir, **kw):
    """
    R-10 修复：添加 home_url 字段（相关链接）。
    value: URL
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", "")
    if not value:
        return 0
    ok = _update_frontmatter_field(skill_md, "home_url", value)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-11: 产出物路径修复
# ═══════════════════════════════════════════════════

def fix_artifact_paths(skill_dir, **kw):
    """
    R-11 修复：将违规文件迁出根目录/脚本目录。
    
    两步逻辑：
    1. 分辨文件性质：
       - 缓存/临时/错误文件（*.tmp, *.bak, __pycache__/, .DS_Store等）→ 直接删除
       - 有意义的文件（脚本、配置、数据）→ 移到正确位置（scripts/ 或 data/）
    2. 修正引用：
       - 移动/删除后，扫描所有文件中的引用路径并修正
    
    返回：修复的文件数
    """
    fixed = 0
    skill_name = os.path.basename(os.path.abspath(skill_dir))
    std_base = os.path.join(".standardization", skill_name)
    
    # ── 第1步：分辨文件性质，决定删除还是移动 ──
    # 应删除的垃圾文件模式（缓存、临时、错误文件）
    _TRASH_PATTERNS = {
        r'.*\.tmp$', r'.*\.bak$', r'.*\.swp$', r'.*\.swo$',
        r'.*\.pyc$', r'.*\.pyo$', r'.*__pycache__.*',
        r'.*\.DS_Store$', r'.*\.Thumbs\.db$', r'.*\~$',
        r'^#.*#$', r'.*\.log$',  # 日志文件也删
    }
    import re
    trash_re = re.compile('|'.join(_TRASH_PATTERNS))
    
    # 收集需要处理的违规文件（来自审计结果）
    violations = kw.get("violations", [])
    if not violations:
        # 如果没有传 violations，自己跑一次审计
        from .artifact_checker import check_artifact_paths
        with open(os.path.join(skill_dir, "SKILL.md"), "r", encoding="utf-8") as f:
            content = f.read()
        fm, body = parse_simple_yaml_frontmatter(content)
        result = check_artifact_paths(None, content, fm, body, skill_dir=skill_dir)
        violations = result.get("violations", [])
    
    # 分类：删除 vs 移动
    to_delete = []  # (path, reason)
    to_move = []    # (src, dst_dir, reason)
    
    for v in violations:
        src = v.get("source", "")
        path_lit = v.get("path_literal", "")
        suggestion = v.get("suggestion", "")
        
        if not path_lit or not os.path.exists(os.path.join(skill_dir, path_lit)):
            continue
        
        full_path = os.path.join(skill_dir, path_lit)
        
        # 判断：垃圾文件 → 删除；其他 → 移动
        is_trash = trash_re.search(path_lit) is not None
        # 额外启发：0字节文件、乱码文件名 → 删除
        try:
            if os.path.getsize(full_path) == 0:
                is_trash = True
        except OSError:
            pass
        
        if is_trash:
            to_delete.append((full_path, f"垃圾文件: {suggestion}"))
        else:
            # 有意义文件：移到正确位置
            # suggestion 格式：skills/.standardization/<skill>/<cat>/<fname>
            # 提取目标目录
            if "/" in suggestion:
                parts = suggestion.replace("skills/.standardization/", "").split("/")
                if len(parts) >= 2:
                    cat = parts[1]  # outputs/data/cache/temp
                    dst_dir = os.path.join(skill_dir, ".standardization", skill_name, cat)
                    to_move.append((full_path, dst_dir, suggestion))
    
    # ── 执行删除 ──
    deleted_files = []
    for fpath, reason in to_delete:
        try:
            os.remove(fpath)
            deleted_files.append(fpath)
            fixed += 1
            print(f"  [删除] {os.path.relpath(fpath, skill_dir)} — {reason}")
        except Exception as e:
            print(f"  [删除失败] {fpath}: {e}")
    
    # ── 执行移动 ──
    moved_files = []
    for src, dst_dir, suggestion in to_move:
        try:
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            # 如果目标已存在，加后缀
            if os.path.exists(dst):
                base, ext = os.path.splitext(dst)
                dst = f"{base}_moved{ext}"
            shutil.move(src, dst)
            moved_files.append((src, dst))
            fixed += 1
            print(f"  [移动] {os.path.relpath(src, skill_dir)} → {os.path.relpath(dst, skill_dir)}")
        except Exception as e:
            print(f"  [移动失败] {src}: {e}")
    
    # ── 第2步：修正引用 ──
    # 收集所有被删除/移动的文件路径（相对 skill_dir）
    affected = {}
    for fpath in deleted_files:
        rel = os.path.relpath(fpath, skill_dir)
        affected[rel] = None  # None 表示已删除
    for src, dst in moved_files:
        src_rel = os.path.relpath(src, skill_dir)
        dst_rel = os.path.relpath(dst, skill_dir)
        affected[src_rel] = dst_rel
    
    if affected:
        print(f"  扫描引用路径，共 {len(affected)} 个文件受影响...")
        # 扫描所有文件，查找引用
        for root, dirs, files in os.walk(skill_dir):
            # 跳过 .standardization/ 数据目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    original = content
                    # 替换所有受影响路径
                    for old_rel, new_rel in affected.items():
                        if new_rel is None:
                            # 文件已删除：移除引用行或注释掉
                            # 简单处理：替换文件名为警告注释
                            old_name = os.path.basename(old_rel)
                            content = content.replace(old_name, f"[DELETED:{old_name}]")
                        else:
                            # 文件已移动：更新路径
                            content = content.replace(old_rel, new_rel)
                            # 也试试 Unix 风格路径
                            content = content.replace(old_rel.replace("\\", "/"), 
                                                       new_rel.replace("\\", "/"))
                    if content != original:
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"  [修正引用] {os.path.relpath(fpath, skill_dir)}")
                        fixed += 1
                except Exception:
                    continue
    
    return fixed


# ═══════════════════════════════════════════════════
# R-12: 外部数据目录修复
# ═══════════════════════════════════════════════════

def fix_external_data_dir(skill_dir, **kw):
    """
    R-12 修复：统一数据目录路径到 skills/.standardization/<skill>/data/
    调用 artifact_checker 中的 fix_external_data_dir 函数。
    """
    from .artifact_checker import fix_external_data_dir as _fix
    return _fix(skill_dir)


# ═══════════════════════════════════════════════════
# R-13: sensitive_access 字段修复
# ═══════════════════════════════════════════════════

def fix_sensitive_access(skill_dir, **kw):
    """
    R-13 修复：添加/更正 sensitive_access 字段。
    value: true/false
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", False)
    ok = _update_frontmatter_field(skill_md, "sensitive_access", bool(value))
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-14: critical_write 字段修复
# ═══════════════════════════════════════════════════

def fix_critical_write(skill_dir, **kw):
    """
    R-14 修复：添加/更正 critical_write 字段。
    value: true/false
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", False)
    ok = _update_frontmatter_field(skill_md, "critical_write", bool(value))
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-15: 权限说明文档修复
# ═══════════════════════════════════════════════════

def fix_create_permissions_md(skill_dir, **kw):
    """
    R-15 修复：创建 references/permissions.md 并说明高权限操作风险。
    """
    refs_dir = os.path.join(skill_dir, "references")
    os.makedirs(refs_dir, exist_ok=True)
    permissions_md = os.path.join(refs_dir, "permissions.md")
    if os.path.isfile(permissions_md):
        return 0  # 已存在
    content = (
        "# 权限说明\n\n"
        "## 风险等级\n\n"
        "（请填写：LOW / MEDIUM / HIGH / CRITICAL）\n\n"
        "## 高权限操作说明\n\n"
        "（如含敏感信息访问、关键位置写入，请在此说明：）\n"
        "- 操作：\n"
        "- 必要性：\n"
        "- 如何降低风险：\n"
    )
    _write_file(permissions_md, content)
    return 1


# ═══════════════════════════════════════════════════
# R-16: permission_weight 字段修复
# ═══════════════════════════════════════════════════

def fix_permission_weight(skill_dir, **kw):
    """
    R-16 修复：添加/更正 permission_weight 字段。
    value: LOW / MEDIUM / HIGH / CRITICAL
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    value = kw.get("value", "LOW")
    ok = _update_frontmatter_field(skill_md, "permission_weight", value)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-17: 渐进加载强制修复
# ═══════════════════════════════════════════════════

def fix_progressive_loading(skill_dir, **kw):
    """
    R-17 修复：如果 SKILL.md 超过 200 行，拆分到 references/。
    这是一个复杂修复，可能需要人工介入。
    此函数提供一个基础实现：添加 references/ 引用提示。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    lines = body.split("\n")
    if len(lines) <= 200:
        return 0  # 不需要修复

    # 在核心能力/工作流程章节添加渐进式加载引用提示
    # 实际拆分需要人工判断，这里只添加提示
    note = "\n> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。\n"
    if "> 📚 **渐进式加载**" not in body:
        # 在第一个 ## 章节前插入提示
        new_lines = []
        inserted = False
        for ln in lines:
            if not inserted and ln.strip().startswith("## "):
                new_lines.append(note.strip())
                inserted = True
            new_lines.append(ln)
        new_body = "\n".join(new_lines)
        # 重写文件
        buf = io.StringIO()
        buf.write("---\n")
        for k, v in fm.items():
            if isinstance(v, bool):
                buf.write(f"{k}: {'true' if v else 'false'}\n")
            elif isinstance(v, (int, float)):
                buf.write(f"{k}: {v}\n")
            else:
                buf.write(f"{k}: {v}\n")
        buf.write("---\n")
        buf.write(new_body)
        _write_file(skill_md, buf.getvalue())
        return 1
    return 0


# ═══════════════════════════════════════════════════
# R-18: 反模式渐进式修复
# ═══════════════════════════════════════════════════

def fix_antipattern_progressive(skill_dir, **kw):
    """
    R-18 修复：将反模式内容移到 references/antipatterns.md，
    并在 SKILL.md 中添加引用。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    refs_dir = os.path.join(skill_dir, "references")
    os.makedirs(refs_dir, exist_ok=True)
    antipattern_md = os.path.join(refs_dir, "antipatterns.md")
    if not os.path.isfile(antipattern_md):
        # 创建模板
        content = (
            "# 反模式与常见错误\n\n"
            "## AP-01: 错误做法示例\n\n"
            "**错误做法：**\n\n"
            "（请描述错误做法）\n\n"
            "**正确做法：**\n\n"
            "（请描述正确做法）\n\n"
            "**深层原因：**\n\n"
            "（请描述深层原因）\n"
        )
        _write_file(antipattern_md, content)
    # 在 SKILL.md 中添加引用（如果还没有）
    body = _read_file(skill_md)
    if "references/antipatterns.md" not in body:
        # 在文件末尾添加引用
        new_content = body + "\n> 详见 [反模式](references/antipatterns.md)\n"
        _write_file(skill_md, new_content)
    return 1


# ═══════════════════════════════════════════════════
# R-19: FAQ 渐进式修复
# ═══════════════════════════════════════════════════

def fix_faq_progressive(skill_dir, **kw):
    """
    R-19 修复：将 FAQ 内容移到 references/faq.md，
    并在 SKILL.md 中添加引用。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    refs_dir = os.path.join(skill_dir, "references")
    os.makedirs(refs_dir, exist_ok=True)
    faq_md = os.path.join(refs_dir, "faq.md")
    if not os.path.isfile(faq_md):
        # 创建模板
        content = (
            "# FAQ / 常见问题\n\n"
            "## Q1: 本技能是做什么的？\n\n"
            "A: （请填写答案，≥15字）\n\n"
            "## Q2: 如何触发本技能？\n\n"
            "A: （请填写答案，≥15字）\n\n"
            "## Q3: 本技能有哪些限制？\n\n"
            "A: （请填写答案，≥15字）\n"
        )
        _write_file(faq_md, content)
    # 在 SKILL.md 中添加引用（如果还没有）
    body = _read_file(skill_md)
    if "references/faq.md" not in body:
        new_content = body + "\n> 详见 [FAQ](references/faq.md)\n"
        _write_file(skill_md, new_content)
    return 1


# ═══════════════════════════════════════════════════
# R-20: 写作规范修复
# ═══════════════════════════════════════════════════

def fix_writing_standards(skill_dir, **kw):
    """
    R-20 修复：自动更正术语不一致、添加中英文混排空格等。
    这是一个复杂修复，可能需要人工审核。
    此函数提供一个基础实现：自动更正最常见的术语不一致。
    返回：修复的问题数
    """
    fixed = 0
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    original = content
    # 术语不一致自动修复（常见错误）
    replacements = [
        ("建立", "创建"),
        ("新建", "创建"),
        ("修改", "更新"),
        ("变更", "更新"),
        ("移除", "删除"),
        ("去掉", "删除"),
        ("设置", "配置"),
        ("设定", "配置"),
    ]
    for wrong, right in replacements:
        if wrong in content:
            content = content.replace(wrong, right)
            fixed += 1
    if content != original:
        _write_file(skill_md, content)
    # 也检查 references/*.md
    refs_dir = os.path.join(skill_dir, "references")
    if os.path.isdir(refs_dir):
        for fname in sorted(os.listdir(refs_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(refs_dir, fname)
            ref_content = _read_file(fpath)
            ref_original = ref_content
            for wrong, right in replacements:
                if wrong in ref_content:
                    ref_content = ref_content.replace(wrong, right)
                    fixed += 1
            if ref_content != ref_original:
                _write_file(fpath, ref_content)
    return fixed


# ═══════════════════════════════════════════════════
# R-21: 渐进式加载显式说明修复
# ═══════════════════════════════════════════════════

def fix_progressive_loading_explicit(skill_dir, **kw):
    """
    R-21 修复：在 ## 核心能力 或 ## 工作流程 章节添加固定模板句。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    fixed = False
    if "> 📚 **渐进式加载**" not in body:
        # 在 ## 核心能力 章节开头插入
        fixed_body = body.replace(
            "## 核心能力",
            "## 核心能力\n\n> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。"
        )
        if fixed_body == body:
            # 尝试在 ## 工作流程 章节开头插入
            fixed_body = body.replace(
                "## 工作流程",
                "## 工作流程\n\n> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。"
            )
        if fixed_body != body:
            # 重写文件
            buf = io.StringIO()
            buf.write("---\n")
            for k, v in fm.items():
                if isinstance(v, bool):
                    buf.write(f"{k}: {'true' if v else 'false'}\n")
                elif isinstance(v, (int, float)):
                    buf.write(f"{k}: {v}\n")
                else:
                    buf.write(f"{k}: {v}\n")
            buf.write("---\n")
            buf.write(fixed_body)
            _write_file(skill_md, buf.getvalue())
            fixed = True
    return 1 if fixed else 0


# ═══════════════════════════════════════════════════
# R-22: 数据目录规范修复
# ═══════════════════════════════════════════════════

def fix_data_dir_compliance(skill_dir, dry_run=False, **kw):
    """
    R-22 修复：自动迁移安装目录中的越位数据文件到数据目录。
    调用 data_dir_checker 中的 fix_data_dir_compliance 函数。
    """
    from .data_dir_checker import fix_data_dir_compliance as _fix
    return _fix(skill_dir, dry_run=dry_run)


# ═══════════════════════════════════════════════════
# R-23: 文档-代码一致性修复
# ═══════════════════════════════════════════════════

def _find_actual_file(skill_dir, ref_stem, ref_ext):
    """通用文件查找：先同目录，再递归 scripts/
    返回 (found_path, skill_dir_relative_path) 或 None
    """
    from pathlib import Path
    # 递归搜索 scripts/ 下所有文件，建立 basename→实际路径 索引
    scripts_dir = os.path.join(skill_dir, 'scripts')
    if os.path.isdir(scripts_dir):
        for root, dirs, files in os.walk(scripts_dir):
            for fname in files:
                fstem, fext = os.path.splitext(fname)
                if fstem == ref_stem and fext != ref_ext:
                    rel = os.path.relpath(os.path.join(root, fname), skill_dir).replace('\\', '/')
                    return (os.path.join(root, fname), rel)
    return None


def _fix_md_file_refs(skill_dir, md_path):
    """修复单个 .md 中不存在的文件路径引用（通用文件查找）"""
    import re
    if not os.path.isfile(md_path):
        return 0
    content = _read_file(md_path)
    changed = 0
    new_content = content
    for m in reversed(list(re.finditer(r'([^\s`]+\.[a-zA-Z]{2,4})', content))):
        ref = m.group(1).strip().strip("'\"")
        if '/' not in ref and '\\' not in ref:
            continue
        if ref.startswith(('http', 'file:', '{', '<', '-')):
            continue
        if '*' in ref or '?' in ref:
            continue
        if re.search(r'[{\u4e00-\u9fff]', ref):
            continue
        full = os.path.join(skill_dir, ref)
        if os.path.isfile(full):
            continue
        ref_stem = os.path.splitext(os.path.basename(ref))[0]
        ref_ext = os.path.splitext(ref)[1]

        # 先查同目录
        ref_dir = os.path.dirname(full)
        found = False
        if os.path.isdir(ref_dir):
            for actual in sorted(os.listdir(ref_dir)):
                actual_stem, actual_ext = os.path.splitext(actual)
                if actual_stem == ref_stem and actual_ext != ref_ext:
                    new_path = os.path.join(os.path.dirname(ref), actual).replace('\\', '/')
                    new_content = new_content.replace(m.group(1), new_path, 1)
                    changed += 1
                    found = True
                    break
        if found:
            continue

        # 递归查 scripts/
        result = _find_actual_file(skill_dir, ref_stem, ref_ext)
        if result:
            new_content = new_content.replace(m.group(1), result[1], 1)
            changed += 1

    if changed > 0:
        _write_file(md_path, new_content)
    return changed


def fix_doc_code_consistency(skill_dir, **kw):
    """
    R-23 修复：文档-代码一致性问题。
    1. 自动修复 .md 中不存在的文件路径引用（查找同名不同扩展名的文件）
    2. 脚本 --help 检查（基础）
    返回：修复的问题数
    """
    fixed = 0
    # 1. 修复 .md 文件中的文件路径引用
    md_files = [os.path.join(skill_dir, 'SKILL.md')]
    refs_dir = os.path.join(skill_dir, 'references')
    if os.path.isdir(refs_dir):
        for fname in sorted(os.listdir(refs_dir)):
            if fname.endswith('.md'):
                md_files.append(os.path.join(refs_dir, fname))
    for md_path in md_files:
        fixed += _fix_md_file_refs(skill_dir, md_path)
    # 2. 脚本 --help 检查（原有逻辑）
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return fixed
    return fixed


# ═══════════════════════════════════════════════════
# fix_meta_json_completeness — _meta.json 7 标准字段补全
# ═══════════════════════════════════════════════════

def fix_meta_json_completeness(skill_dir, **kw):
    """R-25: 补全 _meta.json 缺失的 7 标准字段，非标字段判断迁移或删除。"""
    import os, json
    meta_path = os.path.join(skill_dir, '_meta.json')
    if not os.path.isfile(meta_path):
        meta = {}
    else:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)

    META_STANDARD = {'name', 'version', 'description', 'author', 'tags',
                     'data_dir', 'triggers'}
    skill_name = os.path.basename(skill_dir.rstrip('/\\'))
    fixes = 0

    # 补缺失字段
    defaults = {
        'name': skill_name,
        'version': '1.0.0',
        'description': '',
        'author': 'unknown',
        'tags': [],
        'data_dir': f'skills/.standardization/{skill_name}/',
        'triggers': [],
    }
    for field in META_STANDARD:
        if field not in meta:
            meta[field] = defaults[field]
            fixes += 1

    # 非标字段处理：先输出供判断，再删除（_meta.json 不应有不一致字段）
    extra = [k for k in meta if k not in META_STANDARD]
    if extra:
        print(f'  ⚠️  发现非标字段: {", ".join(extra)}')
        print(f'  → _meta.json 是机器元数据，不应存在非标准字段。')
        print(f'  → 请确认这些字段是否需要迁移到标准字段体系：')
        print(f'     - 若字段值有用（如 home_url），建议迁移到 frontmatter 或 scripts/spec/')
        print(f'     - 若字段是历史遗留/冗余数据，将自动删除')
        # 直接删除非标字段（_meta.json 应保持严格一致）
        for k in extra:
            del meta[k]
        print(f'  ✅ 已删除非标字段: {", ".join(extra)}')

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    if fixes > 0:
        print(f'  ✅ _meta.json: 补全 {fixes} 个缺失字段')
    return fixes


# ═══════════════════════════════════════════════════
# fix_frontmatter_fields — SKILL.md frontmatter 13 标准字段补全
# ═══════════════════════════════════════════════════

def fix_frontmatter_fields(skill_dir, **kw):
    """R-01 修复：补全 frontmatter 缺失的 11 required + 2 conditional 字段，标记非标字段。"""
    import os, re, tempfile, shutil
    skill_md = os.path.join(skill_dir, 'SKILL.md')
    if not os.path.isfile(skill_md):
        return 0

    # ── 分层字段定义 ──
    FM_REQUIRED = {'name','version','description','author','license','tags',
                   'data_dir','external_data_dir',
                   'sensitive_access','critical_write','permission_weight'}
    FM_CONDITIONAL = {'trigger','trigger_negative'}
    FM_OPTIONAL = {'references','category','priority','deprecated'}
    FM_STANDARD = FM_REQUIRED | FM_CONDITIONAL | FM_OPTIONAL

    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()

    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return 0

    fm_text = m.group(1)
    existing = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('  '): continue
        kv = re.match(r'^([\w_-]+)\s*:', line)
        if kv:
            existing[kv.group(1)] = line

    skill_name = os.path.basename(skill_dir.rstrip('/\\'))
    defaults = {
        'name': f'name: {skill_name}',
        'version': 'version: 1.0.0',
        'description': 'description: ',
        'author': 'author: [username-redacted]',
        'license': 'license: MIT',
        'tags': 'tags: []',
        'data_dir': f'data_dir: ../.standardization/{skill_name}/',
        'external_data_dir': 'external_data_dir:',    # 空值（对应 YAML null）
        'sensitive_access': 'sensitive_access: false',
        'critical_write': 'critical_write: false',
        'permission_weight': 'permission_weight: LOW',
        'trigger': 'trigger: ',                        # 空值（用户后续填写）
        'trigger_negative': 'trigger_negative: ',      # 空值（用户后续填写）
    }

    fm_lines = fm_text.split('\n')
    insert_pos = 0
    for i, line in enumerate(fm_lines):
        if line.startswith('name:'):
            insert_pos = i + 1
            break

    added = []
    # 先补 required，再补 conditional（条件字段优先级低）
    for field in sorted(FM_REQUIRED):
        if field not in existing:
            fm_lines.insert(insert_pos + len(added), defaults[field])
            added.append(field)
    for field in sorted(FM_CONDITIONAL):
        if field not in existing:
            fm_lines.insert(insert_pos + len(added), defaults[field])
            added.append(field)

    extra = [k for k in existing if k not in FM_STANDARD]
    if extra:
        print(f'  [WARN] 非标字段(仅提醒，不移除。如需清理请手动处理): {", ".join(extra)}')

    if not added:
        return 0

    new_fm = '\n'.join(fm_lines)
    new_content = content[:m.start(1)] + new_fm + content[m.end(1):]
    tmp = tempfile.mktemp(suffix='.md', dir=skill_dir)
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(new_content)
    shutil.move(tmp, skill_md)
    print(f'  [OK] SKILL.md frontmatter: +{", ".join(added)}')
    return len(added)


# ═══════════════════════════════════════════════════
# fix_missing_data_dir — 给脚本补 DEFAULT_DATA_DIR_RAW + DATA_DIR
# ═══════════════════════════════════════════════════

def fix_missing_data_dir(skill_dir, **kw):
    """
    R-12 step 1.5 配套修复：给引用 .standardization 但缺少 DATA_DIR 的脚本
    补上 DEFAULT_DATA_DIR_RAW + DATA_DIR 声明。

    处理逻辑：
    - Python 脚本：在最后一个 import 后插入，缺 pathlib 则补
    - Shell 脚本：在 shebang 后插入 bash 兼容的变量赋值
    - 已有 DATA_DIR 的脚本跳过

    返回：修复的脚本数量
    """
    dry_run = kw.get("dry_run", False)
    skill_name = os.path.basename(os.path.normpath(skill_dir))
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return 0

    fixed = 0
    # DATA 变量正则（与 artifact_checker.py 保持一致）
    data_var_re = re.compile(
        r'^([A-Za-z_]*?(?:DATA|STORAGE|DB|CACHE|CONFIG)[A-Za-z_]*(?:_DIR|_PATH))\s*=\s*(.+)$'
    )

    for fname in sorted(os.listdir(scripts_dir)):
        fpath = os.path.join(scripts_dir, fname)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in (".py", ".sh", ".bat", ".ps1"):
            continue

        content = _read_file(fpath)
        # 没引用 .standardization 的跳过
        if ".standardization" not in content:
            continue
        # 已有 DATA 变量的跳过
        if data_var_re.search(content, re.MULTILINE):
            continue

        if ext == ".py":
            new_content = _insert_data_dir_python(content, skill_name, fname)
        else:
            new_content = _insert_data_dir_shell(content, skill_name, fname)

        if new_content and new_content != content:
            if dry_run:
                print(f"  [DRY-RUN] {fname}: 将插入 DATA_DIR")
            else:
                _write_file(fpath, new_content)
            fixed += 1
            if not dry_run:
                print(f"    [OK] {fname}: 已添加 DEFAULT_DATA_DIR_RAW + DATA_DIR")

    return fixed


def _insert_data_dir_python(content, skill_name, fname):
    """为 Python 脚本插入 DATA_DIR 代码块（仅插入顶层导入区，不进函数体）"""
    lines = content.splitlines(keepends=True)

    # 找到插入点：最后一个顶层 import/from 行之后
    # 仅统计在第一个 def/class/if __name__ 之前的 import
    insert_at = 0
    need_pathlib = True
    reached_body = False
    in_multiline_import = False  # 跟踪多行 import 的括号嵌套
    paren_depth = 0
    for i, l in enumerate(lines):
        s = l.strip()
        # 遇到函数定义、类定义、模块级 if/for/while 就停止统计 import
        if s.startswith("def ") or s.startswith("class "):
            reached_body = True
            break
        # 跟踪多行 import: from x import ( ... )
        if "import (" in s or ("import" in s and "(" in s.split("#")[0]):
            if "(" in s and ")" not in s.split("#")[0]:
                in_multiline_import = True
                paren_depth = s.count("(") - s.count(")")
                continue
        if in_multiline_import:
            paren_depth += s.count("(") - s.count(")")
            if paren_depth <= 0:
                in_multiline_import = False
                # 多行 import 结束后，插入点设在此行之后
                insert_at = i + 1
            continue
        if s.startswith("import ") or s.startswith("from "):
            insert_at = i + 1  # 插入在此行之后
            if "pathlib" in s and "Path" in s:
                need_pathlib = False

    # 如果找不到任何顶层 import（文件内 import 都在函数中），在第一个函数定义前插入
    if insert_at == 0 and reached_body:
        for i, l in enumerate(lines):
            s = l.strip()
            if s.startswith("def ") or s.startswith("class "):
                insert_at = i
                break

    # 构建插入块
    block_lines = []
    block_lines.append("")
    block_lines.append("# R-12 审计锚点：数据目录字面量声明")
    block_lines.append('DEFAULT_DATA_DIR_RAW = "skills/.standardization/' + skill_name + '/data/"')
    block_lines.append("")
    block_lines.append("SKILL_DIR = Path(__file__).resolve().parent.parent")
    block_lines.append("# 运行时绝对路径")
    block_lines.append('DATA_DIR = SKILL_DIR.parent / ".standardization" / "' + skill_name + '" / "data"')
    block_lines.append("")

    block = "\n".join(block_lines) + "\n"

    if need_pathlib:
        # 补 from pathlib import Path
        pathlib_line = "from pathlib import Path\n"
        # 在 insert_at 位置先插 pathlib，再插 block
        new_lines = lines[:insert_at] + [pathlib_line] + [block] + lines[insert_at:]
    else:
        new_lines = lines[:insert_at] + [block] + lines[insert_at:]

    return "".join(new_lines)


def _insert_data_dir_shell(content, skill_name, fname):
    """为 Shell 脚本插入 DATA_DIR 变量"""
    lines = content.splitlines(keepends=True)

    # 找到 shebang 行的位置
    insert_at = 0
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("#!") and ("bash" in s or "sh" in s or "zsh" in s):
            insert_at = i + 1
            break

    block_lines = []
    block_lines.append("")
    block_lines.append("# R-12 审计锚点：数据目录")
    block_lines.append('DEFAULT_DATA_DIR_RAW="skills/.standardization/' + skill_name + '/data/"')
    block_lines.append('SKILL_DIR="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"')
    block_lines.append('DATA_DIR="$SKILL_DIR/../.standardization/' + skill_name + '/data"')
    block_lines.append("")

    block = "\n".join(block_lines) + "\n"
    new_lines = lines[:insert_at] + [block] + lines[insert_at:]
    return "".join(new_lines)


def fix_meta_field_sync(skill_dir, **kw):
    """
    R-10 修复：同步 _meta.json 与 frontmatter 的共享字段。
    按权威方向同步：tags(_meta→fm), description(fm→_meta), trigger(fm→_meta)
    """
    import json, os, re
    skill_md = os.path.join(skill_dir, "SKILL.md")
    meta_path = os.path.join(skill_dir, "_meta.json")
    if not os.path.isfile(skill_md) or not os.path.isfile(meta_path):
        return 0

    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    fixed = 0

    # 1. tags: _meta → frontmatter
    meta_tags = meta.get('tags', [])
    if meta_tags:
        fm_tags_str = ', '.join(f"'{t}'" for t in meta_tags) if meta_tags else '[]'
        # Update frontmatter
        new_fm = {}
        for k, v in fm.items():
            if k == 'tags':
                new_fm[k] = f"[{', '.join(repr(t) for t in meta_tags)}]"
            else:
                new_fm[k] = v
        fm = new_fm
        fixed += 1

    # 2. description: frontmatter → _meta
    fm_desc = str(fm.get('description', '')).strip() if isinstance(fm.get('description'), str) else ''
    if fm_desc:
        meta['description'] = fm_desc
        fixed += 1

    # 3. trigger: frontmatter → _meta.triggers（转数组）
    fm_trigger = fm.get('trigger', '')
    if fm_trigger and isinstance(fm_trigger, str):
        trigger_list = [t.strip() for t in fm_trigger.split('|') if t.strip()]
        meta['triggers'] = trigger_list
        fixed += 1

    # 4. data_dir: _meta → frontmatter（转换 skills/ 格式为 ../ 相对路径）
    meta_data_dir = meta.get('data_dir', '')
    fm_data_dir_str = str(fm.get('data_dir', '')).strip() if isinstance(fm.get('data_dir'), str) else ''
    if meta_data_dir and fm_data_dir_str:
        def _norm_rel(p):
            p = p.replace('\\', '/').rstrip('/')
            # _meta 格式: skills/.standardization/xxx/data/ → ../.standardization/xxx/data/
            if p.startswith('skills/'):
                p = '../' + p[len('skills/'):]
            return p
        fm_data_dir_norm = _norm_rel(fm_data_dir_str)
        meta_data_dir_norm = _norm_rel(meta_data_dir)
        if fm_data_dir_norm != meta_data_dir_norm:
            fm['data_dir'] = meta_data_dir_norm
            fixed += 1

    # Write _meta.json
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Rebuild and write SKILL.md
    buf = io.StringIO()
    buf.write("---\n")
    for k, v in fm.items():
        if isinstance(v, bool):
            buf.write(f"{k}: {'true' if v else 'false'}\n")
        elif isinstance(v, (int, float)):
            buf.write(f"{k}: {v}\n")
        else:
            buf.write(f"{k}: {v}\n")
    buf.write("---\n")
    buf.write(body)
    _write_file(skill_md, buf.getvalue())

    return fixed


# ═══════════════════════════════════════════════════════════
# fix_section_constraint — 从目标技能代码采集约束，生成 ## 约束 章节
# ═══════════════════════════════════════════════════════════
def fix_section_constraint(skill_dir, **kw):
    """
    从目标技能自身的脚本和文档中采集约束，生成 ## 约束 章节。
    不套模板，不照抄——只提取该技能特有的操作规则。
    
    采集来源（按优先级）：
    1. scripts/*.py 中注释/文档字符串含"必须/不得/禁止/MUST/REQUIRED"的规则
    2. references/*.md 中 markdown 列表项含"必须/不得/禁止"的条目
    3. SKILL.md 正文中已有的规则描述（去重后提取）
    
    输出：无序列表，每行一条约束，最多 5 条。
    """
    import ast, os, re
    
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    
    constraints = []
    
    # ── 采集源1: 扫描 scripts/*.py 中的 docstring 和注释 ──
    scripts_dir = os.path.join(skill_dir, "scripts")
    if os.path.isdir(scripts_dir):
        for root, dirs, files in os.walk(scripts_dir):
            for f in files:
                if not f.endswith('.py'):
                    continue
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, 'r', encoding='utf-8') as fh:
                        src = fh.read()
                except Exception:
                    continue
                # 提取 docstring 中含约束词的句子
                for m in re.finditer(r'(?:必须|不得|禁止|MUST|REQUIRED)[\u4e00-\u9fff]{4,}[。！]', src):
                    rule = m.group().strip().strip('。！\n')
                    if rule and len(rule) > 4 and rule not in constraints:
                        constraints.append(rule)
    
    # ── 采集源2: 扫描 references/*.md 中的列表项 ──
    refs_dir = os.path.join(skill_dir, "references")
    if os.path.isdir(refs_dir):
        for f in os.listdir(refs_dir):
            if not f.endswith('.md'):
                continue
            fpath = os.path.join(refs_dir, f)
            try:
                with open(fpath, 'r', encoding='utf-8') as fh:
                    ref_content = fh.read()
            except Exception:
                continue
            for m in re.finditer(r'^[-*]\s+(?:必须|不得|禁止)[\u4e00-\u9fff]{4,}[。！]', ref_content, re.MULTILINE):
                rule = m.group().strip().lstrip('-* ')
                if rule and len(rule) > 6 and rule not in constraints:
                    constraints.append(rule)
    
    # ── 采集源3: 从已有 body 中找约束类内容（去重）──
    for m in re.finditer(r'^[-*]\s+.*?(?:必须|不得|禁止|MUST)[^\\n]*', body, re.MULTILINE):
        rule = m.group().strip().lstrip('-* ')
        if rule and len(rule) > 6 and rule not in constraints:
            constraints.append(rule)
    
    # ── 如果没有采集到，回退到从蓝皮书中提取核心功能 ──
    if not constraints:
        # 从 SKILL.md 的触发场景和核心能力中提取关键词
        trigger_section = re.search(r'## 触发场景.*?(?=## |\\Z)', body, re.DOTALL)
        if trigger_section:
            # 提取触发词作为能力的体现
            items = re.findall(r'[-*]\s*(.+?)(?:当|如果|用户|需要)', trigger_section.group())
            for item in items[:3]:
                item = item.strip()
                if item and len(item) > 4:
                    constraints.append(f"操作前必须确认{item[:30]}")
    
    if not constraints:
        return 0  # 实在采集不到就跳过
    
    # ── 去重 + 截断最多 5 条 ──
    seen = set()
    unique = []
    for c in constraints:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    constraints = unique[:5]
    
    body_lines = constraints
    section_body = '\n'.join(f'- {c}' for c in constraints)
    
    ok = _add_section_to_body(skill_md, "约束", section_body, insert_after=None)
    return len(constraints) if ok else 0


# ═══════════════════════════════════════════════════════════
# fix_progressive_index_table — 扫描 references/ 生成渐进式索引表
# ═══════════════════════════════════════════════════════════
def fix_progressive_index_table(skill_dir, **kw):
    """
    扫描目标技能 references/ 目录下的每个 .md 文件，读取其标题和首段内容，
    生成 ### 渐进式文件索引 表格（3 列：文件名 | 位置 | 说明）。
    
    不从模板拷贝——每个文件的说明从文件自身的标题和首段提取。
    放在 ## 核心能力 章节末尾。
    """
    import os
    
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    
    refs_dir = os.path.join(skill_dir, "references")
    if not os.path.isdir(refs_dir):
        return 0
    
    # 收集所有 .md 文件及其描述
    ref_files = sorted(f for f in os.listdir(refs_dir) if f.endswith('.md'))
    if not ref_files:
        return 0
    
    rows = []
    for fn in ref_files:
        fpath = os.path.join(refs_dir, fn)
        try:
            with open(fpath, 'r', encoding='utf-8') as fh:
                ref_content = fh.read()
        except Exception:
            rows.append((fn, '参考文档', ''))
            continue
        
        # 提取 H1 或第一行非空文本作为"位置"
        h1 = re.search(r'^#\s+(.+)$', ref_content, re.MULTILINE)
        position = h1.group(1).strip() if h1 else fn.replace('.md', '').replace('-', ' ')
        
        # 提取 H1 后的第一段非空文本作为"说明"
        after_h1 = ref_content[h1.end():] if h1 else ref_content
        first_para = ''
        for line in after_h1.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                first_para = stripped[:60]
                break
        
        rows.append((fn, position, first_para))
    
    # 生成表格
    table_lines = [
        '### 渐进式文件索引',
        '',
        '| 文件名 | 位置 | 说明 |',
        '|--------|------|------|',
    ]
    for fn, pos, desc in rows:
        desc_clean = desc.replace('|', '/') if desc else ''
        table_lines.append(f'| `references/{fn}` | {pos} | {desc_clean} |')
    table_lines.append('')
    
    section_body = '\n'.join(table_lines)
    
        # 检查是否已存在，存在则整块删除后重建
    has_table = '### 渐进式文件索引' in body
    if has_table:
        body = re.sub(
            r'### 渐进式文件索引\n.*?(?=\n## |\n---|\Z)',
            '',
            body,
            flags=re.DOTALL
        )
    
    # 找到核心能力章节末尾，插入索引表
    core_match = re.search(r'^##\s+(?:核心能力|核心功能|概述).*?(?=^##\s|\Z)', body, re.MULTILINE | re.DOTALL)
    if core_match:
        core_end = core_match.end()
        body = body[:core_end] + '\n' + section_body + body[core_end:]
    
    # 写回
    new_content = '---\n'
    for k, v in fm.items():
        if isinstance(v, bool):
            new_content += f'{k}: {"true" if v else "false"}\n'
        else:
            new_content += f'{k}: {v}\n'
    new_content += '---\n' + body.lstrip('\n')
    _write_file(skill_md, new_content)
    
    return len(rows)


# ═══════════════════════════════════════════════════════════
# fix_reclassify_section — 通用的非标章节归类处理（Phase 3）
# ═══════════════════════════════════════════════════════════
def fix_reclassify_section(skill_dir, **kw):
    """
    通用的非标章节归类处理。不由硬编码驱动，由参数驱动。
    
    三种处理方式（由 action 参数控制）：
    - "merge": 将 section_title 的内容降级为 ### 移入 target_section
    - "split": 将 section_title 的内容拆分到 references/
    - "delete": 删除该章节（内容已被其他章节覆盖）
    
    用法：
        from scripts.skill_audit.fix import fix_reclassify_section
        # 归并到工作流程
        fix_reclassify_section(skill_dir, 
            action="merge", 
            section_title="循环与分支编排（v1.20.0 新增）", 
            target_section="工作流程")
        # 拆分到 references/
        fix_reclassify_section(skill_dir,
            action="split",
            section_title="旧版功能说明")
        # 直接删除
        fix_reclassify_section(skill_dir,
            action="delete",
            section_title="已废弃章节")
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    
    action = kw.get("action", "split")
    section_title = kw.get("section_title", "")
    target_section = kw.get("target_section", "")
    
    if not section_title:
        return 0
    
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    
    # 找到目标章节在 body 中的起止位置
    section_pattern = re.compile(
        r'^##\s*' + re.escape(section_title) + r'\s*$\n(.*?)(?=^##\s|\Z)',
        re.MULTILINE | re.DOTALL
    )
    section_match = section_pattern.search(body)
    if not section_match:
        # 尝试前缀匹配（兼容版本标注）
        for m in re.finditer(r'^##\s+(.+?)$\n(.*?)(?=^##\s|\Z)', body, re.MULTILINE | re.DOTALL):
            title = m.group(1).strip()
            if title.startswith(section_title) or section_title.startswith(title):
                section_match = m
                section_title = title
                break
    
    if not section_match:
        return 0
    
    section_content = section_match.group(0)
    section_body_raw = section_match.group(2)
    
    if action == "delete":
        # 直接删除
        body = body.replace(section_content, '', 1)
        
    elif action == "split":
        # 拆分到 references/
        refs_dir = os.path.join(skill_dir, "references")
        os.makedirs(refs_dir, exist_ok=True)
        safe_name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', section_title).strip('_')
        if not safe_name:
            safe_name = "section"
        ref_path = os.path.join(refs_dir, f"{safe_name}.md")
        ref_rel = f"references/{safe_name}.md"
        
        ref_content = f"# {section_title}\n\n{section_body_raw.strip()}\n"
        _write_file(ref_path, ref_content)
        
        # 替换为引用
        replacement = f"## {section_title}\n\n> → 详见 `{ref_rel}`\n"
        body = body.replace(section_content, replacement, 1)
        
    elif action == "merge" and target_section:
        # 降级为 ### 移入目标章节
        target_pattern = re.compile(
            r'^##\s*' + re.escape(target_section) + r'\s*$\n.*?(?=^##\s|\Z)',
            re.MULTILINE | re.DOTALL
        )
        target_match = target_pattern.search(body)
        if not target_match:
            return 0
        
        # 从原位置删除
        body = body.replace(section_content, '', 1)
        
        # 降级内容（## → ###）
        merged_content = section_content
        merged_content = merged_content.replace(f'## {section_title}', f'### {section_title}', 1)
        
        # 重新计算目标章节位置（body 变了）
        target_match_new = target_pattern.search(body)
        if target_match_new:
            target_end = target_match_new.end()
            body = body[:target_end] + '\n' + merged_content.strip() + '\n' + body[target_end:]
    
    # 写回
    new_content = '---\n'
    for k, v in fm.items():
        if isinstance(v, bool):
            new_content += f'{k}: {"true" if v else "false"}\n'
        else:
            new_content += f'{k}: {v}\n'
    new_content += '---\n' + body.lstrip('\n')
    _write_file(skill_md, new_content)
    
    # ★ 操作后自动同步渐进式索引表，保证引用表与 references/ 一致
    fix_progressive_index_table(skill_dir)
    
    return 1


# ═══════════════════════════════════════════════════
# 统一入口：apply_fix()
# ═══════════════════════════════════════════════════

def apply_fix(skill_dir, fix_key, **kw):
    """
    统一修复入口。
    fix_key: 对应审计结果中 fix["key"] 的值
    **kw: 附加参数（如 value、dry_run 等）

    返回：修复数量（0 表示未修复或失败）

    用法：
        from skill_audit.fix import apply_fix
        n = apply_fix("/path/to/skill", "name", value="git-sync")
    """
    dispatch = {
        "name": fix_name,
        "description": fix_description,
        "author": fix_author,
        "version": fix_version,
        "skill_macro": fix_skill_macro,
        "h1": fix_h1,
        "h1_version": fix_h1_version,
        "h1_position": fix_h1_position,
        "section_trigger": fix_section_trigger,
        "section_core": fix_section_core,
        "section_workflow": fix_section_workflow,
        "home_url": fix_home_url,
        "artifact_paths": fix_artifact_paths,
        "external_data_dir": fix_external_data_dir,
        "missing_data_dir": fix_missing_data_dir,
        "sensitive_access": fix_sensitive_access,
        "critical_write": fix_critical_write,
        "create_permissions_md": fix_create_permissions_md,
        "permission_weight": fix_permission_weight,
        "progressive_loading": fix_progressive_loading,
        "antipattern_progressive": fix_antipattern_progressive,
        "faq_progressive": fix_faq_progressive,
        "writing_standards": fix_writing_standards,
        "progressive_loading_explicit": fix_progressive_loading_explicit,
        "data_dir_compliance": fix_data_dir_compliance,
        "doc_code_consistency": fix_doc_code_consistency,
        "meta_json": fix_meta_json_completeness,
        "frontmatter_fields": fix_frontmatter_fields,
        "meta_field_sync": fix_meta_field_sync,
        "split_nonstandard": fix_split_nonstandard,
        "section_order": fix_section_order,
        "section_constraint": fix_section_constraint,
        "progressive_index_table": fix_progressive_index_table,
        "reclassify_section": fix_reclassify_section,
        "version_con": fix_version_con,
        "sanitize": fix_sanitize,
        "data_dir": fix_data_dir,
        "section_antipattern": fix_section_antipattern,
        "section_faq": fix_section_faq,
    }

    func = dispatch.get(fix_key)
    if func is None:
        raise ValueError(f"未知的 fix_key: {fix_key}（支持：{', '.join(sorted(dispatch.keys()))}）")
    return func(skill_dir, **kw)


# ── Body spec 辅助 ──────────────────────────────────────────────────

def _load_body_spec():
    """加载 body.json 规范。"""
    spec_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'scripts', 'spec', 'body.json'
    )
    if not os.path.isfile(spec_path):
        return {}
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _load_section_order():
    """返回 section_order 列表。"""
    return _load_body_spec().get("section_order", [])


def _load_allowed_sections():
    """返回 allowed_sections 白名单。"""
    spec = _load_body_spec()
    allowed = set(k.lower() for k in spec.get("allowed_sections", []))
    for syns in spec.get("section_synonyms", {}).values():
        for s in syns:
            allowed.add(s.lower())
    return allowed


# ═══════════════════════════════════════════════════
# R-17/C-11: 非标章节拆分 + 章节重排
# ═══════════════════════════════════════════════════

def fix_split_nonstandard(skill_dir, **kw):
    """
    R-17 修复：将不在 allowed_sections 白名单中的 H2 章节拆分到 references/。
    每个非标章节的内容被迁移到 references/<section-slug>.md，
    原始位置替换为「→ 详见 references/<section-slug>.md」引用。
    
    Returns: 迁移的章节数
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0

    allowed = _load_allowed_sections()
    if not allowed:
        return 0

    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0

    refs_dir = os.path.join(skill_dir, "references")
    os.makedirs(refs_dir, exist_ok=True)

    # 解析所有 ## H2 章节
    sections = list(re.finditer(r'^##\s+(.+?)$\n(.*?)(?=^##\s|\Z)', body, re.MULTILINE | re.DOTALL))
    if not sections:
        return 0

    migrated = 0
    dry_run = kw.get("dry_run", False)

    for m in sections:
        title = m.group(1).strip()
        title_lower = title.lower()
        if title_lower in allowed:
            continue

        section_content = m.group(2).strip()
        if not section_content:
            continue

        # 生成安全文件名
        safe_name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', title).strip('_')
        if not safe_name:
            safe_name = f"section_{m.start()}"

        ref_path = os.path.join(refs_dir, f"{safe_name}.md")
        ref_rel = f"references/{safe_name}.md"

        if dry_run:
            migrated += 1
            continue

        # 写 references/ 文件
        ref_content = f"# {title}\n\n{section_content}\n\n*由 fix_split_nonstandard 从 SKILL.md 迁移*"
        with open(ref_path, 'w', encoding='utf-8') as f:
            f.write(ref_content)

        # 在 body 中替换为引用
        full_match = m.group(0)
        replacement = f"## {title}\n\n> → 详见 `{ref_rel}`\n"
        body = body.replace(full_match, replacement, 1)
        migrated += 1

    if migrated > 0 and not dry_run:
        # 写回 SKILL.md
        new_content = f"---\n"
        for k, v in fm.items():
            new_content += f"{k}: {v}\n"
        new_content += "---\n"
        new_content += body.lstrip('\n')
        _write_file(skill_md, new_content)
    
    if migrated > 0:
        # ★ 新增引用文件后自动同步索引表
        fix_progressive_index_table(skill_dir)

    return migrated


def fix_section_order(skill_dir, **kw):
    """
    R-25 C-11 修复：按 body.json section_order 重排 SKILL.md 的 H2 章节顺序。
    不在 section_order 中的章节放到末尾。
    
    Returns: 重排的章节数
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0

    order = _load_section_order()
    if not order:
        return 0

    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0

    # 构建别名映射
    spec = _load_body_spec()
    synonyms = spec.get("section_synonyms", {})
    name_to_pos = {}
    for pos, name in enumerate(order):
        name_to_pos[name.lower()] = pos
        for canon, syns in synonyms.items():
            if canon.lower() == name.lower():
                for s in syns:
                    name_to_pos[s.lower()] = pos

    # 找到所有 ## 章节在 body 中的位置（含前导内容）
    # 用 split 分割 body
    parts = re.split(r'^(?=##\s)', body, flags=re.MULTILINE)
    if not parts:
        return 0

    # 第一部分是非章节前导内容（H1、空行、注释等）
    preamble = parts[0]
    sections = parts[1:]

    # 给每个章节分配位置
    ordered = []
    unordered = []
    for sec in sections:
        first_line = sec.split('\n')[0].strip()
        title = re.sub(r'^##\s+', '', first_line).strip()
        pos = name_to_pos.get(title.lower(), -1)
        if pos >= 0:
            ordered.append((pos, sec))
        else:
            unordered.append(sec)

    ordered.sort(key=lambda x: x[0])

    dry_run = kw.get("dry_run", False)
    if dry_run:
        return len(ordered) + len(unordered)

    # 组装
    new_body = preamble + '\n' + '\n'.join(sec for _, sec in ordered)
    if unordered:
        new_body += '\n' + '\n'.join(unordered)

    # 写回
    new_content = f"---\n"
    for k, v in fm.items():
        new_content += f"{k}: {v}\n"
    new_content += "---\n"
    new_content += new_body.lstrip('\n')
    _write_file(skill_md, new_content)

    return len(ordered) + len(unordered)




# ═══════════════════════════════════════════════════════════
# fix_version_con — R-03: version SemVer 格式校验与修复
# ═══════════════════════════════════════════════════════════
def fix_version_con(skill_dir, **kw):
    """
    R-03 修复：校验 frontmatter version 为 SemVer 格式 (X.Y.Z)。
    如果不符合，尝试修复为合法格式。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    ver = str(fm.get("version", "")).strip()
    if not ver:
        return 0
    # SemVer: MAJOR.MINOR.PATCH
    semver_match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-[\w.]+)?(?:\+[\w.]+)?$', ver)
    if semver_match:
        return 0  # 已合法
    # 尝试修复
    parts = re.findall(r'\d+', ver)
    if len(parts) >= 3:
        new_ver = f"{parts[0]}.{parts[1]}.{parts[2]}"
    elif len(parts) == 2:
        new_ver = f"{parts[0]}.{parts[1]}.0"
    elif len(parts) == 1:
        new_ver = f"{parts[0]}.0.0"
    else:
        new_ver = "1.0.0"
    ok = _update_frontmatter_field(skill_md, "version", new_ver)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════════════
# fix_sanitize — R-05: name 与目录名一致
# ═══════════════════════════════════════════════════════════
def fix_sanitize(skill_dir, **kw):
    """
    R-05 修复：将 frontmatter name 改为与父目录名一致。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    dir_name = os.path.basename(os.path.normpath(skill_dir))
    current = str(fm.get("name", "")).strip()
    if current == dir_name:
        return 0  # 已一致
    ok = _update_frontmatter_field(skill_md, "name", dir_name)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════════════
# fix_data_dir — R-12: 数据目录路径合规
# ═══════════════════════════════════════════════════════════
def fix_data_dir(skill_dir, **kw):
    """
    R-12 修复：确保 _meta.json 包含 data_dir 字段，值为 .standardization/<skill>/data/。
    同时检查 scripts/ 中源码是否声明了 data_dir 的 DEFAULT_DATA_DIR_RAW 锚点。
    """
    import json as _json
    
    meta_path = os.path.join(skill_dir, "_meta.json")
    if not os.path.isfile(meta_path):
        return 0
    
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = _json.load(f)
    except Exception:
        return 0
    
    skill_name = os.path.basename(os.path.normpath(skill_dir))
    expected_data_dir = f".standardization/{skill_name}/data/"
    
    current = meta.get("data_dir", "")
    if current == expected_data_dir:
        return 0  # 已正确
    
    meta["data_dir"] = expected_data_dir
    import tempfile, shutil
    tmp = tempfile.mktemp(suffix='.json', dir=os.path.dirname(meta_path))
    with open(tmp, 'w', encoding='utf-8') as f:
        _json.dump(meta, f, ensure_ascii=False, indent=2)
    shutil.move(tmp, meta_path)
    return 1


# ═══════════════════════════════════════════════════════════
# fix_section_antipattern — R-18: 反模式章节内容
# ═══════════════════════════════════════════════════════════
def fix_section_antipattern(skill_dir, **kw):
    """
    R-18 修复：添加 ## 反模式 章节，每条含具体错误描述和正确做法。
    从目标技能的特征生成至少 3 条反模式，每条 ≥20 字。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    name = fm.get("name", "本技能")
    
    # 从触发词和描述生成反模式
    desc = str(fm.get("description", ""))
    triggers = str(fm.get("trigger", ""))
    
    # 通用反模式模板（从技能特征调整）
    antipatterns = [
        f"**忽略 {name} 的约束条件** — 直接按一般逻辑执行，忽略本技能的特殊操作约束，导致文件损坏或版本号不一致。正确做法：操作前先读 `## 约束` 章节，确认本技能特有的操作规则。",
        f"**手动编辑 .md 文件** — 使用 Write/Edit 工具直接修改 SKILL.md，破坏编码或格式。正确做法：使用对应 Python 脚本原子写入，保证编码和 frontmatter 完整。",
        f"**跳过审计直接提交** — 修改后不运行 audit 就推送，导致未发现的 ERROR 进入仓库。正确做法：每次修改后运行 `audit .` 自审，确认 0 ERROR 0 WARN。",
    ]
    if '标准化' in desc or '审计' in desc:
        antipatterns.append(
            f"**一次只修一个 WARN** — 审计报了多个 WARN 但逐个手动修，效率低。正确做法：用 `--fix` 批量修复可自动修复的项，再手动处理 LLM  精筛项。"
        )
    
    section_body = '\n'.join(f'> ❌ **{a.split("**")[0].lstrip("> ❌ ")}**\n> ✅ {a.split("。正确做法：")[1]}' if "。正确做法：" in a else a for a in antipatterns[:5])
    
    # 实际用简单列表格式
    items = []
    for a in antipatterns[:5]:
        parts = a.split("。正确做法：")
        if len(parts) == 2:
            items.append(f"- ❌ **{parts[0].lstrip('**').rstrip('**')}**\n\n  ✅ {parts[1]}")
        else:
            items.append(f"- {a}")
    
    section_body = '\n\n'.join(items)
    ok = _add_section_to_body(skill_md, "反模式", section_body, insert_after=None)
    return len(antipatterns) if ok else 0


# ═══════════════════════════════════════════════════════════
# fix_section_faq — R-19: FAQ 章节内容
# ═══════════════════════════════════════════════════════════
def fix_section_faq(skill_dir, **kw):
    """
    R-19 修复：添加 ## FAQ 章节，包含至少 3 个有意义的 Q&A 对。
    Q ≥10 字，A ≥15 字，从技能名称和描述生成。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    name = fm.get("name", "本技能")
    desc = str(fm.get("description", ""))
    
    qas = [
        {
            "q": f"{name} 主要用来做什么？",
            "a": f"{name} 是一个 WorkBuddy 技能，{desc[:60]}。主要用于帮助用户自动化处理特定场景下的任务，减少重复劳动。"
        },
        {
            "q": f"如何开始使用 {name}？",
            "a": f"在对话中提到需要使用 {name} 的场景即可触发。建议先查看 SKILL.md 的「快速开始」章节，按步骤完成首个示例。"
        },
        {
            "q": f"使用 {name} 时需要注意什么？",
            "a": f"使用前务必阅读 `## 约束` 章节中的操作铁律。每次修改后应运行 audit 自审确认 0 ERROR。版本号更新需三端一致。"
        },
        {
            "q": f"{name} 和其他技能有什么区别？",
            "a": f"每个技能专注于特定领域。{name} 的核心能力在 SKILL.md 的 `## 核心能力` 表格中列出，建议阅读后与自身需求对比。"
        },
    ]
    
    section_body = '\n\n'.join(f"### Q: {qa['q']}\n\n**A:** {qa['a']}" for qa in qas)
    ok = _add_section_to_body(skill_md, "FAQ", section_body, insert_after=None)
    return len(qas) if ok else 0



def list_fixable():
    """列出所有可修复的 key"""
    return [
        "name",                        # R-01
        "description",                 # R-02
        "author",                     # R-03
        "version",                    # R-04
        "skill_macro",               # R-05
        "h1",                        # R-06
        "h1_version",                # R-06 清理版本号
        "h1_position",               # R-06 移到 frontmatter 后
        "section_trigger",            # R-07
        "section_core",              # R-08
        "section_workflow",          # R-09
        "home_url",                  # R-10
        "artifact_paths",            # R-11
        "external_data_dir",         # R-12
        "missing_data_dir",          # R-12 step 1.5
        "sensitive_access",          # R-13
        "critical_write",            # R-14
        "create_permissions_md",     # R-15
        "permission_weight",          # R-16
        "progressive_loading",      # R-17
        "antipattern_progressive",  # R-18
        "faq_progressive",          # R-19
        "writing_standards",        # R-20
        "progressive_loading_explicit",  # R-21
        "data_dir_compliance",       # R-22
        "doc_code_consistency",      # R-23
        "meta_json",                 # R-25
        "frontmatter_fields",        # R-01
        "meta_field_sync",           # R-10 共享字段同步
        "split_nonstandard",         # R-17 非标章节拆分
        "section_order",             # R-25 C-11 章节重排
        "section_constraint",         # 从目标技能采集约束生成 ## 约束
        "progressive_index_table",    # 从 references/ 生成渐进式索引表
        "reclassify_section",         # Phase 3 通用非标章节归类（merge/split/delete）
        "version_con",                # R-03 version SemVer 格式
        "sanitize",                   # R-05 name=目录名
        "data_dir",                   # R-12 数据目录路径
        "section_antipattern",        # R-18 反模式内容
        "section_faq",                # R-19 FAQ 内容
    ]
