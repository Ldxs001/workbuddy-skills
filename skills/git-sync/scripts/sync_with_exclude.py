#!/usr/bin/env python3
"""同步目录，应用与 pack_zip.py 一致的排除规则。
用法: python sync_with_exclude.py <src_dir> <dst_dir>
设计：替代 rsync 的排除同步，确保仓库文件与打包排除规则一致。
"""
import os
import sys
import shutil

from auth_check import initialize


# ── 排除规则（与 pack_zip.py 保持一致）──────────────────────────
EXCLUDE_DIRS = {
    "__pycache__", ".git", ".eggs", "eggs", "dist", "build",
    ".eggs-info", ".pytest_cache", ".mypy_cache", "node_modules",
    ".standardization", "outputs", "test-outputs",
}
EXCLUDE_FILES_EXACT = {
    ".gitignore", ".ds_store", "thumbs.db",
    "config.json", "manifest.json", "pack_zip.py",
}
EXCLUDE_FILES_GLOB = {
    "*.pyc", "*.pyo", "*.log", "*.zip", "*.bak*",
    "*.tmp", "._*", ".decisions.json",
    "*.sensitive_scan_*.json", "zip_out", "preview_server.py",
    "*_fixed.py", "stderr.txt", "stdout.txt",
}
FUNCTIONAL_FILE_WHITELIST = {"settings.html", "preview.html"}


def should_exclude(rel_path):
    """判断相对路径是否应被排除。"""
    import fnmatch

    p = rel_path.replace(os.sep, "/")
    name = os.path.basename(p)
    parent_dir = os.path.dirname(p)

    lower_name = name.lower()
    for w in FUNCTIONAL_FILE_WHITELIST:
        if lower_name == w.lower():
            return False

    parts = p.split("/")
    for part in parts[:-1]:
        if part.lower() in (d.lower() for d in EXCLUDE_DIRS):
            return True

    lower_exact = {f.lower() for f in EXCLUDE_FILES_EXACT}
    if name.lower() in lower_exact:
        if name.lower() in ("config.json", "manifest.json"):
            if parent_dir == "":
                return True
            else:
                return False
        return True

    for pat in EXCLUDE_FILES_GLOB:
        if fnmatch.fnmatch(name, pat):
            return True
        if fnmatch.fnmatch(p, pat):
            return True

    return False


def sync_with_exclude(src, dst):
    """用排除规则同步 src → dst（先清空 dst，再复制）"""
    src = os.path.normpath(src)
    dst = os.path.normpath(dst)

    if not os.path.isdir(src):
        print(f"❌ 源目录不存在: {src}")
        sys.exit(1)

    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(dst, exist_ok=True)

    copy_count = 0
    for root, dirs, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        rel_root = "" if rel_root == "." else rel_root

        if rel_root:
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]
        else:
            dirs[:] = [d for d in dirs if not should_exclude(d)]

        for fname in files:
            rel_path = os.path.join(rel_root, fname) if rel_root else fname
            if should_exclude(rel_path):
                continue
            src_file = os.path.join(root, fname)
            dst_file = os.path.join(dst, rel_path)
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            shutil.copy2(src_file, dst_file)
            copy_count += 1

    print(f"  ✅ Python 排除复制完成: {copy_count} 个文件")
    return copy_count


if __name__ == "__main__":
    initialize()
    if len(sys.argv) < 3:
        print("用法: python sync_with_exclude.py <src_dir> <dst_dir>")
        sys.exit(1)
    sync_with_exclude(sys.argv[1], sys.argv[2])