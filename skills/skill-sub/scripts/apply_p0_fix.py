#!/usr/bin/env python3
"""补丁脚本：补全 P0 剩余两项"""
import sys
from pathlib import Path

SKILL_DIR = Path(r"C:\Users\sm001\.workbuddy\skills\skill-sub")

def patch_chain_manager():
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    c = p.read_text(encoding="utf-8")

    # ---- 插入 clear-progress / resume 子命令（在 p_run 之后）----
    marker = '    p_run = subparsers.add_parser("run", help="执行调用链（生成执行计划）")\n'
    if marker not in c:
        # 尝试另一种格式
        marker2 = 'p_run = subparsers.add_parser("run"'
        idx = c.find(marker2)
        if idx == -1:
            print("  ❌ 未找到 p_run 子命令定义")
            return False
        # 找到该行末尾
        line_end = c.find("\n", idx)
        marker = c[idx:line_end+1]
        insert_pos = line_end + 1
    else:
        insert_pos = c.find(marker) + len(marker)

    # 跳过 p_run 的 add_argument 行，找到下一个 subparsers.add_parser 或 main
    # 直接在 p_run 的 add_argument 之后插入
    new_cmds = (
        '    p_run.add_argument("--name", required=True, help="调用链名称")'
        if '--name' not in c[max(0,insert_pos-500):insert_pos]
        else ''
    )
    # 更稳健：直接在 subparsers 定义后，p_run 定义后插入
    # 实际做法：在 "def cmd_run(" 之前插入新子命令定义
    cmd_run_pos = c.find('def cmd_run(')
    if cmd_run_pos == -1:
        print("  ❌ 未找到 def cmd_run")
        return False

    # 在最后一个 subparser 的 set_defaults 之后插入
    # 找 "subparsers =" 行
    sp_idx = c.rfind('subparsers = ')
    if sp_idx == -1:
        print("  ❌ 未找到 subparsers 定义")
        return False

    # 找 subparsers 代码块的结束位置（下一个函数定义或 main）
    # 找 "def " 在 sp_idx 之后的位置
    next_def = c.find('\ndef ', sp_idx + 1)
    if next_def == -1:
        print("  ❌ 未找到 subparsers 后的 def")
        return False

    # 在 next_def 之前插入新子命令
    insert_at = next_def

    new_subparsers = '''    p_clear = subparsers.add_parser("clear-progress", help="清除执行进度")
    p_clear.add_argument("--name", required=True, help="调用链名称")
    p_clear.set_defaults(func=cmd_clear_progress)

    p_resume = subparsers.add_parser("resume", help="从断点恢复执行（等价 run --resume）")
    p_resume.add_argument("--name", required=True, help="调用链名称")
    p_resume.set_defaults(func=cmd_resume)

'''
    if 'p_clear = subparsers' not in c:
        c = c[:insert_at] + new_subparsers + c[insert_at:]
        print("  ✅ clear-progress / resume 子命令已插入")
    else:
        print("  ⚠️  clear-progress / resume 子命令已存在")

    p.write_text(c, encoding="utf-8")
    return True


def patch_chain_executor():
    p = SKILL_DIR / "scripts" / "chain_executor.py"
    c = p.read_text(encoding="utf-8")

    # 在 cmd_validate 的 "# 输出结果" 之前插入增强检查
    # 找 "def cmd_validate(" 然后找 "# 输出结果"
    fstart = c.find('def cmd_validate(')
    if fstart == -1:
        print("  ❌ 未找到 def cmd_validate")
        return False

    # 在函数体内找 "# 输出结果"
    func_body = c[fstart:]
    oi = func_body.find('# 输出结果')
    if oi == -1:
        # 尝试中文
        oi = func_body.find('# 输出结果')
        if oi == -1:
            print("  ❌ 未找到 '# 输出结果'")
            return False

    insert_at = fstart + oi

    enhanced = '''
    # 6. 步骤 index 连续性检查
    indices = sorted([s.get("index", i+1) for i, s in enumerate(steps)])
    expected = list(range(1, len(indices)+1))
    if indices != expected:
        missing = set(expected) - set(indices)
        if missing:
            errors.append(f"步骤 index 不连续，缺少 index: {sorted(missing)}")
        dup = [idx for idx in indices if indices.count(idx) > 1]
        if dup:
            errors.append(f"步骤 index 重复: {set(dup)}")

    # 7. 步骤名唯一性检查
    names = [s.get("step_name", "") for s in steps if s.get("step_name")]
    if len(names) != len(set(names)):
        from collections import Counter
        dup = [n for n, cnt in Counter(names).items() if cnt > 1]
        warnings.append(f"步骤名重复: {dup}")

    # 8. 条件表达式格式检查
    import re
    cond_pattern = re.compile(r"^(step_\\d+_(success|failed)|always|never|variable_\\w+_exists)$")
    for step in steps:
        cond = step.get("condition", "").strip()
        if cond and not cond_pattern.match(cond):
            warnings.append(f"步骤{step.get('index')}: condition 格式可能不正确: {cond}")

    # 9. 输出变量冲突检测
    output_vars = {}
    for step in steps:
        for var_name, var_def in (step.get("variables", {})).items():
            if var_def.get("direction") == "output":
                if var_name in output_vars:
                    warnings.append(f"输出变量冲突: {var_name} 在步骤{output_vars[var_name]} 和步骤{step.get('index')} 都定义为输出")
                else:
                    output_vars[var_name] = step.get("index")

    # 10. 重试策略合理性检查
    default_max = 3
    try:
        from .chain_manager import load_user_config
        default_max = load_user_config().get("default_max_retries", 3)
    except Exception:
        pass
    for step in steps:
        rp = step.get("retry_policy", {})
        max_r = rp.get("max_retries", default_max)
        if max_r < 0:
            errors.append(f"步骤{step.get('index')}: max_retries 不能为负数")
        elif max_r > 10:
            warnings.append(f"步骤{step.get('index')}: max_retries={max_r} 过大，建议 ≤10")

    # 11. 死代码检查（条件引用不存在的步骤）
    step_indices = {s.get("index") for s in steps}
    for step in steps:
        cond = step.get("condition", "").strip()
        if cond.startswith("step_") and cond.endswith("_success"):
            try:
                ref_idx = int(cond.replace("step_", "").replace("_success", ""))
                if ref_idx not in step_indices:
                    warnings.append(f"步骤{step.get('index')}: condition 引用了不存在的步骤{ref_idx}")
                if ref_idx == step.get("index"):
                    warnings.append(f"步骤{step.get('index')}: condition 引用了自己（死条件）")
            except ValueError:
                pass

    # 12. 空步骤检查
    for step in steps:
        if not step.get("action") and not step.get("skill_instruction"):
            warnings.append(f"步骤{step.get('index')}: action 和 skill_instruction 都为空")

    # 13. 依赖合理性检查
    for step in steps:
        idx = step.get("index", 0)
        deps = step.get("depends_on", [])
        if idx in deps:
            errors.append(f"步骤{idx}: 不能依赖自己")
        for d in deps:
            if d >= idx:
                warnings.append(f"步骤{idx}: 依赖步骤{d}（index >= 自己），拓扑排序可能异常")

'''
    if '# 6. 步骤 index 连续性检查' not in c:
        c = c[:insert_at] + enhanced + c[insert_at:]
        print("  ✅ cmd_validate 增强检查已插入")
    else:
        print("  ⚠️  cmd_validate 增强检查已存在")

    p.write_text(c, encoding="utf-8")
    return True


if __name__ == "__main__":
    print("=== 补全 P0 补丁 ===")
    r1 = patch_chain_manager()
    r2 = patch_chain_executor()
    if r1 and r2:
        print("\n✅ 所有补丁成功！")
    else:
        print("\n⚠️  部分补丁失败")
