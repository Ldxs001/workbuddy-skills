#!/usr/bin/env python3
"""
补丁脚本：为 skill-sub 添加断点续执行 + 链静态检查增强
- chain_manager.py: 添加断点续执行（save/load/clear progress, --resume 参数）
- chain_executor.py: 增强 cmd_validate 函数
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

SKILL_DIR = Path(r"C:\Users\sm001\.workbuddy\skills\skill-sub")
CHAIN_DIR = SKILL_DIR / "data" / "chains"
STATE_DIR  = SKILL_DIR / "data" / "state"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ============================================================
# 补丁1：chain_manager.py 添加断点续执行
# ============================================================
def patch_chain_manager():
    p = SKILL_DIR / "scripts" / "chain_manager.py"
    content = p.read_text(encoding="utf-8")

    # ---- 1. 在 ensure_dirs() 调用后添加状态目录创建 ----
    old = '    CHAIN_DIR.mkdir(parents=True, exist_ok=True)'
    new = '''    CHAIN_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)'''
    if old in content and 'STATE_DIR' not in content[:content.find(old)+100]:
        content = content.replace(old, new, 1)
        print("  ✅ 补丁1a: STATE_DIR 创建已添加")
    else:
        print("  ⚠️  补丁1a: STATE_DIR 已存在或未找到插入点")

    # ---- 2. 在文件末尾的 argparse 之前插入进度管理函数 ----
    # 找 main 函数或 if __name__ == "__main__"
    main_marker = 'if __name__ == "__main__":'
    if main_marker not in content:
        print("  ❌ 未找到 main 入口点")
        return False

    insert_pos = content.find(main_marker)

    progress_funcs = '''\n\n# ============================================================\n# 断点续执行：进度管理\n# ============================================================\n\ndef get_progress_path(chain_name):\n    """返回进度文件路径"""\n    safe = chain_name.replace(" ", "_").replace("/", "_").replace("\\\\", "_")\n    return STATE_DIR / f"{safe}_progress.json"\n\n\ndef save_run_progress(chain_name, current_step, step_results, variables=None):\n    \"\"\"保存执行进度（每完成一步调用一次）\"\"\"\n    path = get_progress_path(chain_name)\n    chain = load_chain(chain_name)\n    data = {\n        "chain_name": chain_name,\n        "chain_updated_at": chain.get("updated_at", "") if chain else "",\n        "current_step": current_step,\n        "step_results": step_results,\n        "variables": variables or {},\n        "start_time": step_results.get("_start_time", now_iso()),\n        "last_update": now_iso(),\n    }\n    # 首次保存时记录开始时间\n    if "_start_time" not in step_results:\n        data["step_results"]["_start_time"] = data["start_time"]\n    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")\n\n\ndef load_run_progress(chain_name):\n    \"\"\"加载执行进度。返回 (data, error)。\"\"\"\n    path = get_progress_path(chain_name)\n    if not path.exists():\n        return None, "没有找到可恢复的进度"\n    try:\n        data = json.loads(path.read_text(encoding="utf-8"))\n    except Exception as e:\n        return None, f"进度文件损坏: {e}"\n\n    # 验证链是否发生变化\n    chain = load_chain(chain_name)\n    if chain:\n        if data.get("chain_updated_at") != chain.get("updated_at", ""):\n            return data, "WARNING_CHAIN_CHANGED"  # 特殊警告，不直接失败\n    return data, None\n\n\ndef clear_run_progress(chain_name):\n    \"\"\"清除执行进度（执行完成或用户取消后调用）\"\"\"\n    path = get_progress_path(chain_name)\n    if path.exists():\n        path.unlink()\n\n\ndef print_progress_summary(data):\n    \"\"\"打印进度摘要\"\"\"\n    chain_name = data.get("chain_name", "?")\n    current = data.get("current_step", 0)\n    results = data.get("step_results", {})\n    total = len([k for k in results if k != "_start_time"])\n    done = sum(1 for k, v in results.items() if k != "_start_time" and v is True)\n    failed = sum(1 for k, v in results.items() if k != "_start_time" and v is False)\n    print(f"\\n📊 执行进度恢复: {chain_name}")\n    print(f"  已完成: {done} 步 | 失败: {failed} 步 | 下一步: 第 {current} 步")\n    print(f"  开始时间: {results.get('_start_time', '未知')}")\n    print(f"  最后更新: {data.get('last_update', '未知')}")\n\n'''
    # 插入到 main 之前
    if 'def get_progress_path' not in content:
        content = content[:insert_pos] + progress_funcs + content[insert_pos:]
        print("  ✅ 补丁1b: 进度管理函数已插入")
    else:
        print("  ⚠️  补丁1b: 进度管理函数已存在")

    # ---- 3. 修改 cmd_run 支持 --resume ----
    # 在 cmd_run 中添加 --resume 参数
    old_run = '    p_run.add_argument("name", help="调用链名称")'
    new_run = '''    p_run.add_argument("name", help="调用链名称")
    p_run.add_argument("--resume", action="store_true", help="从断点恢复执行")
    p_run.add_argument("--no-save-progress", action="store_true", help="不保存执行进度")'''
    if old_run in content and '--resume' not in content:
        content = content.replace(old_run, new_run, 1)
        print("  ✅ 补丁1c: --resume 参数已添加")
    else:
        print("  ⚠️  补丁1c: --resume 参数已存在或未找到插入点")

    # ---- 4. 在 cmd_run 函数末尾添加进度恢复逻辑 ----
    # 找 cmd_run 的 return 0 之前，添加进度恢复说明
    # 由于 cmd_run 实际上只是生成执行计划，不真正执行，
    # 所以我们需要在输出执行计划时，附加上 "从断点恢复" 的提示
    # 以及让 AI 知道有哪些步骤已经完成

    # 更简单的方法：在 cmd_run 输出执行计划后，附加恢复信息
    old_cmd_run_end = '    print(f"\\n✅ 执行计划已生成。请按上述步骤执行（三层回退策略）。")'
    new_cmd_run_end = '''    # 断点续执行：检查是否有可恢复的进度
    progress_path = get_progress_path(args.name)
    if progress_path.exists() and not getattr(args, 'resume', False):
        try:
            pdata = json.loads(progress_path.read_text(encoding='utf-8'))
            done = sum(1 for k, v in pdata.get('step_results', {}).items() if k != '_start_time' and v is True)
            total = len([k for k in pdata.get('step_results', {}) if k != '_start_time'])
            print(f"\\n💡 检测到未完成的执行进度（已完成 {done}/{total} 步）")
            print(f"   恢复执行: python chain_manager.py run {args.name} --resume")
            print(f"   清除进度: python chain_manager.py clear-progress --name {args.name}")
        except Exception:
            pass
    elif getattr(args, 'resume', False) and progress_path.exists():
        pdata, err = load_run_progress(args.name)
        if err and err != 'WARNING_CHAIN_CHANGED':
            print(f"\\n❌ 无法恢复进度: {err}")
        else:
            if err == 'WARNING_CHAIN_CHANGED':
                print(f"\\n⚠️  警告: 调用链已修改，进度可能不准确")
            print_progress_summary(pdata)
            print(f"\\n  请在 AI 执行时跳过已完成步骤，从步骤 {pdata.get('current_step', 1)} 开始")
            print(f"  已完成步骤结果: { {k:v for k,v in pdata.get('step_results',{}).items() if k!='_start_time'} }")

    print(f"\\n✅ 执行计划已生成。请按上述步骤执行（三层回退策略）。")'''

    if old_cmd_run_end.split('\n')[0] in content and 'get_progress_path' not in content[content.find('def cmd_run('):content.find('def cmd_run(')+5000]:
        # 更精确的查找
        marker = 'print(f"\\n✅ 执行计划已生成。请按上述步骤执行'
        if marker in content:
            # 找到这行，替换它及后面部分
            idx = content.find(marker)
            # 找行尾
            line_end = content.find('\\n', idx)
            # 替换为新内容
            new_block = new_cmd_run_end
            content = content[:idx] + new_block + content[line_end:]
            print("  ✅ 补丁1d: cmd_run 断点恢复逻辑已添加")
        else:
            print("  ⚠️  补丁1d: 未找到插入点（marker not found）")
    else:
        print("  ⚠️  补丁1d: 断点恢复逻辑已存在或 cmd_run 结构已变")

    # ---- 5. 添加 cmd_clear_progress 和 cmd_resume 命令 ----
    # 在 argparse 中添加 clear-progress 子命令
    # 找 "p_run" 的 add_parser 之后，添加 clear-progress

    if 'p_clear = subparsers.add_parser("clear-progress"' not in content:
        # 在 p_run.add_parser 之后插入
        insert_after = '    p_run = subparsers.add_parser("run", help="输出执行计划")'
        if insert_after in content:
            new_cmds = '''
    p_clear = subparsers.add_parser("clear-progress", help="清除执行进度")
    p_clear.add_argument("name", help="调用链名称")
    p_clear.set_defaults(func=cmd_clear_progress)

    p_resume = subparsers.add_parser("resume", help="从断点恢复执行（等价 run --resume）")
    p_resume.add_argument("name", help="调用链名称")
    p_resume.set_defaults(func=cmd_resume)
'''
            pos = content.find(insert_after) + len(insert_after)
            content = content[:pos] + new_cmds + content[pos:]
            print("  ✅ 补丁1e: clear-progress/resume 子命令已添加")
        else:
            print("  ⚠️  补丁1e: 未找到插入点")
    else:
        print("  ⚠️  补丁1e: clear-progress 子命令已存在")

    # ---- 6. 添加 cmd_clear_progress 和 cmd_resume 函数 ----
    if 'def cmd_clear_progress(' not in content:
        # 在 cmd_run 函数之前插入这两个函数
        insert_before = 'def cmd_run('
        if insert_before in content:
            new_funcs = '''\n\ndef cmd_clear_progress(args):
    """清除执行进度"""
    progress_path = get_progress_path(args.name)
    if not progress_path.exists():
        print(f"⚠️  没有找到 {args.name} 的执行进度")
        return 0
    try:
        progress_path.unlink()
        print(f"✅ 已清除 {args.name} 的执行进度")
    except Exception as e:
        print(f"❌ 清除失败: {e}")
        return 1
    return 0\n\n\ndef cmd_resume(args):
    """从断点恢复执行（包装 cmd_run --resume）"""
    args.resume = True
    return cmd_run(args)\n\n\n'''

            pos = content.find(insert_before)
            content = content[:pos] + new_funcs + content[pos:]
            print("  ✅ 补丁1f: cmd_clear_progress/cmd_resume 函数已添加")
        else:
            print("  ⚠️  补丁1f: 未找到插入点")
    else:
        print("  ⚠️  补丁1f: cmd_clear_progress 函数已存在")

    # 写入文件
    p.write_text(content, encoding="utf-8")
    print("✅ chain_manager.py 补丁完成")
    return True


# ============================================================
# 补丁2：chain_executor.py 增强 cmd_validate 函数
# ============================================================
def patch_chain_executor():
    p = SKILL_DIR / "scripts" / "chain_executor.py"
    content = p.read_text(encoding="utf-8")

    # 在 cmd_validate 的 "输出结果" 部分之前插入增强检查
    # 找 "if not errors and not warnings:" 之前

    marker = '    # 输出结果\n    print(f"🔍 验证调用链:'
    if marker not in content:
        print("  ❌ 未找到 cmd_validate 输出部分")
        return False

    insert_pos = content.find(marker)

    # 构建增强检查代码
    enhanced_checks = '''\n    # 6. 步骤 index 连续性检查\n    indices = sorted([s.get("index", i+1) for i, s in enumerate(steps)])\n    expected = list(range(1, len(indices)+1))\n    if indices != expected:\n        missing = set(expected) - set(indices)\n        if missing:\n            errors.append(f"步骤 index 不连续，缺少 index: {sorted(missing)}")\n        dup = [idx for idx in indices if indices.count(idx) > 1]\n        if dup:\n            errors.append(f"步骤 index 重复: {set(dup)}")\n\n    # 7. 步骤名唯一性检查\n    names = [s.get("step_name", "") for s in steps if s.get("step_name")]\n    if len(names) != len(set(names)):\n        from collections import Counter\n        dup = [n for n, c in Counter(names).items() if c > 1]\n        warnings.append(f"步骤名重复: {dup}")\n\n    # 8. 条件表达式格式检查\n    import re\n    cond_pattern = re.compile(r"^(step_\\d+_(success|failed)|always|never|variable_\\w+_exists)$")\n    for step in steps:\n        cond = step.get("condition", "")\n        if cond and not cond_pattern.match(cond.strip()):\n            warnings.append(f"步骤{step.get('index')}: condition 格式可能不正确: {cond}")\n\n    # 9. 输出变量冲突检测\n    output_vars = {}\n    for step in steps:\n        for var_name, var_def in (step.get("variables", {})).items():\n            if var_def.get("direction") == "output":\n                if var_name in output_vars:\n                    warnings.append(f"输出变量冲突: {var_name} 在步骤{output_vars[var_name]} 和步骤{step.get('index')} 都定义为输出")\n                else:\n                    output_vars[var_name] = step.get("index")\n\n    # 10. 重试策略合理性检查\n    default_max = load_user_config().get("default_max_retries", 3) if 'load_user_config' in dir() else 3\n    for step in steps:\n        rp = step.get("retry_policy", {})\n        max_r = rp.get("max_retries", default_max)\n        if max_r < 0:\n            errors.append(f"步骤{step.get('index')}: max_retries 不能为负数")\n        elif max_r > 10:\n            warnings.append(f"步骤{step.get('index')}: max_retries={max_r} 过大，建议 ≤10")\n\n    # 11. 死代码检查（条件永远无法满足）\n    step_indices = {s.get("index") for s in steps}\n    for step in steps:\n        cond = step.get("condition", "").strip()\n        if cond.startswith("step_") and cond.endswith("_success"):\n            try:\n                ref_idx = int(cond.replace("step_", "").replace("_success", ""))\n                if ref_idx not in step_indices:\n                    warnings.append(f"步骤{step.get('index')}: condition 引用了不存在的步骤{ref_idx}")\n                # 检查是否是自己的 index\n                if ref_idx == step.get("index"):\n                    warnings.append(f"步骤{step.get('index')}: condition 引用了自己（死条件）")\n            except ValueError:\n                pass\n\n    # 12. 空步骤检查（action 和 skill_instruction 都为空）\n    for step in steps:\n        if not step.get("action") and not step.get("skill_instruction"):\n            warnings.append(f"步骤{step.get('index')}: action 和 skill_instruction 都为空")\n\n    # 13. 依赖合理性检查\n    for step in steps:\n        idx = step.get("index", 0)\n        deps = step.get("depends_on", [])\n        if idx in deps:\n            errors.append(f"步骤{idx}: 不能依赖自己")\n        for d in deps:\n            if d >= idx:\n                warnings.append(f"步骤{idx}: 依赖步骤{d}（index >= 自己），可能导致拓扑排序异常")\n\n'''

    # 插入到输出结果之前
    if '# 输出结果' not in content[max(0,insert_pos-500):insert_pos+100]:
        # 直接在 marker 之前插入
        content = content[:insert_pos] + enhanced_checks + '\n' + content[insert_pos:]
        print("  ✅ 补丁2a: 增强检查项已插入 cmd_validate")
    else:
        print("  ⚠️  补丁2a: 增强检查项已存在")

    p.write_text(content, encoding="utf-8")
    print("✅ chain_executor.py 补丁完成")
    return True


if __name__ == "__main__":
    print("=== 开始打补丁 ===")
    print("[1/2] 补丁 chain_manager.py ...")
    r1 = patch_chain_manager()
    print("[2/2] 补丁 chain_executor.py ...")
    r2 = patch_chain_executor()

    if r1 and r2:
        print("\n✅ 所有补丁成功！")
    else:
        print("\n⚠️  部分补丁失败，请检查上述输出")
