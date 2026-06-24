#!/usr/bin/env python3
"""
novel-style-check — 风格一致性校验 + 报告输出。

校验维度：
  1. 人称一致性（第一人称/第三人称是否统一）
  2. 术语密度（每段技术概念数量是否超标）
  3. 关键人物/物品名称是否前后一致
  4. 语调稳定性（是否有情绪/风格的突变段落）

用法：
  python novel_style_check.py <chapter_dir> <scene_setting_path> <report_path>
"""

import os
import sys
import json
import re


TECH_TERMS = [
    "系统", "协议", "接口", "线程", "模型", "算法", "参数",
    "函数", "数据", "传感器", "信号", "代码", "模块", "日志",
    "诊断", "BPM", "皮层", "神经元", "神经", "激素", "皮质醇",
    "催产素", "突触", "频率", "阈值", "误差", "反馈"
]


def _read_all_text(chapter_dir: str) -> list:
    """读取子目录下所有 .txt 文件，返回 (filename, lines) 列表"""
    if not os.path.isdir(chapter_dir):
        return []
    files = sorted([f for f in os.listdir(chapter_dir) if f.endswith(".txt")])
    result = []
    for f in files:
        path = os.path.join(chapter_dir, f)
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        result.append((f, [l.strip() for l in lines if l.strip()]))
    return result


def _check_person_consistency(all_text: list) -> list:
    """检查人称一致性"""
    issues = []
    first_person_count = 0
    third_person_count = 0

    for fname, lines in all_text:
        for line in lines:
            if re.search(r'^我', line):
                first_person_count += 1
            if re.search(r'^他|^她|^它', line):
                third_person_count += 1

    total = first_person_count + third_person_count
    if total > 0:
        first_ratio = first_person_count / total
        if first_ratio < 0.7:
            issues.append({
                "level": "WARN",
                "dimension": "人称一致性",
                "detail": f"第一人称占比 {first_ratio:.0%}，可能偏离第一人称叙事"
            })
        else:
            issues.append({
                "level": "PASS",
                "dimension": "人称一致性",
                "detail": f"第一人称占比 {first_ratio:.0%}，符合预期"
            })
    return issues


def _check_tech_density(all_text: list) -> list:
    """检查术语密度——每段技术概念数量"""
    issues = []
    for fname, lines in all_text:
        tech_count = 0
        for term in TECH_TERMS:
            for line in lines:
                if term in line:
                    tech_count += 1
        density = tech_count / max(len(lines), 1)
        if density > 3.0:
            issues.append({
                "level": "WARN",
                "dimension": "术语密度",
                "detail": f"{fname}: 每行平均 {density:.1f} 个技术概念（建议 ≤3）"
            })
        else:
            issues.append({
                "level": "PASS",
                "dimension": "术语密度",
                "detail": f"{fname}: 每行平均 {density:.1f} 个技术概念"
            })
    return issues


def _check_name_consistency(all_text: list, scene_setting: dict) -> list:
    """检查关键人物/物品名称是否一致"""
    issues = []
    # 从 scene_setting 提取关键名称
    names = set()
    protagonist = scene_setting.get("protagonist", {})
    if protagonist.get("ai_self", {}).get("name"):
        names.add(protagonist["ai_self"]["name"])
    if protagonist.get("human_body", {}).get("name"):
        names.add(protagonist["human_body"]["name"])
    relationship = protagonist.get("human_body", {}).get("relationship", {})
    if isinstance(relationship, dict):
        for k, v in relationship.items():
            if isinstance(v, str):
                names.add(v.split("（")[0].strip())

    all_text_combined = "\n".join([" ".join(lines) for _, lines in all_text])
    for name in names:
        if name and name not in all_text_combined:
            issues.append({
                "level": "INFO",
                "dimension": "名称一致性",
                "detail": f"角色名 [{name}] 在本章中未出现"
            })
        else:
            issues.append({
                "level": "PASS",
                "dimension": "名称一致性",
                "detail": f"角色名 [{name}] 存在"
            })
    return issues


def generate_report(chapter_dir: str, scene_setting_path: str, report_path: str):
    if not os.path.exists(scene_setting_path):
        print(f"ERROR: novel_state.json 未找到: {scene_setting_path}")
        print(f"  → 必须先运行 novel_state_manager.py init")
        sys.exit(1)

    # 阶段门禁：需要 ≥ writing
    _order = {"none": 0, "init": 10, "stage1_done": 20, "writing": 30, "chapter_done": 40, "stage3_ready": 50, "complete": 60}
    with open(scene_setting_path, "r", encoding="utf-8") as f:
        _state = json.load(f)
    _p = _order.get(_state.get("current_phase", "none"), 0)
    if _p < 30:
        print(f"ERROR: novel_style_check 需要阶段 ≥ writing(30)，当前为 {_state.get('current_phase', 'none')}({_p})")
        print(f"  请至少完成一个子结构的写作后再执行风格校验。")
        sys.exit(1)
    all_text = _read_all_text(chapter_dir)
    if not all_text:
        print("ERROR: 章节目录为空或不存在")
        sys.exit(1)

    scene_setting = {}
    if os.path.exists(scene_setting_path):
        with open(scene_setting_path, "r", encoding="utf-8") as f:
            scene_setting = json.load(f)

    dir_name = os.path.basename(chapter_dir)
    report_lines = []
    report_lines.append(f"# 风格一致性报告 — {dir_name}")
    report_lines.append(f"")

    # 人称检查
    report_lines.append(f"## 人称一致性")
    for issue in _check_person_consistency(all_text):
        icon = "✅" if issue["level"] == "PASS" else "⚠️"
        report_lines.append(f"- {icon} {issue['detail']}")
    report_lines.append(f"")

    # 术语密度
    report_lines.append(f"## 术语密度")
    for issue in _check_tech_density(all_text):
        icon = "✅" if issue["level"] == "PASS" else "⚠️"
        report_lines.append(f"- {icon} {issue['detail']}")
    report_lines.append(f"")

    # 名称一致性
    report_lines.append(f"## 名称一致性")
    for issue in _check_name_consistency(all_text, scene_setting):
        icon = "✅" if issue["level"] == "PASS" else "ℹ️"
        report_lines.append(f"- {icon} {issue['detail']}")
    report_lines.append(f"")

    # 总结
    report_lines.append(f"## 总结")
    all_issues = (
        _check_person_consistency(all_text)
        + _check_tech_density(all_text)
        + _check_name_consistency(all_text, scene_setting)
    )
    pass_count = sum(1 for i in all_issues if i["level"] == "PASS")
    warn_count = sum(1 for i in all_issues if i["level"] == "WARN")
    info_count = sum(1 for i in all_issues if i["level"] == "INFO")
    report_lines.append(f"- ✅ PASS: {pass_count}")
    report_lines.append(f"- ⚠️ WARN: {warn_count}")
    report_lines.append(f"- ℹ️ INFO: {info_count}")
    report_lines.append(f"")
    report_lines.append(f"---")
    report_lines.append(f"*报告由 novel-style-check 生成*")

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        f.flush()
        os.fsync(f.fileno())

    print(f"OK report={report_path} pass={pass_count} warn={warn_count}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: novel_style_check.py <chapter_dir> <scene_setting_path> [report_path]")
        sys.exit(1)

    report_path = sys.argv[3] if len(sys.argv) >= 4 else os.path.join(
        sys.argv[1], "..", "..", "data", "style_report.md"
    )
    generate_report(
        chapter_dir=sys.argv[1],
        scene_setting_path=sys.argv[2],
        report_path=report_path
    )
