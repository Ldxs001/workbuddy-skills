import re

fpath = "scripts/skill_audit/structure_checker.py"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the broken function def and fix it
# The problem: _BUILTINS block was inserted between def signature and body
# We need to remove the misplaced _BUILTINS and reinsert it inside the function body
new_lines = []
skip_until = -1
in_docstring = False
fixed = False

i = 0
while i < len(lines):
    line = lines[i]
    
    # Detect the broken section: _BUILTINS inside function signature
    if '_BUILTINS = {' in line and i > 0 and 'def check_doc_code_consistency' in lines[i-1]:
        # This is misplaced - skip these lines until we find 'filepath, content'
        # Actually, let's just rebuild from scratch - find function start and end of signature
        pass
    
    new_lines.append(line)
    i += 1

# Better approach: rewrite the function properly
content = "".join(lines)

# Fix: remove misplaced _BUILTINS block from between def and body
# The broken pattern:
# def check_doc_code_consistency(\n    # Filter out...\n    _BUILTINS = {...}\nfilepath, content, ...
# Should be:
# def check_doc_code_consistency(\n    filepath, content, ...):\n    """docstring"""\n    _BUILTINS = {...}

# Step 1: fix the function signature
broken = '''def check_doc_code_consistency(
    # Filter out Python builtins falsely matched as "functions/classes defined in skill"
    _BUILTINS = {
        "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",
        "ImportError", "FileNotFoundError", "KeyError", "IndexError",
        "RuntimeError", "AttributeError", "NameError",
    }
filepath, content, fm, body, **kw):'''

fixed_sig = '''def check_doc_code_consistency(
    filepath, content, fm, body, **kw):'''

if broken in content:
    content = content.replace(broken, fixed_sig)
    print("  Fixed function signature")
else:
    print("  WARNING: broken pattern not found, trying alternative fix...")
    # Try line-by-line fix
    pass

# Step 2: insert _BUILTINS inside the function body (after docstring)
# Find: """docstring..."""  then insert _BUILTINS after the docstring
docstring_end = '    """'
insert_block = '''
    # R-23: filter out Python builtins falsely matched as "functions/classes defined in skill"
    _BUILTINS = {
        "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",
        "ImportError", "FileNotFoundError", "KeyError", "IndexError",
        "RuntimeError", "AttributeError", "NameError",
    }
'''

# Only insert if not already present
if "_BUILTINS" not in content:
    # Find where to insert: after the docstring of check_doc_code_consistency
    # Look for the function and the line after its docstring
    lines2 = content.split('\n')
    result = []
    in_target_func = False
    docstring_closed = False
    inserted = False
    
    for j, l in enumerate(lines2):
        result.append(l)
        if 'def check_doc_code_consistency(' in l:
            in_target_func = True
        if in_target_func and not inserted:
            # Check if this line closes the docstring
            if docstring_closed:
                # Next non-empty line is where we insert
                if l.strip() and not l.strip().startswith('"""') and not l.strip().startswith('#'):
                    # Insert before this line
                    result = result[:-1]  # remove last line
                    result.append(insert_block.rstrip())
                    result.append(l)
                    inserted = True
                    continue
            if '"""' in l and l.strip().endswith('"""') and not l.strip() == '"""':
                docstring_closed = True
    
    if inserted:
        content = '\n'.join(result)
        print("  Inserted _BUILTINS filter inside function body")
    else:
        print("  WARNING: could not find insertion point, appending after docstring marker")
        # Fallback: just add after the docstring ends
        content = content.replace(
            '    验证 SKILL.md 中引用的脚本/文件/函数名真实存在。\n    """',
            '    验证 SKILL.md 中引用的脚本/文件/函数名真实存在。\n    """' + insert_block
        )

with open(fpath, "w", encoding="utf-8") as f:
    f.write(content)

print("  structure_checker.py: repair complete")
