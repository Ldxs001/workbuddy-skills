"""
tool_base.py — 工具抽象基类

所有工具继承 BaseTool，实现 execute() 和 get_schema()。
"""

from abc import ABC, abstractmethod
from typing import Any


class ToolResult:
    """工具执行结果"""

    def __init__(
        self,
        success: bool,
        output: str = "",
        error: str = "",
        data: Any = None,
    ):
        self.success = success
        self.output = output
        self.error = error
        self.data = data

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"[错误] {self.error}"

    def to_observation(self) -> str:
        """格式化为 ReAct 观察文本"""
        if self.success:
            return f"观察结果:\n{self.output[:3000]}"
        return f"工具执行错误: {self.error}"


class BaseTool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具，返回 ToolResult"""
        ...

    def get_schema(self) -> dict:
        """
        返回工具的 JSON schema，供 LLM 理解参数结构。
        子类可重写以提供更精确的 schema。
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }

    def get_react_description(self) -> str:
        """返回 ReAct prompt 中使用的工具描述字符串"""
        schema = self.get_schema()
        params = schema.get("parameters", {}).get("properties", {})
        param_lines = []
        for pname, pinfo in params.items():
            required = pname in schema.get("parameters", {}).get("required", [])
            flag = "（必填）" if required else "（可选）"
            param_lines.append(f"    - {pname}: {pinfo.get('description', '')} {flag}")
        param_str = "\n".join(param_lines) if param_lines else "    无参数"
        return f"- {self.name}: {self.description}\n{param_str}"
