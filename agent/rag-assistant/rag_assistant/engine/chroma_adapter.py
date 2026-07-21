"""
ChromaDB 原生适配器（替代 langchain_chroma.Chroma）
API 兼容：Chroma() / similarity_search() / as_retriever() / from_documents() / add_documents()
"""

import os
import uuid
import logging

logger = logging.getLogger(__name__)

# chromadb 原生 API 的引用（lazy import）
_chromadb = None

def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        import chromadb as _c
        _chromadb = _c
    return _chromadb


class ChromaRetriever:
    """Chroma 的 as_retriever() 返回的 retriever 兼容对象"""

    def __init__(self, collection, embedding_function, search_type="similarity",
                 search_kwargs=None):
        self._collection = collection
        self._embedding_function = embedding_function
        self._search_type = search_type
        self._search_kwargs = search_kwargs or {"k": 3}

    def invoke(self, query: str):
        """执行检索，返回 Document 列表（兼容 langchain retriever.invoke()）"""
        from utils import Document
        k = self._search_kwargs.get("k", 3)
        score_threshold = self._search_kwargs.get("score_threshold")

        query_emb = self._embedding_function.embed_query(query)
        results = self._collection.query(
            query_embeddings=[query_emb],
            n_results=k,
        )

        docs = []
        if not results or not results.get("documents"):
            return docs
        for i, content in enumerate(results["documents"][0]):
            meta = {}
            if results.get("metadatas") and results["metadatas"][0]:
                meta = results["metadatas"][0][i] or {}
            doc = Document(page_content=content, metadata=meta)

            # score_threshold 过滤（余弦相似度转为距离比较）
            if score_threshold is not None:
                dists = results.get("distances", [[]])
                if dists and dists[0] and i < len(dists[0]):
                    distance = dists[0][i]
                    # ChromaDB 距离 0=相同, 2=最远
                    # 余弦距离 ≈ 1 - cosine_sim
                    similarity = 1 - distance / 2.0
                    if similarity < score_threshold:
                        continue
            docs.append(doc)
        return docs


class Chroma:
    """ChromaDB 原生适配器，兼容 langchain_chroma.Chroma 核心 API"""

    def __init__(self, persist_directory: str, embedding_function):
        self._persist_dir = persist_directory
        self._embedding_function = embedding_function
        cd = _get_chromadb()

        # ChromaDB 要求目录必须存在
        os.makedirs(persist_directory, exist_ok=True)

        self._client = cd.PersistentClient(path=persist_directory)
        # langchain_chroma 默认 collection 名为 "langchain"
        collection_name = "langchain"
        try:
            self._collection = self._client.get_collection(collection_name)
        except Exception:
            self._collection = self._client.create_collection(
                collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        self._collection_name = collection_name

    @property
    def _collection(self):
        """暴露 _collection 属性，兼容 vs._collection.get() / .count() / .delete() 调用"""
        return self.__collection

    @_collection.setter
    def _collection(self, val):
        self.__collection = val

    def similarity_search(self, query: str, k: int = 4) -> list:
        """按文本相似度检索（内部自动转向量）"""
        from utils import Document
        query_emb = self._embedding_function.embed_query(query)
        results = self.__collection.query(
            query_embeddings=[query_emb],
            n_results=k,
        )
        docs = []
        if not results or not results.get("documents"):
            return docs
        for i, content in enumerate(results["documents"][0]):
            meta = {}
            if results.get("metadatas") and results["metadatas"][0]:
                meta = results["metadatas"][0][i] or {}
            docs.append(Document(page_content=content, metadata=meta))
        return docs

    def as_retriever(self, search_type="similarity", search_kwargs=None):
        """返回兼容的 retriever 对象（支持 .invoke()）"""
        return ChromaRetriever(
            self.__collection,
            self._embedding_function,
            search_type=search_type,
            search_kwargs=search_kwargs,
        )

    def get(self, include=None, where=None):
        """获取集合中的文档（兼容 langchain_chroma.Chroma.get()）"""
        kwargs = {}
        if include:
            kwargs["include"] = include
        if where:
            kwargs["where"] = where
        try:
            return self.__collection.get(**kwargs)
        except Exception:
            return {"documents": [], "metadatas": [], "ids": []}

    def add_documents(self, documents, ids=None):
        """添加文档（兼容 langchain_chroma.Chroma.add_documents()）"""
        if not documents:
            return
        texts = []
        metadatas = []
        doc_ids = ids or [str(uuid.uuid4()) for _ in documents]

        for i, doc in enumerate(documents):
            if hasattr(doc, "page_content"):
                texts.append(doc.page_content)
                metadatas.append(getattr(doc, "metadata", {}) or {})
            else:
                texts.append(str(doc))
                metadatas.append({})

        # 计算 embedding
        embeddings = self._embedding_function.embed_documents(texts)

        self.__collection.add(
            ids=doc_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    @classmethod
    def from_documents(cls, documents, embedding, persist_directory=None):
        """类方法：创建新库并写入文档（兼容 langchain_chroma.Chroma.from_documents()）"""
        vs = cls(persist_directory=persist_directory, embedding_function=embedding)
        vs.add_documents(documents)
        return vs

    def delete_collection(self):
        """删除整个集合"""
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
