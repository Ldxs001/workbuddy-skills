"""配置管理器 — 读写 config.json"""
import json
import copy
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

DEFAULT_CONFIG = {
    "planner_model": {
        "backend": "lmstudio",
        "base_url": "http://localhost:1234",
        "model": "",
        "timeout": 180,
        "max_tokens": 4096,
        "temperature": 0.6
    },
    "writer_model": {
        "backend": "lmstudio",
        "base_url": "http://localhost:1234",
        "model": "",
        "timeout": 300,
        "max_tokens": 8192,
        "temperature": 0.7
    },
    "default_prompt": "请以专业、客观、结构清晰的风格撰写。注重逻辑递进和数据支撑。使用Markdown格式。",
    "selected_template": "通用公文",
    "rag_path": "",
    "context_review_length": 8000,
    "fact_check_enabled": False,
    "max_sessions": 20,
    "templates": {}
}


class ConfigManager:
    def __init__(self, config_path=None):
        self.path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config = None
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            # 合并默认值：旧文件缺少的新配置项自动补上
            for k, v in DEFAULT_CONFIG.items():
                if k not in self._config:
                    self._config[k] = copy.deepcopy(v)
                elif isinstance(v, dict) and isinstance(self._config[k], dict):
                    # 深层合并：嵌套 dict 中新 key 也补上
                    for sk, sv in v.items():
                        if sk not in self._config[k]:
                            self._config[k][sk] = copy.deepcopy(sv)
            # ── 硬保护：确保"自定义"模板始终存在 ──
            templates = self._config.get("templates", {})
            if "自定义" not in templates:
                templates["自定义"] = {
                    "meta": [{"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto"}],
                    "content": [{"name": "正文", "show_label": False, "desc": "文章主体内容", "source": "llm", "type": "section"}],
                    "style": "",
                    "logic": ""
                }
                self._config["templates"] = templates
                migrated = True
            # ── 旧格式迁移 ──
            templates = self._config.get("templates", {})
            migrated = False
            for tname, tval in list(templates.items()):
                if isinstance(tval, str):  # 最旧格式：纯字符串 → structure → meta+content
                    structure = [
                        {"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto", "type": "leaf"},
                        {"name": "正文", "show_label": False, "desc": "文章主体", "source": "llm", "type": "section"},
                    ]
                    templates[tname] = _convert_structure_to_mc(structure, tval)
                    migrated = True
                elif isinstance(tval, dict) and "structure" in tval:  # structure 格式 → meta+content
                    style = tval.get("style", "")
                    templates[tname] = _convert_structure_to_mc(tval["structure"], style)
                    migrated = True
            if migrated:
                self._config["templates"] = templates
                self.save()

        else:
            self._config = copy.deepcopy(DEFAULT_CONFIG)
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value
        self.save()

    def get_all(self):
        return copy.deepcopy(self._config)

    def update(self, data: dict):
        """批量更新配置，支持新增键。templates 和 user_templates 做全量替换。"""
        for key in self._config:
            if key in data:
                if isinstance(data[key], dict) and isinstance(self._config[key], dict):
                    # templates 和 user_templates 全量替换（支持删除）
                    if key in ("templates", "user_templates"):
                        self._config[key] = copy.deepcopy(data[key])
                    else:
                        self._config[key].update(data[key])
                else:
                    self._config[key] = data[key]
        # 处理 data 中的新增键（不在 self._config 中）
        for key in data:
            if key not in self._config:
                self._config[key] = data[key]
        self.save()


def _convert_structure_to_mc(structure: list, style: str = "") -> dict:
    """将旧 flat structure 转换为 meta+content+logic"""
    meta = []
    content = []
    for f in structure:
        entry = {"name": f["name"], "show_label": f.get("show_label", False), "desc": f.get("desc", "")}
        source = f.get("source", "llm")
        if source in ("user", "auto"):
            entry["source"] = source
            meta.append(entry)
        else:
            entry["type"] = f.get("type", "section")
            content.append(entry)
    return {"meta": meta, "content": content, "style": style, "logic": ""}
