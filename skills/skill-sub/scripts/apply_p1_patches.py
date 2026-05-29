#!/usr/bin/env python3
"""P1 扩展点补丁：智能依赖推断 + 历史链推荐 + 链优化建议 + 参数推断"""
import re
from pathlib import Path
from collections import defaultdict

SKILL_DIR = Path(r"C:\Users\sm001\.workbuddy\skills\skill-sub")

def patch_smart_dep_inference():
    """智能依赖推断：添加 cmd_infer_deps 函数"""
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    content = p.read_text(encoding="utf-8")

    # 检查是否已存在
    if "def cmd_infer_deps(" in content:
        print("  ⚠️  cmd_infer_deps 已存在")
        return True

    # 在函数列表末尾插入新函数
    insert_before = 'def cmd_clear_progress('
    if insert_before not in content:
        print("  ❌ 未找到插入点")
        return False

    new_func = '''\ndef cmd_infer_deps(args):
    """智能依赖推断：基于步骤名和 action 自动推断 depends_on"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    steps = chain.get("steps", [])
    if not steps:
        print(f"❌ 调用链 '{args.name}' 没有步骤")
        return 1

    print(f"🧠 智能依赖推断: {chain['name']}")
    print(f"{'='*70}")

    # 关键词匹配规则
    keyword_rules = [
        ("审查", "生成"),
        ("检查", "生成"),
        ("测试", "开发"),
        ("部署", "测试"),
        ("发布", "部署"),
        ("备份", "修改"),
        ("恢复", "备份"),
        ("优化", "分析"),
        ("分析", "提取"),
        ("提取", "读取"),
    ]

    # 步骤名相似度计算（简单版）
    def calc_similarity(s1, s2):
        if not s1 or not s2:
            return 0.0
        # 公共子串
        m = [[0] * (len(s2) + 1) for _ in range(len(s1) + 1)]
        max_len = 0
        for i in range(1, len(s1) + 1):
            for j in range(1, len(s2) + 1):
                if s1[i-1] == s2[j-1]:
                    m[i][j] = m[i-1][j-1] + 1
                    if m[i][j] > max_len:
                        max_len = m[i][j]
        return max_len / max(len(s1), len(s2))

    changes = []
    for i, step in enumerate(steps):
        idx = step.get("index", i + 1)
        action = step.get("action", "")
        sname = step.get("step_name", "")
        current_deps = step.get("depends_on", []) or []

        # 推断的依赖
        inferred = set()

        # 规则1：关键词匹配
        for before_kw, after_kw in keyword_rules:
            if after_kw in action or after_kw in sname:
                # 找前面的步骤是否包含 before_kw
                for j in range(i):
                    prev = steps[j]
                    prev_action = prev.get("action", "")
                    prev_sname = prev.get("step_name", "")
                    if before_kw in prev_action or before_kw in prev_sname:
                        inferred.add(prev.get("index", j + 1))

        # 规则2：技能名相同，可能依赖前面的
        skill_name = step.get("skill_name", "")
        if skill_name:
            for j in range(i):
                prev = steps[j]
                if prev.get("skill_name") == skill_name and j < i:
                    # 不强制添加，只提供建议
                    pass

        # 规则3：步骤名相似度高的前面步骤
        for j in range(i):
            prev = steps[j]
            prev_sname = prev.get("step_name", "")
            sim = calc_similarity(sname, prev_sname)
            if sim > 0.5:  # 相似度 > 0.5
                inferred.add(prev.get("index", j + 1))

        # 过滤掉已经在 depends_on 中的
        new_deps = sorted(inferred - set(current_deps))
        if new_deps:
            changes.append((idx, current_deps, new_deps))

    if not changes:
        print(f"✅ 依赖关系已合理，无需推断")
        return 0

    print(f"\n  推断结果:")
    for idx, current, new in changes:
        step = steps[idx - 1]
        print(f"    步骤{idx}({step.get('step_name', '')}):")
        print(f"      当前: {current}")
        print(f"      建议添加: {new}")

    if not args.auto_apply:
        print(f"\n  使用 --auto-apply 参数自动应用推断结果")
        return 0

    # 应用推断结果
    for idx, current, new in changes:
        step = steps[idx - 1]
        step["depends_on"] = sorted(set(current) | set(new))
        print(f"    ✅ 步骤{idx}: depends_on = {step['depends_on']}")

    chain["updated_at"] = now_iso()
    save_chain(chain)
    print(f"\n✅ 已应用推断结果")
    return 0\n\n'''

    content = content.replace(insert_before, new_func + insert_before)
    p.write_text(content, encoding="utf-8")
    print("  ✅ cmd_infer_deps 已添加")
    return True

def patch_historical_recommendation():
    """历史链推荐：添加 cmd_recommend 函数"""
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    content = p.read_text(encoding="utf-8")

    if "def cmd_recommend(" in content:
        print("  ⚠️  cmd_recommend 已存在")
        return True

    insert_before = 'def cmd_infer_deps('
    if insert_before not in content:
        print("  ❌ 未找到插入点")
        return False

    new_func = '''\ndef cmd_recommend(args):
    """历史链推荐：基于意图匹配推荐已有链"""
    intent = args.intent or ""
    if not intent:
        print("❌ 请提供意图描述（--intent 参数）")
        return 1

    chains_dir = CHAIN_DIR
    if not chains_dir.exists():
        print("❌ chains 目录不存在")
        return 1

    print(f"🔍 历史链推荐: {intent}")
    print(f"{'='*70}")

    # 加载所有链
    chains = []
    for f in chains_dir.glob("*.json"):
        try:
            chain = json.loads(f.read_text(encoding="utf-8"))
            chains.append(chain)
        except Exception:
            pass

    if not chains:
        print("❌ 没有找到任何调用链")
        return 1

    # 简单相似度计算（基于关键词重叠）
    def calc_intent_similarity(intent_str, chain_obj):
        intent_words = set(re.findall(r"\\w+", intent_str.lower()))
        chain_words = set()

        # 从链的名称、描述、步骤名中提取关键词
        chain_words.add(chain_obj.get("name", "").lower())
        chain_words.add(chain_obj.get("description", "").lower())
        for step in chain_obj.get("steps", []):
            chain_words.add(step.get("step_name", "").lower())
            chain_words.add(step.get("action", "").lower())

        overlap = intent_words & chain_words
        return len(overlap) / max(len(intent_words), 1)

    # 计算相似度并排序
    results = []
    for chain in chains:
        sim = calc_intent_similarity(intent, chain)
        if sim > 0:
            results.append((chain, sim))

    results.sort(key=lambda x: x[1], reverse=True)

    if not results:
        print("❌ 没有找到相似的调用链")
        return 1

    print(f"\n  推荐结果（按相似度排序）:")
    for i, (chain, sim) in enumerate(results[:5]):  # 只显示前5个
        print(f"    {i+1}. {chain.get('name', '?')} (相似度: {sim:.2f})")
        print(f"       描述: {chain.get('description', '无')}")
        print(f"       步骤数: {len(chain.get('steps', []))}")

    return 0\n\n'''

    content = content.replace(insert_before, new_func + insert_before)
    p.write_text(content, encoding="utf-8")
    print("  ✅ cmd_recommend 已添加")
    return True

def patch_chain_optimization():
    """链优化建议：添加 cmd_optimize 函数"""
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    content = p.read_text(encoding="utf-8")

    if "def cmd_optimize(" in content:
        print("  ⚠️  cmd_optimize 已存在")
        return True

    insert_before = 'def cmd_recommend('
    if insert_before not in content:
        print("  ❌ 未找到插入点")
        return False

    new_func = '''\ndef cmd_optimize(args):
    """链优化建议：识别冗余步骤、可合并步骤、潜在并行机会"""
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    steps = chain.get("steps", [])
    if not steps:
        print(f"❌ 调用链 '{args.name}' 没有步骤")
        return 1

    print(f"🔧 链优化建议: {chain['name']}")
    print(f"{'='*70}")

    suggestions = []

    # 1. 冗余步骤检查（action 完全相同）
    action_count = defaultdict(list)
    for step in steps:
        action = step.get("action", "")
        if action:
            action_count[action].append(step.get("index", 0))

    for action, indices in action_count.items():
        if len(indices) > 1:
            suggestions.append((
                "冗余步骤",
                f"步骤 {indices} 的 action 完全相同，建议合并"
            ))

    # 2. 可合并步骤检查（步骤名相似）
    for i in range(len(steps)):
        for j in range(i + 1, len(steps)):
            s1 = steps[i].get("step_name", "")
            s2 = steps[j].get("step_name", "")
            if s1 and s2 and s1 == s2:
                suggestions.append((
                    "重复步骤名",
                    f"步骤{i+1}({s1}) 和 步骤{j+1}({s2}) 名称相同，建议合并"
                ))

    # 3. 潜在并行机会（没有依赖关系）
    step_map = {step.get("index", i+1): step for i, step in enumerate(steps)}
    for i in range(len(steps)):
        for j in range(i + 1, len(steps)):
            s1 = steps[i]
            s2 = steps[j]
            idx1 = s1.get("index", i + 1)
            idx2 = s2.get("index", j + 1)
            deps1 = s1.get("depends_on", []) or []
            deps2 = s2.get("depends_on", []) or []

            if idx1 not in deps2 and idx2 not in deps1:
                suggestions.append((
                    "潜在并行",
                    f"步骤{idx1} 和 步骤{idx2} 没有依赖关系，可以并行执行"
                ))

    # 4. 里程碑过多检查
    ms_count = sum(1 for s in steps if s.get("failure_mode", {}).get("is_milestone"))
    if ms_count > len(steps) / 2:
        suggestions.append((
            "里程碑过多",
            f"里程碑步骤数 ({ms_count}) 超过总步骤数的一半，建议减少"
        ))

    # 5. 空步骤检查
    for step in steps:
        if not step.get("action") and not step.get("skill_instruction"):
            suggestions.append((
                "空步骤",
                f"步骤{step.get('index', '?')} 没有 action 和 skill_instruction"
            ))

    if not suggestions:
        print(f"✅ 没有发现优化建议")
        return 0

    print(f"\n  优化建议:")
    for i, (category, suggestion) in enumerate(suggestions):
        print(f"    {i+1}. [{category}] {suggestion}")

    return 0\n\n'''

    content = content.replace(insert_before, new_func + insert_before)
    p.write_text(content, encoding="utf-8")
    print("  ✅ cmd_optimize 已添加")
    return True

def patch_parameter_inference():
    """参数推断：添加 cmd_infer_params 函数"""
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    content = p.read_text(encoding="utf-8")

    if "def cmd_infer_params(" in content:
        print("  ⚠️  cmd_infer_params 已存在")
        return True

    insert_before = 'def cmd_optimize('
    if insert_before not in content:
        print("  ❌ 未找到插入点")
        return False

    new_func = '''\ndef cmd_infer_params(args):
    """参数推断：从用户意图推断链的全局参数"""
    intent = args.intent or ""
    if not intent:
        print("❌ 请提供意图描述（--intent 参数）")
        return 1

    print(f"🧠 参数推断: {intent}")
    print(f"{'='*70}")

    # 简单规则匹配
    inferred = {}

    # 输出格式
    if "markdown" in intent.lower() or "md" in intent.lower():
        inferred["output_format"] = "markdown"
    elif "html" in intent.lower():
        inferred["output_format"] = "html"
    elif "json" in intent.lower():
        inferred["output_format"] = "json"
    elif "报告" in intent or "report" in intent.lower():
        inferred["output_format"] = "markdown"

    # 目标平台
    if "web" in intent.lower() or "网页" in intent:
        inferred["target_platform"] = "web"
    elif "mobile" in intent.lower() or "移动端" in intent:
        inferred["target_platform"] = "mobile"
    elif "desktop" in intent.lower() or "桌面" in intent:
        inferred["target_platform"] = "desktop"

    # 执行模式
    if "自动" in intent or "auto" in intent.lower():
        inferred["execution_mode"] = "automatic"
    elif "手动" in intent or "manual" in intent.lower():
        inferred["execution_mode"] = "manual"
    elif "半自动" in intent:
        inferred["execution_mode"] = "semi-automatic"

    # 优先级
    if "高优先级" in intent or "high priority" in intent.lower():
        inferred["priority"] = "high"
    elif "低优先级" in intent or "low priority" in intent.lower():
        inferred["priority"] = "low"

    if not inferred:
        print(f"⚠️  未能推断出参数，请手动配置")
        return 1

    print(f"\n  推断结果:")
    for key, value in inferred.items():
        print(f"    {key}: {value}")

    if not args.auto_apply:
        print(f"\n  使用 --auto-apply 参数自动应用到链的 variables 字段")
        return 0

    # 应用到链
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链 '{args.name}' 不存在")
        return 1

    if "variables" not in chain:
        chain["variables"] = {}
    if "input" not in chain["variables"]:
        chain["variables"]["input"] = {}

    chain["variables"]["input"].update(inferred)
    chain["updated_at"] = now_iso()
    save_chain(chain)
    print(f"\n✅ 已应用推断参数到链 {args.name}")
    return 0\n\n'''

    content = content.replace(insert_before, new_func + insert_before)
    p.write_text(content, encoding="utf-8")
    print("  ✅ cmd_infer_params 已添加")
    return True

def add_subparsers():
    """添加子命令到 argparse"""
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    content = p.read_text(encoding="utf-8")

    # 在 argparse 部分添加新子命令
    if 'p_infer = subparsers.add_parser("infer-deps"' in content:
        print("  ⚠️  infer-deps 子命令已存在")
    else:
        # 找合适的插入点
        insert_after = '    p_restore = subparsers.add_parser("restore"'
        if insert_after in content:
            new_subparser = '''
    p_infer = subparsers.add_parser("infer-deps", help="智能依赖推断")
    p_infer.add_argument("--name", required=True, help="调用链名称")
    p_infer.add_argument("--auto-apply", action="store_true", help="自动应用推断结果")
    p_infer.set_defaults(func=cmd_infer_deps)

    p_recommend = subparsers.add_parser("recommend", help="历史链推荐")
    p_recommend.add_argument("--intent", help="意图描述")
    p_recommend.set_defaults(func=cmd_recommend)

    p_optimize = subparsers.add_parser("optimize", help="链优化建议")
    p_optimize.add_argument("--name", required=True, help="调用链名称")
    p_optimize.set_defaults(func=cmd_optimize)

    p_infer_params = subparsers.add_parser("infer-params", help="参数推断")
    p_infer_params.add_argument("--name", required=True, help="调用链名称")
    p_infer_params.add_argument("--intent", help="意图描述")
    p_infer_params.add_argument("--auto-apply", action="store_true", help="自动应用推断结果")
    p_infer_params.set_defaults(func=cmd_infer_params)
'''
            pos = content.find(insert_after) + len(insert_after)
            content = content[:pos] + new_subparser + content[pos:]
            print("  ✅ 子命令已添加")
        else:
            print("  ❌ 未找到插入点（subparser）")

    p.write_text(content, encoding="utf-8")
    return True

if __name__ == "__main__":
    print("=== 开始 P1 扩展点补丁 ===")
    print("[1/5] 智能依赖推断...")
    r1 = patch_smart_dep_inference()
    print("[2/5] 历史链推荐...")
    r2 = patch_historical_recommendation()
    print("[3/5] 链优化建议...")
    r3 = patch_chain_optimization()
    print("[4/5] 参数推断...")
    r4 = patch_parameter_inference()
    print("[5/5] 添加子命令...")
    r5 = add_subparsers()

    if all([r1, r2, r3, r4, r5]):
        print("\n✅ 所有 P1 扩展点补丁成功！")
    else:
        print("\n⚠️  部分补丁失败，请检查上述输出")
