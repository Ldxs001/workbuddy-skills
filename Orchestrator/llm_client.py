"""
llm_client.py — 纯 Python LLM 客户端

通过 OpenAI 兼容接口调用本地模型（LM Studio / Ollama / vLLM）。
无外部 SDK 依赖，仅用标准库 urllib + json。
"""

import json
import time
import urllib.request
import urllib.error
import sys, os
from typing import Optional, Iterator

# 支持直接/模块两种运行方式
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_config import AgentConfig


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------
class LLMError(Exception):
    """LLM 调用相关异常"""
    pass


class LLMConnectionError(LLMError):
    """连接失败"""
    pass


class LLMResponseError(LLMError):
    """响应解析失败"""
    pass


# ---------------------------------------------------------------------------
# LLM 客户端
# ---------------------------------------------------------------------------
class LLMClient:
    """
    纯 Python LLM 客户端，无外部依赖。

    支持的本地后端（只需改 base_url）：
      - LM Studio:   http://localhost:1234/v1
      - Ollama:      http://localhost:11434/v1
      - vLLM:        http://localhost:8000/v1
    """

    def __init__(self, config: AgentConfig):
        self.base_url = config.llm_base_url.rstrip("/")
        self.api_key = config.llm_api_key
        self.model = config.llm_model
        self.temperature = config.llm_temperature
        self.max_tokens = config.llm_max_tokens
        self.top_p = config.llm_top_p
        self.timeout = 600  # 默认10分钟，可通过 set_timeout 修改
        self.stream_timeout = 600
        # 续接控制（可通过 setter 或外部直接修改）
        self.continuation_enabled = True
        self.max_continuations = 5
        self._continuation_tokens = 16384  # 续接请求专用的 max_tokens

    def set_timeout(self, seconds: int):
        """设置 HTTP 请求超时（秒），最长可设 86400（24h）"""
        self.timeout = min(seconds, 86400)
        self.stream_timeout = min(seconds, 86400)

    def set_max_tokens(self, tokens: int):
        """设置 max_tokens，最长 131072"""
        self.max_tokens = min(tokens, 131072)

    def set_continuation_tokens(self, tokens: int):
        """设置续接请求专用的 max_tokens，最长 131072"""
        self._continuation_tokens = min(tokens, 131072)

    def set_max_continuations(self, count: int):
        """设置最大续接次数，0=不续接，最长 20"""
        self.max_continuations = max(0, min(count, 20))

    # ------------------------------------------------------------------
    # 连接检测
    # ------------------------------------------------------------------
    def check_connection(self) -> tuple[bool, str]:
        """检测 LLM 后端是否可达"""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                models = [m["id"] for m in data.get("data", [])]
                return True, f"连接成功，可用模型: {', '.join(models[:5])}{'...' if len(models) > 5 else ''}"
        except urllib.error.URLError as e:
            return False, f"连接失败: {e.reason}"
        except json.JSONDecodeError:
            return False, "响应解析失败（非 JSON）"
        except Exception as e:
            return False, f"未知错误: {e}"

    # ------------------------------------------------------------------
    # Chat Completion（非流式，带自动续接）
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        continuation: Optional[bool] = None,
    ) -> str:
        """
        发送对话请求，返回文本回复。
        如果 continuation=True（默认由 self.continuation_enabled 控制）且模型返回 finish_reason="length"，
        自动追加"继续"请求续接，最多续接 self.max_continuations 次。
        continuation 参数可显式覆盖 self.continuation_enabled。
        """
        if continuation is None:
            continuation = self.continuation_enabled

        full_content = ""
        attempt = 0
        current_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        while attempt <= (self.max_continuations if continuation else 0):
            # 第一次用原有 max_tokens，续接用 _continuation_tokens
            tok = current_max_tokens if attempt == 0 else self._continuation_tokens

            body = json.dumps({
                "model": self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature,
                "max_tokens": tok,
                "top_p": self.top_p,
                "stream": False,
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                raise LLMResponseError(f"HTTP {e.code}: {detail}")
            except urllib.error.URLError as e:
                raise LLMConnectionError(f"连接失败: {e.reason}")
            except json.JSONDecodeError as e:
                raise LLMResponseError(f"JSON 解析失败: {e}")

            try:
                content = result["choices"][0]["message"]["content"]
                finish_reason = result["choices"][0].get("finish_reason", "stop")
            except (KeyError, IndexError) as e:
                raise LLMResponseError(
                    f"响应格式异常: {e} — "
                    f"原始响应: {json.dumps(result, ensure_ascii=False)[:300]}"
                )

            full_content += content
            attempt += 1

            # 如果已经完成或不允许续接，返回
            if finish_reason != "length" or not continuation:
                break

            # 追加继续指令到对话历史
            messages.append({"role": "assistant", "content": content})
            # 提取最后几行作为"接续点"提示
            last_lines = [l for l in content.strip().split("\n") if l.strip()][-3:]
            tail_hint = "，上一次结束于: " + " | ".join(last_lines) if last_lines else ""
            messages.append({
                "role": "user",
                "content": f"继续输出。{tail_hint}\n直接续写，不要重复已写的内容，不要总结不要确认，接着写下去。",
            })

        return full_content

    # ------------------------------------------------------------------
    # Chat Completion（流式）
    # ------------------------------------------------------------------
    def chat_stream(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """
        流式对话，逐 chunk 产出文本片段。
        用法: for chunk in client.chat_stream(messages): print(chunk, end="")
        """
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "top_p": self.top_p,
            "stream": True,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            resp = urllib.request.urlopen(req, timeout=self.stream_timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise LLMResponseError(f"HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            raise LLMConnectionError(f"连接失败: {e.reason}")

        buffer = ""
        while True:
            chunk = resp.read(1)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            # SSE 按行分隔
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line or line.startswith(":"):
                    continue
                if line == "data: [DONE]":
                    return
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    # ------------------------------------------------------------------
    # 便捷方法：system + user 单轮对话
    # ------------------------------------------------------------------
    def ask(self, system: str, user: str, **kwargs) -> str:
        """单轮 system + user 对话"""
        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ], **kwargs)

    # ------------------------------------------------------------------
    # 重试包装
    # ------------------------------------------------------------------
    def chat_with_retry(
        self,
        messages: list[dict],
        max_retries: int = 3,
        **kwargs,
    ) -> str:
        """带指数退避重试的 chat"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.chat(messages, **kwargs)
            except (LLMConnectionError, LLMResponseError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
        raise LLMError(f"重试 {max_retries} 次后仍然失败: {last_error}")
