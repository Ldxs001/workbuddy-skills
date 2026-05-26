#!/usr/bin/env python3
"""fix_skill_sub_final.py — 稳定修复 skill-sub 剩余规范问题"""
import re
from pathlib import Path

SKILL = Path(r"C:\Users\sm001\.workbuddy\skills\skill-sub")

def fix_cache_var():
    """R-12: skill_extractor.py 变量名 CACHE_DIR → _cache_dir"""
    p = SKILL / "scripts" / "skill_extractor.py"
    text = p.read_text(encoding="utf-8")
    
    # 只改赋值和引用，不改注释
    # CACHE_DIR = ...  →  _cache_dir = ...
    text = re.sub(r'(?m)^CACHE_DIR\s*=', '_cache_dir =', text)
    # cf = CACHE_DIR / ... → cf = _cache_dir /
    text = re.sub(r'CACHE_DIR\s*/', '_cache_dir /', text)
    # CACHE_DIR.mkdir(...) → _cache_dir.mkdir(...)
    text = re.sub(r'CACHE_DIR\.', '_cache_dir.', text)
    
    p.write_text(text, encoding="utf-8")
    print(f"✅ {p.name}: CACHE_DIR → _cache_dir")

def fix_frontmatter():
    """R-13/14/16: 补充 frontmatter 字段"""
    p = SKILL / "SKILL.md"
    text = p.read_text(encoding="utf-8")
    
    if "sensitive_access:" not in text:
        text = text.replace("external_data_dir: true\n", 
                       "external_data_dir: true\nsensitive_access: false\n")
    if "critical_write:" not in text:
        text = text.replace("sensitive_access: false\n",
                       "sensitive_access: false\ncritical_write: false\n")
    if "permission_weight:" not in text:
        text = text.replace("critical_write: false\n",
                       "critical_write: false\npermission_weight: LOW\n")
    
    p.write_text(text, encoding="utf-8")
    print("✅ SKILL.md: 补充 sensitive_access/critical_write/permission_weight")

def fix_r18_ref():
    """R-18: SKILL.md 添加 references/antipatterns.md 引用"""
    p = SKILL / "SKILL.md"
    text = p.read_text(encoding="utf-8")
    if "antipatterns.md" not in text:
        # 在 --- 结束后、第一个 ## 前插入引用
        text = re.sub(r'(?m)^---
\n', 
                       '---\n\n> 反模式详见 [references/antipatterns.md](../references/antipatterns.md)\n\n',
                       text, count=1)
        p.write_text(text, encoding="utf-8")
        print("✅ SKILL.md: 添加 antipatterns.md 引用")
    else:
        print("ℹ️ SKILL.md: antipatterns.md 引用已存在")

def clean_patch_script():
    """删除临时修复脚本"""
    p = SKILL / "scripts" / "patch_skill_extractor.py"
    if p.exists():
        p.unlink()
        print(f"🗑️ 删除临时脚本: {p.name}")

if __name__ == "__main__":
    fix_cache_var()
    fix_frontmatter()
    fix_r18_ref()
    clean_patch_script()
    print("\n✅ 所有修复完成")
