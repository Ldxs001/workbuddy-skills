# -*- coding: utf-8 -*-
"""local-rag-builder Prompt 管理模块"""

import os
import json
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
CUSTOM_PRESETS_FILE = os.path.join(PROMPTS_DIR, "custom_presets.json")


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


def build_persona_prompt(persona_text: str) -> str:
    """包装用户画像提示文本为 prompt 片段（方案 C 扩展点）"""
    if not persona_text:
        return ""
    return persona_text


# ═══════════════ 自定义预设 CRUD ═══════════════

def _load_custom_presets() -> dict:
    """读取自定义预设 JSON"""
    if not os.path.exists(CUSTOM_PRESETS_FILE):
        return {}
    try:
        with open(CUSTOM_PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_custom_presets(data: dict):
    """原子写入自定义预设 JSON"""
    tmp = CUSTOM_PRESETS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CUSTOM_PRESETS_FILE)
    except OSError:
        pass


def get_all_presets() -> dict:
    """合并内置 + 自定义预设，每条标注 built_in"""
    result = {}
    for key, p in PROMPT_PRESETS.items():
        result[key] = {**p, "built_in": True}
    for key, p in _load_custom_presets().items():
        result[key] = {**p, "built_in": False}
    return result


def save_custom_preset(label: str, template: str, description: str = "") -> dict:
    """保存一条自定义预设，返回 {success, key, error}"""
    if not label or not template:
        return {"success": False, "error": "名称和模板不能为空"}
    import time
    key = f"custom_{int(time.time())}"
    presets = _load_custom_presets()
    presets[key] = {"label": label, "description": description or "", "template": template}
    _save_custom_presets(presets)
    return {"success": True, "key": key, "label": label}


def delete_custom_preset(key: str) -> dict:
    """删除一条自定义预设，返回 {success, error}"""
    if not key or key in PROMPT_PRESETS:
        return {"success": False, "error": "内置预设不可删除"}
    presets = _load_custom_presets()
    if key not in presets:
        return {"success": False, "error": "预设不存在"}
    del presets[key]
    _save_custom_presets(presets)
    return {"success": True}
