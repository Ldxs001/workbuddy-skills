"""
local-rag-builder 配置管理模块
v0.1.0
"""

import os
import sys
from utils import cfg_dir, safe_json_load, safe_json_dump

DEFAULT_CONFIG = {
    "mode": "integrated",
    "input_sources": {
        "enable_pdf": False,
        "enable_ocr": False,
        "enable_html2md": False,
        "pdf_backend": "pypdf",  # pypdf / pdfplumber
    },
    "splitting": {
        "strategy": "recursive",
        "chunk_size": 500,
        "chunk_overlap": 50,
        "separators": ["\n\n", "\n", "。", "；", "，", " ", ""],
        "headers_to_split_on": [["#", "h1"], ["##", "h2"], ["###", "h3"]],
        "strip_headers": False,
        "semantic_breakpoint": "percentile",
        "secondary_strategy": None,
        "guards": ["code"],
        "strategy_overrides": {
            "headers": {"chunk_size": None, "chunk_overlap": None},
            "semantic": {"chunk_size": None, "chunk_overlap": None},
            "sentence": {"chunk_size": None, "chunk_overlap": None},
        },
    },
    "router": {
        "enabled": True,
        "fallback": {
            "enabled": True,
            "model_path": "",
            "min_score_threshold": 0.3,
            "broadcast_on_fail": True,
            "auto_update_signatures": True,
            "signature_auto_rebuild": False,
        },
    },
    "reranker": {
        "enabled": False,
        "mode": "model",
        "model_path": "",
        "top_k": 5,
        "sort_rules": [],
    },
    "nli": {
        "enabled": False,
        "output_enabled": False,
        "model_path": "MoritzLaurer/mDeBERTa-v3-base-xnli",
        "top_k": 0,
    },
    "memory": {
        "compress_ratio": 0.7,
        "compress_remove_ratio": 0.4,
        "max_sessions": 20,
    },
    "retrieval": {
        "k": 3,
        "score_threshold": None,
        "search_type": "similarity",
    },
    "llm": {
        "base_url": "http://localhost:1234/v1",
        "api_key": "not-needed",
        "backend": "ollama",
        "model": "",
        "temperature": 0.1,
        "max_tokens": 4096,
        "timeout": 180,
    },
    "kb": {
        "active_kb": "default",
        "auto_classify": False,
        "min_import_score": 0.4,
    },
    "prompt": {
        "template_file": "default_template.txt",
    },
}


def get_config_path():
    return os.path.join(cfg_dir, "rag_config.json")


def load_config():
    """加载配置，不存在则返回默认"""
    cfg = safe_json_load(get_config_path())
    if cfg is None:
        return DEFAULT_CONFIG.copy()
    # 合并缺失的默认字段（兼容顶层非 dict 字段）
    merged = DEFAULT_CONFIG.copy()
    needs_save = False
    if isinstance(cfg, dict):
        for k, v in cfg.items():
            if k in DEFAULT_CONFIG and isinstance(DEFAULT_CONFIG[k], dict) and isinstance(v, dict):
                merged[k].update(v)
                for sk, sv in DEFAULT_CONFIG[k].items():
                    if sk not in v:
                        merged[k][sk] = sv
            else:
                merged[k] = v

        # 迁移旧版顶层 LLM key 到 llm 子字典（覆盖默认值）
        llm = merged.setdefault("llm", {})
        for old_key, new_key in [("llm_backend", "backend"), ("llm_model", "model"),
                                  ("llm_timeout", "timeout"), ("llm_max_tokens", "max_tokens")]:
            if old_key in merged:
                llm[new_key] = merged.pop(old_key)
                needs_save = True
        llm.pop("model_name", None)

    if needs_save:
        try:
            safe_json_dump(merged, get_config_path())
        except Exception:
            pass

    # ═══════════ 模型路径自动修正 ═══════════
    # 如果配置的模型路径无效（空/不存在/未下载），且有已下载的同类型模型，自动用第一个
    try:
        from embedding_model_manager import list_downloaded_models as _list_dl
        _dl = _list_dl()
        if _dl:
            _dl_ids = {m["model_id"] for m in _dl}
            # 类型映射：config section → model_index type
            _type_map = {"embedding": "embedding", "reranker": "rerank", "nli": "nli"}
            for _section, _key in [("embedding", "model_path"), ("reranker", "model_path"), ("nli", "model_path")]:
                _path = merged.get(_section, {}).get(_key, "")
                # 检查路径是否有效（在已下载列表中或是本地路径）
                _valid = _path and (_path in _dl_ids or os.path.exists(_path))
                if not _valid:
                    _t = _type_map.get(_section)
                    _candidates = [m for m in _dl if m.get("type") == _t]
                    if _candidates:
                        merged.setdefault(_section, {})[_key] = _candidates[0]["model_id"]
    except Exception:
        pass

    return merged


def save_config(cfg):
    """保存配置"""
    try:
        safe_json_dump(cfg, get_config_path())
        return True
    except (OSError, IOError) as e:
        return False


def get_section(section_name):
    """获取配置中的某个 section"""
    try:
        cfg = load_config()
        return cfg.get(section_name, DEFAULT_CONFIG.get(section_name, {}))
    except Exception:
        return DEFAULT_CONFIG.get(section_name, {})


def update_section(section_name, updates):
    """更新配置中的某个 section"""
    try:
        cfg = load_config()
        if section_name not in cfg:
            cfg[section_name] = {}
        cfg[section_name].update(updates)
        save_config(cfg)
        return cfg[section_name]
    except (OSError, IOError, KeyError) as e:
        return DEFAULT_CONFIG.get(section_name, {})


def reset_config():
    """重置为默认配置"""
    save_config(DEFAULT_CONFIG.copy())
    return DEFAULT_CONFIG.copy()
