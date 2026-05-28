#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_R24.py — 为 skill-standardization 增加 R-24 规则：
更新日志禁止直接在 SKILL.md（必须渐进到 references/changelog.md）
v2.38.6
"""
import os
import re

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
AUDIT_DIR = os.path.join(SCRIPTS_DIR, "skill_audit")

def patch_file(filepath, replacements):
    """替换文件中的多段文本"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    modified = content
    for old, new in replacements:
        if old not in modified:
            print(f"  [WARN] 未找到目标文本 in {os.path.basename(filepath)}")
            print(f"          snippet: {repr(old[:60])}")
            continue
        modified = modified.replace(old, new, 1)
        print(f"  [OK] patched {os.path.basename(filepath)}")
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(modified)

def main():
    print("=== 增加 R-24 规则：更新日志禁止直接在 SKILL.md ===")

    # ── 1. structure_checker.py：增加 check_changelog_progressive() ─────
    sc_path = os.path.join(AUDIT_DIR, "structure_checker.py")
    with open(sc_path, "r", encoding="utf-8") as f:
        sc_content = f.read()

    # 在文件头 docstring 增加 R-24
    old_doc = 'skill_audit/structure_checker.py — 正文结构检查函数 (R-06~R-09, R-18~R-21, R-23)'
    new_doc = 'skill_audit/structure_checker.py — 正文结构检查函数 (R-06~R-09, R-18~R-24)'
    sc_content = sc_content.replace(old_doc, new_doc, 1)

    # 在文件末尾（return R-23 之后）追加 R-24 函数
    r24_func = r'''
def check_changelog_progressive(filepath, content, fm, body, **kw):
    """
    R-24: 更新日志（changelog）禁止直接在 SKILL.md。
    必须在 references/changelog.md 中，SKILL.md 只保留引用。
    """
    import os
    skill_dir = kw.get("skill_dir", "")
    skill_md_dir = os.path.dirname(filepath) if filepath else ""

    # 检查 SKILL.md 正文是否含有"更新日志" / "changelog" / "变更记录"章节
    changelog_pattern = re.compile(
        r'^##\s*(更新日志|changelog|变更记录|更新记录|版本历史)',
        re.MULTILINE | re.IGNORECASE
    )
    m = changelog_pattern.search(body)
    if m:
        line_no = body[:m.start()].count('\n') + 1
        # 找到绝对行号
        fm_lines = content[:len(content) - len(body)].count('\n') if body else 0
        abs_line = fm_lines + line_no
        return {
            "passed": False,
            "detail": f"{filepath}:{abs_line} - R-24: 更新日志章节直接在 SKILL.md 中，必须移至 references/changelog.md",
            "fix": {
                "key": "changelog_progressive",
                "location": f"{filepath}:{abs_line}",
                "operation": "将更新日志章节移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
                "verification": "重新运行 audit_skill()，确认 R-24 passed"
            }
        }

    # 检查 SKILL.md 正文是否含有版本号+更新描述的混合段落（松散检测）
    # 匹配如 "v2.3.0\n- 更新..." 或 "## v2.3.0" 等模式
    loose_pattern = re.compile(
        r'^(#\s+v\d+\.\d+\.\d+|[·•]\s*v\d+\.\d+\.\d+|-.+v\d+\.\d+\.\d+)',
        re.MULTILINE
    )
    # 只检测 H2 及以上的版本号标题
    h2_version = re.compile(r'^##\s+v?\d+\.\d+\.\d+', re.MULTILINE)
    m2 = h2_version.search(body)
    if m2:
        line_no = body[:m2.start()].count('\n') + 1
        fm_lines = content[:len(content) - len(body)].count('\n') if body else 0
        abs_line = fm_lines + line_no
        return {
            "passed": False,
            "detail": f"{filepath}:{abs_line} - R-24: SKILL.md 中含版本号标题（疑似更新日志），必须移至 references/changelog.md",
            "fix": {
                "key": "changelog_progressive",
                "location": f"{filepath}:{abs_line}",
                "operation": "将版本更新记录移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
                "verification": "重新运行 audit_skill()，确认 R-24 passed"
            }
        }

    # 检查 references/changelog.md 是否存在（推荐但不强制）
    changelog_path = os.path.join(skill_md_dir, "references", "changelog.md")
    if skill_dir:
        changelog_path2 = os.path.join(skill_dir, "references", "changelog.md")
        if os.path.isfile(changelog_path2):
            changelog_path = changelog_path2

    if not os.path.isfile(changelog_path):
        return {
            "passed": True,   # SKILL.md 中没有更新日志，通过
            "detail": f"{filepath}:1 - R-24: SKILL.md 无更新日志章节（references/changelog.md 不存在，但 SKILL.md 也未含日志，通过）",
        }

    return {"passed": True,
            "detail": f"{filepath}:1 - R-24: 更新日志在 references/changelog.md 中（SKILL.md 无内嵌日志，通过）"}
'''
    # 在 R-23 return 之前插入 R-24 函数
    # 找到 R-23 函数末尾的 return {"passed": False, ...} 之后的空白处
    # 简单做法：在文件末尾（if __name__ 之前或文件末尾）追加
    if "def check_changelog_progressive" not in sc_content:
        sc_content = sc_content.rstrip() + "\n" + r24_func

    with open(sc_path, "w", encoding="utf-8", newline="") as f:
        f.write(sc_content)
    print(f"  [OK] structure_checker.py — 追加 check_changelog_progressive()")

    # ── 2. __init__.py：METHOD_MAP 增加 R-24 ─────────────────────
    init_path = os.path.join(AUDIT_DIR, "__init__.py")
    with open(init_path, "r", encoding="utf-8") as f:
        init_content = f.read()

    # 在 METHOD_MAP 增加 R-24 条目
    old_method = '    "check_doc_code_consistency": check_doc_code_consistency,'
    new_method = old_method + '\n    "check_changelog_progressive": check_changelog_progressive,'
    if old_method in init_content and "check_changelog_progressive" not in init_content:
        init_content = init_content.replace(old_method, new_method, 1)
        # 在 import 区增加导入
        old_import = '    check_doc_code_consistency,'
        new_import = old_import + '\n    check_changelog_progressive,'
        init_content = init_content.replace(old_import, new_import, 1)
        with open(init_path, "w", encoding="utf-8", newline="") as f:
            f.write(init_content)
        print(f"  [OK] __init__.py — METHOD_MAP + import 更新")
    else:
        print(f"  [SKIP] __init__.py — 已包含或找不到目标")

    # ── 3. utils.py：RULES 列表增加 R-24 ─────────────────────────
    utils_path = os.path.join(AUDIT_DIR, "utils.py")
    with open(utils_path, "r", encoding="utf-8") as f:
        utils_content = f.read()

    r24_rule = '''    {
        "id": "R-24",
        "name": "更新日志渐进加载",
        "severity": "W",
        "method": "check_changelog_progressive",
        "check": "更新日志必须放在 references/changelog.md，SKILL.md 只能有引用",
        "fixable": False,
    },
'''
    # 在 RULES 列表的 R-23 之后插入
    if '"id": "R-23"' in utils_content and '"id": "R-24"' not in utils_content:
        # 找到 R-23 条目末尾的 }, 之后插入
        # 简单做法：在 RULES = [ 之后找到最后一个条目后插入
        # 更稳健：在 RULES 列表的 ] 之前插入
        old_end = '    # ── 方法分派表 ───────────────────────────────────────'
        if old_end in utils_content:
            pass  # 不在此文件改，改 rules.md 和 progress_manager.py 即可
        print(f"  [INFO] utils.py RULES 列表需手动确认（在第 290 行附近）")

    # 直接改 utils.py 的 RULES 列表
    # 找到 R-23 条目，在其后插入 R-24
    old_r23_end = '        "fixable": False,\n    },'
    new_r23_end = old_r23_end + '\n' + r24_rule.strip() + '\n'
    if old_r23_end in utils_content and '"id": "R-24"' not in utils_content:
        utils_content = utils_content.replace(old_r23_end, new_r23_end, 1)
        with open(utils_path, "w", encoding="utf-8", newline="") as f:
            f.write(utils_content)
        print(f"  [OK] utils.py — RULES 列表增加 R-24")
    else:
        print(f"  [SKIP] utils.py — R-24 已存在或找不到 R-23 末尾")

    # ── 4. progress_manager.py：RULES_ORDER 和 RULES_NAMES 更新 ────
    pm_path = os.path.join(SCRIPTS_DIR, "skill_audit", "progress_manager.py")
    with open(pm_path, "r", encoding="utf-8") as f:
        pm_content = f.read()

    old_order = 'RULES_ORDER = [f"R-{i:02d}" for i in range(1, 24)]  # R-01 ~ R-23'
    new_order = 'RULES_ORDER = [f"R-{i:02d}" for i in range(1, 25)]  # R-01 ~ R-24'
    pm_content = pm_content.replace(old_order, new_order, 1)

    old_names_end = '    "R-23": "文档-代码一致性检查",\n}'
    new_names_end = '    "R-23": "文档-代码一致性检查",\n    "R-24": "更新日志渐进加载",\n}'
    pm_content = pm_content.replace(old_names_end, new_names_end, 1)

    with open(pm_path, "w", encoding="utf-8", newline="") as f:
        f.write(pm_content)
    print(f"  [OK] progress_manager.py — RULES_ORDER + RULES_NAMES 更新")

    # ── 5. rules.md：增加 R-24 铁律条目 ─────────────────────────
    rules_path = os.path.join(SKILL_DIR, "references", "rules.md")
    with open(rules_path, "r", encoding="utf-8") as f:
        rules_content = f.read()

    r24_section = r'''
---

## 铁律 7：更新日志渐进加载（R-24）

> 自 v2.38.6 起，更新日志（changelog）**禁止**直接写在 `SKILL.md` 正文中。

### 规则内容

- `SKILL.md` **不得**含有 `## 更新日志` / `## Changelog` / `## 变更记录` 等章节
- `SKILL.md` **不得**含有版本号标题（如 `## v2.3.0`）形式的更新记录
- 更新日志必须放在 `references/changelog.md` 中
- `SKILL.md` 中只能保留一行引用：
  ```
  → 详见 references/changelog.md
  ```

### 设计理由

- `SKILL.md` 是**入口文件**，应当保持精简（≤230 行）
- 更新日志会不断累积，直接写在 `SKILL.md` 会导致文件迅速膨胀
- 渐进式加载是 skill-standardization 的核心规范之一（R-17~R-21）

### 修复方法

1. 将 `SKILL.md` 中的更新日志章节移至 `references/changelog.md`
2. 在 `SKILL.md` 原位置替换为：`→ 详见 references/changelog.md`
3. 确认 `references/changelog.md` 格式规范（每条含版本号、日期、变更说明）

### 检查方法

- `structure_checker.py` 的 `check_changelog_progressive()` 函数
- 正则检测 `## 更新日志` / `## Changelog` / `## vX.Y.Z` 等模式
'''
    # 在文件末尾（最后一个 --- 之后）追加
    if '## 铁律 7' not in rules_content:
        rules_content = rules_content.rstrip() + "\n" + r24_section
        with open(rules_path, "w", encoding="utf-8", newline="") as f:
            f.write(rules_content)
        print(f"  [OK] rules.md — 增加铁律 7（R-24）")
    else:
        print(f"  [SKIP] rules.md — 铁律 7 已存在")

    # ── 6. SKILL.md：更新版本号 + 触发词覆盖 ───────────────────
    skill_md_path = os.path.join(SKILL_DIR, "SKILL.md")
    with open(skill_md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # 更新 version
    md_content = re.sub(r'^version:\s*\S+', 'version: 2.38.6', md_content, count=1, flags=re.MULTILINE)
    # 更新 H1 标题
    md_content = re.sub(r'^# skill-standardization v\S+', '# skill-standardization v2.38.6', md_content, count=1, flags=re.MULTILINE)
    # 触发词增加"更新日志"（如果尚未覆盖）
    if '更新日志' not in md_content and 'changelog' not in md_content.lower():
        # 在触发场景章节追加
        trigger_pattern = re.compile(r'(## 触发场景.*?)(?=\n## |\Z)', re.DOTALL)
        m = trigger_pattern.search(md_content)
        if m:
            additional = "\n- 当 AI 试图将更新日志直接写在 SKILL.md 中时（应渐进到 references/changelog.md）\n"
            md_content = md_content[:m.end()] + additional + md_content[m.end():]

    with open(skill_md_path, "w", encoding="utf-8", newline="") as f:
        f.write(md_content)
    print(f"  [OK] SKILL.md — 版本号更新为 v2.38.6")

    # ── 7. _meta.json：更新版本号 ─────────────────────────────
    meta_path = os.path.join(SKILL_DIR, "_meta.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    if isinstance(meta, dict):
        meta["version"] = "2.38.6"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  [OK] _meta.json — 版本号更新为 2.38.6")

    # ── 8. changelog.md：增加 v2.38.6 条目 ──────────────────
    try:
        import json
    except ImportError:
        pass
    cl_path = os.path.join(SKILL_DIR, "references", "changelog.md")
    with open(cl_path, "r", encoding="utf-8") as f:
        cl_content = f.read()

    new_entry = """## v2.38.6 (2026-05-28)

### 新增
- **R-24 规则**：更新日志禁止直接在 SKILL.md，必须渐进到 `references/changelog.md`
- `structure_checker.py` 新增 `check_changelog_progressive()` 函数
- `progress_manager.py` RULES_ORDER 扩展至 R-24

### 修复
- 无

### 变更
- SKILL.md 触发场景覆盖 R-24 场景

---

"""
    if "## v2.38.6" not in cl_content:
        cl_content = cl_content.replace("## v2.38.5", new_entry + "## v2.38.5", 1)
        with open(cl_path, "w", encoding="utf-8", newline="") as f:
            f.write(cl_content)
        print(f"  [OK] changelog.md — 增加 v2.38.6 条目")
    else:
        print(f"  [SKIP] changelog.md — v2.38.6 条目已存在")

    print("\n=== 完成 ===")
    print("下一步：运行 python scripts/run_audit.py audit . --fix 验证")

if __name__ == "__main__":
    main()
