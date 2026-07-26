"""LLM 统一客户端 — 支持 LM Studio / Ollama / OpenAI 兼容 API"""
import json
import urllib.request
import urllib.error
from typing import Optional


class LLMClientError(Exception):
    pass


class LLMClient:
    def __init__(self, backend="lmstudio", base_url="http://localhost:1234",
                 timeout=180, model="", max_tokens=4096):
        self.backend = backend
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.model = model
        self.max_tokens = max_tokens

    def _get_api_url(self):
        if self.backend == "ollama":
            return f"{self.base_url}/api/chat"
        else:
            return f"{self.base_url}/v1/chat/completions"

    def _build_payload(self, messages, max_tokens=4096, temperature=0.7):
        if self.backend == "ollama":
            return json.dumps({
                "model": self.model,
                "messages": messages,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            }).encode("utf-8")
        else:
            return json.dumps({
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }).encode("utf-8")

    def _parse_response(self, body: bytes) -> str:
        data = json.loads(body)
        if self.backend == "ollama":
            return data.get("message", {}).get("content", "")
        else:
            return data["choices"][0]["message"]["content"]

    def _parse_finish_reason(self, body: bytes) -> str:
        """解析 finish_reason: stop / length / null"""
        try:
            data = json.loads(body)
            if self.backend == "ollama":
                return data.get("done_reason", "stop")
            else:
                return data["choices"][0].get("finish_reason", "stop")
        except Exception:
            return "stop"

    def chat(self, messages, max_tokens=None, temperature=0.7,
             timeout=None) -> str:
        url = self._get_api_url()
        mt = max_tokens if max_tokens is not None else self.max_tokens
        payload = self._build_payload(messages, mt, temperature)
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            timeout = timeout or self.timeout
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return self._parse_response(resp.read())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise LLMClientError(f"连接失败: {e.reason}")
        except Exception as e:
            raise LLMClientError(f"LLM 调用异常: {e}")

    def chat_detailed(self, messages, max_tokens=None, temperature=0.7,
                      timeout=None) -> dict:
        """调用 LLM 并返回 {content, finish_reason}，用于检测截断续写"""
        url = self._get_api_url()
        mt = max_tokens if max_tokens is not None else self.max_tokens
        payload = self._build_payload(messages, mt, temperature)
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            timeout = timeout or self.timeout
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                content = self._parse_response(body)
                finish_reason = self._parse_finish_reason(body)
                return {"content": content, "finish_reason": finish_reason}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise LLMClientError(f"连接失败: {e.reason}")
        except Exception as e:
            raise LLMClientError(f"LLM 调用异常: {e}")

    def test_connection(self) -> tuple[bool, str]:
        try:
            if self.backend == "ollama":
                url = f"{self.base_url}/api/tags"
            else:
                url = f"{self.base_url}/v1/models"

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if self.backend == "ollama":
                    models = [m["name"] for m in data.get("models", [])]
                else:
                    models = [m["id"] for m in data.get("data", [])]
                return True, f"已连接，可用模型：{', '.join(models[:10])}"
        except Exception as e:
            return False, f"连接失败：{e}"

    def list_models(self) -> list[str]:
        try:
            if self.backend == "ollama":
                url = f"{self.base_url}/api/tags"
            else:
                url = f"{self.base_url}/v1/models"

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if self.backend == "ollama":
                    return [m["name"] for m in data.get("models", [])]
                else:
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []
