import re, os

# Fix 1: changelog.md terminology
fpath = "references/changelog.md"
with open(fpath, "r", encoding="utf-8") as f:
    content = f.read()
replacements = [("用户可以设置", "用户可以配置"), ("请设置", "请配置"), ("可设置", "可配置"), ("已设置", "已配置")]
modified = False
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        modified = True
        print(f"  changelog.md: {old} -> {new}")
if modified:
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    print("  changelog.md: 术语已统一")
else:
    print("  changelog.md: 无需修改")

# Fix 2: structure_checker.py - filter builtins from R-23
fpath2 = "scripts/skill_audit/structure_checker.py"
with open(fpath2, "r", encoding="utf-8") as f:
    content2 = f.read()

# Check if builtins filter already exists
if "builtins" not in content2:
    # Find check_doc_code_consistency function and add builtins filter
    # Python builtins that might appear in SKILL.md docs
    builtins_filter = '''
    # Filter out Python builtins falsely matched as "functions/classes defined in skill"
    _BUILTINS = {
        "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",
        "ImportError", "FileNotFoundError", "KeyError", "IndexError",
        "RuntimeError", "AttributeError", "NameError",
    }
'''
    # Insert after the function definition line
    content2 = content2.replace(
        'def check_doc_code_consistency(',
        'def check_doc_code_consistency(' + builtins_filter
    )
    # Also filter them in the actual check logic
    content2 = content2.replace(
        'for name in mentioned_names:',
        'for name in mentioned_names:\n        if name in _BUILTINS:  # R-23: skip Python builtins\n            continue'
    )
    with open(fpath2, "w", encoding="utf-8") as f:
        f.write(content2)
    print("  structure_checker.py: added builtins filter for R-23")
else:
    print("  structure_checker.py: builtins filter already exists")
