"""
round-robin-allocator  |  CLI 主入口
======================================
支持两种使用模式：

  模式 A：对话式（逐步引导）
      python main.py

  模式 B：一行统计数据直接输入
      python main.py --input "5个方案，4周，33个项目，比例7:8:10:3:5"
      python main.py --input "3 options, 6 rounds, 20 items, ratio 1:1:2"

输出（每次运行均生成以下文件，路径可通过 --outdir 指定）：
  allocation_result.md   Markdown 表格
  allocation_result.csv  CSV 数据
  allocation_result.html 可交互 HTML 可视化

依赖：Python 标准库（无第三方包）
      可视化需要浏览器打开 HTML（无需服务器）
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

# 确保能找到同目录下的 allocator / visualizer
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from allocator import allocate, compute_stats
from visualizer import render_html


# ─────────────────────────────────────────────
# 自然语言解析
# ─────────────────────────────────────────────

# 支持的数字中文/英文词
_CN_NUM = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "十一": 11, "十二": 12, "二十": 20, "三十": 30,
    "百": 100,
}


def _to_int(s: str) -> int | None:
    s = s.strip()
    if s.isdigit():
        return int(s)
    if s in _CN_NUM:
        return _CN_NUM[s]
    return None


def parse_one_line(text: str) -> dict | None:
    """
    从一行文字中尝试提取 N / T / K / ratios。
    示例：
      "5个方案，4个周期，33个项目，比例7:8:10:3:5"
      "3 options, 6 rounds, 20 items, ratio 1:1:2"
      "N=20 T=3 K=4 ratios=1,1,1,2"
      只有数字："33 4 5 7 8 10 3 5"（按 N T K r1 r2... 顺序）
    返回 dict(N, T, K, ratios) 或 None（无法解析）
    """
    text = text.strip()

    # ── 关键字匹配模式 ──
    result: dict = {}

    # 尝试识别 N（对象数）：中文"33个项目/对象/人/条..."
    for pat in [
        r"(\d+)\s*(?:个|名|条|位|件|只|台)?\s*(?:项目|对象|样本|用户|学生|员工|商品|条目|item|object|subject|entity)",
        r"N\s*[=:＝]\s*(\d+)",
        r"(?:对象|主体|item)[数量共有]*\s*(\d+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["N"] = int(m.group(1))
            break

    # 尝试识别 T（轮次）
    for pat in [
        r"(\d+)\s*(?:个|轮|次)?\s*(?:周期|轮次|轮|周|月|阶段|round|period|week|month|turn)",
        r"T\s*[=:＝]\s*(\d+)",
        r"(?:周期|轮次|轮数|round)[数共]*\s*(\d+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["T"] = int(m.group(1))
            break

    # 尝试识别 K（选项数）
    for pat in [
        r"(\d+)\s*(?:个|套|种|类|条)?\s*(?:方案|选项|策略|类别|组|颜色|option|choice|type|category|scheme|variant)",
        r"K\s*[=:＝]\s*(\d+)",
        r"(?:方案|选项|策略)[数共]*\s*(\d+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["K"] = int(m.group(1))
            break

    # 尝试识别比例
    for pat in [
        r"(?:比例|ratio|ratios|权重|weight)\s*[=:＝]?\s*([\d\s:,，/]+)",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            nums = re.findall(r"\d+\.?\d*", raw)
            if nums:
                result["ratios"] = [float(x) for x in nums]
            break

    # ── 如果关键字匹配不完整，尝试纯数字顺序推断 ──
    if len(result) < 3:
        nums = re.findall(r"\d+\.?\d*", text)
        if len(nums) >= 3:
            # 尝试：第1个=N, 第2个=T, 第3个=K, 后续=ratios
            candidate_N = int(float(nums[0]))
            candidate_T = int(float(nums[1]))
            candidate_K = int(float(nums[2]))
            candidate_ratios = [float(x) for x in nums[3:]]
            if not candidate_ratios or len(candidate_ratios) != candidate_K:
                candidate_ratios = [1.0] * candidate_K
            result.setdefault("N", candidate_N)
            result.setdefault("T", candidate_T)
            result.setdefault("K", candidate_K)
            result.setdefault("ratios", candidate_ratios)

    # ── 验证完整性 ──
    if not all(k in result for k in ("N", "T", "K")):
        return None

    K = result["K"]
    if "ratios" not in result or len(result["ratios"]) != K:
        result["ratios"] = [1.0] * K  # 等比例回退

    return result


# ─────────────────────────────────────────────
# 对话式引导
# ─────────────────────────────────────────────

def _ask(prompt: str, validator=None, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            val = validator(raw) if validator else raw
            return val
        except Exception as e:
            print(f"  ⚠️  输入无效：{e}，请重新输入")


def interactive_input(labels: dict | None = None) -> dict:
    """
    逐步对话收集参数。
    labels 可自定义术语，例如 {"obj": "学生", "slot": "月", "option": "方案"}
    """
    if labels is None:
        labels = {}
    obj_name   = labels.get("obj",    "对象")
    slot_name  = labels.get("slot",   "轮次")
    opt_name   = labels.get("option", "选项")

    print()
    print("═" * 50)
    print("  均匀轮转分配工具  |  交互式设置")
    print("═" * 50)
    print(f"  说明：将若干「{obj_name}」在多个「{slot_name}」中，")
    print(f"        按比例分配「{opt_name}」，并尽量让每个{obj_name}")
    print(f"        每次都获得不同的{opt_name}。")
    print()
    print("  提示：直接粘贴一行描述也可自动解析")
    print("        例：「33个项目，4个周期，5个方案，比例7:8:10:3:5」")
    print()

    # 先尝试一行解析
    first = input("  ▶ 请输入描述（或直接回车进入逐步设置）: ").strip()
    if first:
        parsed = parse_one_line(first)
        if parsed:
            print(f"\n  ✅ 自动识别成功：")
            print(f"     {obj_name}数量 N = {parsed['N']}")
            print(f"     {slot_name}数量 T = {parsed['T']}")
            print(f"     {opt_name}数量 K = {parsed['K']}")
            print(f"     比例 = {parsed['ratios']}")
            confirm = input("  确认使用以上参数？(y/n) [y]: ").strip().lower()
            if confirm != "n":
                return parsed
        else:
            print("  ⚠️  无法自动解析，进入逐步设置……")

    # 逐步引导
    N = _ask(f"  {obj_name}数量 N", lambda x: int(x) if int(x) > 0 else (_ for _ in ()).throw(ValueError("必须>0")))
    T = _ask(f"  {slot_name}数量 T", lambda x: int(x) if int(x) > 0 else (_ for _ in ()).throw(ValueError("必须>0")))
    K = _ask(f"  {opt_name}数量 K", lambda x: int(x) if int(x) > 0 else (_ for _ in ()).throw(ValueError("必须>0")))

    print(f"\n  请输入 {K} 个{opt_name}的比例（空格/冒号/逗号分隔，例：7 8 10 3 5）")
    ratios_raw = _ask(f"  比例", default=" ".join(["1"] * K))
    nums = re.findall(r"\d+\.?\d*", ratios_raw)
    if len(nums) != K:
        print(f"  ⚠️  识别到 {len(nums)} 个数，期望 {K} 个，将使用等比例 1:1:…:1")
        ratios = [1.0] * K
    else:
        ratios = [float(x) for x in nums]

    return {"N": N, "T": T, "K": K, "ratios": ratios}


# ─────────────────────────────────────────────
# 输出：Markdown 表格
# ─────────────────────────────────────────────

def write_markdown(
    results: list[dict],
    stats: dict,
    params: dict,
    outpath: Path,
    labels: dict | None = None,
) -> None:
    if labels is None:
        labels = {}
    obj_name  = labels.get("obj",    "对象")
    slot_name = labels.get("slot",   "轮次")
    opt_name  = labels.get("option", "选项")

    T = params["T"]
    K = params["K"]

    lines = []
    lines.append(f"# 均匀轮转分配结果\n")
    lines.append(f"- **{obj_name}总数 N**：{params['N']}")
    lines.append(f"- **{slot_name}数 T**：{T}")
    lines.append(f"- **{opt_name}数 K**：{K}")
    lines.append(f"- **比例**：{params['ratios']}")
    lines.append(f"- **平均覆盖率**：{stats['avg_coverage']:.1%}")
    lines.append(f"- **全覆盖{obj_name}数**：{stats['full_coverage']} / {params['N']}")
    lines.append("")

    # 分配明细表
    header = f"| {obj_name}ID |"
    for t in range(T):
        header += f" {slot_name}{t+1} |"
    header += " 覆盖率 |"
    lines.append(header)

    sep = "|------|" + " ------|" * T + " ------|"
    lines.append(sep)

    for obj in results:
        row = f"| {obj['id']:>4} |"
        for opt in obj["slots"]:
            row += f" {opt_name}{opt} |"
        row += f" {obj['coverage']:.1%} |"
        lines.append(row)

    lines.append("")
    lines.append("## 各轮次分布统计\n")

    stat_header = f"| {slot_name} |"
    for k in range(1, K + 1):
        stat_header += f" {opt_name}{k} |"
    lines.append(stat_header)
    lines.append("|------|" + " ------|" * K)

    for t in range(T):
        row = f"| {slot_name}{t+1} |"
        for k in range(1, K + 1):
            cnt = stats["period_dist"][t].get(k, 0)
            row += f" {cnt} |"
        lines.append(row)

    outpath.write_text("\n".join(lines), encoding="utf-8")
    print(f"  📄 Markdown → {outpath}")


# ─────────────────────────────────────────────
# 输出：CSV
# ─────────────────────────────────────────────

def write_csv(
    results: list[dict],
    params: dict,
    outpath: Path,
    labels: dict | None = None,
) -> None:
    if labels is None:
        labels = {}
    obj_name  = labels.get("obj",    "对象")
    slot_name = labels.get("slot",   "轮次")

    T = params["T"]
    with outpath.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [f"{obj_name}ID"] + [f"{slot_name}{t+1}" for t in range(T)] + ["覆盖率"]
        )
        for obj in results:
            writer.writerow(
                [obj["id"]] + obj["slots"] + [f"{obj['coverage']:.1%}"]
            )
    print(f"  📊 CSV    → {outpath}")


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="均匀轮转分配工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input",  "-i", help="一行统计描述（自动解析）", default=None)
    parser.add_argument("--outdir", "-o", help="输出目录（默认当前目录）", default=".")
    parser.add_argument("--obj",    help="对象术语（默认：对象）",  default=None)
    parser.add_argument("--slot",   help="轮次术语（默认：轮次）",  default=None)
    parser.add_argument("--option", help="选项术语（默认：选项）",  default=None)
    parser.add_argument("--no-html", action="store_true", help="不生成 HTML")
    parser.add_argument("--no-open", action="store_true", help="生成后不自动打开浏览器")
    args = parser.parse_args()

    labels: dict = {}
    if args.obj:    labels["obj"]    = args.obj
    if args.slot:   labels["slot"]   = args.slot
    if args.option: labels["option"] = args.option

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ── 获取参数 ──
    if args.input:
        params = parse_one_line(args.input)
        if not params:
            print(f"⚠️  无法解析输入：{args.input!r}")
            print("   请尝试格式：\"33个项目，4个周期，5个方案，比例7:8:10:3:5\"")
            sys.exit(1)
        print(f"✅ 解析结果：N={params['N']}  T={params['T']}  K={params['K']}  ratios={params['ratios']}")
    else:
        params = interactive_input(labels)

    print()
    print("  ⏳ 正在计算分配方案……")

    # ── 执行分配 ──
    results = allocate(params["N"], params["T"], params["K"], params["ratios"])
    stats   = compute_stats(results, params["T"], params["K"])

    print(f"  ✅ 分配完成：平均覆盖率 {stats['avg_coverage']:.1%}，"
          f"全覆盖 {stats['full_coverage']}/{params['N']} 个对象")
    print()

    # ── 输出文件 ──
    md_path  = outdir / "allocation_result.md"
    csv_path = outdir / "allocation_result.csv"
    html_path = outdir / "allocation_result.html"

    write_markdown(results, stats, params, md_path,  labels)
    write_csv(results, params, csv_path, labels)

    if not args.no_html:
        render_html(results, stats, params, html_path, labels)

    print()
    print(f"  🎉 全部完成！输出目录：{outdir.resolve()}")

    # 自动打开 HTML
    if not args.no_html and not args.no_open:
        try:
            import webbrowser
            webbrowser.open(html_path.resolve().as_uri())
            print(f"  🌐 已在浏览器中打开可视化报告")
        except Exception:
            print(f"  💡 请手动打开：{html_path.resolve()}")


if __name__ == "__main__":
    main()
