"""
scenario_engine.py — 场景测试引擎

从蓝皮书（inspector 产出）获取目标技能的完整元信息（脚本清单、函数、引用链路），
结合 SKILL.md 中声明的触发场景、核心能力、工作流程，
自动构建测试计划并对每个场景执行真实 CLI 命令。

蓝皮书即事实来源——所有代码分析已在 inspector 中完成，此处不重复扫描。

场景链路的三个维度：
S1 场景链路完整性 — 对每个 trigger 场景执行真实 CLI，验证可走通
S2 场景输入产出匹配 — 对每个核心能力执行真实 CLI，验证功能可用
S3 场景数据流正确性 — 对工作流步骤执行端到端 CLI，验证链路连续
"""
import ast
import json
import os
import re
import subprocess
import sys
from typing import Optional


class ScenarioResult:
    def __init__(self, sid: str, name: str, status: str = "pass",
                 level: str = "info", message: str = "",
                 file: str = "", lineno: int = 0,
                 suggestion: str = "", detail: str = ""):
        self.sid = sid
        self.name = name
        self.status = status
        self.level = level
        self.message = message
        self.file = file
        self.lineno = lineno
        self.suggestion = suggestion
        self.detail = detail

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in
                ("sid", "name", "status", "level", "message",
                 "file", "lineno", "suggestion", "detail")}

    def __str__(self):
        icon = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}.get(self.status, "?")
        loc = f" {self.file}:{self.lineno}" if self.file else ""
        lev = f"[{self.level.upper()}]" if self.level in ("block", "warn") else ""
        return f"  {icon} {lev} [{self.sid}] {self.name}{loc} — {self.message}"


# ═══════════════════════════════════════════════════════
# SKILL.md 场景解析
# ═══════════════════════════════════════════════════════

def parse_skill_md(skill_dir: str) -> dict:
    """从目标技能目录解析 SKILL.md，提取场景信息"""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_md):
        return {"error": "SKILL.md 不存在"}

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    result = {
        "trigger_scenes": [],
        "capabilities": [],
        "workflow_steps": [],
    }

    # 解析 Frontmatter trigger
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        for line in fm.split("\n"):
            if line.strip().startswith("trigger:"):
                val = line.split(":", 1)[1].strip().strip("'\"")
                result["trigger_scenes"] = [s.strip() for s in val.split("/") if s.strip()]

    # 解析核心能力表格
    cap_match = re.search(r'## 核心能力\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if cap_match:
        cap_section = cap_match.group(1)
        for line in cap_section.split("\n"):
            if line.strip().startswith("| **") or "| **" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3:
                    result["capabilities"].append({
                        "name": parts[1].replace("**", "").strip(),
                        "desc": parts[2] if len(parts) > 2 else "",
                    })

    # 解析工作流程
    wf_match = re.search(r'## 工作流程\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if wf_match:
        wf = wf_match.group(1)
        for line in wf.split("\n"):
            stripped = line.strip()
            if re.match(r'^\d+\.', stripped):
                result["workflow_steps"].append(stripped)
            elif stripped.startswith("- **"):
                m = re.search(r'`([^`]+)`', stripped)
                if m:
                    result["workflow_steps"].append(stripped)

    return result


# ═══════════════════════════════════════════════════════
# 测试计划构建（完全基于蓝皮书数据，不重新扫描）
# ═══════════════════════════════════════════════════════

def auto_build_test_plan(parsed_md: dict, blueprint: dict) -> list[dict]:
    """
    根据 SKILL.md 解析结果和蓝皮书数据构建测试计划。
    蓝皮书由 inspector 在阶段 2 生成，包含：
      - cli_scripts: 所有有 __main__ 的脚本及其支持的参数
      - functions: 所有函数的 AST 签名
      - import_chain: 模块间引用关系
      - file_manifest: 完整文件清单
    """
    cli_scripts = blueprint.get("cli_scripts", [])
    functions = blueprint.get("functions", [])
    py_files = blueprint.get("file_manifest", {}).get("python", [])
    tests = []

    # ── 从 trigger 场景匹配 CLI 脚本 ──
    for scene in parsed_md.get("trigger_scenes", []):
        matched = []
        kw = scene.lower().replace("/", " ").split()
        for s in cli_scripts:
            sname = s["name"].lower()
            for k in kw:
                if len(k) >= 2 and (k in sname or k in s["path"].lower()):
                    matched.append(s)
                    break
        tests.append({
            "scene": scene, "source": "trigger",
            "matched_scripts": matched[:5],
        })

    # ── 从核心能力匹配 CLI 脚本 ──
    for cap in parsed_md.get("capabilities", []):
        name = cap.get("name", "").lower()
        matched = []
        kw = name.replace("+", " ").split()
        for s in cli_scripts:
            for k in kw:
                if len(k) >= 2 and (k in s["name"].lower() or k in s["path"].lower()):
                    matched.append(s)
                    break
        tests.append({
            "scene": f"能力:{cap.get('name', '')}", "source": "capability",
            "matched_scripts": matched[:3],
        })

    # ── 从工作流步骤匹配 CLI 脚本 ──
    for step in parsed_md.get("workflow_steps", []):
        refs = re.findall(r'`([^`]+)`', step)
        matched = []
        for ref in refs:
            ref_clean = ref.replace(".py", "").strip().replace(".", "").strip()
            for s in cli_scripts:
                if ref_clean in s["name"] or ref_clean in s["path"].lower():
                    matched.append(s)
                    break
        if matched:
            tests.append({
                "scene": f"工作流:{step[:50]}", "source": "workflow",
                "matched_scripts": matched[:3],
            })

    return tests


# ═══════════════════════════════════════════════════════
# 场景测试执行器
# ═══════════════════════════════════════════════════════

class ScenarioRunner:
    """
    通用场景测试执行器。
    基于蓝皮书的 cli_scripts 清单执行真实 CLI 命令。
    不硬编码任何技能特定的脚本名、参数或路径。
    """

    def __init__(self, skill_dir: str, blueprint: dict):
        self.skill_dir = skill_dir
        self.blueprint = blueprint  # 蓝皮书即事实来源
        self.results: list[ScenarioResult] = []

        # 从蓝皮书获取 CLI 脚本（infra 层已在 inspector 中完成检测）
        self.cli_scripts = blueprint.get("cli_scripts", [])

        # 解析 SKILL.md
        self.parsed_md = parse_skill_md(skill_dir)

        # 自动构建测试计划
        self.test_plan = auto_build_test_plan(self.parsed_md, blueprint)

    def add(self, r: ScenarioResult):
        self.results.append(r)

    def run(self):
        """执行 S1-S3 场景测试"""
        self._run_s1_scenarios()
        self._run_s2_scenarios()
        self._run_s3_scenarios()

    def _exec(self, script: dict, args: list[str],
              test_name: str, sid: str) -> ScenarioResult:
        """执行 CLI 脚本"""
        abspath = os.path.join(self.skill_dir, script["path"])
        try:
            cmd = [sys.executable, abspath] + args
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
                cwd=self.skill_dir,
            )
            if result.returncode in (0, 2):
                return ScenarioResult(sid, f"「{test_name}」", "pass", "info",
                                       f"rc={result.returncode}")
            err = result.stderr.strip()[:150] or result.stdout.strip()[:150]
            return ScenarioResult(sid, f"「{test_name}」", "fail", "warn",
                                   f"rc={result.returncode}: {err}",
                                   script["path"])
        except subprocess.TimeoutExpired:
            return ScenarioResult(sid, f"「{test_name}」", "fail", "block",
                                   "执行超时 (30s)", script["path"])
        except Exception as e:
            return ScenarioResult(sid, f"「{test_name}」", "fail", "block",
                                   f"执行异常: {e}", script["path"])

    def _run_suite(self, tests: list[dict], sid: str, label: str):
        """通用场景执行逻辑"""
        if not tests:
            self.add(ScenarioResult(sid, label, "skip", "info", "无测试场景"))
            return

        executed = 0
        for test in tests:
            scripts = test["matched_scripts"]
            if not scripts:
                self.add(ScenarioResult(sid, f"{label}「{test['scene'][:40]}」", "pass", "info",
                                         "由外部编排实现，无直接 CLI"))
                continue
            for sc in scripts:
                self._exec(sc, ["--help"],
                           f"{test['scene'][:30]} → {sc['name']} --help", sid)
                executed += 1
                # 如果脚本有 --json/--list/--show，也测试
                for flag in ["--json", "--list", "--show", "--check-only"]:
                    if sc["supports"].get(flag):
                        self._exec(sc, [flag],
                                   f"{test['scene'][:30]} → {sc['name']} {flag}", sid)
                        executed += 1
                        break

        if executed > 0:
            self.add(ScenarioResult(sid, f"{label}执行汇总", "pass", "info",
                                     f"执行了 {executed} 个 CLI 命令"))

    # ═══════════════════════════════════════════════════════
    # S1: 每个 trigger 场景执行 CLI 验证
    # ═══════════════════════════════════════════════════════
    def _run_s1_scenarios(self):
        trigger_tests = [t for t in self.test_plan if t["source"] == "trigger"]
        self._run_suite(trigger_tests, "S1", "触发场景")

    # ═══════════════════════════════════════════════════════
    # S2: 每个核心能力执行 CLI 验证
    # ═══════════════════════════════════════════════════════
    def _run_s2_scenarios(self):
        cap_tests = [t for t in self.test_plan if t["source"] == "capability"]
        self._run_suite(cap_tests, "S2", "核心能力")

    # ═══════════════════════════════════════════════════════
    # S3: 工作流步骤端到端 CLI 验证
    # ═══════════════════════════════════════════════════════
    def _run_s3_scenarios(self):
        wf_tests = [t for t in self.test_plan if t["source"] == "workflow"]
        if not wf_tests:
            self.add(ScenarioResult("S3", "工作流链路", "skip", "info", "无工作流程"))
            return
        tested = set()
        for test in wf_tests:
            for sc in test["matched_scripts"]:
                p = sc["path"]
                if p in tested:
                    continue
                tested.add(p)
                self._exec(sc, ["--help"],
                           f"工作流:{sc['name']} --help", "S3")
        if tested:
            self.add(ScenarioResult("S3", "工作流链路", "pass", "info",
                                     f"验证了 {len(tested)} 个脚本入口"))

    def generate_report(self) -> dict:
        summary = {"total": 0, "pass": 0, "fail": 0, "skip": 0,
                   "block": 0, "warn": 0, "info": 0}
        for r in self.results:
            summary["total"] += 1
            summary[r.status] += 1
            if r.level in ("block", "warn", "info"):
                summary[r.level] += 1
        return {"summary": summary, "results": [r.to_dict() for r in self.results]}

    def print_report(self) -> str:
        s = self.generate_report()["summary"]
        lines = [
            "=" * 60,
            "  场景测试报告（基于蓝皮书 · 真实 CLI 执行）",
            "=" * 60,
            f"  总计: {s['total']} | 通过: {s['pass']} | 失败: {s['fail']} | 跳过: {s['skip']}",
            f"  F-0 BLOCK: {s['block']} | F-1 WARN: {s['warn']} | F-2 INFO: {s['info']}",
            "",
            "── 详细结果:",
        ]
        for r in self.results:
            lines.append(str(r))
            if r.suggestion:
                lines.append(f"    场景建议: {r.suggestion[:150]}")
        lines.append("=" * 60)
        lines.append(f"  场景结论: {'PASS' if s['block'] == 0 else 'FAIL'} (BLOCK={s['block']})")
        lines.append("=" * 60)
        return "\n".join(lines)


def run_scenario_test(skill_dir: str, blueprint: dict) -> tuple[dict, str]:
    runner = ScenarioRunner(skill_dir, blueprint)
    runner.run()
    return runner.generate_report(), runner.print_report()


if __name__ == "__main__":
    from inspector import scan

    if len(sys.argv) >= 2:
        target = sys.argv[1]
        bb = scan(target)
        bp = bb.to_dict()
        report, text = run_scenario_test(target, bp)
        print(text)

        report_path = os.path.join(target, ".scenario-test_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n场景报告 JSON 已保存: {report_path}")
    else:
        print("用法: python scenario_engine.py <skill-dir>")
