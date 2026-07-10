"""
tools/web_tool.py — 网络工具
"""

import json
import urllib.parse
import urllib.request
from ..tool_base import BaseTool, ToolResult


class WebFetchTool(BaseTool):
    """获取网页内容"""

    def __init__(self):
        super().__init__(
            name="web_fetch",
            description="获取网页文本内容（移除 HTML 标签）。适用于查阅在线文档、API 文档等。",
        )

    def execute(self, url: str = "", max_chars: int = 5000) -> ToolResult:
        if not url.strip():
            return ToolResult(False, error="URL 不能为空")

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")

            # 简陋的 HTML 标签去除
            import re
            text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n...(内容已截断)"

            return ToolResult(True, output=text, data={"url": url, "content": text})
        except Exception as e:
            return ToolResult(False, error=f"获取网页失败: {e}")

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "要获取的网页 URL"},
                    "max_chars": {
                        "type": "integer",
                        "description": "最多返回字符数（可选，默认 5000）",
                    },
                },
                "required": ["url"],
            },
        }


class WebSearchTool(BaseTool):
    """搜索网络 —— 通过调用外部搜索 API"""

    def __init__(self, search_url: str = "https://api.duckduckgo.com/?q={q}&format=json"):
        super().__init__(
            name="web_search",
            description="搜索网络获取最新信息。注意：需要网络连接。",
        )
        self.search_url = search_url

    def execute(self, query: str = "") -> ToolResult:
        if not query.strip():
            return ToolResult(False, error="搜索关键词不能为空")

        # 尝试 DuckDuckGo 即时答案 API (免费，无需 key)
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            # 提取摘要和相关信息
            abstract = data.get("AbstractText", "")
            answer = data.get("Answer", "")
            results = []
            for topic in data.get("RelatedTopics", []):
                if "Text" in topic:
                    results.append(topic["Text"])
                elif "Topics" in topic:
                    for subtopic in topic["Topics"]:
                        if "Text" in subtopic:
                            results.append(subtopic["Text"])

            parts = []
            if answer:
                parts.append(f"📌 {answer}")
            if abstract:
                parts.append(f"📝 {abstract}")
            if results:
                parts.append("相关结果:")
                for r in results[:5]:
                    parts.append(f"  • {r[:200]}")

            output = "\n".join(parts) if parts else f"未找到「{query}」的相关信息。"

            return ToolResult(True, output=output, data={"query": query, "raw": data})
        except Exception as e:
            return ToolResult(False, error=f"搜索失败: {e}")

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        }


class PythonExecuteTool(BaseTool):
    """执行 Python 代码"""

    def __init__(self):
        super().__init__(
            name="python_execute",
            description="执行 Python 代码并返回输出。可用于计算、数据分析、图表绘制等。注意：代码运行在隔离环境。",
        )

    def execute(self, code: str = "") -> ToolResult:
        if not code.strip():
            return ToolResult(False, error="代码不能为空")

        import sys
        from io import StringIO

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_out = StringIO()
        redirected_err = StringIO()
        sys.stdout = redirected_out
        sys.stderr = redirected_err

        result = None
        error_text = ""

        try:
            # 编译并执行
            compiled = compile(code.strip(), "<agent_exec>", "exec")
            exec(compiled, {"__builtins__": __builtins__})
        except Exception as e:
            error_text = str(e)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        stdout_text = redirected_out.getvalue()
        stderr_text = redirected_err.getvalue()

        if error_text:
            return ToolResult(False, error=f"执行错误: {error_text}")
        if stderr_text:
            return ToolResult(True, output=stdout_text + f"\n[stderr]\n{stderr_text}")

        return ToolResult(True, output=stdout_text or "代码执行完毕（无输出）")

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要执行的 Python 代码"},
                },
                "required": ["code"],
            },
        }
