#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
authorization_manager.py v1.0.0
授权管理器：支持统一审批（中高风险）和即时审批（高风险操作前）。

工作流程：
1. 请求授权（统一/即时）
2. 检查是否已授权
3. 记录授权决定

统一审批：中高风险操作，批量展示风险列表，用户一次性审批
即时审批：高风险操作执行前，单独请求用户确认

存储：~/.workbuddy/skills/.standardization/skill-standardization/auth_decisions.json
"""

import os
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ── 常量定义 ────────────────────────────────────────────────────────────────────

AUTH_DECISIONS_FILE = (
    Path.home()
    / ".workbuddy/skills/.standardization/skill-standardization/auth_decisions.json"
)

RISK_LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class AuthorizationManager:
    """
    授权管理器主类。

    管理 skill 执行过程中的授权请求和决策记录。
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化授权管理器。

        Args:
            storage_dir: 授权决定存储目录（默认 ~/.workbuddy/skills/.standardization/skill-standardization/）
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = AUTH_DECISIONS_FILE.parent
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.auth_file = self.storage_dir / "auth_decisions.json"
        self._ensure_auth_file()

    # ── 公共接口 ────────────────────────────────────────────────────────────────

    def request_authorization(
        self,
        skill_name: str,
        risk_level: str,
        operations: List[Dict],
        mode: str = "unified",
    ) -> Dict:
        """
        请求用户授权。

        Args:
            skill_name: skill 名称
            risk_level: 风险等级（low/medium/high/critical）
            operations: 待授权操作列表，每项含 {type, file, description, severity}
            mode: 授权模式（unified=统一审批, immediate=即时审批）

        Returns:
            dict: {approved: bool, decision_id: str, message: str}
        """
        decision_id = self._generate_decision_id(skill_name)
        timestamp = datetime.now().isoformat()

        # 构建授权请求
        request = {
            "decision_id": decision_id,
            "skill_name": skill_name,
            "risk_level": risk_level,
            "operations": operations,
            "mode": mode,
            "timestamp": timestamp,
            "status": "pending",  # pending/approved/rejected
            "user_response": None,
            "response_timestamp": None,
        }

        # 保存请求
        self._save_request(request)

        # 生成用户提示
        message = self._format_authorization_request(request)

        return {
            "approved": False,  # 初始为未授权
            "decision_id": decision_id,
            "message": message,
            "prompt": self._generate_user_prompt(request),
        }

    def check_authorization(self, decision_id: str) -> Dict:
        """
        检查授权状态。

        Args:
            decision_id: 授权决定 ID

        Returns:
            dict: {authorized: bool, status: str, message: str}
        """
        requests = self._load_requests()
        target = None

        for req in requests:
            if req["decision_id"] == decision_id:
                target = req
                break

        if not target:
            return {
                "authorized": False,
                "status": "not_found",
                "message": f"授权请求不存在: {decision_id}",
            }

        status_map = {
            "approved": True,
            "rejected": False,
            "pending": False,
        }

        return {
            "authorized": status_map.get(target["status"], False),
            "status": target["status"],
            "message": f"授权状态: {target['status']}",
            "response": target.get("user_response"),
        }

    def record_decision(self, decision_id: str, approved: bool, note: str = "") -> Dict:
        """
        记录用户授权决定。

        Args:
            decision_id: 授权决定 ID
            approved: 是否批准
            note: 用户备注

        Returns:
            dict: {success: bool, message: str}
        """
        requests = self._load_requests()
        target = None

        for req in requests:
            if req["decision_id"] == decision_id:
                target = req
                break

        if not target:
            return {"success": False, "message": f"授权请求不存在: {decision_id}"}

        # 更新状态
        target["status"] = "approved" if approved else "rejected"
        target["user_response"] = "approved" if approved else "rejected"
        target["response_timestamp"] = datetime.now().isoformat()
        target["user_note"] = note

        # 保存
        self._save_requests(requests)

        action = "批准" if approved else "拒绝"
        return {
            "success": True,
            "message": f"已记录授权决定: {action} (decision_id={decision_id})",
        }

    def batch_approve(
        self, skill_name: str, decision_ids: List[str], note: str = ""
    ) -> Dict:
        """
        批量批准授权请求（统一审批模式）。

        Args:
            skill_name: skill 名称
            decision_ids: 要批准的授权 ID 列表
            note: 用户备注

        Returns:
            dict: {success: bool, approved_count: int, message: str}
        """
        requests = self._load_requests()
        approved_count = 0

        for req in requests:
            if (
                req["skill_name"] == skill_name
                and req["decision_id"] in decision_ids
                and req["status"] == "pending"
            ):
                req["status"] = "approved"
                req["user_response"] = "approved"
                req["response_timestamp"] = datetime.now().isoformat()
                req["user_note"] = note
                approved_count += 1

        self._save_requests(requests)

        return {
            "success": True,
            "approved_count": approved_count,
            "message": f"已批量批准 {approved_count} 个授权请求",
        }

    def get_pending_requests(self, skill_name: Optional[str] = None) -> List[Dict]:
        """
        获取待审批的授权请求。

        Args:
            skill_name: 按 skill 名称过滤（可选）

        Returns:
            list: 待审批请求列表
        """
        requests = self._load_requests()
        pending = [req for req in requests if req["status"] == "pending"]

        if skill_name:
            pending = [req for req in pending if req["skill_name"] == skill_name]

        return pending

    def clear_decisions(self, older_than_days: int = 7) -> Dict:
        """
        清理过期的授权决定。

        Args:
            older_than_days: 保留最近 N 天的记录

        Returns:
            dict: {success: bool, removed_count: int, message: str}
        """
        requests = self._load_requests()
        cutoff = datetime.now().timestamp() - (older_than_days * 86400)

        filtered = []
        removed_count = 0

        for req in requests:
            req_time = datetime.fromisoformat(req["timestamp"]).timestamp()
            if req_time < cutoff:
                removed_count += 1
            else:
                filtered.append(req)

        self._save_requests(filtered)

        return {
            "success": True,
            "removed_count": removed_count,
            "message": f"已清理 {removed_count} 条过期授权记录",
        }

    # ── 内部方法：文件操作 ────────────────────────────────────────────────────

    def _ensure_auth_file(self) -> None:
        """确保授权决定文件存在。"""
        if not self.auth_file.exists():
            self._save_requests([])

    def _load_requests(self) -> List[Dict]:
        """加载所有授权请求。"""
        try:
            with open(self.auth_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_requests(self, requests: List[Dict]) -> None:
        """保存授权请求列表。"""
        with open(self.auth_file, "w", encoding="utf-8") as f:
            json.dump(requests, f, indent=2, ensure_ascii=False)

    def _save_request(self, request: Dict) -> None:
        """保存单个授权请求（追加）。"""
        requests = self._load_requests()
        requests.append(request)
        self._save_requests(requests)

    # ── 内部方法：辅助函数 ────────────────────────────────────────────────────

    def _generate_decision_id(self, skill_name: str) -> str:
        """生成授权决定 ID。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{skill_name}_{timestamp}"

    def _format_authorization_request(self, request: Dict) -> str:
        """
        格式化授权请求为用户可读的文本。

        Args:
            request: 授权请求字典

        Returns:
            str: 格式化的授权请求文本
        """
        lines = [
            "=" * 60,
            f"🔐 授权请求 (模式: {request['mode']})",
            "=" * 60,
            f"Skill: {request['skill_name']}",
            f"风险等级: {request['risk_level'].upper()}",
            f"操作数量: {len(request['operations'])}",
            "",
            "待授权操作列表：",
        ]

        for i, op in enumerate(request["operations"], 1):
            severity = op.get("severity", "UNKNOWN")
            lines.append(
                f"  {i}. [{severity}] {op.get('description', '未知操作')}"
            )
            if "file" in op:
                lines.append(f"     文件: {op['file']}")
            if "pattern" in op:
                lines.append(f"     模式: {op['pattern']}")

        lines += [
            "",
            "-" * 60,
            "请审批：",
            "  ✅ 输入 'y' 或 'yes' 批准",
            "  ❌ 输入 'n' 或 'no' 拒绝",
            "  📝 输入 'note: <备注>' 添加备注",
            "-" * 60,
        ]

        return "\n".join(lines)

    def _generate_user_prompt(self, request: Dict) -> str:
        """
        生成用户提示（用于 AI 向用户展示）。

        Args:
            request: 授权请求字典

        Returns:
            str: 用户提示文本
        """
        risk_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴",
            "critical": "⚫",
        }
        emoji = risk_emoji.get(request["risk_level"], "⚪")

        prompt = [
            f"{emoji} **授权请求** (skill: {request['skill_name']})",
            "",
            f"风险等级: **{request['risk_level'].upper()}**",
            f"待执行操作: {len(request['operations'])} 项",
            "",
        ]

        if request["mode"] == "unified":
            prompt.append("**统一审批模式**: 请一次性审批以下所有操作：")
        else:
            prompt.append("**即时审批模式**: 请在执行前确认此项操作：")

        prompt.append("")

        for i, op in enumerate(request["operations"][:5], 1):  # 最多显示 5 项
            severity = op.get("severity", "UNKNOWN")
            prompt.append(
                f"{i}. `[{severity}]` {op.get('description', '未知操作')}"
            )

        if len(request["operations"]) > 5:
            prompt.append(f"... 还有 {len(request['operations']) - 5} 项操作")

        prompt += [
            "",
            "**是否批准？** (y/n)",
        ]

        return "\n".join(prompt)


# ── CLI 入口 ─────────────────────────────────────────────────────────────────────

def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="授权管理器：统一审批（中高风险）+ 即时审批（高风险操作前）"
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # request 子命令：请求授权
    req_parser = subparsers.add_parser("request", help="请求授权")
    req_parser.add_argument("--skill-name", required=True, help="skill 名称")
    req_parser.add_argument(
        "--risk-level",
        required=True,
        choices=["low", "medium", "high", "critical"],
        help="风险等级",
    )
    req_parser.add_argument(
        "--operations", required=True, help="待授权操作列表（JSON 字符串）"
    )
    req_parser.add_argument(
        "--type",
        choices=["unified", "immediate"],
        default="unified",
        help="授权模式（unified=统一审批, immediate=即时审批）",
    )
    req_parser.add_argument("--output", "-o", help="输出 JSON 结果到文件")

    # check 子命令：检查授权状态
    check_parser = subparsers.add_parser("check", help="检查授权状态")
    check_parser.add_argument("--decision-id", required=True, help="授权决定 ID")
    check_parser.add_argument("--output", "-o", help="输出 JSON 结果到文件")

    # record 子命令：记录授权决定
    record_parser = subparsers.add_parser("record", help="记录授权决定")
    record_parser.add_argument("--decision-id", required=True, help="授权决定 ID")
    record_parser.add_argument(
        "--approved",
        type=lambda x: x.lower() == "true",
        required=True,
        help="是否批准（true/false）",
    )
    record_parser.add_argument("--note", default="", help="用户备注")

    # batch-approve 子命令：批量批准
    batch_parser = subparsers.add_parser("batch-approve", help="批量批准授权请求")
    batch_parser.add_argument("--skill-name", required=True, help="skill 名称")
    batch_parser.add_argument(
        "--decision-ids", required=True, nargs="+", help="要批准的授权 ID 列表"
    )
    batch_parser.add_argument("--note", default="", help="用户备注")

    # pending 子命令：查看待审批请求
    pending_parser = subparsers.add_parser("pending", help="查看待审批请求")
    pending_parser.add_argument("--skill-name", help="按 skill 名称过滤")

    # clear 子命令：清理过期记录
    clear_parser = subparsers.add_parser("clear", help="清理过期授权记录")
    clear_parser.add_argument(
        "--older-than-days", type=int, default=7, help="保留最近 N 天的记录"
    )

    args = parser.parse_args()

    # 执行命令
    mgr = AuthorizationManager()

    if args.command == "request":
        operations = json.loads(args.operations)
        result = mgr.request_authorization(
            skill_name=args.skill_name,
            risk_level=args.risk_level,
            operations=operations,
            mode=args.type,
        )
        _output_result(result, args.output)

    elif args.command == "check":
        result = mgr.check_authorization(decision_id=args.decision_id)
        _output_result(result, args.output)

    elif args.command == "record":
        result = mgr.record_decision(
            decision_id=args.decision_id,
            approved=args.approved,
            note=args.note,
        )
        _output_result(result, args.output)

    elif args.command == "batch-approve":
        result = mgr.batch_approve(
            skill_name=args.skill_name,
            decision_ids=args.decision_ids,
            note=args.note,
        )
        _output_result(result, args.output)

    elif args.command == "pending":
        result = mgr.get_pending_requests(skill_name=args.skill_name)
        _output_result({"pending_count": len(result), "requests": result}, args.output)

    elif args.command == "clear":
        result = mgr.clear_decisions(older_than_days=args.older_than_days)
        _output_result(result, args.output)

    else:
        parser.print_help()
        sys.exit(1)


def _output_result(result: Dict, output_file: Optional[str]) -> None:
    """输出结果（JSON 格式）。"""
    json_str = json.dumps(result, indent=2, ensure_ascii=False)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"[*] 结果已保存: {output_file}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
