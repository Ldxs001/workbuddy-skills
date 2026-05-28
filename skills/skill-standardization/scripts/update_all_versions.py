#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性更新所有版本相关文件。

用法：
  python update_all_versions.py --skill skill-standardization --version 2.38.8 --confirm
  python update_all_versions.py --skill universal-file-ops --version 1.2.0 --confirm

注意：--confirm 参数是必须的，防止误执行。
"""

import argparse
import json, os, re


def update_skill_standardization(new_version: str) -> bool:
    """更新 skill-standardization 的 _meta.json 和 changelog.md"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ok = True

    # 1. _meta.json
    meta_path = os.path.join(base_dir, "_meta.json")
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        old_version = m.get("version", "?")
        m["version"] = new_version
        m["description"] = m.get("description", "").replace(old_version, new_version)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[OK] skill-standardization/_meta.json: {old_version} → {new_version}")
    except Exception as e:
        print(f"[ERROR] _meta.json 更新失败: {e}")
        ok = False

    # 2. changelog.md 中最近一个版本条目
    cl_path = os.path.join(base_dir, "references", "changelog.md")
    try:
        with open(cl_path, "r", encoding="utf-8") as f:
            cl = f.read()
        # 替换最近一个版本条目标题中的版本号
        pattern = rf"## v{re.escape(old_version)} "
        replacement = f"## v{new_version} "
        cl_new = re.sub(pattern, replacement, cl, count=1)
        if cl_new != cl:
            with open(cl_path, "w", encoding="utf-8") as f:
                f.write(cl_new)
            print(f"[OK] changelog.md 最近版本标题: {old_version} → {new_version}")
        else:
            print(f"[WARN] changelog.md 中未找到 v{old_version} 条目，跳过")
    except Exception as e:
        print(f"[ERROR] changelog.md 更新失败: {e}")
        ok = False

    return ok


def update_universal_file_ops(new_version: str) -> bool:
    """更新 universal-file-ops 的 _meta.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta_path = os.path.join(base_dir, "..", "universal-file-ops", "_meta.json")
    meta_path = os.path.abspath(meta_path)
    if not os.path.exists(meta_path):
        print(f"[ERROR] universal-file-ops 不存在: {meta_path}")
        return False
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        old_version = m.get("version", "?")
        m["version"] = new_version
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[OK] universal-file-ops/_meta.json: {old_version} → {new_version}")
        return True
    except Exception as e:
        print(f"[ERROR] universal-file-ops 更新失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="一次性更新指定技能的版本号（_meta.json + changelog）",
    )
    parser.add_argument("--skill", required=True,
                        choices=["skill-standardization", "universal-file-ops"],
                        help="目标技能名称")
    parser.add_argument("--version", required=True,
                        help="新版本号（如 2.38.8）")
    parser.add_argument("--confirm", action="store_true",
                        help="⚠️ 必须提供此参数才能执行（防止误操作）")

    args = parser.parse_args()

    if not args.confirm:
        print("⚠️ 缺少 --confirm 参数。修改版本号是破坏性操作，请确认后加上 --confirm 再执行。")
        print(f"   示例: python update_all_versions.py --skill {args.skill} --version {args.version} --confirm")
        return 1

    print(f"即将更新 {args.skill} → {args.version}")
    if args.skill == "skill-standardization":
        ok = update_skill_standardization(args.version)
    elif args.skill == "universal-file-ops":
        ok = update_universal_file_ops(args.version)
    else:
        ok = False

    if ok:
        print("ALL DONE")
        return 0
    else:
        print("部分操作失败，请检查")
        return 1


if __name__ == "__main__":
    exit(main())
