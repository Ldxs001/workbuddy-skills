#!/usr/bin/env python3
"""
chain_manager.py - Skill Sub Manager v1.2.0
调用链管理核心脚本：创建、查询、更新、删除、执行调用链。

v1.1.0: retry_policy、failure_mode、skill_instruction 字段支持。
v1.2.0: 设置功能集成（记忆参考、命名方式、重试次数）、里程碑通用逻辑规则。

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
    env_home = os.environ.get("SKILL_SUB_HOME") or os.environ.get("SKILL_CHAIN_HOME")
    if env_home:
        return Path(env_home)
    # 默认路径
    default = Path.home() / ".workbuddy" / "skill-sub"
    return default


def get_skills_dir():
    """获取已安装技能目录"""
    env_dir = os.environ.get("WORKBUDDY_SKILLS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".workbuddy" / "skills"


def get_skill_dir():
    """获取 skill-sub 技能根目录"""
    return Path(__file__).resolve().parent.parent


CHAIN_HOME = get_chain_home()
CHAINS_DIR = CHAIN_HOME / "chains"
INDEX_FILE = CHAINS_DIR / "index.json"
CONFIG_FILE = CHAIN_HOME / "config.json"
SKILL_DIR = get_skill_dir()


# ============================================================
# 里程碑通用判断规则
# ============================================================

# 里程碑关键词：步骤名包含这些关键词时，自动标记为里程碑
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
    """基于结构特征的通用里程碑判断。

    规则优先级（从高到低）：
    1. 用户显式标记 is_milestone=true → 里程碑
    2. 用户显式标记 is_milestone=false → 非里程碑
    3. 总步骤数 <= 2 → 全部里程碑（链太短，每步都关键）
    4. 步骤名包含里程碑关键词 → 里程碑
    5. 被多个后续步骤依赖（瓶颈点，>=2个后续步骤依赖它）→ 里程碑
    6. 是最后一步 → 里程碑（最终交付物）
    7. 其余 → 非里程碑

    返回：list[dict] 每项包含 step_index, is_milestone, reason
    """
    n = len(steps)
    if n == 0:
        return []

    # 构建依赖关系：谁依赖谁
    depended_by = {}  # step_index -> set of step_indices that depend on it
    step_indices = []
    for i, step in enumerate(steps):
        idx = step.get("index", i + 1)
        step_indices.append(idx)
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

        # 规则1：显式标记 true
        if fm.get("is_milestone") is True:
            results.append({"step_index": idx, "is_milestone": True, "reason": "用户显式标记"})
            continue

        # 规则2：显式标记 false
        if fm.get("is_milestone") is False:
            # 仍然检查其他规则，但显式 false 会覆盖
            pass

        step_name = step.get("step_name", "")
        step_name_lower = step_name.lower()

        # 规则3：总步骤 <= 2
        if n <= 2:
            results.append({"step_index": idx, "is_milestone": True, "reason": "短链（<=2步），所有步骤均为里程碑"})
            continue

        # 规则4：关键词匹配
        keyword_hit = None
        for kw in MILESTONE_KEYWORDS:
            if kw.lower() in step_name_lower:
                keyword_hit = kw
                break
        if keyword_hit:
            results.append({"step_index": idx, "is_milestone": True, "reason": f"关键词匹配: '{keyword_hit}'"})
            continue

        # 规则5：瓶颈点（>=2个后续步骤依赖）
        downstream_count = len(depended_by.get(idx, set()))
        if downstream_count >= 2:
            results.append({"step_index": idx, "is_milestone": True, "reason": f"瓶颈点（{downstream_count}个后续步骤依赖）"})
            continue

        # 规则6：最后一步
        if i == n - 1:
            results.append({"step_index": idx, "is_milestone": True, "reason": "最终交付步骤"})
            continue

        # 规则7：默认非里程碑（如果用户没有显式设 false，也按默认处理）
        explicit_false = fm.get("is_milestone") is False
        results.append({
            "step_index": idx,
            "is_milestone": False,
            "reason": "显式取消里程碑" if explicit_false else "默认规则（非关键节点）"
        })

    return results


# ============================================================
# 配置加载
# ============================================================

def load_user_config():
    """加载用户配置（合并默认值 + 用户覆盖）"""
    defaults_path = SKILL_DIR / "assets" / "default_config.json"
    defaults = {}
    if defaults_path.exists():
        defaults = json.loads(defaults_path.read_text(encoding="utf-8"))

    user_cfg = {}
    if CONFIG_FILE.exists():
        user_cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

    defaults.update(user_cfg)
    return defaults


def get_config_value(key, fallback=None):
    """获取配置值（带回退）"""
    config = load_user_config()
    return config.get(key, fallback)


# ============================================================
# 默认值常量
# ============================================================

def _get_default_retry():
    """从配置获取默认重试次数"""
    v = get_config_value("default_max_retries", 3)
    try:
        return max(1, int(v))
    except (TypeError, ValueError):
        return 3


# 这些会在模块加载时使用 get_config_value，但 fallback 仍可用
DEFAULT_RETRY_POLICY = {"max_retries": 3}  # 实际使用 _get_default_retry() 覆盖
DEFAULT_FAILURE_MODE = {"on_exhaust": "ask", "is_milestone": False}
VALID_ON_EXHAUST_VALUES = {"ask", "skip", "abort"}
VALID_ERROR_TYPES = {"file_locked", "network_error", "auth_error", "timeout"}


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
    safe = name.replace("/", "-").replace("\\", "-").replace(":", "-")
    safe = safe.replace(" ", "_").replace("*", "").replace("?", "").replace('"', "")
    safe = safe.replace("<", "").replace(">", "").replace("|", "")
    return safe[:100]


def now_iso():
    """返回当前时间的 ISO 格式"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


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
            errors.append(f"retry_policy.max_retries 必须是非负整数，当前: {policy['max_retries']}")
    if "error_types" in policy:
        if not isinstance(policy["error_types"], list):
            errors.append("retry_policy.error_types 必须是数组")
        else:
            for et in policy["error_types"]:
                if et not in VALID_ERROR_TYPES:
                    errors.append(f"retry_policy.error_types 中的未知错误类型: {et}")

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
        if mode["on_exhaust"] not in VALID_ON_EXHAUST_VALUES:
            errors.append(f"failure_mode.on_exhaust 必须是 {VALID_ON_EXHAUST_VALUES} 之一，当前: {mode['on_exhaust']}")
    if "is_milestone" in mode:
        if not isinstance(mode["is_milestone"], bool):
            errors.append(f"failure_mode.is_milestone 必须是布尔值，当前: {mode['is_milestone']}")

    return errors


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

            rp_errors = validate_retry_policy(step.get("retry_policy"))
            for e in rp_errors:
                errors.append(f"步骤 {i+1}: {e}")

            fm_errors = validate_failure_mode(step.get("failure_mode"))
            for e in fm_errors:
                errors.append(f"步骤 {i+1}: {e}")

    return errors


def apply_step_defaults(step):
    """为步骤应用默认值（retry_policy、failure_mode）"""
    default_retries = _get_default_retry()
    if "retry_policy" not in step or not step["retry_policy"]:
        step["retry_policy"] = {"max_retries": default_retries}
    else:
        # 如果 retry_policy 存在但没有 max_retries，用配置值填充
        if "max_retries" not in step["retry_policy"]:
            step["retry_policy"]["max_retries"] = default_retries

    if "failure_mode" not in step or not step["failure_mode"]:
        step["failure_mode"] = dict(DEFAULT_FAILURE_MODE)
    if "skill_instruction" not in step:
        step["skill_instruction"] = ""
    return step


# ============================================================
# 命令实现
# ============================================================

def cmd_init(args):
    """初始化数据目录"""
    ensure_dirs()
    if not CONFIG_FILE.exists():
        # 从默认配置生成
        config = load_user_config()
        # 移除内部字段
        config.pop("_saved", None)
        config.pop("_skill_sub_home", None)
        # 确保基础字段存在
        config.setdefault("version", "1.2.0")
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"✅ 初始化完成")
    print(f"   数据目录: {CHAIN_HOME}")
    print(f"   调用链目录: {CHAINS_DIR}")

    # 输出当前设置
    config = load_user_config()
    mem_ref = config.get("use_memory_reference", False)
    naming = config.get("naming_mode", "manual")
    retries = config.get("default_max_retries", 3)
    print(f"   设置: 记忆参考={'是' if mem_ref else '否'} | 命名={'自动' if naming == 'auto' else '人工'} | 重试={retries}次")


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

    # 补全步骤 index 并应用默认值
    for i, step in enumerate(steps):
        step.setdefault("index", i + 1)
        apply_step_defaults(step)

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

    # 里程碑分类
    if steps:
        ms_results = classify_milestones(steps)
        milestones = [r for r in ms_results if r["is_milestone"]]
        if milestones:
            ms_names = [f"步骤{r['step_index']}({steps[r['step_index']-1].get('step_name', '')})" for r in milestones]
            print(f"   里程碑: {', '.join(ms_names)}")
            # 输出判断依据
            for r in milestones:
                step_obj = steps[r["step_index"] - 1]
                # 如果不是显式标记，应用里程碑设置
                if step_obj.get("failure_mode", {}).get("is_milestone") is not True:
                    step_obj.setdefault("failure_mode", {})
                    step_obj["failure_mode"]["is_milestone"] = True
                    step_obj["failure_mode"].setdefault("on_exhaust", "abort")
            # 保存更新后的里程碑
            chain_data["steps"] = steps
            save_chain(chain_data)
        else:
            print(f"   里程碑: 无")
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

    chains.sort(key=lambda c: c.get("updated_at", ""), reverse=True)

    print(f"📋 调用链列表（共 {len(chains)} 条）")
    print(f"{'='*70}")
    for c in chains:
        steps_count = len(c.get("steps", []))
        exec_count = c.get("exec_count", 0)
        created = c.get("created_at", "")[:10]
        tags = ", ".join(c.get("tags", []))
        milestone_count = sum(1 for s in c.get("steps", []) if s.get("failure_mode", {}).get("is_milestone"))
        print(f"  📌 {c['name']}")
        print(f"     描述: {c.get('description', '(无)')}")
        print(f"     步骤: {steps_count}步 | 执行: {exec_count}次 | 里程碑: {milestone_count}步 | 创建: {created}")
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
        # 里程碑分类
        ms_results = classify_milestones(steps)
        ms_map = {r["step_index"]: r for r in ms_results}

        print(f"\n{'─'*70}")
        print(f"  执行步骤（共 {len(steps)} 步）:")
        print(f"  ┌──────┬─────────────────┬──────────────┬──────────────────────────────┬──────────┬──────────┐")
        print(f"  │  序号  │      技能       │    步骤名     │          关键动作             │  里程碑   │  重试上限 │")
        print(f"  ├──────┼─────────────────┼──────────────┼──────────────────────────────┼──────────┼──────────┤")
        for step in steps:
            idx = f"{step.get('index', '-')}".center(4)
            skill = (step.get("skill_name", "")[:15]).ljust(15)
            sname = (step.get("step_name", "")[:12]).ljust(12)
            action = step.get("action", "")[:30]
            fm = step.get("failure_mode", {})
            ms = " ★" if fm.get("is_milestone") else "  "
            rp = step.get("retry_policy", {})
            retry_str = str(rp.get("max_retries", _get_default_retry())).center(6)
            deps = step.get("depends_on", [])
            dep_str = f" (依赖:{deps})" if deps else ""
            print(f"  │  {idx}  │ {skill} │ {sname} │ {action}{dep_str:<{28-len(dep_str)}} │{ms}      │{retry_str}  │")
        print(f"  └──────┴─────────────────┴──────────────┴──────────────────────────────┴──────────┴──────────┘")
        print(f"  ★ = 里程碑步骤（失败时强制中止）")

        # 里程碑判断依据
        print(f"\n  📐 里程碑判断依据:")
        for r in ms_results:
            step_obj = steps[r["step_index"] - 1]
            sname = step_obj.get("step_name", "")
            ms_icon = "★" if r["is_milestone"] else "○"
            print(f"     {ms_icon} 步骤{r['step_index']}({sname}): {r['reason']}")

    # 重试策略详情
    default_retries = _get_default_retry()
    retry_steps = [s for s in steps if s.get("retry_policy", {}).get("max_retries") != default_retries or s.get("retry_policy", {}).get("error_types")]
    if retry_steps:
        print(f"\n  自定义重试策略:")
        for s in retry_steps:
            rp = s.get("retry_policy", {})
            et = rp.get("error_types", [])
            et_str = f", 仅针对: {', '.join(et)}" if et else ""
            print(f"    步骤{s['index']}({s.get('step_name', '')}): 最多{rp.get('max_retries', default_retries)}次{et_str}")

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
        if skill_name in ("(内置)", "(内置打包)", ""):
            continue
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

    # 读取设置
    config = load_user_config()
    use_memory = config.get("use_memory_reference", False)

    print(f"📌 执行调用链: {chain['name']}")
    print(f"{'='*70}")

    if use_memory:
        print(f"  📖 记忆参考: 已启用（读取用户上下文文件增强步骤描述）")

    if missing_skills:
        print(f"\n⚠️  以下技能未找到:")
        for ms in missing_skills:
            print(f"   - {ms}")
        print(f"   请先安装缺失的技能")

    # 里程碑分类
    ms_results = classify_milestones(steps)
    ms_map = {r["step_index"]: r for r in ms_results}

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
            idx = min(remaining.keys())
            exec_order.append(remaining[idx])
            executed.add(idx)
            del remaining[idx]

    # 输出执行计划
    print(f"\n📋 执行计划（{len(exec_order)} 步）:")
    print(f"  ┌──────┬─────────────────┬──────────────┬──────────────────────────────┬──────────┐")
    print(f"  │  序号  │      技能       │    步骤名     │          关键动作             │  里程碑   │")
    print(f"  ├──────┼─────────────────┼──────────────┼──────────────────────────────┼──────────┤")
    for i, step in enumerate(exec_order, 1):
        idx = str(i).center(4)
        skill = (step.get("skill_name", "")[:15]).ljust(15)
        sname = (step.get("step_name", "")[:12]).ljust(12)
        action = step.get("action", "")[:30]
        fm = step.get("failure_mode", {})
        ms = " ★" if fm.get("is_milestone") else "  "
        si = step.get("skill_instruction", "")
        si_str = f" [{si}]" if si else ""
        action_with_si = (action + si_str)[:30]
        print(f"  │  {idx}  │ {skill} │ {sname} │ {action_with_si:<30} │{ms}      │")
    print(f"  └──────┴─────────────────┴──────────────┴──────────────────────────────┴──────────┘")
    print(f"  ★ = 里程碑步骤（失败时强制中止）")

    # 并行机会识别
    from collections import defaultdict

    step_map = {s.get("index", 0): s for s in exec_order}
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

    # 重试策略摘要
    default_retries = _get_default_retry()
    print(f"\n  🔄 重试策略（默认最多 {default_retries} 次）:")
    print(f"     文件占用(file_locked): 立即重试")
    print(f"     网络错误(network_error): 间隔5秒")
    print(f"     执行超时(timeout): 间隔5秒")
    print(f"     认证错误(auth_error): 直接询问用户")
    print(f"     其他错误: 间隔2秒")
    print(f"     耗尽后按 on_exhaust 设置处理（ask/skip/abort）")

    if args.verbose:
        print(f"\n{'─'*70}")
        print(f"  详细执行指令:")
        for i, step in enumerate(exec_order, 1):
            print(f"\n  步骤 {i}: [{step.get('skill_name', '')}] {step.get('step_name', '')}")
            print(f"    动作: {step.get('action', '')}")
            if step.get("skill_instruction"):
                print(f"    指令: {step['skill_instruction']}")
            if step.get("detail"):
                print(f"    详情: {step['detail']}")
            if step.get("condition"):
                print(f"    条件: {step['condition']}")
            rp = step.get("retry_policy", {})
            print(f"    重试: 最多{rp.get('max_retries', default_retries)}次", end="")
            et = rp.get("error_types", [])
            if et:
                print(f", 仅针对: {', '.join(et)}")
            else:
                print()
            fm = step.get("failure_mode", {})
            oe = fm.get("on_exhaust", "ask")
            ms = fm.get("is_milestone", False)
            print(f"    失败处理: {oe}" + (" (里程碑，强制中止)" if ms else ""))
            # 里程碑判断依据
            ms_r = ms_map.get(step.get("index", i))
            if ms_r:
                print(f"    里程碑: {ms_r['reason']}")
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

    print(f"\n✅ 执行计划已生成。请按上述步骤执行（三层回退策略）。")
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
    default_retries = _get_default_retry()
    new_step = {
        "index": new_index,
        "skill_name": args.skill,
        "step_name": args.step_name,
        "action": args.action,
        "skill_instruction": "",
        "detail": args.detail or "",
        "depends_on": args.depends_on.split(",") if args.depends_on else [new_index - 1] if new_index > 1 else [],
        "condition": args.condition or "",
        "variables": {},
        "retry_policy": {"max_retries": default_retries},
        "failure_mode": dict(DEFAULT_FAILURE_MODE)
    }

    insert_after = args.after or len(steps)
    insert_pos = min(insert_after, len(steps))

    steps.insert(insert_pos, new_step)
    for i, step in enumerate(steps):
        step["index"] = i + 1
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

    # 里程碑自动判断
    ms_results = classify_milestones(steps)
    new_ms = ms_results[insert_pos] if insert_pos < len(ms_results) else None
    ms_info = ""
    if new_ms and new_ms["is_milestone"]:
        ms_info = f" [里程碑: {new_ms['reason']}]"

    print(f"✅ 已添加步骤 '{args.step_name}' 到调用链 '{args.name}'（位置: {insert_pos + 1}）")
    print(f"   默认重试: 最多{default_retries}次 | 默认失败处理: {DEFAULT_FAILURE_MODE['on_exhaust']}{ms_info}")
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

    for i, step in enumerate(steps):
        step["index"] = i + 1
        new_deps = []
        for d in step.get("depends_on", []):
            if d == target:
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
    ms_info = " (里程碑)" if removed.get("failure_mode", {}).get("is_milestone") else ""
    print(f"✅ 已从调用链 '{args.name}' 删除步骤 {target}（{removed.get('step_name', '')}{ms_info}）")
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
    if args.skill_instruction is not None:
        step["skill_instruction"] = args.skill_instruction

    if args.retry_max is not None:
        if "retry_policy" not in step:
            step["retry_policy"] = {"max_retries": _get_default_retry()}
        step["retry_policy"]["max_retries"] = args.retry_max

    if args.retry_types is not None:
        if "retry_policy" not in step:
            step["retry_policy"] = {"max_retries": _get_default_retry()}
        if args.retry_types:
            types_list = [t.strip() for t in args.retry_types.split(",") if t.strip()]
            step["retry_policy"]["error_types"] = types_list
        else:
            step["retry_policy"].pop("error_types", None)

    if args.on_exhaust is not None:
        if "failure_mode" not in step:
            step["failure_mode"] = dict(DEFAULT_FAILURE_MODE)
        step["failure_mode"]["on_exhaust"] = args.on_exhaust

    if args.milestone is not None:
        if "failure_mode" not in step:
            step["failure_mode"] = dict(DEFAULT_FAILURE_MODE)
        step["failure_mode"]["is_milestone"] = args.milestone

    chain["steps"] = steps
    chain["updated_at"] = now_iso()

    errors = []
    rp_errors = validate_retry_policy(step.get("retry_policy"))
    errors.extend(rp_errors)
    fm_errors = validate_failure_mode(step.get("failure_mode"))
    errors.extend(fm_errors)

    if errors:
        save_chain(chain)
        print(f"⚠️ 已更新步骤 {target}，但有以下警告:")
        for e in errors:
            print(f"   - {e}")
        return 0

    save_chain(chain)
    print(f"✅ 已更新调用链 '{args.name}' 的步骤 {target}")
    rp = step.get("retry_policy", {})
    fm = step.get("failure_mode", {})
    print(f"   重试: 最多{rp.get('max_retries', _get_default_retry())}次 | 失败处理: {fm.get('on_exhaust', 'ask')}" +
          (" (里程碑)" if fm.get("is_milestone") else ""))
    return 0


def cmd_rename(args):
    """重命名调用链"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    old_name = chain["name"]
    new_name = args.new_name

    index = load_index()
    if new_name in index:
        print(f"❌ 调用链 '{new_name}' 已存在")
        return 1

    old_file = Path(index[old_name])
    if old_file.exists():
        old_file.unlink()

    chain["name"] = new_name
    chain["updated_at"] = now_iso()

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
        steps_count = len(chain.get("steps", []))
        exec_count = chain.get("exec_count", 0)
        print(f"⚠️  即将删除调用链: {chain['name']}")
        print(f"   描述: {chain.get('description', '(无)')}")
        print(f"   步骤: {steps_count}步 | 执行: {exec_count}次")
        print(f"   确认删除请使用 --force 参数")
        return 0

    index = load_index()
    if args.name in index:
        chain_file = Path(index[args.name])
        if chain_file.exists():
            chain_file.unlink()
        del index[args.name]
        save_index(index)

    print(f"✅ 调用链 '{args.name}' 已删除")
    return 0


def cmd_config(args):
    """查看当前配置"""
    config = load_user_config()
    # 移除内部字段
    for k in ("_saved", "_skill_sub_home"):
        config.pop(k, None)
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Skill Sub Manager v1.2.0 - 调用链管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python chain_manager.py init
  python chain_manager.py config
  python chain_manager.py create --name "发布流水线" --description "技能发布流程" --purpose "一键发布" --steps '[{"skill_name":"security","step_name":"审计","action":"安全审计"}]'
  python chain_manager.py list
  python chain_manager.py list --tag "发布"
  python chain_manager.py show --name "发布流水线"
  python chain_manager.py run --name "发布流水线" --verbose
  python chain_manager.py add-step --name "发布流水线" --after 1 --skill "git-sync" --step-name "推送代码" --action "推送到GitHub"
  python chain_manager.py remove-step --name "发布流水线" --step 3
  python chain_manager.py update-step --name "发布流水线" --step 2 --action "新的动作"
  python chain_manager.py update-step --name "发布流水线" --step 1 --milestone --retry-max 5
  python chain_manager.py update-step --name "发布流水线" --step 3 --on-exhaust abort
  python chain_manager.py rename --name "发布流水线" --new-name "技能发布完整流程"
  python chain_manager.py delete --name "发布流水线" --force
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("init", help="初始化数据目录")
    subparsers.add_parser("config", help="查看当前配置")

    p_create = subparsers.add_parser("create", help="创建调用链")
    p_create.add_argument("--name", required=True, help="调用链名称")
    p_create.add_argument("--description", help="描述")
    p_create.add_argument("--purpose", help="目的")
    p_create.add_argument("--user-intent", help="用户原始意图")
    p_create.add_argument("--tags", help="标签（逗号分隔）")
    p_create.add_argument("--steps", help="步骤JSON数组")

    p_list = subparsers.add_parser("list", help="列出所有调用链")
    p_list.add_argument("--tag", help="按标签过滤")

    p_show = subparsers.add_parser("show", help="查看调用链详情")
    p_show.add_argument("--name", required=True, help="调用链名称")

    p_run = subparsers.add_parser("run", help="执行调用链（生成执行计划）")
    p_run.add_argument("--name", required=True, help="调用链名称")
    p_run.add_argument("--verbose", "-v", action="store_true", help="输出详细信息")

    p_add = subparsers.add_parser("add-step", help="添加步骤")
    p_add.add_argument("--name", required=True, help="调用链名称")
    p_add.add_argument("--after", type=int, default=0, help="在指定步骤之后插入（0=末尾）")
    p_add.add_argument("--skill", required=True, help="技能名称")
    p_add.add_argument("--step-name", required=True, help="步骤名称")
    p_add.add_argument("--action", required=True, help="动作描述")
    p_add.add_argument("--detail", default="", help="详细说明")
    p_add.add_argument("--depends-on", default="", help="依赖步骤索引（逗号分隔）")
    p_add.add_argument("--condition", default="", help="条件表达式")

    p_rm = subparsers.add_parser("remove-step", help="删除步骤")
    p_rm.add_argument("--name", required=True, help="调用链名称")
    p_rm.add_argument("--step", type=int, required=True, help="步骤序号")

    p_upd = subparsers.add_parser("update-step", help="更新步骤")
    p_upd.add_argument("--name", required=True, help="调用链名称")
    p_upd.add_argument("--step", type=int, required=True, help="步骤序号")
    p_upd.add_argument("--action", default=None, help="新的动作描述")
    p_upd.add_argument("--detail", default=None, help="新的详细说明")
    p_upd.add_argument("--skill", default=None, help="新的技能名称")
    p_upd.add_argument("--step-name", default=None, help="新的步骤名称")
    p_upd.add_argument("--condition", default=None, help="新的条件表达式")
    p_upd.add_argument("--depends-on", default=None, help="新的依赖（逗号分隔）")
    p_upd.add_argument("--skill-instruction", default=None, help="技能指令名称")
    p_upd.add_argument("--retry-max", type=int, default=None, help="最大重试次数")
    p_upd.add_argument("--retry-types", default=None, help="适用的错误类型（逗号分隔）")
    p_upd.add_argument("--on-exhaust", default=None, choices=["ask", "skip", "abort"], help="重试耗尽后的行为")
    p_upd.add_argument("--milestone", action="store_true", default=None, help="标记为里程碑步骤")
    p_upd.add_argument("--no-milestone", action="store_false", dest="milestone", help="取消里程碑标记")

    p_rename = subparsers.add_parser("rename", help="重命名调用链")
    p_rename.add_argument("--name", required=True, help="当前名称")
    p_rename.add_argument("--new-name", required=True, help="新名称")

    p_del = subparsers.add_parser("delete", help="删除调用链")
    p_del.add_argument("--name", required=True, help="调用链名称")
    p_del.add_argument("--force", "-f", action="store_true", help="强制删除（不确认）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "init": cmd_init,
        "config": cmd_config,
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
