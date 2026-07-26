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
        "max_tokens": 4096
    },
    "writer_model": {
        "backend": "lmstudio",
        "base_url": "http://localhost:1234",
        "model": "",
        "timeout": 300,
        "max_tokens": 8192
    },
    "default_prompt": "请以专业、客观、结构清晰的风格撰写。注重逻辑递进和数据支撑。使用Markdown格式。",
    "selected_template": "通用公文",
    "rag_path": "",
    "templates": {
        "通用公文": "请以正式、客观、条理清晰的公文风格撰写。结构要求：前言说明背景和目的，正文分条列举事项和要求，结尾总结或提出执行要求。语言简洁庄重，不使用口语化表达。使用Markdown格式，各级标题用 #/##/###。",
        "新闻报道": "请以新闻写作风格撰写。采用倒金字塔结构：导语概括5W1H（时间、地点、人物、事件、原因、方式），正文按重要性递减展开细节。语言客观中立，引用需注明来源。使用Markdown格式。",
        "论文综述": "请以学术论文风格撰写。结构建议：摘要概括全文→引言说明研究背景和问题→分论点逐层论述→结论总结发现。要求逻辑严密，论证充分，引用规范，语言学术化。每节应有明确论点。使用Markdown格式。",
        "技术报告": "请以技术报告风格撰写。结构建议：背景与问题→技术方案与架构→关键数据与指标→对比分析→结论与建议。要求数据驱动，结论有据可循，可使用列表和表格。使用Markdown格式。",
        "自定义": ""
    }
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
        """批量更新配置，只覆盖存在的键"""
        for key in self._config:
            if key in data:
                if isinstance(data[key], dict) and isinstance(self._config[key], dict):
                    self._config[key].update(data[key])
                else:
                    self._config[key] = data[key]
        self.save()
