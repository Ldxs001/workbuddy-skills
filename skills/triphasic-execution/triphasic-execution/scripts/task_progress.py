#!/usr/bin/env python3
"""
task_progress.py - Triphasic Execution 临时进度文件管理器 (v5.6)

功能：
  init    -- 初始化进度文件（任务规划后调用）
  update  -- 更新步骤状态（每步 Execute→Review→Advance 后调用）
  resume  -- 恢复中断任务（读取进度文件，输出恢复信息）
  list    -- 列出所有活跃任务
  abort   -- 手动中止任务（标记为已中止）
  clean   -- 清理已完成的进度文件

使用：
  python task_progress.py init --task "任务名称" --plan "规划内容"
  python task_progress.py update --task "任务名称" --step 1 --status "success" --review "审查结论" --advance "推进决策"
  python task_progress.py resume --task "任务名称"
  python task_progress.py list
  python task_progress.py abort --task "任务名称"
  python task_progress.py complete --task "任务名称"
"""

import argparse
import json
import os
import sys
import glob
from datetime import datetime, timezone
from pathlib import Path

# 默认数据目录
DEFAULT_HOME = os.path.join(os.path.expanduser("~"), ".workbuddy", "triphasic")
ACTIVE_TASKS_DIR = ".active_tasks"


def get_home():
    """获取数据目录路径"""
    home = os.environ.get("TRIPHASIC_HOME", DEFAULT_HOME)
    return home


def get_active_dir():
    """获取活跃任务目录路径"""
    return os.path.join(get_home(), ACTIVE_TASKS_DIR)


def ensure_dirs():
    """确保必要目录存在"""
    active_dir = get_active_dir()
    os.makedirs(active_dir, exist_ok=True)


def find_task_file(task_name):
    """根据任务名称查找进度文件（支持模糊匹配）"""
    active_dir = get_active_dir()
    # 精确匹配
    pattern = os.path.join(active_dir, f"{task_name}_*.json")
    files = glob.glob(pattern)
    if files:
        # 返回最新的
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        return files[0]

    # 模糊匹配（任务名包含）
    for f in glob.glob(os.path.join(active_dir, "*.json")):
        fname = os.path.basename(f)
        if task_name.lower() in fname.lower().rsplit("_", 1)[0].lower():
            return f

    return None


def cmd_init(args):
    """初始化进度文件"""
    ensure_dirs()

    task_name = args.task
    plan_content = args.plan
    steps_json = args.steps  # JSON string: list of step descriptions

    if not task_name:
        print("错误: 必须指定 --task 参数")
        sys.exit(1)

    # 生成文件名: task_name_timestamp.json
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = task_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    filename = f"{safe_name}_{ts}.json"
    filepath = os.path.join(get_active_dir(), filename)

    # 构建进度数据
    steps = []
    if steps_json:
        try:
            steps_data = json.loads(steps_json)
            for i, s in enumerate(steps_data, 1):
                step = {
                    "index": i,
                    "description": s.get("description", ""),
                    "purpose": s.get("purpose", ""),
                    "tool": s.get("tool", ""),
                    "status": "pending",  # pending/running/success/failed/skipped
                    "retries": 0,
                    "review": "",
                    "advance": "",
                    "started_at": "",
                    "completed_at": "",
                    "error_detail": ""
                }
                steps.append(step)
        except json.JSONDecodeError as e:
            print(f"错误: --steps 参数 JSON 格式无效: {e}")
            sys.exit(1)

    data = {
        "task_name": task_name,
        "plan": plan_content or "",
        "status": "active",  # active/completed/aborted
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "total_steps": len(steps),
        "completed_steps": 0,
        "steps": steps,
        "context": {
            "workspace": os.getcwd(),
            "purpose": args.purpose or "",
            "requirements": args.requirements or "",
            "risks": args.risks or ""
        }
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"进度文件已创建: {filename}")
    print(f"任务: {task_name}")
    print(f"步骤数: {len(steps)}")
    print(f"文件路径: {filepath}")
    return filepath


def cmd_update(args):
    """更新步骤状态"""
    task_name = args.task
    step_idx = args.step

    filepath = find_task_file(task_name)
    if not filepath:
        print(f"错误: 未找到任务 '{task_name}' 的进度文件")
        print("提示: 使用 list 命令查看活跃任务")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data["status"] != "active":
        print(f"错误: 任务状态为 '{data['status']}'，不可更新")
        sys.exit(1)

    # 查找步骤
    step_found = None
    for s in data["steps"]:
        if s["index"] == step_idx:
            step_found = s
            break

    if not step_found:
        print(f"错误: 未找到步骤 {step_idx}")
        print(f"可用步骤: {[s['index'] for s in data['steps']]}")
        sys.exit(1)

    # 更新状态
    status_map = {
        "pending": "pending",
        "running": "running",
        "success": "success",
        "failed": "failed",
        "skipped": "skipped"
    }

    new_status = status_map.get(args.status.lower(), args.status.lower())
    step_found["status"] = new_status
    step_found["review"] = args.review or ""
    step_found["advance"] = args.advance or ""
    step_found["error_detail"] = args.error or ""

    if new_status == "running":
        step_found["started_at"] = datetime.now().isoformat()
    elif new_status in ("success", "failed", "skipped"):
        step_found["completed_at"] = datetime.now().isoformat()
        if new_status == "failed":
            step_found["retries"] += 1

    # 重新计算完成数
    data["completed_steps"] = sum(
        1 for s in data["steps"] if s["status"] in ("success", "skipped")
    )
    data["updated_at"] = datetime.now().isoformat()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 输出当前进度表
    _print_progress_table(data)
    print(f"\n文件已更新: {os.path.basename(filepath)}")
    return filepath


def cmd_resume(args):
    """恢复中断任务"""
    task_name = args.task
    filepath = find_task_file(task_name)

    if not filepath:
        print(f"错误: 未找到任务 '{task_name}' 的进度文件")
        print("提示: 使用 list 命令查看活跃任务")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n{'='*60}")
    print(f"任务恢复信息")
    print(f"{'='*60}")
    print(f"任务名称: {data['task_name']}")
    print(f"创建时间: {data['created_at']}")
    print(f"最后更新: {data['updated_at']}")
    print(f"当前状态: {data['status']}")

    if data["context"]["purpose"]:
        print(f"任务目的: {data['context']['purpose']}")
    if data["context"]["requirements"]:
        print(f"具体要求: {data['context']['requirements']}")
    if data["context"]["risks"]:
        print(f"潜在风险: {data['context']['risks']}")

    print(f"\n{data['plan']}")

    # 输出进度表
    _print_progress_table(data)

    # 找到需要恢复的步骤
    next_step = None
    failed_steps = [s for s in data["steps"] if s["status"] == "failed"]
    pending_steps = [s for s in data["steps"] if s["status"] == "pending"]

    if failed_steps:
        next_step = failed_steps[0]
        print(f"\n[恢复建议] 步骤 {next_step['index']} 上次失败，建议重试")
        print(f"  失败原因: {next_step['review']}")
        print(f"  重试次数: {next_step['retries']}")
        if next_step['error_detail']:
            print(f"  错误详情: {next_step['error_detail']}")
    elif pending_steps:
        next_step = pending_steps[0]
        print(f"\n[恢复建议] 从步骤 {next_step['index']} 继续")
        print(f"  步骤描述: {next_step['description']}")
        if next_step['purpose']:
            print(f"  任务目的: {next_step['purpose']}")
    else:
        print(f"\n[状态] 所有步骤已完成或跳过")

    print(f"\n工作目录: {data['context'].get('workspace', os.getcwd())}")
    print(f"{'='*60}")
    return data


def cmd_list(args):
    """列出所有活跃任务"""
    ensure_dirs()
    active_dir = get_active_dir()

    files = glob.glob(os.path.join(active_dir, "*.json"))
    if not files:
        print("当前没有活跃任务")
        return

    # 按更新时间排序
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    print(f"\n活跃任务列表 ({len(files)} 个):\n")
    print(f"{'序号':<4} {'任务名称':<30} {'状态':<10} {'进度':<12} {'最后更新':<20}")
    print(f"{'─'*4} {'─'*30} {'─'*10} {'─'*12} {'─'*20}")

    for i, filepath in enumerate(files, 1):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            name = data.get("task_name", os.path.basename(filepath))
            status = data.get("status", "unknown")
            total = data.get("total_steps", 0)
            completed = data.get("completed_steps", 0)
            updated = data.get("updated_at", "")

            status_icon = {"active": "🟢", "completed": "✅", "aborted": "🔴"}.get(status, "❓")
            progress = f"{completed}/{total}" if total > 0 else "N/A"

            # 截断名称
            if len(name) > 28:
                name = name[:26] + ".."

            print(f"{i:<4} {name:<30} {status_icon:<2} {status:<8} {progress:<12} {updated[:19]:<20}")
        except (json.JSONDecodeError, KeyError):
            fname = os.path.basename(filepath)
            print(f"{i:<4} {fname:<30} {'❓':<2} {'invalid':<8} {'-':<12} {'-':<20}")

    print()


def cmd_complete(args):
    """标记任务完成并删除进度文件"""
    task_name = args.task
    filepath = find_task_file(task_name)

    if not filepath:
        print(f"错误: 未找到任务 '{task_name}' 的进度文件")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 验证所有步骤是否完成
    incomplete = [s for s in data["steps"] if s["status"] not in ("success", "skipped")]
    if incomplete and not args.force:
        print(f"警告: 以下步骤尚未完成:")
        for s in incomplete:
            print(f"  步骤 {s['index']}: {s['description']} [{s['status']}]")
        print(f"\n使用 --force 强制完成并删除进度文件")
        sys.exit(1)

    if not args.keep:
        os.remove(filepath)
        print(f"任务 '{task_name}' 已完成，进度文件已删除")
    else:
        data["status"] = "completed"
        data["updated_at"] = datetime.now().isoformat()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"任务 '{task_name}' 已标记为完成（进度文件保留）")

    print(f"完成步骤: {data['completed_steps']}/{data['total_steps']}")
    if data.get("context", {}).get("purpose"):
        print(f"任务目的: {data['context']['purpose']}")


def cmd_abort(args):
    """中止任务"""
    task_name = args.task
    filepath = find_task_file(task_name)

    if not filepath:
        print(f"错误: 未找到任务 '{task_name}' 的进度文件")
        sys.exit(1)

    data = json.load(open(filepath, "r", encoding="utf-8"))
    data["status"] = "aborted"
    data["updated_at"] = datetime.now().isoformat()
    data["abort_reason"] = args.reason or "用户手动中止"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"任务 '{task_name}' 已中止")
    if args.reason:
        print(f"中止原因: {args.reason}")
    print(f"进度文件已保留: {os.path.basename(filepath)}")


def cmd_clean(args):
    """清理已完成/中止的进度文件"""
    active_dir = get_active_dir()
    files = glob.glob(os.path.join(active_dir, "*.json"))

    if not files:
        print("没有需要清理的进度文件")
        return

    removed = 0
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("status") in ("completed", "aborted"):
                os.remove(filepath)
                removed += 1
                print(f"已清理: {os.path.basename(filepath)}")
        except (json.JSONDecodeError, KeyError):
            # 损坏的文件也清理
            os.remove(filepath)
            removed += 1
            print(f"已清理(损坏): {os.path.basename(filepath)}")

    if removed == 0:
        print("没有已完成或中止的任务需要清理")
    else:
        print(f"\n共清理 {removed} 个进度文件")


def _print_progress_table(data):
    """打印进度追踪表"""
    steps = data.get("steps", [])
    if not steps:
        return

    total = data.get("total_steps", len(steps))
    completed = data.get("completed_steps", 0)
    pct = int(completed / total * 100) if total > 0 else 0

    status_map = {
        "pending": "⏳",
        "running": "🔄",
        "success": "✅",
        "failed": "❌",
        "skipped": "⏭️"
    }

    # ASCII 表格
    print(f"\n  ┌──────┬────────┬────────┬────────────┬────────────┐")
    print(f"  │ {'步骤':^4} │ {'状态':^6} │ {'重试':^6} │ {'审查结论':^10} │ {'推进决策':^10} │")
    print(f"  ├──────┼────────┼────────┼────────────┼────────────┤")

    for s in steps:
        icon = status_map.get(s["status"], "❓")
        retry = f"{s['retries']}" if s['retries'] > 0 else "-"
        review = s.get("review", "") or "-"
        advance = s.get("advance", "") or "-"
        # 截断
        if len(review) > 8:
            review = review[:7] + ".."
        if len(advance) > 8:
            advance = advance[:7] + ".."
        print(f"  │  {s['index']:<3} │  {icon}    │  {retry:<4} │ {review:^12} │ {advance:^12} │")

    print(f"  └──────┴────────┴────────┴────────────┴────────────┘")

    # 找当前步骤
    current = None
    for s in steps:
        if s["status"] in ("running", "failed", "pending"):
            current = s["index"]
            break

    next_info = f"▸ 当前：步骤{current}" if current else "▸ 全部完成"
    print(f"  进度：{completed}/{total}（{pct}%）{next_info}")


def main():
    parser = argparse.ArgumentParser(
        description="Triphasic Execution 临时进度文件管理器 (v5.6)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 初始化进度文件
  python task_progress.py init --task "修复登录Bug" --purpose "修复Token验证缺失" \\
    --steps '[{"description":"读取代码","purpose":"理解逻辑","tool":"Read"},{"description":"修复代码","purpose":"添加验证","tool":"Edit"}]'

  # 更新步骤状态
  python task_progress.py update --task "修复登录Bug" --step 1 --status success --review "代码已读取" --advance "继续步骤2"
  python task_progress.py update --task "修复登录Bug" --step 2 --status failed --review "语法错误" --advance "重试" --error "第45行缺少冒号"

  # 恢复中断任务
  python task_progress.py resume --task "修复登录Bug"

  # 列出活跃任务
  python task_progress.py list

  # 完成任务并删除进度文件
  python task_progress.py complete --task "修复登录Bug"

  # 中止任务
  python task_progress.py abort --task "修复登录Bug" --reason "用户取消"

  # 清理已完成任务
  python task_progress.py clean
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init
    p_init = subparsers.add_parser("init", help="初始化进度文件")
    p_init.add_argument("--task", "-t", required=True, help="任务名称")
    p_init.add_argument("--plan", "-p", default="", help="规划内容（文本）")
    p_init.add_argument("--steps", "-s", default="[]", help="步骤列表（JSON数组）")
    p_init.add_argument("--purpose", help="任务目的")
    p_init.add_argument("--requirements", "-r", help="具体要求")
    p_init.add_argument("--risks", help="潜在风险")
    p_init.add_argument("--home", help="数据目录（覆盖 TRIPHASIC_HOME）")

    # update
    p_update = subparsers.add_parser("update", help="更新步骤状态")
    p_update.add_argument("--task", "-t", required=True, help="任务名称")
    p_update.add_argument("--step", type=int, required=True, help="步骤编号")
    p_update.add_argument("--status", required=True, choices=["pending", "running", "success", "failed", "skipped"], help="新状态")
    p_update.add_argument("--review", help="审查结论")
    p_update.add_argument("--advance", help="推进决策")
    p_update.add_argument("--error", help="错误详情")
    p_update.add_argument("--home", help="数据目录（覆盖 TRIPHASIC_HOME）")

    # resume
    p_resume = subparsers.add_parser("resume", help="恢复中断任务")
    p_resume.add_argument("--task", "-t", required=True, help="任务名称")
    p_resume.add_argument("--home", help="数据目录（覆盖 TRIPHASIC_HOME）")

    # list
    p_list = subparsers.add_parser("list", help="列出活跃任务")
    p_list.add_argument("--home", help="数据目录（覆盖 TRIPHASIC_HOME）")

    # complete
    p_complete = subparsers.add_parser("complete", help="完成任务")
    p_complete.add_argument("--task", "-t", required=True, help="任务名称")
    p_complete.add_argument("--force", "-f", action="store_true", help="强制完成（即使有未完成步骤）")
    p_complete.add_argument("--keep", "-k", action="store_true", help="保留进度文件")
    p_complete.add_argument("--home", help="数据目录（覆盖 TRIPHASIC_HOME）")

    # abort
    p_abort = subparsers.add_parser("abort", help="中止任务")
    p_abort.add_argument("--task", "-t", required=True, help="任务名称")
    p_abort.add_argument("--reason", help="中止原因")
    p_abort.add_argument("--home", help="数据目录（覆盖 TRIPHASIC_HOME）")

    # clean
    p_clean = subparsers.add_parser("clean", help="清理已完成任务")
    p_clean.add_argument("--home", help="数据目录（覆盖 TRIPHASIC_HOME）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 覆盖数据目录
    if hasattr(args, "home") and args.home:
        os.environ["TRIPHASIC_HOME"] = args.home

    # 命令映射
    cmd_map = {
        "init": cmd_init,
        "update": cmd_update,
        "resume": cmd_resume,
        "list": cmd_list,
        "complete": cmd_complete,
        "abort": cmd_abort,
        "clean": cmd_clean,
    }

    cmd_func = cmd_map.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
