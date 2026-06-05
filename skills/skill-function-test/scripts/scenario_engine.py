"""
scenario_engine.py — 场景测试引擎

从目标技能的 SKILL.md 中解析触发场景、核心能力、工作流程，
构造场景级端到端测试用例。

场景链路的四个维度：
S1 场景链路完整性 — 触发场景 → 核心能力 → 工作流程 → 代码实现
S2 场景输入产出匹配 — 场景声称的输入是否有对应的函数参数
S3 场景数据流正确性 — 场景步骤间的数据传递是否连续
"""
import ast
import json
import os
import re
import sys
from typing import Optional

# R-12 审计锚点
DEFAULT_DATA_DIR_RAW = "skills/.standardization/skill-function-test/data/"


class ScenarioResult:
    def __init__(self, sid: str, name: str, status: str = "pass",
                 level: str = "info", message: str = "",
                 file: str = "", lineno: int = 0,
                 suggestion: str = "", detail: str = ""):
        self.sid = sid          # S1/S2/S3
        self.name = name
        self.status = status    # pass/fail/skip
        self.level = level      # block/warn/info
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
        "reference_files": [],
        "mentioned_functions": [],
    }

    # 解析 Frontmatter
    fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        for line in fm.split("\n"):
            if line.strip().startswith("trigger:"):
                val = line.split(":", 1)[1].strip().strip("'\"")
                result["trigger_scenes"] = [s.strip() for s in val.split("/") if s.strip()]
            if line.strip().startswith("trigger_negative:"):
                val = line.split(":", 1)[1].strip().strip("'\"")
                result["trigger_negative"] = [s.strip() for s in val.split("/") if s.strip()]

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
            # 渐进式文件索引
            if "| `" in line and "` |" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2 and parts[0].startswith("`"):
                    result["reference_files"].append(parts[0].strip("`"))

    # 解析工作流程
    wf_match = re.search(r'## 工作流程\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if wf_match:
        wf = wf_match.group(1)
        for line in wf.split("\n"):
            stripped = line.strip()
            if re.match(r'^\d+\.', stripped):
                result["workflow_steps"].append(stripped)
            elif stripped.startswith("- `"):
                m = re.search(r'`([^`]+)`', stripped)
                if m:
                    result["mentioned_functions"].append(m.group(1))

    # 从代码块中提取函数引用
    for m in re.finditer(r'```(?:python|bash)?\n(.*?)```', content, re.DOTALL):
        code = m.group(1)
        for imp in re.finditer(r'(?:from\s+(\S+)\s+)?import\s+(\S+)', code):
            full = imp.group(0).strip()
            if full not in result["mentioned_functions"]:
                result["mentioned_functions"].append(full)
        for func_ref in re.finditer(r'(\w+\.\w+\([^)]*\))', code):
            result["mentioned_functions"].append(func_ref.group(1))

    return result


# ═══════════════════════════════════════════════════════
# 场景测试执行
# ═══════════════════════════════════════════════════════

class ScenarioRunner:
    def __init__(self, skill_dir: str, blueprint: dict):
        self.skill_dir = skill_dir
        self.blueprint = blueprint
        self.results: list[ScenarioResult] = []

    def add(self, r: ScenarioResult):
        self.results.append(r)

    def run(self):
        """执行 S1-S3 场景测试"""
        self._run_s1_chain()
        self._run_s2_io()
        self._run_s3_flow()

    # ═══════════════════════════════════════════════════════
    # S1: 场景链路完整性
    # ═══════════════════════════════════════════════════════
    def _run_s1_chain(self):
        """触发场景 → 核心能力 → 工作流程 → 代码实现"""
        skill_md = os.path.join(self.skill_dir, "SKILL.md")
        if not os.path.exists(skill_md):
            self.add(ScenarioResult("S1", "SKILL.md 不存在", "fail", "block",
                                     f"路径: {skill_md}"))
            return

        parsed = parse_skill_md(self.skill_dir)

        # 检查是否有触发场景
        scenes = parsed.get("trigger_scenes", [])
        if scenes:
            self.add(ScenarioResult("S1", f"触发场景: {len(scenes)} 个", "pass", "info",
                                     "; ".join(scenes[:5])))
        else:
            self.add(ScenarioResult("S1", "缺少触发场景声明", "fail", "warn",
                                     "frontmatter 中无 trigger 字段或为空",
                                     "SKILL.md", 0, "在 frontmatter 中添加 trigger 字段"))

        # 检查核心能力
        caps = parsed.get("capabilities", [])
        if caps:
            self.add(ScenarioResult("S1", f"核心能力: {len(caps)} 项", "pass", "info",
                                     ", ".join(c[:20] for c in [c["name"] for c in caps[:5]])))
        else:
            self.add(ScenarioResult("S1", "缺少核心能力声明", "fail", "warn",
                                     "SKILL.md 中无 ## 核心能力 章节或为空",
                                     "SKILL.md", 0, "添加核心能力表格"))

        # 检查工作流程步骤
        steps = parsed.get("workflow_steps", [])
        if steps:
            self.add(ScenarioResult("S1", f"工作流程: {len(steps)} 步", "pass", "info",
                                     "; ".join(s[:30] for s in steps[:3])))
        else:
            self.add(ScenarioResult("S1", "缺少工作流程声明", "fail", "warn",
                                     "SKILL.md 中无 ## 工作流程 章节",
                                     "SKILL.md", 0, "添加工作流程章节"))

        # 检查 MD 中引用的文件在蓝皮书中是否存在
        ref_files = parsed.get("reference_files", [])
        all_files = set()
        for cat in self.blueprint.get("file_manifest", {}).values():
            all_files.update(cat)

        for ref in ref_files:
            found = False
            for af in all_files:
                if ref in af or af in ref:
                    found = True
                    break
            if not found:
                self.add(ScenarioResult("S1", f"引用文件可能缺失", "warn", "fail",
                                         f"SKILL.md 中声明了 {ref} 但蓝皮书未找到一致路径",
                                         "SKILL.md", 0,
                                         f"确认 {ref} 是否存在，或修正 SKILL.md 中的路径引用"))

    # ═══════════════════════════════════════════════════════
    # S2: 场景输入产出匹配
    # ═══════════════════════════════════════════════════════
    def _run_s2_io(self):
        """场景声称的输入→产出是否有对应的函数实现"""
        parsed = parse_skill_md(self.skill_dir)
        mentioned = parsed.get("mentioned_functions", [])
        functions = self.blueprint.get("functions", [])
        func_names = {f["name"] for f in functions}

        for ref in mentioned:
            # 提取纯函数名（去掉括号和参数）
            pure_name = ref.split("(")[0].split(".")[-1].strip()
            if pure_name and pure_name not in ("print", "len", "range", "open", "str",
                                                "int", "float", "list", "dict", "set",
                                                "type", "isinstance", "hasattr", "getattr",
                                                "super", "object", "property"):
                if pure_name not in func_names:
                    # 可能是模块名引用而非函数
                    self.add(ScenarioResult("S2", f"场景引用函数未在蓝皮书中找到", "warn", "fail",
                                             f"SKILL.md 引用了 {ref} 但 AST 扫描未发现 {pure_name}()",
                                             "SKILL.md", 0,
                                             f"确认 {ref} 是实际存在的函数名，或修正 SKILL.md 中的引用"))

        # 检查每个场景是否有对应的实现函数
        for scene in parsed.get("trigger_scenes", [])[:10]:
            # 寻找名称中包含场景关键词的函数
            keywords = scene.replace("/", " ").split()
            matching = [f for f in functions
                       if any(kw.lower() in f["name"].lower() for kw in keywords)]
            if matching:
                self.add(ScenarioResult("S2", f"场景 '{scene[:20]}' 有 {len(matching)} 个匹配函数",
                                         "pass", "info",
                                         ", ".join(m["name"] for m in matching[:3])))
            else:
                self.add(ScenarioResult("S2", f"场景 '{scene[:20]}' 无直接匹配函数",
                                         "warn", "pass",
                                         "可能由 LLM 编排实现，非直接函数映射"))

    # ═══════════════════════════════════════════════════════
    # S3: 场景数据流正确性
    # ═══════════════════════════════════════════════════════
    def _run_s3_flow(self):
        """场景步骤间的数据传递是否连续"""
        imports = self.blueprint.get("import_chain", {})
        functions = self.blueprint.get("functions", [])

        # 检查模块间的 import 依赖是否完整
        for src_file, imported in imports.items():
            for imp in imported[:5]:  # 只看前5个
                mod = imp.split(".")[0]
                if mod in ("os", "sys", "json", "math", "re", "datetime",
                           "typing", "collections", "random", "copy",
                           "shutil", "tempfile", "sqlite3", "subprocess",
                           "pathlib", "functools", "itertools", "abc",
                           "enum", "dataclasses", "hashlib", "base64",
                           "io", "textwrap", "logging", "argparse",
                           "threading", "time", "glob", "csv", "html",
                           "http", "urllib", "webbrowser", "uuid", "socket"):
                    continue
                # 检查内部 import
                found = False
                for py_file in self.blueprint.get("file_manifest", {}).get("python", []):
                    fname = py_file.replace("/", ".").replace(".py", "")
                    if fname.endswith(mod):
                        found = True
                        break
                if not found:
                    self.add(ScenarioResult("S3", f"跨模块引用需确认", "info", "pass",
                                             f"{src_file} → {imp}（外部依赖或运行时加载）"))

        # 检查函数间的参数传递是否有明显断链
        func_pairs = []
        for fn in functions:
            params = fn.get("params", [])
            # 查找参数名与另一个函数返回值的匹配
            if params:
                func_pairs.append((fn["name"], params))

        # 检查调用链中有无明显的"输出不匹配输入"
        for name, params in func_pairs:
            for p in params:
                if p in ("self", "cls", "args", "kwargs", "*"):
                    continue
                # 查找是否有其他函数产出这个参数名作为输出
                producers = [f["name"] for f in functions
                            if p in f["name"].lower()]
                if not producers and p not in ("state", "data", "config", "result",
                                                "input_data", "output", "options",
                                                "settings", "file", "path", "name",
                                                "mode", "value", "key", "db_path",
                                                "limit", "items", "values", "opt",
                                                "weight", "volume", "count", "size",
                                                "dry_run", "backup", "verbose",
                                                "no_backup", "force", "yes"):
                    self.add(ScenarioResult("S3", f"参数 '{p}' 无可识别生产者", "info", "pass",
                                             f"函数 {name}() 的参数 '{p}' 可能由外部传入"))

        # 检查数据目录路径一致性
        py_files = self.blueprint.get("file_manifest", {}).get("python", [])
        data_dirs = set()
        data_re = re.compile(r'\.standardization/([^/]+)/data/')
        for relpath in py_files:
            abspath = os.path.join(self.skill_dir, relpath)
            try:
                with open(abspath, "r", encoding="utf-8") as f:
                    for line in f:
                        if ".standardization" in line and "data" in line:
                            m = data_re.search(line)
                            if m:
                                data_dirs.add(m.group())
            except Exception:
                pass

        if len(data_dirs) > 1:
            self.add(ScenarioResult("S3", f"多数据目录引用", "warn", "fail",
                                     f"发现 {len(data_dirs)} 个不同数据目录: {data_dirs}",
                                      "", 0, "统一到单一 data_dir"))

    def generate_report(self) -> dict:
        """生成场景测试报告"""
        summary = {"total": 0, "pass": 0, "fail": 0, "skip": 0,
                   "block": 0, "warn": 0, "info": 0}
        for r in self.results:
            summary["total"] += 1
            summary[r.status] += 1
            if r.level in ("block", "warn", "info"):
                summary[r.level] += 1
        return {
            "summary": summary,
            "results": [r.to_dict() for r in self.results],
        }

    def print_report(self) -> str:
        report = self.generate_report()
        s = report["summary"]
        lines = [
            "=" * 60,
            "  场景测试报告",
            "=" * 60,
            f"  总计: {s['total']} | 通过: {s['pass']} | 失败: {s['fail']}",
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


# ═══════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════

def run_scenario_test(skill_dir: str, blueprint: dict) -> tuple[dict, str]:
    """执行完整场景测试"""
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

        # 保存报告到数据目录（R-12 合规）
        from test_config import config_path as _cfg
        _rd = os.path.dirname(_cfg(target))
        os.makedirs(_rd, exist_ok=True)
        report_path = os.path.join(_rd, ".scenario-test_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n场景报告 JSON 已保存: {report_path}")
    else:
        print("用法: python scenario_engine.py <skill-dir>")
