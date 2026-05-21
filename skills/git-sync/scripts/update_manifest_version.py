import json, os

manifest_path = os.path.expanduser("~/.workbuddy/skills/git-sync/manifest.json")
with open(manifest_path, "r", encoding="utf-8") as f:
    data = json.load(f)

repo = data["repos"]["workbuddy-skills"]
items = repo["items"]

updated = []
for name, item in items.items():
    meta_path = os.path.expanduser(f"~/.workbuddy/skills/{name}/_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        ver = meta.get("version", "1.0.0")
    else:
        ver = "1.0.0"
    item["version"] = ver
    updated.append(f"  {name}: {ver}")

# 写回
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("manifest.json version 字段已更新：")
for u in updated:
    print(u)
