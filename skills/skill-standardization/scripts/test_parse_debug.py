import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from skill_audit.utils import parse_simple_yaml_frontmatter

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'SKILL.md'), 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 frontmatter 文本
fm_start = content.find('---')
if fm_start == -1:
    print("ERROR: No frontmatter start")
    sys.exit(1)
fm_text_start = fm_start + 4  # skip '---\n'
fm_end = content.find('\n---', fm_text_start)
if fm_end == -1:
    print("ERROR: No frontmatter end")
    sys.exit(1)
fm_text = content[fm_text_start:fm_end]
print(f"=== fm_text ({len(fm_text)} chars) ===")
print(repr(fm_text))
print()

result, body = parse_simple_yaml_frontmatter(content)
print(f"=== parse_simple_yaml_frontmatter result ({len(result)} fields) ===")
for k, v in result.items():
    print(f"  {k!r} = {v!r} (type: {type(v).__name__})")
print()
print("Missing fields:", [k for k in ['name','version','author','license','description','data_dir','sensitive_access','critical_write','permission_weight','artifact_paths','writing_standards'] if k not in result])
