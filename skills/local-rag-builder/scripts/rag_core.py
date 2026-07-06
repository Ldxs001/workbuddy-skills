"""
local-rag-builder 共享核心模块
v0.3.0

纯核心层：不涉及任何 LLM 调用，不依赖外部服务。
同时被 rag_skill.py（技能接口）和 rag_standalone.py（独立系统）导入。

v0.3.0 新增：路由层（router）和重排序层（reranker）集成
"""

import os
import json
import re

from config import load_config
from utils import KB_DIR, MODELS_DIR, find_model_dirs


def apply_markdown_preprocess(text: str, preprocess_cfg: dict) -> str:
    """Markdown 标题预处理：根据正则匹配行，注入 Markdown 标题标记"""
    if not preprocess_cfg or not preprocess_cfg.get("enabled"):
        return text

    # 构建 (level_prefix, [compiled_patterns]) 映射，按级别优先
    patterns = []
    for level, prefix in [(1, "# "), (2, "## "), (3, "### "), (4, "#### ")]:
        raw_list = preprocess_cfg.get(f"h{level}_patterns", [])
        compiled = []
        for p in raw_list:
            p = p.strip()
            if p:
                try:
                    compiled.append((re.compile(p), prefix))
                except re.error:
                    pass  # 非法正�则忽略
        patterns.extend(compiled)

    if not patterns:
        return text

    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for pattern, prefix in patterns:
            m = pattern.match(stripped)
            if m:
                title = m.group(1) if m.lastindex and m.lastindex >= 1 else stripped
                result.append(f"{prefix}{title}")
                matched = True
                break
        if not matched:
            result.append(line)

    return "\n".join(result)


def get_embeddings(model_path=None, device="auto", kb_name=None):
    """获取嵌入模型实例。
    如果指定 kb_name，优先使用该知识库的专属模型；没有则回退全局默认。
    """
    from langchain_huggingface import HuggingFaceEmbeddings
    import torch

    cfg = load_config()
    emb_cfg = cfg.get("embedding", {})

    # 如果指定了知识库，优先查 KB 专属模型
    if model_path is None and kb_name:
        try:
            from knowledge_base_manager import get_kb_model
            kb_model = get_kb_model(kb_name)
            if kb_model:
                model_path = kb_model
        except Exception:
            pass

    if model_path is None:
        model_path = emb_cfg.get("model_path", "")

    # 如果 model_path 不是有效路径，尝试从 model_index.json 解析 model_id → 路径
    if model_path and not os.path.exists(model_path):
        from utils import MODELS_DIR
        index_path = os.path.join(MODELS_DIR, "model_index.json")
        if os.path.exists(index_path):
            try:
                import json
                with open(index_path, "r", encoding="utf-8") as f:
                    idx = json.load(f)
                # 精确匹配 model_id
                if model_path in idx:
                    actual = idx[model_path].get("path", "")
                    if actual and os.path.exists(actual):
                        model_path = actual
                # 模糊匹配子路径（如 model_path 是 HuggingFace ID，索引用反斜杠路径）
                if not os.path.exists(model_path):
                    for mid, info in idx.items():
                        if mid.replace("/", "_") in model_path or mid == model_path:
                            actual = info.get("path", "")
                            if actual and os.path.exists(actual):
                                model_path = actual
                                break
            except Exception:
                pass

    # 校验：路径为空或路径失效时回退到扫描 MODELS_DIR
    if not model_path or not os.path.exists(model_path):
        models = find_model_dirs(MODELS_DIR)
        if not models:
            raise ValueError("未找到嵌入模型。请先运行 embedding_model_manager.py 下载模型")
        model_path = models[0]["path"]

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    return HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": device, "local_files_only": True},
        encode_kwargs={"normalize_embeddings": emb_cfg.get("normalize_embeddings", True)},
    )


def retrieve_documents(query, kb_name="default", k=None, score_threshold=None, embeddings=None):
    """检索相关文档"""
    from langchain_chroma import Chroma

    if embeddings is None:
        embeddings = get_embeddings(kb_name=kb_name)

    kb_path = os.path.join(KB_DIR, kb_name)
    if not os.path.exists(kb_path) or not os.listdir(kb_path):
        return []

    # 尝试检索，HNSW 损坏时自动修复
    import time as _t
    for _attempt in range(2):
        try:
            vectorstore = Chroma(
                persist_directory=kb_path,
                embedding_function=embeddings,
            )
            cfg = load_config()
            ret_cfg = cfg.get("retrieval", {})
            if k is None:
                k = ret_cfg.get("k", 3)
            if score_threshold is None:
                score_threshold = ret_cfg.get("score_threshold")

            if score_threshold:
                retriever = vectorstore.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={"score_threshold": score_threshold, "k": k},
                )
            else:
                retriever = vectorstore.as_retriever(search_kwargs={"k": k})

            return retriever.invoke(query)
        except Exception as e:
            err_str = str(e).lower()
            if "hnsw" in err_str or "segment reader" in err_str or "compactor" in err_str:
                from knowledge_base_manager import _try_repair_kb, _backup_kb
                if _attempt == 0 and _try_repair_kb(kb_path):
                    _backup_kb(kb_path)
                    continue
            raise  # 非 HNSW 错误或修复失败则透传


def build_context(docs):
    """从检索结果构建上下文字符串"""
    parts = []
    for i, doc in enumerate(docs):
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        source = meta.get("source", meta.get("h1", f"[{i + 1}]"))
        parts.append(f"[片段 {i + 1}] (来源: {source})\n{content}")
    return "\n\n---\n\n".join(parts)


def retrieve_context(question, kb_name="default", k=None, score_threshold=None, embeddings=None,
                     use_router=True, use_reranker=True):
    """
    纯检索接口：只检索和构建 context，不调用 LLM。

    路由逻辑（v0.3.0）：
    - 从 knowledge_base_manager 直接拿硬编码规则做第一次路由
    - 失败后用 FallbackRouter（KB 签名 + 语义模型）
    - 再失败 → broadcast 所有 KB
    """
    from config import load_config
    cfg = load_config()

    # ==================== 路由阶段 ====================
    if use_router and cfg.get("router", {}).get("enabled", True):
        from router import route_query
        routing = route_query(question)
        kb_names = routing["kb_names"]
        routing_method = routing["method"]
    else:
        kb_names = [kb_name]
        routing_method = "direct"

    # ==================== 检索阶段 ====================
    # Rerank 开启时自动扩容候选池，保证精排有足够的筛选空间
    reranker_enabled = use_reranker and cfg.get("reranker", {}).get("enabled", False)
    if reranker_enabled:
        reranker_top_k = cfg.get("reranker", {}).get("top_k", 5)
        default_k = cfg.get("retrieval", {}).get("k", 3)
        effective_k = k if k is not None else max(default_k, reranker_top_k * 4)
    else:
        effective_k = k

    all_docs = []
    source_kb_map = {}
    for target_kb in kb_names:
        try:
            docs = retrieve_documents(
                question, kb_name=target_kb, k=effective_k,
                score_threshold=score_threshold, embeddings=embeddings,
            )
            for d in docs:
                if hasattr(d, "metadata"):
                    d.metadata["_kb"] = target_kb
                source_kb_map[id(d)] = target_kb
            all_docs.extend(docs)
        except Exception:
            continue

    # ==================== Rerank 阶段 ====================
    if use_reranker and cfg.get("reranker", {}).get("enabled", True) and all_docs:
        from reranker import Reranker
        try:
            reranker = Reranker(cfg)
            reranked = reranker.rerank(question, all_docs)
            reranked_docs = [d for d, _ in reranked]
        except Exception:
            reranked_docs = all_docs
    else:
        reranked_docs = all_docs

    # ==================== 构建输出 ====================
    if not reranked_docs:
        return {
            "context": "",
            "source_docs": [],
            "source_count": 0,
            "question": question,
            "routing_info": {
                "method": routing_method,
                "kb_names": kb_names,
                "kb_count": len(kb_names),
            },
        }

    context = build_context(reranked_docs)
    serialized = []
    for d in reranked_docs:
        source_kb = source_kb_map.get(id(d), kb_name)
        serialized.append({
            "content": d.page_content if hasattr(d, "page_content") else str(d),
            "metadata": d.metadata if hasattr(d, "metadata") else {},
            "length": len(d.page_content) if hasattr(d, "page_content") else len(str(d)),
            "_kb": source_kb,
        })

    return {
        "context": context,
        "source_docs": serialized,
        "source_count": len(reranked_docs),
        "question": question,
        "routing_info": {
            "method": routing_method,
            "kb_names": kb_names,
            "kb_count": len(kb_names),
        },
    }


def format_skill_output(question, kb_name="default", k=None, score_threshold=None,
                        embeddings=None, template=None):
    """
    [技能接口核心] 检索 + 格式化输出。
    返回的 JSON 包含完整的 prompt（已填充 {context} 和 {question}），
    任何智能体直接拿着 prompt 即可作答。

    返回结构:
    {
      "question": str,          # 原始问题
      "kb": str,                # 检索的知识库
      "context": str,           # 检索到的文本块
      "source_count": int,      # 命中的片段数
      "source_docs": [...],     # 每个片段的详情
      "prompt": str,            # 已填充的完整 prompt（含 context + question）
      "prompt_template": str,   # 原始 prompt 模板
      "has_context": bool,      # 是否找到相关内容
    }
    """
    from prompt_manager import load_template, get_default_template, get_full_prompt

    # 检索
    retrieval = retrieve_context(
        question, kb_name=kb_name, k=k,
        score_threshold=score_threshold, embeddings=embeddings,
    )

    context = retrieval["context"]
    has_context = bool(context)

    # 获取完整 prompt（系统层 + 用户层）
    tpl = get_full_prompt(template)

    # 填充占位符
    if has_context:
        prompt = tpl.format(context=context, question=question)
    else:
        # 无 context 时也尝试填充，占位符缺失则保留原样
        try:
            prompt = tpl.format(context="（未检索到相关资料）", question=question)
        except KeyError:
            prompt = tpl.replace("{context}", "（未检索到相关资料）").replace("{question}", question)

    return {
        "question": question,
        "kb": kb_name,
        "context": context,
        "source_count": retrieval["source_count"],
        "source_docs": retrieval["source_docs"],
        "prompt": prompt,
        "prompt_template": tpl,
        "has_context": has_context,
    }


def import_documents_to_kb(file_path, kb_name="default", embeddings=None, splitter_config=None):
    """导入文档到知识库

    v0.3.0 新增：导入后自动更新 KB 签名
    """
    from text_splitter import split_pipeline
    from knowledge_base_manager import add_documents_to_kb

    if embeddings is None:
        embeddings = get_embeddings(kb_name=kb_name)

    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            # 扫描版 PDF 自动回退 OCR
            total_chars = sum(len(d.page_content) for d in docs)
            # 中文文本质量检测：文件名含中文但提取文本中 CJK 字符占比过低 → 编码乱码
            fname = os.path.basename(file_path)
            has_chinese_filename = bool(re.search(r'[\u4e00-\u9fff]', fname))
            if total_chars >= 50 and has_chinese_filename:
                all_text = "".join(d.page_content for d in docs)
                cjk = sum(1 for c in all_text if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf')
                cjk_ratio = cjk / max(total_chars, 1)
                if cjk_ratio < 0.10 and total_chars > 100:
                    print(f"  [OCR fallback] 中文文件名但 CJK 占比 {cjk_ratio:.1%}，触发 OCR")
                    total_chars = 0  # 强制走 OCR 回退
            if total_chars < 50:
                try:
                    from pdf2image import convert_from_path
                    import numpy as np
                    import easyocr
                    reader = easyocr.Reader(["ch_sim", "en"])
                    images = convert_from_path(file_path, dpi=200)
                    all_text = []
                    for img in images:
                        arr = np.array(img)
                        result = reader.readtext(arr)
                        all_text.append("\n".join([r[1] for r in result]))
                    from langchain_core.documents import Document
                    docs = [Document(
                        page_content="\n\n--- 换页 ---\n\n".join(all_text),
                        metadata={"source": os.path.basename(file_path), "ocr": True}
                    )]
                except Exception as ocr_err:
                    raise RuntimeError(f"PDF 无文本且 OCR 失败: {ocr_err}")
        else:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path, encoding="utf-8")
            docs = loader.load()
    except Exception as e:
        raise RuntimeError(f"文档加载失败: {e}")

    cfg = load_config()
    split_cfg = splitter_config or cfg.get("splitting", {})

    # 合并基础配置 + 策略级覆盖
    strategy_overrides = split_cfg.get("strategy_overrides", {})
    primary = split_cfg.get("strategy", "recursive")
    sec_strat = split_cfg.get("secondary_strategy")

    pipeline_kwargs = dict(
        guards=split_cfg.get("guards", ["code"]),
        primary=primary,
        secondary=sec_strat,
        chunk_size=split_cfg.get("chunk_size", 500),
        chunk_overlap=split_cfg.get("chunk_overlap", 50),
        separators=split_cfg.get("separators"),
        headers_to_split_on=split_cfg.get("headers_to_split_on"),
        strip_headers=split_cfg.get("strip_headers", False),
        strategy_overrides=strategy_overrides,
        embeddings=embeddings,
    )

    # 从 strategy_overrides 注入当前策略的专属参数
    over = strategy_overrides.get(primary, {})
    for k in ("separators", "headers_to_split_on", "strip_headers", "breakpoint_type", "language", "delimiters"):
        if k in over:
            pipeline_kwargs[k] = over[k]

    # Markdown 标题预处理（守卫栈之后、切片之前）
    preprocess_cfg = cfg.get("preprocess", {})
    if preprocess_cfg.get("enabled"):
        # 合并所有页的文本（PDF 多页时 PyPDFLoader 每页一个 Document）
        text = "\n\n".join(d.page_content for d in docs)
        docs[0].page_content = apply_markdown_preprocess(text, preprocess_cfg)
        primary = "headers"
        pipeline_kwargs["primary"] = "headers"
        if not pipeline_kwargs.get("headers_to_split_on"):
            pipeline_kwargs["headers_to_split_on"] = [
                ("h1", "# "), ("h2", "## "), ("h3", "### "), ("h4", "#### ")
            ]

    chunks = split_pipeline(docs[0].page_content, **pipeline_kwargs)

    for chunk in chunks:
        chunk.metadata["source"] = os.path.basename(file_path)

    ok, msg = add_documents_to_kb(kb_name, chunks, embeddings)

    # 导入后自动更新 KB 签名
    router_cfg = cfg.get("router", {})
    if router_cfg.get("fallback", {}).get("auto_update_signatures", True):
        try:
            from router import update_kb_signature
            update_kb_signature(kb_name, chunks)
        except Exception:
            pass

    return {
        "success": ok,
        "message": msg,
        "chunks_count": len(chunks),
        "source": os.path.basename(file_path),
    }
