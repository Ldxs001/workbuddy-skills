import os
import re

p = 'C:/Users/sm001/.workbuddy/skills/skill-standardization/scripts/skill_audit/structure_checker.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We want to replace lines 756-763 (1-indexed) = indices 755-762
# Line 756: relevant_cmds = []
# Line 757: for cmd in all_commands:
# Line 758: # 命令中提及此脚本名（含路径）才检查
# Line 759: if script_basename in cmd ...
# Line 760:     relevant_cmds.append(cmd)
# Line 761: # DEBUG
# Line 762: import sys
# Line 763: print(f"[R-23 DEBUG] ...)

new_block = [
    '            relevant_cmds = []\n',
    '            for cmd in all_commands:\n',
    '                # 命令中提及此脚本名（含路径）才检查\n',
    "                if script_basename in cmd or script_path.replace('\\\\', '/') in cmd or script_path.replace('/', '\\\\') in cmd:\n",
    '                    # 按行拆分，只保留真正调用此脚本的命令行（避免整个代码块被当作一条命令）\n',
    '                    for _line in cmd.splitlines():\n',
    '                        _line = _line.strip()\n',
    "                        if _line.startswith('#'): continue\n",
    "                        if script_basename in _line or script_path.replace('\\\\', '/') in _line or script_path.replace('/', '\\\\') in _line:\n",
    '                            relevant_cmds.append(_line)\n',
]

# Replace lines 755-762 (indices) with new_block, keep the rest
new_lines = lines[:755] + new_block + lines[763:]

with open(p + '.tmp', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
os.replace(p + '.tmp', p)
print('OK: fixed relevant_cmds logic and removed DEBUG')
