#!/usr/bin/env python3
"""合并根目录 CHANGELOG.md 到 references/changelog.md，删除根目录副本，
   并在 SKILL.md 和 guide.md 中加入文件修改约束"""

import os, re, shutil

skill_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
skill_md = os.path.join(skill_dir, 'SKILL.md')
guide_md = os.path.join(skill_dir, 'references', 'guide.md')
ref_changelog = os.path.join(skill_dir, 'references', 'changelog.md')
root_changelog = os.path.join(skill_dir, 'CHANGELOG.md')

# ========== 1. 合并根目录 CHANGELOG.md 到 references/changelog.md ==========
if os.path.exists(root_changelog) and os.path.exists(ref_changelog):
    with open(root_changelog, 'r', encoding='utf-8') as f:
        root_content = f.read()
    with open(ref_changelog, 'r', encoding='utf-8') as f:
        ref_content = f.read()

    # 从根目录 CHANGELOG.md 提取 [2.33.0]~[2.30.0] 条目（这些 ref 里没有）
    # 匹配 ## [x.y.z] - date 格式
    new_entries = re.findall(r'(##\s*\[\d+\.\d+\.\d+\].*?)(?=\n##\s*\[|$)', root_content, re.DOTALL)
    
    # 更简单的做法：提取根目录 CHANGELOG.md 中 v2.33.0 / v2.32.0 / v2.31.0 / v2.30.0 的条目
    needed_versions = ['2.33.0', '2.32.0', '2.31.0', '2.30.0']
    entries_to_add = []
    
    for ver in needed_versions:
        # 在 root_content 中找这个版本的段落
        pattern = rf'(##\s*\[{re.escape(ver)}\].*?)(?=\n##\s*\[|-\n##\s+\w|$)'
        m = re.search(pattern, root_content, re.DOTALL)
        if m:
            entries_to_add.append(m.group(1).strip())
    
    if entries_to_add:
        # 在 ref_changelog 的 --- 分隔线之后（第一个版本之前）插入新条目
        # references/changelog.md 格式：标题 + 引言 + --- + 版本条目
        # 找到第一个 ## v 的位置，在其前面插入
        ref_lines = ref_content.splitlines()
        insert_idx = None
        for i, line in enumerate(ref_lines):
            if re.match(r'^##\s+v?\d+\.\d+', line):
                insert_idx = i
                break
        
        if insert_idx is not None:
            # 格式转换：把 [2.33.0] - 2026-05-26 格式转为 ## v2.33.0 + 日期格式
            converted = []
            for entry in entries_to_add:
                # 提取版本号和日期
                vm = re.match(r'##\s*\[([\d.]+)\]\s*-\s*(\d{4}-\d{2}-\d{2})', entry)
                if vm:
                    v = vm.group(1)
                    d = vm.group(2)
                    # 转换条目格式
                    converted.append(f'\n---\n\n## v{v}\n\n{d}\n')
                    # 提取 ### 新增/修改/修复/移除 内容
                    sections = re.split(r'\n###\s+', entry)
                    for sec in sections[1:]:  # 跳过版本标题部分
                        sec_title = sec.split('\n', 1)[0].strip()
                        sec_body = sec.split('\n', 1)[1] if '\n' in sec else ''
                        converted.append(f'### {sec_title}\n\n{sec_body.strip()}\n')
            
            # 插入到 ref_lines
            new_ref_lines = ref_lines[:insert_idx] + [''] + converted + ['', '---', ''] + ref_lines[insert_idx:]
            
            with open(ref_changelog + '.tmp', 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_ref_lines))
            os.replace(ref_changelog + '.tmp', ref_changelog)
            print(f'OK: {ref_changelog} 已合并 {len(entries_to_add)} 个新版本条目')
        else:
            print('WARN: 在 references/changelog.md 中找不到插入位置')
    else:
        print('INFO: 没有需要合并的新版本条目')

    # 删除根目录 CHANGELOG.md
    os.remove(root_changelog)
    print(f'OK: 已删除根目录 {root_changelog}')
else:
    print('INFO: 根目录 CHANGELOG.md 不存在，跳过合并')

# ========== 2. 在 SKILL.md 加入「⚠️ 文件修改约束」章节 ==========
with open(skill_md, 'r', encoding='utf-8') as f:
    content = f.read()

constraint_section = """
## ⚠️ 文件修改约束

> **本技能的所有 `.md` 文件禁止使用 Write/Edit 工具修改（会损坏 UTF-8 中文编码）。**
> 必须用 `scripts/` 下的 Python 脚本原子写入（`tmp + os.replace()`）。

| 文件 | 修改方式 | 脚本 |
|------|----------|------|
| `SKILL.md` frontmatter | Python 原子写入 | `scripts/update_skill_frontmatter.py` |
| `SKILL.md` 正文 | Python 正则替换 | `scripts/fix_progressive_loading.py` |
| `references/*.md` | `scripts/safe_io.py` 的 `safe_write()` | 随技能自带 |
| `CHANGELOG.md` | Python 合并脚本 | 每次发版统一维护 `references/changelog.md` |

**检查清单（每次修改前）**：
- [ ] 是否用了 Write/Edit 工具？→ 立刻停止，改用 Python 脚本
- [ ] 是否在 `references/changelog.md` 维护变更记录？→ 根目录不得有 `CHANGELOG.md`
- [ ] 修改后是否用 `python -m scripts.skill_audit audit .` 自审？→ 必须 0 ERROR 0 WARN
"""

if '⚠️ 文件修改约束' not in content:
    # 插入到「## 触发场景」之前
    content = content.replace('\n## 触发场景\n', constraint_section + '\n## 触发场景\n', 1)
    
    with open(skill_md + '.tmp', 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(skill_md + '.tmp', skill_md)
    print(f'OK: {skill_md} 已加入「⚠️ 文件修改约束」章节')
else:
    print('INFO: SKILL.md 已有约束章节，跳过')

# ========== 3. 在 references/guide.md 工作流程中加入同样约束 ==========
if os.path.exists(guide_md):
    with open(guide_md, 'r', encoding='utf-8') as f:
        guide_content = f.read()
    
    guide_constraint = """> **⚠️ 文件修改约束**：修改 `SKILL.md` 或 `references/*.md` 时，**严禁使用 Write/Edit 工具**（会损坏 UTF-8 编码）。必须使用 `scripts/` 下的 Python 脚本原子写入（`open(tmp)+os.replace()`）。修改后必须自审 0 ERROR 0 WARN。\n\n"""
    
    if '⚠️ 文件修改约束' not in guide_content:
        # 插入到第一个 ### 标题之前
        guide_content = re.sub(r'(\n### )', guide_constraint + r'\1', guide_content, count=1)
        
        with open(guide_md + '.tmp', 'w', encoding='utf-8') as f:
            f.write(guide_content)
        os.replace(guide_md + '.tmp', guide_md)
        print(f'OK: {guide_md} 已加入文件修改约束')
    else:
        print('INFO: guide.md 已有约束，跳过')
else:
    print('WARN: references/guide.md 不存在')

print('\n=== 全部完成 ===')
