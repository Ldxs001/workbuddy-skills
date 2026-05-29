#!/usr/bin/env python3
"""patch_chain_manager.py - 给 chain_manager.py 加入备份机制和版本管理"""
import re

p = r"C:\Users\sm001\.workbuddy\skills\skill-sub\scripts\chain_manager.py"
with open(p, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 在 ensure_dirs() 后面插入 backup_chain 函数 ==========
# 找到 ensure_dirs 函数结尾
ensure_end = content.find("def load_index():")
if ensure_end == -1:
    print("❌ 未找到 ensure_dirs 结尾")
    exit(1)

backup_func = '''
def backup_chain(name, reason="auto"):
    """在覆盖/删除前备份调用链到 backups/ 目录。

    备份路径：CHAIN_HOME / "backups" / name / timestamp.json
    同时维护 versions.json（版本索引）。
    """
    chain = load_chain(name)
    if not chain:
        return  # 没有数据，无需备份

    # 确保备份目录存在
    backup_dir = CHAIN_HOME / "backups" / name
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 版本号自增
    versions_file = backup_dir / "versions.json"
    versions = []
    if versions_file.exists():
        versions = json.loads(versions_file.read_text(encoding="utf-8"))

    new_version = len(versions) + 1
    chain["_backup_version"] = new_version
    chain["_backup_reason"] = reason
    chain["_backup_time"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # 保存备份文件（保留最近 10 个）
    backup_file = backup_dir / f"v{new_version:03d}_{chain.get('updated_at','')[:10]}.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(chain, f, ensure_ascii=False, indent=2)

    # 更新版本索引
    versions.append({
        "version": new_version,
        "reason": reason,
        "time": chain["_backup_time"],
        "file": backup_file.name
    })
    # 只保留最近 20 个版本索引
    versions = versions[-20:]
    with open(versions_file, "w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)

    # 清理旧备份文件（保留最新 10 个）
    all_backups = sorted(backup_dir.glob("v*.json"), key=lambda f: f.name)
    for old_file in all_backups[:-10]:
        old_file.unlink()

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
    # 去掉备份元数据
    chain_data.pop("_backup_version", None)
    chain_data.pop("_backup_reason", None)
    chain_data.pop("_backup_time", None)
    return chain_data, None

'''

content = content[:ensure_end] + backup_func + content[ensure_end:]

# ========== 2. 在 save_chain 开头加入备份调用 ==========
save_chain_def = content.find("def save_chain(chain_data):")
if save_chain_def == -1:
    print("❌ 未找到 save_chain")
    exit(1)

# 在 save_chain 函数体开头（ensure_dirs() 之后）插入备份
# 找到 ensure_dirs() 行
save_body_start = content.find("    ensure_dirs()\n", save_chain_def)
if save_body_start == -1:
    print("❌ 未找到 save_chain 中的 ensure_dirs")
    exit(1)

insert_pos = save_body_start + len("    ensure_dirs()\n")
backup_call = """    # 备份机制：覆盖前先备份
    name = chain_data["name"]
    if load_chain(name):
        backup_chain(name, reason="overwrite")

"""
content = content[:insert_pos] + backup_call + content[insert_pos:]

# ========== 3. 在 cmd_delete 中删除前加入备份 ==========
# 找到 cmd_delete 函数
cmd_delete_def = content.find("def cmd_delete(args):")
if cmd_delete_def == -1:
    print("❌ 未找到 cmd_delete")
    exit(1)

# 在 cmd_delete 中，检查链存在之后、删除之前插入备份
# 找到 "if not args.force:" 之前
force_check = content.find("    if not args.force:\n", cmd_delete_def)
if force_check == -1:
    print("❌ 未找到 cmd_delete 中的 force 检查")
    exit(1)

# 往前找到 chain = load_chain 之后的位置
# 直接在 force_check 之前插入备份
backup_delete = """
    # 备份机制：删除前先备份
    backup_chain(args.name, reason="delete")
"""

insert_pos = force_check
content = content[:insert_pos] + backup_delete + content[insert_pos:]

# ========== 4. 在 cmd_create 中（重名时）提示有备份 ==========
# 找到 cmd_create 中的重名检查
create_duplicate = content.find('        print(f"⚠️ 调用链 \\'{args.name}\\' 已存在')
if create_duplicate == -1:
    print("⚠️ 未找到 cmd_create 重名检查（可能已修改）")
else:
    # 在重名错误信息之后插入备份提示
    msg_end = content.find("\\n", create_duplicate + 100)
    if msg_end != -1:
        backup_hint = '    # 检查是否有备份可用\n    backups = list_backups(args.name)\n    if backups:\n        print(f"   提示: 该链有 {len(backups)} 个备份版本，可用 restore 命令恢复")\n'
        # 找到 return 1 之前插入
        ret_pos = content.find("        return 1\n", create_duplicate)
        if ret_pos != -1:
            content = content[:ret_pos] + backup_hint + content[ret_pos:]

# ========== 5. 添加 list-backups 和 restore 子命令 ==========
# 在 main() 的 parsers 里添加新子命令
# 找到 "p_del =" 这一行
p_del_pos = content.find("    p_del = subparsers.add_parser(\"delete\"")
if p_del_pos == -1:
    print("❌ 未找到 delete subparser")
    exit(1)

# 在 delete 之后插入新子命令
new_cmds = '''
    p_backups = subparsers.add_parser("list-backups", help="列出调用链的备份版本")
    p_backups.add_argument("--name", required=True, help="调用链名称")

    p_restore = subparsers.add_parser("restore", help="从备份恢复调用链")
    p_restore.add_argument("--name", required=True, help="调用链名称")
    p_restore.add_argument("--version", type=int, required=True, help="要恢复的版本号")
    p_restore.add_argument("--force", "-f", action="store_true", help="强制覆盖当前版本")

'''

insert_pos = content.find("\n", p_del_pos + 100) + 1
content = content[:insert_pos] + new_cmds + content[insert_pos:]

# ========== 6. 在 commands 字典里添加新命令处理函数 ==========
# 找到 commands 字典
commands_dict = content.find("    commands = {\n")
if commands_dict == -1:
    print("❌ 未找到 commands 字典")
    exit(1)

# 在 commands 字典结尾（} 之前）添加新命令
commands_end = content.find("\n    }\n", commands_dict)
if commands_end == -1:
    print("❌ 未找到 commands 字典结尾")
    exit(1)

new_entries = """        "list-backups": cmd_list_backups,
        "restore": cmd_restore,
    """

content = content[:commands_end] + "        \"list-backups\": cmd_list_backups,\n        \"restore\": cmd_restore,\n    " + content[commands_end:]

# ========== 7. 添加 cmd_list_backups 和 cmd_restore 函数 ==========
# 在 cmd_delete 函数之后插入
cmd_delete_end = content.find("\n\ndef cmd_config(args):")
if cmd_delete_end == -1:
    # 尝试另一种找法
    cmd_delete_end = content.find("\ndef cmd_", content.find("def cmd_delete") + 1)
    if cmd_delete_end == -1:
        print("❌ 未找到 cmd_delete 结尾")
        exit(1)

new_funcs = '''

def cmd_list_backups(args):
    """列出调用链的备份版本"""
    backups = list_backups(args.name)
    if not backups:
        print(f"📋 调用链 '{args.name}' 没有备份")
        return 0

    print(f"📋 调用链 '{args.name}' 的备份版本（共 {len(backups)} 个）:")
    print(f"{'='*60}")
    for v in backups:
        print(f"  v{v['version']:03d}  {v['time']}  {v['reason']}")

    print(f"\n  恢复命令: python chain_manager.py restore --name \"{args.name}\" --version <版本号>")
    return 0

def cmd_restore(args):
    """从备份恢复调用链"""
    chain_data, err = restore_backup(args.name, args.version)
    if err:
        print(f"❌ {err}")
        return 1

    if not args.force:
        print(f"⚠️ 即将恢复 '{args.name}' 到版本 {args.version}")
        print(f"   描述: {chain_data.get('description', '')}")
        print(f"   步骤数: {len(chain_data.get('steps', []))}")
        print(f"   使用 --force 确认恢复")
        return 0

    save_chain(chain_data)
    print(f"✅ 已恢复 '{args.name}' 到版本 {args.version}")
    return 0

'''

content = content[:cmd_delete_end] + new_funcs + content[cmd_delete_end:]

# 保存
with open(p, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ chain_manager.py 已更新：备份机制 + 版本管理")
print("   新增命令: list-backups, restore")
'''