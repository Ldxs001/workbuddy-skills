"""配置管理器 — 读写 config.json + data/templates/user_templates.json"""
import json
import copy
import os
from pathlib import Path

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
USER_TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "data" / "templates" / "user_templates.json"

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
}

# ── 内置模板（代码级只读，永不写入文件） ──

DEFAULT_TEMPLATES = {
    "日常写作": {
        "meta": [{"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto"}],
        "content": [{"name": "正文", "show_label": False, "desc": "文章主体内容，需层次分明", "type": "section"}, {"name": "结尾", "show_label": False, "desc": "收束总结或开放式结束语", "type": "leaf"}],
        "style": "日常交流风格，自然流畅，平实易懂。适当使用口语化但不失条理。",
        "logic": ""
    },
    "学术论文": {
        "meta": [{"name": "标题", "show_label": True, "desc": "论文标题，应准确反映研究内容", "source": "auto"}, {"name": "作者", "show_label": True, "desc": "作者姓名及单位", "source": "user"}, {"name": "单位", "show_label": True, "desc": "通讯地址和邮箱", "source": "user"}],
        "content": [
            {"name": "关键词", "show_label": False, "desc": "仅输出3-5个关键词（用逗号分隔），不要段落，不要多余文字", "type": "leaf", "logical_order": 2},
            {"name": "摘要", "show_label": True, "desc": "论文核心内容概括，200-300字", "type": "leaf", "logical_order": 2},
            {"name": "引言", "show_label": True, "desc": "研究背景、问题提出、文献综述、研究意义", "type": "section"},
            {"name": "方法", "show_label": True, "desc": "研究设计、实验方法、数据采集与分析方法", "type": "section"},
            {"name": "结果", "show_label": True, "desc": "实验结果与数据分析，图表支撑", "type": "section"},
            {"name": "讨论", "show_label": True, "desc": "结果解读、与前人工作对比、研究局限", "type": "section"},
            {"name": "结论", "show_label": True, "desc": "主要发现总结、研究贡献、未来方向", "type": "section"},
            {"name": "参考文献", "show_label": True, "desc": "引用文献完整列表，每篇标注引用来源", "type": "leaf", "logical_order": 2, "citation_check": True, "citation_format": "[x]=1."}
        ],
        "style": "学术严谨风格，客观中立，措辞精准，论据充分，引用规范。使用第三人称和被动语态。段落逻辑严密，数据支撑充分。",
        "logic": "按 IMRaD 顺序撰写：引言→方法→结果→讨论→结论；摘要、关键词、参考文献在正文完成后最后产出。注意引用标记的对应关系，引用来源标注为目标文件名。"
    },
    "正式公文": {
        "meta": [{"name": "标题", "show_label": True, "desc": "公文标题，应准确概括文件主旨", "source": "auto"}, {"name": "发文机关", "show_label": True, "desc": "发文单位全称或规范简称", "source": "user"}, {"name": "文号", "show_label": True, "desc": "公文编号如'X发〔2024〕XX号'", "source": "user"}, {"name": "密级", "show_label": True, "desc": "秘密/机密/绝密/普通", "source": "user"}, {"name": "抄送", "show_label": True, "desc": "抄送机关名称", "source": "user"}],
        "content": [{"name": "前言", "show_label": True, "desc": "行文依据、目的和背景", "type": "section"}, {"name": "主体", "show_label": True, "desc": "公文核心内容，分条陈述", "type": "section"}, {"name": "执行要求", "show_label": True, "desc": "落实要求、时限、联系方式等", "type": "section"}],
        "style": "正式、严谨、规范的公文风格。用语简练准确，条理清晰；层次分明，多用'一、二、三'分条；立场客观，表述权威，体现公文严肃性。",
        "logic": ""
    },
    "新闻报道": {
        "meta": [{"name": "标题", "show_label": True, "desc": "新闻标题，应吸引读者并概括核心", "source": "auto"}, {"name": "作者", "show_label": True, "desc": "记者或撰稿人姓名", "source": "user"}],
        "content": [{"name": "导语", "show_label": True, "desc": "新闻核心要素：5W1H，一句话概括", "type": "leaf"}, {"name": "正文", "show_label": True, "desc": "按重要性递减展开细节，倒金字塔结构", "type": "section"}, {"name": "背景", "show_label": False, "desc": "相关背景信息，供参考", "type": "section", "logical_order": 2}],
        "style": "新闻报道风格。导语一句话概括核心5W1H；正文按倒金字塔结构排列，最重要的信息最前；语言客观简洁，直接引语增强可信度；避免主观评价。",
        "logic": "导语和正文优先写，背景在最后补充。"
    },
    "技术报告": {
        "meta": [{"name": "标题", "show_label": True, "desc": "报告标题", "source": "auto"}, {"name": "作者", "show_label": True, "desc": "报告撰写人", "source": "user"}, {"name": "版本号", "show_label": True, "desc": "文档版本标识", "source": "auto"}],
        "content": [{"name": "背景", "show_label": True, "desc": "项目背景、目标和范围", "type": "section"}, {"name": "技术方案", "show_label": True, "desc": "技术架构设计、实现细节", "type": "section"}, {"name": "关键数据", "show_label": True, "desc": "性能数据、测试结果、对比分析", "type": "section"}, {"name": "下一步计划", "show_label": True, "desc": "后续工作计划和改进方向", "type": "section"}],
        "style": "技术文档风格。语言精确，数据驱动；善用图表、代码片段、数据对比增强说服力；逻辑从问题→方案→验证→展望递进；避免模糊描述。",
        "logic": ""
    },
    "通用公文": {
        "meta": [{"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto"}],
        "content": [{"name": "正文", "show_label": False, "desc": "主体内容", "type": "section"}, {"name": "结尾", "show_label": False, "desc": "收束语、执行要求或落款", "type": "leaf"}],
        "style": "正式、简洁、条理清晰的公文风格。用语规范，逻辑严密。",
        "logic": ""
    },
    "论文综述": {
        "meta": [{"name": "标题", "show_label": True, "desc": "综述标题", "source": "auto"}, {"name": "作者", "show_label": True, "desc": "作者姓名", "source": "user"}],
        "content": [
            {"name": "摘要", "show_label": True, "desc": "综述核心内容概括，200-300字", "type": "leaf", "logical_order": 2},
            {"name": "引言", "show_label": True, "desc": "研究背景、综述范围与目的、文献检索策略", "type": "section"},
            {"name": "分主题评述", "show_label": True, "desc": "按主题聚类组织文献，每个主题独立成节，包含核心发现、进展与争议", "type": "section"},
            {"name": "研究空白与展望", "show_label": True, "desc": "现有研究不足、未解决问题、未来研究方向", "type": "section"},
            {"name": "参考文献", "show_label": True, "desc": "引用文献完整列表，每篇标注引用来源", "type": "leaf", "logical_order": 2, "citation_check": True, "citation_format": "[x]=1."}
        ],
        "style": "学术综述风格。对现有文献进行系统梳理和批判性评价；按主题聚类而非简单罗列；指出研究空白和争议点；客观公正，不偏颇。",
        "logic": "正文优先撰写（引言→分主题评述→研究空白与展望），摘要和参考文献最后完成。注意引用标记的对应关系，引用来源标注为目标文件名。"
    },
    "自定义": {
        "meta": [{"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto"}],
        "content": [{"name": "正文", "show_label": False, "desc": "文章主体内容", "source": "llm", "type": "section"}],
        "style": "",
        "logic": ""
    },
}

BUILTIN_TEMPLATE_NAMES = set(DEFAULT_TEMPLATES.keys())


class ConfigManager:
    def __init__(self, config_path=None):
        self.path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config = None
        self.load()

    def _load_user_templates(self) -> dict:
        """从 data/templates/user_templates.json 加载用户自定义模板"""
        if USER_TEMPLATES_PATH.exists():
            try:
                with open(USER_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_user_templates(self, templates: dict):
        """保存用户自定义模板到 data/templates/user_templates.json"""
        USER_TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = USER_TEMPLATES_PATH.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
        tmp.replace(USER_TEMPLATES_PATH)

    def _migrate_old_templates(self):
        """从 config.json 迁移旧模板到 data/templates/user_templates.json"""
        old_templates = self._config.get("templates", {})
        old_user_templates = self._config.get("user_templates", {})
        if not old_templates and not old_user_templates:
            return

        # 取出用户自定义的模板（不在内置中的 + user_templates 标记的）
        migrated = {}
        for name, tval in old_templates.items():
            if name not in BUILTIN_TEMPLATE_NAMES or name in old_user_templates:
                # 处理旧格式
                if isinstance(tval, str):
                    migrated[name] = {
                        "meta": [{"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto", "type": "leaf"}],
                        "content": [{"name": "正文", "show_label": False, "desc": "文章主体", "source": "llm", "type": "section"}],
                        "style": tval, "logic": ""
                    }
                elif isinstance(tval, dict) and "structure" in tval:
                    migrated[name] = _convert_structure_to_mc(tval["structure"], tval.get("style", ""))
                elif isinstance(tval, dict) and ("meta" in tval or "content" in tval):
                    migrated[name] = tval

        # 兼容旧 user_templates 中标记但 templates 中不存在的模板
        for name in old_user_templates:
            if name not in migrated and name not in BUILTIN_TEMPLATE_NAMES:
                migrated[name] = {
                    "meta": [{"name": "标题", "show_label": False, "desc": "文章标题", "source": "auto"}],
                    "content": [{"name": "正文", "show_label": False, "desc": "文章主体内容", "type": "section"}],
                    "style": "", "logic": ""
                }

        if migrated:
            existing = self._load_user_templates()
            existing.update(migrated)
            self._save_user_templates(existing)

        # 清理 config.json 中的旧模板字段
        if "templates" in self._config:
            del self._config["templates"]
        if "user_templates" in self._config:
            del self._config["user_templates"]
        self.save()

    def load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            # 合并默认值
            for k, v in DEFAULT_CONFIG.items():
                if k not in self._config:
                    self._config[k] = copy.deepcopy(v)
                elif isinstance(v, dict) and isinstance(self._config[k], dict):
                    for sk, sv in v.items():
                        if sk not in self._config[k]:
                            self._config[k][sk] = copy.deepcopy(sv)

            # 迁移旧模板
            self._migrate_old_templates()
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
        if key == "templates":
            return self.get_all_templates()
        return self._config.get(key, default)

    def set(self, key, value):
        if key == "templates":
            user_only = {}
            for name, tpl in value.items():
                if name not in BUILTIN_TEMPLATE_NAMES:
                    user_only[name] = tpl
            self._save_user_templates(user_only)
            return
        self._config[key] = value
        self.save()

    def get_all(self):
        """返回完整配置（含合并后的 templates）"""
        result = copy.deepcopy(self._config)
        result["templates"] = self.get_all_templates()
        # 加入内置模板名称列表供前端判断只读
        result["builtin_templates"] = sorted(BUILTIN_TEMPLATE_NAMES)
        result["_template_source"] = "separated"
        # 兼容旧前端——标记哪些模板是内置的
        return result

    def get_all_templates(self) -> dict:
        """合并内置模板 + 用户自定义模板，用户模板覆盖同名内置"""
        merged = dict(DEFAULT_TEMPLATES)
        user_tpls = self._load_user_templates()
        merged.update(user_tpls)
        return merged

    def update(self, data: dict):
        """批量更新配置。templates 字段只保存用户自定义部分。"""
        for key in self._config:
            if key in data:
                if isinstance(data[key], dict) and isinstance(self._config[key], dict):
                    if key in ("templates",):
                        continue  # 跳过，单独处理
                    self._config[key].update(data[key])
                else:
                    self._config[key] = data[key]

        # 处理 templates：只保存用户自定义的
        if "templates" in data:
            user_only = {}
            for name, tpl in data["templates"].items():
                if name not in BUILTIN_TEMPLATE_NAMES:
                    user_only[name] = tpl
            self._save_user_templates(user_only)

        # 处理新增键
        for key in data:
            if key not in self._config and key != "templates":
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
