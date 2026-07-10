"""
memory.py — 智能体记忆系统

两层记忆：
  1. 短期记忆（会话内）：对话历史 + 思考轨迹
  2. 工作记忆（持久化）：关键事实、用户偏好、任务状态
"""

import json
import os
from typing import Optional

from .agent_config import AgentConfig


class WorkingMemory:
    """
    工作记忆 —— 持久化到 JSON 文件。

    存储：
      - 用户偏好（preferences）
      - 关键事实（facts）
      - 活跃任务（tasks）
      - 上下文标签（tags）
    """

    def __init__(self, config: AgentConfig):
        self.file_path = config.memory_working_file
        self.data: dict = {"preferences": {}, "facts": [], "tasks": [], "tags": []}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except (json.JSONDecodeError, Exception):
                pass

    def save(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)) or ".", exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_fact(self, fact: str):
        """添加关键事实"""
        if fact not in self.data["facts"]:
            self.data["facts"].append(fact)
            self.save()

    def set_preference(self, key: str, value: str):
        """设置用户偏好"""
        self.data["preferences"][key] = value
        self.save()

    def add_task(self, task: str, status: str = "pending"):
        """添加任务"""
        self.data["tasks"].append({"task": task, "status": status})
        self.save()

    def add_tag(self, tag: str):
        """添加上下文标签"""
        if tag not in self.data["tags"]:
            self.data["tags"].append(tag)
            self.save()

    def to_text(self) -> str:
        """格式化为 LLM 可读的文本"""
        parts = []
        if self.data["preferences"]:
            parts.append("用户偏好:")
            for k, v in self.data["preferences"].items():
                parts.append(f"  {k}: {v}")
        if self.data["facts"]:
            parts.append("\n关键事实:")
            for f in self.data["facts"]:
                parts.append(f"  • {f}")
        if self.data["tasks"]:
            parts.append("\n活跃任务:")
            for t in self.data["tasks"]:
                parts.append(f"  [{t['status']}] {t['task']}")
        return "\n".join(parts)


class ConversationMemory:
    """
    短期记忆 —— 对话历史管理。

    自动截断到 max_history 轮和 max_context_chars 字符。
    """

    def __init__(self, config: AgentConfig):
        self.max_history = config.memory_max_history
        self.max_chars = config.memory_max_context_chars
        self.history: list[dict] = []  # [{"role": "user"/"assistant", "content": ...}]

    def add_user(self, content: str):
        self.history.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content: str):
        self.history.append({"role": "assistant", "content": content})
        self._trim()

    def add_system(self, content: str):
        self.history.append({"role": "system", "content": content})

    def _trim(self):
        """裁剪至 max_history 且总字符不超过 max_chars"""
        # 保留系统消息
        system_msgs = [m for m in self.history if m["role"] == "system"]
        non_system = [m for m in self.history if m["role"] != "system"]

        # 按轮次裁剪
        if len(non_system) > self.max_history:
            non_system = non_system[-self.max_history:]

        # 按字符数裁剪
        total = sum(len(m["content"]) for m in system_msgs + non_system)
        while total > self.max_chars and len(non_system) > 2:
            removed = non_system.pop(0)
            total -= len(removed["content"])

        self.history = system_msgs + non_system

    def get_messages(self) -> list[dict]:
        return list(self.history)

    def get_recent(self, n: int = 5) -> list[dict]:
        """获取最近 N 轮"""
        return self.history[-n * 2:]  # 每轮 user+assistant 两条

    def clear(self):
        self.history = []

    def __len__(self):
        return len(self.history)
