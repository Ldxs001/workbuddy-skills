"""
ChromaDB + hnswlib 适配器（替代 langchain_chroma.Chroma）
API 兼容：Chroma() / similarity_search() / as_retriever() / from_documents() / add_documents()

ChromaDB 只用于 metadata 存储（SQLite），向量搜索走 hnswlib，
绕开 ChromaDB Rust 后端的 compaction bug。
"""

import os
import json
import uuid
import logging
import numpy as np

logger = logging.getLogger(__name__)

_chromadb = None
def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        import chromadb as _c
        _chromadb = _c
    return _chromadb

# ── hnswlib 索引管理 ─────────────────────────────

INDEX_FILE = "hnsw_index.bin"
INDEX_META = "hnsw_meta.json"


def _hnsw_storage_dir(persist_dir: str) -> str:
    """返回 hnswlib 索引文件的存储目录（ASCII-only 路径，避免中文路径 bug）
    存放在 data/_hnsw/ 下，不放在 kb 目录内，避免被 KB 扫描器误扫。
    """
    from knowledge_base_manager import sm3
    # persist_dir = data/kb/机动车 → data_root = data/
    data_root = os.path.normpath(os.path.join(persist_dir, "..", ".."))
    kb_name = os.path.basename(persist_dir)
    safe_name = sm3(kb_name.encode("utf-8"))[:16]
    storage = os.path.join(data_root, "_hnsw", safe_name)
    os.makedirs(storage, exist_ok=True)
    return storage


class HNSWIndex:
    """hnswlib 向量索引的封装，负责读写持久化文件"""

    def __init__(self, persist_dir: str, dimension: int, m: int = 16):
        self._persist_dir = persist_dir
        self._dimension = dimension
        self._storage = _hnsw_storage_dir(persist_dir)
        self._index_path = os.path.join(self._storage, INDEX_FILE)
        self._meta_path = os.path.join(self._storage, INDEX_META)

        # 加载已有索引或创建新的
        self._index = None
        self._id_map = {}       # hnswlib internal_id → chroma_id (str)
        self._reverse_map = {}  # chroma_id (str) → hnswlib internal_id
        self._next_id = 0
        self._m = m

        if os.path.exists(self._index_path):
            self._load()
        else:
            self._create(m)

    def _create(self, m: int):
        import hnswlib
        self._index = hnswlib.Index(space='cosine', dim=self._dimension)
        self._index.init_index(max_elements=100000, ef_construction=m * 2, M=m)
        self._m = m
        self._next_id = 0
        self._id_map = {}
        self._reverse_map = {}
        self._save_meta()

    def _load(self):
        import hnswlib
        self._index = hnswlib.Index(space='cosine', dim=self._dimension)
        self._index.load_index(self._index_path)
        # 恢复元数据
        if os.path.exists(self._meta_path):
            with open(self._meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            self._id_map = {int(k): v for k, v in meta.get('id_map', {}).items()}
            self._reverse_map = {v: int(k) for k, v in self._id_map.items()}
            self._next_id = meta.get('next_id', len(self._id_map))

    def _save(self):
        if self._index is not None:
            self._index.save_index(self._index_path)
        self._save_meta()

    def _save_meta(self):
        with open(self._meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'id_map': {str(k): v for k, v in self._id_map.items()},
                'next_id': self._next_id,
                'm': self._m,
            }, f, ensure_ascii=False)

    def add_items(self, embeddings: list, chroma_ids: list) -> list:
        """添加向量，返回分配给各向量的 internal_id 列表"""
        if not embeddings:
            return []
        emb_array = np.array(embeddings, dtype=np.float32)
        internal_ids = list(range(self._next_id, self._next_id + len(embeddings)))

        self._index.add_items(emb_array, internal_ids)

        for iid, cid in zip(internal_ids, chroma_ids):
            self._id_map[iid] = cid
            self._reverse_map[cid] = iid
        self._next_id += len(embeddings)
        self._save()
        return internal_ids

    def query(self, query_emb: list, k: int) -> tuple:
        """查询 top-k，返回 (chroma_ids, distances)"""
        q = np.array([query_emb], dtype=np.float32)
        labels, distances = self._index.knn_query(q, k=k)
        ids_out = []
        dists_out = []
        for iid, dist in zip(labels[0], distances[0]):
            if iid == -1:
                break
            cid = self._id_map.get(iid)
            if cid is not None:
                ids_out.append(cid)
                dists_out.append(float(dist))
        return ids_out, dists_out

    def count(self) -> int:
        """返回索引中的元素数"""
        return self._index.element_count if self._index else 0

    def delete(self):
        """删除索引文件和元数据"""
        self._index = None
        for p in [self._index_path, self._meta_path]:
            if os.path.exists(p):
                os.remove(p)

    @property
    def elements(self) -> int:
        return self._index.element_count if self._index else 0

    def set_ef(self, ef: int):
        if self._index:
            self._index.set_ef(ef)


class ChromaRetriever:
    """兼容 as_retriever() 返回的 retriever 对象"""

    def __init__(self, hnsw: HNSWIndex, chroma_coll, embedding_function,
                 search_kwargs=None):
        self._hnsw = hnsw
        self._chroma_coll = chroma_coll
        self._embedding_function = embedding_function
        self._search_kwargs = search_kwargs or {"k": 3}

    def invoke(self, query: str):
        from utils import Document
        k = self._search_kwargs.get("k", 3)
        score_threshold = self._search_kwargs.get("score_threshold")

        query_emb = self._embedding_function.embed_query(query)
        chroma_ids, distances = self._hnsw.query(query_emb, k)

        if not chroma_ids:
            return []

        # 从 ChromaDB 批量读取文档内容和元数据
        results = self._chroma_coll.get(ids=chroma_ids, include=['documents', 'metadatas'])

        docs = []
        for i, cid in enumerate(chroma_ids):
            # 按 ID 查找在结果中的索引
            try:
                idx = results['ids'].index(cid)
            except ValueError:
                continue
            content = results['documents'][idx] if results.get('documents') else ''
            meta = results['metadatas'][idx] if results.get('metadatas') else {}

            doc = Document(page_content=content, metadata=meta or {})

            if score_threshold is not None and i < len(distances):
                distance = distances[i]
                similarity = 1 - distance  # 余弦距离已归一化到 [0,2]
                if similarity < score_threshold:
                    continue
            docs.append(doc)
        return docs


class Chroma:
    """ChromaDB+hnswlib 适配器，兼容 langchain_chroma.Chroma 核心 API"""

    def __init__(self, persist_directory: str, embedding_function):
        self._persist_dir = persist_directory
        self._embedding_function = embedding_function
        os.makedirs(persist_directory, exist_ok=True)

        # 初始化 ChromaDB（仅用于 metadata 存储）
        cd = _get_chromadb()
        self._client = cd.PersistentClient(path=persist_directory)
        collection_name = "langchain"
        try:
            self._chroma_coll = self._client.get_collection(collection_name)
        except Exception:
            self._chroma_coll = self._client.create_collection(
                collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        # 初始化 hnswlib 索引
        test_emb = self._embedding_function.embed_query("test")
        dimension = len(test_emb)
        self._hnsw = HNSWIndex(persist_directory, dimension)

        # 设置 ef_search（影响查询速度/精度）
        self._hnsw.set_ef(256)

        # 兼容 vs._collection 属性（部分外部代码直接调用 get/count/delete）
        self.__collection = _ChromaCollectionBridge(self._hnsw, self._chroma_coll, persist_directory)

    @property
    def _collection(self):
        return self.__collection

    @_collection.setter
    def _collection(self, val):
        self.__collection = val

    def similarity_search(self, query: str, k: int = 4) -> list:
        from utils import Document
        query_emb = self._embedding_function.embed_query(query)
        chroma_ids, distances = self._hnsw.query(query_emb, k)

        if not chroma_ids:
            return []

        # 从 ChromaDB 读取
        results = self._chroma_coll.get(ids=chroma_ids, include=['documents', 'metadatas'])
        docs = []
        for cid in chroma_ids:
            try:
                idx = results['ids'].index(cid)
            except ValueError:
                continue
            content = results['documents'][idx] if results.get('documents') else ''
            meta = results['metadatas'][idx] if results.get('metadatas') else {}
            docs.append(Document(page_content=content, metadata=meta or {}))
        return docs

    def as_retriever(self, search_type="similarity", search_kwargs=None):
        return ChromaRetriever(
            self._hnsw, self._chroma_coll, self._embedding_function,
            search_kwargs=search_kwargs,
        )

    def get(self, include=None, where=None):
        """兼容 Chroma.get()"""
        kwargs = {}
        if include:
            kwargs["include"] = include
        if where:
            kwargs["where"] = where
        try:
            return self._chroma_coll.get(**kwargs)
        except Exception:
            return {"documents": [], "metadatas": [], "ids": []}

    def add_documents(self, documents, ids=None):
        if not documents:
            return
        texts = []
        metadatas = []
        doc_ids = ids or [str(uuid.uuid4()) for _ in documents]

        for doc in documents:
            if hasattr(doc, "page_content"):
                texts.append(doc.page_content)
                metadatas.append(getattr(doc, "metadata", {}) or {})
            else:
                texts.append(str(doc))
                metadatas.append({})

        # 计算 embedding
        embeddings = self._embedding_function.embed_documents(texts)

        # 写入 ChromaDB（metadata）
        self._chroma_coll.add(
            ids=doc_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        # 写入 hnswlib（向量索引）
        self._hnsw.add_items(embeddings, doc_ids)

    @classmethod
    def from_documents(cls, documents, embedding, persist_directory=None):
        vs = cls(persist_directory=persist_directory, embedding_function=embedding)
        vs.add_documents(documents)
        return vs

    def delete_collection(self):
        """删除整个集合（hnswlib + ChromaDB metadata）"""
        self._hnsw.delete()
        try:
            self._client.delete_collection("langchain")
        except Exception:
            pass


class _ChromaCollectionBridge:
    """桥接 vs._collection 的外部访问（get/count/delete）"""

    def __init__(self, hnsw: HNSWIndex, chroma_coll, persist_dir: str):
        self._hnsw = hnsw
        self._chroma_coll = chroma_coll
        self._persist_dir = persist_dir

    def _fallback_get(self, ids: list):
        """当 ChromaDB Rust 后端崩溃时，直接从 SQLite 读取"""
        import sqlite3, os
        db_path = os.path.join(self._persist_dir, "chroma.sqlite3")
        if not os.path.isfile(db_path):
            return {"ids": [], "documents": [], "metadatas": []}
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        results = {"ids": [], "documents": [], "metadatas": []}
        for cid in ids:
            # 读文档内容
            cur.execute(
                "SELECT string_value FROM embedding_metadata WHERE id=? AND key='chroma:document'",
                (int(cid),)
            )
            doc_row = cur.fetchone()
            if not doc_row:
                continue
            results["ids"].append(cid)
            results["documents"].append(doc_row[0])

            # 读所有 metadata
            cur.execute(
                "SELECT key, string_value FROM embedding_metadata WHERE id=? AND key!='chroma:document'",
                (int(cid),)
            )
            meta = {k: v for k, v in cur.fetchall()}
            results["metadatas"].append(meta)
        conn.close()
        return results

    def count(self):
        """返回 ChromaDB SQLite 中的真实文档数（不依赖 hnswlib）"""
        import sqlite3, os
        db_path = os.path.join(self._persist_dir, "chroma.sqlite3")
        if not os.path.isfile(db_path):
            return 0
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM embedding_metadata WHERE key='chroma:document'")
            cnt = cur.fetchone()[0]
            conn.close()
            return cnt
        except Exception:
            return self._hnsw.count()

    def get(self, **kwargs):
        try:
            return self._chroma_coll.get(**kwargs)
        except Exception:
            # ChromaDB Rust 后端崩溃时降级到 SQLite
            ids = kwargs.get("ids", [])
            include = kwargs.get("include", ["documents", "metadatas"])
            result = self._fallback_get(ids)
            # 按 include 过滤
            if "documents" not in include:
                result["documents"] = []
            if "metadatas" not in include:
                result["metadatas"] = []
            return result

    def delete(self, ids=None, where=None):
        return self._chroma_coll.delete(ids=ids, where=where)
