#!/usr/bin/env python3
"""
chain_executor.py - Chain Executor v1.0.0
调用链执行引擎：根据调用链定义生成结构化执行计划，
识别依赖关系、并行机会，输出 AI 可直接执行的指令序列。

注意：本脚本不直接执行技能（技能执行由 AI 完成），
而是生成详细的执行计划，供 AI 按步骤加载原始 SKILL.md 并执行。

零外部依赖，仅使用 Python 标准库。
跨平台支持 Windows/Linux/macOS。
"""

import argparse
import json
import sys
from pathlib import Path


# ============================================================
# 路径配置
# ============================================================

def get_chain_home():
    import os
    env_home = os.environ.get("SKILL_CHAIN_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".workbuddy" / "skill-sub"


CHAIN_HOME = get_chain_home()
CHAINS_DIR = CHAIN_HOME / "chains"
INDEX_FILE = CHAINS_DIR / "index.json"


# ============================================================
# 工具函数
# ============================================================

def load_index():
    if not INDEX_FILE.exists():
        return {}
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_chain(name):
    index = load_index()
    if name not in index:
        return None
    chain_file = Path(index[name])
    if not chain_file.exists():
        return None
    with open(chain_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_skills_dir():
    import os
    env_dir = os.environ.get("WORKBUDDY_SKILLS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".workbuddy" / "skills"


def find_skill_path(skill_name):
    """查找技能的实际目录路径"""
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        return None

    # 精确匹配
    for entry in skills_dir.iterdir():
        if entry.is_dir() and entry.name.lower() == skill_name.lower():
            return entry

    # 模糊匹配
    for entry in skills_dir.iterdir():
        if entry.is_dir():
            slug = entry.name.lower().replace(" ", "-")
            if skill_name.lower() in slug or slug in skill_name.lower():
                return entry

    return None


# ============================================================
# 执行计划生成
# ============================================================

def build_execution_plan(chain_data, verbose=False):
    """构建执行计划"""
    steps = chain_data.get("steps", [])
    if not steps:
        return {"error": "调用链没有步骤", "chain": chain_data["name"]}

    # 1. 检查技能可用性
    skill_paths = {}
    missing_skills = []
    for step in steps:
        skill_name = step.get("skill_name", "")
        if skill_name in ("(内置)", "(内置打包)", ""):
            skill_paths[skill_name] = None
            continue
        if skill_name not in skill_paths:
            path = find_skill_path(skill_name)
            if path:
                skill_paths[skill_name] = str(path)
            else:
                missing_skills.append(skill_name)

    # 2. 拓扑排序
    step_map = {s.get("index", i + 1): s for i, s in enumerate(steps)}
    # 补全 index
    for i, s in enumerate(steps):
        s.setdefault("index", i + 1)

    exec_order = []
    executed = set()
    remaining = dict(step_map)

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
            idx = min(remaining.keys())
            exec_order.append(remaining[idx])
            executed.add(idx)
            del remaining[idx]

    # 3. 按依赖深度分组（用于识别并行）
    from collections import defaultdict
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
        max_dep = max(get_depth(d) for d in deps)
        depth_cache[idx] = max_dep + 1
        return depth_cache[idx]

    depth_groups = defaultdict(list)
    for step in exec_order:
        d = get_depth(step.get("index", 0))
        depth_groups[d].append(step)

    # 4. 构建执行计划
    plan = {
        "chain_name": chain_data.get("name", ""),
        "description": chain_data.get("description", ""),
        "purpose": chain_data.get("purpose", ""),
        "user_intent": chain_data.get("user_intent", ""),
        "total_steps": len(exec_order),
        "missing_skills": list(set(missing_skills)),
        "execution_groups": [],
        "variable_flow": []
    }

    for depth in sorted(depth_groups.keys()):
        group_steps = depth_groups[depth]
        group = {
            "group_index": depth + 1,
            "can_parallel": len(group_steps) > 1,
            "steps": []
        }
        for step in group_steps:
            step_info = {
                "step_index": step.get("index", 0),
                "skill_name": step.get("skill_name", ""),
                "step_name": step.get("step_name", ""),
                "action": step.get("action", ""),
                "detail": step.get("detail", ""),
                "condition": step.get("condition", ""),
                "skill_path": skill_paths.get(step.get("skill_name", ""), ""),
                "depends_on": step.get("depends_on", []),
                "input_vars": {},
                "output_vars": {}
            }
            # 变量映射
            variables = step.get("variables", {})
            step_info["input_vars"] = variables.get("input", {})
            step_info["output_vars"] = variables.get("output", {})
            group["steps"].append(step_info)

            # 收集变量流
            if step_info["output_vars"]:
                plan["variable_flow"].append({
                    "from_step": step_info["step_index"],
                    "from_step_name": step_info["step_name"],
                    "outputs": step_info["output_vars"]
                })

        plan["execution_groups"].append(group)

    # 5. 生成 AI 执行指令
    plan["ai_instructions"] = generate_ai_instructions(plan, verbose)

    return plan


def generate_ai_instructions(plan, verbose=False):
    """生成 AI 执行指令文本"""
    lines = []
    lines.append(f"【执行调用链】{plan['chain_name']}")
    lines.append(f"{'='*70}")
    lines.append(f"📌 目的: {plan['purpose']}")
    lines.append(f"📝 意图: {plan['user_intent']}")
    lines.append(f"📐 总步骤: {plan['total_steps']}")

    if plan["missing_skills"]:
        lines.append(f"\n⚠️ 缺失技能（请先安装）: {', '.join(set(plan['missing_skills']))}")

    # 执行概览表
    lines.append(f"\n{'─'*70}")
    lines.append(f"执行步骤:")
    step_num = 0
    for group in plan["execution_groups"]:
        if group["can_parallel"]:
            lines.append(f"\n  ⚡ 并行组 {group['group_index']}:")
        for step in group["steps"]:
            step_num += 1
            skill = step["skill_name"]
            sname = step["step_name"]
            action = step["action"]
            lines.append(f"  {step_num}. [{skill}] {sname} — {action}")
            if verbose:
                if step.get("detail"):
                    lines.append(f"     详情: {step['detail']}")
                if step.get("condition"):
                    lines.append(f"     条件: {step['condition']}")
                if step.get("input_vars"):
                    lines.append(f"     输入: {json.dumps(step['input_vars'], ensure_ascii=False)}")
                if step.get("output_vars"):
                    lines.append(f"     输出: {json.dumps(step['output_vars'], ensure_ascii=False)}")

    # 变量传递关系
    if plan["variable_flow"]:
        lines.append(f"\n{'─'*70}")
        lines.append(f"变量传递链:")
        for vf in plan["variable_flow"]:
            lines.append(f"  步骤{vf['from_step']}({vf['from_step_name']}) → 输出: {vf['outputs']}")

    # AI 执行指令
    lines.append(f"\n{'─'*70}")
    lines.append(f"AI 执行指令:")
    lines.append(f"")
    lines.append(f"对于每个步骤:")
    lines.append(f"  1. 向用户展示步骤编号、技能名和关键动作")
    lines.append(f"  2. 使用 Skill 工具加载对应技能的 SKILL.md")
    lines.append(f"  3. 按照动作描述执行关键步骤（参考原始 SKILL.md 指令）")
    lines.append(f"  4. 记录输出变量，作为后续步骤的输入")
    lines.append(f"  5. 汇报步骤执行结果（✅成功 / ❌失败）")
    lines.append(f"")
    lines.append(f"错误处理:")
    lines.append(f"  - 某步失败 → 询问用户: 跳过(S) / 重试(R) / 中止(A)")
    lines.append(f"  - 技能缺失 → 提示安装，跳过或中止")

    return "\n".join(lines)


# ============================================================
# 命令实现
# ============================================================

def cmd_plan(args):
    """生成执行计划"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        print("   使用 chain_manager.py list 查看所有调用链")
        return 1

    plan = build_execution_plan(chain, verbose=args.verbose)
    if "error" in plan:
        print(f"❌ {plan['error']}")
        return 1

    # 输出 AI 执行指令
    print(plan["ai_instructions"])

    # JSON 输出（可选）
    if args.json:
        # 移除 ai_instructions 避免重复
        json_plan = {k: v for k, v in plan.items() if k != "ai_instructions"}
        print(f"\n{'─'*70}")
        print("JSON 执行计划:")
        print(json.dumps(json_plan, ensure_ascii=False, indent=2))

    return 0


def cmd_quick(args):
    """快速执行（直接根据步骤 JSON 生成执行计划，无需保存调用链）"""
    if not args.steps:
        print("❌ 必须提供 --steps 参数")
        return 1

    try:
        steps = json.loads(args.steps)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        return 1

    # 构造临时调用链
    temp_chain = {
        "name": args.name or "临时调用链",
        "description": args.description or "",
        "purpose": args.purpose or "",
        "user_intent": "",
        "steps": steps
    }

    plan = build_execution_plan(temp_chain, verbose=args.verbose)
    if "error" in plan:
        print(f"❌ {plan['error']}")
        return 1

    print(plan["ai_instructions"])

    if args.json:
        json_plan = {k: v for k, v in plan.items() if k != "ai_instructions"}
        print(f"\n{'─'*70}")
        print(json.dumps(json_plan, ensure_ascii=False, indent=2))

    return 0


def cmd_validate(args):
    """验证调用链的完整性"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    errors = []
    warnings = []

    # 1. 基本结构
    if not chain.get("name"):
        errors.append("缺少名称")
    if not chain.get("steps"):
        errors.append("没有步骤")

    steps = chain.get("steps", [])

    # 2. 步骤完整性
    indices = set()
    for i, step in enumerate(steps):
        idx = step.get("index", i + 1)
        indices.add(idx)

        if not step.get("skill_name"):
            warnings.append(f"步骤 {idx}: 缺少技能名称")
        if not step.get("action"):
            warnings.append(f"步骤 {idx}: 缺少动作描述")
        if not step.get("step_name"):
            warnings.append(f"步骤 {idx}: 缺少步骤名称")

        # 依赖检查
        for dep in step.get("depends_on", []):
            if dep not in indices and dep != idx - 1:
                warnings.append(f"步骤 {idx}: 依赖步骤 {dep} 不存在（或未按顺序定义）")

    # 3. 技能可用性
    missing = []
    for step in steps:
        skill_name = step.get("skill_name", "")
        if skill_name in ("(内置)", "(内置打包)", ""):
            continue
        path = find_skill_path(skill_name)
        if not path:
            missing.append(skill_name)

    if missing:
        missing_unique = list(set(missing))
        for ms in missing_unique:
            errors.append(f"技能未安装: {ms}")

    # 4. 循环依赖检查
    step_map = {s.get("index", i + 1): s for i, s in enumerate(steps)}
    visited = set()
    rec_stack = set()

    def has_cycle(idx, path=None):
        if path is None:
            path = []
        visited.add(idx)
        rec_stack.add(idx)
        path.append(idx)
        step = step_map.get(idx)
        if step:
            for dep in step.get("depends_on", []):
                if dep not in visited:
                    if has_cycle(dep, path):
                        return True
                elif dep in rec_stack:
                    return True
        path.pop()
        rec_stack.discard(idx)
        return False

    for idx in step_map:
        if idx not in visited:
            if has_cycle(idx):
                errors.append("检测到循环依赖")
                break

    # 输出结果
    print(f"🔍 验证调用链: {chain['name']}")
    print(f"{'='*60}")

    if not errors and not warnings:
        print(f"✅ 验证通过，无问题")
        return 0

    if warnings:
        print(f"\n  ⚠️ 警告 ({len(warnings)}):")
        for w in warnings:
            print(f"     - {w}")

    if errors:
        print(f"\n  ❌ 错误 ({len(errors)}):")
        for e in errors:
            print(f"     - {e}")
        return 1

    return 0


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Chain Executor - 调用链执行引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python chain_executor.py plan --name "发布流水线"
  python chain_executor.py plan --name "发布流水线" --verbose --json
  python chain_executor.py validate --name "发布流水线"
  python chain_executor.py quick --name "临时链" --steps '[{"skill_name":"a","step_name":"A","action":"执行A"}]'
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # plan
    p_plan = subparsers.add_parser("plan", help="生成执行计划")
    p_plan.add_argument("--name", required=True, help="调用链名称")
    p_plan.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")
    p_plan.add_argument("--json", action="store_true", help="JSON 格式输出")

    # quick
    p_quick = subparsers.add_parser("quick", help="快速执行（无需保存调用链）")
    p_quick.add_argument("--name", default="临时调用链", help="临时名称")
    p_quick.add_argument("--description", default="", help="描述")
    p_quick.add_argument("--purpose", default="", help="目的")
    p_quick.add_argument("--steps", required=True, help="步骤JSON数组")
    p_quick.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")
    p_quick.add_argument("--json", action="store_true", help="JSON 格式输出")

    # validate
    p_validate = subparsers.add_parser("validate", help="验证调用链完整性")
    p_validate.add_argument("--name", required=True, help="调用链名称")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "plan": cmd_plan,
        "quick": cmd_quick,
        "validate": cmd_validate,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
