import re, os

# Fix 1: changelog.md - unify terminology (变更→更新)
fpath = "references/changelog.md"
with open(fpath, "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    ("- **修复", "- **更新"),
    ("- **变更", "- **更新"),
    ("修复：", "更新："),
    ("变更：", "更新："),
]
modified = False
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        modified = True
        print(f"  changelog.md: {old.strip()} -> {new.strip()}")

if modified:
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    print("  changelog.md: 术语已统一")
else:
    print("  changelog.md: 无需修改")

# Fix 2: structure_checker.py - _BUILTINS filter not working
# Find the real file containing check_doc_code_consistency
import glob
pyfiles = glob.glob("scripts/skill_audit/*.py")
target = None
for pf in pyfiles:
    with open(pf, "r", encoding="utf-8") as f:
        if "check_doc_code_consistency" in f.read():
            target = pf
            break

if target:
    print(f"  Found: {target}")
    with open(target, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Find the function and ensure _BUILTINS is defined AND used
    new_lines = []
    in_func = False
    func_indent = ""
    builtins_added = False
    filter_added = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detect function start
        if "def check_doc_code_consistency(" in line:
            in_func = True
            func_indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(line)
            i += 1
            continue
        
        # After docstring, insert _BUILTINS
        if in_func and not builtins_added:
            # Check if we're past the docstring
            stripped = line.strip()
            if stripped == '"""' or stripped.startswith('"""'):
                # Skip docstring end
                new_lines.append(line)
                i += 1
                if i < len(lines):
                    next_line = lines[i]
                    # Insert _BUILTINS here
                    indent = next_line[:len(next_line) - len(next_line.lstrip())]
                    new_lines.append(indent + "# R-23: filter Python builtins falsely matched as skill-defined names\n")
                    new_lines.append(indent + "_BUILTINS = {\n")
                    new_lines.append(indent + '    "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",\n')
                    new_lines.append(indent + '    "ImportError", "FileNotFoundError", "KeyError", "IndexError",\n')
                    new_lines.append(indent + '    "RuntimeError", "AttributeError", "NameError",\n')
                    new_lines.append(indent + "}\n")
                    builtins_added = True
                    continue
                continue
            else:
                new_lines.append(line)
                i += 1
                continue
        
        # Fix the filter: ensure "if name in _BUILTINS: continue" exists
        if in_func and "for " in line and ("name" in line or "func" in line or "cls" in line):
            # This is the for loop - next lines should have _BUILTINS filter
            new_lines.append(line)
            i += 1
            # Check if next non-empty line has _BUILTINS filter
            j = i
            found_filter = False
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and "_BUILTINS" in lines[j]:
                found_filter = True
            if not found_filter:
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(indent + "    if name in _BUILTINS:  # R-23: skip Python builtins\n")
                new_lines.append(indent + "        continue\n")
            continue
        
        new_lines.append(line)
        i += 1
    
    with open(target, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"  {target}: _BUILTINS filter updated")
else:
    print("  ERROR: could not find check_doc_code_consistency function")

print("All fixes applied.")
