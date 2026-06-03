"""
风险维度库 — 按项目上下文自动匹配分析维度

用法：
    from risk_dimensions import select_dimensions, build_analysis_suggestions
    dims = select_dimensions(context)
    suggestions = build_analysis_suggestions(dims, cpm_result, mc_results, phases)
"""

import re

# ═══════════════════════════════════════════════════
# 风险维度定义
# ═══════════════════════════════════════════════════

DIMENSIONS = {
    "D1": {
        "id": "D1",
        "name": "技术风险",
        "icon": "🛠️",
        "condition": lambda ctx: ctx.get("tech_novelty", "medium") in ("high", "medium")
                                  or "ai" in ctx.get("domain", "").lower(),
        "analysis_template": {
            "title": "技术风险分析",
            "sub_risks": [
                {
                    "name": "技术选型风险",
                    "description": "LLM模型选择（开源vs闭源）、框架版本锁定、API兼容性",
                    "severity": "high",
                    "mitigation": "设置PoC验证周期，核心模块与API调用层解耦"
                },
                {
                    "name": "技术实现复杂度",
                    "description": "RAG准确性、Agent幻觉率、多智能体协调",
                    "severity": "high",
                    "mitigation": "分阶段验证AI能力，先PoC后规模化"
                },
                {
                    "name": "集成风险",
                    "description": "企业系统API兼容性、数据格式转换、认证集成",
                    "severity": "medium",
                    "mitigation": "集成测试前置到开发中期，Mock接口先行"
                },
            ]
        }
    },
    "D2": {
        "id": "D2",
        "name": "供应商/外部依赖风险",
        "icon": "🔗",
        "condition": lambda ctx: ctx.get("domain", "") in ("ai-enterprise", "saas", "platform")
                                  or ctx.get("integration_count", 0) > 2,
        "analysis_template": {
            "title": "供应商与外部依赖风险",
            "sub_risks": [
                {
                    "name": "API依赖风险",
                    "description": "LLM供应商定价变化、服务中断、模型版本淘汰",
                    "severity": "high",
                    "mitigation": "核心功能与API调用层抽象解耦，准备多模型备选方案"
                },
                {
                    "name": "开源组件风险",
                    "description": "许可变更、社区活跃度下降、安全漏洞",
                    "severity": "medium",
                    "mitigation": "定期评估依赖健康状况，锁定关键版本"
                },
                {
                    "name": "供应商锁定",
                    "description": "难以迁移的自定义接口、专属格式",
                    "severity": "medium",
                    "mitigation": "设计时考虑可替换性，使用开放标准"
                },
            ]
        }
    },
    "D3": {
        "id": "D3",
        "name": "相关方风险",
        "icon": "👥",
        "condition": lambda ctx: ctx.get("scale", "medium") in ("large", "enterprise")
                                  or ctx.get("integration_count", 0) > 3,
        "analysis_template": {
            "title": "相关方风险与变革管理",
            "sub_risks": [
                {
                    "name": "用户接受度",
                    "description": "AI辅助决策的信任建立、工作流变更适应",
                    "severity": "high",
                    "mitigation": "渐进式上线，先辅助模式后自动模式"
                },
                {
                    "name": "管理层支持",
                    "description": "预算持续保障、组织优先级变化",
                    "severity": "medium",
                    "mitigation": "分层沟通策略，C-level关注ROI指标"
                },
                {
                    "name": "跨部门协作",
                    "description": "数据共享壁垒、流程所有权模糊",
                    "severity": "medium",
                    "mitigation": "明确数据所有权和流程RACI矩阵"
                },
            ]
        }
    },
    "D4": {
        "id": "D4",
        "name": "进度风险",
        "icon": "📅",
        "condition": lambda ctx: True,  # 总是启用
        "analysis_template": {
            "title": "进度与关键路径风险",
            "sub_risks": [
                {
                    "name": "关键路径集中度",
                    "description": "",
                    "severity": "dynamic",
                    "mitigation": ""
                },
                {
                    "name": "并行执行依赖",
                    "description": "多分支汇合点的阻塞风险",
                    "severity": "medium",
                    "mitigation": "合并点设置明确Owner和deadline"
                },
                {
                    "name": "估算偏差",
                    "description": "",
                    "severity": "dynamic",
                    "mitigation": ""
                },
            ]
        }
    },
    "D5": {
        "id": "D5",
        "name": "商务风险",
        "icon": "💰",
        "condition": lambda ctx: ctx.get("is_commercial", False)
                                  or "roi" in str(ctx.get("phases", "")).lower(),
        "analysis_template": {
            "title": "商务与投资风险",
            "sub_risks": [
                {
                    "name": "ROI不确定性",
                    "description": "AI效率提升的可衡量性",
                    "severity": "high",
                    "mitigation": "设置明确ROI指标（工时节省/错误率降低）"
                },
                {
                    "name": "预算超支",
                    "description": "技术探索成本不可预测",
                    "severity": "medium",
                    "mitigation": "总预算保留15%-20%应急储备"
                },
            ]
        }
    },
    "D6": {
        "id": "D6",
        "name": "资源风险",
        "icon": "👤",
        "condition": lambda ctx: "ai" in ctx.get("domain", "").lower()
                                  or ctx.get("tech_novelty", "medium") == "high",
        "analysis_template": {
            "title": "人力资源风险",
            "sub_risks": [
                {
                    "name": "关键人才获取",
                    "description": "AI工程师、提示工程师的市场供给不足",
                    "severity": "high",
                    "mitigation": "提前启动招聘，保留外部顾问管道"
                },
                {
                    "name": "团队技能匹配",
                    "description": "现有团队与新技术栈的差距",
                    "severity": "medium",
                    "mitigation": "提前规划2-4周培训周期"
                },
                {
                    "name": "关键人员流失",
                    "description": "核心模块知识集中",
                    "severity": "medium",
                    "mitigation": "核心模块安排两人交叉了解（Bus Factor>1）"
                },
            ]
        }
    },
    "D7": {
        "id": "D7",
        "name": "路径实现风险",
        "icon": "🔄",
        "condition": lambda ctx: ctx.get("integration_count", 0) > 2
                                  or ctx.get("critical_path_len", 0) > 10,
        "analysis_template": {
            "title": "实施路径与技术债务风险",
            "sub_risks": [
                {
                    "name": "架构演进风险",
                    "description": "微服务拆分粒度的反复调整",
                    "severity": "medium",
                    "mitigation": "架构决策记录（ADR），追踪每次关键选择"
                },
                {
                    "name": "技术债务",
                    "description": "快速原型阶段遗留的临时方案",
                    "severity": "medium",
                    "mitigation": "每3-4个迭代预留1个技术债偿还周期"
                },
                {
                    "name": "集成爆炸",
                    "description": "多系统对接的测试复杂度",
                    "severity": "high",
                    "mitigation": "集成测试自动化覆盖率目标>80%"
                },
            ]
        }
    },
}


def select_dimensions(context: dict) -> list[dict]:
    """根据项目上下文选择匹配的风险维度"""
    active = []
    for dim_id, dim in DIMENSIONS.items():
        try:
            if dim["condition"](context):
                active.append(dim)
        except Exception:
            pass
    return active


def build_analysis_suggestions(
    active_dims: list[dict],
    cpm_result=None,
    mc_results=None,
    phases: list[dict] = None
) -> str:
    """根据激活的维度构建HTML分析建议内容"""
    lines = ['<div class="card"><h2>多维风险分析</h2>']

    # 关键数字摘要
    mc_stats = ""
    p50_p90_gap = 0
    if mc_results:
        pert = mc_results.get("pert", {})
        stats = pert.get("stats", {})
        quants = pert.get("quantiles", {})
        if stats and quants:
            mean = stats.get("mean", 0)
            std = stats.get("stddev", 0)
            p50 = quants.get("p50", 0)
            p90 = quants.get("p90", 0)
            p50_p90_gap = p90 - p50
            mc_stats = f"P50={p50:.1f}天 / P90={p90:.1f}天 / P90-P50跨度={p50_p90_gap:.1f}天"

    cp_len = len(cpm_result.critical_ids) if (cpm_result and cpm_result.critical_ids) else 0
    project_dur = cpm_result.project_duration if cpm_result else 0

    # 概览条
    gap_risk = ""
    if p50_p90_gap > 0:
        ratio = (p50_p90_gap / max(project_dur, 1)) * 100
        if ratio > 30:
            gap_risk = f'<span class="tag tag-err">⚠️ 进度不确定性高 (P50-P90跨度{ratio:.0f}%)</span>'
        elif ratio > 15:
            gap_risk = f'<span class="tag tag-warn">进度不确定性中等 (P50-P90跨度{ratio:.0f}%)</span>'
        else:
            gap_risk = f'<span class="tag tag-ok">进度不确定性可控</span>'

    lines.append(f'<p><strong>项目总工期:</strong> {project_dur:.1f}天 | '
                 f'<strong>关键路径:</strong> {cp_len}个任务 | '
                 f'{mc_stats}</p>')
    if gap_risk:
        lines.append(f'<p>{gap_risk}</p>')

    # 各维度详细分析
    for dim in active_dims:
        template = dim.get("analysis_template", {})
        sub_risks = template.get("sub_risks", [])

        lines.append(f'<div style="margin:12px 0;padding:10px;border-left:4px solid #3498db;'
                     f'background:#f8f9fa;border-radius:4px">')
        lines.append(f'<h3 style="margin:0 0 8px 0">{dim.get("icon","")} {template.get("title", dim["name"])}</h3>')

        for sr in sub_risks:
            name = sr.get("name", "")
            desc = sr.get("description", "")
            sev = sr.get("severity", "medium")
            mitigation = sr.get("mitigation", "")

            # 动态严重度替换
            if sev == "dynamic":
                if name == "关键路径集中度":
                    if cp_len > 15:
                        sev = "high"
                        desc = f"关键路径上有{cp_len}个任务，路径集中度高，任一延迟将直接影响总工期"
                        mitigation = "为关键路径每个任务分配明确Owner，每日站会跟踪"
                    elif cp_len > 8:
                        sev = "medium"
                        desc = f"关键路径上有{cp_len}个任务，需要关注"
                        mitigation = "关键路径任务设置里程碑检查点"
                    else:
                        sev = "low"
                        desc = f"关键路径仅{cp_len}个任务，路径较分散"
                        mitigation = "保持常规跟踪即可"
                elif name == "估算偏差":
                    if p50_p90_gap > project_dur * 0.3:
                        sev = "high"
                        desc = f"P50-P90跨度{p50_p90_gap:.1f}天，不确定性显著"
                        mitigation = "建议设置项目总工期10%-15%的缓冲期"
                    elif p50_p90_gap > project_dur * 0.15:
                        sev = "medium"
                        desc = f"P50-P90跨度{p50_p90_gap:.1f}天"
                        mitigation = "建议设置5%-10%缓冲期"
                    else:
                        sev = "low"
                        desc = f"P50-P90跨度{p50_p90_gap:.1f}天，估算较为稳定"
                        mitigation = "保持现有计划"

            sev_tag = {"high": "高危", "medium": "中危", "low": "低危"}
            sev_color = {"high": "#e74c3c", "medium": "#f39c12", "low": "#27ae60"}
            lines.append(f'<p style="margin:6px 0">'
                         f'<span class="tag" style="background:{sev_color.get(sev,"#999")};color:#fff">'
                         f'{sev_tag.get(sev, sev)}</span> '
                         f'<strong>{name}</strong>：{desc}')
            if mitigation:
                lines.append(f'<br><span style="color:#666;font-size:0.9em">→ 建议：{mitigation}</span>')
            lines.append('</p>')

        lines.append('</div>')

    # 综合建议
    lines.append('<h3>综合行动建议</h3><ul>')
    if cp_len > 10:
        lines.append(f'<li>关键路径{cp_len}个任务建议每日跟踪，设置明确的里程碑Owner</li>')
    if p50_p90_gap > project_dur * 0.3 if project_dur > 0 else False:
        lines.append(f'<li>P50-P90跨度较大，建议在关键路径末端设置{p50_p90_gap:.0f}天缓冲期</li>')
    if any(d["id"] == "D1" for d in active_dims):
        lines.append('<li>技术风险较高，建议AI核心模块先做技术验证(PoC)再进入正式开发</li>')
    if any(d["id"] == "D3" for d in active_dims):
        lines.append('<li>相关方影响面大，建议制定分层沟通计划和变革管理策略</li>')
    if any(d["id"] == "D6" for d in active_dims):
        lines.append('<li>稀缺人才风险需提前布局，建议招聘与培训并行</li>')
    lines.append('</ul>')

    lines.append('</div>')
    return "\n".join(lines)
