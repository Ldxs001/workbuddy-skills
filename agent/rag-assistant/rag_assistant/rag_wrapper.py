"""
local-rag-builder 封装层
直接 import 技能模块，但完整走技能自身流程，不改造路由逻辑
"""
import sys
import os
import logging

logger = logging.getLogger(__name__)

ENGINE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")
if ENGINE_PATH not in sys.path:
    sys.path.insert(0, ENGINE_PATH)


class RAGWrapper:
    """封装技能，完整走技能流程（路由 → 检索 → reranker），不改造任何内部逻辑"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self._ready = False
        self._import_modules()

    def _import_modules(self):
        try:
            from rag_core import retrieve_context, import_documents_to_kb
            from knowledge_base_manager import list_knowledge_bases
            self._retrieve_context = retrieve_context
            self._import_documents = import_documents_to_kb
            self._list_kbs = list_knowledge_bases
            self._ready = True
        except ImportError as e:
            logger.error(f"RAG 模块加载失败: {e}")

    @property
    def ready(self) -> bool:
        return self._ready

    def query(self, question: str, kb_name: str = None, include_header: bool = False, **kwargs) -> dict:
        """直接调 retrieve_context，完整走技能自身流程"""
        if not self._ready:
            return {"context": "", "has_context": False, "success": False,
                    "error": "RAG 模块未就绪"}

        try:
            result = self._retrieve_context(
                question,
                kb_name=kb_name or "default",
                k=kwargs.get("k", 5),
                score_threshold=kwargs.get("score_threshold", 0.0),
                include_header=include_header,
            )
            context = result.get("context", "")
            docs = result.get("source_docs", result.get("documents", []))
            actual_kb = ""
            if docs:
                kb_from_meta = docs[0].get("_kb", "") if isinstance(docs[0], dict) else (
                    docs[0].metadata.get("_kb", "") if hasattr(docs[0], "metadata") else ""
                )
                actual_kb = kb_from_meta
            return {
                "context": context,
                "docs": docs,
                "kb": actual_kb or kb_name or "",
                "success": True,
                "has_context": bool(context.strip()),
                "headers": result.get("headers", {}),
            }
        except Exception as e:
            logger.exception(f"RAG 检索失败: {e}")
            return {"context": "", "has_context": False, "success": False, "error": str(e)}

    def import_file(self, file_path: str, kb_name: str = "default") -> dict:
        if not self._ready:
            return {"success": False, "error": "RAG 模块未就绪"}
        try:
            from rag_core import import_documents_to_kb
            doc_count = import_documents_to_kb(file_path, kb_name=kb_name)
            if doc_count is False or (isinstance(doc_count, str) and "失败" in doc_count):
                return {"success": False, "error": str(doc_count), "kb": kb_name}
            return {"success": True, "doc_count": doc_count, "kb": kb_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_text(self, text: str, kb_name: str = "default", title: str = "") -> dict:
        if not self._ready:
            return {"success": False, "error": "RAG 模块未就绪"}
        try:
            import tempfile
            from rag_core import import_documents_to_kb
            content = f"# {title}\n\n{text}" if title else text
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
                f.write(content)
                tmp = f.name
            try:
                dc = import_documents_to_kb(tmp, kb_name=kb_name)
                return {"success": True, "doc_count": dc, "kb": kb_name, "title": title}
            finally:
                os.unlink(tmp)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_kbs(self) -> dict:
        if not self._ready:
            return {}
        try:
            return self._list_kbs()
        except Exception as e:
            return {}

    def get_gaps(self, min_count: int = 2) -> list:
        from .memory import Memory
        mem = Memory(self.config.get("data_dir", "data"))
        return mem.get_gaps(min_count=min_count)
