"""
local-rag-builder RAG 核心引擎模块
v0.1.0
整合嵌入模型、向量检索、LLM 调用
"""

import os
import sys
import re
import json

from config import load_config, save_config
from utils import KB_DIR, OUTPUT_DIR, find_model_dirs, MODELS_DIR


def get_embeddings(model_path=None, device="auto"):
    """获取嵌入模型实例"""
    from langchain_huggingface import HuggingFaceEmbeddings
    import torch

    cfg = load_config()
    emb_cfg = cfg.get("embedding", {})

    if model_path is None:
        model_path = emb_cfg.get("model_path", "")
    if not model_path:
        # 自动查找已下载的模型
        models = find_model_dirs(MODELS_DIR)
        if not models:
            raise ValueError("未找到嵌入模型。请先运行 embedding_model_manager.py 下载模型")
        model_path = models[0]["path"]

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    return HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": emb_cfg.get("normalize_embeddings", True)},
    )


def get_vectorstore(kb_name="default", embeddings=None):
    """获取向量存储"""
    from langchain_chroma import Chroma

    if embeddings is None:
        embeddings = get_embeddings()

    kb_path = os.path.join(KB_DIR, kb_name)
    os.makedirs(kb_path, exist_ok=True)

    if os.path.exists(kb_path) and os.listdir(kb_path):
        return Chroma(
            persist_directory=kb_path,
            embedding_function=embeddings,
        )
    return None


def retrieve_documents(query, kb_name="default", k=3, score_threshold=None, embeddings=None):
    """检索相关文档"""
    from langchain_chroma import Chroma

    if embeddings is None:
        embeddings = get_embeddings()

    kb_path = os.path.join(KB_DIR, kb_name)
    if not os.path.exists(kb_path) or not os.listdir(kb_path):
        return []

    vectorstore = Chroma(
        persist_directory=kb_path,
        embedding_function=embeddings,
    )

    cfg = load_config()
    ret_cfg = cfg.get("retrieval", {})
    k = k or ret_cfg.get("k", 3)
    score_threshold = score_threshold if score_threshold is not None else ret_cfg.get("score_threshold")

    if score_threshold:
        retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": score_threshold, "k": k},
        )
    else:
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})

    return retriever.invoke(query)


def get_llm(base_url=None, temperature=None, max_tokens=None):
    """获取 LLM 实例（通过 OpenAI 兼容接口）"""
    from langchain_community.llms import OpenAI

    cfg = load_config()
    llm_cfg = cfg.get("llm", {})

    return OpenAI(
        base_url=base_url or llm_cfg.get("base_url", "http://localhost:1234/v1"),
        api_key=llm_cfg.get("api_key", "not-needed"),
        temperature=temperature if temperature is not None else llm_cfg.get("temperature", 0.1),
        max_tokens=max_tokens or llm_cfg.get("max_tokens", 512),
    )


def build_context(docs):
    """从检索结果构建上下文文本"""
    parts = []
    for i, doc in enumerate(docs):
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        source = meta.get("source", meta.get("h1", f"[{i + 1}]"))
        parts.append(f"[片段 {i + 1}] (来源: {source})\n{content}")
    return "\n\n---\n\n".join(parts)


def answer_question(question, kb_name="default", template=None, llm_instance=None,
                    embeddings=None, k=None, score_threshold=None):
    """
    完整 RAG 问答流程
    返回: {"answer": str, "source_docs": list, "context": str}
    """
    from prompt_manager import build_prompt

    # 检索
    docs = retrieve_documents(
        question, kb_name=kb_name, k=k,
        score_threshold=score_threshold, embeddings=embeddings,
    )

    if not docs:
        return {
            "answer": "知识库中未找到相关信息。请先导入文档。",
            "source_docs": [],
            "context": "",
        }

    # 构建上下文
    context = build_context(docs)

    # 构建 Prompt
    prompt = build_prompt(context, question, template)

    # 调用 LLM
    if llm_instance is None:
        llm_instance = get_llm()

    try:
        raw_answer = llm_instance.invoke(prompt)
    except Exception as e:
        return {
            "answer": f"LLM 调用失败: {str(e)}\n请确保 LM Studio 或兼容服务正在运行。",
            "source_docs": docs,
            "context": context,
        }

    # 清理 think 标签
    clean_answer = re.sub(r"<think>.*?</think>\s*", "", raw_answer, flags=re.DOTALL).strip()

    return {
        "answer": clean_answer,
        "source_docs": docs,
        "context": context,
    }


def import_documents_to_kb(file_path, kb_name="default", embeddings=None, splitter_config=None):
    """导入文档到知识库"""
    from text_splitter import split_recursive
    from knowledge_base_manager import add_documents_to_kb

    if embeddings is None:
        embeddings = get_embeddings()

    # 加载文档
    try:
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
    except Exception as e:
        raise RuntimeError(f"文档加载失败: {e}")

    cfg = load_config()
    split_cfg = splitter_config or cfg.get("splitting", {})

    # 切分
    chunks = split_recursive(
        docs[0].page_content,
        chunk_size=split_cfg.get("chunk_size", 500),
        chunk_overlap=split_cfg.get("chunk_overlap", 50),
        separators=split_cfg.get("separators"),
    )

    # 保留元数据
    for chunk in chunks:
        chunk.metadata["source"] = os.path.basename(file_path)

    # 入库
    ok, msg = add_documents_to_kb(kb_name, chunks, embeddings)

    return {
        "success": ok,
        "message": msg,
        "chunks_count": len(chunks),
        "source": os.path.basename(file_path),
    }


def verify_llm_connection():
    """验证 LLM 连接"""
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    base_url = llm_cfg.get("base_url", "http://localhost:1234/v1")

    import urllib.request
    try:
        req = urllib.request.Request(f"{base_url}/models")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "LLM 连接正常"
    except Exception as e:
        return False, f"LLM 连接失败: {e}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG 核心引擎")
    parser.add_argument("--question", type=str, help="提问")
    parser.add_argument("--kb", type=str, default="default", help="知识库名称")
    parser.add_argument("--import-file", type=str, dest="import_file", help="导入文件")
    parser.add_argument("--k", type=int, help="检索文档数")
    parser.add_argument("--threshold", type=float, help="相似度阈值")
    parser.add_argument("--verify-llm", action="store_true", help="验证 LLM 连接")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    if args.verify_llm:
        ok, msg = verify_llm_connection()
        print(f"[{'OK' if ok else '!'}] {msg}")
        if args.json:
            print(json.dumps({"success": ok, "message": msg}, ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.import_file:
        if not os.path.exists(args.import_file):
            print(f"[!] 文件不存在: {args.import_file}")
            sys.exit(1)
        print(f"导入 {args.import_file} 到知识库 '{args.kb}'...")
        try:
            result = import_documents_to_kb(args.import_file, args.kb)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"[{'OK' if result['success'] else '!'}] {result['message']}")
                print(f"  切分块数: {result['chunks_count']}")
        except Exception as e:
            print(f"[!] 导入失败: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.question:
        result = answer_question(
            args.question, kb_name=args.kb,
            k=args.k, score_threshold=args.threshold,
        )
        if args.json:
            print(json.dumps({
                "answer": result["answer"],
                "source_count": len(result["source_docs"]),
            }, ensure_ascii=False, indent=2))
        else:
            print(f"\n答案:\n{result['answer']}")
            if result["source_docs"]:
                print(f"\n引用来源 ({len(result['source_docs'])} 个片段):")
                for i, doc in enumerate(result["source_docs"]):
                    content = doc.page_content[:100] if hasattr(doc, "page_content") else str(doc)[:100]
                    print(f"  [{i + 1}] {content}...")
        sys.exit(0)

    parser.print_help()
