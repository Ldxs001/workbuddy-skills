"""PyPI 发布器 — git-sync 子模块
用法: pypi_publish.py <source_dir> <name> <version> [--pypi-name PYPI_NAME]

修复内容 (v2):
  1. ⚡ 动态检测包目录（不再硬编码 rag_assistant）
  2. ⚡ 生成 pyproject.toml（防止 setuptools>=61 把 description 标记为 Dynamic）
  3. ⚡ 修复硬编码的 ~/.workbuddy/workbuddy-skills 路径
  4. ✅ 构建后验证 wheel 元数据是否包含 long_description
"""
import sys, os, shutil, subprocess, tempfile, json, zipfile


def find_pkg_dir(build_dir: str) -> str:
    """在构建目录中自动检测主包目录"""
    for item in sorted(os.listdir(build_dir)):
        full = os.path.join(build_dir, item)
        if os.path.isdir(full) and not item.startswith("_") and not item.startswith(".") \
           and item not in ("scripts","__pycache__","venv","env","dist","build","vendor","tools"):
            if os.path.exists(os.path.join(full, "__init__.py")):
                return item
    # fallback: 任何含 __init__.py 的目录
    for item in os.listdir(build_dir):
        full = os.path.join(build_dir, item)
        if os.path.isdir(full) and os.path.exists(os.path.join(full, "__init__.py")):
            return item
    return ""


def write_setup_py(build_dir: str, pkg_dir: str, name: str, version: str, pypi_name: str):
    """生成 setup.py"""
    setup_content = f'''import os
from setuptools import setup, find_packages

PKG = "{pkg_dir}"
f = os.path.join(os.path.dirname(__file__), PKG, "__init__.py")
V = "{version}"
if os.path.exists(f):
    with open(f) as fp:
        V = next((l.split('"')[1] for l in fp if l.startswith("__version__")), V)

rf = os.path.join(os.path.dirname(__file__), "requirements.txt")
REQ = []
if os.path.exists(rf):
    with open(rf) as fp:
        REQ = [l.strip() for l in fp if l.strip() and not l.startswith("#")]

rm = os.path.join(os.path.dirname(__file__), "README.md")
LD = "{name}"
if os.path.exists(rm):
    with open(rm, encoding="utf-8") as fp:
        LD = fp.read()

setup(
    name="{pypi_name}",
    version=V,
    description="{name}",
    long_description=LD,
    long_description_content_type="text/markdown",
    author="Ldxs (wUwproject)",
    author_email="wuwofc@yeah.net",
    url="https://github.com/Ldxs001/workbuddy-skills",
    packages=find_packages(include=[PKG, PKG + ".*"]),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=REQ,
    entry_points={{"console_scripts": ["{pypi_name}=main:main"]}},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
'''
    with open(os.path.join(build_dir, "setup.py"), "w", encoding="utf-8") as f:
        f.write(setup_content)


def write_pyproject_toml(build_dir: str):
    """生成 pyproject.toml — 防止 setuptools>=61 把 description 标记为 Dynamic"""
    with open(os.path.join(build_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write('[build-system]\nrequires = ["setuptools>=61"]\nbuild-backend = "setuptools.build_meta"\n')


def write_manifest(build_dir: str, pkg_dir: str):
    """生成 MANIFEST.in"""
    lines = [
        "include pyproject.toml",
        "include requirements.txt",
        "include README.md",
        "include LICENSE",
        "include setup.py",
        "include main.py",
        f"graft {pkg_dir}",
        "prune __pycache__",
        "prune *.pyc",
    ]
    with open(os.path.join(build_dir, "MANIFEST.in"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def get_token() -> str:
    """获取 PyPI token"""
    # 先尝试从 git remote 提取
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10
        )
        rmt = r.stdout.strip()
        if "//" in rmt and "@" in rmt:
            tp = rmt.split("//")[1].split("@")[0]
            if ":" in tp:
                return tp.split(":")[1]
    except Exception:
        pass
    # 尝试环境变量
    token = os.environ.get("PYPI_TOKEN", "")
    if token:
        return token
    # 尝试 .pypirc
    pypirc = os.path.expanduser("~/.pypirc")
    if os.path.exists(pypirc):
        with open(pypirc) as f:
            for line in f:
                if "password =" in line:
                    return line.split("=", 1)[1].strip()
    return ""


def verify_wheel_metadata(build_dir: str, pypi_name: str, version: str) -> bool:
    """验证 wheel 元数据包含 long_description"""
    whl_name = f"{pypi_name.replace('-', '_')}-{version}-py3-none-any.whl"
    whl_path = os.path.join(build_dir, "dist", whl_name)
    if not os.path.exists(whl_path):
        print(f"  ❌ wheel 文件未找到: {whl_path}")
        return False
    with zipfile.ZipFile(whl_path) as zf:
        for mf in zf.namelist():
            if mf.endswith("METADATA"):
                meta = zf.read(mf).decode("utf-8")
                if "Description:" in meta or "Description-Content-Type:" in meta:
                    return True
                print(f"  ⚠️  警告: 元数据缺少 Description 字段")
                return False
    return False


def main():
    if len(sys.argv) < 4:
        print("用法: pypi_publish.py <source_dir> <name> <version> [--pypi-name NAME]")
        sys.exit(1)

    src_dir = sys.argv[1]
    name = sys.argv[2]
    version = sys.argv[3]
    # 可选自定义 PyPI 包名
    pypi_name = f"{name}-ldxs"
    if "--pypi-name" in sys.argv:
        idx = sys.argv.index("--pypi-name")
        if idx + 1 < len(sys.argv):
            pypi_name = sys.argv[idx + 1]

    print(f":: PyPI Publish — {name} v{version} -> {pypi_name}")

    if not os.path.isdir(src_dir):
        print(f"  ❌ 源目录不存在: {src_dir}")
        sys.exit(1)

    # 创建隔离构建目录
    build_dir = os.path.join(tempfile.gettempdir(), f"pypi_build_{name}_{version}")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    shutil.copytree(src_dir, build_dir, symlinks=False,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "dist", "build", "*.egg-info"))

    # 动态检测包目录
    pkg_dir = find_pkg_dir(build_dir)
    if not pkg_dir:
        print(f"  ❌ 未检测到包目录（缺少 __init__.py）")
        shutil.rmtree(build_dir, ignore_errors=True)
        sys.exit(1)
    print(f"  📦 检测到包目录: {pkg_dir}")

    # 生成打包配置
    write_pyproject_toml(build_dir)
    print(f"  ✅ 生成 pyproject.toml (防止 Dynamic description)")
    write_setup_py(build_dir, pkg_dir, name, version, pypi_name)
    print(f"  ✅ 生成 setup.py")
    write_manifest(build_dir, pkg_dir)
    print(f"  ✅ 生成 MANIFEST.in")

    # 构建 wheel
    print(f"  🏗️  构建 {pypi_name} v{version}...")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        cwd=build_dir, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ❌ 构建失败: {result.stderr[:300]}")
        shutil.rmtree(build_dir, ignore_errors=True)
        sys.exit(1)

    # 验证元数据
    if verify_wheel_metadata(build_dir, pypi_name, version):
        print(f"  ✅ 元数据验证通过 (含 Description)")
    else:
        print(f"  ⚠️  元数据缺少 Description，PyPI 上可能不显示项目说明")

    # 获取 token
    token = get_token()
    if not token:
        print(f"  ⚠️  未找到 PyPI token，跳过上传")
        print(f"  📝 wheel 位于: {build_dir}/dist/")
        shutil.rmtree(build_dir, ignore_errors=True)
        sys.exit(0)

    # 上传
    whl_name = f"{pypi_name.replace('-', '_')}-{version}-py3-none-any.whl"
    whl_path = os.path.join(build_dir, "dist", whl_name)
    if os.path.exists(whl_path):
        print(f"  上传到 PyPI...")
        result = subprocess.run(
            [sys.executable, "-m", "twine", "upload", "--disable-progress",
             whl_path, "-u", "__token__", "-p", token],
            cwd=build_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  ✅ https://pypi.org/project/{pypi_name}/")
        else:
            print(f"  ❌ 上传失败: {result.stderr[:300]}")

    # 清理
    shutil.rmtree(build_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
