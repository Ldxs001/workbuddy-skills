"""
activity-duration-estimation 全流程编排层

Python 驱动三子技能的完整执行流程。LLM 只需调用 run_pipeline() 主入口，
所有阶段顺序、验证、数据流转由代码硬编码保障，不依赖 LLM 自觉执行。

用法（LLM调用）：
    from scripts.runner import run_pipeline, PipelineState

    # 全流程一键执行
    state = run_pipeline("帮我规划并估算一个电商后台管理系统", mode="full")

    # 只做WBS
    state = run_pipeline("电商后台", mode="wbs")
    print(state.wbs_text_tree)

    # 分步交互（LLM在每一步介入决策）
    state = PipelineState("电商后台")
    state.run_wbs(template="deliverable", custom_data={...})
    state.prepare_estimation()     # WBS→估算参数
    state.run_estimate()            # 执行估算
    state.generate_docs("立项申请书", mode="manual")
"""

import os
import sys
import json
import traceback
from datetime import datetime
from typing import Optional

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)

sys.path.insert(0, SKILL_DIR)
from wbs_engine import (
    WBSNode, WBSResult, build_node_tree, assign_wbs_codes,
    calc_max_depth, validate_wbs, meets_termination_conditions,
    format_text_tree, format_markdown_tree, format_json, format_svg_tree,
    wbs_to_phases, wbs_to_dependencies,
    WBSOutput, WBSFlowState, get_template_info as wbs_get_templates,
    WBS_TEMPLATES
)
from analysis_engine import (
    calc_cpm, auto_plan_dependencies, parse_dependency_string,
    monte_carlo_multi, calc_overlap,
    generate_gantt_svg, generate_mc_svg,
    validate_cpm_input, validate_mc_input, validate_mc_result,
    validate_overlap_tasks, validate_all,
    CPMResult, ValidationResult
)
from project_docs_engine import (
    ProjectData, load_template, list_templates,
    output_manual, customize_sections, add_section, remove_section,
    reorder_sections, rename_section, set_section_mode,
    list_sections_by_mode, customize_template,
    assemble_mixed_document, save_template, delete_template,
    get_template_structure_summary, get_template_mode_summary,
    SectionGenState, TEMPLATES_DIR
)


# ═══════════════════════════════════════════════════
# 阶段枚举
# ═══════════════════════════════════════════════════

PHASE_WBS = "wbs"
PHASE_ESTIMATE = "estimate"
PHASE_DOCS = "docs"


# ═══════════════════════════════════════════════════
# PipelineState — 全流程状态管理
# ═══════════════════════════════════════════════════

class PipelineState:
    """
    全流程状态对象。所有阶段的数据、中间结果、错误信息都存储在此。
    LLM 读取 state 的各字段来获取当前进度和结果。
    """

    def __init__(self, description: str = ""):
        # 输入
        self.description: str = description
        self.project_name: str = ""

        # WBS阶段产出
        self.wbs_result: Optional[WBSResult] = None
        self.wbs_text_tree: str = ""
        self.wbs_json_str: str = ""
        self.wbs_svg: str = ""
        self.wbs_valid: bool = False
        self.wbs_issues: list[str] = []

        # 估算阶段产出
        self.phases: list[dict] = []           # [{name, o, m, p, deliverable}]
        self.dependencies: dict = {}            # {idx: [(pred_idx, type)]}
        self.cpm_result: Optional[CPMResult] = None
        self.mc_results: dict = {}
        self.overlap_results: dict = {}
        self.estimate_summary: str = ""

        # 文档阶段产出
        self.doc_content: str = ""
        self.doc_path: str = ""

        # 运行时
        self.current_phase: str = ""
        self.errors: list[str] = []
        self.last_error: str = ""
        self.completed_phases: list[str] = []

    # ── 查询 ──

    @property
    def has_wbs(self) -> bool:
        return self.wbs_result is not None

    @property
    def has_estimate(self) -> bool:
        return self.cpm_result is not None

    @property
    def has_doc(self) -> bool:
        return bool(self.doc_content)

    def status(self) -> str:
        """输出当前状态摘要（供LLM读取）"""
        lines = [f"项目: {self.project_name or '未设置'}"]
        lines.append(f"描述: {self.description[:80]}...")
        lines.append(f"已完成阶段: {', '.join(self.completed_phases) or '无'}")
        if self.has_wbs:
            lines.append(f"  WBS: 工作包{len(self.wbs_result.work_packages)}个, 验证{'通过' if self.wbs_valid else '有'+str(len(self.wbs_issues))+'个问题'}")
        if self.has_estimate:
            lines.append(f"  估算: 总工期{self.cpm_result.project_duration:.1f}, 关键路径{len(self.cpm_result.critical_ids)}任务")
        if self.has_doc:
            lines.append(f"  文档: 已生成 ({len(self.doc_content)}字)")
        if self.errors:
            lines.append(f"  错误: {len(self.errors)}个")
        return "\n".join(lines)

    # ── 重置 ──

    def reset(self, phase: str = None):
        """重置指定阶段或全部"""
        if phase is None or phase == PHASE_WBS:
            self.wbs_result = None
            self.wbs_text_tree = ""
            self.wbs_json_str = ""
            self.wbs_svg = ""
            self.wbs_valid = False
            self.wbs_issues = []
        if phase is None or phase == PHASE_ESTIMATE:
            self.phases = []
            self.dependencies = {}
            self.cpm_result = None
            self.mc_results = {}
            self.overlap_results = {}
            self.estimate_summary = ""
        if phase is None or phase == PHASE_DOCS:
            self.doc_content = ""
            self.doc_path = ""
        if phase and phase in self.completed_phases:
            self.completed_phases.remove(phase)


    # ═══════════════════════════════════════════════
    # WBS 阶段
    # ═══════════════════════════════════════════════

    def run_wbs(self, template: str = "deliverable",
                custom_data: dict = None) -> WBSResult:
        """
        执行WBS分解。
        template: "deliverable" | "lifecycle" | "modular"
        custom_data: LLM可传入已结构化的WBS数据
        返回: WBSResult (self.wbs_result 同步更新)
        """
        self.current_phase = PHASE_WBS
        self.reset(PHASE_WBS)

        try:
            result = WBSResult()
            result.project_name = self.project_name or "未命名项目"
            result.method_name = WBS_TEMPLATES.get(template, {}).get("name", "交付成果式")

            if custom_data and "children" in custom_data:
                # LLM已提供结构化数据 → 直接构建
                root = WBSNode(name=result.project_name, level=0)
                skeleton = custom_data.get("children", {})
                build_node_tree(skeleton, root)
                result.root = root
            else:
                # 无数据 → 创建单根节点占位（由LLM后续填充）
                root = WBSNode(name=result.project_name, level=0)
                result.root = root

            # 编码 & 深度
            if result.root:
                assign_wbs_codes(result.root)
                result.max_depth = calc_max_depth(result.root)

            # 收集工作包
            result.collect_work_packages()

            # 100%规则验证（自动、不可跳过）
            validate_wbs(result)
            self.wbs_valid = result.is_valid
            self.wbs_issues = result.validation_issues

            # 多格式输出（自动生成）
            self.wbs_text_tree = format_text_tree(result)
            self.wbs_json_str = format_json(result)
            self.wbs_svg = format_svg_tree(result)

            self.wbs_result = result
            self.completed_phases.append(PHASE_WBS)

        except Exception as e:
            self._handle_error(PHASE_WBS, e)

        return self.wbs_result

    def wbs_add_nodes(self, children_data: dict):
        """
        向已存在的WBS根节点追加子节点（增量式构建）。
        LLM可在run_wbs()后逐步添加节点。
        """
        if not self.wbs_result or not self.wbs_result.root:
            self.run_wbs()
        build_node_tree(children_data, self.wbs_result.root)
        assign_wbs_codes(self.wbs_result.root)
        self.wbs_result.collect_work_packages()
        validate_wbs(self.wbs_result)
        self.wbs_valid = self.wbs_result.is_valid
        self.wbs_issues = self.wbs_result.validation_issues
        self.wbs_text_tree = format_text_tree(self.wbs_result)
        self.wbs_json_str = format_json(self.wbs_result)


    # ═══════════════════════════════════════════════
    # 估算阶段
    # ═══════════════════════════════════════════════

    def prepare_estimation(self, custom_phases: list[dict] = None,
                           custom_deps: dict = None):
        """
        准备估算参数。
        - 有WBS时：自动从WBS工作包转换阶段参数
        - 无WBS时：使用custom_phases（由LLM提供）
        - 紧前关系：自动从WBS层级推演，或使用custom_deps
        """
        self.current_phase = PHASE_ESTIMATE

        if custom_phases:
            self.phases = custom_phases
        elif self.wbs_result:
            self.phases = wbs_to_phases(self.wbs_result)
        else:
            raise ValueError("prepare_estimation: 请提供custom_phases或先执行run_wbs()")

        if custom_deps:
            self.dependencies = custom_deps
        elif self.wbs_result:
            self.dependencies = wbs_to_dependencies(self.wbs_result)
        else:
            self.dependencies = auto_plan_dependencies(len(self.phases))

        # 转换 0-based → 1-based（calc_cpm 需要 task_id 从1开始）
        deps_1based = {}
        for k, v in self.dependencies.items():
            k1 = k + 1 if isinstance(k, int) else k
            deps_1based[k1] = []
            for dep in v:
                if isinstance(dep, (list, tuple)):
                    pred_id = dep[0] + 1 if isinstance(dep[0], int) else dep[0]
                    dep_type = dep[1] if len(dep) >= 2 else "FS"
                    deps_1based[k1].append((pred_id, dep_type))
                else:
                    deps_1based[k1].append(dep + 1 if isinstance(dep, int) else dep)
        self.dependencies = deps_1based

    def run_estimate(self, mc_iterations: int = 2000) -> dict:
        """
        执行估算计算（自动运行CPM + MC + 重叠分析）。
        prepare_estimation() 必须已调用。
        返回: 估算结果摘要 dict
        """
        self.current_phase = PHASE_ESTIMATE

        if not self.phases:
            raise ValueError("run_estimate: 请先调用prepare_estimation()")

        # 只重置计算结果，不清除已设置的参数
        self.cpm_result = None
        self.mc_results = {}
        self.overlap_results = {}
        self.estimate_summary = ""

        try:
            # 准备数据
            durations = {i+1: (p.get("m", 0) or 0) for i, p in enumerate(self.phases)}
            mc_phases = [(p["name"], p.get("o", 0), p.get("m", 0), p.get("p", 0))
                         for p in self.phases]

            # 依赖已是1-based（prepare_estimation中已转换）
            deps_formatted = self.dependencies

            # ── 自动验证（不可跳过） ──
            vr_input = validate_cpm_input(durations, deps_formatted)
            vr_mc = validate_mc_input(mc_phases)

            # ── CPM ──
            self.cpm_result = calc_cpm(durations, deps_formatted)

            # ── 蒙特卡洛 ──
            if len(self.phases) >= 1:
                self.mc_results = monte_carlo_multi(
                    mc_phases, mc_iterations,
                    ['pert', 'triangular', 'poisson']
                )

            # ── 重叠分析 ──
            overlap_tasks = []
            if self.cpm_result:
                for tid, cd in self.cpm_result.task_cpm.items():
                    overlap_tasks.append({
                        "name": self.phases[tid-1]["name"] if tid <= len(self.phases) else f"任务{tid}",
                        "start": cd["es"],
                        "end": cd["ef"],
                        "id": tid,
                    })
            if overlap_tasks:
                self.overlap_results = calc_overlap(overlap_tasks)

            # ── 自动验证输出 ──
            vr_cpm = validate_cpm_input(durations, deps_formatted)
            if self.mc_results:
                vr_mc_out = validate_mc_result(self.mc_results)

            # ── 构建摘要 ──
            lines = [f"项目总工期: {self.cpm_result.project_duration:.1f}"]
            if self.cpm_result.critical_path:
                lines.append(f"关键路径: {' → '.join(str(t) for t in self.cpm_result.critical_path)}")
            if self.mc_results:
                pert = self.mc_results.get("pert", {})
                stats = pert.get("stats", {})
                quants = pert.get("quantiles", {})
                lines.append(f"PERT-Beta: 均值={stats.get('mean',0):.1f}, σ={stats.get('stddev',0):.1f}")
                lines.append(f"P50={quants.get('p50',0):.1f}, P90={quants.get('p90',0):.1f}")
            self.estimate_summary = "\n".join(lines)

            self.completed_phases.append(PHASE_ESTIMATE)

        except Exception as e:
            self._handle_error(PHASE_ESTIMATE, e)

        return {
            "summary": self.estimate_summary,
            "cpm": self.cpm_result,
            "mc": self.mc_results,
            "overlap": self.overlap_results,
        }


    # ═══════════════════════════════════════════════
    # 文档阶段
    # ═══════════════════════════════════════════════

    def generate_docs(self, template_name: str = "立项申请书",
                      mode: str = "manual",
                      filled_sections: dict[str, str] = None,
                      output_file: bool = True) -> str:
        """
        生成项目文档。

        template_name: 模板名（预设或自定义）
        mode: "manual" → 输出空模版 | "mixed" → 按章节模式混合组装
        filled_sections: {section_key: content} — auto/outline模式的填充内容
        output_file: 是否保存到文件
        返回: 文档内容字符串
        """
        self.current_phase = PHASE_DOCS
        self.reset(PHASE_DOCS)

        try:
            tpl = load_template(template_name)

            # 构建ProjectData
            pd = ProjectData()
            pd.project_name = self.project_name
            pd.project_description = self.description

            if self.wbs_result:
                pd.wbs_tree_text = self.wbs_text_tree
                pd.wbs_json = self.wbs_json_str
                pd.wbs_work_packages = [
                    {"code": wp.code, "name": wp.name,
                     "deliverable": wp.deliverable,
                     "o": wp.o, "m": wp.m, "p": wp.p}
                    for wp in self.wbs_result.work_packages
                ]

            if self.cpm_result:
                pd.project_duration = self.cpm_result.project_duration
                pd.critical_path = [str(t) for t in self.cpm_result.critical_path]
                pd.cpm_result = f"关键路径: {'→'.join(str(t) for t in self.cpm_result.critical_path)}, 总工期={self.cpm_result.project_duration:.1f}"

            if self.mc_results:
                pert = self.mc_results.get("pert", {})
                quants = pert.get("quantiles", {})
                stats = pert.get("stats", {})
                pd.p50 = quants.get("p50", 0)
                pd.p90 = quants.get("p90", 0)
                pd.estimation_result = f"P50={pd.p50}, P90={pd.p90}, 均值={stats.get('mean',0):.1f}±{stats.get('stddev',0):.1f}"

            # 生成文档
            if mode == "manual":
                self.doc_content = output_manual(tpl, pd)
            elif mode == "mixed":
                self.doc_content = assemble_mixed_document(tpl, pd, filled_sections or {})
            else:
                raise ValueError(f"不支持的模式: {mode}。可选: manual, mixed")

            # 保存文件
            if output_file:
                filename = tpl.get("output_filename", "{project_name}_文档.md")
                filename = filename.replace("{project_name}", self.project_name or "未命名项目")
                from project_docs_engine import save_document
                self.doc_path = save_document(self.doc_content, tpl, pd)

            self.completed_phases.append(PHASE_DOCS)

        except Exception as e:
            self._handle_error(PHASE_DOCS, e)

        return self.doc_content


    # ═══════════════════════════════════════════════
    # 内部
    # ═══════════════════════════════════════════════

    def _handle_error(self, phase: str, error: Exception):
        """统一错误处理"""
        tb = traceback.format_exc()
        msg = f"[{phase}] {error}"
        self.errors.append(msg)
        self.last_error = msg
        # 不抛出异常，由LLM读取state.errors并决定如何处理


# ═══════════════════════════════════════════════════
# 全流程一键入口
# ═══════════════════════════════════════════════════

def run_pipeline(
    description: str,
    mode: str = "full",
    project_name: str = None,
    wbs_template: str = "deliverable",
    wbs_custom_data: dict = None,
    doc_template: str = "立项申请书",
    doc_mode: str = "manual",
    doc_filled: dict[str, str] = None,
    mc_iterations: int = 2000,
    custom_phases: list[dict] = None,
) -> PipelineState:
    """
    全流程一键执行。LLM 只需调这一个入口。

    参数:
        description: 项目描述
        mode: "full" → 全部执行 | "wbs" → 仅WBS | "estimate" → 仅估算 | "docs" → 仅文档
        project_name: 项目名（自动从description提取或手动指定）
        wbs_template: WBS模板 deliverable/lifecycle/modular
        wbs_custom_data: WBS结构化数据（由LLM提供，可略过）
        doc_template: 文档模板名
        doc_mode: manual/mixed
        doc_filled: 文档填充内容 {section_key: content}
        mc_iterations: MC模拟次数
        custom_phases: 自定义估算阶段（有WBS时自动转换）

    返回:
        PipelineState 对象，读取其字段获取各阶段结果

    用法（LLM）:
        state = run_pipeline("电商后台管理系统")
        print(state.wbs_text_tree)        # WBS文本树
        print(state.estimate_summary)     # 估算摘要
        print(state.doc_content)          # 文档内容
    """
    state = PipelineState(description)
    state.project_name = project_name or _extract_project_name(description)

    try:
        if mode in ("full", "wbs"):
            state.run_wbs(template=wbs_template, custom_data=wbs_custom_data)

            # 如果用户提供了阶段参数，直接使用
            if custom_phases:
                state.phases = custom_phases

        if mode in ("full", "estimate"):
            if custom_phases:
                state.prepare_estimation(custom_phases=custom_phases)
            elif state.phases:
                pass  # already set by user
            elif state.wbs_result:
                state.prepare_estimation()  # auto from WBS
            state.run_estimate(mc_iterations=mc_iterations)

        if mode in ("full", "docs"):
            state.generate_docs(
                template_name=doc_template,
                mode=doc_mode,
                filled_sections=doc_filled or {},
            )

    except Exception as e:
        state._handle_error("pipeline", e)

    return state


def _extract_project_name(description: str) -> str:
    """从项目描述中提取项目名（启发式）"""
    # 去掉常见前缀
    text = description.strip()
    prefixes = ["帮我", "请", "规划", "估算", "生成", "做", "搞", "开发", "做一个"]
    for p in prefixes:
        if text.startswith(p):
            text = text[len(p):].strip()
    # 取关键短语
    for suffix in ["项目", "系统", "平台", "应用", "工具", "网站", "App"]:
        if suffix in text:
            idx = text.index(suffix)
            start = max(0, idx - 8)
            return text[start:idx + len(suffix)]
    # 截取前12字
    return text[:12] or "未命名项目"


# ═══════════════════════════════════════════════════
# 工具查询
# ═══════════════════════════════════════════════════

def list_available_templates() -> str:
    """列出可用模板（供LLM读取）"""
    tpls = list_templates()
    lines = ["可用模板:"]
    for name, desc in tpls.items():
        lines.append(f"  - {name}: {desc[:40]}...")
    lines.append("")
    lines.append("WBS模板: deliverable / lifecycle / modular")
    return "\n".join(lines)


def get_pipeline_help() -> str:
    """输出run_pipeline的使用说明"""
    return """
run_pipeline(description, mode="full", ...) — 全流程入口

mode:
  "full"      → WBS + 估算 + 文档 （全自动串联）
  "wbs"       → 仅WBS分解
  "estimate"  → 仅估算（需已有阶段参数）
  "docs"      → 仅文档生成（需已有项目资料）

返回 PipelineState 对象，读取字段:
  state.wbs_text_tree      → WBS文本树
  state.wbs_json_str       → WBS字典JSON
  state.estimate_summary   → 估算摘要
  state.cpm_result         → CPM完整结果
  state.mc_results          → MC模拟结果
  state.doc_content         → 文档内容
  state.errors              → 错误列表
  state.status()            → 当前状态摘要

示例:
  state = run_pipeline("电商后台管理系统", mode="full")
  print(state.wbs_text_tree)
  print(state.estimate_summary)
  print(state.doc_content)
"""
