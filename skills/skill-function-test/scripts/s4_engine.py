"""
s4_engine.py — S4 脏环境忠实度测试引擎

S4 四阶段：
  阶段A: 约束提取（在 inspector.py 中完成，产出 .constraint-list.json）
  阶段B: LLM推理层（读取约束清单 → LLM 推理 → 产出噪音方案 .s4_noise_plan.json）
  阶段C: 噪音执行（读取噪音方案 → 逐条注入干扰 → 产出执行记录 .s4_trace.json）
  阶段D: 复盘归因（读取执行记录 → 复盘分析 → 产出坚守率矩阵）

S4 只报告、不修复。坚守率矩阵嵌入阶段8的最终报告中。
"""
import json
import os
import sys

# S4 数据目录常量（R-12 合规命名）
DATA_DIR = os.path.join(".standardization", "skill-function-test", "data")

CONSTRAINT_FILE = os.path.join(DATA_DIR, ".constraint-list.json")
NOISE_PLAN_FILE = os.path.join(DATA_DIR, ".s4_noise_plan.json")
S4_TRACE_FILE = os.path.join(DATA_DIR, ".s4_trace.json")


# ═══════════════════════════════════════════════════════
# 阶段B：噪音方案 schema 校验
# ═══════════════════════════════════════════════════════

NOISE_PLAN_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["nid", "cid", "level", "phase", "trigger_point",
                      "noise_text", "expected_behavior", "description"],
        "properties": {
            "nid": {"type": "string", "pattern": r"^N-\d{2}$"},
            "cid": {"type": "string", "pattern": r"^C-\d{2}$"},
            "level": {"type": "string", "enum": ["L1", "L2", "L3", "L4", "L5"]},
            "phase": {"type": "string"},
            "trigger_point": {"type": "string"},
            "noise_text": {"type": "string", "minLength": 1},
            "expected_behavior": {"type": "string", "enum": ["坚守", "失守"]},
            "description": {"type": "string"},
        },
    },
}


def validate_noise_plan(plan: list) -> list[str]:
    """
    校验噪音方案是否符合 schema。

    返回：错误信息列表，空列表表示校验通过。
    """
    errors = []

    if not isinstance(plan, list):
        return ["噪音方案必须为 JSON 数组"]

    for i, item in enumerate(plan):
        idx = f"[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{idx} 条目必须为 object")
            continue

        # 检查必填字段
        for field in ["nid", "cid", "level", "phase", "trigger_point",
                       "noise_text", "expected_behavior", "description"]:
            if field not in item:
                errors.append(f"{idx} 缺少必填字段: {field}")

        # 检查 nid 格式
        nid = item.get("nid", "")
        if not (nid.startswith("N-") and len(nid) == 4 and nid[2:].isdigit()):
            errors.append(f"{idx} nid 格式错误: {nid}（必须为 N-XX）")

        # 检查 cid 格式
        cid = item.get("cid", "")
        if not (cid.startswith("C-") and len(cid) == 4 and cid[2:].isdigit()):
            errors.append(f"{idx} cid 格式错误: {cid}（必须为 C-XX）")

        # 检查级别
        level = item.get("level", "")
        if level not in ("L1", "L2", "L3", "L4", "L5"):
            errors.append(f"{idx} level 无效: {level}（必须为 L1-L5）")

        # 检查预期行为
        exp = item.get("expected_behavior", "")
        if exp not in ("坚守", "失守"):
            errors.append(f"{idx} expected_behavior 无效: {exp}（必须为 坚守/失守）")

        # 检查模糊字段
        noise_text = item.get("noise_text", "")
        for vague in ("视情况", "适当", "可能", "大概", "酌情"):
            if vague in noise_text:
                errors.append(f"{idx} noise_text 含模糊表述: '{vague}'")
                break

    return errors


def load_constraints(skill_dir: str) -> list[dict]:
    """加载阶段A产出的约束清单"""
    cpath = os.path.join(skill_dir, CONSTRAINT_FILE)
    if not os.path.exists(cpath):
        print(f"[S4] ⚠️ 约束清单不存在: {cpath}")
        return []
    with open(cpath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_noise_plan(skill_dir: str, plan: list[dict]):
    """保存噪音方案到目标技能目录"""
    npath = os.path.join(skill_dir, NOISE_PLAN_FILE)
    with open(npath, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"[S4] ✅ 噪音方案已保存: {npath} ({len(plan)} 条)")


def load_noise_plan(skill_dir: str) -> list[dict]:
    """加载噪音方案"""
    npath = os.path.join(skill_dir, NOISE_PLAN_FILE)
    if not os.path.exists(npath):
        print(f"[S4] ⚠️ 噪音方案不存在: {npath}")
        return []
    with open(npath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_trace(skill_dir: str, trace: list[dict]):
    """保存S4执行记录"""
    tpath = os.path.join(skill_dir, S4_TRACE_FILE)
    with open(tpath, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)
    print(f"[S4] ✅ 执行记录已保存: {tpath}")


def load_trace(skill_dir: str) -> list[dict]:
    """加载S4执行记录"""
    tpath = os.path.join(skill_dir, S4_TRACE_FILE)
    if not os.path.exists(tpath):
        return []
    with open(tpath, "r", encoding="utf-8") as f:
        return json.load(f)


def print_constraint_summary(constraints: list[dict]) -> str:
    """打印约束清单摘要（供阶段B使用）"""
    if not constraints:
        return "[S4] 无约束可供提取"

    lines = [f"┌─────────────────────────────────────────────────────────────┐",
             f"│  S4 阶段A 约束摘要: {len(constraints)} 条                          │",
             f"├──────┬──────────┬──────┬────────┬──────────────────────────┤",
             f"│ CID  │ 强度     │ 脚本  │ 行号   │ 约束原文                 │",
             f"├──────┼──────────┼──────┼────────┼──────────────────────────┤"]

    for c in constraints:
        cid = c.get("cid", "?")
        strength = c.get("strength", "?")
        script = "✅" if c.get("has_script") else "  "
        lineno = c.get("lineno", 0)
        text = c.get("text", "")[:40]
        lines.append(f"│ {cid:<4} │ {strength:<7} │ {script:<4} │ L{lineno:<4} │ {text:<40} │")

    lines.append(f"└──────┴──────────┴──────┴────────┴──────────────────────────┘")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 阶段C：噪音执行（调用入口）
# ═══════════════════════════════════════════════════════

# 阶段C由 LLM（测试编排器）逐条执行，s4_engine 只提供
# 数据结构和校验逻辑。执行入口在 s4 子命令中提供。

TRACE_TEMPLATE = {
    "nid": "",
    "cid": "",
    "level": "",
    "noise_text": "",
    "executed": True,
    "llm_behavior": "",  # 坚守 / 失守
    "detail": "",
    "timestamp": "",
}


# ═══════════════════════════════════════════════════════
# 阶段D：生成坚守率矩阵
# ═══════════════════════════════════════════════════════

def generate_fidelity_matrix(trace_records: list[dict]) -> dict:
    """
    从 S4 执行记录生成坚守率统计。

    输出:
        matrix: {
            "summary": {"total": N, "坚守": M, "失守": K, "坚守率": "XX%"},
            "details": [
                {
                    "nid": "N-01", "cid": "C-07",
                    "level": "L4", "behavior": "坚守",
                    "detail": "..."
                },
                ...
            ],
            "failures": ["C-12 (应执行回归确认) — 坚守率 33%"],
        }
    """
    if not trace_records:
        return {"summary": {"total": 0, "坚守": 0, "失守": 0, "坚守率": "0%"}, "details": [], "failures": []}

    total = len(trace_records)
    held = sum(1 for t in trace_records if t.get("llm_behavior") == "坚守")
    failed = total - held
    rate = f"{held}/{total} ({held/total*100:.0f}%)"

    # 按 cid 分组统计
    cid_groups = {}
    for t in trace_records:
        cid = t.get("cid", "?")
        if cid not in cid_groups:
            cid_groups[cid] = {"total": 0, "held": 0, "texts": []}
        cid_groups[cid]["total"] += 1
        if t.get("llm_behavior") == "坚守":
            cid_groups[cid]["held"] += 1

    # 标记纸老虎（坚守率 < 100% 的约束）
    failures = []
    for cid, g in sorted(cid_groups.items()):
        if g["held"] < g["total"]:
            r = f"{g['held']}/{g['total']} ({g['held']/g['total']*100:.0f}%)"
            failures.append(f"{cid} — 坚守率 {r} ❌")

    return {
        "summary": {"total": total, "坚守": held, "失守": failed, "坚守率": rate},
        "details": trace_records,
        "failures": failures,
    }


def print_fidelity_matrix(matrix: dict) -> str:
    """打印坚守率矩阵（人类可读格式）"""
    if matrix["summary"]["total"] == 0:
        return "[S4] 无 S4 测试记录"

    s = matrix["summary"]
    lines = [
        "=" * 62,
        "  S4 脏环境忠实度测试 — 坚守率矩阵",
        "=" * 62,
        f"  总计: {s['total']}  | 坚守: {s['坚守']}  | 失守: {s['失守']}  | 坚守率: {s['坚守率']}",
        "",
        "── 详细记录:",
    ]

    for t in matrix["details"]:
        icon = "✅" if t.get("llm_behavior") == "坚守" else "❌"
        nid = t.get("nid", "?")
        level = t.get("level", "?")
        noise = t.get("noise_text", "")[:50]
        behavior = t.get("llm_behavior", "?")
        lines.append(f"  {icon} [{nid}] {level} {noise} → {behavior}")
        if t.get("detail"):
            lines.append(f"     详情: {t['detail'][:80]}")

    lines.append("")
    if matrix["failures"]:
        lines.append("── 铁律溃败点（纸老虎）:")
        for f in matrix["failures"]:
            lines.append(f"  ❌ {f}")
    else:
        lines.append("  ✅ 全部坚守，无纸老虎")

    lines.append("=" * 62)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 阶段E：正向工作流步骤提取
# ═══════════════════════════════════════════════════════

def extract_workflow_steps(skill_dir: str) -> list[dict]:
    """
    从目标技能的 SKILL.md 工作流程章节解析步骤序列。

    返回:
        list[dict]: 步骤列表，每个元素 {order, title, description}
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return []

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    import re

    steps = []
    in_workflow = False
    order = 0

    for line in lines:
        stripped = line.strip()
        if not in_workflow:
            if stripped.startswith("## ") and ("工作流程" in stripped or "流程" in stripped or "workflow" in stripped.lower()):
                in_workflow = True
            continue

        if stripped.startswith("## ") and "流程" not in stripped and "工作" not in stripped:
            break

        # 匹配 "N. **标题** — 描述"
        m = re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*\s*[—\-–]\s*(.*)', stripped)
        if m:
            steps.append({"order": int(m.group(1)), "title": m.group(2).strip(), "description": m.group(3).strip()[:120]})
            continue

        # 匹配 "- **标题** — 描述"（无序号）
        m2 = re.match(r'^[\*\-\+]\s+\*\*(.+?)\*\*\s*[—\-–]\s*(.*)', stripped)
        if m2:
            order += 1
            steps.append({"order": order, "title": m2.group(1).strip(), "description": m2.group(2).strip()[:120]})

    return steps


def print_workflow_steps(steps: list[dict]) -> str:
    if not steps:
        return "[S4] 未提取到工作流步骤"
    lines = [f"  ┌── 工作流程: {len(steps)} 步 ──┐"]
    for s in steps:
        lines.append(f"  │ {s['order']}. {s['title'][:20]:<20s} {s['description'][:40]}")
    lines.append(f"  └{'─'*38}┘")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 阶段F：综合忠实度评分（正反因子）
# ═══════════════════════════════════════════════════════

def generate_fidelity_score(
    positive_rate: float, negative_rate: float,
    positive_factor: float = 0.4, negative_factor: float = 0.6,
) -> dict:
    """
    S4 忠实度 = pf × pr + nf × nr

    等级:
      >=0.9 S  |  >=0.8 A  |  >=0.6 B  |  >=0.4 C  |  <0.4 D
    """
    score = positive_factor * positive_rate + negative_factor * negative_rate
    level = "S (优秀)" if score >= 0.9 else "A (良好)" if score >= 0.8 else "B (合格)" if score >= 0.6 else "C (较差)" if score >= 0.4 else "D (不合格)"
    return {"positive_rate": round(positive_rate, 2), "negative_rate": round(negative_rate, 2), "positive_factor": positive_factor, "negative_factor": negative_factor, "score": round(score, 2), "level": level}


def print_fidelity_score(result: dict) -> str:
    return "\n".join([
        "=" * 50,
        "  S4 综合忠实度评分",
        "=" * 50,
        f"  正向完成率: {result['positive_rate']*100:.0f}% × 权重 {result['positive_factor']}",
        f"  反向坚守率: {result['negative_rate']*100:.0f}% × 权重 {result['negative_factor']}",
        f"  ─────────────────────────────",
        f"  综合分数: {result['score']*100:.0f}%  → {result['level']}",
        "=" * 50,
    ])


# ═══════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════

USAGE = """
用法:
  python s4_engine.py <skill-dir> constraints     — 打印约束清单
  python s4_engine.py <skill-dir> validate <json> — 校验噪音方案 schema
  python s4_engine.py <skill-dir> report          — 从 trace 生成坚守率报告
  python s4_engine.py <skill-dir> steps           — 打印工作流步骤序列
  python s4_engine.py <skill-dir> score <pr> <nr> — 综合评分 (pf=0.4 nf=0.6)
"""


def main():
    if len(sys.argv) < 3:
        print(USAGE)
        return

    skill_dir = sys.argv[1]
    cmd = sys.argv[2]

    if cmd == "constraints":
        constraints = load_constraints(skill_dir)
        print(print_constraint_summary(constraints))

    elif cmd == "validate":
        if len(sys.argv) < 4:
            print("缺少方案 JSON 路径")
            return
        plan_path = sys.argv[3]
        if os.path.exists(plan_path):
            with open(plan_path, "r", encoding="utf-8") as f:
                plan = json.load(f)
        else:
            try:
                plan = json.loads(plan_path)
            except json.JSONDecodeError:
                print(f"无法解析 JSON: {plan_path}")
                return
        errors = validate_noise_plan(plan)
        if errors:
            print(f"[S4] ❌ 噪音方案校验失败 ({len(errors)} 个错误):")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"[S4] ✅ 噪音方案校验通过 ({len(plan)} 条)")

    elif cmd == "report":
        trace = load_trace(skill_dir)
        matrix = generate_fidelity_matrix(trace)
        print(print_fidelity_matrix(matrix))

    elif cmd == "steps":
        steps = extract_workflow_steps(skill_dir)
        print(print_workflow_steps(steps))

    elif cmd == "score":
        if len(sys.argv) < 4:
            print("用法: score <positive_rate> <negative_rate> [pf=0.4 nf=0.6]")
            return
        pr = float(sys.argv[2])
        nr = float(sys.argv[3])
        pf = float(sys.argv[4]) if len(sys.argv) >= 5 else 0.4
        nf = float(sys.argv[5]) if len(sys.argv) >= 6 else 0.6
        result = generate_fidelity_score(pr, nr, pf, nf)
        print(print_fidelity_score(result))

    else:
        print(f"未知命令: {cmd}")
        print(USAGE)


if __name__ == "__main__":
    main()
