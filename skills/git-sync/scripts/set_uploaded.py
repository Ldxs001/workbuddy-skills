#!/usr/bin/env python3
"""标记 manifest.json 中指定 skill 为 uploaded=true"""
import json, sys

def main():
    if len(sys.argv) < 3:
        return
    manifest_file = sys.argv[1]
    skill_name = sys.argv[2]
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("repos", {}).get("workbuddy-skills", {}).get("items", {})
        if skill_name in items and isinstance(items[skill_name], dict):
            items[skill_name]["uploaded"] = True
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"  ✅ 已标记 {skill_name} 为 uploaded")
    except Exception as e:
        pass

if __name__ == "__main__":
    main()
