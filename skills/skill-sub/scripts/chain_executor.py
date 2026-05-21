#!/usr/bin/env python3
"""
chain_executor.py - Chain Executor v1.2.0
调用链执行引擎：根据调用链定义生成结构化执行计划，
识别依赖关系、并行机会，输出 AI 可直接执行的指令序列。

v1.1.0: 三层回退执行规则、分级重试策略、retry_policy/failure_mode 信息输出。
v1.2.0: 里程碑通用逻辑规则、配置集成（重试次数从设置读取）。

注意：本脚本不直接执行技能（技能执行由 AI 完成），
而是生成详细的执行计划，供 AI 按步骤执行。

零外部依赖，仅使用 Python 标准库。
跨平台支持 Windows/Linux/macOS。
"""

import argparse
import json
import os
import sys
from pathlib import Path


# ============================================================
# 路径配置
# ============================================================

def get_chain_home():
    import os
    env_home = os.environ.get("SKILL_SUB_HOME") or os.environ.get("SKILL_CHAIN_HOME")
    if env_home:
        return Path(env_home)
    return Path.home() / ".workbuddy" / "skill-sub"


def get_skill_dir():
    """获取 skill-sub 技能根目录"""
    return Path(__file__).resolve().parent.parent


CHAIN_HOME = get_chain_home()
CHAINS_DIR = CHAIN_HOME / "chains"
INDEX_FILE = CHAINS_DIR / "index.json"
SKILL_DIR = get_skill_dir()


# ============================================================
# 重试策略常量
# ============================================================

RETRY_STRATEGY = {
    "file_locked":  {"interval": 0, "description": "文件占用/锁定"},
    "network_error": {"interval": 5, "description": "网络不通/超时"},
    "timeout":      {"interval": 5, "description": "执行超时"},
    "auth_error":   {"interval": -1, "description": "认证/权限错误（不重试）"},
    "other":        {"interval": 2, "description": "其他错误"},
}

DEFAULT_ON_EXHAUST = "ask"


def get_default_max_retries():
    """从配置获取默认重试次数"""
    config = _load_user_config()
    try:
        return max(1, int(config.get("default_max_retries", 3)))
    except (TypeError, ValueError):
        return 3


def _load_user_config():
    """加载用户配置（合并默认值 + 用户覆盖）"""
    defaults_path = SKILL_DIR / "assets" / "default_config.json"
    defaults = {}
    if defaults_path.exists():
        defaults = json.loads(defaults_path.read_text(encoding="utf-8"))

    config_path = CHAIN_HOME / "config.json"
    user_cfg = {}
    if config_path.exists():
        user_cfg = json.loads(config_path.read_text(encoding="utf-8"))

    defaults.update(user_cfg)
    return defaults


# ============================================================
# 里程碑通用判断规则（与 chain_manager.py 保持一致）
# ============================================================

MILESTONE_KEYWORDS = [
    "审计", "安全", "部署", "发布", "上线", "打包",
    "测试", "验证", "校验", "审批", "审核",
    "付款", "支付", "下单", "提交", "推送",
    "导入", "导出", "迁移", "备份", "恢复",
    "audit", "deploy", "release", "publish", "push",
    "test", "verify", "validate", "approve", "review",
    "payment", "submit", "import", "export", "migrate",
    "backup", "restore", "build", "compile", "install",
]


def classify_milestones(steps):
    """基于结构特征的通用里程碑判断（与 chain_manager.py 一致）"""
    n = len(steps)
    if n == 0:
        return []

    depended_by = {}
    for i, step in enumerate(steps):
        idx = step.get("index", i + 1)
        depended_by[idx] = set()

    for i, step in enumerate(steps):
        idx = step.get("index", i + 1)
        for dep in step.get("depends_on", []):
            if dep in depended_by:
                depended_by[dep].add(idx)

    results = []
    for i, step in enumerate(steps):
        idx = step.get("index", i + 1)
        fm = step.get("failure_mode", {})

        if fm.get("is_milestone") is True:
            results.append({"step_index": idx, "is_milestone": True, "reason": "用户显式标记"})
            continue

        step_name = step.get("step_name", "")
        step_name_lower = step_name.lower()

        if n <= 2:
            results.append({"step_index": idx, "is_milestone": True, "reason": "短链（<=2步），所有步骤均为里程碑"})
            continue

        keyword_hit = None
        for kw in MILESTONE_KEYWORDS:
            if kw.lower() in step_name_lower:
                keyword_hit = kw
                break
        if keyword_hit:
            results.append({"step_index": idx, "is_milestone": True, "reason": f"关键词匹配: '{keyword_hit}'"})
            continue

        downstream_count = len(depended_by.get(idx, set()))
        if downstream_count >= 2:
            results.append({"step_index": idx, "is_milestone": True, "reason": f"瓶颈点（{downstream_count}个后续步骤依赖）"})
            continue

        if i == n - 1:
            results.append({"step_index": idx, "is_milestone": True, "reason": "最终交付步骤"})
            continue

        explicit_false = fm.get("is_milestone") is False
        results.append({
            "step_index": idx,
            "is_milestone": False,
            "reason": "显式取消里程碑" if explicit_false else "默认规则（非关键节点）"
        })

    return results


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
    env_dir = os.environ.get("WORKBUDDY_SKILLS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".workbuddy" / "skills"


def find_skill_path(skill_name):
    """查找技能实际目录"""
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        return None

    # 精确匹配
    exact = skills_dir / skill_name
    if exact.is_dir():
        return exact

    # 模糊匹配
    target = skill_name.lower().replace(" ", "-")
    for entry in skills_dir.iterdir():
        if entry.is_dir():
            if entry.name.lower().replace(" ", "-") == target or target in entry.name.lower():
                return entry

    return None


def classify_error(error_msg):
    """将错误消息分类为已知的错误类型"""
    msg = error_msg.lower()
    if any(k in msg for k in ["locked", "in use", "permission denied", "being used", "filelocked"]):
        return "file_locked"
    if any(k in msg for k in ["network", "connection", "dns", "timeout", "timed out", "socket", "refused"]):
        return "network_error"
    if any(k in msg for k in ["auth", "unauthorized", "forbidden", "401", "403", "token", "credential"]):
        return "auth_error"
    if any(k in msg for k in ["timeout", "timed out"]):
        return "timeout"
    return "other"


def validate_retry_policy(policy):
    """验证 retry_policy 字段"""
    if not policy:
        return []
    errors = []
    if not isinstance(policy, dict):
        errors.append("retry_policy 必须是对象")
        return errors
    if "max_retries" in policy:
        if not isinstance(policy["max_retries"], int) or policy["max_retries"] < 0:
            errors.append(f"retry_policy.max_retries 必须是非负整数")
    if "error_types" in policy:
        if not isinstance(policy["error_types"], list):
            errors.append("retry_policy.error_types 必须是数组")
        else:
            for et in policy["error_types"]:
                if et not in RETRY_STRATEGY and et != "other":
                    errors.append(f"retry_policy.error_types 中的未知类型: {et}")
    return errors


def validate_failure_mode(mode):
    """验证 failure_mode 字段"""
    if not mode:
        return []
    errors = []
    if not isinstance(mode, dict):
        errors.append("failure_mode 必须是对象")
        return errors
    if "on_exhaust" in mode:
        if mode["on_exhaust"] not in {"ask", "skip", "abort"}:
            errors.append(f"on_exhaust 无效值: {mode['on_exhaust']}")
    return errors


# ============================================================
# 执行计划生成
# ============================================================

def build_execution_plan(chain_data, verbose=False):
    """构建执行计划"""
    steps = chain_data.get("steps", [])
    if not steps:
        return {"error": "调用链没有步骤", "chain": chain_data["name"]}

    default_retries = get_default_max_retries()

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

    # 3. 按依赖深度分组
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

    # 4. 里程碑分类
    ms_results = classify_milestones(steps)
    ms_map = {r["step_index"]: r for r in ms_results}

    # 5. 构建执行计划
    plan = {
        "chain_name": chain_data.get("name", ""),
        "description": chain_data.get("description", ""),
        "purpose": chain_data.get("purpose", ""),
        "user_intent": chain_data.get("user_intent", ""),
        "total_steps": len(exec_order),
        "missing_skills": list(set(missing_skills)),
        "default_max_retries": default_retries,
        "execution_groups": [],
        "variable_flow": [],
        "milestone_analysis": ms_results
    }

    for depth in sorted(depth_groups.keys()):
        group_steps = depth_groups[depth]
        group = {
            "group_index": depth + 1,
            "can_parallel": len(group_steps) > 1,
            "steps": []
        }
        for step in group_steps:
            rp = step.get("retry_policy", {})
            fm = step.get("failure_mode", {})
            step_idx = step.get("index", 0)

            # 获取里程碑判断结果
            ms_info = ms_map.get(step_idx, {"is_milestone": False, "reason": ""})
            effective_milestone = fm.get("is_milestone", ms_info["is_milestone"])

            step_info = {
                "step_index": step_idx,
                "skill_name": step.get("skill_name", ""),
                "step_name": step.get("step_name", ""),
                "action": step.get("action", ""),
                "skill_instruction": step.get("skill_instruction", ""),
                "detail": step.get("detail", ""),
                "condition": step.get("condition", ""),
                "skill_path": skill_paths.get(step.get("skill_name", ""), ""),
                "depends_on": step.get("depends_on", []),
                "input_vars": {},
                "output_vars": {},
                "retry_policy": {
                    "max_retries": rp.get("max_retries", default_retries),
                    "error_types": rp.get("error_types", [])
                },
                "failure_mode": {
                    "on_exhaust": fm.get("on_exhaust", DEFAULT_ON_EXHAUST),
                    "is_milestone": effective_milestone
                },
                "milestone_reason": ms_info.get("reason", "")
            }
            variables = step.get("variables", {})
            step_info["input_vars"] = variables.get("input", {})
            step_info["output_vars"] = variables.get("output", {})
            group["steps"].append(step_info)

            if step_info["output_vars"]:
                plan["variable_flow"].append({
                    "from_step": step_info["step_index"],
                    "from_step_name": step_info["step_name"],
                    "outputs": step_info["output_vars"]
                })

        plan["execution_groups"].append(group)

    # 6. 生成 AI 执行指令
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
    lines.append(f"🔄 默认重试: 最多{plan.get('default_max_retries', 3)}次")

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
            si = step.get("skill_instruction", "")
            si_str = f" [{si}]" if si else ""
            ms = " ★" if step.get("failure_mode", {}).get("is_milestone") else ""
            lines.append(f"  {step_num}. [{skill}] {sname}{ms} — {action}{si_str}")
            if verbose:
                if step.get("detail"):
                    lines.append(f"     详情: {step['detail']}")
                if step.get("condition"):
                    lines.append(f"     条件: {step['condition']}")
                if step.get("input_vars"):
                    lines.append(f"     输入: {json.dumps(step['input_vars'], ensure_ascii=False)}")
                if step.get("output_vars"):
                    lines.append(f"     输出: {json.dumps(step['output_vars'], ensure_ascii=False)}")
                rp = step.get("retry_policy", {})
                fm = step.get("failure_mode", {})
                lines.append(f"     重试: 最多{rp.get('max_retries', 3)}次", end="")
                et = rp.get("error_types", [])
                if et:
                    lines.append(f", 仅针对: {', '.join(et)}")
                else:
                    lines.append("")
                oe = fm.get("on_exhaust", "ask")
                milestone = fm.get("is_milestone", False)
                ms_str = " (里程碑，强制中止)" if milestone else ""
                lines.append(f"     失败处理: {oe}{ms_str}")
                if step.get("milestone_reason"):
                    lines.append(f"     里程碑依据: {step['milestone_reason']}")

    # 变量传递关系
    if plan["variable_flow"]:
        lines.append(f"\n{'─'*70}")
        lines.append(f"变量传递链:")
        for vf in plan["variable_flow"]:
            lines.append(f"  步骤{vf['from_step']}({vf['from_step_name']}) → 输出: {vf['outputs']}")

    # AI 执行指令 - 三层回退
    lines.append(f"\n{'─'*70}")
    lines.append(f"AI 执行指令（三层回退策略）:")
    lines.append(f"")
    lines.append(f"对于每个步骤:")
    lines.append(f"  【第一层】展示 action + skill_instruction，直接按动作执行")
    lines.append(f"  → 如果执行不充分:")
    lines.append(f"  【第二层】按需读取 SKILL.md 对应指令片段（通过 skill_instruction 定位）")
    lines.append(f"  → 如果仍然不够:")
    lines.append(f"  【第三层】加载完整 SKILL.md 作为上下文参考")
    lines.append(f"  4. 记录输出变量，作为后续步骤的输入")
    lines.append(f"  5. 汇报步骤执行结果（✅成功 / ❌失败）")
    lines.append(f"")

    # 分级重试策略
    lines.append(f"分级重试策略:")
    lines.append(f"  ┌─────────────────┬──────────┬────────────────────────────┐")
    lines.append(f"  │    错误类型      │  重试间隔  │         说明              │")
    lines.append(f"  ├─────────────────┼──────────┼────────────────────────────┤")
    lines.append(f"  │ file_locked     │   0 秒    │ 文件占用/锁定，立即重试    │")
    lines.append(f"  │ network_error   │   5 秒    │ 网络不通/超时              │")
    lines.append(f"  │ timeout         │   5 秒    │ 执行超时                  │")
    lines.append(f"  │ auth_error      │   -       │ 认证/权限错误，直接询问用户 │")
    lines.append(f"  │ other           │   2 秒    │ 其他错误                  │")
    lines.append(f"  └─────────────────┴──────────┴────────────────────────────┘")
    lines.append(f"  默认最多重试 {plan.get('default_max_retries', 3)} 次")
    lines.append(f"  重试耗尽后 → 按 on_exhaust 处理（ask: 询问 / skip: 跳过 / abort: 中止）")
    lines.append(f"  里程碑步骤(★)失败 → 无论 on_exhaust 设置，强制中止整条链")

    return "\n".join(lines)


# ============================================================
# 命令实现
# ============================================================

def cmd_plan(args):
    """生成执行计划"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    plan = build_execution_plan(chain, verbose=args.verbose)

    if "error" in plan:
        print(f"❌ {plan['error']}")
        return 1

    # 里程碑分析摘要
    ms_results = plan.get("milestone_analysis", [])
    milestones = [r for r in ms_results if r["is_milestone"]]
    non_milestones = [r for r in ms_results if not r["is_milestone"]]

    print(f"📋 执行计划: {plan['chain_name']}")
    print(f"{'='*70}")
    print(f"  总步骤: {plan['total_steps']}")
    print(f"  缺失技能: {', '.join(plan['missing_skills']) if plan['missing_skills'] else '无'}")
    print(f"  默认重试: {plan.get('default_max_retries', 3)} 次")
    print(f"  里程碑: {len(milestones)} 步", end="")
    if non_milestones:
        print(f" | 非里程碑: {len(non_milestones)} 步")
    else:
        print()

    if milestones:
        print(f"\n  里程碑步骤:")
        for r in milestones:
            icon = "★"
            print(f"    {icon} 步骤{r['step_index']}: {r['reason']}")

    if args.verbose and non_milestones:
        print(f"\n  非里程碑步骤:")
        for r in non_milestones:
            print(f"    ○ 步骤{r['step_index']}: {r['reason']}")

    # 输出 AI 指令
    print(f"\n{plan['ai_instructions']}")

    # JSON 输出
    if args.json:
        print(f"\n{'─'*70}")
        json_plan = {k: v for k, v in plan.items() if k != "ai_instructions"}
        json_plan["ai_instructions"] = plan["ai_instructions"]
        print(json.dumps(json_plan, ensure_ascii=False, indent=2))

    return 0


def cmd_quick(args):
    """快速执行（无需保存调用链）"""
    try:
        steps = json.loads(args.steps)
    except json.JSONDecodeError as e:
        print(f"❌ 步骤 JSON 解析失败: {e}")
        return 1

    # 构建临时调用链数据
    chain_data = {
        "name": args.name,
        "description": args.description or "",
        "purpose": args.purpose or "",
        "user_intent": "",
        "tags": [],
        "steps": steps,
        "created_at": "",
        "updated_at": "",
        "exec_count": 0
    }

    plan = build_execution_plan(chain_data, verbose=args.verbose)

    if "error" in plan:
        print(f"❌ {plan['error']}")
        return 1

    print(f"📋 快速执行计划: {plan['chain_name']}")
    print(f"{'='*70}")
    print(plan["ai_instructions"])

    if args.json:
        print(f"\n{'─'*70}")
        print(json.dumps(plan, ensure_ascii=False, indent=2))

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

        rp_errors = validate_retry_policy(step.get("retry_policy"))
        for e in rp_errors:
            errors.append(f"步骤 {idx}: retry_policy - {e}")

        fm_errors = validate_failure_mode(step.get("failure_mode"))
        for e in fm_errors:
            errors.append(f"步骤 {idx}: failure_mode - {e}")

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

    # 5. 里程碑通用规则验证
    ms_results = classify_milestones(steps)
    milestones = [r for r in ms_results if r["is_milestone"]]
    no_manual_ms = all(
        s.get("failure_mode", {}).get("is_milestone") is not True
        for s in steps
    )

    if no_manual_ms and steps:
        if milestones:
            # 有自动判断的里程碑，但用户没有手动标记
            auto_names = [f"步骤{r['step_index']}({steps[r['step_index']-1].get('step_name', '')})" for r in milestones]
            warnings.append(f"未手动标记里程碑。建议确认以下自动判断: {', '.join(auto_names)}")
        else:
            warnings.append("没有里程碑步骤。建议为关键步骤设置 is_milestone=true")

    # 检查里程碑 on_exhaust 是否为 abort
    for step in steps:
        fm = step.get("failure_mode", {})
        if fm.get("is_milestone") and fm.get("on_exhaust") != "abort":
            warnings.append(f"步骤{step.get('index')}: 里程碑步骤建议 on_exhaust=abort（当前: {fm.get('on_exhaust')}）")

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
        description="Chain Executor v1.2.0 - 调用链执行引擎",
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

    p_plan = subparsers.add_parser("plan", help="生成执行计划")
    p_plan.add_argument("--name", required=True, help="调用链名称")
    p_plan.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")
    p_plan.add_argument("--json", action="store_true", help="JSON 格式输出")

    p_quick = subparsers.add_parser("quick", help="快速执行（无需保存调用链）")
    p_quick.add_argument("--name", default="临时调用链", help="临时名称")
    p_quick.add_argument("--description", default="", help="描述")
    p_quick.add_argument("--purpose", default="", help="目的")
    p_quick.add_argument("--steps", required=True, help="步骤JSON数组")
    p_quick.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")
    p_quick.add_argument("--json", action="store_true", help="JSON 格式输出")

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
