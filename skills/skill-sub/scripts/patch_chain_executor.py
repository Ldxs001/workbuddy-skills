#!/usr/bin/env python3
"""patch_chain_executor.py - 给 chain_executor.py 插入 _cmd_dry_run 函数"""
import re

p = r"C:\Users\sm001\.workbuddy\skills\skill-sub\scripts\chain_executor.py"
with open(p, "r", encoding="utf-8") as f:
    content = f.read()

# 在 cmd_plan 的 return 0 之后、cmd_quick 之前插入 _cmd_dry_run
# 精确匹配 cmd_plan 结尾和 cmd_quick 开头之间的空白区域
marker = '    return 0\n\n\ndef cmd_quick(args):'
if marker not in content:
    # 尝试另一种匹配
    idx = content.find("def cmd_quick(args):")
    if idx != -1:
        # 往前找 return 0
        pre = content[:idx]
        last_return = pre.rfind("    return 0")
        if last_return != -1:
            insert_pos = last_return + len("    return 0")
            # 往后跳过空白和换行
            while insert_pos < len(content) and content[insert_pos] in " \t\n":
                insert_pos += 1
            # 现在 insert_pos 指向 def cmd_quick 的 d
            new_func = '''\n\n\ndef _cmd_dry_run(plan):\n    """Dry-run 模式：模拟执行，输出每步会发生什么"""\n    print(f"\\n🏖️  Dry-Run 模式（模拟执行，不实际调用技能）")\n    print(f"{'='*70}")\n\n    step_num = 0\n    for group in plan.get("execution_groups", []):\n        if group.get("can_parallel"):\n            print(f"\\n  ⚡ 并行组 {group['group_index']}:（以下步骤可同时执行）")\n        for step in group.get("steps", []):\n            step_num += 1\n            skill = step.get("skill_name", "")\n            sname = step.get("step_name", "")\n            action = step.get("action", "")\n            ms = " ★" if step.get("failure_mode", {}).get("is_milestone") else ""\n            cond = step.get("condition", "")\n            cond_str = f" [条件: {cond}]" if cond else ""\n\n            print(f"\\n  {step_num}. [{skill}] {sname}{ms}{cond_str}")\n            print(f"     动作: {action}")\n\n            if cond:\n                eval_result, reason = evaluate_condition(cond)\n                status = "✅ 条件满足" if eval_result else "⚠️ 条件不满足（将跳过）"\n                print(f"     条件判断: {status} — {reason}")\n\n            if step.get("skill_instruction"):\n                print(f"     指令: {step['skill_instruction']}")\n            if step.get("detail"):\n                print(f"     详情: {step['detail'][:100]}")\n\n            rp = step.get("retry_policy", {})\n            fm = step.get("failure_mode", {})\n            max_r = rp.get("max_retries", plan.get("default_max_retries", 3))\n            on_exh = fm.get("on_exhaust", "ask")\n            ms_flag = fm.get("is_milestone", False)\n            print(f"     重试: 最多{max_r}次 | 失败处理: {on_exh}" + (" (里程碑，强制中止)" if ms_flag else ""))\n\n            if step.get("output_vars"):\n                import json\n                print(f"     输出变量: {json.dumps(step['output_vars'], ensure_ascii=False)}")\n\n    print(f"\\n{'─'*70}")\n    print(f"  Dry-Run 完成：共 {step_num} 步，以上为模拟执行结果。")\n    print(f"  要实际执行，请去掉 --dry-run 参数。")\n    return 0\n\n\n'''
            new_content = content[:insert_pos] + new_func + content[insert_pos:]
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("✅ _cmd_dry_run 已插入")
            exit(0)

    print("❌ 未找到插入点")
    exit(1)
else:
    new_func = '''\n\n\ndef _cmd_dry_run(plan):\n    """Dry-run 模式：模拟执行，输出每步会发生什么"""\n    print(f"\\n🏖️  Dry-Run 模式（模拟执行，不实际调用技能）")\n    print(f"{'='*70}")\n\n    step_num = 0\n    for group in plan.get("execution_groups", []):\n        if group.get("can_parallel"):\n            print(f"\\n  ⚡ 并行组 {group['group_index']}:（以下步骤可同时执行）")\n        for step in group.get("steps", []):\n            step_num += 1\n            skill = step.get("skill_name", "")\n            sname = step.get("step_name", "")\n            action = step.get("action", "")\n            ms = " ★" if step.get("failure_mode", {}).get("is_milestone") else ""\n            cond = step.get("condition", "")\n            cond_str = f" [条件: {cond}]" if cond else ""\n\n            print(f"\\n  {step_num}. [{skill}] {sname}{ms}{cond_str}")\n            print(f"     动作: {action}")\n\n            if cond:\n                eval_result, reason = evaluate_condition(cond)\n                status = "✅ 条件满足" if eval_result else "⚠️ 条件不满足（将跳过）"\n                print(f"     条件判断: {status} — {reason}")\n\n            if step.get("skill_instruction"):\n                print(f"     指令: {step['skill_instruction']}")\n            if step.get("detail"):\n                print(f"     详情: {step['detail'][:100]}")\n\n            rp = step.get("retry_policy", {})\n            fm = step.get("failure_mode", {})\n            max_r = rp.get("max_retries", plan.get("default_max_retries", 3))\n            on_exh = fm.get("on_exhaust", "ask")\n            ms_flag = fm.get("is_milestone", False)\n            print(f"     重试: 最多{max_r}次 | 失败处理: {on_exh}" + (" (里程碑，强制中止)" if ms_flag else ""))\n\n            if step.get("output_vars"):\n                import json\n                print(f"     输出变量: {json.dumps(step['output_vars'], ensure_ascii=False)}")\n\n    print(f"\\n{'─'*70}")\n    print(f"  Dry-Run 完成：共 {step_num} 步，以上为模拟执行结果。")\n    print(f"  要实际执行，请去掉 --dry-run 参数。")\n    return 0\n\n\n'''
    new_content = content.replace(marker, '    return 0\n' + new_func + '\ndef cmd_quick(args):\n', 1)
    with open(p, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("✅ _cmd_dry_run 已插入")
    exit(0)
