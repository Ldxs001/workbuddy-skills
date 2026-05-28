#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_data_dir_paths.py
修复所有 .py 中的 DATA_DIR_RAW / DEFAULT_DATA_DIR_RAW 定义：
  - 去掉 'skills/' 前缀（'..' 已经到 skills/）
  - 去掉 '/data/' 后缀（data/ 是子目录，不是根目录）
  - 与 SILL.md frontmatter 的 data_dir: 声明对齐
新值：'.standardization/skill-standardization/'
"""
import os, re, sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = ".standardization/skill-standardization/"

# 需要修复的文件和对应的变量名
TARGET_FILES = {
    "safe_io.py":           ("DATA_DIR_RAW",        TARGET),
    "op_logger.py":         ("DEFAULT_DATA_DIR_RAW", TARGET),
    "skill_rollback.py":    ("DEFAULT_DATA_DIR_RAW", TARGET),
}

def fix_file(filepath, var_name, new_val):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 匹配：VAR_NAME = "xxx"  或  VAR_NAME = 'xxx'
    pattern = re.compile(
        r'(^[ \t]*' + re.escape(var_name) + r'[ \t]*=[ \t]*)(["\'])(.*?)\2',
        re.MULTILINE
    )

    new_content, n = pattern.subn(
        lambda m: f'{m.group(1)}{m.group(2)}{new_val}{m.group(2)}',
        content
    )

    if n == 0:
        print(f"  [SKIP] {os.path.basename(filepath)}: 未找到 {var_name} = ... 模式")
        return False

    # 原子写入
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(filepath), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(new_content)
    os.replace(tmp, filepath)
    print(f"  [OK] {os.path.basename(filepath)}: {var_name} = '{new_val}'")
    return True

def main():
    print("修复 DATA_DIR_RAW 定义 ...")
    print(f"  目标值: '{TARGET}'\n")
    ok = 0
    for fname, (var_name, new_val) in TARGET_FILES.items():
        fpath = os.path.join(SKILL_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [WARN] 文件不存在: {fname}")
            continue
        if fix_file(fpath, var_name, new_val):
            ok += 1
    print(f"\n完成: {ok}/{len(TARGET_FILES)} 个文件已修复")

    # 验证 _data_dir_abs 计算是否正确
    print("\n验证 _data_dir_abs 计算 ...")
    sys.path.insert(0, SKILL_DIR)
    for mod_name in ["safe_io", "op_logger", "skill_rollback"]:
        try:
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            mod = __import__(mod_name, fromlist=["_data_dir_abs"])
            abs_path = mod._data_dir_abs
            expected_end = os.path.join(".standardization", "skill-standardization")
            if expected_end.replace("/", "\\") in abs_path or expected_end in abs_path:
                print(f"  [OK] {mod_name}._data_dir_abs = {abs_path}")
            else:
                print(f"  [WARN] {mod_name}._data_dir_abs 可能仍有问题: {abs_path}")
        except Exception as e:
            print(f"  [ERROR] 无法导入 {mod_name}: {e}")

if __name__ == "__main__":
    main()
