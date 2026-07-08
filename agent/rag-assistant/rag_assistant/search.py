"""
联网搜索回退模块
RAG 结果不足时触发，搜索内容与 RAG 结果融合后交由 LLM 处理
"""
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)


class WebSearch:
    """联网搜索（回退用）"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("web_search_enabled", True)
        self.api_key = self.config.get("web_search_api_key", "")
        self.search_engine = self.config.get("web_search_engine", "duckduckgo")

    def search(self, query: str, max_results: int = 5) -> dict:
        """
        执行联网搜索
        返回: {"results": list, "success": bool, "error": str}
        """
        if not self.enabled:
            return {"results": [], "success": False, "error": "联网搜索已禁用"}

        try:
            if self.search_engine == "duckduckgo":
                return self._search_duckduckgo(query, max_results)
            elif self.search_engine == "tavily":
                return self._search_tavily(query, max_results)
            else:
                return self._search_duckduckgo(query, max_results)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"results": [], "success": False, "error": str(e)}

    def _search_duckduckgo(self, query: str, max_results: int) -> dict:
        """DuckDuckGo 搜索（无需 API Key）"""
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                formatted = []
                for r in results:
                    formatted.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
                return {"results": formatted, "success": True}
        except ImportError:
            logger.warning("duckduckgo_search 未安装，尝试 urllib 回退")
            return self._search_fallback(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> dict:
        """Tavily 搜索（需 API Key）"""
        if not self.api_key:
            return {"results": [], "success": False, "error": "Tavily API Key 未配置"}
        try:
            import requests
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": self.api_key, "query": query, "max_results": max_results},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"results": data.get("results", []), "success": True}
        except Exception as e:
            logger.error(f"Tavily 搜索失败: {e}")
            return {"results": [], "success": False, "error": str(e)}

    def _search_fallback(self, query: str, max_results: int) -> dict:
        """纯 urllib 回退（Google 抓取）"""
        import urllib.parse
        import urllib.request
        import re

        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # 简单解析搜索结果
            results = []
            for match in re.finditer(
                r'<a rel="nofollow" href="(.*?)".*?class="result__a".*?>(.*?)</a>.*?class="result__snippet".*?>(.*?)</',
                html, re.DOTALL
            ):
                results.append({
                    "title": re.sub(r"<.*?>", "", match.group(2)).strip(),
                    "url": match.group(1),
                    "snippet": re.sub(r"<.*?>", "", match.group(3)).strip(),
                })
                if len(results) >= max_results:
                    break

            return {"results": results, "success": bool(results)}
        except Exception as e:
            return {"results": [], "success": False, "error": str(e)}
