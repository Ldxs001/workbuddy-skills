"""
_path_detector.py — 统一路径定义检测层

所有审计规则中涉及"是否路径定义"的判断，统一调用此模块。
避免 R-12 / R-25 C-20 / R-23 各写一套模式匹配逻辑导致结果不一致。

检测准则：
  - 字面量路径：含 "skills/" 或 ".standardization/" 或平台绝对路径
  - 变量推导路径：赋值含 Path(__file__) / os.path.join / parent 链
  - *_DIR / *_PATH / *_ROOT 赋值
"""

import ast, os, re


# ── 路径特征识别 ──

_PATH_LITERAL_PATTERNS = [
    r'skills/',
    r'\.standardization/',
    r'os\.path\.join\(',
    r'Path\s*\(',
    r'__file__',
    r'\.parent',
]

_BLOCKED_FIX_KEYS = {"workflow_completeness", "example_quality",
                     "capability_boundary", "section_names"}


def has_path_feature(text: str) -> bool:
    """判断文本是否包含路径特征（字面量、os.path.join、Path等）"""
    for pat in _PATH_LITERAL_PATTERNS:
        if pat in text:
            return True
    # 平台绝对路径（Windows / Unix）
    if re.search(r'[A-Za-z]:[\\/]', text) or re.search(r'^/[^/]', text):
        return True
    # 变量名含 _DIR / _PATH / _ROOT
    if re.search(r'\b[A-Z_]+_(?:DIR|PATH|ROOT)\s*=', text):
        return True
    return False


def is_path_definition(line: str) -> bool:
    """判断一行是否为路径定义赋值（模块级）"""
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        return False
    # 赋值模式：VAR = ...
    if '=' not in stripped:
        return False
    # 变量名含 _DIR / _PATH / _ROOT
    if not re.search(r'^[A-Za-z_]+_(?:DIR|PATH|ROOT)\s*=', stripped):
        # 或包含路径字面量特征
        if not has_path_feature(stripped):
            return False
    # 右侧包含路径特征
    val = stripped.split('=', 1)[1].strip()
    return has_path_feature(val) or bool(re.search(r'_[A-Z]+\s*/(?:|/)', val))


def detect_path_type(line: str) -> str:
    """识别路径定义的类型：literal / derived / argv / unknown"""
    stripped = line.strip()
    # sys.argv + 文件操作
    if 'sys.argv[' in stripped and has_path_feature(stripped):
        return 'argv'
    # 硬编码字面量
    if re.search(r'"(?:skills/|\.standardization/|\.workbuddy)', stripped):
        return 'literal'
    if re.search(r"'(?:skills/|\.standardization/|\.workbuddy)", stripped):
        return 'literal'
    # 变量推导（Path / os.path.join / parent 链）
    if re.search(r'Path\s*\(|os\.path\.join|\.parent', stripped):
        return 'derived'
    return 'unknown'


def is_llm_only_fix(fix_key: str) -> bool:
    """判断一个 fix key 是否属于 LLM 手动修复（非 auto-fix）"""
    return fix_key in _BLOCKED_FIX_KEYS or False


def get_standardized_dirs(skill_name: str):
    """返回标准数据目录字典（按 R-11/R-12 规范）"""
    return {
        "STD_ROOT": f"skills/.standardization/",
        "STD_DIR": f"skills/.standardization/{skill_name}/",
        "DATA_DIR": f"skills/.standardization/{skill_name}/data/",
        "OUTPUTS_DIR": f"skills/.standardization/{skill_name}/outputs/",
        "BACKUP_DIR": f"skills/.standardization/{skill_name}/backup/",
        "CACHE_DIR": f"skills/.standardization/{skill_name}/cache/",
        "TEMP_DIR": f"skills/.standardization/{skill_name}/temp/",
    }
