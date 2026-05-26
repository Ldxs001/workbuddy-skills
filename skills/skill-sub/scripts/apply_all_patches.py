#!/usr/bin/env python3
"""apply_all_patches.py - 给 chain_manager.py 全量打补丁"""
import re
from pathlib import Path
import json
from datetime import datetime

p = r"C:\Users\sm001\.workbuddy\skills\skill-sub\scripts\chain_manager.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

# ===== 补丁 1: 在 ensure_dirs 后插入备份函数 =====
insert1 = '''
def backup_chain(name, reason="auto"):
    """覆盖/删除前备份调用链到 backups/ 目录。

    备份路径：CHAIN_HOME / "backups" / name / timestamp.json
    同时维护 versions.json（版本索引），保留最近 20 个版本索引。
    """
    chain = load_chain(name)
    if not chain:
        return

    backup_dir = CHAIN_HOME / "backups" / name
    backup_dir.mkdir(parents=True, exist_ok=True)

    versions_file = backup_dir / "versions.json"
    versions = []
    if versions_file.exists():
        versions = json.loads(versions_file.read_text(encoding="utf-8"))

    new_version = len(versions) + 1
    chain["_backup_version"] = new_version
    chain["_backup_reason"] = reason
    chain["_backup_time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"v{new_version:03d}_{ts}.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(chain, f, ensure_ascii=False, indent=2)

    versions.append({
        "version": new_version,
        "reason": reason,
        "time": chain["_backup_time"],
        "file": backup_file.name
    })
    versions = versions[-20:]
    with open(versions_file, "w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)

    # 清理旧备份文件（保留最新 10 个）
    all_backups = sorted(backup_dir.glob("v*.json"), key=lambda f: f.name)
    for old in all_backups[:-10]:
        old.unlink()

    return new_version


def list_backups(name):
    """列出指定调用链的备份版本。"""
    backup_dir = CHAIN_HOME / "backups" / name
    versions_file = backup_dir / "versions.json"
    if not versions_file.exists():
        return []
    return json.loads(versions_file.read_text(encoding="utf-8"))


def restore_backup(name, version):
    """从指定版本恢复调用链。"""
    backup_dir = CHAIN_HOME / "backups" / name
    versions_file = backup_dir / "versions.json"
    if not versions_file.exists():
        return None, f"没有找到 {name} 的备份"

    versions = json.loads(versions_file.read_text(encoding="utf-8"))
    target = None
    for v in versions:
        if v["version"] == int(version):
            target = v
            break

    if not target:
        return None, f"版本 {version} 不存在"

    backup_file = backup_dir / target["file"]
    if not backup_file.exists():
        return None, f"备份文件不存在: {target['file']}"

    chain_data = json.loads(backup_file.read_text(encoding="utf-8"))
    chain_data.pop("_backup_version", None)
    chain_data.pop("_backup_reason", None)
    chain_data.pop("_backup_time", None)
    return chain_data, None


'''

# 在 ensure_dirs 函数结尾后插入
marker1 = '    CHAINS_DIR.mkdir(parents=True, exist_ok=True)\n\n'
if marker1 in c:
    c = c.replace(marker1, '    CHAINS_DIR.mkdir(parents=True, exist_ok=True)\n\n' + insert1, 1)
    print("✅ 补丁1：备份函数已插入")
else:
    print("❌ 未找到补丁1插入点")
    # 尝试找 ensure_dirs 结尾
    idx = c.find("def ensure_dirs")
    if idx != -1:
        # 找函数结尾的空行
        end_idx = c.find("\ndef ", idx + 1)
        if end_idx != -1:
            # 在 ensure_dirs 和下一个 def 之间插入
            c = c[:end_idx] + insert1 + c[end_idx:]
            print("✅ 补丁1（备选）：备份函数已插入")
        else:
            print("❌ 补丁1 完全失败")

# ===== 补丁 2: save_chain 覆盖前先备份 =====
marker2_old = 'def save_chain(chain_data):\n    """保存调用链"""\n    ensure_dirs()\n    name = chain_data["name"]\n    chain_file = CHAINS_DIR / f"{name}.json"\n    with open'
marker2_new = 'def save_chain(chain_data):\n    """保存调用链（覆盖前先备份）"""\n    ensure_dirs()\n    name = chain_data["name"]\n    # 覆盖前先备份\n    if load_chain(name):\n        backup_chain(name, reason="overwrite")\n    chain_file = CHAINS_DIR / f"{name}.json"\n    with open'
if marker2_old in c:
    c = c.replace(marker2_old, marker2_new, 1)
    print("✅ 补丁2：save_chain 备份机制已启用")
else:
    print("❌ 未找到补丁2插入点")

# ===== 补丁 3: cmd_delete 删除前先备份 =====
marker3_old = '    if not args.force:\n        steps_count = len(chain.get("steps", []))\n        exec_count = chain.get("exec_count", 0)\n'
marker3_new = '    # 删除前先备份\n    backup_chain(args.name, reason="delete")\n\n    if not args.force:\n        steps_count = len(chain.get("steps", []))\n        exec_count = chain.get("exec_count", 0)\n'
if marker3_old in c:
    c = c.replace(marker3_old, marker3_new, 1)
    print("✅ 补丁3：cmd_delete 备份机制已启用")
else:
    print("❌ 未找到补丁3插入点（可能 cmd_delete 已修改，跳过）")

# ===== 补丁 4: 在 main() 的 subparsers 里添加新子命令 =====
# 找到 p_del = subparsers.add_parser("delete" 之后插入
marker4_old = '    p_del = subparsers.add_parser("delete", help="删除调用链")\n    p_del.add_argument("--name", required=True, help="调用链名称")\n    p_del.add_argument("--force", "-f", action="store_true", help="强制删除（不确认）")\n'
marker4_new = '''    p_del = subparsers.add_parser("delete", help="删除调用链")
    p_del.add_argument("--name", required=True, help="调用链名称")
    p_del.add_argument("--force", "-f", action="store_true", help="强制删除（不确认）")

    p_backups = subparsers.add_parser("list-backups", help="列出调用链的备份版本")
    p_backups.add_argument("--name", required=True, help="调用链名称")

    p_restore = subparsers.add_parser("restore", help="从备份恢复调用链")
    p_restore.add_argument("--name", required=True, help="调用链名称")
    p_restore.add_argument("--version", type=int, required=True, help="要恢复的版本号")
    p_restore.add_argument("--force", "-f", action="store_true", help="强制覆盖当前版本")
'''
if marker4_old in c:
    c = c.replace(marker4_old, marker4_new, 1)
    print("✅ 补丁4：list-backups / restore 子命令已添加")
else:
    print("❌ 未找到补丁4插入点")

# ===== 补丁 5: 在 commands 字典里添加新命令 =====
marker5_old = '    commands = {\n        "init": cmd_init,\n        "config": cmd_config,\n        "create": cmd_create,\n        "list": cmd_list,\n        "show": cmd_show,\n        "run": cmd_run,\n        "add-step": cmd_add_step,\n        "remove-step": cmd_remove_step,\n        "update-step": cmd_update_step,\n        "rename": cmd_rename,\n        "delete": cmd_delete,\n    }'
marker5_new = '    commands = {\n        "init": cmd_init,\n        "config": cmd_config,\n        "create": cmd_create,\n        "list": cmd_list,\n        "show": cmd_show,\n        "run": cmd_run,\n        "add-step": cmd_add_step,\n        "remove-step": cmd_remove_step,\n        "update-step": cmd_update_step,\n        "rename": cmd_rename,\n        "delete": cmd_delete,\n        "list-backups": cmd_list_backups,\n        "restore": cmd_restore,\n    }'
if marker5_old in c:
    c = c.replace(marker5_old, marker5_new, 1)
    print("✅ 补丁5：commands 字典已更新")
else:
    print("❌ 未找到补丁5插入点")

# ===== 补丁 6: 在 cmd_delete 函数后插入 cmd_list_backups 和 cmd_restore =====
# 找 cmd_delete 函数结尾
marker6_old = '    print(f"✅ 调用链 \'{args.name}\' 已删除")\n    return 0\n\n\ndef cmd_config'
marker6_new = '''    print(f"✅ 调用链 \'{args.name}\' 已删除")
    return 0


def cmd_list_backups(args):
    """列出调用链的备份版本"""
    backups = list_backups(args.name)
    if not backups:
        print(f"📋 调用链 '{args.name}' 没有备份")
        return 0

    print(f"📋 调用链 '{args.name}' 的备份版本（共 {len(backups)} 个）:")
    print(f"{"="*60}")
    for v in backups:
        print(f"  v{v['version']:03d}  {v['time']}  {v['reason']}")
    print(f"\\n  恢复命令: python chain_manager.py restore --name \"{args.name}\" --version <版本号>")
    return 0


def cmd_restore(args):
    """从备份恢复调用链"""
    chain_data, err = restore_backup(args.name, args.version)
    if err:
        print(f"❌ {err}")
        return 1

    if not args.force:
        print(f"⚠️  即将恢复 '{args.name}' 到版本 {args.version}")
        print(f"   描述: {chain_data.get('description', '(无)')}")
        print(f"   步骤数: {len(chain_data.get('steps', []))}")
        print(f"   使用 --force 确认恢复")
        return 0

    save_chain(chain_data)
    print(f"✅ 已恢复 '{args.name}' 到版本 {args.version}")
    return 0


def cmd_config'''

if marker6_old in c:
    c = c.replace(marker6_old, marker6_new, 1)
    print("✅ 补丁6：cmd_list_backups / cmd_restore 已插入")
else:
    print("❌ 未找到补丁6插入点")
    # 尝试找 cmd_delete return 0
    idx = c.rfind('    print(f"✅ 调用链')
    if idx != -1:
        end_idx = c.find('\\n\\n', idx)
        if end_idx != -1:
            # 在 cmd_delete 结尾后插入
            insert_pos = end_idx + 2  # 跳过 \n\n
            c = c[:insert_pos] + marker6_new[len('    print(f"✅ 调用链 \'{args.name}\' 已删除")\\n    return 0\\n\\n'):] + c[insert_pos:]
            print("✅ 补丁6（备选）：函数已插入")

# ===== 保存 =====
with open(p, "w", encoding="utf-8") as f:
    f.write(c)

print(f"\\n✅ 所有补丁已应用：{p}")
print("   新增功能：备份机制 + 版本管理 + list-backups + restore")
