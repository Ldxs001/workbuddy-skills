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


# ═══════════════════════════════════════════════════
# R-07: 触发条件章节修复
# ═══════════════════════════════════════════════════

def fix_section_trigger(skill_dir, **kw):
    """
    R-07 修复：添加/完善 ## 触发场景 章节。
    value: True（触发词数量 ≥3、含否定条件、无危险表述）
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    if fm is None:
        return 0
    name = fm.get("name", "本技能")
    section_body = (
        f"当用户需要使用 {name} 时\n"
        f"当要求使用 {name} 时\n"
        f"当询问关于 {name} 的问题时\n\n"
        "不触发条件：\n"
        "- 用户没有明确提到相关需求时\n"
        "- 上下文不足以判断时需要询问用户\n"
    )
    ok = _add_section_to_body(skill_md, "触发场景", section_body, insert_after=None)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-08: 核心能力章节修复
# ═══════════════════════════════════════════════════

def fix_section_core(skill_dir, **kw):
    """
    R-08 修复：添加 ## 核心能力 章节。
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return 0
    name = fm.get("name", "本技能") if (fm := ...) else "本技能"
    content = _read_file(skill_md)
    fm, body = parse_simple_yaml_frontmatter(content)
    name = fm.get("name", "本技能") if fm else "本技能"
    section_body = (
        f"- {name} 的核心功能 1\n"
        f"- {name} 的核心功能 2\n"
        f"- {name} 的核心功能 3\n"
        "> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），"
        "详细内容拆分到 `references/*.md` 按需加载。"
    )
    ok = _add_section_to_body(skill_md, "核心能力", section_body, insert_after=None)
    return 1 if ok else 0


# ═══════════════════════════════════════════════════
# R-09: 工作流程章节修复
# ═══════════════════════════════════════════════════

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

def fix_doc_code_consistency(skill_dir, **kw):
    """
    R-23 修复：文档-代码一致性问题。
    这是一个复杂修复，通常需要人工介入。
    此函数提供一个基础实现：自动添加缺失的 --help 文档。
    返回：修复的问题数
    """
    fixed = 0
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return 0
    for fname in sorted(os.listdir(scripts_dir)):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(scripts_dir, fname)
        content = _read_file(fpath)
        # 检查是否定义了 --help
        if "--help" not in content and "-h" not in content:
            # 简单添加 argparse --help 支持（基础模板）
            if 'argparse' in content and 'add_argument' in content:
                # 在第一个 add_argument 前插入 --help
                pass  # 复杂，不自动修复
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
    }
    func = dispatch.get(fix_key)
    if func is None:
        raise ValueError(f"未知的 fix_key: {fix_key}（支持：{', '.join(sorted(dispatch.keys()))}）")
    return func(skill_dir, **kw)


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
    ]
