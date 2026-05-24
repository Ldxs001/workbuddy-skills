#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
permission_checker.py v1.0.0
权限检查器：扫描 skill 脚本，提取文件操作，计算权限权重，生成风险报告。

检查维度：
1. 敏感信息访问（memory/、credentials、token、password）
2. 关键位置写入（skills/、.workbuddy/、系统目录）
3. 网络访问（requests、urllib、httpx、curl）
4. 文件删除（os.remove、os.rmdir、shutil.rmtree、del、rm）
5. Subprocess 调用（os.system、subprocess、popen）

权重模型：
- 敏感信息访问：40%
- 关键位置写入：30%
- 网络访问：20%
- 文件删除：10%
- Subprocess 调用：+20% 额外加权

输出：JSON 格式风险报告 + 权限权重评分
"""

import os
import re
import json
import sys
import ast
import tokenize
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

# ── 常量定义 ────────────────────────────────────────────────────────────────────

SENSITIVE_PATTERNS = [
    # 记忆文件路径（路径级，需单词边界或路径分隔符）
    r"\bmemory/", r"\.workbuddy/memory", r"\bMEMORY\.md\b", r"\b\d{4}-\d{2}-\d{2}\.md\b",
    # 凭证相关（加单词边界，避免匹配关键词列表）
    r"\bcredential\w*\b", r"\bpasswd\b", r"\bsecret\b", r"\bapi[_-]?key\b",
    r"\btoken\w*\b", r"\baccess[_-]?token\b", r"\bprivate[_-]?key\b",
    # 环境变量敏感词（精确匹配环境变量名）
    r"\bOPENAI_API_KEY\b", r"\bANTHROPIC_API_KEY\b", r"\bGITHUB_TOKEN\b", r"\bAWS_\w+\b",
]

CRITICAL_PATH_PATTERNS = [
    # 技能目录
    r"skills/", r"\.workbuddy/skills",
    # 系统配置目录
    r"\.workbuddy/", r"\.config/", r"\.ssh/", r"AppData",
    # 根目录写入
    r"/$", r"^[A-Za-z]:[\\/]$",  # 根目录
    r"C:\\\\", r"/usr/", r"/etc/", r"/var/",
]

NETWORK_PATTERNS = [
    r"import requests", r"from requests", r"urllib", r"httpx",
    r"curl", r"wget", r"fetch\(", r"XMLHttpRequest",
    r"axios", r"http\.get", r"http\.post", r"websocket",
]

DELETE_PATTERNS = [
    r"os\.remove", r"os\.rmdir", r"shutil\.rmtree",
    r"\bos\.unlink\b", r"\brm\b", r"\brmdir\b",
    r"fs\.unlink", r"fs\.rmdir", r"fs\.rm",
]

SUBPROCESS_PATTERNS = [
    r"os\.system", r"subprocess", r"popen", r"popen2",
    r"exec\(", r"eval\(", r"Runtime\.getRuntime", r"ProcessBuilder",
]

# ── 权限权重配置 ────────────────────────────────────────────────────────────────

WEIGHT_CONFIG = {
    "sensitive_access": 0.40,    # 敏感信息访问 40%
    "critical_write": 0.30,       # 关键位置写入 30%
    "network_access": 0.20,       # 网络访问 20%
    "file_delete": 0.10,          # 文件删除 10%
    "subprocess_call": 0.20,      # Subprocess 调用 +20% 额外加权
}

# ── 风险等级阈值 ─────────────────────────────────────────────────────────────────

RISK_THRESHOLD = {
    "low": 0.0,
    "medium": 0.30,    # ≥ 30% 中风险
    "high": 0.60,      # ≥ 60% 高风险
    "critical": 0.80,  # ≥ 80% 严重风险
}


class PermissionChecker:
    """
    权限检查器主类。

    扫描 skill 目录下的脚本文件，检测敏感操作，计算权限权重。
    """

    def __init__(self, skill_dir: str, verbose: bool = False):
        """
        初始化权限检查器。

        Args:
            skill_dir: skill 根目录路径
            verbose: 是否输出详细日志
        """
        self.skill_dir = Path(skill_dir).resolve()
        self.verbose = verbose
        self.issues: List[Dict] = []
        self.stats = {
            "files_scanned": 0,
            "lines_scanned": 0,
            "sensitive_access": 0,
            "critical_write": 0,
            "network_access": 0,
            "file_delete": 0,
            "subprocess_call": 0,
        }
        self._current_string_ranges = []  # (start_char, end_char) for .py string literals

    # ── 公共接口 ────────────────────────────────────────────────────────────────

    def scan(self) -> Dict:
        """
        扫描 skill 目录，执行完整权限检查。

        Returns:
            dict: 检查结果字典，含权限权重、风险等级、问题列表
        """
        if self.verbose:
            print(f"[*] 扫描 skill 目录: {self.skill_dir}")

        # 1. 扫描脚本文件
        self._scan_scripts()

        # 2. 检查 SKILL.md frontmatter
        self._check_frontmatter()

        # 3. 计算权限权重
        weight = self._calculate_weight()

        # 4. 确定风险等级
        risk_level = self._determine_risk_level(weight)

        # 4.5 生成授权方式建议，并合并进 issues
        suggestions = self.suggest_authorization_methods()
        for i, sug in enumerate(suggestions):
            if i < len(self.issues):
                self.issues[i]["authorization_method"] = sug["authorization_method"]
                self.issues[i]["reason"] = sug["reason"]

        # 5. 生成报告
        report = self._generate_report(weight, risk_level)

        if self.verbose:
            print(f"[*] 扫描完成: {self.stats['files_scanned']} 文件, "
                  f"{self.stats['lines_scanned']} 行")
            print(f"[*] 风险等级: {risk_level.upper()}, 权重: {weight:.2%}")

        return report

    # ── 内部方法：文件扫描 ─────────────────────────────────────────────────────

    def _scan_scripts(self) -> None:
        """扫描 scripts/ 目录下的所有脚本文件。"""
        scripts_dir = self.skill_dir / "scripts"
        if not scripts_dir.is_dir():
            if self.verbose:
                print(f"[!] scripts/ 目录不存在: {scripts_dir}")
            return

        for ext in ["*.py", "*.js", "*.sh", "*.ps1", "*.bat"]:
            for file_path in scripts_dir.glob(ext):
                if file_path.is_file():
                    self._scan_file(file_path)

    def _get_ast_string_ranges(self, content: str) -> List[Tuple[int, int]]:
        """
        用 AST 解析 Python 源码，返回所有字符串字面量的字符偏移范围。
        用于跳过字符串内容中的关键词误匹配。
        """
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        ranges = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                # 有精确结束位置（Python 3.8+）
                if hasattr(node, 'end_lineno') and hasattr(node, 'end_col_offset'):
                    start = self._linecol_to_offset(content, node.lineno, node.col_offset)
                    end = self._linecol_to_offset(content, node.end_lineno, node.end_col_offset)
                    if start is not None and end is not None:
                        ranges.append((start, end))
        return ranges

    def _linecol_to_offset(self, content: str, line: int, col: int) -> Optional[int]:
        """(line, col) → 字符偏移。"""
        lines = content.splitlines(True)
        if line < 1 or line > len(lines):
            return None
        offset = sum(len(lines[i]) for i in range(line - 1))
        return offset + col

    def _in_string(self, pos: int) -> bool:
        """检查字符位置是否在字符串字面量内。"""
        for (s, e) in self._current_string_ranges:
            if s <= pos < e:
                return True
        return False

    def _scan_file(self, file_path: Path) -> None:
        """
        扫描单个文件，检测权限相关操作。

        Args:
            file_path: 文件路径
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            if self.verbose:
                print(f"[!] 无法读取文件 {file_path}: {e}")
            return

        self.stats["files_scanned"] += 1
        self.stats["lines_scanned"] += len(content.splitlines())

        # 对 .py 文件，用 AST 计算字符串字面量范围，用于跳过误匹配
        self._current_string_ranges = []
        if file_path.suffix == '.py':
            self._current_string_ranges = self._get_ast_string_ranges(content)

        # 检测各类操作
        self._check_sensitive_access(file_path, content)
        self._check_critical_write(file_path, content)
        self._check_network_access(file_path, content)
        self._check_file_delete(file_path, content)
        self._check_subprocess_call(file_path, content)

    # ── 内部方法：操作检测 ─────────────────────────────────────────────────────

    def _check_sensitive_access(self, file_path: Path, content: str) -> None:
        """
        检测敏感信息访问。

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        for pattern in SENSITIVE_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if self._in_string(match.start()):
                    continue
                line_num = content[:match.start()].count("\n") + 1
                self.stats["sensitive_access"] += 1
                self.issues.append({
                    "type": "sensitive_access",
                    "file": str(file_path.relative_to(self.skill_dir)),
                    "line": line_num,
                    "pattern": pattern,
                    "match": match.group(0),
                    "description": "检测到敏感信息访问（memory/credentials/token）",
                    "severity": "HIGH",
                })

    def _check_critical_write(self, file_path: Path, content: str) -> None:
        """
        检测关键位置写入。

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        for pattern in CRITICAL_PATH_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if self._in_string(match.start()):
                    continue
                # 排除注释和字符串中的无害引用
                line_num = content[:match.start()].count("\n") + 1
                line_content = content.splitlines()[line_num - 1] if line_num <= len(content.splitlines()) else ""
                if line_content.strip().startswith("#"):
                    continue

                self.stats["critical_write"] += 1
                self.issues.append({
                    "type": "critical_write",
                    "file": str(file_path.relative_to(self.skill_dir)),
                    "line": line_num,
                    "pattern": pattern,
                    "match": match.group(0),
                    "description": "检测到关键位置写入（skills/.workbuddy/系统目录）",
                    "severity": "HIGH",
                })

    def _check_network_access(self, file_path: Path, content: str) -> None:
        """
        检测网络访问。

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        for pattern in NETWORK_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if self._in_string(match.start()):
                    continue
                line_num = content[:match.start()].count("\n") + 1
                self.stats["network_access"] += 1
                self.issues.append({
                    "type": "network_access",
                    "file": str(file_path.relative_to(self.skill_dir)),
                    "line": line_num,
                    "pattern": pattern,
                    "match": match.group(0),
                    "description": "检测到网络访问（requests/urllib/httpx等）",
                    "severity": "MEDIUM",
                })

    def _check_file_delete(self, file_path: Path, content: str) -> None:
        """
        检测文件删除操作。

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        for pattern in DELETE_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if self._in_string(match.start()):
                    continue
                line_num = content[:match.start()].count("\n") + 1
                self.stats["file_delete"] += 1
                self.issues.append({
                    "type": "file_delete",
                    "file": str(file_path.relative_to(self.skill_dir)),
                    "line": line_num,
                    "pattern": pattern,
                    "match": match.group(0),
                    "description": "检测到文件删除操作（os.remove/shutil.rmtree等）",
                    "severity": "HIGH",
                })

    def _check_subprocess_call(self, file_path: Path, content: str) -> None:
        """
        检测 subprocess 调用。

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        for pattern in SUBPROCESS_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if self._in_string(match.start()):
                    continue
                line_num = content[:match.start()].count("\n") + 1
                # 排除注释
                line_content = content.splitlines()[line_num - 1] if line_num <= len(content.splitlines()) else ""
                if line_content.strip().startswith("#"):
                    continue

                self.stats["subprocess_call"] += 1
                self.issues.append({
                    "type": "subprocess_call",
                    "file": str(file_path.relative_to(self.skill_dir)),
                    "line": line_num,
                    "pattern": pattern,
                    "match": match.group(0),
                    "description": "检测到 subprocess 调用（os.system/subprocess等）",
                    "severity": "HIGH",
                })

    # ── 内部方法：frontmatter 检查 ──────────────────────────────────────────────

    def _check_frontmatter(self) -> None:
        """检查 SKILL.md 的 frontmatter 是否声明了权限相关字段。"""
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.is_file():
            return

        try:
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return

        # 提取 frontmatter
        fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE)
        if not fm_match:
            return

        fm_content = fm_match.group(1)

        # 检查 sensitive_access 声明
        if "sensitive_access" not in fm_content and self.stats["sensitive_access"] > 0:
            self.issues.append({
                "type": "missing_declaration",
                "file": "SKILL.md",
                "line": 1,
                "pattern": "sensitive_access",
                "match": "",
                "description": "脚本含敏感信息访问，但 frontmatter 未声明 sensitive_access: true",
                "severity": "ERROR",
            })

        # 检查 critical_write 声明
        if "critical_write" not in fm_content and self.stats["critical_write"] > 0:
            self.issues.append({
                "type": "missing_declaration",
                "file": "SKILL.md",
                "line": 1,
                "pattern": "critical_write",
                "match": "",
                "description": "脚本含关键位置写入，但 frontmatter 未声明 critical_write: true",
                "severity": "ERROR",
            })

    # ── 内部方法：权重计算 ──────────────────────────────────────────────────────

    def _calculate_weight(self) -> float:
        """
        计算权限权重。

        Returns:
            float: 权重值（0.0 ~ 1.0+）
        """
        weight = 0.0

        if self.stats["sensitive_access"] > 0:
            weight += WEIGHT_CONFIG["sensitive_access"]

        if self.stats["critical_write"] > 0:
            weight += WEIGHT_CONFIG["critical_write"]

        if self.stats["network_access"] > 0:
            weight += WEIGHT_CONFIG["network_access"]

        if self.stats["file_delete"] > 0:
            weight += WEIGHT_CONFIG["file_delete"]

        if self.stats["subprocess_call"] > 0:
            weight += WEIGHT_CONFIG["subprocess_call"]

        # 归一化到 0.0 ~ 1.0
        return min(weight, 1.0)

    def _determine_risk_level(self, weight: float) -> str:
        """
        根据权重确定风险等级。

        Args:
            weight: 权限权重

        Returns:
            str: 风险等级（low/medium/high/critical）
        """
        if weight >= RISK_THRESHOLD["critical"]:
            return "critical"
        elif weight >= RISK_THRESHOLD["high"]:
            return "high"
        elif weight >= RISK_THRESHOLD["medium"]:
            return "medium"
        else:
            return "low"

    # ── 内部方法：报告生成 ──────────────────────────────────────────────────────

    def _generate_report(self, weight: float, risk_level: str) -> Dict:
        """
        生成权限检查报告。

        Args:
            weight: 权限权重
            risk_level: 风险等级

        Returns:
            dict: 完整报告字典
        """
        return {
            "skill_dir": str(self.skill_dir),
            "risk_level": risk_level,
            "permission_weight": round(weight, 4),
            "stats": self.stats,
            "issues": self.issues,
            "summary": {
                "total_issues": len(self.issues),
                "high_severity": sum(1 for i in self.issues if i["severity"] == "HIGH"),
                "error_severity": sum(1 for i in self.issues if i["severity"] == "ERROR"),
                "recommendation": self._get_recommendation(risk_level),
            }
        }

    def _get_recommendation(self, risk_level: str) -> str:
        """
        根据风险等级给出建议。

        Args:
            risk_level: 风险等级

        Returns:
            str: 建议文本
        """
        recommendations = {
            "low": "风险较低，建议保持当前设计。",
            "medium": "中风险：建议在 SKILL.md 中增加权限说明，并在高权限操作前增加用户确认。",
            "high": "高风险：必须在 frontmatter 声明 sensitive_access/critical_write，"
                    "并在执行前通过 authorization_manager.py 请求用户授权。",
            "critical": "严重风险：建议重新评估 skill 设计，避免不必要的敏感信息访问和关键位置写入。"
                          "必须实施完整的授权检查机制。",
        }
        return recommendations.get(risk_level, "未知风险等级。")

    def _detect_skill_nature(self) -> str:
        """
        检测技能工作性质：automated（自动化）或 interactive（交互式）。

        判断依据（按优先级）：
        1. SKILL.md frontmatter 含 `automated: true` / `cron: true` → automated
        2. SKILL.md frontmatter 含 `interactive: true` → interactive
        3. description 含关键词（自动/定时/cron/schedule）→ automated
        4. tags 含 automation/cron/schedule → automated
        5. 默认 → interactive（保守）

        Returns:
            str: "automated" 或 "interactive"
        """
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.is_file():
            return "interactive"

        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            return "interactive"

        fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE)
        fm_content = fm_match.group(1) if fm_match else ""
        desc_match = re.search(r"description:\s*>(.*?)(?=\n\w|$)", content, re.DOTALL)
        description = desc_match.group(1) if desc_match else ""

        # 1. frontmatter 显式声明
        if re.search(r"^\s*automated\s*:\s*true", fm_content, re.MULTILINE | re.IGNORECASE):
            return "automated"
        if re.search(r"^\s*cron\s*:\s*true", fm_content, re.MULTILINE | re.IGNORECASE):
            return "automated"
        if re.search(r"^\s*interactive\s*:\s*true", fm_content, re.MULTILINE | re.IGNORECASE):
            return "interactive"

        # 2. description 关键词
        auto_keywords = ["自动", "定时", "cron", "schedule", "周期性", "每天", "每周", "hourly", "daily", "weekly"]
        if any(kw in description.lower() for kw in auto_keywords):
            return "automated"

        # 3. tags 关键词
        tags_match = re.search(r"tags:\s*\[(.*?)\]", fm_content, re.DOTALL)
        if tags_match:
            tags_str = tags_match.group(1).lower()
            if any(kw in tags_str for kw in ["automation", "cron", "schedule", "sync", "backup"]):
                return "automated"

        return "interactive"

    def suggest_authorization_methods(self) -> List[Dict]:
        """
        为每个检测到的风险操作建议授权方式。

        授权方式决策逻辑：
        1. 先判断技能工作性质（_detect_skill_nature）：
           - automated：自动化技能（如 git-sync、定时任务）
           - interactive：交互式技能（需要用户对话触发）

        2. 根据性质和风险类型决定授权方式：
           [automated 技能]
           - critical_write（skills/系统目录写入）→ unified（一次性授权，后续不再询问）
           - file_delete（文件删除）→ unified
           - subprocess_call（子进程调用）→ unified
           - sensitive_access（敏感信息访问）→ unified
           - 中风险 → silent（静默执行，仅记录）
           - 极关键操作（如删除非工作区目录）→ immediate（每次确认）

           [interactive 技能]
           - 高风险 → immediate（每次执行前确认）
           - 中风险 → unified（一次性授权）
           - 低风险 → silent

        Returns:
            list: 含授权建议的操作列表，每项含 {
                "file", "line", "type", "severity",
                "description", "authorization_method", "reason"
            }
        """
        nature = self._detect_skill_nature()
        suggestions = []

        for issue in self.issues:
            severity = issue.get("severity", "")
            issue_type = issue.get("type", "")
            method = "silent"
            reason = ""

            if nature == "automated":
                # 自动化技能：优先 unified，减少用户打扰
                if severity in ("HIGH", "ERROR"):
                    # 判断是否「极关键操作」→ 才用 immediate
                    is_critical = (
                        issue_type == "critical_write"
                        and "outside" in issue.get("description", "").lower()
                    ) or (
                        issue_type == "file_delete"
                        and "system" in issue.get("description", "").lower()
                    )
                    if is_critical:
                        method = "immediate"
                        reason = "极关键操作，即使是自动化技能也需每次确认"
                    else:
                        method = "unified"
                        reason = "自动化技能：一次性授权，后续自动执行不再询问"
                elif severity == "MEDIUM":
                    method = "silent"
                    reason = "自动化技能：中风险静默执行，仅记录"
                else:
                    method = "silent"
                    reason = "低风险操作，静默执行，仅记录"
            else:
                # 交互式技能：保守策略
                if severity in ("HIGH", "ERROR"):
                    method = "immediate"
                    reason = "高风险操作，每次执行前需用户确认"
                elif severity == "MEDIUM":
                    method = "unified"
                    reason = "中风险操作，可批量统一授权"
                else:
                    method = "silent"
                    reason = "低风险操作，静默执行，仅记录"

            suggestions.append({
                "file": issue.get("file", ""),
                "line": issue.get("line", 0),
                "type": issue_type,
                "severity": severity,
                "description": issue.get("description", ""),
                "authorization_method": method,
                "reason": reason,
            })

        return suggestions


# ── CLI 入口 ─────────────────────────────────────────────────────────────────────

def main():
    """命令行入口。"""
    import argparse

    parser = argparse.ArgumentParser(
        description="权限检查器：扫描 skill 脚本，计算权限权重，生成风险报告"
    )
    parser.add_argument("skill_dir", help="skill 根目录路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细日志")
    parser.add_argument("--output", "-o", help="输出 JSON 报告文件路径")
    parser.add_argument("--exit-code", action="store_true",
                        help="根据风险等级设置退出码（low=0, medium=1, high=2, critical=3）")

    args = parser.parse_args()

    # 执行扫描
    checker = PermissionChecker(args.skill_dir, verbose=args.verbose)
    report = checker.scan()

    # 输出报告
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"[*] 报告已保存: {args.output}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    # 退出码
    if args.exit_code:
        exit_code_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        sys.exit(exit_code_map.get(report["risk_level"], 0))


if __name__ == "__main__":
    main()
