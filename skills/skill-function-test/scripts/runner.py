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
    2: "蓝皮书扫描 + 约束提取",
    3: "询问测试计划",
    4: "场景+功能+S4脏环境测试",
    5: "LLM 后处理过滤",
    6: "修复",
    7: "回归循环",
    8: "回归确认",
    9: "报告输出 + S4 坚守率矩阵",
    10: "自动版本号更新",
    11: "清理",
}

# 数据目录常量（R-12 合规）
DATA_DIR = os.path.join(".standardization", "skill-function-test", "data")

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
        self.constraints: list[dict] = []   # S4 阶段A：约束清单
        self.test_scope: list[dict] = []    # S4 阶段A：全量测试范围
        self.test_plan: dict = {}        # {dimensions: [], fix_mode: str, s4_enabled: bool}
        self.scenario_report: dict = {}
        self.function_report: dict = {}
        self.scenario_text: str = ""
        self.function_text: str = ""
        self.s4_matrix: dict = {}        # S4 坚守率矩阵
        self.s4_matrix_text: str = ""    # S4 坚守率矩阵可读文本
        self.s4_score: dict = {}         # S4 综合忠实度评分
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
    """阶段2: 蓝皮书扫描 + S4 阶段A 约束提取"""
    from inspector import scan, print_bluebook, extract_constraints
    print(f"\n{'='*50}")
    print(f"  阶段2/8: 蓝皮书扫描 + 约束提取")
    print(f"{'='*50}")

    bb = scan(state.skill_dir)
    state.blueprint = bb.to_dict()
    state.blueprint_text = print_bluebook(bb)
    print(state.blueprint_text)

    # 保存到目标技能目录
    s4_data_dir = os.path.join(state.skill_dir, DATA_DIR)
    os.makedirs(s4_data_dir, exist_ok=True)

    bp_path = os.path.join(s4_data_dir, ".scenario-test_blueprint.json")
    with open(bp_path, "w", encoding="utf-8") as f:
        json.dump(state.blueprint, f, ensure_ascii=False, indent=2)
    print(f"\n  蓝皮书已保存: {bp_path}")

    # S4 阶段A：约束提取 + 全量测试范围生成
    print("\n  [S4 阶段A] 提取约束...")
    constraints = extract_constraints(state.skill_dir)
    state.constraints = constraints
    cpath = os.path.join(s4_data_dir, ".constraint-list.json")
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(constraints, f, ensure_ascii=False, indent=2)
    print(f"  [S4] 约束清单已保存: {cpath} ({len(constraints)} 条)")

    print("\n  [S4 阶段A] 生成全量测试范围（蓝皮书+约束+工作流+引用链路）...")
    from s4_engine import generate_test_scope, save_test_scope
    full_scope = generate_test_scope(state.skill_dir)
    save_test_scope(state.skill_dir, full_scope)
    state.test_scope = full_scope

    # 打印约束摘要
    if constraints:
        from s4_engine import print_constraint_summary
        print(print_constraint_summary(full_scope))

    state.log_stage(2, "ok",
        f"文件: {state.blueprint['file_count']} | 函数: {len(state.blueprint.get('functions',[]))} | "
        f"全量范围: {len(full_scope)} 项")
    return state


def stage_3_ask(state: PipelineState) -> PipelineState:
    """
    阶段3: 展示配置计划（LLM 交互点）
    基于 .test-config.json 展示当前配置，允许修改
    """
    print(f"\n{'='*50}")
    print(f"  阶段3/8: 展示配置计划（LLM 交互点）")
    print(f"{'='*50}")

    bp = state.blueprint
    func_count = len(bp.get("functions", []))
    class_count = len(bp.get("classes", []))
    file_count = bp.get("file_count", 0)

    # 读取配置文件
    from test_config import load_config, format_config, _fix_mode_text_scenario, _fix_mode_text_function

    cfg = load_config(state.skill_dir)

    print(f"""
╔══════════════════════════════════════════════╗
║  技能蓝皮书摘要                            ║
╠══════════════════════════════════════════════╣
║  技能: {bp.get('skill_name','?'):<35s} ║
║  版本: {bp.get('version','?'):<35s} ║
║  文件: {file_count:<4d} 个                  ║
║  函数: {func_count:<4d} 个                  ║
║  类:   {class_count:<4d} 个                  ║
║  约束: {len(state.constraints):<4d} 条 (S4)  ║
╚══════════════════════════════════════════════╝

=== 当前配置（来自 .test-config.json）===
""".strip())

    print(format_config(cfg))

    print("""
── 允许以下操作 ──
  • 直接按当前配置执行（输入 yes/y）
  • 修改配置（输入 cfg <命令>）:
       cfg show                       — 查看配置
       cfg rounds <N>                 — 设置全局轮数
       cfg fix_mode scenario <0|1>    — 场景修复模式
       cfg fix_mode function <0|1|2>  — 功能修复模式
       cfg s4 on/off                  — 开启/关闭 S4
       cfg s4 rounds <N>              — S4独立轮数
       cfg <dim> on/off               — 开关某个维度
       cfg reset                      — 重置默认
       cfg html                       — 打开 HTML 配置界面
  • 取消（输入 no/n）
""")

    # 更新 state.test_plan 中的配置字段
    from test_config import get_active_tests, get_s4_rounds
    active = get_active_tests(cfg)
    fm = cfg.get("fix_mode", {})
    state.test_plan = {
        "dimensions": active,
        "fix_mode": fm,
        "rounds": cfg.get("rounds", 3),
        "s4_enabled": cfg.get("s4", {}).get("enabled", True),
        "s4_rounds": get_s4_rounds(cfg),
    }

    state.log_stage(3, "pending", "等待 LLM 收集用户选择/修改配置")
    return state


def stage_4_test(state: PipelineState) -> PipelineState:
    """阶段4: 执行场景+功能+S4脏环境测试（按配置，多轮）"""
    from scenario_engine import run_scenario_test
    from test_engine import run_full_test as run_function_test
    from s4_engine import load_trace, generate_fidelity_matrix, print_fidelity_matrix, extract_workflow_steps, print_workflow_steps, generate_fidelity_score, print_fidelity_score
    from test_config import load_config
    print(f"\n{'='*50}")
    print(f"  阶段4/8: 执行测试（场景+功能+S4）")
    print(f"{'='*50}")

    plan = state.test_plan
    dims = plan.get("dimensions", "all")
    config = load_config(state.skill_dir)

    # 辅助：判断维度是否启用（支持 "all" 字符串 或 数组 或 逗号字符串）
    def _has_dim(name: str, alt_id: str = None) -> bool:
        if dims == "all": return True
        if isinstance(dims, str):
            return name in dims or (alt_id and alt_id in dims)
        if isinstance(dims, list):
            return name in dims or (alt_id and alt_id in dims)
        return False

    # 场景测试
    if _has_dim("S1", "1") or _has_dim("S2", "2") or _has_dim("S3", "3"):
        print("  [RUN] 场景测试 (S1-S3)...")
        s_report, s_text = run_scenario_test(state.skill_dir, state.blueprint)
        state.scenario_report = s_report
        state.scenario_text = s_text
        print(s_text)
        print()

    # 功能测试（从配置读取启用的维度）
    dim_map = {"D1": "d1_smoke", "D2": "d2_breakpoint", "D3": "d3_contamination",
               "D4": "d4_noise", "D5": "d5_correctness", "D6": "d6_robustness"}
    func_dims_to_run = []
    for name, engine_dim in dim_map.items():
        if _has_dim(name):
            func_dims_to_run.append(engine_dim)

    if func_dims_to_run:
        print(f"  [RUN] 功能测试 ({', '.join(dim_map.keys())})...")
        f_report, f_text = run_function_test(state.skill_dir, func_dims_to_run or None)
        state.function_report = f_report
        state.function_text = f_text
        print(f_text)
    else:
        print("  [SKIP] 功能测试维度未启用")

    # S4 脏环境测试（多轮）
    s4_enabled = config.get("s4", {}).get("enabled", plan.get("s4_enabled", True))
    if s4_enabled and _has_dim("S4", "10"):
        s4_rounds = config.get("s4", {}).get("rounds", plan.get("s4_rounds", config.get("rounds", 3)))
        print(f"\n  [RUN] S4 脏环境忠实度测试 ({s4_rounds} 轮)...")

        # 先用 Python 播放器生成随机化噪音脚本
        try:
            from s4_engine import NoisePlayer
            player = NoisePlayer(state.skill_dir)
            if player.plan:
                player.playback_all_rounds(rounds=s4_rounds)
        except ImportError:
            pass

        # S4 修复钩子（fix_mode=1 时自动修复引用链路断裂和缺失文件）
        s4_fix_mode = plan.get("fix_mode", {}).get("s4", 0) if isinstance(plan.get("fix_mode"), dict) else 0
        if s4_fix_mode == 1:
            print("\n  [S4-修复] 检查可修复项...")
            try:
                from s4_engine import s4_scope_repair, load_test_scope
                scope = load_test_scope(state.skill_dir)
                if scope:
                    s4_scope_repair(state.skill_dir, scope, dry_run=False)
            except ImportError:
                pass

        all_s4_rounds = []
        s4_data_dir = os.path.join(state.skill_dir, DATA_DIR)
        os.makedirs(s4_data_dir, exist_ok=True)

        for r in range(1, s4_rounds + 1):
            print(f"\n  ── S4 第 {r}/{s4_rounds} 轮 ──")
            # 读取分轮 trace（每轮由 LLM 执行时写入圆括号文件）
            round_file = os.path.join(s4_data_dir, f".s4_trace_r{r}.json")
            if os.path.exists(round_file):
                with open(round_file, "r", encoding="utf-8") as f:
                    round_trace = json.load(f)
            else:
                round_trace = load_trace(state.skill_dir)
                if round_trace and s4_rounds > 1:
                    trace_backup = os.path.join(s4_data_dir, f".s4_trace_round{r}.json")
                    with open(trace_backup, "w", encoding="utf-8") as fb:
                        json.dump(round_trace, fb, ensure_ascii=False, indent=2)

            if round_trace:
                all_s4_rounds.extend(round_trace)
                print(f"  [S4] 第 {r} 轮完成: {len(round_trace)} 条噪音")
            else:
                print(f"\n  ╔══ S4 第 {r}/{s4_rounds} 轮：LLM 必须执行 ═══╗")
                print(f"  ║                                                    ║")
                print(f"  ║  1. 读取约束清单 → 设计噪音方案：                  ║")
                print(f"  ║     python s4_engine.py <skill-dir> constraints     ║")
                print(f"  ║     → LLM 按推理模板设计 N-01~ 噪音条目            ║")
                print(f"  ║     → 保存到 .s4_noise_plan.json                   ║")
                print(f"  ║                                                    ║")
                print(f"  ║  2. 执行噪音：逐条注入干扰，记录坚守/失守          ║")
                print(f"  ║     → 保存到 .s4_trace_r{r}.json                   ║")
                print(f"  ║                                                    ║")
                print(f"  ╚════════════════════════════════════════════════════╝")

        # 聚合所有轮次（反向-脏环境）
        s4_weights = config.get("s4_weights", {"positive": 0.4, "negative": 0.6})
        negative_rate = 0.0
        if all_s4_rounds:
            s4_matrix = generate_fidelity_matrix(all_s4_rounds)
            state.s4_matrix = s4_matrix
            state.s4_matrix_text = print_fidelity_matrix(s4_matrix)
            print(state.s4_matrix_text)
            n_held = sum(1 for t in all_s4_rounds if t.get('llm_behavior')=='坚守')
            n_total = len(all_s4_rounds)
            negative_rate = n_held / n_total if n_total > 0 else 0.0
            print(f"  [S4] 反向坚守率: {n_held}/{n_total} ({negative_rate*100:.0f}%)")

            # ═══════════════════════════════════════════════
            # 正向测试：工作流步骤完成率
            # ═══════════════════════════════════════════════
            print(f"\n  [S4-正向] 提取工作流步骤...")
            steps = extract_workflow_steps(state.skill_dir)
            print(print_workflow_steps(steps))

            # 读取正向追踪记录（由LLM执行时写入 .s4_positive.json）
            positive_file = os.path.join(s4_data_dir, ".s4_positive.json")
            if os.path.exists(positive_file):
                with open(positive_file, "r", encoding="utf-8") as f:
                    positive_trace = json.load(f)
                completed = sum(1 for p in positive_trace if p.get("completed", False))
                total_steps = len(positive_trace)
                positive_rate = completed / total_steps if total_steps > 0 else 0.0
                print(f"  [S4-正向] 步骤完成率: {completed}/{total_steps} ({positive_rate*100:.0f}%)")
            else:
                print("  [S4-正向] 无正向追踪记录")
                print("  ╔═══════ 正向测试：LLM 必须执行 ══════╗")
                print("  ║                                     ║")
                print("  ║  1. 按以上工作流步骤顺序执行一次     ║")
                print("  ║  2. 每步完成后记录到                 ║")
                print("  ║     .s4_positive.json               ║")
                print('  ║     格式: [{"step":1,"title":"备份",  ║')
                print('  ║            "completed":true}]        ║')
                print("  ║                                     ║")
                print("  ╚═════════════════════════════════════╝")
                # 有步骤但无追踪 → exit(1) 强制LLM执行
                import sys as _sys
                _sys.exit(1)

            # ═══════════════════════════════════════════════
            # 综合忠实度评分
            # ═══════════════════════════════════════════════
            score_result = generate_fidelity_score(
                positive_rate, negative_rate,
                s4_weights.get("positive", 0.4),
                s4_weights.get("negative", 0.6),
            )
            state.s4_score = score_result
            print()
            print(print_fidelity_score(score_result))
        else:
            # ═══════════════════════════════════════════════
            # [强制] S4 已启用但无执行记录 → exit(1) 截断
            # ═══════════════════════════════════════════════
            print(f"\n{'='*55}")
            print(f"  ⛔ S4 脏环境测试已开启，但无噪音执行记录")
            print(f"  🚫 LLM 必须完成以上步骤后再继续")
            print(f"  🚫 执行完毕后重新运行全流程")
            print(f"{'='*55}")
            import sys as _sys
            _sys.exit(1)

    # 更新 state 记录
    state.log_stage(4, "ok",
        f"{'场景已跑' if state.scenario_report else '场景跳过'} | "
        f"{'功能已跑' if state.function_report else '功能跳过'} | "
        f"{'S4矩阵' if state.s4_matrix else 'S4跳过'}")
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

    state.log_stage(5, "ok", f"待判断问题: {len(all_issues)} 条")
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

    # 1. 清理目标技能目录的测试残留（data 目录中）
    s4_data_dir = os.path.join(state.skill_dir, DATA_DIR)
    patterns = [".scenario-test_blueprint.json", ".scenario-test_report.json",
                ".function-test_blueprint.json", ".function-test_report.json"]
    removed = 0
    for pattern in patterns:
        for base in [state.skill_dir, s4_data_dir]:
            fpath = os.path.join(base, pattern)
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
    """阶段8: 输出完整报告（含 S4 坚守率矩阵）"""
    print(f"\n{'='*50}")
    print(f"  阶段9/11: 输出报告 + S4 坚守率矩阵")
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
    if state.s4_matrix_text:
        lines.append("")
        lines.append("── S4 脏环境忠实度 ──")
        lines.append(state.s4_matrix_text)
    if state.s4_score:
        lines.append("")
        from s4_engine import print_fidelity_score
        lines.append(print_fidelity_score(state.s4_score))
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

def run_full(skill_dir: str, dimensions: list = None, fix_mode: dict = None) -> PipelineState:
    """
    全流程一键执行（11 阶段，基于 .test-config.json 配置）

    阶段顺序:
      1 备份 → 2 蓝皮书+约束 → 3 询问 → 4 测试(按配置+多轮) →
      5 LLM后处理过滤 → 6 修复 → 7 回归循环 → 8 回归确认 →
      9 报告输出+S4矩阵 → 10 自动bump → 11 清理

    参数:
      skill_dir: 目标技能目录
      dimensions: 覆盖配置的维度（None=使用配置）
      fix_mode: 覆盖配置的修复模式 dict，如 {"scenario":0, "function":1}

    配置文件 .test-config.json 控制所有行为。
    """
    from test_config import load_config, get_active_tests, format_config

    state = PipelineState(skill_dir)

    # 从配置文件加载测试计划
    cfg = load_config(skill_dir)
    active_dims = get_active_tests(cfg)

    state.test_plan = {
        "dimensions": dimensions or active_dims,
        "fix_mode": fix_mode if fix_mode is not None else cfg.get("fix_mode", {"scenario": 0, "function": 0}),
        "rounds": cfg.get("rounds", 3),
        "s4_enabled": cfg.get("s4", {}).get("enabled", True),
        "s4_rounds": cfg.get("s4", {}).get("rounds", cfg.get("rounds", 3)),
    }

    print(f"\n{'='*50}")
    print(f"  全流程启动 — 基于 .test-config.json")
    print(f"{'='*50}")
    print(f"  维度: {', '.join(active_dims)}")
    fm = state.test_plan['fix_mode']
    print(f"  场景修复: {['仅报告','尝试修复'][fm.get('scenario',0)]}")
    print(f"  功能修复: {['仅报告','直接修复','询问后修复'][fm.get('function',0)]}")
    s4_r = state.test_plan['s4_rounds']
    print(f"  S4: {'开启' if cfg['s4']['enabled'] else '关闭'} ({s4_r}轮, 仅报告)")
    print(f"  配置命令: cfg show/reset/rounds/fix_mode/s4/<dim>")
    print()

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
        state = stage_9_report(state)
        state = stage_11_cleanup(state)


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
