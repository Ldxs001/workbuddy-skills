"""Repair structure_checker.py - fix R-23 function"""
fpath = "scripts/skill_audit/structure_checker.py"
with open(fpath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the check_doc_code_consistency function
# Fix 1: ensure _BUILTINS is defined after docstring
# Fix 2: line 785 - change 'name' to 'ref'
new_lines = []
in_r23_func = False
past_docstring = False
docstring_close_found = False
builtins_inserted = False
i = 0

while i < len(lines):
    line = lines[i]
    
    # Detect function start
    if "def check_doc_code_consistency(" in line:
        in_r23_func = True
        new_lines.append(line)
        i += 1
        continue
    
    if in_r23_func and not builtins_inserted:
        stripped = line.strip()
        # Detect docstring end
        if not docstring_close_found:
            if stripped == '"""' or stripped.endswith('"""'):
                docstring_close_found = True
                new_lines.append(line)
                i += 1
                continue
            elif '"""' in stripped and not stripped.startswith('"""'):
                # inline docstring end
                docstring_close_found = True
                new_lines.append(line)
                i += 1
                continue
        
        # After docstring, insert _BUILTINS
        if docstring_close_found:
            # This is the first non-docstring line - insert _BUILTINS before it
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(indent + "# R-23: filter Python builtins falsely matched as skill-defined names\n")
            new_lines.append(indent + "_BUILTINS = {\n")
            new_lines.append(indent + '    "SyntaxWarning", "Warning", "Exception", "TypeError", "ValueError",\n')
            new_lines.append(indent + '    "ImportError", "FileNotFoundError", "KeyError", "IndexError",\n')
            new_lines.append(indent + '    "RuntimeError", "AttributeError", "NameError",\n')
            new_lines.append(indent + "}\n")
            new_lines.append("\n")
            builtins_inserted = True
            # fall through to append current line
    
    # Fix: 'name' -> 'ref' on the _BUILTINS check line
    if in_r23_func and "_BUILTINS" in line and "name" in line and "ref" not in line:
        line = line.replace("if name in _BUILTINS:", "if ref in _BUILTINS:")
    
    new_lines.append(line)
    
    # Also fix: if _BUILTINS was already defined but in wrong place, 
    # we still need to fix the 'name' -> 'ref' on line 785
    i += 1

# If _BUILTINS was never inserted (already exists somewhere), just fix name->ref
if not builtins_inserted:
    print("  _BUILTINS already exists, only fixing name->ref")
    new_lines2 = []
    for ln in new_lines:
        if "_BUILTINS" in ln and "name" in ln and "ref" not in ln:
            ln = ln.replace("if name in _BUILTINS:", "if ref in _BUILTINS:")
        new_lines2.append(ln)
    new_lines = new_lines2

with open(fpath, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("  structure_checker.py: R-23 repair complete")
