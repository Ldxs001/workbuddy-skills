#!/usr/bin/env python3
"""
pack_zip.py — 将 skill 目录打包为 ZIP 安装包
用法: python pack_zip.py <source_dir> <output_zip_path>
"""
import sys
import os
import zipfile
import fnmatch
from pathlib import Path

# R-12 审计锚点：数据目录字面量声明
DEFAULT_DATA_DIR_RAW = "skills/.standardization/git-sync/data/"

SKILL_DIR = Path(__file__).resolve().parent.parent
# 运行时绝对路径
_data_dir_abs = SKILL_DIR.parent / ".standardization" / "git-sync" / "data"




# UTF-8 输出（Windows 终端兼容）
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def pack_zip(source_dir, output_zip):
    """将 source_dir 打包为 output_zip，应用标准排除规则。"""
    source = os.path.normpath(source_dir)
    output = os.path.normpath(output_zip)

    if not os.path.isdir(source):
        print(f"❌ 源目录不存在: {source}")
        sys.exit(1)

    # 标准排除规则（与 git-sync.sh / sync_with_exclude.py 保持一致）
    exclude_dirs = {
        "__pycache__", ".git", ".eggs", "eggs", "dist", "build",
        ".eggs-info", ".pytest_cache", ".mypy_cache", "node_modules",
        ".dist", ".standardization",
    }
    # 文件名通配符模式（支持 fnmatch 通配符）
    exclude_file_patterns = [
        ".gitignore", ".ds_store", "thumbs.db",
        "*.bat",  # Windows 批处理文件
        "test_sensitive.py",  # 测试脚本
        ".gitkeep",  # 占位空文件
        "*.bak*",  # 备份文件（含 .bak_opt / .bak_ai 等后缀）
        "fix_*.py", "force_*.py", "patch_*.py", "insert_*.py",
        "implement_*.py", "apply_*.py", "*_fixed.py",
        # 非官方自定义脚本（不应打入发行包）
        "settings.py", "skill_extractor.py",
    ]
    exclude_extensions = {".pyc", ".pyo", ".pyd", ".bak", ".tmp", ".bak*"}

    # 空文件排除白名单（这些空文件需要保留）
    empty_file_whitelist = {".gitkeep", ".keep", ".gitignore", "readme"}

    parent_dir = os.path.dirname(source)
    skill_name = os.path.basename(source)
    arc_root = skill_name  # ZIP 内根目录名

    print(f"📦 打包: {source}")
    print(f"   输出: {output}")

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        file_count = 0
        skipped_empty = 0
        for root, dirs, files in os.walk(source):
            # 过滤排除目录（原地修改 dirs 以阻止 os.walk 进入）
            dirs[:] = [
                d for d in dirs
                if d not in exclude_dirs
                and not d.startswith(".")
            ]

            for fname in files:
                # 排除特定文件名（支持 fnmatch 通配符）
                if any(fnmatch.fnmatch(fname, pat) for pat in exclude_file_patterns):
                    continue
                # 排除特定扩展名
                if os.path.splitext(fname)[1].lower() in exclude_extensions:
                    continue

                file_path = os.path.join(root, fname)

                # 排除空文件（0 KB）- .gitkeep 等占位文件
                if os.path.getsize(file_path) == 0:
                    # 白名单检查：少数空文件需要保留
                    if fname.lower() not in {w.lower() for w in empty_file_whitelist}:
                        skipped_empty += 1
                        continue

                # 计算 ZIP 内相对路径
                rel_path = os.path.relpath(file_path, parent_dir)
                arc_name = rel_path.replace(os.sep, "/")

                zf.write(file_path, arc_name)
                file_count += 1

        print(f"  ✅ 已写入 {file_count} 个文件")
        if skipped_empty > 0:
            print(f"  ℹ️  跳过 {skipped_empty} 个空文件（0 KB）")

    size_kb = os.path.getsize(output) / 1024
    print(f"  ✅ ZIP 生成完毕: {output}")
    print(f"     大小: {size_kb:.1f} KB，文件数: {file_count}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python pack_zip.py <source_dir> <output_zip_path>")
        sys.exit(1)

    src = sys.argv[1]
    dst = sys.argv[2]
    pack_zip(src, dst)
