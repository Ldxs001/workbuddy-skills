"""
Embedding 模型包装器（替代 langchain_huggingface.HuggingFaceEmbeddings）
直接使用 sentence-transformers 原生 API
"""

import logging

logger = logging.getLogger(__name__)

# 模块级缓存 key=(model_path, device)
_EMBEDDING_CACHE: dict = {}


class SentenceTransformerEmbeddings:
    """与 HuggingFaceEmbeddings 接口兼容的 SentenceTransformer 包装器"""

    def __init__(self, model_name: str = "", model_kwargs: dict = None,
                 encode_kwargs: dict = None):
        if model_kwargs is None:
            model_kwargs = {}
        if encode_kwargs is None:
            encode_kwargs = {}

        self._model_path = model_name
        self._local_files_only = model_kwargs.get("local_files_only", False)
        self._device = model_kwargs.get("device", "cpu")
        self._normalize = encode_kwargs.get("normalize_embeddings", True)

        from sentence_transformers import SentenceTransformer
        import os

        model_kw = {}
        if self._local_files_only:
            model_kw["local_files_only"] = True

        self._model = SentenceTransformer(model_name, **model_kw)
        self._model.to(self._device)
        logger.debug(f"Loaded embedding model: {model_name} on {self._device}")

    def embed_query(self, text: str) -> list[float]:
        """将单条文本转为向量（兼容 HuggingFaceEmbeddings 接口）"""
        return self._model.encode(text, normalize_embeddings=self._normalize).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """将多条文本转为向量"""
        embeddings = self._model.encode(texts, normalize_embeddings=self._normalize)
        return [emb.tolist() for emb in embeddings]

    @property
    def model(self):
        return self._model


def get_embeddings(model_path: str, device: str = "cpu",
                   local_files_only: bool = True,
                   normalize_embeddings: bool = True,
                   kb_name: str = None) -> SentenceTransformerEmbeddings:
    """获取嵌入模型实例（模块级缓存）"""
    cache_key = f"{model_path}::{device}"
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]

    emb = SentenceTransformerEmbeddings(
        model_name=model_path,
        model_kwargs={"device": device, "local_files_only": local_files_only},
        encode_kwargs={"normalize_embeddings": normalize_embeddings},
    )
    _EMBEDDING_CACHE[cache_key] = emb
    return emb


def get_model_dimension(model_id: str) -> int | None:
    """运行时检测模型的向量维度"""
    try:
        dim = _MODEL_DIMENSION_MAP.get(model_id)
        if dim is not None:
            return dim
    except NameError:
        pass
    try:
        emb = SentenceTransformerEmbeddings(
            model_name=model_id,
            model_kwargs={"local_files_only": True},
        )
        return len(emb.embed_query("测"))
    except Exception:
        return None


# 常用模型维度表（避免运行时加载检测）
_MODEL_DIMENSION_MAP = {
    "BAAI/bge-small-zh-v1.5": 512,
    "BAAI/bge-base-zh-v1.5": 768,
    "BAAI/bge-large-zh-v1.5": 1024,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-m3": 1024,
    "intfloat/multilingual-e5-small": 384,
    "intfloat/multilingual-e5-base": 768,
    "intfloat/multilingual-e5-large": 1024,
    "shibing624/text2vec-base-chinese": 768,
    "maidalun1020/bce-embedding-base_v1": 768,
    "Alibaba-NLP/gte-Qwen2-7B-instruct": 3584,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
}
