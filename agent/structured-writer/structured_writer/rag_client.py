"""RAG 客户端 — 通过 HTTP 调 rag-assistant 8767 外部 API"""

import json
import urllib.request
import urllib.error
from typing import Optional


class RAGClientError(Exception):
    pass


class RAGClient:
    def __init__(self, base_url="http://localhost:8767", timeout=30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def query(self, kb: str, query_text: str, top_k: int = 5,
              score_threshold: Optional[float] = None) -> dict:
        """检索知识库返回上下文，不调用 LLM 生成

        参数:
            kb: 知识库名称，空字符串=自动路由
            query_text: 查询文本
            top_k: 返回文档数
            score_threshold: 相似度阈值

        返回:
            {"context": str, "sources": list, "has_context": bool, "kb": str}
        """
        body = {
            "kb": kb or "",
            "query": query_text,
            "top_k": top_k,
        }
        if score_threshold is not None:
            body["score_threshold"] = score_threshold

        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/kb/query",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RAGClientError(f"HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise RAGClientError(f"连接失败: {e.reason}")
        except Exception as e:
            raise RAGClientError(f"RAG 查询异常: {e}")
