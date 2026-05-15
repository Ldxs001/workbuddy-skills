#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Install — 一键安装 triphasic-execution 技能
============================================
将技能安装到 ~/.workbuddy/skills/ 本地目录，并可选注册 exec 全局管理。

用法:
  python install.py                    # 安装技能到 ~/.workbuddy/skills/
  python install.py --register-exec    # 安装 + 注册 exec wrapper
  python install.py --uninstall        # 卸载
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# 脚本所在目录即技能根目录
SKILL_SOURCE = Path(__file__).parent.parent
SKILL_NAME = "triphasic-execution"
TARGET_DIR = Path.home() / ".workbuddy" / "skills" / SKILL_NAME
TRIPHASIC_HOME = Path.home() / ".workbuddy" / "triphasic"


def install_skill():
    """安装技能到 ~/.workbuddy/skills/"""
    print(f"📦 安装 {SKILL_NAME} 技能...")

    if TARGET_DIR.exists():
        print(f"   ⚠️  目标已存在：{TARGET_DIR}")
        overwrite = input("   是否覆盖？(y/N): ").strip().lower()
        if overwrite != "y":
            print("   取消安装")
            return False
        shutil.rmtree(TARGET_DIR)

    shutil.copytree(SKILL_SOURCE, TARGET_DIR)
    print(f"   ✅ 已安装到：{TARGET_DIR}")

    # 初始化数据目录
    logger = TARGET_DIR / "scripts" / "problem_logger.py"
    if logger.exists():
        import subprocess
        result = subprocess.run(
            [sys.executable, str(logger), "init"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"   ✅ 数据目录已初始化：{TRIPHASIC_HOME}")
        else:
            print(f"   ⚠️  数据目录初始化失败：{result.stderr}")

    return True


def register_exec():
    """注册 exec 全局管理"""
    print(f"\n🔧 注册 exec 全局管理...")

    wrapper = TARGET_DIR / "scripts" / "exec_wrapper.py"

    if sys.platform == "win32":
        ps_profile = Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        # 检测其他常见位置
        if not ps_profile.parent.exists():
            ps_profile = Path.home() / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"

        func_code = f'''
# Triphasic Execution - exec wrapper
$env:TRIPHASIC_HOME = "{TRIPHASIC_HOME}"
function exec {{ python "{wrapper}" @args }}
'''
        print(f"   请将以下内容添加到 PowerShell Profile：")
        print(f"   Profile 位置：{ps_profile}")
        print(f"   ---")
        print(func_code.strip())
        print(f"   ---")
        print(f"   或运行：")
        print(f'   Add-Content -Path "{ps_profile}" -Value @\'')
        print(func_code.strip())
        print(f'\'@')

    else:
        func_code = f'''
# Triphasic Execution - exec wrapper
export TRIPHASIC_HOME="{TRIPHASIC_HOME}"
exec() {{
    python3 "{wrapper}" "$@"
}}
'''
        print(f"   请将以下内容添加到 ~/.bashrc 或 ~/.zshrc：")
        print(f"   ---")
        print(func_code.strip())
        print(f"   ---")

    print(f"\n   注册后重启终端即可使用 `exec` 命令")
    return True


def uninstall():
    """卸载技能"""
    print(f"🗑️  卸载 {SKILL_NAME}...")

    if not TARGET_DIR.exists():
        print(f"   ⚠️  技能未安装")
        return

    shutil.rmtree(TARGET_DIR)
    print(f"   ✅ 已删除：{TARGET_DIR}")
    print(f"\n   以下数据目录保留未删除（如需清理请手动删除）：")
    print(f"   {TRIPHASIC_HOME}")


def main():
    parser = argparse.ArgumentParser(description=f"安装 {SKILL_NAME} 技能")
    parser.add_argument("--register-exec", action="store_true", help="安装后注册 exec wrapper")
    parser.add_argument("--uninstall", action="store_true", help="卸载技能")

    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    else:
        installed = install_skill()
        if installed and args.register_exec:
            register_exec()
        elif installed:
            print(f"\n💡 提示：运行 `python install.py --register-exec` 注册 exec 全局管理")


if __name__ == "__main__":
    main()
