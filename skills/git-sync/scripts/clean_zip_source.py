#!/usr/bin/env python3
from auth_check import authorize, initialize

"""清理打包源目录中的残留文件（扫描产物、系统隐藏文件）
用法：python clean_zip_source.py <zip_source_dir>
"""
import os, sys, fnmatch
import subprocess
import hashlib
import json

def normalize_path(p):
    """将路径规范化为 Windows 绝对路径（处理 Git Bash /c/... 格式）"""
    p = os.path.expanduser(p)
    if p.startswith("/") and len(p) > 2 and p[1].isalpha() and p[2] == "/":
        p = p[1].upper() + ":" + p[2:].replace("/", "\\")
    return os.path.normpath(p)

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
    target = normalize_path(sys.argv[1])
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
        initialize()
    # R-15 合规：自治模式授权检查（不阻断执行）
    _skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _auth_script = os.path.join(_skill_dir, "skill-standardization", "scripts", "authorization_manager.py")
    # 完整性校验：检查 authorization_manager.py 是否被篡改
    if os.path.exists(_auth_script):
        try:
            import hashlib, json, pathlib
            _hash_file = pathlib.Path.home() / ".workbuddy" / "skills" / ".standardization" / "git-sync" / "script_hashes.json"
            with open(_auth_script, "rb") as _f:
                _auth_hash = hashlib.sha256(_f.read()).hexdigest()
            if _hash_file.exists():
                with open(_hash_file) as _f:
                    _records = json.load(_f)
                _rel = str(pathlib.Path(_auth_script).relative_to(pathlib.Path.home() / ".workbuddy" / "skills"))
                if _rel in _records and _records[_rel] != _auth_hash:
                    print(f"⚠️ 警告: authorization_manager.py 哈希不匹配（可能被篡改）: {_rel}")
                    print(f"  预期: {_records[_rel][:16]}...")
                    print(f"  实际: {_auth_hash[:16]}...")
                else:
                    _records[_rel] = _auth_hash
                    with open(_hash_file, "w") as _f:
                        json.dump(_records, _f, indent=2, ensure_ascii=False)
            else:
                _hash_file.parent.mkdir(parents=True, exist_ok=True)
                with open(_hash_file, "w") as _f:
                    json.dump({_rel: _auth_hash}, _f, indent=2, ensure_ascii=False)
        except Exception as _e:
            print(f"⚠️ 哈希校验失败: {_e}")
    if os.path.exists(_auth_script):
        _r = subprocess.run(
            [sys.executable, _auth_script, "request", "--type", "immediate", "--reason", "git-sync 高危操作"],
            capture_output=True, text=True
        )
        if _r.returncode != 0:
            print(f"⚠️ 授权检查警告: {_r.stderr.strip()}")


    main()