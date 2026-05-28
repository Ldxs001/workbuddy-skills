import re

fpath = "scripts/skill_audit/__init__.py"
with open(fpath, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Add warnings filter at top of file (after shebang)
import_block = "# -*- coding: utf-8 -*-\n\"\"\""
warnings_addition = "# -*- coding: utf-8 -*-\nimport warnings\nwarnings.filterwarnings(\"ignore\", category=SyntaxWarning)\n\"\"\""
content = content.replace(import_block, warnings_addition)

# Fix 2: Handle tuple returns in audit_skill (line ~192)
# Replace the result.get() pattern to handle both dict and tuple
old_result_block = '''        passed = result.get("passed", False)
        skipped = result.get("skip", False)'''

new_result_block = '''        # 兼容 dict 和 tuple 两种返回格式
        if isinstance(result, dict):
            passed = result.get("passed", False)
            skipped = result.get("skip", False)
        elif isinstance(result, (tuple, list)) and len(result) >= 1:
            # 旧格式: (passed, details, fixable)
            passed = bool(result[0]) if len(result) > 0 else False
            skipped = result[2].get("skip", False) if len(result) > 2 and isinstance(result[2], dict) else False
            # 将 tuple 转为 dict 以便后续处理
            detail = result[1] if len(result) > 1 else ""
            fix = result[2] if len(result) > 2 and isinstance(result[2], dict) else None
            result = {"passed": passed, "detail": detail, "fix": fix}
        else:
            passed = False
            skipped = False'''

if old_result_block in content:
    content = content.replace(old_result_block, new_result_block)
    print("  Fixed: tuple return compatibility (audit_skill)")
else:
    print("  WARNING: Could not find result.get() block to patch")

with open(fpath, "w", encoding="utf-8") as f:
    f.write(content)

print("  __init__.py: fixes applied")
