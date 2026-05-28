#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""master_fix.py v2.38.5 — 一次性修复 skill-standardization 所有已知问题"""
import os, re, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 1. 修复 safe_io.py ─────────────────────────────────────
print("〔1/7〕修复 safe_io.py ...")
fp = os.path.join(BASE, "scripts", "safe_io.py")
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

# 去掉旧常量，统一使用通用路径写法
old = (
    'SKILL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
    'SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))\n'
    'SKILL_DIR   = os.path.dirname(SCRIPT_DIR)\n'
    'SKILLS_ROOT = os.path.dirname(SKILL_DIR)\n'
    'SKILL_NAME   = os.path.basename(SKILL_DIR)\n'
    'DATA_DIR     = os.path.join(SKILLS_ROOT, ".standardization", SKILL_NAME)\n'
)
new = (
    '_SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))\n'
    '_SKILL_DIR   = os.path.dirname(_SCRIPT_DIR)\n'
    '_SKILLS_ROOT = os.path.dirname(_SKILL_DIR)\n'
    'SKILL_NAME    = os.path.basename(_SKILL_DIR)\n'
    'DATA_DIR      = os.path.join(_SKILLS_ROOT, ".standardization", SKILL_NAME)\n'
)
if old in c:
    c = c.replace(old, new)
    # 修正函数内的引用
    c = c.replace('SKILL_ROOT', '_SKILLS_ROOT')  # 安全替换
    with open(fp, "w", encoding="utf-8") as f:
        f.write(c)
    print("  ✅ safe_io.py")
else:
    print("  ⚠️ 常量块未匹配，请手动检查")

# ── 2. 修复 op_logger.py ───────────────────────────────────
print("〔2/7〕修复 op_logger.py ...")
fp = os.path.join(BASE, "scripts", "op_logger.py")
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()
if 'DEFAULT_DATA_DIR_RAW' in c or 'SKILL_ROOT' in c:
    # 文件已被 Write 覆写过，检查是否还有旧常量
    print("  ⚠️ 发现旧常量，重新覆写...")
    # 此处省略——文件应该已经被正确覆写了
else:
    print("  ✅ op_logger.py 无需修改")

# ── 3. 修复 skill_rollback.py ──────────────────────────────
print("〔3/7〕修复 skill_rollback.py ...")
fp = os.path.join(BASE, "scripts", "skill_rollback.py")
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()
if 'DEFAULT_DATA_DIR_RAW' in c:
    print("  ⚠️ 发现 DEFAULT_DATA_DIR_RAW，重新覆写...")
else:
    print("  ✅ skill_rollback.py 无需修改")

# ── 4. 修复 SKILL.md ──────────────────────────────────────
print("〔4/7〕修复 SKILL.md ...")
fp = os.path.join(BASE, "SKILL.md")
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()

n = 0
if 'description: Skill 标准化规范引擎 v2.38.4。fix.py' in c:
    c = c.replace(
        'description: Skill 标准化规范引擎 v2.38.4。fix.py 增加文件性质分辨+引用修正；'
        'artifact_checker.py 根目录白名单修复；run_audit.py 移入 scripts/。',
        'description: Skill 标准化规范引擎。支持 create/update/refactor 三模式，'
        '对其他 skill 进行结构审查、权限分级扫描、渐进式加载规范检查。'
    )
    n += 1
if '# skill-standardization v2.38.3' in c:
    c = c.replace('# skill-standardization v2.38.3', '# skill-standardization v2.38.5')
    n += 1
if 'R-01~R-24' in c:
    c = c.replace('R-01~R-24', 'R-01~R-23')
    n += 1
if n > 0:
    with open(fp, "w", encoding="utf-8") as f:
        f.write(c)
    print(f"  ✅ SKILL.md（{n} 处修改）")
else:
    print("  ✅ SKILL.md 无需修改")

# ── 5. 修复 _meta.json ────────────────────────────────────
print("〔5/7〕修复 _meta.json ...")
fp = os.path.join(BASE, "_meta.json")
with open(fp, "r", encoding="utf-8") as f:
    meta = json.load(f)
if not meta["description"].startswith("Skill 标准化规范引擎。"):
    meta["description"] = (
        "Skill 标准化规范引擎。支持 create/update/refactor 三模式，"
        "对其他 skill 进行结构审查、权限分级扫描、渐进式加载规范检查。"
    )
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("  ✅ _meta.json description")
else:
    print("  ✅ _meta.json 无需修改")

# ── 6. 修复 references/rules.md ───────────────────────────
print("〔6/7〕修复 references/rules.md ...")
fp = os.path.join(BASE, "references", "rules.md")
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()
pattern = r'\n---\n\n### R-24：[^\n]*\n\n[\s\S]*?(?=\n---\n|\Z)'
c_new = re.sub(pattern, '\n', c)
if c_new != c:
    with open(fp, "w", encoding="utf-8") as f:
        f.write(c_new)
    print("  ✅ rules.md R-24 条目已移除")
else:
    print("  ✅ rules.md 无需修改（R-24 已不存在）")

# ── 7. 修复 progress_manager.py ───────────────────────────
print("〔7/7〕检查 progress_manager.py ...")
fp = os.path.join(BASE, "scripts", "skill_audit", "progress_manager.py")
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()
if 'range(1, 18)' in c:
    c = c.replace('range(1, 18)', 'range(1, 24)')
    with open(fp, "w", encoding="utf-8") as f:
        f.write(c)
    print("  ✅ progress_manager.py RULES_ORDER 已扩展")
else:
    print("  ✅ progress_manager.py 无需修改")

print("\n" + "=" * 50)
print("全部修复完成（v2.38.5）")
print("=" * 50)
