"""
tools/rag_tool.py — RAG 检索工具

直接调用 local-rag-builder 的 rag_core.py，无需子进程。
"""

import importlib.util
import os
import sys
from typing import Optional

from ..tool_base import BaseTool, ToolResult
from ..agent_config import AgentConfig


class RAGTool(BaseTool):
    """
    RAG 知识库检索工具。

    在本地知识库中搜索与问题最相关的文档片段。
    需要 local-rag-builder 技能已安装并配置好。
    """

    def __init__(self, config: AgentConfig):
        super().__init__(
            name="rag_search",
            description="在本地知识库中检索信息，返回与问题最相关的文档片段。适用于回答需要查阅本地资料的问题。",
        )
        self.config = config
        self._rag_core = None

    def _load_rag_core(self):
        """动态导入 local-rag-builder 的 rag_core 模块"""
        if self._rag_core is not None:
            return self._rag_core

        skill_path = self.config.rag_skill_path
        scripts_dir = os.path.join(skill_path, "scripts")

        if not os.path.exists(scripts_dir):
            raise ImportError(f"local-rag-builder 脚本目录不存在: {scripts_dir}")

        # 将 scripts 目录加入 sys.path
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        # 导入 rag_core
        spec = importlib.util.spec_from_file_location(
            "rag_core", os.path.join(scripts_dir, "rag_core.py")
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载 rag_core.py: {os.path.join(scripts_dir, 'rag_core.py')}")

        rag_core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rag_core)
        self._rag_core = rag_core
        return rag_core

    def _load_embeddings(self):
        """获取嵌入模型"""
        from ..agent_config import AgentConfig
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return None

        skill_path = self.config.rag_skill_path
        models_dir = os.path.join(skill_path, "data", "models")

        if not os.path.exists(models_dir):
            return None

        # 找已下载的嵌入模型
        for d in os.listdir(models_dir):
            dpath = os.path.join(models_dir, d)
            if os.path.isdir(dpath) and os.path.exists(os.path.join(dpath, "config.json")):
                try:
                    return SentenceTransformer(dpath, trust_remote_code=True)
                except Exception:
                    continue
        return None

    def execute(
        self,
        query: str = "",
        kb_name: Optional[str] = None,
        k: Optional[int] = None,
    ) -> ToolResult:
        """
        执行 RAG 检索。

        Parameters
        ----------
        query : str
            搜索查询
        kb_name : str, optional
            知识库名称，默认使用配置中的 default_kb
        k : int, optional
            返回的文档片段数，默认使用配置中的 k
        """
        if not query.strip():
            return ToolResult(False, error="查询内容不能为空")

        kb = kb_name or self.config.rag_default_kb
        top_k = k or self.config.rag_k

        try:
            rag_core = self._load_rag_core()
        except ImportError as e:
            return ToolResult(False, error=f"RAG 核心加载失败: {e}。请确保 local-rag-builder 已正确安装。")

        # 获取嵌入模型
        embeddings = self._load_embeddings()
        if embeddings is None:
            return ToolResult(False, error="嵌入模型未找到。请先运行 embedding_model_manager.py 下载嵌入模型。")

        try:
            result = rag_core.retrieve_context(
                question=query,
                kb_name=kb,
                k=top_k,
                score_threshold=self.config.rag_score_threshold,
                embeddings=embeddings,
            )
        except Exception as e:
            return ToolResult(False, error=f"RAG 检索失败: {e}")

        docs = result.get("source_docs", [])
        context = result.get("context", "")

        if not docs:
            return ToolResult(
                True,
                output=f"知识库「{kb}」中未找到与「{query}」相关的内容。",
                data={"found": False, "context": ""},
            )

        output = (
            f"在知识库「{kb}」中找到 {len(docs)} 个相关片段:\n\n"
            f"{context[:4000]}"
        )

        return ToolResult(
            True,
            output=output,
            data={
                "found": True,
                "context": context,
                "source_count": len(docs),
                "sources": [
                    {
                        "content": d.get("content", d.get("page_content", ""))[:500],
                        "metadata": d.get("metadata", {}),
                    }
                    for d in docs
                ],
            },
        )

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要搜索的问题或关键词",
                    },
                    "kb_name": {
                        "type": "string",
                        "description": "知识库名称（可选，默认使用 default）",
                    },
                    "k": {
                        "type": "integer",
                        "description": "返回的文档片段数量（可选，默认 5）",
                    },
                },
                "required": ["query"],
            },
        }
