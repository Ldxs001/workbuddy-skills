"""
gen_report.py — 测试报告生成器（HTML + Markdown 双输出）
"""
import glob
import json
import math
import os
import subprocess
import sys

# R-12 审计锚点
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-function-test/data/"

# 流程钩子
_HOOKS_SCRIPT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "hooks.py"
))
def _hook_check(skill_dir, step):
    r = subprocess.run([sys.executable, _HOOKS_SCRIPT, "check", skill_dir, step],
                        capture_output=True, text=True)
    if r.stdout.strip(): print(r.stdout)
    if r.returncode != 0: sys.exit(r.returncode)
def _hook_done(skill_dir, step):
    subprocess.run([sys.executable, _HOOKS_SCRIPT, "done", skill_dir, step],
                    capture_output=True)


def _data_dir_for(skill_dir: str) -> str:
    skill_name = os.path.basename(os.path.abspath(skill_dir))
    _SKILL_DIR = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."
    ))
    _SKILLS_ROOT = os.path.normpath(os.path.join(_SKILL_DIR, ".."))
    d = os.path.normpath(os.path.join(
        _SKILLS_ROOT, ".standardization", "skill-function-test", "data", skill_name
    ))
    os.makedirs(d, exist_ok=True)
    return d


def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_rounds(skill_dir: str) -> list[dict]:
    datadir = _data_dir_for(skill_dir)
    rounds = []
    tl = _load_json(os.path.join(datadir, ".timeline.json"))
    if tl:
        rounds.append(tl)
    for f in sorted(glob.glob(os.path.join(datadir, ".timeline_*.json"))):
        data = _load_json(f)
        if data:
            rounds.append(data)
    return rounds


def load_all(skill_dir: str) -> dict:
    datadir = _data_dir_for(skill_dir)
    skill_name = os.path.basename(os.path.abspath(skill_dir))
    scenario_report = _load_json(os.path.join(datadir, ".scenario-test_report.json"))
    if not scenario_report:
        scenario_report = _load_json(os.path.join(skill_dir, ".scenario-test_report.json"))
    function_report = _load_json(os.path.join(datadir, ".function-test_report.json"))
    s4_trace = _load_json(os.path.join(datadir, ".s4_trace.json"))
    s4_noise_plan = _load_json(os.path.join(datadir, ".s4_noise_plan.json"))
    fix_record = _load_json(os.path.join(datadir, ".fix-record.json"))
    if isinstance(fix_record, dict):
        fix_record = fix_record.get("fixes", [])
    if not isinstance(fix_record, list):
        fix_record = []
    rounds = _load_rounds(skill_dir)
    timeline = rounds[-1] if rounds else {}
    test_reports = {}
    for f in os.listdir(datadir):
        if f.endswith("_report.json") and not f.startswith("."):
            test_reports[f] = _load_json(os.path.join(datadir, f))
    return {
        "skill_dir": skill_dir,
        "skill_name": skill_name,
        "timeline": timeline,
        "rounds": rounds,
        "scenario": scenario_report,
        "function": function_report,
        "s4_trace": s4_trace,
        "s4_plan": s4_noise_plan,
        "fix_record": fix_record,
        "test_reports": test_reports,
    }


def compute_timing(data: dict) -> dict:
    """计算计时统计（栈式配对，修复相位名重复问题）"""
    timeline = data.get("timeline", {})
    markers = timeline.get("markers", [])
    if not markers:
        return {"total": 0, "py_script": 0, "llm": 0, "target_skill": 0, "steps": [], "by_phase": {}}
    started_at = timeline.get("started_at", 0)
    sorted_markers = sorted(markers, key=lambda m: m["t"])
    total = round(max(m["t"] for m in sorted_markers) - started_at, 3)
    stack = []
    py_script_total = 0.0
    target_skill_total = 0.0
    step_list = []
    for m in sorted_markers:
        if m["mark"] == "start":
            stack.append(m)
        elif m["mark"] == "end":
            for i in range(len(stack) - 1, -1, -1):
                sm = stack[i]
                if sm["type"] == m["type"] and sm["phase"] == m["phase"]:
                    stack.pop(i)
                    dur = round(m["t"] - sm["t"], 3)
                    step_list.append({
                        "phase": m["phase"],
                        "label": sm.get("label", "")[:40],
                        "type": m["type"],
                        "duration": dur,
                    })
                    # py_script: 只计根级（栈中无其他 py_script）
                    if m["type"] == "py_script":
                        has_parent_py = any(s["type"] == "py_script" for s in stack)
                        if not has_parent_py:
                            py_script_total += dur
                    elif m["type"] == "subprocess_wall":
                        target_skill_total += dur
                    break
    llm_time = max(0, round(total - py_script_total, 3))
    by_phase = {}
    for s in step_list:
        ph = s["phase"]
        tp = s["type"]
        if ph not in by_phase:
            by_phase[ph] = {}
        if tp not in by_phase[ph]:
            by_phase[ph][tp] = {"count": 0, "total": 0.0}
        by_phase[ph][tp]["count"] += 1
        by_phase[ph][tp]["total"] += s["duration"]
    return {
        "total": total,
        "py_script": round(py_script_total, 3),
        "llm": llm_time,
        "target_skill": round(target_skill_total, 3),
        "steps": step_list,
        "by_phase": by_phase,
    }


def compute_round_stats(rounds: list[dict]) -> dict:
    if len(rounds) < 2:
        return {"rounds": len(rounds), "has_stats": False, "has_control_chart": False}
    totals = []
    targets = []
    for r in rounds:
        markers = r.get("markers", [])
        if not markers:
            continue
        started_at = r.get("started_at", 0)
        total_end = max(m["t"] for m in markers)
        totals.append(total_end - started_at)
        tgt = 0.0
        ws = {}
        for m in markers:
            if m["type"] == "subprocess_wall":
                if m["mark"] == "start":
                    ws[m["id"]] = m["t"]
                elif m["mark"] == "end":
                    pid = m.get("parent_id")
                    if pid and pid in ws:
                        tgt += m["t"] - ws.pop(pid)
        targets.append(tgt)
    if not totals:
        return {"rounds": 0, "has_stats": False, "has_control_chart": False}
    n = len(totals)
    mean_total = sum(totals) / n
    mean_target = sum(targets) / n
    std_total = math.sqrt(sum((x - mean_total) ** 2 for x in totals) / max(n - 1, 1))
    std_target = math.sqrt(sum((x - mean_target) ** 2 for x in targets) / max(n - 1, 1))
    return {
        "rounds": n, "has_stats": n >= 2, "has_control_chart": n >= 9,
        "mean_total": round(mean_total, 3), "std_total": round(std_total, 3),
        "mean_target": round(mean_target, 3), "std_target": round(std_target, 3),
        "totals": [round(t, 3) for t in totals],
        "targets": [round(t, 3) for t in targets],
    }


def extract_issues(data: dict) -> list[dict]:
    issues = []
    for r in data.get("scenario", {}).get("results", []):
        if r.get("status") in ("fail", "error"):
            issues.append({
                "source": f"S{r.get('sid', '?')}", "name": r.get("name", ""),
                "level": r.get("level", "info"), "message": r.get("message", ""),
                "file": r.get("file", ""), "line": r.get("lineno", 0),
                "suggestion": r.get("suggestion", ""), "detail": r.get("detail", ""),
            })
    for r in data.get("function", {}).get("results", []):
        if r.get("status") in ("fail", "error"):
            issues.append({
                "source": r.get("dim", "?"), "name": r.get("name", ""),
                "level": r.get("level", "info"), "message": r.get("message", ""),
                "file": r.get("file", ""), "line": r.get("lineno", 0),
                "suggestion": r.get("suggestion", ""), "detail": r.get("detail", ""),
            })
    return issues


def gen_markdown(data: dict) -> str:
    timing = compute_timing(data)
    stats = compute_round_stats(data.get("rounds", []))
    issues = extract_issues(data)

    lines = []
    lines.append(f"# 测试报告: {data['skill_name']}")
    lines.append("")
    lines.append(f"> 生成时间: {data['timeline'].get('started_at_iso', 'N/A')}")
    lines.append("")

    lines.append("## 1. 测试步骤")
    lines.append("")
    lines.append("| 测试 | 维度 | 状态 |")
    lines.append("|------|------|------|")

    scenario = data.get("scenario", {})
    s_summary = scenario.get("summary", {})
    if s_summary:
        for r in scenario.get("results", []):
            status = "PASS" if r.get("status") == "pass" else "FAIL"
            lines.append(f"| {r.get('sid', 'S?')} | {r.get('name', '')[:40]} | {status} |")
    if not s_summary:
        lines.append("| - | 无场景测试数据 | - |")

    func = data.get("function", {})
    f_summary = func.get("summary", {})
    if f_summary:
        for r in func.get("results", []):
            status = "PASS" if r.get("status") == "pass" else "FAIL"
            lines.append(f"| {r.get('dim', 'D?')} | {r.get('name', '')[:40]} | {status} |")
    if not f_summary:
        lines.append("| - | 无功能测试数据 | - |")

    lines.append("")
    lines.append(f"场景测试: {s_summary.get('pass', 0)}/{s_summary.get('total', 0)} 通过 (BLOCK={s_summary.get('block', 0)})")
    lines.append(f"功能测试: {f_summary.get('pass', 0)}/{f_summary.get('total', 0)} 通过 (BLOCK={f_summary.get('block', 0)})")
    lines.append("")

    lines.append("## 2. 问题列表")
    lines.append("")
    if not issues:
        lines.append("> 无发现问题")
    else:
        level_order = {"block": 0, "warn": 1, "info": 2}
        issues_sorted = sorted(issues, key=lambda x: level_order.get(x["level"], 9))
        for i, iss in enumerate(issues_sorted, 1):
            lines.append(f"### {i}. `{iss['level'].upper()}` {iss['name']}")
            lines.append("")
            lines.append(f"- **来源**: {iss['source']}")
            lines.append(f"- **消息**: {iss['message']}")
            if iss["file"]:
                lines.append(f"- **文件**: {iss['file']}:{iss['line']}")
            if iss["detail"]:
                lines.append(f"- **解析**: {iss['detail']}")
            if iss["suggestion"]:
                lines.append(f"- **建议**: {iss['suggestion']}")
            lines.append("")

    lines.append("## 3. 计时统计")
    lines.append("")
    lines.append(f"| 指标 | 耗时 (s) |")
    lines.append(f"|------|---------|")
    lines.append(f"| 总耗时 | {timing['total']} |")
    lines.append(f"| 脚本执行 | {timing['py_script']} |")
    lines.append(f"| LLM 处理 | {timing['llm']} |")
    lines.append(f"| 目标技能调用 | {timing['target_skill']} |")

    by_phase = timing.get("by_phase", {})
    if by_phase:
        lines.append("")
        lines.append("### 单步耗时细目")
        lines.append("")
        lines.append("| 步骤 | 类型 | 调用次数 | 总耗时 (s) |")
        lines.append("|------|------|---------|-----------|")
        for phase in sorted(by_phase.keys()):
            for tp in sorted(by_phase[phase].keys()):
                s = by_phase[phase][tp]
                lines.append(f"| {phase} | {tp} | {s['count']} | {s['total']:.3f} |")

    if stats.get("has_stats"):
        lines.append("")
        lines.append("| 统计 | 均值 (s) | 标准差 (s) |")
        lines.append("|------|---------|-----------|")
        lines.append(f"| 总耗时 | {stats['mean_total']} | {stats['std_total']} |")
        lines.append(f"| 目标技能 | {stats['mean_target']} | {stats['std_target']} |")
        lines.append(f"  > 基于 {stats['rounds']} 轮数据")

    lines.append("")
    lines.append("## 4. 修复记录")
    lines.append("")
    fixes = data.get("fix_record", [])
    if not fixes:
        lines.append("> 无修复记录")
    else:
        lines.append("| # | 类型 | 文件 | 详情 | 状态 |")
        lines.append("|---|------|------|------|------|")
        for i, fx in enumerate(fixes, 1):
            ftype = fx.get("fix_type", "?")
            fpath = fx.get("filepath", "")[-40:]
            detail = fx.get("detail", "")[:30]
            status = "OK" if fx.get("success") else "FAIL"
            lines.append(f"| {i} | {ftype} | `{fpath}` | {detail} | {status} |")

    lines.append("")
    return "\n".join(lines)


def _render_issue_rows(issues: list[dict]) -> str:
    rows = []
    level_order = {"block": 0, "warn": 1, "info": 2}
    sorted_issues = sorted(issues, key=lambda x: level_order.get(x["level"], 9))
    for iss in sorted_issues:
        level = iss["level"]
        cls = {"block": "danger", "warn": "warning", "info": "info"}.get(level, "info")
        rows.append(f'''
    <tr class="row-{cls}">
      <td><span class="badge badge-{cls}">{level.upper()}</span></td>
      <td>{iss["source"]}</td>
      <td>{iss["name"][:50]}</td>
      <td>{iss["message"][:100]}</td>
      <td>{iss.get("file", "")}:{iss.get("line", 0)}</td>
      <td>{iss.get("suggestion", "")[:80]}</td>
    </tr>''')
    return "\n".join(rows)


def _render_control_chart(stats: dict) -> str:
    if not stats.get("has_control_chart"):
        return ""
    totals = stats["totals"]
    mean = stats["mean_total"]
    std = stats["std_total"]
    import json as _json
    return f'''
    <div class="chart-container">
      <canvas id="controlChart"></canvas>
    </div>
    <script>
    const ctx = document.getElementById('controlChart').getContext('2d');
    new Chart(ctx, {{
      type: 'scatter',
      data: {{
        datasets: [{{
          label: '\u5404\u8f6e\u603b\u8017\u65f6',
          data: {_json.dumps([{"x": i, "y": v} for i, v in enumerate(totals, 1)])},
          backgroundColor: '#534AB7', pointRadius: 6,
        }},{{
          label: '\u76ee\u6807\u6280\u80fd\u8017\u65f6',
          data: {_json.dumps([{"x": i, "y": v} for i, v in enumerate(stats["targets"], 1)])},
          backgroundColor: '#D85A30', pointRadius: 6,
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{
          title: {{ display: true, text: '\u591a\u8f6e\u8017\u65f6\u63a7\u5236\u56fe (n={len(totals)})', font: {{ size: 14 }} }},
          annotation: {{
            annotations: {{
              meanLine: {{
                type: 'line', yMin: {mean}, yMax: {mean},
                borderColor: '#534AB7', borderWidth: 2, borderDash: [6,3],
                label: {{ display: true, content: '\u5747\u503c: {mean:.2f}s', position: 'end' }}
              }},
              ucl: {{
                type: 'line', yMin: {mean + 3*std}, yMax: {mean + 3*std},
                borderColor: '#E24B4A', borderWidth: 1, borderDash: [4,4],
                label: {{ display: true, content: 'UCL: {mean+3*std:.2f}s', position: 'end' }}
              }},
              lcl: {{
                type: 'line', yMin: {mean - 3*std}, yMax: {mean - 3*std},
                borderColor: '#E24B4A', borderWidth: 1, borderDash: [4,4],
                label: {{ display: true, content: 'LCL: {mean-3*std:.2f}s', position: 'end' }}
              }},
            }}
          }}
        }},
        scales: {{
          x: {{ title: {{ display: true, text: '\u6d4b\u8bd5\u8f6e\u6b21' }} }},
          y: {{ title: {{ display: true, text: '\u8017\u65f6 (s)' }} }},
        }}
      }}
    }});
    </script>'''


def gen_html(data: dict) -> str:
    timing = compute_timing(data)
    stats = compute_round_stats(data.get("rounds", []))
    issues = extract_issues(data)

    f0_count = sum(1 for i in issues if i["level"] == "block")
    f1_count = sum(1 for i in issues if i["level"] == "warn")
    f2_count = sum(1 for i in issues if i["level"] == "info")

    s_summary = data.get("scenario", {}).get("summary", {})
    f_summary = data.get("function", {}).get("summary", {})
    s_pass = s_summary.get("pass", "N/A") if s_summary else "N/A"
    s_total = s_summary.get("total", "N/A") if s_summary else "N/A"
    f_pass = f_summary.get("pass", "N/A") if f_summary else "N/A"
    f_total = f_summary.get("total", "N/A") if f_summary else "N/A"

    issue_rows = _render_issue_rows(issues)
    control_chart = _render_control_chart(stats)

    # 多轮统计行
    stats_row = ""
    if stats.get("has_stats"):
        stats_row = f'''
      <p class="stats-info">基于 {stats['rounds']} 轮 — 均值 {stats['mean_total']}s / 标准差 {stats['std_total']}s</p>
      <table class="stats-table">
        <tr><th></th><th>均值 (s)</th><th>标准差 (s)</th></tr>
        <tr><td>总耗时</td><td>{stats['mean_total']}</td><td>{stats['std_total']}</td></tr>
        <tr><td>目标技能</td><td>{stats['mean_target']}</td><td>{stats['std_target']}</td></tr>
      </table>'''

    # 单步耗时行
    by_phase = timing.get("by_phase", {})
    steps_html = ""
    if by_phase:
        step_rows = ""
        for phase in sorted(by_phase.keys()):
            for tp in sorted(by_phase[phase].keys()):
                s = by_phase[phase][tp]
                step_rows += f'<tr><td>{phase}</td><td>{tp}</td><td>{s["count"]}</td><td>{s["total"]:.3f}</td></tr>\n    '
        steps_html = f'''
  <h3 style="margin-top:14px;font-size:14px;font-weight:600;color:#534AB7;">单步耗时细目</h3>
  <table class="timing-table">
    <tr><th>步骤</th><th>类型</th><th>调用次数</th><th>总耗时 (s)</th></tr>
    {step_rows}
  </table>'''

    # 测试详情行
    scenario_rows = ""
    for r in data.get("scenario", {}).get("results", []):
        st = "PASS" if r.get("status") == "pass" else "FAIL"
        scenario_rows += f"<tr><td>S{r.get('sid','')}</td><td>{r.get('name','')[:40]}</td><td>{st}</td><td>{r.get('message','')}</td></tr>\n    "
    function_rows = ""
    for r in data.get("function", {}).get("results", []):
        st = "PASS" if r.get("status") == "pass" else "FAIL"
        function_rows += f"<tr><td>{r.get('dim','')}</td><td>{r.get('name','')[:40]}</td><td>{st}</td><td>{r.get('message','')}</td></tr>\n    "

    # 修复记录行
    fix_record = data.get("fix_record", [])
    if fix_record:
        fix_rows = ""
        for i, fx in enumerate(fix_record, 1):
            fpath = os.path.basename(fx.get("filepath", ""))
            fdetail = fx.get("detail", "")[:40]
            ftype = fx.get("fix_type", "")
            fst = "OK" if fx.get("success") else "FAIL"
            fix_rows += f"<tr><td>{i}</td><td>{ftype}</td><td>{fpath}</td><td>{fdetail}</td><td>{fst}</td></tr>\n    "
        fix_section = f'''
  <table>
    <tr><th>#</th><th>类型</th><th>文件</th><th>详情</th><th>状态</th></tr>
    {fix_rows}
  </table>'''
    else:
        fix_section = '<p style="color: var(--text-muted);">无修复记录</p>'

    issue_section = '<p style="color: var(--success);">无发现问题</p>' if not issues else f'''
  <table>
    <tr><th>级别</th><th>来源</th><th>名称</th><th>消息</th><th>位置</th><th>建议</th></tr>
    {issue_rows}
  </table>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>测试报告: {data['skill_name']}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3"></script>
<style>
:root {{
  --primary: #534AB7; --success: #3B6D11; --danger: #A32D2D;
  --warning: #854F0B; --info: #185FA5; --bg: #f8f9fa;
  --card: #ffffff; --border: #dee2e6; --text: #212529; --text-muted: #6c757d;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 20px; }}
.container {{ max-width: 960px; margin: 0 auto; }}
.header {{ background: var(--primary); color: white; padding: 24px 32px; border-radius: 12px; margin-bottom: 24px; }}
.header h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 6px; }}
.header p {{ opacity: 0.85; font-size: 13px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; margin-bottom: 20px; }}
.card h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 14px; color: var(--primary); border-bottom: 2px solid var(--primary); padding-bottom: 8px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 16px; }}
.stat-box {{ text-align: center; padding: 14px; background: var(--bg); border-radius: 8px; }}
.stat-box .num {{ font-size: 24px; font-weight: 700; }}
.stat-box .label {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}
.stat-box.pass .num {{ color: var(--success); }}
.stat-box.fail .num {{ color: var(--danger); }}
.stat-box.warn .num {{ color: var(--warning); }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }}
th {{ background: var(--bg); font-weight: 600; font-size: 12px; text-transform: uppercase; color: var(--text-muted); }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
.badge-danger {{ background: #FCEBEB; color: var(--danger); }}
.badge-warning {{ background: #FAEEDA; color: var(--warning); }}
.badge-info {{ background: #E6F1FB; color: var(--info); }}
.row-danger {{ background: #FFF5F5; }}
.row-warning {{ background: #FFFBF0; }}
.row-info {{ background: #F5F9FF; }}
.timing-table {{ margin-top: 10px; }}
.timing-table td:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
.stats-info {{ font-size: 13px; color: var(--text-muted); margin-bottom: 8px; }}
.stats-table {{ width: auto; }}
.stats-table td {{ padding: 4px 16px 4px 0; }}
.chart-container {{ max-width: 600px; margin: 16px auto; }}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>测试报告: {data['skill_name']}</h1>
  <p>生成时间: {data['timeline'].get('started_at_iso', 'N/A')}</p>
</div>

<div class="card">
  <h2>1. 测试概览</h2>
  <div class="grid">
    <div class="stat-box pass"><div class="num">{s_pass}/{s_total}</div><div class="label">场景测试通过</div></div>
    <div class="stat-box pass"><div class="num">{f_pass}/{f_total}</div><div class="label">功能测试通过</div></div>
    <div class="stat-box fail"><div class="num">{f0_count}</div><div class="label">F-0 BLOCK</div></div>
    <div class="stat-box warn"><div class="num">{f1_count}</div><div class="label">F-1 WARN</div></div>
    <div class="stat-box"><div class="num">{f2_count}</div><div class="label">F-2 INFO</div></div>
  </div>
</div>

<div class="card">
  <h2>2. 计时统计</h2>
  <table class="timing-table">
    <tr><td>总耗时</td><td><strong>{timing['total']}s</strong></td></tr>
    <tr><td>脚本执行</td><td>{timing['py_script']}s</td></tr>
    <tr><td>LLM 处理（推导）</td><td>{timing['llm']}s</td></tr>
    <tr><td>目标技能调用</td><td><strong>{timing['target_skill']}s</strong></td></tr>
  </table>
  {stats_row}
  {control_chart}
  {steps_html}
</div>

<div class="card">
  <h2>3. 问题列表</h2>
  {issue_section}
</div>

<div class="card">
  <h2>4. 测试详情</h2>
  <table>
    <tr><th>测试</th><th>维度</th><th>状态</th><th>详情</th></tr>
    {scenario_rows}
    {function_rows}
  </table>
</div>

<div class="card">
  <h2>5. 修复记录</h2>
  {fix_section}
</div>

</div>
</body>
</html>'''


USAGE = """
用法:
  python gen_report.py <skill-dir>              — 生成 HTML + Markdown
  python gen_report.py <skill-dir> --html       — 仅 HTML
  python gen_report.py <skill-dir> --markdown   — 仅 Markdown
"""


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        return
    skill_dir = sys.argv[1]
    _hook_check(skill_dir, "gen_report")
    mode = "both"
    if "--html" in sys.argv:
        mode = "html"
    elif "--markdown" in sys.argv:
        mode = "markdown"
    data = load_all(skill_dir)
    # 输出到数据目录（R-11 合规）
    report_dir = _data_dir_for(skill_dir)
    os.makedirs(report_dir, exist_ok=True)
    if mode in ("markdown", "both"):
        md = gen_markdown(data)
        md_path = os.path.join(report_dir, ".test-report.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"  [REPORT] Markdown 报告: {md_path}")
    if mode in ("html", "both"):
        html = gen_html(data)
        html_path = os.path.join(report_dir, ".test-report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [REPORT] HTML 报告: {html_path}")
    _hook_done(skill_dir, "gen_report")


if __name__ == "__main__":
    main()
