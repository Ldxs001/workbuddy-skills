# -*- coding: utf-8 -*-
"""local-rag-builder Prompt 管理模块"""

import os
import json
from utils import PROMPTS_DIR

# ═══════════════ 系统提示词（锁定，用户不可改） ═══════════════
# 只暴露 {cite_format} {output_style} {fallback} 三个插槽给用户
SYSTEM_PROMPT_PREFIX = '基于以下资料回答问题。如果资料中没有相关信息，请说"不知道"。\n\n资料：\n{context}\n\n问题：\n{question}\n\n回答：'

# 第二轮作答的固定框架（锁定）。{kb}{context}{question} 由代码注入
SECOND_PASS_TEMPLATE = """基于以下资料回答用户问题。不能脱离资料编造。
{cite_format}
{output_style}

资料（来自 {kb}）：
{context}

问题：
{question}

回答：{fallback}"""

# ═══════════════ 用户可配插槽（默认值） ═══════════════
DEFAULT_SLOTS = {
    "cite_format": "每个结论后面用 [n] 标注来源的段落编号",
    "output_style": "用 Markdown 格式输出",
    "fallback": "如果资料中没有明确结论，可以结合资料进行分析推理，但不能编造不存在的内容"
}

# ═══════════════ 预设（插槽预填组合） ═══════════════
PROMPT_PRESETS = {
    "default": {
        "label": "标准模式",
        "description": "Markdown + 引用标注 + 分析推理",
        "slots": {
            "cite_format": "每个结论后面用 [n] 标注来源的段落编号",
            "output_style": "用 Markdown 格式输出",
            "fallback": "如果资料中没有明确结论，可以结合资料进行分析推理，但不能编造不存在的内容"
        }
    },
    "structured": {
        "label": "深度分析",
        "description": "分层输出（结论→论据→引用）",
        "slots": {
            "cite_format": "每个论据后面用 [n] 标注来源的段落编号",
            "output_style": "先给出核心结论，再展开论据，最后附上引用",
            "fallback": "可以结合资料进行分析推理，但不能编造不存在的内容"
        }
    },
    "compare": {
        "label": "对比分析",
        "description": "对比式输出，罗列异同",
        "slots": {
            "cite_format": "每个对比结论后面用 [n] 标注来源的段落编号",
            "output_style": "用表格对比输出，列出异同点",
            "fallback": "可以从多维度对比异同，但不能编造不存在的内容"
        }
    },
    "friendly": {
        "label": "友好对话",
        "description": "亲和口语化回答",
        "slots": {
            "cite_format": "回答末尾统一用 [1][2] 标注引用",
            "output_style": "用亲切易懂的语言回答",
            "fallback": "如果资料中没有明确结论，可以说\"我目前掌握的信息有限\"，但不能编造不存在的内容"
        }
    },
}

TEMPLATE_FILE = os.path.join(PROMPTS_DIR, "custom_prompt_template.txt")
CUSTOM_PRESETS_FILE = os.path.join(PROMPTS_DIR, "custom_presets.json")

# ═══════════════ 插槽管理 ═══════════════

_SLOTS_CONFIG_KEY = "prompt_slots"


def _load_slots_from_config() -> dict:
    """从配置加载用户插槽值"""
    try:
        from config import load_config
        cfg = load_config()
        return cfg.get(_SLOTS_CONFIG_KEY, {})
    except Exception:
        return {}


def _save_slots_to_config(slots: dict):
    """保存用户插槽值到配置"""
    try:
        from config import load_config, save_config
        cfg = load_config()
        cfg[_SLOTS_CONFIG_KEY] = slots
        save_config(cfg)
    except Exception:
        pass


def load_slots() -> dict:
    """合并默认 + 用户配置的插槽值"""
    defaults = dict(DEFAULT_SLOTS)
    user = _load_slots_from_config()
    defaults.update(user)
    return defaults


def save_slots(slots: dict):
    """保存插槽（只保存用户有定义的字段）"""
    clean = {k: v for k, v in slots.items() if k in DEFAULT_SLOTS and v}
    _save_slots_to_config(clean)


def get_selected_preset() -> str:
    try:
        from config import load_config
        return load_config().get("prompt_selected_preset", "default")
    except Exception:
        return "default"


def set_selected_preset(key: str):
    try:
        from config import load_config, save_config
        cfg = load_config()
        cfg["prompt_selected_preset"] = key
        save_config(cfg)
    except Exception:
        pass


def apply_preset(key: str):
    """应用预设到插槽，并保存"""
    presets = get_all_presets()
    if key not in presets:
        return False
    slots = presets[key].get("slots", {})
    save_slots(slots)
    set_selected_preset(key)
    return True


# ═══════════════ 第二轮作答 prompt 构建 ═══════════════

def build_second_pass_prompt(context: str, question: str, kb: str = "",
                             cite_format: str = None, output_style: str = None,
                             fallback: str = None) -> str:
    """
    构建第二轮作答的系统提示。
    框架由 SECOND_PASS_TEMPLATE（锁定）决定，
    3 个插槽从用户配置读取，也可直接传入覆盖。
    """
    slots = load_slots()
    return SECOND_PASS_TEMPLATE.format(
        cite_format=cite_format or slots.get("cite_format", DEFAULT_SLOTS["cite_format"]),
        output_style=output_style or slots.get("output_style", DEFAULT_SLOTS["output_style"]),
        fallback=fallback or slots.get("fallback", DEFAULT_SLOTS["fallback"]),
        context=context,
        question=question,
        kb=kb,
    )


# ═══════════════ 旧版兼容（供 rag_core/rag_standalone 使用） ═══════════════

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
    if not persona_text:
        return ""
    return persona_text


# ═══════════════ 自定义预设 CRUD ═══════════════

def _load_custom_presets() -> dict:
    if not os.path.exists(CUSTOM_PRESETS_FILE):
        return {}
    try:
        with open(CUSTOM_PRESETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_custom_presets(data: dict):
    tmp = CUSTOM_PRESETS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CUSTOM_PRESETS_FILE)
    except OSError:
        pass


def get_all_presets() -> dict:
    """合并内置 + 自定义预设，返回 slots 格式"""
    result = {}
    for key, p in PROMPT_PRESETS.items():
        result[key] = {**p, "built_in": True}
    for key, p in _load_custom_presets().items():
        result[key] = {**p, "built_in": False}
    return result


def save_custom_preset(label: str, slots: dict, description: str = "") -> dict:
    """保存一条自定义预设（slots 格式）"""
    if not label or not slots:
        return {"success": False, "error": "名称和插槽不能为空"}
    import time
    key = f"custom_{int(time.time())}"
    presets = _load_custom_presets()
    presets[key] = {"label": label, "description": description or "", "slots": slots}
    _save_custom_presets(presets)
    return {"success": True, "key": key, "label": label}


def delete_custom_preset(key: str) -> dict:
    if not key or key in PROMPT_PRESETS:
        return {"success": False, "error": "内置预设不可删除"}
    presets = _load_custom_presets()
    if key not in presets:
        return {"success": False, "error": "预设不存在"}
    del presets[key]
    _save_custom_presets(presets)
    return {"success": True}
