"""
联网搜索回退模块
RAG 结果不足时触发，搜索内容与 RAG 结果融合后交由 LLM 处理
支持：DuckDuckGo / Tavily / Google Custom Search / Bing Search / 自定义 API
"""
import logging
import json
import urllib.parse
import urllib.request
import re
from typing import Optional

logger = logging.getLogger(__name__)


class WebSearch:
    """联网搜索（回退用）"""

    # 常见嵌入模型 → 向量维度
    BACKEND_LABELS = {
        "duckduckgo": "DuckDuckGo（免费，无需 Key）",
        "tavily": "Tavily（需 API Key）",
        "google": "Google Custom Search（需 API Key + CX）",
        "bing": "Bing Search（需 API Key）",
        "custom": "自定义 API",
    }

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("web_search_enabled", False)
        search = self.config.get("search", {})
        self.backend = search.get("backend", "duckduckgo")
        self.api_key = search.get("api_key", "")
        self.google_key = search.get("google_key", "")
        self.google_cx = search.get("google_cx", "")
        self.bing_key = search.get("bing_key", "")
        self.custom_url = search.get("custom_url", "")

    def search(self, query: str, max_results: int = 5) -> dict:
        """
        执行联网搜索
        返回: {"results": list, "success": bool, "error": str}
        """
        if not self.enabled:
            return {"results": [], "success": False, "error": "联网搜索已禁用"}

        try:
            if self.backend == "duckduckgo":
                return self._search_duckduckgo(query, max_results)
            elif self.backend == "tavily":
                return self._search_tavily(query, max_results)
            elif self.backend == "google":
                return self._search_google(query, max_results)
            elif self.backend == "bing":
                return self._search_bing(query, max_results)
            elif self.backend == "custom":
                return self._search_custom(query, max_results)
            else:
                return self._search_duckduckgo(query, max_results)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"results": [], "success": False, "error": str(e)}

    def _search_duckduckgo(self, query: str, max_results: int) -> dict:
        """DuckDuckGo 搜索（无需 API Key）"""
        try:
            from duckduckgo_search import DDGS
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

    def _search_google(self, query: str, max_results: int) -> dict:
        """Google Custom Search JSON API"""
        if not self.google_key or not self.google_cx:
            return {"results": [], "success": False, "error": "Google API Key 或 CX 未配置"}
        try:
            import requests
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_key,
                "cx": self.google_cx,
                "q": query,
                "num": min(max_results, 10),
            }
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            formatted = []
            for item in items:
                formatted.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })
            return {"results": formatted, "success": True}
        except Exception as e:
            logger.error(f"Google 搜索失败: {e}")
            return {"results": [], "success": False, "error": str(e)}

    def _search_bing(self, query: str, max_results: int) -> dict:
        """Bing Search API v7"""
        if not self.bing_key:
            return {"results": [], "success": False, "error": "Bing API Key 未配置"}
        try:
            import requests
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": self.bing_key}
            params = {"q": query, "count": min(max_results, 50)}
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("webPages", {}).get("value", [])
            formatted = []
            for item in items:
                formatted.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                })
            return {"results": formatted, "success": True}
        except Exception as e:
            logger.error(f"Bing 搜索失败: {e}")
            return {"results": [], "success": False, "error": str(e)}

    def _search_custom(self, query: str, max_results: int) -> dict:
        """自定义 API 搜索（URL 中用 {q} 和 {key} 占位）"""
        if not self.custom_url:
            return {"results": [], "success": False, "error": "自定义 API URL 未配置"}
        try:
            import requests
            url = self.custom_url.replace("{q}", urllib.parse.quote(query)).replace("{key}", self.api_key or "")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # 尝试常见返回格式
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = (data.get("results") or data.get("items") or data.get("data") or [])
            formatted = []
            for item in items[:max_results]:
                if isinstance(item, str):
                    formatted.append({"title": "", "url": "", "snippet": item})
                elif isinstance(item, dict):
                    formatted.append({
                        "title": item.get("title", item.get("name", "")),
                        "url": item.get("url", item.get("link", "")),
                        "snippet": item.get("snippet", item.get("body", item.get("description", ""))),
                    })
            return {"results": formatted, "success": True}
        except Exception as e:
            logger.error(f"自定义搜索失败: {e}")
            return {"results": [], "success": False, "error": str(e)}

    def _search_fallback(self, query: str, max_results: int) -> dict:
        """纯 urllib 回退（DuckDuckGo HTML 抓取）"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")

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
