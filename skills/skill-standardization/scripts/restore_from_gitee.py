import urllib.request
import os

url = "https://gitee.com/[username-redacted]/workbuddy-skills/raw/main/skill-standardization/scripts/{filename}"
files = [
    "_apply_all_fixes.py",
    "_fix_r23.py",
    "add_R24.py",
    "find_z_final.py",
    "find_z_proper.py",
    "search_literal_z.py",
    "fix_all_remaining.py",
    "fix_data_dir.py",
    "fix_data_dir_paths.py",
    "fix_final.py",
    "fix_init.py",
    "fix_paths.py",
    "fix_safe_io.py",
    "fix_skill_md.py",
    "fix_utils_r24.py",
    "master_fix.py",
    "repair_r23.py",
    "repair_structure.py",
    "update_all_versions.py",
    "update_version.py",
    "update_version_v2_38_0.py",
]

for f in files:
    try:
        u = url.format(filename=f)
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            content = r.read().decode("utf-8")
        with open(f, "w", encoding="utf-8") as w:
            w.write(content)
        print(f"[OK] {f} ({len(content)} bytes)")
    except Exception as e:
        print(f"[FAIL] {f}: {e}")
