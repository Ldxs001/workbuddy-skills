"""
rag-assistant LLM 客户端
支持 Ollama API / LM Studio (OpenAI兼容) / Web API (OpenAI兼容远程)
统一接口，运行时自动检测可用后端
"""
import json
import requests
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────────────
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_LMSTUDIO_URL = "http://localhost:1234"


class LLMClient:
    """LLM 统一调用接口"""

    def __init__(self, config: dict = None, data_dir: str = None):
        self.config = config or {}
        self.data_dir = data_dir
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
        elif self.backend == "web_api":
            return self._call_web_api(messages, stream, **kwargs)
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

    def _get_web_llm_profiles(self) -> list:
        """从 web_llm 插件配置读取所有 profile"""
        if not self.data_dir:
            return []
        config_path = Path(self.data_dir) / "plugins" / "web_llm" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                profiles = raw.get("profiles", [])
                if not profiles and isinstance(raw, dict) and "base_url" in raw:
                    # 旧格式兼容
                    profiles = [raw]
                return profiles
            except Exception as e:
                logger.error(f"读取 web_llm 插件配置失败: {e}")
        return []

    def _get_web_llm_config(self, model_name: str = None) -> dict:
        """按模型名查找对应的 profile 配置"""
        profiles = self._get_web_llm_profiles()
        target = model_name or self.model
        if target:
            for p in profiles:
                if p.get("model") == target:
                    return p
        # 没匹配到则返回第一个
        if profiles:
            return dict(profiles[0])
        return {
            "base_url": "https://api.openai.com/v1",
            "api_key": "", "model": "",
            "temperature": 0.7, "top_p": 1.0, "max_tokens": 4096,
        }

    def _call_web_api(self, messages: list, stream: bool, **kwargs) -> dict:
        """调用 OpenAI 兼容的远程 API（按模型名匹配 profile 配置）"""
        model_name = self.model or kwargs.get("model", "")
        wc = self._get_web_llm_config(model_name)
        base_url = wc.get("base_url", "https://api.openai.com/v1").rstrip("/")
        api_key = wc.get("api_key", "")
        model_name = model_name or wc.get("model", "gpt-4o")

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
            "temperature": wc.get("temperature", 0.7),
            "top_p": wc.get("top_p", 1.0),
            "max_tokens": wc.get("max_tokens", 4096),
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            resp = self._session.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=kwargs.get("timeout", self.timeout),
            )
            if not resp.ok:
                logger.error(f"Web API 返回 {resp.status_code}: {resp.text[:500]}")
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
            logger.error(f"Web API 调用失败: {e}")
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
        elif self.backend == "web_api":
            profiles = self._get_web_llm_profiles()
            return [p.get("model", "") for p in profiles if p.get("model")]
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
            elif self.backend == "web_api":
                wc = self._get_web_llm_config()
                base_url = wc.get("base_url", "https://api.openai.com/v1").rstrip("/")
                api_key = wc.get("api_key", "")
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = requests.get(f"{base_url}/models", headers=headers, timeout=5)
                return resp.ok
        except Exception:
            return False
        return False
