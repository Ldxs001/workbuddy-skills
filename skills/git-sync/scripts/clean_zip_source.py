#!/usr/bin/env python3
"""清理打包源目录中的残留文件（扫描产物、系统隐藏文件）
用法：python clean_zip_source.py <zip_source_dir>
"""
import os, sys, fnmatch

EXCLUDE_PATTERNS = [
    ".sensitive_scan_*.json",
    ".decisions.json",
    "._*",
    ".DS_Store",
    "Thumbs.db",
    "__pycache__",
    "*.pyc",
]

def should_delete(fname):
    for pat in EXCLUDE_PATTERNS:
        if "*" in pat:
            if fnmatch.fnmatch(fname, pat):
                return True
        else:
            if fname == pat:
                return True
    return False

def main():
    if len(sys.argv) < 2:
        print("用法: python clean_zip_source.py <dir>")
        sys.exit(1)
    target = sys.argv[1]
    if not os.path.isdir(target):
        print(f"目录不存在: {target}")
        sys.exit(1)
    deleted = 0
    for root, dirs, files in os.walk(target, topdown=True):
        # 清理文件
        for fname in files:
            if should_delete(fname):
                fpath = os.path.join(root, fname)
                try:
                    os.remove(fpath)
                    deleted += 1
                    print(f"  🗑️  已删除: {os.path.relpath(fpath, target)}")
                except Exception as e:
                    print(f"  ⚠️  删除失败 {fpath}: {e}")
        # 清理 __pycache__ 目录
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for d in dirs[:]:
            if d.startswith(".") and d in (".__pycache__",):
                dpath = os.path.join(root, d)
                import shutil
                try:
                    shutil.rmtree(dpath, ignore_errors=True)
                    deleted += 1
                except Exception:
                    pass
    print(f"  ✅ 清理完成，共删除 {deleted} 项")

if __name__ == "__main__":
    main()
