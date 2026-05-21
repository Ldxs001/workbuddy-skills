#!/usr/bin/env python3
"""打包 skill 为 ZIP，精确排除指定文件/目录"""

import os
import sys
import zipfile

def pack_skill(skill_dir, zip_path, exclude_patterns=None):
    """
    skill_dir: 技能源目录 (e.g. ~/.workbuddy/skills/git-sync)
    zip_path: 输出 ZIP 路径
    exclude_patterns: 排除模式列表 (e.g. ['*.sh', '__pycache__'])
    """
    if exclude_patterns is None:
        exclude_patterns = []

    skill_name = os.path.basename(os.path.normpath(skill_dir))
    temp_zip = zip_path + ".tmp"

    def should_exclude(rel_path):
        name = os.path.basename(rel_path)
        for pat in exclude_patterns:
            if '*' in pat:
                # glob 模式
                import fnmatch
                if fnmatch.fnmatch(name, pat):
                    return True
            else:
                # 精确名称或目录名
                if name == pat or rel_path == pat:
                    return True
        return False

    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_dir):
            # 计算相对路径
            rel_root = os.path.relpath(root, os.path.dirname(skill_dir))
            zip_root = os.path.join(skill_name, os.path.relpath(root, skill_dir))

            # 排除目录
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]

            for fname in files:
                rel_path = os.path.join(rel_root, fname)
                if should_exclude(rel_path):
                    continue
                full_path = os.path.join(root, fname)
                arcname = os.path.join(zip_root, fname)
                zf.write(full_path, arcname)

    # 原子替换
    if os.path.exists(zip_path):
        os.remove(zip_path)
    os.rename(temp_zip, zip_path)
    print(f"  ✅ ZIP 已生成: {zip_path}")
    print(f"  📦 包含文件数: {len(zf.namelist())}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python pack_zip.py <skill_dir> <zip_path> [exclude_patterns...]")
        sys.exit(1)

    skill_dir = sys.argv[1]
    zip_path = sys.argv[2]
    exclude = sys.argv[3:]

    # 默认排除规则
    default_exclude = [
        '__pycache__', '*.pyc', '*.html', '*.log', '*.zip',
        'ZIP_OUT', 'preview_server.py',
        'update_manifest_version.py', 'build_index_now.py',
        'git-sync.sh',   # 同步脚本本身不打入 ZIP
    ]
    all_exclude = list(set(default_exclude + exclude))

    print(f"  打包: {skill_dir}")
    print(f"  排除: {all_exclude}")
    pack_skill(skill_dir, zip_path, all_exclude)
