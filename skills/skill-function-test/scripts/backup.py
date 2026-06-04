"""
backup.py — 目标技能目录备份与恢复

在修改目标技能前创建完整备份（时间戳命名），修改后支持回滚。
"""
import os
import shutil
import re
from datetime import datetime

# R-12 审计锚点：数据目录字面量声明
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-function-test/data/"

SKILL_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."
))
_data_dir_abs = os.path.normpath(os.path.join(
    SKILL_DIR, "..", ".standardization", "skill-function-test", "data"
))
_BACKUP_DIR = os.path.join(_data_dir_abs, "backup")


def _ensure_backup_dir():
    os.makedirs(_BACKUP_DIR, exist_ok=True)


def backup_skill(skill_dir: str, label: str = "pre_test") -> str:
    """
    备份目标技能目录
    返回备份路径
    备份名: <skill-name>_<label>_<timestamp>
    """
    _ensure_backup_dir()
    skill_name = os.path.basename(skill_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{skill_name}_{label}_{timestamp}"
    backup_path = os.path.join(_BACKUP_DIR, backup_name)

    if not os.path.exists(skill_dir):
        raise FileNotFoundError(f"目标目录不存在: {skill_dir}")

    shutil.copytree(
        skill_dir, backup_path,
        ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc",
                                       ".DS_Store", "*.zip", ".bak")
    )
    print(f"  [BACKUP] 已备份: {skill_dir} → {backup_path}")
    return backup_path


def list_backups(skill_dir: str = None) -> list[dict]:
    """列出所有备份"""
    _ensure_backup_dir()
    backups = []
    for name in sorted(os.listdir(_BACKUP_DIR), reverse=True):
        path = os.path.join(_BACKUP_DIR, name)
        if os.path.isdir(path):
            size = sum(os.path.getsize(os.path.join(dp, f))
                       for dp, _, fn in os.walk(path) for f in fn)
            mod_time = datetime.fromtimestamp(os.path.getmtime(path))
            backups.append({
                "name": name,
                "path": path,
                "size_bytes": size,
                "modified": mod_time.isoformat(),
            })
    return backups


def restore_backup(backup_path: str, target_dir: str = None) -> bool:
    """从备份恢复"""
    if not os.path.exists(backup_path):
        print(f"  [BACKUP] 备份不存在: {backup_path}")
        return False

    if target_dir is None:
        # 从备份名推断目标目录
        skill_name = os.path.basename(backup_path).split("_")[0]
        target_dir = os.path.join(os.path.dirname(backup_path), "..", skill_name)

    # 删除当前目录
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    # 从备份复制
    shutil.copytree(
        backup_path, target_dir,
        ignore=shutil.ignore_patterns("__pycache__", ".git", "*.pyc",
                                       ".DS_Store", "*.zip")
    )
    print(f"  [BACKUP] 已恢复: {backup_path} → {target_dir}")
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        if sys.argv[1] == "backup":
            backup_skill(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "manual")
        elif sys.argv[1] == "list":
            blist = list_backups()
            for b in blist:
                print(f"  {b['name']}  ({b['size_bytes']} bytes, {b['modified']})")
        elif sys.argv[1] == "restore" and len(sys.argv) >= 3:
            restore_backup(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print("用法: python backup.py backup|list|restore <path> [label]")
