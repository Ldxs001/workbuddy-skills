"""
rag-assistant LLM 客户端
支持 Ollama API / LM Studio (OpenAI兼容) / 直接 transformers
统一接口，运行时自动检测可用后端
"""
import json
import requests
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_LMSTUDIO_URL = "http://localhost:1234"


class LLMClient:
    """LLM 统一调用接口"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        llm_cfg = self.config.get("llm", {})
        self.backend = llm_cfg.get("backend", "ollama")
        self.model = llm_cfg.get("model", "")
        self.ollama_url = self.config.get("ollama_url", DEFAULT_OLLAMA_URL)
        self.lmstudio_url = self.config.get("lmstudio_url", DEFAULT_LMSTUDIO_URL)
        self.timeout = llm_cfg.get("timeout", 180)
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def chat(self, messages: list, stream: bool = False, **kwargs) -> dict:
        """统一聊天接口，返回 LLM 回复文本"""
        if self.backend == "ollama":
            return self._call_ollama(messages, stream, **kwargs)
        elif self.backend == "lmstudio":
            return self._call_lmstudio(messages, stream, **kwargs)
        else:
            raise ValueError(f"不支持的 LLM 后端: {self.backend}")

    def _call_ollama(self, messages: list, stream: bool, **kwargs) -> dict:
        payload = {
            "model": self.model or "llama3",
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        }
        try:
            resp = self._session.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=kwargs.get("timeout", self.timeout),
            )
            resp.raise_for_status()
            if stream:
                return resp  # 返回原始 response 对象，由调用方逐行读取
            data = resp.json()
            msg = data.get("message", {})
            return {
                "text": msg.get("content", ""),
                "reasoning": msg.get("reasoning_content", ""),
                "raw": data,
            }
        except requests.RequestException as e:
            logger.error(f"Ollama 调用失败: {e}")
            return {"text": "", "error": str(e)}

    def _call_lmstudio(self, messages: list, stream: bool, **kwargs) -> dict:
        # 如果 model 为空，自动获取已加载的模型名
        model_name = self.model
        if not model_name:
            models = self.list_models()
            if models:
                model_name = models[0]

        payload = {
            "messages": messages,
            "stream": stream,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        if model_name:
            payload["model"] = model_name
        try:
            resp = self._session.post(
                f"{self.lmstudio_url}/v1/chat/completions",
                json=payload,
                timeout=kwargs.get("timeout", self.timeout),
            )
            if not resp.ok:
                logger.error(f"LM Studio 400 响应体: {resp.text[:500]}")
            resp.raise_for_status()
            if stream:
                return resp
            data = resp.json()
            msg = data.get("choices", [{}])[0].get("message", {})
            return {
                "text": msg.get("content", ""),
                "reasoning": msg.get("reasoning_content", ""),
                "raw": data,
            }
        except requests.RequestException as e:
            logger.error(f"LM Studio 调用失败: {e}")
            return {"text": "", "error": str(e)}

    def list_models(self) -> list:
        """列出可用模型（短超时，失败返回空列表）"""
        if self.backend == "ollama":
            try:
                resp = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
            except Exception:
                return []
        elif self.backend == "lmstudio":
            try:
                resp = requests.get(f"{self.lmstudio_url}/v1/models", timeout=3)
                resp.raise_for_status()
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
            except Exception:
                return []
        return []

    def check_health(self) -> bool:
        """检测后端是否可用"""
        try:
            if self.backend == "ollama":
                resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                return resp.ok
            elif self.backend == "lmstudio":
                resp = requests.get(f"{self.lmstudio_url}/v1/models", timeout=5)
                return resp.ok
        except Exception:
            return False
        return False
