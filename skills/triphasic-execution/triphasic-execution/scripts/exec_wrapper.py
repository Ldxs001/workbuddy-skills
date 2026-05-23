#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exec Wrapper — 命令执行拦截器
================================
拦截所有 shell 命令，捕获 stdout/stderr 和退出码，写入管道文件供 daemon 监控。

路径配置：
  环境变量 TRIPHASIC_HOME 或 --home 参数
  默认值 ~/.workbuddy/triphasic/

用法:
  python exec_wrapper.py "your command here"
  python exec_wrapper.py --home /custom/path "your command here"

注册为全局 exec（Mode 2）:
  # Linux/Mac (.bashrc / .zshrc):
    export TRIPHASIC_HOME=~/.workbuddy/triphasic
    alias exec="python3 ~/.workbuddy/skills/triphasic-execution/scripts/exec_wrapper.py"

  # Windows (PowerShell Profile):
    $env:TRIPHASIC_HOME = "$env:USERPROFILE\\.workbuddy\\triphasic"
    function exec { python "$env:USERPROFILE\\.workbuddy\\skills\\triphasic-execution\\scripts\\exec_wrapper.py" @args }
"""

import argparse
import os
import sys
import json
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================================================
# 路径配置
# ============================================================================
_DEFAULT_HOME = Path.home() / ".workbuddy" / "triphasic"
_TRIPHASIC_HOME = Path(os.environ.get("TRIPHASIC_HOME", _DEFAULT_HOME))


def get_home() -> Path:
    home = _TRIPHASIC_HOME
    home.mkdir(parents=True, exist_ok=True)
    return home


def get_exec_pipe() -> Path:
    return get_home() / ".exec_output_pipe.txt"


def get_config_file() -> Path:
    return get_home() / "config.json"


def load_config() -> dict:
    """加载配置"""
    defaults = {}
    default_path = Path(__file__).parent.parent / "assets" / "default_config.json"
    if default_path.exists():
        try:
            defaults = json.loads(default_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    user_path = get_config_file()
    if user_path.exists():
        try:
            user_cfg = json.loads(user_path.read_text(encoding="utf-8"))
            defaults.update(user_cfg)
        except Exception:
            pass
    return defaults


# ============================================================================
# Windows 编码兼容
# ============================================================================
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


# ============================================================================
# 核心函数
# ============================================================================
def write_to_pipe(command: str, exit_code: int, stdout: str, stderr: str):
    """将 exec 输出写入管道文件（供 daemon 监控）"""
    pipe = get_exec_pipe()
    pipe.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    full_output = stdout if stdout else stderr

    record = f"{timestamp}|{exit_code}|{command}\n\n{full_output}"

    with open(pipe, "a", encoding="utf-8", errors="replace") as f:
        f.write(record + "\n" + "=" * 60 + "\n")
        f.flush()


def write_interrupt_to_pipe(command: str, signal_num: int):
    """记录命令被中断的事件"""
    pipe = get_exec_pipe()
    pipe.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    signal_name = {2: "SIGINT(Ctrl+C)", 15: "SIGTERM", 9: "SIGKILL"}.get(signal_num, f"SIG{signal_num}")

    # 中断事件使用特殊退出码 -100 到 -109
    interrupt_exit_code = -100 - signal_num

    record = f"{timestamp}|{interrupt_exit_code}|{command}\n\n⚠️ 命令被强制中断 - {signal_name}"
    with open(pipe, "a", encoding="utf-8", errors="replace") as f:
        f.write(record + "\n" + "=" * 60 + "\n")
        f.flush()


# 全局变量，用于信号处理器
_current_command = ""
_current_args = []


def handle_interrupt(signum, frame):
    """信号处理器：捕获 Ctrl+C 或 SIGTERM，记录中断事件"""
    signal_name = {2: "SIGINT(Ctrl+C)", 15: "SIGTERM"}.get(signum, f"SIG{signum}")
    print(f"\n⚠️ 捕获信号 {signal_name}，正在记录中断事件...", file=sys.stderr)

    # 写入中断记录
    if _current_command:
        write_interrupt_to_pipe(_current_command, signum)

    print("✅ 中断事件已记录，进程退出", file=sys.stderr)
    sys.exit(128 + signum)


# 注册信号处理器（仅在非 Windows 平台）
if sys.platform != "win32":
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)
else:
    # Windows: 使用 setconsoleCtrlHandler
    def win_signal_handler(sig):
        if sig == 0:  # CTRL_C_EVENT
            handle_interrupt(2, None)
        elif sig == 1:  # CTRL_BREAK_EVENT
            handle_interrupt(21, None)  # SIGBREAK
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCtrlHandler(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int)(win_signal_handler), True)
    except Exception:
        pass


def run_command(command_str: str, cmd_args: list[str]) -> tuple[int, str, str]:
    """执行命令，返回 (exit_code, stdout, stderr)"""
    timeout = 300  # 5 分钟超时

    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["cmd.exe", "/c", command_str],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        else:
            # 检测是否需要 shell
            shell_chars = {"|", "&&", "||", ">", "<", "$", "`", "~", ";", "(", "}"}
            needs_shell = any(c in command_str for c in shell_chars)
            if needs_shell:
                result = subprocess.run(
                    ["bash", "-c", command_str],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            else:
                result = subprocess.run(
                    cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
        return result.returncode, result.stdout or "", result.stderr or ""

    except subprocess.TimeoutExpired:
        return -1, "", f"❌ 命令超时（超过 {timeout // 60} 分钟）: {command_str}"
    except FileNotFoundError:
        return -2, "", f"❌ 命令不存在或未找到：{command_str.split()[0] if command_str else '(empty)'}"
    except PermissionError:
        return -3, "", f"❌ 权限不足：{command_str.split()[0] if command_str else '(empty)'}"
    except Exception as e:
        return -4, "", f"❌ 执行失败：{e}"


def main():
    parser = argparse.ArgumentParser(
        description="Exec Wrapper — 命令执行拦截器",
    )
    parser.add_argument("--home", type=str, default=None, help="覆盖 TRIPHASIC_HOME")
    parser.add_argument("--no-pipe", action="store_true", help="不写入管道文件（仅执行）")

    args, remaining = parser.parse_known_args()

    # --home 覆盖
    if args.home:
        global _TRIPHASIC_HOME
        _TRIPHASIC_HOME = Path(args.home).expanduser().resolve()

    if not remaining:
        print("用法：python exec_wrapper.py [--home /path] [--no-pipe] \"command\"", file=sys.stderr)
        return 1

    command_str = " ".join(remaining)

    # 保存当前命令供信号处理器使用
    global _current_command, _current_args
    _current_command = command_str
    _current_args = remaining

    print(f"🔧 执行命令：{command_str}")
    print("-" * 60)

    start_time = time.time()
    exit_code, stdout, stderr = run_command(command_str, remaining)
    elapsed = time.time() - start_time

    # 输出结果
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, file=sys.stderr)

    # 写入管道
    if not args.no_pipe:
        write_to_pipe(command_str, exit_code, stdout, stderr)

    # 返回摘要
    status = "✅ 成功" if exit_code == 0 else f"❌ 失败 (exit={exit_code})"
    print(f"\n[{status}] 耗时 {elapsed:.1f}s", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
