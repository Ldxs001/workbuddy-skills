"""
联网搜索插件 — 内置插件
复用 rag_assistant/search.py 的 WebSearch 后端
"""
import json
import logging
import os
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# 加项目根到 sys.path（插件管理器已处理，此处冗余以确保直接运行也能用）
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from rag_assistant.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class WebSearchPlugin(PluginBase):
    """联网搜索插件"""

    def __init__(self):
        super().__init__()
        self._search_engine = None

    def _get_search_engine(self):
        """延迟初始化搜索后端"""
        if self._search_engine is not None:
            return self._search_engine

        # 从插件配置加载设置
        config = self._load_config()
        self._search_engine = _WebSearchBackend(config)
        return self._search_engine

    def _load_config(self) -> dict:
        """加载插件自有配置"""
        config_file = self.data_dir / "config.json"
        defaults = {
            "backend": "duckduckgo",
            "api_key": "",
            "google_key": "",
            "google_cx": "",
            "bing_key": "",
            "custom_url": "",
            "max_results": 5,
        }
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
            except Exception as e:
                logger.error(f"加载插件配置失败: {e}")
        return defaults

    def _save_config(self, config: dict):
        """保存插件自有配置"""
        config_file = self.data_dir / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    async def execute(self, inputs: dict) -> dict:
        """
        执行联网搜索。
        inputs: {"question": "搜索关键词"}
        """
        question = inputs.get("question", "")
        if not question:
            return {
                "type": "plain_text",
                "content": "",
                "priority": 0,
                "execution_error": "搜索问题为空",
            }

        engine = self._get_search_engine()
        config = self._load_config()
        max_results = config.get("max_results", 5)

        try:
            result = engine.search(question, max_results)
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            return {
                "type": "plain_text",
                "content": "",
                "priority": 0,
                "execution_error": f"搜索执行异常: {e}",
            }

        if not result.get("success"):
            return {
                "type": "plain_text",
                "content": "",
                "priority": 0,
                "execution_error": result.get("error", "搜索失败"),
            }

        results = result.get("results", [])
        if not results:
            return {
                "type": "markdown",
                "content": "联网搜索未找到相关结果。",
                "priority": 0,
            }

        # 格式化为 Markdown
        lines = [f"## 联网搜索结果（来源：{config.get('backend', 'web')}）\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "").strip()
            url = r.get("url", "").strip()

            # 提取正文内容：优先用 content（Tavily），其次 snippet（DuckDuckGo），最后自抓取
            content = r.get("content", "") or r.get("snippet", "") or ""
            if isinstance(content, str):
                content = content.strip()
            else:
                content = str(content).strip() if content else ""

            # 如果后端没有返回正文（snippet 太短 or 为空），尝试自抓取
            if len(content) < 100 and url:
                fetched = self._fetch_page_text(url)
                if fetched:
                    content = fetched

            lines.append(f"### {i}. {title or '无标题'}")
            if url:
                lines.append(f"[来源链接]({url})")
            if content:
                lines.append(content)
            lines.append("")

        return {
            "type": "markdown",
            "content": "\n".join(lines),
            "priority": 0,
        }

    def _fetch_page_text(self, url: str, max_chars: int = 2000) -> str:
        """抓取网页并提取纯文本正文"""
        import urllib.request
        import re

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # 去掉 script/style
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
            # 去掉 HTML 标签
            text = re.sub(r'<[^>]+>', '', html)
            # 解码 HTML 实体
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
            # 合并空白
            text = re.sub(r'\s+', ' ', text).strip()
            # 截取前 max_chars
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            return text

        except Exception as e:
            logger.debug(f"抓取页面内容失败 [{url[:50]}]: {e}")
            return ""

    def open_config_ui(self):
        """Tkinter 配置界面"""
        config = self._load_config()

        root = tk.Tk()
        root.title(f"联网搜索配置 — {self.display_name}")
        root.geometry("480x440")
        root.resizable(False, False)

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)

        # 搜索引擎选择
        ttk.Label(main, text="搜索引擎：").grid(row=0, column=0, sticky="w", pady=(0, 4))
        backend_var = tk.StringVar(value=config.get("backend", "duckduckgo"))
        backend_combo = ttk.Combobox(
            main, textvariable=backend_var, state="readonly", width=30,
            values=["duckduckgo（免费）", "tavily", "google", "bing", "custom"]
        )
        backend_combo.grid(row=0, column=1, sticky="w", pady=(0, 4))

        # 各 Key 输入
        fields = [
            ("API Key（Tavily / 自定义）", "api_key"),
            ("Google API Key", "google_key"),
            ("Google CX", "google_cx"),
            ("Bing API Key", "bing_key"),
            ("自定义 API URL", "custom_url"),
            ("最大结果数", "max_results"),
        ]
        entries = {}
        row = 1
        for label, key in fields:
            ttk.Label(main, text=f"{label}：").grid(row=row, column=0, sticky="w", pady=2)
            if key == "max_results":
                e = ttk.Spinbox(main, from_=1, to=20, width=28)
                e.set(str(config.get(key, 5)))
            else:
                e = ttk.Entry(main, width=32)
                e.insert(0, config.get(key, ""))
            e.grid(row=row, column=1, sticky="w", pady=2)
            entries[key] = e
            row += 1

        # 保存按钮
        status_var = tk.StringVar()

        def do_save():
            backend_raw = backend_var.get()
            # 提取实际 backend 值
            backend_map = {
                "duckduckgo（免费）": "duckduckgo",
                "tavily": "tavily",
                "google": "google",
                "bing": "bing",
                "custom": "custom",
            }
            new_config = {
                "backend": backend_map.get(backend_raw, "duckduckgo"),
                "api_key": entries["api_key"].get().strip(),
                "google_key": entries["google_key"].get().strip(),
                "google_cx": entries["google_cx"].get().strip(),
                "bing_key": entries["bing_key"].get().strip(),
                "custom_url": entries["custom_url"].get().strip(),
                "max_results": int(entries["max_results"].get() or 5),
            }
            self._save_config(new_config)
            self._search_engine = None  # 下次执行时重新初始化
            status_var.set("配置已保存")
            root.after(1500, root.destroy)

        ttk.Button(main, text="保存并关闭", command=do_save).grid(
            row=row, column=0, columnspan=2, pady=(12, 0)
        )
        ttk.Label(main, textvariable=status_var, foreground="green").grid(
            row=row + 1, column=0, columnspan=2, pady=(4, 0)
        )

        root.mainloop()


# ═══════════════ 搜索后端（轻量封装，复用 search.py 逻辑） ═══════════════

class _WebSearchBackend:
    """联网搜索后端（独立实现，不依赖项目 search.py）"""

    def __init__(self, config: dict):
        self.backend = config.get("backend", "duckduckgo")
        self.api_key = config.get("api_key", "")
        self.google_key = config.get("google_key", "")
        self.google_cx = config.get("google_cx", "")
        self.bing_key = config.get("bing_key", "")
        self.custom_url = config.get("custom_url", "")

    def search(self, query: str, max_results: int = 5) -> dict:
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
        return self._search_duckduckgo(query, max_results)

    def _search_duckduckgo(self, query: str, max_results: int) -> dict:
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
            return self._search_fallback(query, max_results)
        except Exception as e:
            return {"results": [], "success": False, "error": str(e)}

    def _search_tavily(self, query: str, max_results: int) -> dict:
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
            return {"results": [], "success": False, "error": str(e)}

    def _search_google(self, query: str, max_results: int) -> dict:
        if not self.google_key or not self.google_cx:
            return {"results": [], "success": False, "error": "Google API Key 或 CX 未配置"}
        try:
            import requests
            url = "https://www.googleapis.com/customsearch/v1"
            params = {"key": self.google_key, "cx": self.google_cx, "q": query, "num": min(max_results, 10)}
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            formatted = [{"title": i.get("title", ""), "url": i.get("link", ""), "snippet": i.get("snippet", "")} for i in items]
            return {"results": formatted, "success": True}
        except Exception as e:
            return {"results": [], "success": False, "error": str(e)}

    def _search_bing(self, query: str, max_results: int) -> dict:
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
            formatted = [{"title": i.get("name", ""), "url": i.get("url", ""), "snippet": i.get("snippet", "")} for i in items]
            return {"results": formatted, "success": True}
        except Exception as e:
            return {"results": [], "success": False, "error": str(e)}

    def _search_custom(self, query: str, max_results: int) -> dict:
        if not self.custom_url:
            return {"results": [], "success": False, "error": "自定义 API URL 未配置"}
        try:
            import requests
            import urllib.parse
            url = self.custom_url.replace("{q}", urllib.parse.quote(query)).replace("{key}", self.api_key or "")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("results") or data.get("items") or data.get("data") or []
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
            return {"results": [], "success": False, "error": str(e)}

    def _search_fallback(self, query: str, max_results: int) -> dict:
        """纯 urllib 回退（DuckDuckGo HTML 抓取）"""
        import urllib.request
        import urllib.parse
        import re
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
