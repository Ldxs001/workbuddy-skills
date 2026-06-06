"""
local-rag-builder 环境检测与自动修复模块
v0.1.0
检测 Python 版本、缺失包，自动创建虚拟环境并安装
"""

import os
import sys
import subprocess
import platform


REQUIRED_PACKAGES = [
    "langchain",
    "langchain-community",
    "langchain-huggingface",
    "langchain-chroma",
    "langchain-text-splitters",
    "chromadb",
    "sentence-transformers",
    "huggingface-hub",
    "modelscope",
    "openai",
]

OPTIONAL_PACKAGES = {
    "unstructured": "unstructured[pdf]",
    "pdfplumber": "pdfplumber",
    "transformers": "transformers",
    "pillow": "pillow",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
}


def get_python_path():
    return sys.executable


def check_python_version():
    """检查 Python 版本（建议 3.8-3.11）"""
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major == 3 and 8 <= v.minor <= 11:
        return True, version_str, "OK"
    elif v.major == 3 and v.minor >= 12:
        return False, version_str, "WARN: chromadb 可能不兼容 3.12+，建议使用 3.8-3.11"
    elif v.major == 3 and v.minor < 8:
        return False, version_str, "ERROR: Python 版本过低，需要 3.8+"
    return False, version_str, "ERROR: 仅支持 Python 3.x"


def check_pip():
    """检查 pip 是否可用"""
    try:
        result = subprocess.run(
            [get_python_path(), "-m", "pip", "--version"],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def list_installed():
    """列出已安装包"""
    try:
        result = subprocess.run(
            [get_python_path(), "-m", "pip", "list", "--format=columns"],
            capture_output=True, text=True, timeout=30
        )
        pkgs = {}
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines[2:]:
                parts = line.split()
                if len(parts) >= 2:
                    pkgs[parts[0].lower()] = parts[1]
        return pkgs
    except (subprocess.TimeoutExpired, OSError):
        return {}


def check_missing(installed_pkgs=None):
    """返回缺失的必需包列表和缺失的可选包列表"""
    if installed_pkgs is None:
        installed_pkgs = list_installed()
    required_missing = []
    optional_missing = []
    for pkg in REQUIRED_PACKAGES:
        if pkg.lower() not in installed_pkgs:
            required_missing.append(pkg)
    for pkg_name, install_name in OPTIONAL_PACKAGES.items():
        if pkg_name.lower() not in installed_pkgs:
            optional_missing.append((pkg_name, install_name))
    return required_missing, optional_missing


def install_packages(packages, upgrade_pip=True):
    """安装指定包列表"""
    python = get_python_path()
    results = {}

    try:
        if upgrade_pip:
            subprocess.run(
                [python, "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True, text=True, timeout=60
            )

        for pkg in packages:
            print(f"  安装 {pkg}...")
            try:
                result = subprocess.run(
                    [python, "-m", "pip", "install", pkg],
                    capture_output=True, text=True, timeout=300
                )
                results[pkg] = result.returncode == 0
                if result.returncode != 0:
                    print(f"    FAIL: {result.stderr.strip()[-200:]}")
                else:
                    print(f"    OK")
            except (subprocess.TimeoutExpired, OSError) as e:
                results[pkg] = False
                print(f"    FAIL: {e}")
    except Exception:
        pass

    return results


def create_venv(venv_path):
    """创建虚拟环境"""
    print(f"创建虚拟环境: {venv_path}")
    try:
        result = subprocess.run(
            [get_python_path(), "-m", "venv", venv_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"  FAIL: {result.stderr.strip()}")
            return None
        
        # 返回 venv 的 python 路径
        if platform.system() == "Windows":
            python_path = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            python_path = os.path.join(venv_path, "bin", "python")
        
        if os.path.exists(python_path):
            return python_path
        return None
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"  FAIL: {e}")
        return None


def check_torch_gpu():
    """检查 PyTorch CUDA 是否可用"""
    try:
        result = subprocess.run(
            [get_python_path(), "-c", "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            cuda_avail = lines[0] == "True"
            gpu_name = lines[1] if len(lines) > 1 else "N/A"
            return cuda_avail, gpu_name
        return False, "无法检测"
    except Exception:
        return False, "检测失败"


def run_full_check():
    """运行完整环境检查"""
    print("=" * 50)
    print("  本地 RAG 环境检测")
    print("=" * 50)

    # Python 版本
    ok, ver, msg = check_python_version()
    print(f"\n[{'OK' if ok else '!'}] Python 版本: {ver} — {msg}")

    # Pip
    pip_ok = check_pip()
    print(f"[{'OK' if pip_ok else '!'}] Pip: {'可用' if pip_ok else '不可用'}")

    # 已安装包
    installed = list_installed()
    print(f"\n已安装包: {len(installed)} 个")

    # 缺失检查
    required_missing, optional_missing = check_missing(installed)
    if required_missing:
        print(f"\n[!] 缺失必需包 ({len(required_missing)}): {', '.join(required_missing)}")
    else:
        print(f"\n[OK] 所有必需包已安装")

    if optional_missing:
        print(f"[i] 可选包未安装 ({len(optional_missing)}): {', '.join(n for n, _ in optional_missing)}")

    # GPU 检测
    cuda, gpu = check_torch_gpu()
    print(f"\n[{'OK' if cuda else 'i'}] GPU: {gpu if cuda else '未检测到 CUDA (将使用 CPU)'}")

    print("\n" + "=" * 50)
    return {
        "python_ok": ok,
        "python_version": ver,
        "pip_ok": pip_ok,
        "required_missing": required_missing,
        "optional_missing": [n for n, _ in optional_missing],
        "cuda_available": cuda,
        "gpu_name": gpu,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 环境检测与修复工具")
    parser.add_argument("--check-only", action="store_true", help="仅检测，不自动修复")
    parser.add_argument("--auto-install", action="store_true", help="自动安装缺失的必需包")
    parser.add_argument("--install-optional", type=str, nargs="*", help="安装指定的可选包")
    parser.add_argument("--create-venv", type=str, help="在指定路径创建虚拟环境")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出（供智能体调用）")

    args = parser.parse_args()

    report = run_full_check()

    if args.json:
        import json
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.auto_install and report["required_missing"]:
        print(f"\n→ 自动安装缺失包...")
        results = install_packages(report["required_missing"])
        failed = [p for p, ok in results.items() if not ok]
        if failed:
            print(f"\n[!] 安装失败: {', '.join(failed)}")
            print("  建议: 手动执行 pip install 或检查网络连接")
        else:
            print(f"\n[OK] 所有必需包安装完成")

    if args.install_optional:
        to_install = []
        for name in args.install_optional:
            if name in dict(OPTIONAL_PACKAGES):
                to_install.append(OPTIONAL_PACKAGES[name])
            else:
                to_install.append(name)
        print(f"\n→ 安装可选包...")
        install_packages(to_install)

    if args.create_venv:
        python = create_venv(args.create_venv)
        if python:
            print(f"[OK] 虚拟环境创建完成: {python}")
        else:
            print(f"[!] 虚拟环境创建失败")
