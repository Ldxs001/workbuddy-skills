"""
tools/file_tool.py — 文件操作工具
"""

import os
from ..tool_base import BaseTool, ToolResult


class ReadFileTool(BaseTool):
    """读取本地文件"""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="读取本地文件内容。支持 txt, md, py, json, yaml, log 等纯文本格式。",
        )

    def execute(self, path: str = "", max_chars: int = 5000) -> ToolResult:
        if not path.strip():
            return ToolResult(False, error="文件路径不能为空")
        if not os.path.exists(path):
            return ToolResult(False, error=f"文件不存在: {path}")
        if not os.path.isfile(path):
            return ToolResult(False, error=f"路径不是文件: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
            return ToolResult(
                True,
                output=f"文件 {path}:\n\n{content}",
                data={"path": path, "content": content},
            )
        except Exception as e:
            return ToolResult(False, error=f"读取失败: {e}")

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件绝对路径"},
                    "max_chars": {
                        "type": "integer",
                        "description": "最多读取字符数（可选，默认 5000）",
                    },
                },
                "required": ["path"],
            },
        }


class WriteFileTool(BaseTool):
    """写入本地文件"""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="将内容写入本地文件。会覆盖已存在的文件。",
        )

    def execute(self, path: str = "", content: str = "") -> ToolResult:
        if not path.strip():
            return ToolResult(False, error="文件路径不能为空")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(True, output=f"文件已写入: {path}")
        except Exception as e:
            return ToolResult(False, error=f"写入失败: {e}")

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件绝对路径"},
                    "content": {"type": "string", "description": "要写入的文件内容"},
                },
                "required": ["path", "content"],
            },
        }


class ListDirTool(BaseTool):
    """列出目录内容"""

    def __init__(self):
        super().__init__(
            name="list_directory",
            description="列出指定目录下的文件和子目录。",
        )

    def execute(self, path: str = ".", max_items: int = 50) -> ToolResult:
        try:
            entries = os.listdir(path)
            entries.sort()
            if len(entries) > max_items:
                entries = entries[:max_items]
                suffix = f"\n... 及另外 {len(os.listdir(path)) - max_items} 项"
            else:
                suffix = ""
            lines = []
            for e in entries:
                full = os.path.join(path, e)
                tag = "📁" if os.path.isdir(full) else "📄"
                lines.append(f"  {tag} {e}")
            return ToolResult(
                True,
                output=f"目录 {path}:\n" + "\n".join(lines) + suffix,
            )
        except Exception as e:
            return ToolResult(False, error=f"列出目录失败: {e}")

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径（可选，默认当前目录）"},
                    "max_items": {
                        "type": "integer",
                        "description": "最多显示条目数（可选，默认 50）",
                    },
                },
            },
        }
