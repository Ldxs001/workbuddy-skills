"""
hooks.py — skill-function-test 流程钩子系统

双档策略：
  - Python-only 步骤（init/backup/blueprint）: 缺了自动补齐，LLM 不需要管
  - LLM 需参与的步骤（scenario/function_test/s4）: 缺了阻断，告诉 LLM 具体做啥
  - gen_report 兜底: 能自动补的自动补，不能补的阻断并指引 LLM

钩子依赖链:
  init → backup → blueprint ─┬→ scenario_test ─┐
                              ├→ function_test ─┤
                              └→ s4 ────────────┘→ gen_report → 双格式报告

LLM 跳不过任何一步。跳了就被阻断指引回来。
"""
import json
import os
import subprocess
import sys

# R-12 审计锚点 — 数据目录字面量
# 规范：skills/.standardization/skill-function-test/data/
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-function-test/data/"

# ── 目录定位 ──
import pathlib
_SCRIPT_DIR = str(pathlib.Path(__file__).resolve().parent)
_SKILL_DIR = str(pathlib.Path(_SCRIPT_DIR).parent)
_SKILLS_ROOT = str(pathlib.Path(_SKILL_DIR).parent)
DATA_DIR = str(pathlib.Path(_SKILLS_ROOT) / ".standardization" / "skill-function-test" / "data")


def _data_dir(skill_dir: str) -> str:
    target = os.path.basename(os.path.abspath(skill_dir))
    d = os.path.join(DATA_DIR, target, "outputs")
    os.makedirs(d, exist_ok=True)
    return d


def _skill_name(skill_dir: str) -> str:
    return os.path.basename(os.path.abspath(skill_dir))


# ── 阻断 / 通过 / 自动 ──

def _block(msg: str, action: str = "", exit_code: int = 1):
    print(f"\n{'='*55}")
    print(f"  [HOOK] ⛔ 流程阻断")
    print(f"  {msg}")
    if action:
        print(f"")
        print(f"  >> 请执行: {action}")
    print(f"{'='*55}")
    sys.exit(exit_code)


def _pass(msg: str):
    print(f"  [HOOK] [OK] {msg}")


def _run_py_step(cmd_args: list[str], label: str) -> bool:
    """自动执行一个纯 Python 步骤（不依赖 LLM 判断）"""
    print(f"  [HOOK] auto: {label}...")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(cmd_args, capture_output=True, text=True, env=env)
    out = r.stdout or ""
    err = r.stderr or ""
    if out.strip():
        for line in out.strip().split("\n"):
            print(f"    {line}")
    if r.returncode != 0:
        if err.strip():
            print(f"    stderr: {err.strip()[-200:]}")
        print(f"  [HOOK] FAIL: {label} (exit={r.returncode})")
        return False
    print(f"  [HOOK] done: {label}")
    return True


# ═══════════════════════════════════════════════════════
# 制品路径
# ═══════════════════════════════════════════════════════

def _timeline_path(skill_dir: str) -> str:
    return os.path.join(DATA_DIR, os.path.basename(os.path.abspath(skill_dir)), ".timeline.json")

def _bp_json_path(skill_dir: str) -> str:
    """蓝皮书 JSON（inspector 输出名带 function 前缀）"""
    return os.path.join(_data_dir(skill_dir), ".function-test_blueprint.json")

def _bp_legacy_path(skill_dir: str) -> str:
    return os.path.join(_data_dir(skill_dir), ".function-test_blueprint.json")

def _scenario_report_path(skill_dir: str) -> str:
    return os.path.join(_data_dir(skill_dir), ".scenario-test_report.json")

def _func_report_path(skill_dir: str) -> str:
    return os.path.join(_data_dir(skill_dir), ".function-test_report.json")

def _backup_for(skill_dir: str) -> list[str]:
    bdir = os.path.join(DATA_DIR, "backup")
    if not os.path.isdir(bdir):
        return []
    name = _skill_name(skill_dir)
    return sorted([f for f in os.listdir(bdir)
                   if f.startswith(name) and f.endswith(".zip")], reverse=True)


# ═══════════════════════════════════════════════════════
# 前置钩子（入口检查 + 自动补齐 / 阻断指引）
# ═══════════════════════════════════════════════════════

def hook_pre_init(skill_dir: str):
    """init: 无前置"""
    _pass("init — 无前置依赖")


def hook_pre_backup(skill_dir: str):
    """备份前：timeline 已初始化 ← 缺了自动 init"""
    tl = _timeline_path(skill_dir)
    if not os.path.exists(tl):
        tl_script = os.path.join(_SCRIPT_DIR, "timeline.py")
        if not _run_py_step([sys.executable, tl_script, "init", skill_dir], "自动初始化时间线"):
            _block("时间线初始化失败", f"python {tl_script} init {skill_dir}")
    _pass("备份 — 时间线已就绪")


def hook_pre_blueprint(skill_dir: str):
    """蓝皮书扫描前：备份已完成 ← 缺了自动备份"""
    # 先确保 timeline 就绪
    hook_pre_backup(skill_dir)

    backups = _backup_for(skill_dir)
    if not backups:
        backup_script = os.path.join(_SCRIPT_DIR, "backup.py")
        if not _run_py_step(
            [sys.executable, backup_script, "backup", skill_dir, "auto_pre_blueprint"],
            f"自动备份 {_skill_name(skill_dir)}",
        ):
            _block("备份失败", f"python {backup_script} backup {skill_dir}")
    _pass("蓝皮书 — 备份已就绪")


def hook_pre_scenario(skill_dir: str):
    """场景测试前：蓝皮书已完成 ← 缺了自动扫描"""
    hook_pre_blueprint(skill_dir)  # 确保备份就绪

    bp_json = _bp_json_path(skill_dir)
    bp_legacy = _bp_legacy_path(skill_dir)
    if not os.path.exists(bp_json) and not os.path.exists(bp_legacy):
        insp_script = os.path.join(_SCRIPT_DIR, "inspector.py")
        if not _run_py_step(
            [sys.executable, insp_script, skill_dir],
            f"自动蓝皮书扫描 {_skill_name(skill_dir)}",
        ):
            _block("蓝皮书扫描失败", f"python {insp_script} {skill_dir}")

    # 从配置读取启用的场景维度
    config_path = os.path.join(_data_dir(skill_dir), ".test-config.json")
    enabled_scenarios = {"S1": True, "S2": True, "S3": True}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k in ["S1", "S2", "S3"]:
            enabled_scenarios[k] = cfg.get("scenarios", {}).get(k, {}).get("enabled", True)
    except Exception:
        pass
    active = [k for k, v in enabled_scenarios.items() if v]
    _pass(f"场景测试 — 启用维度: {', '.join(active) if active else '无'}")


def hook_pre_function_test(skill_dir: str):
    """功能测试前：蓝皮书已完成 ← 缺了自动扫描"""
    hook_pre_blueprint(skill_dir)

    bp_json = _bp_json_path(skill_dir)
    bp_legacy = _bp_legacy_path(skill_dir)
    if not os.path.exists(bp_json) and not os.path.exists(bp_legacy):
        insp_script = os.path.join(_SCRIPT_DIR, "inspector.py")
        if not _run_py_step(
            [sys.executable, insp_script, skill_dir],
            f"自动蓝皮书扫描 {_skill_name(skill_dir)}",
        ):
            _block("蓝皮书扫描失败", f"python {insp_script} {skill_dir}")

    # 从配置读取启用的功能维度
    config_path = os.path.join(_data_dir(skill_dir), ".test-config.json")
    enabled_funcs = {"D1": True, "D2": True, "D3": True, "D4": True, "D5": True, "D6": True}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k in enabled_funcs:
            enabled_funcs[k] = cfg.get("functions", {}).get(k, {}).get("enabled", True)
    except Exception:
        pass
    active = [k for k, v in enabled_funcs.items() if v]
    _pass(f"功能测试 — 启用维度: {', '.join(active) if active else '无'}")


def hook_pre_s4(skill_dir: str):
    """S4 测试前：检查配置中 S4 是否开启"""
    # 检查配置中 S4 是否启用
    config_path = os.path.join(_data_dir(skill_dir), ".test-config.json")
    s4_enabled = True  # 默认开启
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        s4_enabled = cfg.get("s4", {}).get("enabled", True)
    except Exception:
        pass

    if not s4_enabled:
        print(f"  [HOOK] S4 已关闭 (s4.enabled=false)，跳过")
        _mark_done(skill_dir, "s4")
        return
    has_scenario = os.path.exists(_scenario_report_path(skill_dir))
    has_func = os.path.exists(_func_report_path(skill_dir))

    if not has_scenario and not has_func:
        _block(
            "S4 需要前置测试数据",
            "请先执行场景测试 (scenario_engine.py) 或功能测试 (test_engine.py)\n"
            f"  python {os.path.join(_SCRIPT_DIR, 'scenario_engine.py')} {skill_dir}\n"
            f"  python {os.path.join(_SCRIPT_DIR, 'test_engine.py')} {skill_dir}",
        )
    _pass("S4 — 前置测试数据已就绪")

    # ── 校验: LLM 是否已完成 S4 噪音方案 ──
    noise_plan = os.path.join(_data_dir(skill_dir), ".s4_noise_plan.json")
    if not os.path.exists(noise_plan):
        _block(
            "S4 前置: 噪音方案未编写",
            "请先阅读约束清单 (.constraint-list.json)，基于蓝皮书编写噪音方案:\n"
            f"  1. 阅读 constraints 理解铁律\n"
            f"  2. 构造噪音方案写入 .s4_noise_plan.json\n"
            f"  3. 运行校验: python {os.path.join(_SCRIPT_DIR, 's4_engine.py')} {skill_dir} validate <json_path>",
        )
    try:
        with open(noise_plan, "r", encoding="utf-8") as f:
            plan = json.load(f)
        if isinstance(plan, list) and len(plan) < 3:
            _block("S4 前置: 噪音方案条目太少 (<3 条)", "请补全噪音方案")
        _pass(f"S4 — 噪音方案已就绪 ({len(plan) if isinstance(plan, list) else '?'} 条)")
    except Exception:
        _block("S4 前置: 噪音方案 JSON 解析失败", "请修复 .s4_noise_plan.json 格式")


def hook_pre_fix(skill_dir: str):
    """自动修复前：检查 fix_mode 配置"""
    config_path = os.path.join(_data_dir(skill_dir), ".test-config.json")
    need_fix = False
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        fm = cfg.get("fix_mode", {})
        need_fix = fm.get("scenario", 0) == 1 or fm.get("function", 0) == 1
    except Exception:
        pass
    if not need_fix:
        print(f"  [HOOK] fix_mode 未启用，跳过修复步骤")
        _mark_done(skill_dir, "fix")
        _mark_done(skill_dir, "regress")
        _mark_done(skill_dir, "final_regress")
        return
    _pass("自动修复 — 开始基于测试结果修复")
    _mark_done(skill_dir, "fix")


def hook_post_fix(skill_dir: str):
    """修复完成 → 指引回归确认"""
    print(f"  [HOOK] >> 修复完成。请执行回归确认。")


def hook_pre_regress(skill_dir: str):
    """回归确认前：修复已完成"""
    state_path = _flow_state_path(skill_dir)
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)
    if not state.get("steps", {}).get("fix", {}).get("done"):
        _block("回归确认前置: 修复尚未完成", "请先执行修复步骤")
    _pass("回归确认 — 修复已完成")
    _mark_done(skill_dir, "regress")


def hook_pre_final_regress(skill_dir: str):
    """最终回归确认前：回归已完成"""
    state_path = _flow_state_path(skill_dir)
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)
    if not state.get("steps", {}).get("regress", {}).get("done"):
        _block("最终回归前置: 回归尚未完成", "请先执行回归确认")
    _pass("最终回归确认 — 回归已完成")
    _mark_done(skill_dir, "final_regress")


def hook_pre_gen_report(skill_dir: str):
    """报告生成：兜底——能自动补的自动补，不能补的阻断指引"""

    # 1. 时间线
    tl = _timeline_path(skill_dir)
    if not os.path.exists(tl):
        if not _run_py_step(
            [sys.executable, os.path.join(_SCRIPT_DIR, "timeline.py"), "init", skill_dir],
            "自动初始化时间线",
        ):
            _block("时间线初始化失败")

    # 2. 备份 + 蓝皮书（自动补）
    hook_pre_blueprint(skill_dir)

    # 3. 检查测试报告
    has_scenario = os.path.exists(_scenario_report_path(skill_dir))
    has_func = os.path.exists(_func_report_path(skill_dir))

    if not has_scenario and not has_func:
        _block(
            "无任何测试数据",
            "请先执行至少一种测试:\n"
            f"  场景测试: python {os.path.join(_SCRIPT_DIR, 'scenario_engine.py')} {skill_dir}\n"
            f"  功能测试: python {os.path.join(_SCRIPT_DIR, 'test_engine.py')} {skill_dir}",
        )

    # 4. 时间线中有 marker？
    try:
        with open(tl, "r", encoding="utf-8") as f:
            tl_data = json.load(f)
        if not tl_data.get("markers"):
            print(f"  [HOOK] \u26a0 时间线文件存在但无 marker，报告计时部分可能为空")
    except Exception:
        pass

    # 5. 修复记录检查（如果测试发现问题但无修复记录 → 提醒）
    fix_record_path = os.path.join(_data_dir(skill_dir), ".fix-record.json")
    if os.path.exists(fix_record_path):
        try:
            with open(fix_record_path, "r", encoding="utf-8") as f:
                fix_records = json.load(f)
            if isinstance(fix_records, list) and fix_records:
                _pass(f"修复记录已就绪 ({len(fix_records)} 条)")
        except Exception:
            pass

    _pass("所有前置就绪 → 开始生成报告")


# ═══════════════════════════════════════════════════════
# 后置钩子（完成标记 + LLM 指引）
# ═══════════════════════════════════════════════════════

def hook_post_scenario(skill_dir: str):
    """场景测试完成 → 指引 LLM 下一步"""
    _mark_done(skill_dir, "scenario")
    print()
    print(f"  [HOOK] >> 场景测试完成。请审查结果。")
    print(f"  [HOOK] >> 审查后可按需进行: ")
    print(f"  [HOOK] >>   - 功能测试: python {os.path.join(_SCRIPT_DIR, 'test_engine.py')} {skill_dir}")
    print(f"  [HOOK] >>   - S4 测试:  python {os.path.join(_SCRIPT_DIR, 's4_engine.py')} {skill_dir} scope")
    print(f"  [HOOK] >>   - 生成报告: python {os.path.join(_SCRIPT_DIR, 'gen_report.py')} {skill_dir}")


def hook_post_function_test(skill_dir: str):
    """功能测试完成 → 如果 S4 已关闭，自动生成报告"""
    _mark_done(skill_dir, "function_test")
    # 检查 S4 是否已关闭，关闭则直接自动出报告
    config_path = os.path.join(_data_dir(skill_dir), ".test-config.json")
    s4_enabled = True
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        s4_enabled = cfg.get("s4", {}).get("enabled", True)
    except Exception:
        pass
    if not s4_enabled:
        print(f"  [HOOK] >> S4 已关闭，自动生成报告...")
        _run_py_step(
            [sys.executable, os.path.join(_SCRIPT_DIR, "gen_report.py"), skill_dir],
            "自动生成报告",
        )


def hook_post_s4(skill_dir: str):
    _mark_done(skill_dir, "s4")
    print(f"  [HOOK] >> S4 完成，自动生成报告...")
    _run_py_step(
        [sys.executable, os.path.join(_SCRIPT_DIR, "gen_report.py"), skill_dir],
        "自动生成报告",
    )


def hook_post_gen_report(skill_dir: str):
    """报告生成完成 → 清理目标技能根目录的测试残留 + 指引"""
    _mark_done(skill_dir, "report")
    _clean_skill_root(skill_dir, strict=True)
    print(f"  [HOOK] >> 报告已生成。需继续执行步骤9：测试结论写入目标技能。")
    print(f"  请执行: python {os.path.join(_SCRIPT_DIR, 'gen_report.py')} {skill_dir} --write-conclusion")


def hook_pre_write_conclusion(skill_dir: str):
    """结论写入前：报告已生成"""
    state_path = _flow_state_path(skill_dir)
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)
    if not state.get("steps", {}).get("report", {}).get("done"):
        _block("结论写入前置: 报告尚未生成", "请先生成报告: python gen_report.py <skill-dir>")
    _pass("结论写入 — 报告已就绪")


def hook_post_write_conclusion(skill_dir: str):
    """结论写入完成 → 全部流程完毕（终端状态）"""
    _mark_done(skill_dir, "write_conclusion")
    print(f"  [HOOK] >> 测试结论已写入目标技能。全部流程完成。")


def hook_pre_write_tests(skill_dir: str):
    """写测试前置：蓝皮书就绪 + LLM 必须手工编写场景测试用例"""
    hook_pre_blueprint(skill_dir)

    # 检查是否已存在手工编写的测试用例
    test_plan_path = os.path.join(_data_dir(skill_dir), ".s_test_plan.json")
    if os.path.exists(test_plan_path):
        try:
            with open(test_plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
            s_count = len(plan.get("S1", [])) + len(plan.get("S2", [])) + len(plan.get("S3", []))
            if s_count >= 3:
                _pass(f"场景测试用例已就绪 ({s_count} 条)")
                return
        except Exception:
            pass

    _block(
        "写测试前置: 场景测试用例未编写",
        "请基于目标技能的 SKILL.md 和蓝皮书，手工编写场景测试用例:\n"
        f"  1. 阅读目标技能的 SKILL.md，理解其业务场景和能力范围\n"
        f"  2. 阅读蓝皮书的 file_manifest.python 列表，了解全部模块名\n"
        f"  3. 为 S1（触发场景）写真实用户触发词 + 预期行为\n"
        f"  4. 为 S2（核心能力）写输入 + 预期输出\n"
        f"  5. 为 S3（工作流）写多步骤链路 + 预期连贯结果\n"
        f"  6. 每条用例建议填写 modules 字段，指定涉及的 Python 模块名（不含 .py 后缀）\n"
        f"  7. 写入 {test_plan_path}\n"
        f"  格式见 skill-function-test 的 references/s-test-plan-schema.md",
    )


def hook_post_write_tests(skill_dir: str):
    _mark_done(skill_dir, "write_tests")



# R-11 强制清理：gen_report 完成后自动清除目标技能根目录的测试产出物

_KNOWN_TEST_ARTIFACTS = {
    ".function-test_blueprint.json", ".scenario-test_report.json",
    ".test-config.json", ".test-report.html", ".test-report.md",
    ".timeline.json", ".constraint-list.json",
    ".s4_trace.json", ".s4_noise_plan.json",
    ".fix-record.json", ".flow-state.json",
}


def _clean_skill_root(skill_dir: str, strict: bool = False):
    """扫描目标技能根目录，删除已知测试残留文件"""
    removed = []
    for fname in _KNOWN_TEST_ARTIFACTS:
        fpath = os.path.join(skill_dir, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            removed.append(fname)
            print(f"  [HOOK] 🧹 清理残留: {fname}")
    if strict:
        print(f"  [HOOK] ✅ 根目录{'干净，无测试残留' if not removed else f'已清理 {len(removed)} 个文件'}")


# ── 通用标记 ──

_STATE_CACHE = {}

def _flow_state_path(skill_dir: str) -> str:
    target = os.path.basename(os.path.abspath(skill_dir))
    d = os.path.join(DATA_DIR, target)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, ".flow-state.json")


def _mark_done(skill_dir: str, step: str):
    path = _flow_state_path(skill_dir)
    state = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
    if "steps" not in state:
        state["steps"] = {}
    state["steps"][step] = {
        "done": True,
        "at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)  # [HOOK] {step} done


def hook_post_init(skill_dir: str): _mark_done(skill_dir, "init")
def hook_post_backup(skill_dir: str): _mark_done(skill_dir, "backup")
def hook_post_blueprint(skill_dir: str): _mark_done(skill_dir, "blueprint")


# ═══════════════════════════════════════════════════════
# 状态查看
# ═══════════════════════════════════════════════════════

def cmd_status(skill_dir: str):
    state_path = _flow_state_path(skill_dir)
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)
    steps = state.get("steps", {})

    # 从 outputs 目录读取配置（不依赖 skill_dir 根目录，因会被清理）
    config_path = os.path.join(_data_dir(skill_dir), ".test-config.json")
    need_fix = False
    s4_enabled = True
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        fm = cfg.get("fix_mode", {})
        need_fix = fm.get("scenario", 0) == 1 or fm.get("function", 0) == 1
        s4_enabled = cfg.get("s4", {}).get("enabled", True)
    except Exception:
        pass

    flow = [
        ("init",             "初始化时间线"),
        ("backup",           "备份目标技能"),
        ("blueprint",        "蓝皮书扫描"),
        ("write_tests",      "编写场景测试用例"),  # ← LLM 手工编写场景测试
        ("scenario",         "场景测试 (S1-S3)"),
        ("function_test",    "功能测试 (D1-D6)"),
    ]
    if s4_enabled:
        flow.append(("s4", "S4 执行忠实度"))
    if need_fix:
        flow += [
            ("fix",            "自动修复"),
            ("regress",        "回归确认"),
            ("final_regress",  "最终回归确认"),
        ]
    flow += [
        ("report",           "输出报告"),
        ("write_conclusion", "结论写入目标技能"),  # ← 新增：第9步，终端状态
    ]

    print("\n  ── 流程状态 ──")
    all_done = True
    for key, label in flow:
        s = steps.get(key, {})
        done = s.get("done", False) if isinstance(s, dict) else False
        icon = "DONE" if done else "PEND"
        if not done:
            all_done = False
        print(f"  [{icon}] {label}")

    print(f"\n  exit: {'0 (全部完成)' if all_done else '>0 (未完成)'}")


# ═══════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("用法: python hooks.py check|done|status <skill-dir> [step]")
        return

    cmd = sys.argv[1]
    skill_dir = sys.argv[2]

    if cmd == "status":
        cmd_status(skill_dir)
        return

    if len(sys.argv) < 4:
        print("请指定步骤: init | backup | blueprint | write_tests | scenario | function_test | s4 | fix | regress | final_regress | gen_report | write_conclusion")
        return

    step = sys.argv[3]

    if cmd == "check":
        pre_map = {
            "init": hook_pre_init,
            "backup": hook_pre_backup,
            "blueprint": hook_pre_blueprint,
            "write_tests": hook_pre_write_tests,
            "scenario": hook_pre_scenario,
            "function_test": hook_pre_function_test,
            "s4": hook_pre_s4,
            "fix": hook_pre_fix,
            "regress": hook_pre_regress,
            "final_regress": hook_pre_final_regress,
            "gen_report": hook_pre_gen_report,
            "write_conclusion": hook_pre_write_conclusion,
        }
        fn = pre_map.get(step)
        if fn:
            fn(skill_dir)
        else:
            print(f"未知步骤: {step}")
            sys.exit(1)

    elif cmd == "done":
        post_map = {
            "init": hook_post_init,
            "backup": hook_post_backup,
            "blueprint": hook_post_blueprint,
            "write_tests": hook_post_write_tests,
            "scenario": hook_post_scenario,
            "function_test": hook_post_function_test,
            "s4": hook_post_s4,
            "fix": hook_post_fix,
            "gen_report": hook_post_gen_report,
            "write_conclusion": hook_post_write_conclusion,
        }
        fn = post_map.get(step)
        if fn:
            fn(skill_dir)
        else:
            print(f"未知步骤: {step}")
            sys.exit(1)

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
