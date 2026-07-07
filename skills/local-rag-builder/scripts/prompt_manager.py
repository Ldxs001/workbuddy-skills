# -*- coding: utf-8 -*-
"""local-rag-builder Prompt 管理模块"""

import os
from utils import PROMPTS_DIR

SYSTEM_PROMPT_PREFIX = '基于以下资料回答问题。如果资料中没有相关信息，请说"不知道"。\n\n资料：\n{context}\n\n问题：\n{question}\n\n回答：'
DEFAULT_USER_TEMPLATE = '请用 Markdown 格式输出，并在末尾附上引用片段编号。'

PROMPT_PRESETS = {
    "default": {"label": "标准模式", "description": "Markdown 格式输出 + 引用标注", "template": "请用 Markdown 格式输出，并在末尾附上引用片段编号。"},
    "structured": {"label": "深度分析", "description": "分层输出（结论→论据→引用）", "template": "请以{role}身份分析以下资料。\n\n先给出核心结论，再展开论据，最后附上引用。"},
    "friendly": {"label": "友好对话", "description": "亲和口语化回答", "template": "请用亲切、易懂的语言回答问题，回答末尾用 [1][2] 标注引用。如果资料不足，可以说\"我目前掌握的信息有限\"并提供{alt}建议。"},
    "compare": {"label": "对比分析", "description": "对比式输出，罗列异同", "template": "请对比分析以下资料，从{dim}维度进行对比，输出表格。\n\n输出格式：\n## 对比维度\n| 项目 | 差异 |\n|------|------|\n\n## 共同点\n\n## 总结"},
}

TEMPLATE_FILE = os.path.join(PROMPTS_DIR, "custom_prompt_template.txt")


def get_system_prefix():
    try:
        from config import load_config
        cfg = load_config()
        custom = cfg.get("prompt", {}).get("system_prefix")
        if custom:
            return custom
    except Exception:
        pass
    return SYSTEM_PROMPT_PREFIX


def set_system_prefix(prefix):
    from config import load_config, save_config
    cfg = load_config()
    cfg.setdefault("prompt", {})["system_prefix"] = prefix
    save_config(cfg)


def get_template_path():
    return TEMPLATE_FILE


def load_template():
    try:
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    if "回答：" in c:
                        suffix = c[c.rfind("回答：") + 4:].strip()
                        if suffix:
                            save_template(suffix)
                            return suffix
                    return c
    except Exception:
        pass
    return DEFAULT_USER_TEMPLATE


def save_template(content):
    try:
        tmp = TEMPLATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content.strip())
        os.replace(tmp, TEMPLATE_FILE)
        return True
    except Exception:
        return False


def reset_template():
    save_template(DEFAULT_USER_TEMPLATE)
    return DEFAULT_USER_TEMPLATE


def get_default_template():
    return get_system_prefix() + DEFAULT_USER_TEMPLATE


def get_full_prompt(user_template=None):
    return get_system_prefix() + (user_template or load_template())


def build_prompt(context, question, template=None):
    full = get_full_prompt(template)
    return full.format(context=context, question=question)
