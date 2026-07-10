"""
agent_config.py — 智能体统一配置
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

DEFAULT_CONFIG = {
    # LLM 连接
    "llm": {
        "backend": "lmstudio",        # ollama / lmstudio / openai
        "base_url": "http://localhost:1234/v1",
        "api_key": "",
        "model_name": "",
        "temperature": 0.3,
        "max_tokens": 16384,
        "top_p": 0.9,
        "timeout": 180,
        # 各后端专属默认地址
        "ollama_url": "http://localhost:11434",
        "lmstudio_url": "http://localhost:1234",
    },
    # 智能体循环
    "agent": {
        "max_steps": 20,            # 最大思考-行动轮次
        "max_retries": 3,           # 工具调用失败重试次数
        "verbose": True,            # 打印思考过程
        "stop_on_tool_error": False,# 工具失败是否终止
    },
    # 记忆系统
    "memory": {
        "max_history": 20,          # 保留最近 N 轮对话
        "max_context_chars": 8000,  # 截断历史到最长字符数
        "working_memory_file": "working_memory.json",  # 工作记忆持久化
    },
    # RAG 工具
    "rag": {
        "skill_path": os.path.expanduser(
            "~/.workbuddy/skills/local-rag-builder"
        ),
        "default_kb": "default",
        "k": 5,                     # 默认检索条数
        "score_threshold": 0.0,     # 相似度阈值 0-1, 0 不限
    },
}


@dataclass
class AgentConfig:
    """智能体配置，支持 JSON 持久化"""
    data: dict = field(default_factory=lambda: DEFAULT_CONFIG)

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    @property
    def llm_backend(self) -> str:
        return self.data["llm"].get("backend", "lmstudio")

    @property
    def llm_base_url(self) -> str:
        return self.data["llm"]["base_url"]

    @property
    def llm_api_key(self) -> str:
        return self.data["llm"].get("api_key", "")

    @property
    def llm_model(self) -> str:
        return self.data["llm"].get("model_name", "")

    @property
    def llm_timeout(self) -> int:
        return self.data["llm"].get("timeout", 180)

    @property
    def llm_ollama_url(self) -> str:
        return self.data["llm"].get("ollama_url", "http://localhost:11434")

    @property
    def llm_lmstudio_url(self) -> str:
        return self.data["llm"].get("lmstudio_url", "http://localhost:1234")

    @property
    def llm_temperature(self) -> float:
        return self.data["llm"]["temperature"]

    @property
    def llm_max_tokens(self) -> int:
        return self.data["llm"]["max_tokens"]

    @property
    def llm_top_p(self) -> float:
        return self.data["llm"]["top_p"]

    # ------------------------------------------------------------------
    # Agent
    # ------------------------------------------------------------------
    @property
    def agent_max_steps(self) -> int:
        return self.data["agent"]["max_steps"]

    @property
    def agent_max_retries(self) -> int:
        return self.data["agent"]["max_retries"]

    @property
    def agent_verbose(self) -> bool:
        return self.data["agent"]["verbose"]

    @property
    def agent_stop_on_tool_error(self) -> bool:
        return self.data["agent"]["stop_on_tool_error"]

    @property
    def user_prompt(self) -> str:
        return self.data.get("prompt", {}).get("user", "")

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------
    @property
    def memory_max_history(self) -> int:
        return self.data["memory"]["max_history"]

    @property
    def memory_max_context_chars(self) -> int:
        return self.data["memory"]["max_context_chars"]

    @property
    def memory_working_file(self) -> str:
        return self.data["memory"]["working_memory_file"]

    # ------------------------------------------------------------------
    # RAG
    # ------------------------------------------------------------------
    @property
    def rag_skill_path(self) -> str:
        return self.data["rag"]["skill_path"]

    @property
    def rag_default_kb(self) -> str:
        return self.data["rag"]["default_kb"]

    @property
    def rag_k(self) -> int:
        return self.data["rag"]["k"]

    @property
    def rag_score_threshold(self) -> float:
        return self.data["rag"]["score_threshold"]

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "AgentConfig":
        """从 JSON 文件加载配置，缺失字段用默认值"""
        base = dict(DEFAULT_CONFIG)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)
            _deep_merge(base, user)
        return cls(base)

    def save(self, path: str):
        """保存配置到 JSON 文件"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def __getitem__(self, key):
        return self.data[key]


def _deep_merge(base: dict, override: dict):
    """递归合并字典"""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
