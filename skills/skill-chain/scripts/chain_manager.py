#!/usr/bin/env python3
"""
chain_manager.py - Skill Chain Manager v1.0.0
调用链管理核心脚本：创建、查询、更新、删除、执行调用链。

零外部依赖，仅使用 Python 标准库。
跨平台支持 Windows/Linux/macOS。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# 路径配置
# ============================================================

def get_chain_home():
    """获取调用链数据目录"""
    env_home = os.environ.get("SKILL_CHAIN_HOME")
    if env_home:
        return Path(env_home)
    # 默认路径
    default = Path.home() / ".workbuddy" / "skill-chain"
    return default


def get_skills_dir():
    """获取已安装技能目录"""
    env_dir = os.environ.get("WORKBUDDY_SKILLS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".workbuddy" / "skills"


CHAIN_HOME = get_chain_home()
CHAINS_DIR = CHAIN_HOME / "chains"
INDEX_FILE = CHAINS_DIR / "index.json"
CONFIG_FILE = CHAIN_HOME / "config.json"


# ============================================================
# 工具函数
# ============================================================

def ensure_dirs():
    """确保数据目录存在"""
    CHAINS_DIR.mkdir(parents=True, exist_ok=True)


def load_index():
    """加载索引文件"""
    if not INDEX_FILE.exists():
        return {}
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(index):
    """保存索引文件"""
    ensure_dirs()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def load_chain(name):
    """加载指定调用链"""
    index = load_index()
    if name not in index:
        return None
    chain_file = Path(index[name])
    if not chain_file.exists():
        return None
    with open(chain_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_chain(chain_data):
    """保存调用链"""
    ensure_dirs()
    name = chain_data["name"]
    chain_file = CHAINS_DIR / f"{name}.json"
    with open(chain_file, "w", encoding="utf-8") as f:
        json.dump(chain_data, f, ensure_ascii=False, indent=2)
    # 更新索引
    index = load_index()
    index[name] = str(chain_file)
    save_index(index)


def name_to_filename(name):
    """将调用链名称转换为安全的文件名"""
    # 替换不安全字符
    safe = name.replace("/", "-").replace("\\", "-").replace(":", "-")
    safe = safe.replace(" ", "_").replace("*", "").replace("?", "").replace('"', "")
    safe = safe.replace("<", "").replace(">", "").replace("|", "")
    return safe[:100]  # 限制长度


def now_iso():
    """返回当前时间的 ISO 格式"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def validate_chain(chain_data):
    """验证调用链数据结构"""
    errors = []
    required_fields = ["name", "description", "purpose", "steps"]
    for field in required_fields:
        if field not in chain_data or not chain_data[field]:
            errors.append(f"缺少必填字段: {field}")

    if "steps" in chain_data and isinstance(chain_data["steps"], list):
        for i, step in enumerate(chain_data["steps"]):
            step_required = ["skill_name", "step_name", "action"]
            for sf in step_required:
                if sf not in step or not step[sf]:
                    errors.append(f"步骤 {i+1} 缺少必填字段: {sf}")

    return errors


# ============================================================
# 命令实现
# ============================================================

def cmd_init(args):
    """初始化数据目录"""
    ensure_dirs()
    if not CONFIG_FILE.exists():
        default_config = {
            "version": "1.0.0",
            "default_behavior": {
                "auto_save": False,
                "confirm_before_run": True,
                "stop_on_error": True
            }
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
    print(f"✅ 初始化完成")
    print(f"   数据目录: {CHAIN_HOME}")
    print(f"   调用链目录: {CHAINS_DIR}")


def cmd_create(args):
    """创建调用链"""
    ensure_dirs()

    # 解析步骤
    steps = []
    if args.steps:
        try:
            steps = json.loads(args.steps)
        except json.JSONDecodeError as e:
            print(f"❌ 步骤 JSON 解析失败: {e}")
            return 1

    # 补全步骤 index
    for i, step in enumerate(steps):
        step.setdefault("index", i + 1)

    chain_data = {
        "name": args.name,
        "description": args.description or "",
        "purpose": args.purpose or "",
        "user_intent": args.user_intent or "",
        "tags": args.tags.split(",") if args.tags else [],
        "steps": steps,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "exec_count": 0
    }

    # 验证
    errors = validate_chain(chain_data)
    if errors:
        print("❌ 数据验证失败:")
        for err in errors:
            print(f"   - {err}")
        return 1

    # 检查重名
    index = load_index()
    if args.name in index:
        print(f"⚠️ 调用链 '{args.name}' 已存在。使用 update-step 或 rename 修改。")
        return 1

    save_chain(chain_data)
    print(f"✅ 调用链已创建: {args.name}")
    print(f"   描述: {args.description or '(无)'}")
    print(f"   步骤数: {len(steps)}")
    print(f"   标签: {', '.join(chain_data['tags']) or '(无)'}")
    return 0


def cmd_list(args):
    """列出所有调用链"""
    index = load_index()
    if not index:
        print("📋 暂无已保存的调用链")
        print("   使用 create 命令创建新调用链")
        return 0

    chains = []
    for name, filepath in index.items():
        chain = load_chain(name)
        if chain:
            # 标签过滤
            if args.tag:
                if args.tag.lower() not in [t.lower() for t in chain.get("tags", [])]:
                    continue
            chains.append(chain)

    if not chains:
        if args.tag:
            print(f"📋 未找到标签为 '{args.tag}' 的调用链")
        else:
            print("📋 暂无已保存的调用链")
        return 0

    # 按更新时间倒序
    chains.sort(key=lambda c: c.get("updated_at", ""), reverse=True)

    print(f"📋 调用链列表（共 {len(chains)} 条）")
    print(f"{'='*70}")
    for c in chains:
        steps_count = len(c.get("steps", []))
        exec_count = c.get("exec_count", 0)
        created = c.get("created_at", "")[:10]
        tags = ", ".join(c.get("tags", []))
        print(f"  📌 {c['name']}")
        print(f"     描述: {c.get('description', '(无)')}")
        print(f"     步骤: {steps_count}步 | 执行: {exec_count}次 | 创建: {created}")
        if tags:
            print(f"     标签: {tags}")
        print()
    return 0


def cmd_show(args):
    """查看调用链详情"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        print("   使用 list 命令查看所有调用链")
        return 1

    print(f"📌 调用链: {chain['name']}")
    print(f"{'='*70}")
    print(f"  描述: {chain.get('description', '(无)')}")
    print(f"  目的: {chain.get('purpose', '(无)')}")
    print(f"  意图: {chain.get('user_intent', '(无)')}")
    tags = ", ".join(chain.get("tags", []))
    if tags:
        print(f"  标签: {tags}")
    print(f"  创建: {chain.get('created_at', '(无)')}")
    print(f"  更新: {chain.get('updated_at', '(无)')}")
    print(f"  执行次数: {chain.get('exec_count', 0)}")

    steps = chain.get("steps", [])
    if steps:
        print(f"\n{'─'*70}")
        print(f"  执行步骤（共 {len(steps)} 步）:")
        print(f"  ┌──────┬─────────────────┬──────────────┬──────────────────────────────┐")
        print(f"  │  序号  │      技能       │    步骤名     │          关键动作             │")
        print(f"  ├──────┼─────────────────┼──────────────┼──────────────────────────────┤")
        for step in steps:
            idx = f"{step.get('index', '-')}".center(4)
            skill = (step.get("skill_name", "")[:15]).ljust(15)
            sname = (step.get("step_name", "")[:12]).ljust(12)
            action = step.get("action", "")[:30]
            deps = step.get("depends_on", [])
            dep_str = f" (依赖:{deps})" if deps else ""
            print(f"  │  {idx}  │ {skill} │ {sname} │ {action}{dep_str:<{28-len(dep_str)}} │")
        print(f"  └──────┴─────────────────┴──────────────┴──────────────────────────────┘")

    # 变量传递关系
    var_steps = [s for s in steps if s.get("variables")]
    if var_steps:
        print(f"\n  变量传递:")
        for s in var_steps:
            v = s.get("variables", {})
            inp = ", ".join(v.get("input", {}).keys()) if v.get("input") else "(无)"
            out = ", ".join(v.get("output", {}).keys()) if v.get("output") else "(无)"
            print(f"    步骤{s['index']}: 输入=[{inp}] → 输出=[{out}]")

    return 0


def cmd_run(args):
    """执行调用链（输出执行计划，实际执行由 AI 完成）"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    steps = chain.get("steps", [])
    if not steps:
        print(f"❌ 调用链 '{args.name}' 没有步骤")
        return 1

    # 检查技能是否已安装
    skills_dir = get_skills_dir()
    missing_skills = []
    for step in steps:
        skill_name = step.get("skill_name", "")
        if skill_name == "(内置)":
            continue
        # 查找技能目录
        skill_found = False
        if skills_dir.exists():
            for entry in skills_dir.iterdir():
                if entry.is_dir():
                    slug = entry.name.lower().replace(" ", "-")
                    if slug == skill_name.lower() or skill_name.lower() in slug:
                        skill_found = True
                        break
        if not skill_found and skill_name:
            missing_skills.append(skill_name)

    print(f"📌 执行调用链: {chain['name']}")
    print(f"{'='*70}")

    if missing_skills:
        print(f"⚠️  以下技能未找到:")
        for ms in missing_skills:
            print(f"   - {ms}")
        print(f"   请先安装缺失的技能")

    # 构建依赖图并确定执行顺序
    exec_order = []
    executed = set()
    remaining = {s["index"]: s for s in steps if s.get("index")}

    while remaining:
        progress = False
        for idx, step in list(remaining.items()):
            deps = step.get("depends_on", [])
            if all(d in executed for d in deps):
                exec_order.append(step)
                executed.add(idx)
                del remaining[idx]
                progress = True

        if not progress and remaining:
            # 循环依赖，强制按顺序加入
            idx = min(remaining.keys())
            exec_order.append(remaining[idx])
            executed.add(idx)
            del remaining[idx]

    # 输出执行计划
    print(f"\n📋 执行计划（{len(exec_order)} 步）:")
    print(f"  ┌──────┬─────────────────┬──────────────┬──────────────────────────────┐")
    print(f"  │  序号  │      技能       │    步骤名     │          关键动作             │")
    print(f"  ├──────┼─────────────────┼──────────────┼──────────────────────────────┤")
    for i, step in enumerate(exec_order, 1):
        idx = str(i).center(4)
        skill = (step.get("skill_name", "")[:15]).ljust(15)
        sname = (step.get("step_name", "")[:12]).ljust(12)
        action = step.get("action", "")[:30]
        print(f"  │  {idx}  │ {skill} │ {sname} │ {action}                            │")
    print(f"  └──────┴─────────────────┴──────────────┴──────────────────────────────┘")

    # 并行机会识别：按依赖层级分组
    # 同一组内的步骤之间没有依赖关系，可以并行
    from collections import defaultdict

    step_map = {s.get("index", 0): s for s in exec_order}
    # 计算每个步骤的最大依赖深度
    depth_cache = {}

    def get_depth(idx):
        if idx in depth_cache:
            return depth_cache[idx]
        step = step_map.get(idx)
        if not step:
            depth_cache[idx] = 0
            return 0
        deps = step.get("depends_on", [])
        if not deps:
            depth_cache[idx] = 0
            return 0
        max_dep_depth = max(get_depth(d) for d in deps)
        depth_cache[idx] = max_dep_depth + 1
        return depth_cache[idx]

    depth_groups = defaultdict(list)
    for step in exec_order:
        d = get_depth(step.get("index", 0))
        depth_groups[d].append(step)

    parallel_groups = [depth_groups[k] for k in sorted(depth_groups.keys())]
    parallel_count = sum(1 for g in parallel_groups if len(g) > 1)
    if parallel_count > 0:
        print(f"\n  ⚡ 并行机会: {parallel_count} 组步骤可并行执行")
        for i, group in enumerate(parallel_groups):
            if len(group) > 1:
                names = [f"步骤{s.get('index', '?')}({s.get('step_name', '')})" for s in group]
                print(f"     并行组{i+1}: {' + '.join(names)}")

    if args.verbose:
        print(f"\n{'─'*70}")
        print(f"  详细执行指令:")
        for i, step in enumerate(exec_order, 1):
            print(f"\n  步骤 {i}: [{step.get('skill_name', '')}] {step.get('step_name', '')}")
            print(f"    动作: {step.get('action', '')}")
            if step.get("detail"):
                print(f"    详情: {step['detail']}")
            if step.get("condition"):
                print(f"    条件: {step['condition']}")
            v = step.get("variables", {})
            if v:
                if v.get("input"):
                    print(f"    输入变量: {json.dumps(v['input'], ensure_ascii=False)}")
                if v.get("output"):
                    print(f"    输出变量: {json.dumps(v['output'], ensure_ascii=False)}")

    # 更新执行次数
    chain["exec_count"] = chain.get("exec_count", 0) + 1
    chain["updated_at"] = now_iso()
    save_chain(chain)

    print(f"\n✅ 执行计划已生成。请 AI 按上述步骤加载技能并执行。")
    print(f"   (执行次数: {chain['exec_count']})")
    return 0


def cmd_add_step(args):
    """向调用链添加步骤"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    steps = chain.get("steps", [])
    new_index = len(steps) + 1
    new_step = {
        "index": new_index,
        "skill_name": args.skill,
        "step_name": args.step_name,
        "action": args.action,
        "detail": args.detail or "",
        "depends_on": args.depends_on.split(",") if args.depends_on else [new_index - 1] if new_index > 1 else [],
        "condition": args.condition or "",
        "variables": {}
    }

    # 插入到指定位置之后
    insert_after = args.after or len(steps)
    insert_pos = min(insert_after, len(steps))

    # 重新编号
    steps.insert(insert_pos, new_step)
    for i, step in enumerate(steps):
        step["index"] = i + 1
        # 更新依赖引用
        new_deps = []
        for d in step.get("depends_on", []):
            if d > insert_after:
                new_deps.append(d + 1)
            else:
                new_deps.append(d)
        step["depends_on"] = new_deps

    chain["steps"] = steps
    chain["updated_at"] = now_iso()
    save_chain(chain)
    print(f"✅ 已添加步骤 '{args.step_name}' 到调用链 '{args.name}'（位置: {insert_pos + 1}）")
    return 0


def cmd_remove_step(args):
    """从调用链删除步骤"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    steps = chain.get("steps", [])
    target = args.step
    if target < 1 or target > len(steps):
        print(f"❌ 步骤 {target} 不存在（共 {len(steps)} 步）")
        return 1

    removed = steps.pop(target - 1)

    # 重新编号和更新依赖
    for i, step in enumerate(steps):
        step["index"] = i + 1
        new_deps = []
        for d in step.get("depends_on", []):
            if d == target:
                # 被删除步骤的依赖，指向删除步骤的前一步
                if target > 1:
                    new_deps.append(target - 1)
            elif d > target:
                new_deps.append(d - 1)
            else:
                new_deps.append(d)
        step["depends_on"] = new_deps

    chain["steps"] = steps
    chain["updated_at"] = now_iso()
    save_chain(chain)
    print(f"✅ 已从调用链 '{args.name}' 删除步骤 {target}（{removed.get('step_name', '')}）")
    return 0


def cmd_update_step(args):
    """更新调用链中的步骤"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    steps = chain.get("steps", [])
    target = args.step
    if target < 1 or target > len(steps):
        print(f"❌ 步骤 {target} 不存在（共 {len(steps)} 步）")
        return 1

    step = steps[target - 1]
    if args.action:
        step["action"] = args.action
    if args.detail is not None:
        step["detail"] = args.detail
    if args.skill:
        step["skill_name"] = args.skill
    if args.step_name:
        step["step_name"] = args.step_name
    if args.condition is not None:
        step["condition"] = args.condition
    if args.depends_on is not None:
        step["depends_on"] = [int(x.strip()) for x in args.depends_on.split(",") if x.strip()]

    chain["steps"] = steps
    chain["updated_at"] = now_iso()
    save_chain(chain)
    print(f"✅ 已更新调用链 '{args.name}' 的步骤 {target}")
    return 0


def cmd_rename(args):
    """重命名调用链"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    old_name = chain["name"]
    new_name = args.new_name

    # 检查新名称是否已存在
    index = load_index()
    if new_name in index:
        print(f"❌ 调用链 '{new_name}' 已存在")
        return 1

    # 删除旧文件
    old_file = Path(index[old_name])
    if old_file.exists():
        old_file.unlink()

    # 更新名称
    chain["name"] = new_name
    chain["updated_at"] = now_iso()

    # 保存为 新文件
    del index[old_name]
    save_chain(chain)

    print(f"✅ 调用链已重命名: '{old_name}' → '{new_name}'")
    return 0


def cmd_delete(args):
    """删除调用链"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    if not args.force:
        # 输出调用链摘要供确认
        steps_count = len(chain.get("steps", []))
        exec_count = chain.get("exec_count", 0)
        print(f"⚠️  即将删除调用链: {chain['name']}")
        print(f"   描述: {chain.get('description', '(无)')}")
        print(f"   步骤: {steps_count}步 | 执行: {exec_count}次")
        print(f"   确认删除请使用 --force 参数")
        return 0

    # 删除文件
    index = load_index()
    if args.name in index:
        chain_file = Path(index[args.name])
        if chain_file.exists():
            chain_file.unlink()
        del index[args.name]
        save_index(index)

    print(f"✅ 调用链 '{args.name}' 已删除")
    return 0


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Skill Chain Manager - 调用链管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python chain_manager.py init
  python chain_manager.py create --name "发布流水线" --description "技能发布流程" --purpose "一键发布" --steps '[{"skill_name":"security","step_name":"审计","action":"安全审计"}]'
  python chain_manager.py list
  python chain_manager.py list --tag "发布"
  python chain_manager.py show --name "发布流水线"
  python chain_manager.py run --name "发布流水线" --verbose
  python chain_manager.py add-step --name "发布流水线" --after 1 --skill "git-sync" --step-name "推送代码" --action "推送到GitHub"
  python chain_manager.py remove-step --name "发布流水线" --step 3
  python chain_manager.py update-step --name "发布流水线" --step 2 --action "新的动作"
  python chain_manager.py rename --name "发布流水线" --new-name "技能发布完整流程"
  python chain_manager.py delete --name "发布流水线" --force
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init
    subparsers.add_parser("init", help="初始化数据目录")

    # create
    p_create = subparsers.add_parser("create", help="创建调用链")
    p_create.add_argument("--name", required=True, help="调用链名称")
    p_create.add_argument("--description", help="描述")
    p_create.add_argument("--purpose", help="目的")
    p_create.add_argument("--user-intent", help="用户原始意图")
    p_create.add_argument("--tags", help="标签（逗号分隔）")
    p_create.add_argument("--steps", help="步骤JSON数组")

    # list
    p_list = subparsers.add_parser("list", help="列出所有调用链")
    p_list.add_argument("--tag", help="按标签过滤")

    # show
    p_show = subparsers.add_parser("show", help="查看调用链详情")
    p_show.add_argument("--name", required=True, help="调用链名称")

    # run
    p_run = subparsers.add_parser("run", help="执行调用链（生成执行计划）")
    p_run.add_argument("--name", required=True, help="调用链名称")
    p_run.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")

    # add-step
    p_add = subparsers.add_parser("add-step", help="添加步骤")
    p_add.add_argument("--name", required=True, help="调用链名称")
    p_add.add_argument("--after", type=int, default=0, help="在指定步骤之后插入（0=末尾）")
    p_add.add_argument("--skill", required=True, help="技能名称")
    p_add.add_argument("--step-name", required=True, help="步骤名称")
    p_add.add_argument("--action", required=True, help="动作描述")
    p_add.add_argument("--detail", default="", help="详细说明")
    p_add.add_argument("--depends-on", default="", help="依赖步骤索引（逗号分隔）")
    p_add.add_argument("--condition", default="", help="条件表达式")

    # remove-step
    p_rm = subparsers.add_parser("remove-step", help="删除步骤")
    p_rm.add_argument("--name", required=True, help="调用链名称")
    p_rm.add_argument("--step", type=int, required=True, help="步骤序号")

    # update-step
    p_upd = subparsers.add_parser("update-step", help="更新步骤")
    p_upd.add_argument("--name", required=True, help="调用链名称")
    p_upd.add_argument("--step", type=int, required=True, help="步骤序号")
    p_upd.add_argument("--action", default=None, help="新的动作描述")
    p_upd.add_argument("--detail", default=None, help="新的详细说明")
    p_upd.add_argument("--skill", default=None, help="新的技能名称")
    p_upd.add_argument("--step-name", default=None, help="新的步骤名称")
    p_upd.add_argument("--condition", default=None, help="新的条件表达式")
    p_upd.add_argument("--depends-on", default=None, help="新的依赖（逗号分隔）")

    # rename
    p_rename = subparsers.add_parser("rename", help="重命名调用链")
    p_rename.add_argument("--name", required=True, help="当前名称")
    p_rename.add_argument("--new-name", required=True, help="新名称")

    # delete
    p_del = subparsers.add_parser("delete", help="删除调用链")
    p_del.add_argument("--name", required=True, help="调用链名称")
    p_del.add_argument("--force", "-f", action="store_true", help="强制删除（不确认）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "create": cmd_create,
        "list": cmd_list,
        "show": cmd_show,
        "run": cmd_run,
        "add-step": cmd_add_step,
        "remove-step": cmd_remove_step,
        "update-step": cmd_update_step,
        "rename": cmd_rename,
        "delete": cmd_delete,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
