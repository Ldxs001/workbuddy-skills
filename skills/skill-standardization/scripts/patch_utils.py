#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_utils.py — 精确在 utils.py RULES 列表末尾（] 之前）插入 R-24 条目"""
import os

UTILS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "skill_audit", "utils.py"
)

with open(UTILS, "r", encoding="utf-8") as f:
    content = f.read()

R24 = '''    # ── 新增规则 R-24 (v2.38.6) ──────────────────────
    {
        "id": "R-24",
        "name": "更新日志渐进加载",
        "severity": "WARN",
        "method": "check_changelog_progressive",
        "check": "更新日志必须放在 references/changelog.md，SKILL.md 只能有引用",
        "fixable": False,
        "create_template": "将更新日志移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
    },
'''

# 在 RULES = [ 的闭合 ] 之前插入（即最后一个 }, 之后）
old_marker = '        "create_template": "确保 SKILL.md 引用的所有 .py 文件存在于技能目录中，代码示例中的调用方式与实际 argparse/函数签名一致",\n    },\n]'
new_marker = old_marker + '\n' + R24

if old_marker in content:
    content = content.replace(old_marker, new_marker, 1)
    with open(UTILS, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print("[OK] utils.py — RULES 列表增加 R-24")
else:
    print("[WARN] 未找到精确插入点，尝试在 ] 前插入")
    # 备用：在最后一个 }, 之后、] 之前插入
    import re
    m = re.search(r'(\},\n\])', content)
    if m:
        insert_pos = m.start(1) + len('},\n')
        new_content = content[:insert_pos] + R24 + content[insert_pos:]
        with open(UTILS, "w", encoding="utf-8", newline="") as f:
            f.write(new_content)
        print("[OK] utils.py — 备用方案插入 R-24")
    else:
        print("[ERROR] 无法找到插入位置")
