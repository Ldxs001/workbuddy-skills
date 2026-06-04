"""
fixer.py — 通用功能修复工具

借鉴 skill-standardization 的 safe_io 设计，提供：
- safe_write(): 原子写入（临时文件 + os.replace），防止写入中断导致文件损坏
- safe_patch(): 基于精确字符串替换的修补
- safe_patch_regex(): 基于正则的批量替换
- fix_add_none_guard(): 为函数添加零值保护
- fix_stdout_to_logging(): 将 print 替换为 logging
- fix_hardcoded_path(): 将硬编码路径替换为变量引用
"""
import os
import re
import shutil
import tempfile
from datetime import datetime


# ═══════════════════════════════════════════════════════
# 原子 I/O
# ═══════════════════════════════════════════════════════

def safe_write(filepath: str, content: str, encoding: str = "utf-8") -> bool:
    """
    原子写入文件：先写临时文件再 os.replace，确保写入不中断。
    支持任意文件类型（.py / .sh / .md / .json）
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(os.path.abspath(filepath)),
            prefix=".fix_tmp_",
            suffix=os.path.splitext(filepath)[1] or ".tmp",
        )
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        # 备份原文件
        if os.path.exists(filepath):
            bak_path = filepath + ".bak"
            shutil.copy2(filepath, bak_path)
        os.replace(tmp_path, filepath)
        return True
    except Exception as e:
        print(f"  [FIX] 写入失败 {filepath}: {e}")
        return False


def safe_read(filepath: str, encoding: str = "utf-8") -> str:
    """安全读取文件"""
    with open(filepath, "r", encoding=encoding) as f:
        return f.read()


# ═══════════════════════════════════════════════════════
# 字符串修补
# ═══════════════════════════════════════════════════════

def safe_patch(filepath: str, old_str: str, new_str: str) -> bool:
    """基于精确字符串替换的修补"""
    try:
        content = safe_read(filepath)
        if old_str not in content:
            print(f"  [FIX] 未找到匹配: {old_str[:40]}...")
            return False
        new_content = content.replace(old_str, new_str)
        return safe_write(filepath, new_content)
    except Exception as e:
        print(f"  [FIX] patch 失败: {e}")
        return False


def safe_patch_regex(filepath: str, pattern: str, replacement: str) -> bool:
    """基于正则的批量替换"""
    try:
        content = safe_read(filepath)
        new_content, count = re.subn(pattern, replacement, content)
        if count == 0:
            print(f"  [FIX] 正则未匹配: {pattern[:40]}...")
            return False
        ok = safe_write(filepath, new_content)
        if ok:
            print(f"  [FIX] 已替换 {count} 处")
        return ok
    except Exception as e:
        print(f"  [FIX] regex 修补失败: {e}")
        return False


# ═══════════════════════════════════════════════════════
# 特定修复工具
# ═══════════════════════════════════════════════════════

def fix_add_none_guard(filepath: str, func_name: str, lineno: int, param: str) -> bool:
    """
    在函数体内添加零值保护
    在 lineno 行后插入:
        if {param} == 0 / None / '':
            return 0 or raise
    """
    try:
        content = safe_read(filepath)
        lines = content.split("\n")

        if lineno > len(lines):
            return False

        # 查找参数在函数中的使用位置
        guard_code = f"    if {param} == 0 or {param} is None:\n        return 0.0"
        indent = "    "

        # 在 def 行之后，第一个非注释/装饰器行之前插入
        insert_at = lineno  # lineno is the def line
        for i in range(lineno, min(lineno + 5, len(lines))):
            line = lines[i]
            if line.strip() and not line.strip().startswith(("#", "@", '"""', "'''")):
                if line.strip().startswith(("def ", "async def")):
                    continue
                insert_at = i
                break

        lines.insert(insert_at, guard_code)
        return safe_write(filepath, "\n".join(lines))
    except Exception as e:
        print(f"  [FIX] 添加零值保护失败: {e}")
        return False


def fix_stdout_to_logging(filepath: str, module_name: str = None) -> bool:
    """
    将裸 print() 替换为 logging 调用
    自动添加 logging 导入和基本配置
    """
    try:
        content = safe_read(filepath)
        lines = content.split("\n")
        new_lines = []
        has_logging_import = False
        print_count = 0

        for line in lines:
            stripped = line.strip()
            # 跳过标签化的 print (如 [KB] 开头的)
            if stripped.startswith("print(") and not stripped.startswith("print(f"):
                if "[KB]" not in stripped and "[ECON" not in stripped and "[EVM" not in stripped:
                    # 提取内容
                    inner = stripped[6:].strip().strip("()").strip('"').strip("'")
                    indent = line[:len(line) - len(line.lstrip())]
                    new_lines.append(f'{indent}logging.info("{inner}")')
                    print_count += 1
                    continue
            new_lines.append(line)

        if print_count == 0:
            return False

        # 添加 logging 导入
        result = "\n".join(new_lines)
        if "import logging" not in result:
            result = "import logging\n" + result

        # 添加 logging 基本配置（只在 __main__ 前加）
        if "logging.basicConfig" not in result:
            result = result.replace(
                'if __name__ == "__main__":',
                'logging.basicConfig(level=logging.INFO, format="%(message)s")\n\nif __name__ == "__main__":',
            )

        ok = safe_write(filepath, result)
        if ok:
            print(f"  [FIX] 已替换 {print_count} 处 print → logging.info")
        return ok
    except Exception as e:
        print(f"  [FIX] print→logging 转换失败: {e}")
        return False


def fix_hardcoded_path(filepath: str, old_path: str, var_name: str) -> bool:
    """
    将硬编码路径替换为变量引用
    在文件顶部添加变量定义
    """
    try:
        content = safe_read(filepath)
        if old_path not in content:
            return False

        # 添加变量定义
        var_def = f'\n# 路径变量（替换硬编码）\n{var_name} = "{old_path}"\n'
        lines = content.split("\n")

        # 找到 import 块结束的位置
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                insert_at = i + 1

        lines.insert(insert_at, var_def.strip())

        # 替换所有硬编码路径
        new_content = "\n".join(lines)
        new_content = new_content.replace(f'"{old_path}"', var_name)
        new_content = new_content.replace(f"'{old_path}'", var_name)

        return safe_write(filepath, new_content)
    except Exception as e:
        print(f"  [FIX] 路径替换失败: {e}")
        return False


def fix_exception_guard(filepath: str, risky_pattern: str) -> bool:
    """
    为裸露的风险操作添加 try/except 包裹
    匹配行包含 risky_pattern 时，包裹 try/except
    """
    try:
        content = safe_read(filepath)
        lines = content.split("\n")
        new_lines = []
        modified = False

        for i, line in enumerate(lines):
            if risky_pattern in line and not line.strip().startswith("#"):
                indent = line[:len(line) - len(line.lstrip())]
                # 跳过已在 try 块中的
                if i > 0 and lines[i-1].strip().rstrip(":").endswith("try"):
                    new_lines.append(line)
                    continue
                new_lines.append(f"{indent}try:")
                new_lines.append(f"{indent}    {line.strip()}")
                new_lines.append(f"{indent}except Exception as e:")
                new_lines.append(f'{indent}    print(f"  [WARN] 操作失败: {{e}}")')
                modified = True
            else:
                new_lines.append(line)

        if modified:
            return safe_write(filepath, "\n".join(new_lines))
        return False
    except Exception as e:
        print(f"  [FIX] 异常包裹失败: {e}")
        return False


# ═══════════════════════════════════════════════════════
# 批量修复入口
# ═══════════════════════════════════════════════════════

def apply_fix(skill_dir: str, fix_type: str, params: dict = None) -> bool:
    """
    统一修复入口
    fix_type: add_none_guard / stdout_to_logging / hardcoded_path / exception_guard
    """
    fixers = {
        "add_none_guard": lambda: fix_add_none_guard(
            params["filepath"], params["func_name"],
            params["lineno"], params["param"]),
        "stdout_to_logging": lambda: fix_stdout_to_logging(
            params["filepath"]),
        "hardcoded_path": lambda: fix_hardcoded_path(
            params["filepath"], params["old_path"], params["var_name"]),
        "exception_guard": lambda: fix_exception_guard(
            params["filepath"], params["pattern"]),
    }
    fixer = fixers.get(fix_type)
    if fixer:
        return fixer()
    print(f"  [FIX] 未知修复类型: {fix_type}")
    return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        result = apply_fix(sys.argv[1], sys.argv[2],
                           {"filepath": sys.argv[3]} if len(sys.argv) >= 4 else None)
        print(f"  [FIX] {'成功' if result else '失败'}")
    else:
        print("用法: python fixer.py <skill-dir> <fix-type> [filepath]")
