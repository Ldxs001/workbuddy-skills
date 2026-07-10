"""
llm_client.py — 多后端 LLM 客户端
支持 Ollama / LM Studio / OpenAI 兼容 API（含云端）
统一接口，无外部 SDK，仅用标准库。
"""
import json, time, urllib.request, urllib.error, os, sys
from typing import Optional

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path: sys.path.insert(0, _DIR)
from agent_config import AgentConfig


class LLMError(Exception): pass
class LLMConnectionError(LLMError): pass
class LLMResponseError(LLMError): pass


class LLMClient:
    """多后端 LLM 客户端"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.backend = config.llm_backend
        self.model = config.llm_model
        self.temperature = config.llm_temperature
        self.max_tokens = config.llm_max_tokens
        self.top_p = config.llm_top_p
        self.api_key = config.llm_api_key
        self.timeout = config.llm_timeout
        self.stream_timeout = max(config.llm_timeout, 300)

    @property
    def _base_url(self) -> str:
        """按后端解析 base_url"""
        b = self.backend
        if b == "ollama":
            return self.config.llm_ollama_url.rstrip("/")
        elif b == "lmstudio":
            return self.config.llm_lmstudio_url.rstrip("/") + "/v1"
        else:  # openai
            url = self.config.llm_base_url.rstrip("/")
            if not url.endswith("/v1") and "/chat/completions" not in url:
                url += "/v1"
            return url

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    # ------------------------------------------------------------------
    # Chat（非流式）
    # ------------------------------------------------------------------
    def chat(self, messages: list, temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> str:
        if self.backend == "ollama":
            return self._chat_ollama(messages, temperature, max_tokens)
        return self._chat_openai(messages, temperature, max_tokens)

    def _chat_ollama(self, messages, temperature, max_tokens) -> str:
        body = json.dumps({
            "model": self.model or "llama3",
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_predict": max_tokens if max_tokens is not None else self.max_tokens,
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.config.llm_ollama_url}/api/chat",
            data=body, headers=self._headers(), method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
            return data.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            raise LLMResponseError(f"Ollama HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"Ollama 连接失败: {e.reason}")

    def _chat_openai(self, messages, temperature, max_tokens) -> str:
        body = json.dumps({
            "model": self.model or "default",
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "top_p": self.top_p,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body, headers=self._headers(), method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            raise LLMResponseError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"连接失败: {e.reason}")
        except (KeyError, IndexError) as e:
            raise LLMResponseError(f"响应格式异常: {e}")

    # ------------------------------------------------------------------
    # 连接检测
    # ------------------------------------------------------------------
    def check_connection(self) -> tuple:
        try:
            models = self.list_models()
            if models:
                return True, f"连接成功 ({len(models)} 个模型)"
            return True, "连接成功"
        except Exception as e:
            return False, str(e)

    def list_models(self) -> list:
        b = self.backend
        try:
            if b == "ollama":
                req = urllib.request.Request(f"{self.config.llm_ollama_url}/api/tags",
                    headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read().decode())
                return [m["name"] for m in data.get("models", [])]
            else:
                url = self._base_url  # 已经是 /v1 结尾，直接加 /models
                req = urllib.request.Request(f"{url}/models",
                    headers={"Accept": "application/json", **self._headers()})
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read().decode())
                return [m["id"] if isinstance(m, dict) and "id" in m else m.get("name","") for m in data.get("data", [])]
        except Exception:
            return []
