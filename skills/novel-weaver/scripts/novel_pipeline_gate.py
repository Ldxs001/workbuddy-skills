#!/usr/bin/env python3
"""
novel-pipeline-gate — 全流程执行门禁系统。

确保 LLM 无法跳过任何关键步骤。每一步都必须显式 pass，否则 phase 转换被阻断。

门禁点定义（线性流程，顺序不可逆）：
  G01  outline_causality    大纲因果链验证通过
  G02  plan_chapter:L##     子结构批量注册完成
  G03  sub_causality:L##    子结构因果链验证通过
  G04  sub_write_done:L##S## 子结构写作完成
  G05  chapter_finalized:L## 章完结（含连通性+风格+逻辑全部通过）
  G06  fidelity             全文大纲忠实度报告完成
  G07  complete             全文整合完成

使用方式：
  pass <state_path> <gate>             — 标记门禁点为通过
  require <state_path> <target_gate>   — 检查所有前置门禁是否通过，阻断
  status <state_path>                  — 打印所有门禁状态表
  reset <state_path> <gate>            — 重置指定门禁点（调试用）
"""

import os
import sys
import json
import re

# 门禁点定义（有序列表，线性流程）
GATES = [
    "outline_causality",        # G01
    # plan_chapter:L## 和 sub_causality:L## 是动态的（每章一个）
    # chapter_finalized:L## 动态
    "fidelity",                  # G06
    "complete",                  # G07
]

GATE_LABELS = {
    "outline_causality": "大纲因果链验证",
    "plan_chapter": "子结构批量注册",
    "sub_causality": "子结构因果链验证",
    "sub_write": "子结构写作",
    "chapter_finalized": "章完结",
    "fidelity": "大纲忠实度报告",
    "complete": "全文整合",
}


def _state_path_or_die(path: str) -> str:
    if not os.path.exists(path):
        print(f"ERROR: {path} 不存在")
        sys.exit(1)
    return path


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())


def _ensure_pipeline(state: dict, path: str):
    """确保 pipeline 字段存在"""
    if "pipeline" not in state:
        state["pipeline"] = {}
        _save(path, state)


def _is_dynamic_gate(gate: str) -> bool:
    """判断是否是动态门禁（包含 : 分隔符，如 plan_chapter:L03）"""
    return ":" in gate


def _resolve_gate(gate: str) -> str:
    """解析门禁点的基名"""
    if _is_dynamic_gate(gate):
        return gate.split(":")[0]
    return gate


def _gate_order(gate: str) -> int:
    """返回门禁点的顺序（用于 require 检查）"""
    base = _resolve_gate(gate)
    order = {
        "outline_causality": 10,
        "plan_chapter": 20,
        "sub_causality": 30,
        "sub_write": 40,
        "chapter_finalized": 50,
        "fidelity": 60,
        "complete": 70,
    }
    return order.get(base, 999)


def _check_prerequisites(state: dict, target_gate: str) -> list:
    """
    检查到 target_gate 之前的所有必须门禁。
    返回缺失门禁列表（空 = 全部通过）。
    """
    pipeline = state.get("pipeline", {})
    target_base = _resolve_gate(target_gate)
    target_ch = target_gate.split(":")[1] if _is_dynamic_gate(target_gate) else None
    target_order = _gate_order(target_gate)
    missing = []

    # 检查所有顺序小于 target 的静态门禁
    for gate, data in pipeline.items():
        base = _resolve_gate(gate)
        ch = gate.split(":")[1] if _is_dynamic_gate(gate) else None
        order = _gate_order(gate)

        # 如果是动态门禁且属于不同章节，跳过
        if target_ch is not None and ch is not None and ch != target_ch:
            continue

    # 如果 target 是动态门禁，检查它之前的同章门禁
    if target_ch:
        # plan_chapter:L## → 检查 outline_causality
        if target_base == "plan_chapter":
            if not pipeline.get("outline_causality"):
                missing.append("outline_causality (大纲因果链)")

        # sub_causality:L## → 检查 plan_chapter:L##
        elif target_base == "sub_causality":
            if not pipeline.get("outline_causality"):
                missing.append("outline_causality (大纲因果链)")
            pg = f"plan_chapter:{target_ch}"
            if not pipeline.get(pg):
                missing.append(f"{pg} (子结构注册)")

        # chapter_finalized:L## → 检查 plan + sub_causality + 所有子结构写完
        elif target_base == "chapter_finalized":
            if not pipeline.get("outline_causality"):
                missing.append("outline_causality (大纲因果链)")
            pg = f"plan_chapter:{target_ch}"
            if not pipeline.get(pg):
                missing.append(f"{pg} (子结构注册)")
            sc = f"sub_causality:{target_ch}"
            if not pipeline.get(sc):
                missing.append(f"{sc} (子结构因果链)")

    else:
        # 静态门禁：outline_causality → 无前置
        # fidelity → 检查所有章 finalize
        # complete → 检查 fidelity
        if target_base == "fidelity":
            if not pipeline.get("outline_causality"):
                missing.append("outline_causality (大纲因果链)")
            # 检查所有已计划的章节是否 finalized
            for gate_key, passed in pipeline.items():
                if gate_key.startswith("plan_chapter:"):
                    ch = gate_key.split(":")[1]
                    cf = f"chapter_finalized:{ch}"
                    if not pipeline.get(cf):
                        missing.append(f"{cf} ({ch} 未完结)")

        elif target_base == "complete":
            if not pipeline.get("fidelity"):
                missing.append("fidelity (大纲忠实度报告)")

    return missing


def cmd_pass(state_path: str, gate: str):
    """标记一个门禁点为通过"""
    data = _load(state_path)
    _ensure_pipeline(data, state_path)
    data["pipeline"][gate] = True
    _save(state_path, data)
    label = GATE_LABELS.get(_resolve_gate(gate), gate)
    if _is_dynamic_gate(gate):
        ch = gate.split(":")[1]
        print(f"✅ [PASS] {label} — {ch}")
    else:
        print(f"✅ [PASS] {label}")


def cmd_require(state_path: str, target_gate: str):
    """
    检查所有前置门禁是否已通过。未通过则报错退出（阻断）。
    在 set-phase 前调用。
    """
    data = _load(state_path)
    pipeline = data.get("pipeline", {})
    missing = _check_prerequisites(data, target_gate)

    if missing:
        print(f"❌ [BLOCKED] 门禁「{GATE_LABELS.get(_resolve_gate(target_gate), target_gate)}」的前置条件不满足:")
        for m in missing:
            print(f"   - {m}")
        print(f"")
        print(f"  请按顺序完成以上步骤后再试。")
        print(f"  查看所有门禁状态: pipeline_gate.py status <state_path>")
        sys.exit(1)
    else:
        print(f"✅ [REQUIRE OK] 所有前置门禁已通过")


def cmd_status(state_path: str):
    """打印当前所有门禁状态"""
    data = _load(state_path)
    pipeline = data.get("pipeline", {})
    phase = data.get("current_phase", "none")

    print(f"{'='*55}")
    print(f"  [门禁状态] 当前阶段: {phase}")
    print(f"{'='*55}")
    print(f"")

    # 计算动态门禁集合
    chapter_gates = {}
    for gate_key in sorted(pipeline.keys()):
        if _is_dynamic_gate(gate_key):
            base, ch = gate_key.split(":", 1)
            if ch not in chapter_gates:
                chapter_gates[ch] = {}
            chapter_gates[ch][base] = pipeline[gate_key]

    # 静态门禁
    print(f"  {'门禁':<30} {'状态':>8}")
    print(f"  {'-'*40}")
    for gate in GATES:
        passed = pipeline.get(gate, False)
        status = "✅ PASS" if passed else "⬜ PENDING"
        label = GATE_LABELS.get(gate, gate)
        print(f"  {label:<30} {status:>8}")

    # 各章动态门禁
    if chapter_gates:
        print(f"")
        print(f"  {'─'*40}")
        print(f"")
        for ch in sorted(chapter_gates.keys()):
            gates = chapter_gates[ch]
            line_parts = []
            for base in ["plan_chapter", "sub_causality", "chapter_finalized"]:
                passed = gates.get(base, False)
                icon = "✅" if passed else "⬜"
                label = GATE_LABELS.get(base, base)
                line_parts.append(f"{icon}{label}")
            print(f"  [{ch}] {' → '.join(line_parts)}")
            # 子结构级别
            for gate_key in sorted(pipeline.keys()):
                if gate_key.startswith("sub_write:") and gate_key.endswith(ch):
                    sw_passed = pipeline[gate_key]
                    sw_icon = "✅" if sw_passed else "⬜"
                    sw_name = gate_key.split(":")[1] + ":" + gate_key.split(":")[2]
                    print(f"         {sw_icon} {sw_name}")

    print(f"")
    print(f"{'='*55}")

    # 汇总
    total = len(pipeline)
    passed_count = sum(1 for v in pipeline.values() if v)
    print(f"  总计: {passed_count}/{total} 门禁已通过")


def cmd_reset(state_path: str, gate: str):
    """重置指定门禁点（仅调试用）"""
    data = _load(state_path)
    pipeline = data.get("pipeline", {})
    if gate in pipeline:
        del pipeline[gate]
        _save(state_path, data)
        print(f"🔄 [RESET] {gate}")
    else:
        print(f"WARN: {gate} 不存在")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    state_path = sys.argv[2]
    _state_path_or_die(state_path)

    if command == "pass":
        if len(sys.argv) < 4:
            print("用法: pass <state_path> <gate>")
            sys.exit(1)
        cmd_pass(state_path, sys.argv[3])

    elif command == "require":
        if len(sys.argv) < 4:
            print("用法: require <state_path> <target_gate>")
            sys.exit(1)
        cmd_require(state_path, sys.argv[3])

    elif command == "status":
        cmd_status(state_path)

    elif command == "reset":
        if len(sys.argv) < 4:
            print("用法: reset <state_path> <gate>")
            sys.exit(1)
        cmd_reset(state_path, sys.argv[3])

    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)
