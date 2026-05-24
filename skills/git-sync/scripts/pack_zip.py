#!/usr/bin/env python3
from auth_check import authorize, initialize

"""打包 skill 为 ZIP，按文件角色分类排除"""

import os
import sys
import zipfile


def normalize_path(p):
    """将路径规范化为 Windows 绝对路径（处理 Git Bash /c/... 格式）"""
    p = os.path.expanduser(p)
    # 处理 Git Bash 路径格式：/c/Users/... → C:\Users\...
    if p.startswith("/") and len(p) > 2 and p[1].isalpha() and p[2] == "/":
        p = p[1].upper() + ":" + p[2:].replace("/", "\\")
    return os.path.normpath(p)


# ============================================================
# 排除规则体系（按文件角色分类）
# ============================================================
# 设计原则：
#   1. 功能性文件（HTML设置界面、核心脚本等）→ 保留
#   2. 产物文件（ZIP包、index.html 等生成产物）→ 排除
#   3. 缓存/编译产物（__pycache__、*.pyc）→ 排除
#   4. 系统/临时文件（*.log、*.bak、Thumbs.db）→ 排除
#   5. 版本控制目录（.git）→ 排除
#   6. 敏感配置（config.json 精确匹配根目录）→ 排除
#
# 注意：不按扩展名 blanket 排除，而是按角色精确排除。
# ============================================================

# 目录名精确排除（整个目录不入 ZIP）
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".eggs",
    "eggs",
    "dist",
    "build",
    ".eggs-info",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".standardization",
}

# 文件名精确排除（根目录或任意子目录的精确匹配）
EXCLUDE_FILES_EXACT = {
    ".gitignore",
    ".ds_store",
    "thumbs.db",
    "config.json",              # 根目录配置，可能含敏感信息
    "manifest.json",            # 维护清单状态，本地数据不应上传
    "pack_zip.py",             # 打包脚本本身不入 ZIP
}

# glob 模式排除（匹配文件名）
EXCLUDE_FILES_GLOB = {
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.zip",                   # 产物 ZIP 文件
    "*.bak*",
    "*.tmp",
    "._*",                     # macOS 资源分支
    ".decisions.json",           # 敏感扫描决策文件
    ".sensitive_scan_*.json",   # 敏感扫描临时文件
    "zip_out",                  # 产物目录标记文件
    "preview_server.py",        # 预览服务器脚本（开发辅助工具，非运行时必需）
    "*_fixed.py",              # 测试修复文件
    "stderr.txt",              # 临时 stderr 输出
    "stdout.txt",              # 临时 stdout 输出
}

# 功能性文件白名单（即使扩展名匹配上述规则，也不排除）
# 例如：settings.html 是功能性文件，不应被 *.html 规则排除
# （当前没有 blanket *.html 规则，所以不需要白名单，但保留扩展口）
FUNCTIONAL_FILE_WHITELIST = {
    "settings.html",             # git-sync 设置界面
    "preview.html",              # 预览界面（如有）
}


def should_exclude(rel_path):
    """判断相对路径是否应被排除。

    rel_path: 相对于技能源目录的路径（正反斜杠均可），如 "config.json" 或 "scripts/foo.py"
    returns: True 表示排除，False 表示保留
    """
    import fnmatch
    import posixpath

    # 标准化为 POSIX 风格便于匹配
    p = rel_path.replace(os.sep, "/")
    name = os.path.basename(p)
    parent_dir = os.path.dirname(p)  # 相对父目录，"" 表示根目录

    # 1. 白名单检查（最先）：功能性文件跳过所有排除规则
    lower_name = name.lower()
    for w in FUNCTIONAL_FILE_WHITELIST:
        if lower_name == w.lower():
            return False

    # 2. 目录名检查（rel_path 的每个路径成分）
    parts = p.split("/")
    for part in parts[:-1]:  # 最后一个成分是文件名，不算目录
        if part.lower() in (d.lower() for d in EXCLUDE_DIRS):
            return True

    # 3. 精确文件名匹配
    lower_exact = {f.lower() for f in EXCLUDE_FILES_EXACT}
    if name.lower() in lower_exact:
        # config.json / manifest.json 只排除根目录的（parent_dir == ""）
        if name.lower() in ("config.json", "manifest.json"):
            if parent_dir == "":
                return True
            else:
                return False  # 子目录的 config.json 保留
        return True

    # 4. glob 模式匹配
    for pat in EXCLUDE_FILES_GLOB:
        if fnmatch.fnmatch(name, pat):
            return True
        # 也检查 rel_path 级别的模式（如 .sensitive_scan_*.json）
        if fnmatch.fnmatch(p, pat):
            return True

    return False


def pack_skill(skill_dir, zip_path, extra_exclude=None):
    """
    if not authorize("unknown", "\u68c0\u6d4b\u5230\u5173\u952e\u4f4d\u7f6e\u5199\u5165\uff08skills/.workbuddy/\u7cfb\u7edf\u76ee\u5f55\uff09"): return
    if not authorize("unknown", "\u68c0\u6d4b\u5230\u5173\u952e\u4f4d\u7f6e\u5199\u5165\uff08skills/.workbuddy/\u7cfb\u7edf\u76ee\u5f55\uff09"): return
    if not authorize("unknown", "\u68c0\u6d4b\u5230\u5173\u952e\u4f4d\u7f6e\u5199\u5165\uff08skills/.workbuddy/\u7cfb\u7edf\u76ee\u5f55\uff09"): return
    skill_dir: 技能源目录 (e.g. ~/.workbuddy/skills/git-sync)
    zip_path: 输出 ZIP 路径
    extra_exclude: 额外排除模式列表（追加到默认规则）
    """
    skill_dir = normalize_path(skill_dir)

    # 合并额外排除（转为小写集合便于快速匹配）
    exclude_set = set()
    if extra_exclude:
        for pat in extra_exclude:
            exclude_set.add(pat)

    skill_name = os.path.basename(os.path.normpath(skill_dir))
    temp_zip = zip_path + ".tmp"

    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_dir):
            # rel_path: 相对于 skill_dir 的路径（should_exclude 的基准）
            rel_root = os.path.relpath(root, skill_dir)
            zip_root = os.path.join(skill_name, rel_root) if rel_root != "." else skill_name

            # 排除目录（原地修改 dirs 以阻止 os.walk 进入）
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]

            for fname in files:
                rel_path = os.path.join(rel_root, fname) if rel_root != "." else fname
                if should_exclude(rel_path):
                    continue
                full_path = os.path.join(root, fname)
                arcname = os.path.join(zip_root, fname)
                zf.write(full_path, arcname)

    # 原子替换
    if os.path.exists(zip_path):
        if not authorize("unknown", "\u68c0\u6d4b\u5230\u6587\u4ef6\u5220\u9664\u64cd\u4f5c\uff08os.remove/shutil.rmtree\u7b49\uff09"): return
        os.remove(zip_path)
    os.rename(temp_zip, zip_path)
    print(f"  ✅ ZIP 已生成: {zip_path}")
    print(f"  📦 包含文件数: {len(zf.namelist())}")


if __name__ == "__main__":
        initialize()
    if len(sys.argv) < 3:
        print("用法: python pack_zip.py <skill_dir> <zip_path> [extra_exclude...]")
        sys.exit(1)

    skill_dir = sys.argv[1]
    zip_path = sys.argv[2]
    extra = sys.argv[3:]

    print(f"  打包: {skill_dir}")
    if extra:
        print(f"  额外排除: {extra}")
    print(f"  排除目录: {sorted(EXCLUDE_DIRS)}")
    print(f"  排除文件（精确）: {sorted(EXCLUDE_FILES_EXACT)}")
    print(f"  排除模式（glob）: {sorted(EXCLUDE_FILES_GLOB)}")
    print(f"  功能性白名单: {sorted(FUNCTIONAL_FILE_WHITELIST)}")
    pack_skill(skill_dir, zip_path, extra)