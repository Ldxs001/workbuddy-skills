"""
runner.py — 场景测试全流程编排器

代码硬编码的 8 阶段流程（不可跳过、不可乱序）：
1. 备份 → 2. 蓝皮书 → 3. 询问 → 4. 场景+功能测试 → 5. 修复/报告 → 6. 回归循环 → 7. 回归确认 → 8. 报告输出

LLM 交互点：
- Stage 3: LLM 展示测试计划给用户，收集选择
- Stage 5 (mode=ask): LLM 逐条展示修复项给用户，收集 y/N
- Stage 5 (mode=direct): LLM 读取修复建议，执行自动修复
- Stage 7: LLM 展示回归对比结果
"""
import json
import os
import shutil
import sys
from datetime import datetime

# ═══════════════════════════════════════════════════════
# 8 阶段状态常量
# ═══════════════════════════════════════════════════════

STAGES = {
    1: "备份",
    2: "蓝皮书扫描",
    3: "询问测试计划",
    4: "场景+功能测试",
    5: "LLM 后处理过滤",
    6: "修复",
    7: "回归循环",
    8: "回归确认",
    9: "报告输出",
    10: "自动版本号更新",
    11: "清理",
}

# ═══════════════════════════════════════════════════════
# 流程状态
# ═══════════════════════════════════════════════════════

class PipelineState:
    """全流程状态对象，记录每个阶段的结果"""
    def __init__(self, skill_dir: str):
        self.skill_dir = os.path.abspath(skill_dir)
        self.skill_name = os.path.basename(self.skill_dir)
        self.current_stage = 0
        self.stage_log = {}  # stage -> {status, result, timestamp}

        # 各阶段产出物
        self.backup_path: str = ""
        self.blueprint: dict = {}
        self.blueprint_text: str = ""
        self.test_plan: dict = {}        # {dimensions: [], fix_mode: str}
        self.scenario_report: dict = {}
        self.function_report: dict = {}
        self.scenario_text: str = ""
        self.function_text: str = ""
        self.fix_results: list[dict] = []  # [{type, file, success, detail}]
        self.regression_report: dict = {}
        self.regression_text: str = ""
        self.final_report: str = ""

    def log_stage(self, stage: int, status: str, result: str = ""):
        self.stage_log[stage] = {
            "stage": STAGES.get(stage, f"阶段{stage}"),
            "status": status,
            "result": result[:500],
            "timestamp": datetime.now().isoformat(),
        }
        self.current_stage = stage

    def summary(self) -> str:
        lines = [f"=== 流程进度: {self.skill_name} ==="]
        for s in sorted(self.stage_log):
            entry = self.stage_log[s]
            icon = {"ok": "✅", "skip": "⏭️", "blocked": "❌", "pending": "⏳"}.get(
                entry["status"], "❓")
            lines.append(f"  {icon} 阶段{s} {entry['stage']}: {entry['status']}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 阶段执行函数
# ═══════════════════════════════════════════════════════

def stage_1_backup(state: PipelineState) -> PipelineState:
    """阶段1: 备份"""
    from backup import backup_skill
    print(f"\n{'='*50}")
    print(f"  阶段1/8: 备份")
    print(f"{'='*50}")

    if not os.path.exists(state.skill_dir):
        raise FileNotFoundError(f"目标目录不存在: {state.skill_dir}")

    state.backup_path = backup_skill(state.skill_dir, "pre_test")
    state.log_stage(1, "ok", f"备份路径: {state.backup_path}")
    return state


def stage_2_blueprint(state: PipelineState) -> PipelineState:
    """阶段2: 蓝皮书扫描"""
    from inspector import scan, print_bluebook
    print(f"\n{'='*50}")
    print(f"  阶段2/8: 蓝皮书扫描")
    print(f"{'='*50}")

    bb = scan(state.skill_dir)
    state.blueprint = bb.to_dict()
    state.blueprint_text = print_bluebook(bb)
    print(state.blueprint_text)

    # 保存到目标技能目录
    bp_path = os.path.join(state.skill_dir, ".scenario-test_blueprint.json")
    with open(bp_path, "w", encoding="utf-8") as f:
        json.dump(state.blueprint, f, ensure_ascii=False, indent=2)
    print(f"\n  蓝皮书已保存: {bp_path}")

    state.log_stage(2, "ok",
        f"文件: {state.blueprint['file_count']} | 函数: {len(state.blueprint.get('functions',[]))}")
    return state


def stage_3_ask(state: PipelineState) -> PipelineState:
    """
    阶段3: 询问测试计划
    LLM 交互点 — 展示给用户，收集输入后返回
    """
    print(f"\n{'='*50}")
    print(f"  阶段3/8: 询问测试计划（LLM 交互点）")
    print(f"{'='*50}")

    bp = state.blueprint
    func_count = len(bp.get("functions", []))
    class_count = len(bp.get("classes", []))
    file_count = bp.get("file_count", 0)

    print(f"""
╔══════════════════════════════════════════════╗
║  技能蓝皮书摘要                            ║
╠══════════════════════════════════════════════╣
║  技能: {bp.get('skill_name','?'):<35s} ║
║  版本: {bp.get('version','?'):<35s} ║
║  文件: {file_count:<4d} 个                  ║
║  函数: {func_count:<4d} 个                  ║
║  类:   {class_count:<4d} 个                  ║
╚══════════════════════════════════════════════╝

=== 可测试的场景和维度 ===
序号 | 代号                     | 说明
-----|--------------------------|------------------------------------------
1    | S1 场景链路完整性         | 触发词→能力→流程→代码是否完整匹配
2    | S2 场景输入产出匹配       | 场景输入是否有对应函数实现
3    | S3 场景数据流正确性       | 步骤间数据传递是否连续
4    | D1 基础功能完整性         | 语法解析、函数存在性
5    | D2 流程断点检测           | 文件引用、import 链
6    | D3 数据污染检测           | 硬编码路径、DB 交叉
7    | D4 噪音/干扰检测          | 裸 print、副效应
8    | D5 计算正确性             | 零除风险、数值精度
9    | D6 边界鲁棒性             | 异常处理、空值保护

请选择测试范围（逗号分隔序号如 "1,2,3,4,5" 或 "all"）:
修复模式: [0] 仅报告 / [1] 直接修复 / [2] 询问后修复
    """.strip())

    # LLM 在此收集用户输入并设置 state.test_plan
    # test_plan = {"dimensions": [...], "fix_mode": 0/1/2}

    state.log_stage(3, "pending", "等待 LLM 收集用户选择")
    return state


def stage_4_test(state: PipelineState) -> PipelineState:
    """阶段4: 执行场景+功能测试"""
    from scenario_engine import run_scenario_test
    from test_engine import run_full_test as run_function_test
    print(f"\n{'='*50}")
    print(f"  阶段4/8: 执行测试")
    print(f"{'='*50}")

    plan = state.test_plan
    dims = plan.get("dimensions", "all")

    # 场景测试
    if dims == "all" or any(d in dims for d in ["1", "2", "3"]):
        print("  [RUN] 场景测试 (S1-S3)...")
        s_report, s_text = run_scenario_test(state.skill_dir, state.blueprint)
        state.scenario_report = s_report
        state.scenario_text = s_text
        print(s_text)
        print()

    # 功能测试
    dim_map = {"4": "d1_smoke", "5": "d2_breakpoint", "6": "d3_contamination",
               "7": "d4_noise", "8": "d5_correctness", "9": "d6_robustness"}
    if dims == "all":
        func_dims = None
    else:
        func_dims = [dim_map[d] for d in dims if d in dim_map]

    print("  [RUN] 功能测试 (D1-D6)...")
    f_report, f_text = run_function_test(state.skill_dir, func_dims)
    state.function_report = f_report
    state.function_text = f_text
    print(f_text)

    state.log_stage(4, "ok",
        f"场景: {s_report['summary']['total']}项 | 功能: {f_report['summary']['total']}项")
    return state


# ═══════════════════════════════════════════════════════
# LLM 后处理过滤（阶段5：在修复之前）
# ═══════════════════════════════════════════════════════

def stage_5_llm_filter(state: PipelineState) -> PipelineState:
    """
    阶段5: LLM 后处理过滤

    在修复之前对测试结果进行 LLM 判断，区分误报(FP)和真问题。
    只修真问题，不修误报。

    输出格式: 每条问题附带源代码上下文、规则名、判断依据
    """
    print(f"\n{'='*50}")
    print(f"  阶段5/11: LLM 后处理过滤")
    print(f"{'='*50}")

    all_issues = []
    for src, data in [("场景", state.scenario_report), ("功能", state.function_report)]:
        for r in data.get("results", []):
            if r.get("level") in ("block", "warn") and r.get("status") == "fail":
                issue = {
                    "source": src,
                    "dim": r.get("sid", r.get("dim", "?")),
                    "level": r.get("level"),
                    "name": r.get("name", ""),
                    "message": r.get("message", ""),
                    "file": r.get("file", ""),
                    "lineno": r.get("lineno", 0),
                    "suggestion": r.get("suggestion", ""),
                    "llm_judgment": "",  # LLM 填写: FP / 真问题
                }
                if issue["file"] and issue["lineno"]:
                    fpath = os.path.join(state.skill_dir, issue["file"]) \
                        if not os.path.isabs(issue["file"]) else issue["file"]
                    if os.path.exists(fpath):
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                src_lines = f.read().split("\n")
                            start = max(0, issue["lineno"] - 4)
                            end = min(len(src_lines), issue["lineno"] + 3)
                            ctx = []
                            for i in range(start, end):
                                marker = "→" if i == issue["lineno"] - 1 else " "
                                ctx.append(f"{marker} {i+1:4d}| {src_lines[i]}")
                            issue["source_context"] = "\n".join(ctx)
                        except Exception:
                            issue["source_context"] = "(无法读取)"
                all_issues.append(issue)

    state.fix_results = all_issues

    if not all_issues:
        print("  无待判断问题，无需过滤")
        state.log_stage(5, "ok", "无问题")
        return state

    print(f"  共 {len(all_issues)} 条问题待 LLM 判断（FP/真问题）:")
    for i, issue in enumerate(all_issues, 1):
        print(f"\n  [{i}/{len(all_issues)}] {'⚠️' if issue['level']=='warn' else '🔴'} "
              f"[{issue['source']}:{issue['dim']}] {issue['name']}")
        print(f"    级别: F-{'0 BLOCK' if issue['level']=='block' else '1 WARN'}")
        print(f"    文件: {issue['file']}:{issue['lineno']}")
        print(f"    信息: {issue['message']}")
        if issue.get("source_context"):
            print(f"    代码上下文:\n{issue['source_context']}")
        print(f"    建议: {issue['suggestion']}")
        print(f"    ── LLM 判断: [FP] 误报 / [FIX] 真问题 ──")

    state.log_stage(5, "ok", f"待判断: {len(all_issues)} 条")
    return state


# ═══════════════════════════════════════════════════════
# 修复（阶段6：只修真问题）
# ═══════════════════════════════════════════════════════

def stage_6_fix(state: PipelineState, fix_mode: int = 0) -> PipelineState:

    # 收集所有 F-0 和 F-1 问题
    all_issues = []
    for r in state.scenario_report.get("results", []):
        if r.get("level") in ("block", "warn"):
            all_issues.append(("场景", r))
    for r in state.function_report.get("results", []):
        if r.get("level") in ("block", "warn"):
            all_issues.append(("功能", r))

    print(f"  发现 {len(all_issues)} 个待处理问题")

    if fix_mode == 0:
        print("  仅报告模式，不执行修复")

    elif fix_mode == 1:
        print("  直接修复模式，LLM 执行自动修复...")
        # LLM 此处执行: 遍历 all_issues, 调用 fixer.apply_fix()
        import fixer
        for category, issue in all_issues:
            fix_type = None
            msg = issue.get("message", "")
            if "零除" in msg or "零值" in msg:
                fix_type = "add_none_guard"
            elif "print" in msg and "裸" in msg:
                fix_type = "stdout_to_logging"
            elif "路径" in msg and "硬编码" in msg:
                fix_type = "hardcoded_path"
            if fix_type:
                print(f"  [FIX] {category}: {issue.get('name','')} — 尝试 {fix_type}")
                # 实际修复逻辑由 LLM 调用 fixer.apply_fix()

    elif fix_mode == 2:
        print("  询问模式，LLM 逐条展示给用户确认...")
        # LLM 此处: 逐一展示 issue, 收集用户 y/N

    state.log_stage(5, "ok", f"修复模式={fix_mode}, 问题数={len(all_issues)}")
    return state


def stage_10_bump(state: PipelineState) -> PipelineState:
    """
    阶段 5.5: 自动版本号 bump

    如果修复模式是 1（直接修复）且有修复记录，自动执行 PATCH bump。
    三端同步：SKILL.md frontmatter → _meta.json → CHANGELOG.md
    """
    print(f"\n{'='*50}")
    print(f"  阶段10/11: 自动版本号更新")
    print(f"{'='*50}")

    fix_mode = state.test_plan.get("fix_mode", 0)
    if fix_mode != 1:
        print("  仅报告/询问模式，跳过自动 bump")
        state.log_stage(5, "ok", "跳过 bump（非修复模式）")
        return state

    try:
        from bump_version import auto_bump, get_current_version, detect_bump_type
        old = get_current_version(state.skill_dir)
        if not old:
            print("  [BUMP] 无法读取版本号，跳过")
            return state

        btype = detect_bump_type(state.skill_dir)
        print(f"  当前版本: {old}, 检测变更类型: {btype}")
        new_ver = auto_bump(state.skill_dir, btype,
                           ["场景测试修复后自动版本更新"])
        if new_ver:
            print(f"  [BUMP] ✅ 版本已更新: {old} → {new_ver}")
        else:
            print(f"  [BUMP] ⚠️ 版本更新失败")
    except Exception as e:
        print(f"  [BUMP] 自动版本更新异常: {e}")

    return state


def stage_7_regression_loop(state: PipelineState, max_loops: int = 3) -> PipelineState:
    """
    阶段6: 回归循环 — 修复→重测，直到 F-0=0 且无新增
    """
    print(f"\n{'='*50}")
    print(f"  阶段7/11: 回归循环")
    print(f"{'='*50}")

    for loop in range(1, max_loops + 1):
        print(f"\n  [LOOP {loop}/{max_loops}] 重新执行测试...")

        # 重新执行场景+功能测试
        from scenario_engine import run_scenario_test
        from test_engine import run_full_test

        s_report, s_text = run_scenario_test(state.skill_dir, state.blueprint)
        f_report, f_text = run_full_test(state.skill_dir)

        s_block = s_report.get("summary", {}).get("block", 0)
        f_block = f_report.get("summary", {}).get("block", 0)
        total_block = s_block + f_block

        print(f"  [LOOP {loop}] 场景 BLOCK={s_block}, 功能 BLOCK={f_block}")

        if total_block == 0:
            print(f"  [LOOP {loop}] ✅ 全部 BLOCK 已消除，循环结束")
            break

        if loop == max_loops:
            print(f"  [LOOP {loop}] ⚠️ 已达最大循环次数 ({max_loops})，剩余 BLOCK={total_block}")
            print(f"    建议: 人工介入检查未修复的问题")

    state.regression_report = {
        "scenario": s_report.get("summary", {}),
        "function": f_report.get("summary", {}),
        "loops": loop,
        "final_block": total_block,
    }
    state.log_stage(6, "ok", f"循环{loop}次, 最终BLOCK={total_block}")
    return state


def stage_8_regression_confirm(state: PipelineState) -> PipelineState:
    """
    阶段7: 回归确认
    与修复前的基线对比，确认无功能损伤
    """
    print(f"\n{'='*50}")
    print(f"  阶段8/11: 回归确认")
    print(f"{'='*50}")

    # 获取修复前的统计（从 stage 4 的报告）
    pre_s = state.scenario_report.get("summary", {})
    pre_f = state.function_report.get("summary", {})

    # 获取修复后的统计（从 stage 6 的报告）
    post_s = state.regression_report.get("scenario", {})
    post_f = state.regression_report.get("function", {})

    # 对比
    regression = []
    for name, pre, post in [("场景通过", pre_s.get("pass",0), post_s.get("pass",0)),
                             ("功能通过", pre_f.get("pass",0), post_f.get("pass",0)),
                             ("场景BLOCK", pre_s.get("block",0), post_s.get("block",0)),
                             ("功能BLOCK", pre_f.get("block",0), post_f.get("block",0))]:
        diff = post - pre
        status = "✅ 无损伤" if diff >= 0 else "❌ 退步"
        regression.append({"item": name, "before": pre, "after": post, "diff": diff, "status": status})

    # 生成回归对比文本
    lines = ["── 回归对比表 ──"]
    lines.append(f"  {'项目':<12} {'修复前':<8} {'修复后':<8} {'变化':<8} {'状态'}")
    lines.append(f"  {'-'*48}")
    for r in regression:
        diff_str = f"+{r['diff']}" if r['diff'] > 0 else str(r['diff'])
        lines.append(f"  {r['item']:<12} {r['before']:<8} {r['after']:<8} {diff_str:<8} {r['status']}")

    has_damage = any(r["diff"] < 0 for r in regression)
    if has_damage:
        lines.append(f"\n  ⚠️ 检测到功能损伤！建议回滚备份")
    else:
        lines.append(f"\n  ✅ 无功能损伤，回归通过")

    state.regression_text = "\n".join(lines)
    print(state.regression_text)

    state.log_stage(7, "ok" if not has_damage else "blocked", state.regression_text[:200])
    return state


# ═══════════════════════════════════════════════════════
# LLM 后处理过滤
# ═══════════════════════════════════════════════════════

def stage_5_llm_filter(state: PipelineState) -> PipelineState:
    """
    阶段7.5: LLM 后处理 — 过滤误报

    在报告中为每条 F-1 WARN / F-0 BLOCK 级结果附加:
    - 问题文件:行号
    - 问题代码行（含上下文3行）
    - 检测规则名
    - 判断依据: 为什么这条被标记为问题
    - LLM 决策: 误报 / 真问题

    LLM 读取此结构化数据后，逐条判断:
      - 误报 → 标记 FP，跳过
      - 真问题 → 输出修复建议或执行修复
    """
    print(f"\n{'='*50}")
    print(f"  阶段7.5/9: LLM 后处理")
    print(f"{'='*50}")

    # 聚合所有需要 LLM 判断的问题
    all_issues = []
    for src, data in [("场景", state.scenario_report), ("功能", state.function_report)]:
        for r in data.get("results", []):
            if r.get("level") in ("block", "warn") and r.get("status") == "fail":
                issue = {
                    "source": src,
                    "dim": r.get("sid", r.get("dim", "?")),
                    "level": r.get("level"),
                    "name": r.get("name", ""),
                    "message": r.get("message", ""),
                    "file": r.get("file", ""),
                    "lineno": r.get("lineno", 0),
                    "suggestion": r.get("suggestion", ""),
                    "llm_judgment": "",  # LLM 填写: FP / 真问题
                    "llm_fix_plan": "",  # LLM 填写: 修复步骤
                }
                # 尝试读取源代码上下文
                if issue["file"] and issue["lineno"]:
                    fpath = os.path.join(state.skill_dir, issue["file"]) \
                        if not os.path.isabs(issue["file"]) else issue["file"]
                    if os.path.exists(fpath):
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                src_lines = f.read().split("\n")
                            start = max(0, issue["lineno"] - 4)
                            end = min(len(src_lines), issue["lineno"] + 3)
                            ctx = []
                            for i in range(start, end):
                                marker = "→" if i == issue["lineno"] - 1 else " "
                                ctx.append(f"{marker} {i+1:4d}| {src_lines[i]}")
                            issue["source_context"] = "\n".join(ctx)
                        except Exception:
                            issue["source_context"] = "(无法读取)"
                all_issues.append(issue)

    state.fix_results = all_issues

    if not all_issues:
        print("  无待判断问题")
        return state

    print(f"  共 {len(all_issues)} 条问题待 LLM 判断:")
    for i, issue in enumerate(all_issues, 1):
        print(f"\n  [{i}/{len(all_issues)}] {'⚠️' if issue['level']=='warn' else '🔴'} "
              f"[{issue['source']}:{issue['dim']}] {issue['name']}")
        print(f"    级别: F-{'0 BLOCK' if issue['level']=='block' else '1 WARN'}"
              f"{' 🔴' if issue['level']=='block' else ' ⚠️'}")
        print(f"    文件: {issue['file']}:{issue['lineno']}")
        print(f"    信息: {issue['message']}")
        if issue.get("source_context"):
            print(f"    代码上下文:")
            print(f"{issue['source_context']}")
        print(f"    建议: {issue['suggestion']}")
        print(f"    ── LLM 请判断: [FP] 误报 / [FIX] 真问题 ──")

    print(f"\n  共计 {len(all_issues)} 条问题，LLM 逐条判断后进入修复阶段")

    state.log_stage(7, "ok" if not has_damage else "blocked", state.regression_text[:200])
    return state


# ═══════════════════════════════════════════════════════
# 阶段9: 清理
# ═══════════════════════════════════════════════════════

def stage_11_cleanup(state: PipelineState) -> PipelineState:
    """
    阶段9: 清理测试残留文件和管理备份

    清理:
    1. 目标技能目录下的 .scenario-test_* 文件（蓝图、报告）
    2. 备份目录中超过 5 个的旧备份

    保留:
    - 最终报告 (.scenario-test_final_report.md) 默认保留
    - 最近 5 个备份
    """
    import glob as _glob
    print(f"\n{'='*50}")
    print(f"  阶段11/11: 清理")
    print(f"{'='*50}")

    # 1. 清理目标技能目录的测试残留
    patterns = [".scenario-test_blueprint.json", ".scenario-test_report.json",
                ".function-test_blueprint.json", ".function-test_report.json"]
    removed = 0
    for pattern in patterns:
        fpath = os.path.join(state.skill_dir, pattern)
        if os.path.exists(fpath):
            os.remove(fpath)
            removed += 1
            print(f"  [CLEAN] 已删除: {pattern}")

    # 2. 清理备份目录中的旧备份（保留最近 5 个）
    from backup import list_backups
    backups = list_backups(state.skill_dir)
    if len(backups) > 5:
        old = backups[5:]
        for b in old:
            import shutil as _shutil
            _shutil.rmtree(b["path"], ignore_errors=True)
            print(f"  [CLEAN] 已删除旧备份: {b['name']}")

    print(f"  [CLEAN] 清理完成: 删除 {removed} 个临时文件, "
          f"保留 {min(len(backups),5)} 个备份")

    state.log_stage(9, "ok", f"清理 {removed} 文件, 备份保留{min(len(backups),5)}个")
    return state


def stage_9_report(state: PipelineState) -> PipelineState:
    """阶段8: 输出完整报告"""
    print(f"\n{'='*50}")
    print(f"  阶段9/11: 输出报告")
    print(f"{'='*50}")

    lines = []
    lines.append("=" * 60)
    lines.append(f"  场景测试最终报告: {state.skill_name}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(state.summary())
    lines.append("")
    if state.scenario_text:
        lines.append("── 场景测试结果 ──")
        lines.append(state.scenario_text[:500])
    if state.function_text:
        lines.append("── 功能测试结果 ──")
        lines.append(state.function_text[:500])
    if state.regression_text:
        lines.append("")
        lines.append(state.regression_text)

    state.final_report = "\n".join(lines)
    print(state.final_report)

    # 保存报告
    report_path = os.path.join(state.skill_dir, ".scenario-test_final_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(state.final_report)
    print(f"\n  最终报告已保存: {report_path}")

    state.log_stage(8, "ok", f"报告已保存: {report_path}")
    return state


# ═══════════════════════════════════════════════════════
# 全流程一键执行
# ═══════════════════════════════════════════════════════

def run_full(skill_dir: str, dimensions: str = "all", fix_mode: int = 0) -> PipelineState:
    """
    全流程一键执行（11 阶段，代码硬编码，不可跳过）

    阶段顺序:
      1 备份 → 2 蓝皮书 → 3 询问 → 4 测试 →
      5 LLM后处理过滤 → 6 修复 → 7 回归循环 → 8 回归确认 →
      9 报告输出 → 10 自动bump → 11 清理

    LLM 后处理在修复之前，确保只修真问题、不修误报。
    """
    state = PipelineState(skill_dir)
    state.test_plan = {"dimensions": dimensions, "fix_mode": fix_mode}

    state = stage_1_backup(state)
    state = stage_2_blueprint(state)
    state = stage_3_ask(state)
    state = stage_4_test(state)
    state = stage_5_llm_filter(state)
    state = stage_6_fix(state, fix_mode)
    state = stage_7_regression_loop(state)
    state = stage_8_regression_confirm(state)
    state = stage_9_report(state)
    state = stage_10_bump(state)
    state = stage_11_cleanup(state)
    return state


def run_pipeline(skill_dir: str, mode: str = "full", dimensions: str = "all", fix_mode: int = 0) -> PipelineState:
    """
    分段模式执行

    参数:
        mode: "full" 全流程 / "test_only" 仅测试不修复 / "fix_only" 仅修复
    """
    state = PipelineState(skill_dir)
    state.test_plan = {"dimensions": dimensions, "fix_mode": fix_mode}

    if mode in ("full", "test_only"):
        state = stage_1_backup(state)
        state = stage_2_blueprint(state)
        state = stage_4_test(state)

    if mode == "full":
        state = stage_5_fix(state, fix_mode)
        state = stage_5b_auto_bump(state)
        state = stage_6_regression_loop(state)
        state = stage_7_regression_confirm(state)
        state = stage_7b_llm_filter(state)
        state = stage_8_report(state)
        state = stage_9_cleanup(state)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        target = sys.argv[1]
        mode = sys.argv[2] if len(sys.argv) > 2 else "full"
        dims = sys.argv[3] if len(sys.argv) > 3 else "all"
        fix = int(sys.argv[4]) if len(sys.argv) > 4 else 0

        if mode == "full":
            state = run_full(target, dims, fix)
        else:
            state = run_pipeline(target, mode, dims, fix)
    else:
        print("用法: python runner.py <skill-dir> [full|test_only|fix_only] [all|dim_list] [fix_mode]")
        print("  fix_mode: 0=仅报告  1=直接修复  2=询问后修复")
