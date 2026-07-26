"""
SM3 插件签名验证工具
验证插件目录的 SM3 哈希是否与 plugin.json 中的 sm3_hash 一致

用法:
  python tools/verify_plugin.py --dir plugins/builtin/web_search/

返回码:
  0 = 验证通过
  1 = 哈希不匹配
  2 = 文件不存在/损坏
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def compute_hash(plugin_dir: Path) -> str:
    """计算插件目录所有代码文件的 SM3 哈希

    注意：计算 plugin.json 时会先去掉 sm3_hash 字段，
    避免签名自我引用导致哈希不匹配。
    """
    files = sorted(
        p for p in plugin_dir.rglob("*")
        if p.suffix == ".py" or p.name == "plugin.json"
    )
    files = [
        p for p in files
        if not any(part.startswith((".", "__", "_")) for part in p.relative_to(plugin_dir).parts)
        and p.suffix != ".pyc"
    ]

    if not files:
        return ""

    hasher = hashlib.new('sm3')
    for f in files:
        if f.name == "plugin.json":
            # 读 plugin.json，去掉 sm3_hash 后再参与哈希计算
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data.pop("sm3_hash", None)
                cleaned = json.dumps(data, ensure_ascii=False, sort_keys=True)
                hasher.update(cleaned.encode("utf-8"))
            except Exception:
                hasher.update(f.read_bytes())
        else:
            hasher.update(f.read_bytes())
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="SM3 插件签名验证工具")
    parser.add_argument("--dir", required=True, help="插件目录路径")
    args = parser.parse_args()

    plugin_dir = Path(args.dir).resolve()
    plugin_json = plugin_dir / "plugin.json"

    if not plugin_dir.is_dir():
        print(f"错误：目录不存在: {plugin_dir}")
        sys.exit(2)

    if not plugin_json.exists():
        print(f"错误：目录中缺少 plugin.json: {plugin_dir}")
        sys.exit(2)

    # 读取 plugin.json
    try:
        with open(plugin_json, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except json.JSONDecodeError:
        print("错误：plugin.json 格式损坏")
        sys.exit(2)

    expected = meta.get("sm3_hash", "")
    if not expected:
        print("警告：plugin.json 中 sm3_hash 为空，跳过验证")
        sys.exit(0)

    actual = compute_hash(plugin_dir)
    print(f"期望: {expected}")
    print(f"实际: {actual}")

    if actual == expected:
        print("✓ 签名验证通过")
        sys.exit(0)
    else:
        print("✗ 签名验证失败：哈希不匹配")
        print("  文件可能被篡改或损坏")
        sys.exit(1)


if __name__ == "__main__":
    main()
