#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_audit/structure_checker.py — 正文结构检查函数 (R-06~R-09)
"""

import re


def body_has_h1(filepath, content, fm, body, **kw):
    """R-06: 正文含一级标题检查"""
    m = re.search(r'^# ', body, re.MULTILINE)
    return {"passed": m is not None,
            "detail": f"发现一级标题: {m.group(0).strip()}" if m else "未找到一级标题 (# )"}


def _section_exists(body, keywords, label):
    """通用：检查是否包含任一关键词的 ## 级标题"""
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("## "):
            title = s[3:].strip()
            for kw in keywords:
                if kw.lower() in title.lower():
                    return True, f"发现章节: {title}"
    return False, f"未找到 [{label}] 章节（同义词: {', '.join(keywords)}）"


def body_has_trigger_section(filepath, content, fm, body, **kw):
    """R-07: 触发条件章节检查"""
    from .utils import TRIGGER_KEYWORDS
    ok, detail = _section_exists(body, TRIGGER_KEYWORDS, "触发条件")
    return {"passed": ok, "detail": detail}


def body_has_core_section(filepath, content, fm, body, **kw):
    """R-08: 核心能力章节检查"""
    from .utils import CORE_KEYWORDS
    ok, detail = _section_exists(body, CORE_KEYWORDS, "核心能力")
    return {"passed": ok, "detail": detail}


def body_has_workflow_section(filepath, content, fm, body, **kw):
    """R-09: 工作流程/使用方式章节检查"""
    from .utils import WORKFLOW_KEYWORDS
    ok, detail = _section_exists(body, WORKFLOW_KEYWORDS, "工作流程")
    return {"passed": ok, "detail": detail}
