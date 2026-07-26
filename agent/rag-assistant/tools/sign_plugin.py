"""
SM3 插件签名工具
对插件目录下所有 .py 文件和 plugin.json 计算 SM3 哈希，写入 sm3_hash 字段

用法:
  python tools/sign_plugin.py --dir plugins/web_search/
  python tools/sign_plugin.py --dir plugins/builtin/web_search/
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def compute_hash(plugin_dir: Path) -> str:
    """计算插件目录所有代码文件的 SM3 哈希

    注意：计算 plugin.json 时会先去掉已有的 sm3_hash 字段（如果有），
    避免签名自我引用。生成的哈希不包含 sm3_hash 字段自身。
    """
    files = sorted(
        p for p in plugin_dir.rglob("*")
        if p.suffix == ".py" or p.name == "plugin.json"
    )
    # 排除 data/、__pycache__、.git、*.pyc
    files = [
        p for p in files
        if not any(part.startswith((".", "__", "_")) for part in p.relative_to(plugin_dir).parts)
        and p.suffix != ".pyc"
    ]

    if not files:
        print("错误：目录中没有找到 .py 文件或 plugin.json")
        sys.exit(1)

    print(f"签名文件 ({len(files)} 个):")
    for f in files:
        print(f"  {f.relative_to(plugin_dir)}")

    hasher = hashlib.new('sm3')
    for f in files:
        if f.name == "plugin.json":
            # 读 plugin.json，去掉已有 sm3_hash 后再参与哈希计算
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
    parser = argparse.ArgumentParser(description="SM3 插件签名工具")
    parser.add_argument("--dir", required=True, help="插件目录路径")
    args = parser.parse_args()

    plugin_dir = Path(args.dir).resolve()
    if not plugin_dir.is_dir():
        print(f"错误：目录不存在: {plugin_dir}")
        sys.exit(1)

    plugin_json = plugin_dir / "plugin.json"
    if not plugin_json.exists():
        print(f"错误：目录中缺少 plugin.json: {plugin_dir}")
        sys.exit(1)

    # 计算哈希
    hash_value = compute_hash(plugin_dir)
    print(f"\nSM3 哈希: {hash_value}")

    # 写入 plugin.json
    with open(plugin_json, "r", encoding="utf-8") as f:
        meta = json.load(f)

    meta["sm3_hash"] = hash_value

    with open(plugin_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"已写入 {plugin_json.relative_to(plugin_dir.parent.parent)} 的 sm3_hash 字段")
    print("签名完成！")


if __name__ == "__main__":
    main()
