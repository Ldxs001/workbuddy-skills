import re

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Cannot read {filepath}: {e}")
        return False
    
    replacements = [
        ('\u274c', '[X]'),           # ❌
        ('\u2705', '[OK]'),        # ✅
        ('\u26a0\ufe0f', '[!]'),  # ⚠️
        ('\u26a0', '[!]'),          # ⚠
        ('\u1f527', '[fix]'),      # 🔧
        ('\u1f4c6', '[file]'),     # 📦
        ('\u1f4dd', '[search]'),   # 📍
        ('\u1f4a1', '[WARN]'),    # 🟡
        ('\u1f534', '[ERROR]'),   # 🔴
        ('\u2b50', '[PASS]'),      # ⭐
    ]
    
    original = content
    for old, new in replacements:
        content = content.replace(old, new)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    return False

# Fix the three files
base = '/c/Users/sm001/.workbuddy/skills/skill-standardization/scripts'
files = [
    f'{base}/skill_builder/refactor.py',
    f'{base}/skill_audit/__init__.py',
    f'{base}/skill_audit/artifact_checker.py',
]
for f in files:
    fix_file(f)
print('Encoding fix complete')
