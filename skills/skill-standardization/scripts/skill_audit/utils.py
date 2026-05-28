#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/utils.py — 常量定义和工具函数
"""

import os
import re
from pathlib import Path

# ── 规则定义 (R-01 ~ R-23) ─────────────────────────────────────
RULES = [
    {
        "id": "R-01",
        "name": "Frontmatter 存在性",
        "severity": "ERROR",
        "check": "存在 YAML frontmatter（--- 包裹）",
        "method": "regex_frontmatter_exists",
        "fixable": True,
        "create_template": "自动在文件头部插入 --- 包裹的 frontmatter 块，含 name/version/description/sensitive_access/critical_write/permission_weight",
    },
    {
        "id": "R-02",
        "name": "name 字段",
        "severity": "ERROR",
        "check": "frontmatter 含 name 字段，且与目录名一致",
        "method": "yaml_has_name",
        "fixable": True,
        "create_template": "name: <技能名，与目录名完全一致>",
    },
    {
        "id": "R-03",
        "name": "version 字段 (SemVer)",
        "severity": "ERROR",
        "check": "frontmatter 含 version 字段且符合 SemVer（MAJOR.MINOR.PATCH）",
        "method": "yaml_has_semver_version",
        "fixable": True,
        "create_template": "version: 1.0.0",
    },
    {
        "id": "R-04",
        "name": "description 字段",
        "severity": "ERROR",
        "check": "frontmatter 含 description 字段（≤120字符）",
        "method": "yaml_has_description",
        "fixable": False,
        "create_template": 'description: "<一句话描述技能用途，≤120字符>"',
    },
    {
        "id": "R-05",
        "name": "name 与目录名一致",
        "severity": "WARN",
        "check": "frontmatter name 与目录名一致",
        "method": "name_matches_dirname",
        "fixable": True,
        "create_template": "创建时自动从目录名推导，无需手动填写",
    },
    {
        "id": "R-06",
        "name": "正文含一级标题",
        "severity": "WARN",
        "check": "正文含 # 开头的一级标题（与 name 字段一致）",
        "method": "body_has_h1",
        "fixable": True,
        "create_template": "# <技能名>（与 frontmatter name 字段一致）",
    },
    {
        "id": "R-07",
        "name": "触发条件章节（合规）",
        "severity": "ERROR",
        "check": "正文含 ## 触发场景 章节，且含正向触发词≥3个、否定条件≥1个，无「自动执行」等危险表述",
        "method": "body_has_trigger_section",
        "fixable": False,
        "create_template": "## 触发场景\n\n当用户提出以下意图时触发：\n- <触发词1> → 触发 <技能名>\n- <触发词2>\n- <触发词3>\n\n**不触发**：\n- <否定条件1>\n- <否定条件2>",
    },
    {
        "id": "R-08",
        "name": "核心能力章节",
        "severity": "WARN",
        "check": "正文含 ## 核心能力 章节（或同义词），列出 3-5 条核心功能",
        "method": "body_has_core_section",
        "fixable": False,
        "create_template": "## 核心能力\n\n- <功能点1>\n- <功能点2>\n- <功能点3>",
    },
    {
        "id": "R-09",
        "name": "工作流程/使用方式章节",
        "severity": "WARN",
        "check": "正文含 ## 工作流程 章节（或同义词），用步骤列表描述执行流程",
        "method": "body_has_workflow_section",
        "fixable": False,
        "create_template": "## 工作流程\n\n1. <步骤1>\n2. <步骤2>\n3. <步骤3>",
    },
    {
        "id": "R-10",
        "name": "version 一致性",
        "severity": "ERROR",
        "check": "SKILL.md version == _meta.json version（与铁律2版本号更新规则一致）",
        "method": "version_matches_manifest",
        "fixable": True,
        "create_template": "创建时 version: 1.0.0，同步写入 _meta.json",
    },
    {
        "id": "R-11",
        "name": "产出物路径规范性（含风险检测）",
        "severity": "ERROR",
        "check": "产出物路径符合 skills/.standardization/<skill>/ 规范，且无路径遍历、跨目录写入、敏感信息泄露风险",
        "method": "check_artifact_paths",
        "fixable": True,
        "fix_action": "fix_artifact_paths(skill_dir) — 自动修正 scripts/*.py 中的产出物路径，将硬编码路径替换为 skills/.standardization/<skill>/ 规范",
        "create_template": "scripts/ 中产出物路径统一使用 Path(__file__).parent.parent / '.standardization' / '<skill>' / 'data'",
    },
    {
        "id": "R-12",
        "name": "外部数据目录规范性（含风险检测）",
        "severity": "ERROR",
        "check": "外部数据目录路径符合 skills/.standardization/<skill-name>/ 约定，_meta.json 含 data_dir 字段且一致，且无数据泄露风险",
        "method": "check_external_data_dir",
        "fixable": True,
        "fix_action": "fix_external_data_dir(skill_dir) — 自动修正 _meta.json 和 scripts/*.py 中的数据目录变量，确保符合 skills/.standardization/<skill>/data/ 规范",
        "create_template": "如需持久化数据，_meta.json 添加 data_dir: skills/.standardization/<skill-name>/data",
    },
    # ── 新增规则 R-13 ~ R-17 (v2.13.0) ────────────────────────────────
    {
        "id": "R-13",
        "name": "敏感信息访问声明",
        "severity": "WARN",
        "check": "脚本含敏感信息访问（memory/credentials/token）时，frontmatter 须声明 sensitive_access: true 并在 references/permissions.md 中说明用途",
        "method": "check_sensitive_access_declaration",
        "fixable": True,
        "create_template": "sensitive_access: false  # 如果脚本不访问敏感信息",
    },
    {
        "id": "R-14",
        "name": "关键位置写入声明",
        "severity": "WARN",
        "check": "脚本含关键位置写入（skills/.workbuddy/系统目录）时，frontmatter 须声明 critical_write: true 并在 references/permissions.md 中说明用途",
        "method": "check_critical_write_declaration",
        "fixable": True,
        "create_template": "critical_write: false  # 如果脚本不写入关键位置",
    },
    {
        "id": "R-15",
        "name": "高权限操作风险说明",
        "severity": "ERROR",
        "check": "脚本含高权限操作（风险等级 high/critical）时，references/permissions.md 须包含对应操作的风险说明（不强制代码层授权检查）",
        "method": "check_authorization_present",
        "fixable": False,
        "create_template": "permission_weight: LOW  # 根据 PermissionChecker.scan() 实际风险等级填写",
    },
    {
        "id": "R-16",
        "name": "权限权重说明",
        "severity": "WARN",
        "check": "frontmatter 须声明 permission_weight（LOW/MEDIUM/HIGH/CRITICAL），且 references/permissions.md 须包含权限权重说明表格",
        "method": "check_permission_weight_explained",
        "fixable": True,
        "create_template": "permission_weight: LOW  # 根据 PermissionChecker.scan() 实际风险等级填写",
    },
    {
        "id": "R-17",
        "name": "渐进加载引用（强制）",
        "severity": "ERROR",
        "check": "SKILL.md > 200 行时必须拆分到 references/，并通过「→ 详见 references/xxx.md」引用",
        "method": "check_progressive_loading_forced",
        "fixable": False,
        "create_template": "创建时控制 SKILL.md ≤ 200 行，超出部分拆分到 references/",
    },
    # ── 新增规则 R-18 ~ R-20 (v2.17.0) ──────────────────────────────
    {
        "id": "R-18",
        "name": "反模式具体性",
        "severity": "WARN",
        "check": "正文含 ## 反模式/常见错误 章节，且每条反模式含具体描述（≥20字）或代码示例",
        "method": "body_has_antipattern_section",
        "fixable": False,
        "create_template": "## 反模式\n\n- <具体错误描述≥20字>\n  - 正确做法：<说明>",
    },
    {
        "id": "R-19",
        "name": "FAQ 有意义性",
        "severity": "WARN",
        "check": "正文含 ## FAQ/常见问题 章节，且 Q&A 对有意义（Q≥10字，A≥15字）",
        "method": "body_has_faq_section",
        "fixable": False,
        "create_template": "## FAQ\n\nQ: <具体问题≥10字>\nA: <实质回答≥15字>\n",
    },
    {
        "id": "R-20",
        "name": "写作规范（术语一致/无模糊表述/中英文混排）",
        "severity": "WARN",
        "check": "正文术语一致、无模糊表述（可能/应该/大概）、中英文混排有空格",
        "method": "body_check_writing_standards",
        "fixable": False,
        "create_template": "保持术语统一（创建/更新/删除），避免模糊词，中英文间加空格",
    },
    # ── 新增规则 R-21 (v2.24.0) ──────────────────────────────────
    {
        "id": "R-21",
        "name": "渐进式加载显式说明",
        "severity": "WARN",
        "check": "SKILL.md 在显眼位置（核心能力/工作流程章节）显式说明渐进式加载（含「渐进式加载」或「progressive」关键词）",
        "method": "body_has_progressive_loading_explicit",
        "fixable": False,
        "create_template": "## 核心能力\n\n> 📚 **渐进式加载**：本技能采用渐进式 MD 体系，`SKILL.md` 为入口（≤230行），详细内容拆分到 `references/*.md` 按需加载。",
    },
    # ── 新增规则 R-22 (v2.31.0) ──────────────────────────────────
    {
        "id": "R-22",
        "name": "数据目录规范检查",
        "severity": "WARN",
        "check": "安装目录无越位数据文件（构建产物/缓存/日志应放在 data_dir: 声明的数据目录）",
        "method": "check_data_dir_compliance",
        "fixable": True,
        "create_template": "在 frontmatter 中声明 data_dir: ../.standardization/<skill>/",
    },
    # ── 新增规则 R-23 (v2.34.8) ──────────────────────────
    {
        "id": "R-23",
        "name": "文档-代码一致性检查",
        "severity": "WARN",
        "check": "SKILL.md 中引用的脚本/文件/函数名真实存在，代码示例中的调用方式与实际代码一致",
        "method": "check_doc_code_consistency",
        "fixable": False,
        "create_template": "确保 SKILL.md 引用的所有 .py 文件存在于技能目录中，代码示例中的调用方式与实际 argparse/函数签名一致",
    },
    # ── 新增规则 R-24 (v2.38.6) ──────────────────────
    {
        "id": "R-24",
        "name": "更新日志渐进加载",
        "severity": "WARN",
        "method": "check_changelog_progressive",
        "check": "更新日志必须放在 references/changelog.md，SKILL.md 只能有引用",
        "fixable": False,
        "create_template": "将更新日志移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
    },
    # ── 新增规则 R-24 (v2.38.6) ──────────────────────
    {
        "id": "R-24",
        "name": "更新日志渐进加载",
        "severity": "WARN",
        "method": "check_changelog_progressive",
        "check": "更新日志必须放在 references/changelog.md，SKILL.md 只能有引用",
        "fixable": False,
        "create_template": "将更新日志移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
    },
    # ── 新增规则 R-24 (v2.38.6) ──────────────────────
    {
        "id": "R-24",
        "name": "更新日志渐进加载",
        "severity": "WARN",
        "method": "check_changelog_progressive",
        "check": "更新日志必须放在 references/changelog.md，SKILL.md 只能有引用",
        "fixable": False,
        "create_template": "将更新日志移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
    },
    # ── 新增规则 R-24 (v2.38.6) ──────────────────────
    {
        "id": "R-24",
        "name": "更新日志渐进加载",
        "severity": "WARN",
        "method": "check_changelog_progressive",
        "check": "更新日志必须放在 references/changelog.md，SKILL.md 只能有引用",
        "fixable": False,
        "create_template": "将更新日志移至 references/changelog.md，SKILL.md 中保留引用：「→ 详见 references/changelog.md」",
    },
]



# 同义章节关键词映射
TRIGGER_KEYWORDS = ["触发条件", "触发场景", "适用场景", "触发"]
CORE_KEYWORDS = ["核心功能", "核心能力", "概述", "核心概念", "Overview", "技能概述"]
WORKFLOW_KEYWORDS = ["工作流程", "使用方式", "Workflow", "完整执行流程", "核心指令", "完整工作流"]

# R-11: 产出物路径检测 — 违规模式关键词（长名在前防止部分匹配）
ARTIFACT_DIR_NAMES = [
    "outputs", "output", "artifacts", "results", "exports",
    "reports", "report", "backups", "backup", "generated",
    "dumps", "dump", "build", "dist", "logs", "log",
    "data", "cache", "temp", "tmp", "out",
]

# ────────── R-11 产出物全面定义（v2.7.0 扩展）───────────
# 已知标准目录（非产出物 — 属于技能本身结构的一部分）
_KNOWN_STANDARD_DIRS = {
    "scripts",      # 脚本代码
    "references",   # 参考文档
    "assets",       # 静态资源（图标、图片等技能自身资源）
    "__pycache__",  # Python 编译缓存
    ".git",         # Git 版本控制
}

# 产出物目录名 → 产出物分类 映射
# key: 目录名（小写），value: (分类, 描述)
_ARTIFACT_DIR_CLASSIFY = {
    # data 类 — 持久化/结构化数据
    "data":      ("data", "持久化数据目录"),
    "database":  ("data", "数据库目录"),
    "db":        ("data", "数据库目录"),
    "storage":   ("data", "存储目录"),
    "backup":    ("data", "备份目录"),
    "backups":   ("data", "备份目录"),
    "dump":      ("data", "数据转储目录"),
    "dumps":     ("data", "数据转储目录"),
    # cache 类 — 缓存/临时计算
    "cache":     ("cache", "缓存目录"),
    "caches":    ("cache", "缓存目录"),
    ".cache":    ("cache", "隐藏缓存目录"),
    "temp_cache": ("cache", "临时缓存目录"),
    # outputs 类 — 输出/生成产物
    "outputs":   ("outputs", "输出产物目录"),
    "output":    ("outputs", "输出产物目录"),
    "out":       ("outputs", "输出产物目录"),
    "results":   ("outputs", "结果目录"),
    "result":    ("outputs", "结果目录"),
    "exports":   ("outputs", "导出目录"),
    "export":    ("outputs", "导出目录"),
    "reports":   ("outputs", "报告目录"),
    "report":    ("outputs", "报告目录"),
    "generated": ("outputs", "生成产物目录"),
    "build":     ("outputs", "构建产物目录"),
    "dist":      ("outputs", "分发包目录"),
    "artifacts": ("outputs", "产出物目录"),
    # temp 类 — 临时/日志
    "temp":      ("temp", "临时文件目录"),
    "tmp":       ("temp", "临时文件目录"),
    ".tmp":      ("temp", "隐藏临时目录"),
    "logs":      ("temp", "日志目录"),
    "log":       ("temp", "日志目录"),
}

# 全面产出物文件扩展名（按分类）
_ARTIFACT_EXTS_COMPREHENSIVE = {
    # data — 数据文件
    ".json":    "data",   ".csv":   "data",   ".yaml":  "data",
    ".yml":     "data",   ".db":    "data",   ".sqlite": "data",
    ".sqlite3": "data",   ".pkl":   "data",   ".pickle": "data",
    ".parquet": "data",   ".feather": "data", ".h5":    "data",
    ".hdf5":    "data",   ".npy":   "data",   ".npz":   "data",
    # outputs — 输出/展示文件
    ".html":    "outputs", ".pdf":  "outputs", ".png":  "outputs",
    ".jpg":     "outputs", ".jpeg": "outputs", ".svg":  "outputs",
    ".gif":     "outputs", ".ico":  "outputs", ".txt":  "outputs",
    ".log":     "outputs", ".ics":  "outputs", ".xlsx": "outputs",
    ".xls":     "outputs", ".pptx": "outputs", ".docx": "outputs",
    ".md":      "outputs",  # 非 SKILL.md / references 的 md 文件
    # temp — 临时/缓冲文件
    ".tmp":     "temp",   ".bak":   "temp",   ".swp":  "temp",
    ".lock":    "temp",   ".pid":   "temp",   ".cache": "temp",
    # config — 配置快照（仅根目录或非标准目录下才视为产出物）
    ".env":     "data",   ".cfg":   "data",   ".ini":  "data",
    ".toml":    "data",
}

# 根目录已知白名单文件（非产出物）
_KNOWN_ROOT_FILES = {"SKILL.md", "_meta.json", ".gitignore", ".gitkeep", ".progress.md"}

# 旧版兼容：产出物扩展名集合（用于根目录文件扫描）
_ROOT_ARTIFACT_EXTS = set(_ARTIFACT_EXTS_COMPREHENSIVE.keys())

# 根目录文件 → 分类映射（旧版兼容）
_ROOT_EXT_CLASSIFY = _ARTIFACT_EXTS_COMPREHENSIVE.copy()

# 构建产出目录名的正则 alternation（用于 scripts/ 正则扫描）
_ARTIFACT_DIR_PATTERN = "|".join(ARTIFACT_DIR_NAMES)

_ARTIFACT_WRITE_PATTERNS = [
    # Path(__file__).parent / "data_dir" — 产出到脚本同目录
    re.compile(rf'__file__\s*\)\s*\.\s*parent\s*/\s*"({_ARTIFACT_DIR_PATTERN})"'),
    re.compile(rf'os\.path\.dirname\s*\(\s*__file__\s*\)\s*,\s*"({_ARTIFACT_DIR_PATTERN})"'),
    re.compile(rf'os\.path\.join\s*\(\s*os\.path\.dirname\s*\(\s*__file__\s*\)\s*,\s*"({_ARTIFACT_DIR_PATTERN})"'),
    # open("output/report.html", "w") — 捕获完整路径（目录+文件名）
    re.compile(rf'open\s*\(\s*["\'](?:\./)?({_ARTIFACT_DIR_PATTERN}/[^"\']+)["\']\s*,\s*["\']w["\']'),
    # Path("output_dir").mkdir() — 创建产出目录
    re.compile(rf'Path\s*\(\s*["\']\.?({_ARTIFACT_DIR_PATTERN})["\']'),
    # with open("file.json", "w") — 直接写入 JSON/CSV 到工作目录
    re.compile(r'open\s*\(\s*["\']([^"\']+\.(json|csv|html|png|jpg|pdf|txt|ics))["\']\s*,\s*["\']w["\']'),
]

# [v2.11.0] 通用硬编码路径检测：匹配所有引号包裹的路径字符串
# 覆盖：~/.xxx/、/home/、/Users/、C:/Users/、D:/ 等绝对/用户路径
_HARDCODED_PATH_RE = re.compile(
    r'["\']'
    r"((?:~|/home/|/Users/|[A-Za-z]:[\/]Users|[A-Za-z]:[\/]home|[A-Za-z]:[\/])[^\"' \t]*?)"
    r'["\']'
)

# 排除的合法模式（.standardization/ 路径、模板占位符、URL、shell变量）
_PATH_EXCLUDE_RE = re.compile(
    r'^(?:\.standardization/|<[^>]+>|\{[^}]+\}|https?://|ftp://|file://|\$\{|\$\w+)$'
)


def _is_hardcoded_path(s):
    """判断字符串是否是硬编码路径（需要改为 skills/.standardization/ 结构）"""
    if not s or len(s) < 5:
        return False
    if _PATH_EXCLUDE_RE.search(s):
        return False
    # 含有 .standardization/ 的路径视为合法标准化路径
    if '.standardization/' in s.replace('\\', '/'):
        return False
    # 必须包含路径分隔符或 ~ 或盘符
    if '/' in s or '\\' in s or s.startswith('~'):
        return True
    return False


def parse_simple_yaml_frontmatter(text):
    """从 Markdown 文本中提取并解析 YAML frontmatter。
    返回 (dict, body_text) 或 (None, text) 如果没有 frontmatter。"""
    if not text.startswith("---"):
        return None, text

    # 规范化换行符（CRLF 兼容：SKILL.md 可能是 Windows 换行符）
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    lines = text.split("\n", 1)
    rest = lines[1] if len(lines) > 1 else ""

    end_idx = rest.find("\n---")
    if end_idx == -1:
        return None, text

    fm_text = rest[:end_idx]
    body = rest[end_idx + 4:]

    result = {}
    current_key = None

    for line_no, line in enumerate(fm_text.split("\n")):
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if stripped.startswith("- ") and current_key:
            arr_key = current_key
            if arr_key not in result or not isinstance(result.get(arr_key), list):
                existing = result.get(arr_key, "")
                if isinstance(existing, str) and existing:
                    result[arr_key] = [existing]
                else:
                    result[arr_key] = []
            result[arr_key].append(stripped[2:].strip().strip("'\""))
            continue

        colon_idx = stripped.find(":")
        if colon_idx > 0:
            key = stripped[:colon_idx].strip()
            val = stripped[colon_idx + 1:].strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if inner:
                    result[key] = [item.strip().strip("'\"") for item in inner.split(",")]
                else:
                    result[key] = []
            elif val:
                # 转换 true/false 为布尔值（YAML 兼容）
                if val.lower() == "true":
                    result[key] = True
                elif val.lower() == "false":
                    result[key] = False
                else:
                    result[key] = val
            # 无论 val 是否为空，都更新 current_key（修复 bug：移到 if/elif 外面）
            current_key = key
        # 调试输出（正式版关闭）
        # print(f"DEBUG L{line_no+1}: key={key!r} val={val!r} → result has {len(result)} keys")

    return result, body


def _find_skills_dir(skill_dir):
    """向上查找 skills 目录（最多 5 层）。"""
    p = os.path.abspath(skill_dir)
    for _ in range(5):
        if os.path.basename(p) == "skills" and os.path.isdir(p):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return os.path.dirname(os.path.abspath(skill_dir))


def _classify_artifact(dirname):
    """根据目录名推断产出物分类（data/cache/outputs/temp）"""
    d = dirname.lower().rstrip("s")
    # 优先使用 _ARTIFACT_DIR_CLASSIFY
    if d in _ARTIFACT_DIR_CLASSIFY:
        return _ARTIFACT_DIR_CLASSIFY[d][0]
    mapping = {
        "data": "data", "backup": "data", "dump": "data",
        "cache": "cache", "tmp": "temp", "temp": "temp",
        "output": "outputs", "out": "outputs", "result": "outputs",
        "export": "outputs", "report": "outputs", "log": "outputs",
        "build": "outputs", "dist": "outputs", "generated": "outputs",
        "artifact": "outputs",
    }
    return mapping.get(d, "outputs")


def _classify_artifact_by_ext(filename):
    """根据文件名扩展名推断产出物分类（data/cache/outputs/temp）"""
    ext = os.path.splitext(filename)[1].lower()
    cat = _ARTIFACT_EXTS_COMPREHENSIVE.get(ext, "outputs")
    if cat == "temp":
        cat = "outputs"  # temp 类文件在根目录默认归为 outputs
    return cat


def _extract_path_literal(line_text, matched_target):
    """从违规行中提取完整的路径字面量（引号内的内容）。"""
    quoted = re.findall(r"""["']([^"']+)["']""", line_text)
    for q in quoted:
        if matched_target in q:
            return q
    return matched_target
