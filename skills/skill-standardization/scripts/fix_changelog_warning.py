#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 changelog.md 术语不一致：移除 → 删除"""
from pathlib import Path
import os

fpath = Path(__file__).parent.parent / "references" / "changelog.md"
if not fpath.exists():
    print(f"[X] 未找到: {fpath}")
    raise SystemExit(1)

content = fpath.read_text(encoding="utf-8")
new_content = content.replace("移除", "删除")

if new_content == content:
    print("[INFO] 无需替换")
else:
    tmp = fpath.with_suffix(fpath.suffix + ".tmp")
    tmp.write_text(new_content, encoding="utf-8", newline="")
    os.replace(tmp, fpath)
    print("[OK] changelog.md 术语已统一为「删除」")

# 同时修复 SKILL.md 中引用已删除脚本的问题
skill_md = Path(__file__).parent.parent / "SKILL.md"
if skill_md.exists():
    content2 = skill_md.read_text(encoding="utf-8")
    if "repair_r20.py" in content2:
        # 替换为 safe_io.py 的说明
        new_content2 = content2.replace(
            "| `SKILL.md` 正文 | Python 正则替换 | `scripts/repair_r20.py` |",
            "| `SKILL.md` 正文 | Python 直接重建 | `scripts/safe_io.py` 的 `safe_write()` |"
        )
        if new_content2 != content2:
            tmp2 = skill_md.with_suffix(".tmp")
            tmp2.write_text(new_content2, encoding="utf-8", newline="")
            os.replace(tmp2, skill_md)
            print("[OK] SKILL.md 已移除对已删除脚本的引用")
        else:
            print("[INFO] SKILL.md 无需替换")
    else:
        print("[INFO] SKILL.md 未引用 repair_r20.py")
