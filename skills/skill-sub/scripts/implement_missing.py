#!/usr/bin/env python3
"""
implement_missing.py - 稳定实现 skill-sub 缺失的 4 个功能
用读写文件方式修改 chain_manager.py，不使用 Edit 工具。
"""

import re
import sys
from pathlib import Path

TARGET = Path(r"C:\Users\sm001\.workbuddy\skills\skill-sub\scripts\chain_manager.py")

def read_file():
    return TARGET.read_text(encoding="utf-8")

def write_file(content):
    TARGET.write_text(content, encoding="utf-8")
    print(f"✅ 已写入 {TARGET}")

def backup():
    bak = TARGET.with_suffix(".py.bak_missing")
    bak.write_text(read_file(), encoding="utf-8")
    print(f"📦 备份到 {bak}")
    return bak

def implement():
    content = read_file()

    # ============================================================
    # 1. 在 main() 的 subparsers 区域注册缺失的 subcommand
    # ============================================================
    # 找到最后一个 p_es.set_defaults 的位置，在其后插入新 subcommand

    insert_marker = '    p_es.set_defaults(func=cmd_error_stats)'
    if insert_marker not in content:
        print("❌ 找不到插入点 p_es.set_defaults")
        return False

    new_parsers = '''

    # P2: list-tags - 链标签系统增强
    p_lt = subparsers.add_parser("list-tags", help="列出所有标签及使用统计")
    p_lt.add_argument("--min-count", type=int, default=1, help="最少使用次数（过滤）")
    p_lt.add_argument("--sort", choices=["count", "name"], default="count", help="排序方式")
    p_lt.set_defaults(func=cmd_list_tags)

    # P2: tag-enhance - 标签管理（函数已存在，补注册）
    p_tage = subparsers.add_parser("tag-enhance", help="管理调用链标签（add/remove/list）")
    p_tage.add_argument("--name", required=True, help="调用链名称")
    p_tage.add_argument("--subcmd", choices=["add", "remove", "list"], required=True, help="操作")
    p_tage.add_argument("--tag", help="标签名称（add/remove 时必填）")
    p_tage.set_defaults(func=cmd_tag_enhance)

    # P2: milestones - 里程碑影响分析
    p_ms = subparsers.add_parser("milestones", help="里程碑影响分析")
    p_ms.add_argument("--name", required=True, help="调用链名称")
    p_ms.add_argument("--dynamic", action="store_true", help="启用动态里程碑（基于执行历史调整）")
    p_ms.add_argument("--impact", action="store_true", help="输出影响分析报告")
    p_ms.set_defaults(func=cmd_milestones)

    # P2: milestone-stats - 里程碑统计
    p_mss = subparsers.add_parser("milestone-stats", help="里程碑统计分析")
    p_mss.add_argument("--name", required=True, help="调用链名称")
    p_mss.add_argument("--history", action="store_true", help="包含执行历史统计")
    p_mss.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    p_mss.set_defaults(func=cmd_milestone_stats)
'''

    if 'p_lt = subparsers.add_parser("list-tags"' in content:
        print("⚠️  list-tags parser 已存在，跳过注册")
    else:
        content = content.replace(
            insert_marker,
            insert_marker + new_parsers
        )
        print("✅ 已注册 4 个新 subcommand 到 parser")

    # ============================================================
    # 2. 添加 cmd_list_tags 函数（在 cmd_tag_enhance 之前插入）
    # ============================================================
    cmd_list_tags_func = '''

def cmd_list_tags(args):
    """列出所有标签及使用统计"""
    import os
    chain_dir = CHAINS_DIR
    if not chain_dir.exists():
        print("❌ chains 目录不存在")
        return 1

    tag_counter = {}      # tag -> count
    tag_chains = {}       # tag -> [chain_names]
    tag_last_used = {}    # tag -> latest usage timestamp

    for fpath in chain_dir.glob("*.json"):
        if fpath.name == "index.json":
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            chain_name = data.get("name", fpath.stem)
            for t in data.get("tags", []):
                tag_counter[t] = tag_counter.get(t, 0) + 1
                if t not in tag_chains:
                    tag_chains[t] = []
                tag_chains[t].append(chain_name)
                # 取最新执行时间
                last = data.get("last_executed")
                if last:
                    cur = tag_last_used.get(t)
                    if not cur or last > cur:
                        tag_last_used[t] = last
        except Exception as e:
            continue

    if not tag_counter:
        print("📭  没有找到任何标签")
        return 0

    # 排序
    reverse = (args.sort == "count")
    sorted_tags = sorted(tag_counter.items(), key=lambda x: -x[1] if reverse else x[0])

    # 过滤
    filtered = [(t, c) for t, c in sorted_tags if c >= args.min_count]

    if not filtered:
        print(f"📭  没有标签满足 min-count={args.min_count}")
        return 0

    print(f"🏷️  标签统计 (共 {len(filtered)} 个标签，按{'使用次数' if args.sort=='count' else '名称'}排序)")
    print("=" * 60)
    for tag, cnt in filtered:
        chains_str = "、".join(tag_chains.get(tag, [])[:3])
        if len(tag_chains.get(tag, [])) > 3:
            chains_str += f" 等 {len(tag_chains[tag])} 个"
        last_str = ""
        if tag in tag_last_used:
            last_str = f" | 最近使用: {tag_last_used[tag]}"
        print(f"  {tag:<20} {cnt:>3} 次  [{chains_str}]{last_str}")

    return 0

'''

    if 'def cmd_list_tags(args)' in content:
        print("⚠️  cmd_list_tags 已存在，跳过添加")
    else:
        # 在 cmd_tag_enhance 函数定义前插入
        content = content.replace(
            'def cmd_tag_enhance(args):',
            cmd_list_tags_func + 'def cmd_tag_enhance(args):'
        )
        print("✅ 已添加 cmd_list_tags 函数")

    # ============================================================
    # 3. 修复 cmd_tag_enhance 中的路径错误（使用 CHAINS_DIR 常量）
    # ============================================================
    old_path_code = '        chain_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "chains")'
    new_path_code = '        chain_dir = str(CHAINS_DIR)'
    if old_path_code in content:
        content = content.replace(old_path_code, new_path_code)
        print("✅ 已修复 cmd_tag_enhance 中的路径（使用 CHAINS_DIR 常量）")
    else:
        print("⚠️  cmd_tag_enhance 中的路径代码已修改或不存在，跳过")

    # ============================================================
    # 4. 添加 cmd_milestones 函数（里程碑影响分析 + 动态里程碑）
    # ============================================================
    cmd_milestones_func = '''

def cmd_milestones(args):
    """里程碑影响分析 + 动态里程碑"""
    import os
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链不存在: {args.name}")
        return 1

    steps = chain.get("steps", [])
    if not steps:
        print(f"❌ 调用链 {args.name} 没有步骤")
        return 1

    ms_results = classify_milestones(steps)
    milestone_steps = [r for r in ms_results if r["is_milestone"]]

    print(f"📊 里程碑影响分析: {args.name}")
    print("=" * 60)
    print(f"  总步骤: {len(steps)}  |  里程碑: {len(milestone_steps)} 步")
    print()

    # 影响分析
    if args.impact or True:  # 默认也输出基本信息
        print("  【里程碑列表】")
        for r in ms_results:
            icon = "★" if r["is_milestone"] else "○"
            step = next((s for s in steps if s.get("index", 0) == r["step_index"]), None)
            name = step.get("step_name", "?") if step else "?"
            print(f"    {icon} 步骤{r['step_index']}: {name}")
            print(f"       原因: {r['reason']}")
            if step:
                deps = step.get("depends_on", [])
                if deps:
                    print(f"       依赖: {deps}")
                # 找出哪些步骤依赖此步骤
                downstream = [s.get("index") for s in steps if r["step_index"] in s.get("depends_on", [])]
                if downstream:
                    print(f"       被依赖: {downstream}")
            print()

    # 动态里程碑（基于执行历史调整）
    if args.dynamic:
        print("  【动态里程碑调整】")
        history = chain.get("execution_history", [])
        if not history:
            print("    ⚠️  没有执行历史，无法动态调整")
            print("    提示: 执行链后 retry 信息会被记录到 execution_history")
        else:
            # 统计每个步骤的失败/重试次数
            step_stats = {}
            for record in history:
                for step_r in record.get("step_results", []):
                    idx = step_r.get("step_index")
                    if idx not in step_stats:
                        step_stats[idx] = {"attempts": 0, "failures": 0, "retries": 0}
                    step_stats[idx]["attempts"] += 1
                    if not step_r.get("success"):
                        step_stats[idx]["failures"] += 1
                    step_stats[idx]["retries"] += step_r.get("retries", 0)

            print("    基于执行历史，以下步骤建议设为里程碑（高频失败/重试）:")
            suggestions = []
            for idx, stats in step_stats.items():
                fail_rate = stats["failures"] / max(stats["attempts"], 1)
                if fail_rate > 0.3 or stats["retries"] > 2:
                    suggestions.append((idx, fail_rate, stats["retries"]))
            if suggestions:
                for idx, fr, retries in sorted(suggestions, key=lambda x: -x[1]):
                    step = next((s for s in steps if s.get("index") == idx), None)
                    name = step.get("step_name", "?") if step else "?"
                    print(f"      ★ 步骤{idx}: {name}  (失败率 {fr*100:.0f}%, 重试 {retries} 次)")
            else:
                print("    ✅ 所有步骤执行稳定，无需新增里程碑")

        print()

    # 风险分析
    print("  【风险分析】")
    if len(milestone_steps) == 0:
        print("    ⚠️  没有里程碑！建议至少将最后一步设为里程碑")
    elif len(milestone_steps) == len(steps):
        print("    ⚠️  所有步骤都是里程碑，可能过于保守")
    else:
        non_ms = [r for r in ms_results if not r["is_milestone"]]
        print(f"    非里程碑步骤: {len(non_ms)} 个（允许跳过/快速失败）")
        print(f"    里程碑步骤: {len(milestone_steps)} 个（必须确认/不可跳过）")

    return 0

'''

    if 'def cmd_milestones(args)' in content:
        print("⚠️  cmd_milestones 已存在，跳过添加")
    else:
        # 在 cmd_check_compat 函数前插入（它在文件末尾附近）
        insert_before = 'def cmd_check_compat(args):'
        if insert_before in content:
            content = content.replace(
                insert_before,
                cmd_milestones_func + insert_before
            )
            print("✅ 已添加 cmd_milestones 函数")
        else:
            # 追加到文件末尾（在 if __name__ 之前）
            content = content.replace(
                'if __name__ == "__main__":',
                cmd_milestones_func + 'if __name__ == "__main__":'
            )
            print("✅ 已添加 cmd_milestones 函数（追加到文件末尾）")

    # ============================================================
    # 5. 添加 cmd_milestone_stats 函数
    # ============================================================
    cmd_milestone_stats_func = '''

def cmd_milestone_stats(args):
    """里程碑统计分析"""
    import os
    chain = load_chain(args.name)
    if not chain:
        print(f"❌ 调用链不存在: {args.name}")
        return 1

    steps = chain.get("steps", [])
    ms_results = classify_milestones(steps)

    # 基本统计
    total = len(steps)
    ms_count = sum(1 for r in ms_results if r["is_milestone"])
    non_ms_count = total - ms_count

    # 原因分布
    reason_dist = {}
    for r in ms_results:
        reason = r["reason"].split("（")[0]  # 取原因主体（去掉括号详情）
        reason_dist[reason] = reason_dist.get(reason, 0) + 1

    if args.format == "json":
        result = {
            "chain_name": args.name,
            "total_steps": total,
            "milestone_count": ms_count,
            "non_milestone_count": non_ms_count,
            "milestone_ratio": round(ms_count / max(total, 1), 2),
            "reason_distribution": reason_dist,
            "milestones": [r for r in ms_results if r["is_milestone"]],
        }
        # 历史统计
        if args.history:
            history = chain.get("execution_history", [])
            result["execution_history_count"] = len(history)
            if history:
                total_dur = sum(r.get("total_duration", 0) for r in history)
                result["avg_duration"] = round(total_dur / len(history), 2)
                # 里程碑步骤的平均耗时
                ms_indices = set(r["step_index"] for r in ms_results if r["is_milestone"])
                ms_durs = []
                for rec in history:
                    for sr in rec.get("step_results", []):
                        if sr.get("step_index") in ms_indices:
                            ms_durs.append(sr.get("duration", 0))
                if ms_durs:
                    result["milestone_avg_duration"] = round(sum(ms_durs) / len(ms_durs), 2)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # 文本输出
    print(f"📊 里程碑统计: {args.name}")
    print("=" * 60)
    print(f"  总步骤数:       {total}")
    print(f"  里程碑步骤:     {ms_count} ({ms_count/max(total,1)*100:.0f}%)")
    print(f"  非里程碑步骤:   {non_ms_count} ({non_ms_count/max(total,1)*100:.0f}%)")
    print()
    print("  【原因分布】")
    for reason, cnt in sorted(reason_dist.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {cnt} 步")
    print()

    # 里程碑详情
    print("  【里程碑步骤】")
    for r in ms_results:
        if r["is_milestone"]:
            step = next((s for s in steps if s.get("index", 0) == r["step_index"]), None)
            name = step.get("step_name", "?") if step else "?"
            print(f"    ★ 步骤{r['step_index']}: {name}")
            print(f"       原因: {r['reason']}")
    print()

    # 历史统计
    if args.history:
        history = chain.get("execution_history", [])
        print(f"  【执行历史】({len(history)} 条记录)")
        if history:
            total_dur = sum(r.get("total_duration", 0) for r in history)
            avg_dur = total_dur / len(history)
            print(f"    平均总耗时: {avg_dur:.1f}s")
            # 里程碑步骤耗时
            ms_indices = set(r["step_index"] for r in ms_results if r["is_milestone"])
            ms_durs = []
            for rec in history:
                for sr in rec.get("step_results", []):
                    if sr.get("step_index") in ms_indices:
                        ms_durs.append(sr.get("duration", 0))
            if ms_durs:
                print(f"    里程碑平均耗时: {sum(ms_durs)/len(ms_durs):.1f}s")
        else:
            print("    （无执行历史）")

    return 0

'''

    if 'def cmd_milestone_stats(args)' in content:
        print("⚠️  cmd_milestone_stats 已存在，跳过添加")
    else:
        # 在 cmd_milestones 函数前插入
        if 'def cmd_milestones(args):' in content:
            content = content.replace(
                'def cmd_milestones(args):',
                cmd_milestone_stats_func + 'def cmd_milestones(args):'
            )
            print("✅ 已添加 cmd_milestone_stats 函数")
        else:
            # 追加到文件末尾
            content += cmd_milestone_stats_func
            print("✅ 已添加 cmd_milestone_stats 函数（追加）")

    # ============================================================
    # 6. 写回文件
    # ============================================================
    write_file(content)
    return True

def verify():
    """验证语法"""
    import py_compile
    try:
        py_compile.compile(str(TARGET), doraise=True)
        print("✅ 语法验证通过")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ 语法错误: {e}")
        return False

def test_commands():
    """测试新注册的 subcommand 是否能正常显示 help"""
    import subprocess
    py = r"C:\Users\sm001\.workbuddy\binaries\python\versions\3.13.12\python.exe"
    
    for cmd in ["list-tags", "tag-enhance", "milestones", "milestone-stats"]:
        result = subprocess.run(
            [py, str(TARGET), cmd, "--help"],
            capture_output=True, text=True
        )
        if "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower():
            print(f"  ✅ {cmd} --help 正常")
        else:
            print(f"  ❌ {cmd} --help 失败: {result.stderr[:100]}")

    return True

if __name__ == "__main__":
    print("=" * 60)
    print("实现 skill-sub 缺失的 4 个功能")
    print("=" * 60)
    
    backup()
    ok = implement()
    if not ok:
        print("❌ 实现失败")
        sys.exit(1)
    
    if not verify():
        print("❌ 语法验证失败，请检查")
        sys.exit(1)
    
    print()
    print("测试新 subcommand:")
    test_commands()
    
    print()
    print("🎉 全部完成！")
    print()
    print("新增/修复的功能:")
    print("  1. list-tags      - 链标签系统增强（列出所有标签统计）")
    print("  2. tag-enhance    - 标签管理（已存在函数，补注册到 parser）")
    print("  3. milestones     - 里程碑影响分析 + 动态里程碑（--dynamic）")
    print("  4. milestone-stats - 里程碑统计分析（--history 支持执行历史）")
