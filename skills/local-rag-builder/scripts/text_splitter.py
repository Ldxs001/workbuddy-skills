"""
local-rag-builder 文本切分模块
v0.1.0
支持 6 种切分策略及组合：固定窗口、递归切、层级/标题切、按句切、语义切、代码块保护切
"""

import os
import sys
import re
import json

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "output")


def split_fixed_size(text, chunk_size=500, chunk_overlap=50):
    """策略1: 固定窗口切分"""
    from langchain_text_splitters import CharacterTextSplitter
    from langchain_core.documents import Document

    splitter = CharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separator="",
    )
    docs = [Document(page_content=text)]
    return splitter.split_documents(docs)


def split_recursive(text, chunk_size=500, chunk_overlap=50, separators=None):
    """策略2: 递归切分"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document

    if separators is None:
        separators = ["\n\n", "\n", "。", "；", "，", " ", ""]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
    )
    docs = [Document(page_content=text)]
    return splitter.split_documents(docs)


def split_by_headers(text, headers_to_split_on=None, strip_headers=False):
    """策略3: 层级/标题切分"""
    from langchain_text_splitters import MarkdownHeaderTextSplitter

    if headers_to_split_on is None:
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ]

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=strip_headers,
    )
    return splitter.split_text(text)


def split_by_sentence(text):
    """策略4: 按句切分"""
    from langchain_core.documents import Document

    try:
        import nltk
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)
        sentences = nltk.sent_tokenize(text, language="chinese")
    except (ImportError, Exception):
        # 回退到中文句号切分
        sentences = [s.strip() for s in re.split(r'[。！？!?]', text) if s.strip()]
        sentences = [s + "。" for s in sentences if s]

    docs = []
    for s in sentences:
        if s.strip():
            docs.append(Document(page_content=s.strip()))
    return docs


def split_semantic(text, embeddings=None, breakpoint_type="percentile"):
    """策略5: 语义切分（需 langchain-experimental）"""
    try:
        from langchain_experimental.text_splitter import SemanticChunker
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        raise ImportError("语义切分需要 langchain-experimental: pip install langchain-experimental")

    if embeddings is None:
        # 尝试使用默认嵌入
        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")

    splitter = SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type=breakpoint_type,
    )
    return splitter.split_text(text)


def split_with_mermaid_preserve(text, headers_to_split_on=None, strip_headers=False):
    """策略6: 代码块保护切分（先保护 mermaid，再按标题切，最后还原）"""
    mermaid_blocks = []

    def replacer(match):
        mermaid_blocks.append(match.group(0))
        return f"__MERMAID_BLOCK_{len(mermaid_blocks) - 1}__"

    protected = re.sub(r'```mermaid\s*\n[\s\S]*?\n```', replacer, text, flags=re.MULTILINE)

    # 用层级切分
    chunks = split_by_headers(protected, headers_to_split_on, strip_headers)

    # 还原 mermaid 块
    for chunk in chunks:
        for i, block in enumerate(mermaid_blocks):
            chunk.page_content = chunk.page_content.replace(f"__MERMAID_BLOCK_{i}__", block)

    return chunks


def combo_split(text, primary_strategy="recursive", secondary_strategy=None,
                chunk_size=500, chunk_overlap=50, **kwargs):
    """
    组合切分：先用主策略，再对结果二次切分
    返回 Document 列表
    """
    # 主切分
    primary_map = {
        "fixed": split_fixed_size,
        "recursive": split_recursive,
        "headers": split_by_headers,
        "sentence": split_by_sentence,
        "semantic": split_semantic,
        "mermaid": split_with_mermaid_preserve,
    }

    splitter_fn = primary_map.get(primary_strategy)
    if splitter_fn is None:
        raise ValueError(f"未知切分策略: {primary_strategy}，可选: {', '.join(primary_map.keys())}")

    # 第一次切分
    if primary_strategy in ("fixed", "recursive"):
        chunks = splitter_fn(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif primary_strategy == "headers":
        chunks = splitter_fn(text, **{k: kwargs.get(k) for k in ("headers_to_split_on", "strip_headers") if k in kwargs})
    elif primary_strategy == "sentence":
        chunks = splitter_fn(text)
    elif primary_strategy == "semantic":
        chunks = splitter_fn(text, breakpoint_type=kwargs.get("semantic_breakpoint", "percentile"))
    elif primary_strategy == "mermaid":
        chunks = splitter_fn(text, **{k: kwargs.get(k) for k in ("headers_to_split_on", "strip_headers") if k in kwargs})
    else:
        chunks = splitter_fn(text)

    if not secondary_strategy or secondary_strategy == primary_strategy:
        return chunks

    # 二次切分
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    secondary_map = {
        "recursive": RecursiveCharacterTextSplitter(
            chunk_size=chunk_size // 2,
            chunk_overlap=chunk_overlap // 2,
        ),
        "fixed": CharacterTextSplitter(
            chunk_size=chunk_size // 2,
            chunk_overlap=chunk_overlap // 2,
        ),
    }

    secondary = secondary_map.get(secondary_strategy)
    if secondary:
        result = []
        for doc in chunks:
            result.extend(secondary.split_documents([doc]))
        return result

    return chunks


def format_chunks_report(chunks):
    """格式化切分结果报告"""
    lines = [f"切分结果: {len(chunks)} 个块", ""]
    for i, chunk in enumerate(chunks):
        meta = chunk.metadata if hasattr(chunk, "metadata") else {}
        content = chunk.page_content if hasattr(chunk, "page_content") else str(chunk)
        meta_str = json.dumps(meta, ensure_ascii=False) if meta else ""
        lines.append(f"[{i + 1}] {len(content)} 字符 {meta_str}")
        lines.append(content[:150] + ("..." if len(content) > 150 else ""))
        lines.append("")
    return "\n".join(lines)


def save_chunks(chunks, output_path=None):
    """保存切分结果到文件"""
    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, "chunks_output.json")

    data = []
    for chunk in chunks:
        data.append({
            "content": chunk.page_content if hasattr(chunk, "page_content") else str(chunk),
            "metadata": chunk.metadata if hasattr(chunk, "metadata") else {},
            "length": len(chunk.page_content) if hasattr(chunk, "page_content") else len(str(chunk)),
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="文本切分工具")
    parser.add_argument("--input", type=str, required=True, help="输入文件路径 (txt/md)")
    parser.add_argument("--strategy", type=str, default="recursive",
                        choices=["fixed", "recursive", "headers", "sentence", "semantic", "mermaid"],
                        help="切分策略")
    parser.add_argument("--secondary", type=str, choices=["recursive", "fixed"], help="二次切分策略")
    parser.add_argument("--chunk-size", type=int, default=500, help="块大小")
    parser.add_argument("--overlap", type=int, default=50, help="重叠字符数")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--list-strategies", action="store_true", help="列出可用策略")

    args = parser.parse_args()

    if args.list_strategies:
        strategies = [
            ("fixed", "固定窗口切分", "按固定字符数切分，可设重叠"),
            ("recursive", "递归切分", "按优先级尝试不同分隔符，性价比最高"),
            ("headers", "层级/标题切分", "基于 Markdown 标题切分，保留结构元数据"),
            ("sentence", "按句切分", "以句子为单位，适合证据抽取"),
            ("semantic", "语义切分", "计算相邻句子相似度，精度最高但成本高"),
            ("mermaid", "代码块保护切分", "先保护 mermaid 再按标题切，适合含流程图文档"),
        ]
        print("可用切分策略:")
        print("-" * 60)
        for name, title, desc in strategies:
            print(f"  {name:<15} {title:<20} {desc}")
        sys.exit(0)

    if not os.path.exists(args.input):
        print(f"[!] 输入文件不存在: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    print(f"输入文件: {args.input} ({len(text)} 字符)")
    print(f"策略: {args.strategy}", end="")
    if args.secondary:
        print(f" + {args.secondary}")
    else:
        print()

    if args.secondary:
        kwargs = {
            "semantic_breakpoint": "percentile",
            "headers_to_split_on": [("#", "h1"), ("##", "h2"), ("###", "h3")],
            "strip_headers": False,
        }
        chunks = combo_split(
            text,
            primary_strategy=args.strategy,
            secondary_strategy=args.secondary,
            chunk_size=args.chunk_size,
            chunk_overlap=args.overlap,
            **kwargs
        )
    else:
        strategy_map = {
            "fixed": lambda: split_fixed_size(text, args.chunk_size, args.overlap),
            "recursive": lambda: split_recursive(text, args.chunk_size, args.overlap),
            "headers": lambda: split_by_headers(text),
            "sentence": lambda: split_by_sentence(text),
            "semantic": lambda: split_semantic(text),
            "mermaid": lambda: split_with_mermaid_preserve(text),
        }
        chunks = strategy_map[args.strategy]()

    if args.json:
        data = []
        for chunk in chunks:
            data.append({
                "content": chunk.page_content if hasattr(chunk, "page_content") else str(chunk),
                "metadata": chunk.metadata if hasattr(chunk, "metadata") else {},
                "length": len(chunk.page_content) if hasattr(chunk, "page_content") else len(str(chunk)),
            })
        print(json.dumps({"total_chunks": len(chunks), "chunks": data}, ensure_ascii=False, indent=2))
    else:
        print(format_chunks_report(chunks))

    if args.output:
        path = save_chunks(chunks, args.output)
        print(f"\n已保存到: {path}")
