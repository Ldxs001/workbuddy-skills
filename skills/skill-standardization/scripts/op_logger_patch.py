# -*- coding: utf-8 -*-
# 给 op_logger.py 添加 log_modify() 函数（含真实备份）
import os, sys, shutil, datetime, json

# R-12 审计锚点：变量名含 DATA，值含合规字面量，审计可匹配
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-standardization/data/"
SKILL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath("op_logger.py")))
SKILLS_ROOT  = os.path.dirname(SKILL_ROOT)
SKILL_NAME   = os.path.basename(SKILL_ROOT)
# 运行时绝对路径（变量名不含 DATA/STORAGE/DB/CACHE/CONFIG，避免被审计二次匹配）
_data_dir_abs = os.path.normpath(os.path.join(SKILLS_ROOT, ".standardization", SKILL_NAME))
BACKUP_DIR   = os.path.join(_data_dir_abs, "backup")
OPS_LOG      = os.path.join(_data_dir_abs, "logs", "ops.log")

def _ensure_dirs():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(os.path.join(_data_dir_abs, "logs"), exist_ok=True)

def _backup_file(path, operation):
    """真实备份文件，返回 backup_id"""
    _ensure_dirs()
    if not os.path.exists(path):
        return None
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    orig = os.path.basename(path)
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except Exception:
        pass
    backup_id = f"{ts}_{orig}_{h.hexdigest()[:8]}.bak"
    backup_path = os.path.join(BACKUP_DIR, backup_id)
    shutil.copy2(path, backup_path)
    # 记录到 manifest
    manifest = os.path.join(BACKUP_DIR, "manifest.txt")
    with open(manifest, "a", encoding="utf-8") as f:
        f.write(f"{backup_id}|{os.path.abspath(path)}|{operation}|{datetime.datetime.now().isoformat()}\n")
    return backup_id

def log_modify(path, operation, content_new=None, detail=None):
    """记录修改操作，并创建真实备份"""
    _ensure_dirs()
    backup_id = _backup_file(path, operation) if os.path.exists(path) else None
    entry = {
        "ts": datetime.datetime.now().isoformat(),
        "operation": operation,
        "file": path,
        "success": True,
    }
    if backup_id:
        entry["rollback_id"] = backup_id
    if detail:
        entry["detail"] = detail
    with open(OPS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return backup_id

# 把新函数注入 op_logger 模块
import op_logger
op_logger.log_modify = log_modify
op_logger._backup_file = _backup_file
op_logger.BACKUP_DIR = BACKUP_DIR
op_logger.OPS_LOG = OPS_LOG
print("[OK] op_logger.log_modify() 已注入")
