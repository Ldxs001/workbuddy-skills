"""
local-rag-builder 文本切分模块
v1.0.0

架构：插件注册 → 守卫栈(多选) → 主策略(单选) → 后处理(单选/不选)

插件化设计：
  - 每个策略/守卫是一个 Plugin 对象，声明 name/description/config_schema/default_config
  - 通过 register_strategy() / register_guard() 注册
  - 外部用户可通过 register_* 添加自定义策略
  - Web UI 通过 plugin.config_schema 动态渲染配置表单

内置策略：fixed / recursive / headers / sentence / semantic（5种）
内置守卫：mermaid / code / math / table / html（5种）
"""

import os
import sys
import re
import json

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "output")

# ==================== 插件注册架构 ====================

class StrategyPlugin:
    """策略插件：包裹一个切分函数及其配置声明"""
    def __init__(self, name, description, fn, config_schema=None, default_config=None):
        self.name = name
        self.description = description
        self.fn = fn  # fn(text, **resolved_config) → List[Document]
        self.config_schema = config_schema or {}  # {key: {type, label, default, options, min, max, ...}}
        self.default_config = default_config or {}

    def execute(self, text, config=None, **kwargs):
        resolved = dict(self.default_config)
        if config:
            resolved.update(config)
        resolved.update(kwargs)
        return self.fn(text, **resolved)


class GuardPlugin:
    """守卫插件：包裹一个 Guard 及其配置声明"""
    def __init__(self, name, description, guard, config_schema=None, default_config=None):
        self.name = name
        self.description = description
        self.guard = guard  # Guard instance
        self.config_schema = config_schema or {}
        self.default_config = default_config or {}


STRATEGY_REGISTRY = {}  # {name: StrategyPlugin}
GUARD_REGISTRY = {}     # {name: GuardPlugin}


def register_strategy(plugin):
    """注册切分策略"""
    STRATEGY_REGISTRY[plugin.name] = plugin


def register_guard(plugin):
    """注册守卫"""
    GUARD_REGISTRY[plugin.name] = plugin


def get_strategy_config_schema(strategy_name):
    """获取策略的 config_schema（供 Web UI 渲染用）"""
    p = STRATEGY_REGISTRY.get(strategy_name)
    return p.config_schema if p else {}


def get_all_strategies_info():
    """返回 [{name, description, config_schema}] 供 Web UI 用"""
    return [{"name": p.name, "description": p.description, "config_schema": p.config_schema}
            for p in STRATEGY_REGISTRY.values()]


def get_all_guards_info():
    """返回 [{name, description, config_schema}] 供 Web UI 用"""
    return [{"name": p.name, "description": p.description, "config_schema": p.config_schema}
            for p in GUARD_REGISTRY.values()]


# 元数据白名单
INHERITABLE_META_KEYS = {"source", "h1", "h2", "h3", "group_id"}


def filter_inheritable_meta(metadata: dict) -> dict:
    """过滤可继承的元数据（扔掉 chunk_id/start_pos 等位置信息）"""
    return {k: v for k, v in metadata.items() if k in INHERITABLE_META_KEYS}


# ==================== 守卫栈 ====================

class Guard:
    """单个守卫：protect 替换 → restore 还原"""
    def __init__(self, name: str, pattern: re.Pattern):
        self.name = name
        self.pattern = pattern
        self._blocks: list[str] = []

    @property
    def _prefix(self):
        return f"__GUARD_{self.name.upper()}_"

    def protect(self, text: str) -> str:
        """替换匹配内容为占位符，返回保护后的文本"""
        self._blocks = []

        def _replacer(m):
            self._blocks.append(m.group(0))
            return f"{self._prefix}{len(self._blocks) - 1}__"

        return self.pattern.sub(_replacer, text)

    def restore(self, text: str) -> str:
        """将占位符还原为原始内容"""
        for i, block in enumerate(self._blocks):
            text = text.replace(f"{self._prefix}{i}__", block)
        return text

    def restore_chunks(self, chunks: list) -> list:
        """对 chunks 列表进行内容还原"""
        for chunk in chunks:
            if hasattr(chunk, "page_content"):
                chunk.page_content = self.restore(chunk.page_content)
        return chunks

    def reset(self):
        self._blocks = []


# 内置守卫定义
GUARD_MERMAID = Guard(
    "mermaid",
    re.compile(r'```mermaid\s*\n[\s\S]*?\n```', re.MULTILINE),
)

GUARD_CODE = Guard(
    "code",
    re.compile(r'```\w*\n[\s\S]*?\n```', re.MULTILINE),
)

GUARD_MATH = Guard(
    "math",
    re.compile(r'\$\$[\s\S]*?\$\$', re.MULTILINE),
)

# 表格守卫：保护标准 Markdown 表格行（不保护单行，保护连续表格块）
# 匹配至少两行连续的 | ... | 模式
_TABLE_PATTERN = re.compile(
    r'(?:\|.*\|(?:\s*$)\n?){2,}',
    re.MULTILINE,
)
GUARD_TABLE = Guard("table", _TABLE_PATTERN)

# HTML 块级标签守卫（div, table, pre, section, article, main, aside, details）
_HTML_BLOCK_PATTERN = re.compile(
    r'<(div|table|pre|section|article|main|aside|details|blockquote|figure|figcaption)'
    r'[^>]*>[\s\S]*?</\1>',
    re.MULTILINE | re.IGNORECASE,
)
GUARD_HTML = Guard("html", _HTML_BLOCK_PATTERN)

ALL_GUARDS = {
    "mermaid": GUARD_MERMAID,
    "code": GUARD_CODE,
    "math": GUARD_MATH,
    "table": GUARD_TABLE,
    "html": GUARD_HTML,
}


class GuardStack:
    """守卫栈：多个守卫按序执行 protect，反向执行 restore"""

    def __init__(self, guard_names=None):
        self.guards: list[Guard] = []
        if guard_names:
            for name in guard_names:
                name = name.strip().lower()
                if name in ALL_GUARDS:
                    self.guards.append(ALL_GUARDS[name])

    def add(self, name: str):
        name = name.strip().lower()
        if name in ALL_GUARDS and name not in [g.name for g in self.guards]:
            self.guards.append(ALL_GUARDS[name])

    def apply(self, text: str) -> str:
        """按序执行所有守卫的 protect"""
        for g in self.guards:
            g.reset()
            text = g.protect(text)
        return text

    def restore(self, text: str) -> str:
        """反向执行所有守卫的 restore"""
        for g in reversed(self.guards):
            text = g.restore(text)
        return text

    def restore_chunks(self, chunks: list) -> list:
        """反向执行所有守卫的 restore_chunks"""
        for g in reversed(self.guards):
            chunks = g.restore_chunks(chunks)
        return chunks

    def __len__(self):
        return len(self.guards)

    def __repr__(self):
        return f"GuardStack({[g.name for g in self.guards]})"


# ==================== 单策略切分函数（保持不变）====================

def split_fixed_size(text, chunk_size=500, chunk_overlap=50):
    """策略1: 固定窗口切分"""
    from utils import Document

    if chunk_size < 1:
        chunk_size = 500
    if chunk_overlap < 0:
        chunk_overlap = 0
    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 4

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(Document(page_content=text[start:end]))
        if end >= len(text):
            break
        start += chunk_size - chunk_overlap
    return chunks if chunks else [Document(page_content=text)]


def split_recursive(text, chunk_size=500, chunk_overlap=50, separators=None):
    """策略2: 递归切分（按分隔符优先级递归）"""
    from utils import Document

    if separators is None:
        separators = ["\n\n", "\n", "。", "；", "，", " ", ""]

    def _join_chunks(chunks, overlap):
        """合并过小的 chunks，加入重叠"""
        if not chunks:
            return chunks
        merged = [chunks[0]]
        for c in chunks[1:]:
            if len(merged[-1].page_content) + len(c.page_content) < chunk_size * 0.8:
                merged[-1].page_content += c.page_content
                if hasattr(c, "metadata") and c.metadata:
                    merged[-1].metadata.update(c.metadata)
            else:
                merged.append(c)

        # 加重叠
        if overlap > 0 and len(merged) > 1:
            result = [merged[0]]
            for i in range(1, len(merged)):
                prev = merged[i - 1].page_content
                overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                merged[i].page_content = overlap_text + merged[i].page_content
                result.append(merged[i])
            return result
        return merged

    def _split(text, seps, size, overlap):
        if not seps or len(text) <= size:
            return [Document(page_content=text)]
        sep = seps[0]
        if sep == "":
            # 最后一个分隔符：逐字符切
            result = []
            start = 0
            while start < len(text):
                end = min(start + size, len(text))
                result.append(Document(page_content=text[start:end]))
                if end >= len(text):
                    break
                start += size - overlap
            return result

        parts = text.split(sep)
        chunks = []
        current = ""
        for part in parts:
            if not part:
                continue
            candidate = current + sep + part if current else part
            if len(candidate) <= size:
                current = candidate
            else:
                if current:
                    chunks.append(Document(page_content=current))
                # 单部分超长：递归到下一级分隔符
                sub = _split(part, seps[1:], size, overlap)
                chunks.extend(sub)
                current = ""
        if current:
            chunks.append(Document(page_content=current))
        return _join_chunks(chunks, overlap)

    return _split(text, separators, chunk_size, chunk_overlap)


def split_by_headers(text, headers_to_split_on=None, strip_headers=False):
    """策略3: 层级/标题切分"""
    from utils import Document

    if headers_to_split_on is None:
        headers_to_split_on = [("#", "h1"), ("##", "h2"), ("###", "h3")]

    # 构建正则：匹配所有指定的标题级别
    level_patterns = []
    for marker, field in headers_to_split_on:
        escaped = re.escape(marker)
        level_patterns.append((marker, field, re.compile(rf'^{escaped}\s+(.+)$', re.MULTILINE)))

    # 按行处理，跟踪当前标题层级
    lines = text.split('\n')
    chunks = []
    current_section_lines = []
    active_headers = {}  # {field: title}

    def flush():
        if not current_section_lines:
            return
        content = '\n'.join(current_section_lines).strip()
        if content:
            meta = dict(active_headers)
            chunks.append(Document(page_content=content, metadata=meta))
        current_section_lines.clear()

    for line in lines:
        matched = False
        for marker, field, pattern in level_patterns:
            m = pattern.match(line)
            if m:
                flush()
                title = m.group(1).strip()
                # 更新标题层级：清除比当前级别深的标题
                found = False
                for m2, f2 in headers_to_split_on:
                    if m2 == marker:
                        found = True
                    if found:
                        active_headers.pop(f2, None)
                active_headers[field] = title

                if not strip_headers:
                    current_section_lines.append(line)
                matched = True
                break
        if not matched:
            current_section_lines.append(line)

    flush()
    return chunks if chunks else [Document(page_content=text)]


def split_by_sentence(text, language="中文", delimiters=None):
    """策略4: 按句切分"""
    from utils import Document

    if delimiters is None:
        if language == "中文":
            delimiters = ["。", "！", "？"]
        elif language == "English":
            delimiters = [".", "!", "?"]
        else:  # 自定义
            delimiters = list("。！？")

    try:
        import nltk
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            nltk.download("punkt", quiet=True)
        if language == "中文":
            sentences = nltk.sent_tokenize(text, language="chinese")
        elif language == "English":
            sentences = nltk.sent_tokenize(text, language="english")
        else:
            raise ImportError("skip")
    except (ImportError, Exception, LookupError):
        # 捕获组保留 delimiter，避免 re.split 吃掉真实标点后硬粘第一个
        delim_re = "([" + "".join(re.escape(d) for d in delimiters) + "])"
        tokens = re.split(delim_re, text)
        sentences = []
        for i in range(0, len(tokens), 2):
            content = tokens[i].strip()
            delim_sym = tokens[i + 1] if i + 1 < len(tokens) else ""
            if content:
                sentences.append(content + (delim_sym or ""))

    docs = []
    for s in sentences:
        if s.strip():
            docs.append(Document(page_content=s.strip()))
    return docs


def split_semantic(text, embeddings=None, breakpoint_type="percentile"):
    """策略5: 语义切分（余弦断点）"""
    from utils import Document
    import numpy as np

    # 分句
    sentences = re.split(r'(?<=[。！？.!?])\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [Document(page_content=text)]

    # 如果是中文，用中文标点作为主要分句依据
    has_cjk = any('\u4e00' <= c <= '\u9fff' for c in text[:100])
    if has_cjk:
        # 中文分句：先用 。！？ 切，再用 .!? 补充
        delim = r'(?<=[。！？])\s*'
        sentences = [s.strip() for s in re.split(delim, text) if s.strip()]
    else:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

    if len(sentences) < 2:
        return [Document(page_content=text)]

    # 获取句子嵌入
    if embeddings is not None:
        try:
            emb_vectors = embeddings.embed_documents(sentences)
        except Exception:
            emb_vectors = [embeddings.embed_query(s) for s in sentences]
    else:
        # 无嵌入模型时回退到 recursive
        return split_recursive(text)

    emb_array = np.array(emb_vectors)
    norms = np.linalg.norm(emb_array, axis=1, keepdims=True)
    norms[norms == 0] = 1
    emb_array = emb_array / norms

    # 计算相邻余弦相似度
    sims = np.sum(emb_array[:-1] * emb_array[1:], axis=1)
    distances = 1 - sims  # 距离越大越可能是断点

    # 断点检测
    if breakpoint_type == "percentile":
        threshold = np.percentile(distances, 95)
    elif breakpoint_type == "stddev":
        threshold = float(np.mean(distances) + np.std(distances))
    elif breakpoint_type == "gradient":
        grads = np.abs(np.diff(distances))
        threshold = np.percentile(grads, 90)
        # 用梯度峰值作为断点
        break_indices = []
        for i, g in enumerate(grads):
            if g >= threshold and distances[i] > np.median(distances):
                break_indices.append(i + 1)
        # 按断点切分
        chunks = []
        start = 0
        for bi in break_indices:
            if bi > start:
                chunk_text = "".join(sentences[start:bi])
                chunks.append(Document(page_content=chunk_text))
                start = bi
        if start < len(sentences):
            chunks.append(Document(page_content="".join(sentences[start:])))
        return chunks if chunks else [Document(page_content=text)]
    else:
        threshold = np.percentile(distances, 95)

    # 按阈值切分
    chunks = []
    current = []
    for i, sent in enumerate(sentences):
        current.append(sent)
        if i < len(distances) and distances[i] >= threshold:
            # 遇到断点：合并当前块
            chunk_text = "".join(current).strip()
            if chunk_text:
                chunks.append(Document(page_content=chunk_text))
            current = []
    if current:
        chunk_text = "".join(current).strip()
        if chunk_text:
            chunks.append(Document(page_content=chunk_text))

    return chunks if chunks else [Document(page_content=text)]


# ==================== 后处理（子切分）====================

def _run_secondary(chunks: list, secondary_strategy: str,
                  chunk_size: int, chunk_overlap: int,
                  embeddings=None) -> list:
    """
    对 chunks 执行二次切分，metadata 白名单继承。
    只有 chunks 内容长度超过 chunk_size 的才子切。
    """
    from utils import Document

    if not secondary_strategy or secondary_strategy == "none":
        return chunks

    result = []
    for doc in chunks:
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        if len(content) <= chunk_size:
            result.append(doc)
            continue

        parent_meta = filter_inheritable_meta(doc.metadata if hasattr(doc, "metadata") else {})

        if secondary_strategy == "recursive":
            sub_chunks = split_recursive(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        elif secondary_strategy == "fixed":
            sub_chunks = split_fixed_size(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        elif secondary_strategy == "semantic":
            sub_chunks = split_semantic(content, embeddings=embeddings)
        else:
            result.append(doc)
            continue

        for sub in sub_chunks:
            if hasattr(sub, "metadata") and parent_meta:
                sub.metadata.update(parent_meta)
            elif isinstance(sub, str):
                sub = Document(page_content=sub, metadata=parent_meta)
            result.append(sub)

    return result


# ==================== 三层 Pipeline ====================

PRIMARY_MAP = {
    "fixed": split_fixed_size,
    "recursive": split_recursive,
    "headers": split_by_headers,
    "sentence": split_by_sentence,
    "semantic": split_semantic,
}

# 哪些主策略的 metadata 值得传给子切
META_INHERIT_STRATEGIES = {"headers", "semantic"}


def split_pipeline(text, guards=None, primary="recursive", secondary=None,
                   chunk_size=500, chunk_overlap=50, embeddings=None, **kwargs):
    """
    三层切分流水线：守卫栈 → 主切分 → 后处理(子切)

    参数:
        text: 输入文本
        guards: 守卫名称列表，如 ["mermaid", "code", "table"]
        primary: 主策略名，支持 fixed/recursive/headers/sentence/semantic
        secondary: 后处理策略，支持 recursive/fixed/semantic/None
        chunk_size: 块大小
        chunk_overlap: 块重叠
        embeddings: 嵌入模型实例（供语义切分使用，不传则 fallback bge-small-zh-v1.5）
        **kwargs: 传递给主策略的额外参数（headers_to_split_on, strip_headers, separators, etc.）
    """
    from utils import Document

    # 1. 守卫栈（预处理）
    guard_stack = GuardStack(guards or [])
    protected_text = guard_stack.apply(text)

    # 2. 主切分（通过注册表执行）
    plugin = STRATEGY_REGISTRY.get(primary)
    if plugin is None:
        raise ValueError(f"未知切分策略: {primary}，可选: {', '.join(STRATEGY_REGISTRY.keys())}")

    # 策略级覆盖 chunk_size
    strategy_overrides = kwargs.get("strategy_overrides", {})
    if primary in strategy_overrides:
        over = strategy_overrides[primary]
        actual_chunk_size = over.get("chunk_size") if over.get("chunk_size") is not None else chunk_size
        actual_chunk_overlap = over.get("chunk_overlap") if over.get("chunk_overlap") is not None else chunk_overlap
    else:
        actual_chunk_size = chunk_size
        actual_chunk_overlap = chunk_overlap

    # 从 kwargs 中提取策略配置字段
    schema_keys = set(plugin.config_schema.keys())
    strategy_kwargs = {k: v for k, v in kwargs.items() if k in schema_keys}

    # 如果没传，用 default_config
    for k, v in plugin.default_config.items():
        if k not in strategy_kwargs:
            strategy_kwargs[k] = v

    # 覆盖 chunk_size
    if primary in ("fixed", "recursive"):
        strategy_kwargs["chunk_size"] = actual_chunk_size
        strategy_kwargs["chunk_overlap"] = actual_chunk_overlap

    # 注入嵌入模型（语义切分专用，外部传入优先）
    if embeddings is not None and primary == "semantic":
        strategy_kwargs["embeddings"] = embeddings

    chunks = plugin.execute(protected_text, strategy_kwargs)

    # 3. 守卫还原
    chunks = guard_stack.restore_chunks(chunks)

    # 4. 后处理（子切）
    if secondary and secondary != primary:
        # 只有 headers/semantic 主策略需要 metadata 继承
        if primary in META_INHERIT_STRATEGIES:
            chunks = _run_secondary(chunks, secondary, chunk_size, chunk_overlap, embeddings=embeddings)
        else:
            # 固定/递归/按句：纯子切，不继承位置 metadata
            chunks = _run_secondary_without_inherit(chunks, secondary, chunk_size, chunk_overlap, embeddings=embeddings)

    return chunks


def _run_secondary_without_inherit(chunks, secondary_strategy, chunk_size, chunk_overlap, embeddings=None):
    """后处理但不继承 metadata（用于 fixed/recursive/sentence 主策略）"""
    if not secondary_strategy or secondary_strategy == "none":
        return chunks

    result = []
    for doc in chunks:
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        if len(content) <= chunk_size:
            result.append(doc)
            continue

        if secondary_strategy == "recursive":
            sub_chunks = split_recursive(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        elif secondary_strategy == "fixed":
            sub_chunks = split_fixed_size(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        elif secondary_strategy == "semantic":
            sub_chunks = split_semantic(content, embeddings=embeddings)
        else:
            result.append(doc)
            continue

        for sub in sub_chunks:
            if hasattr(sub, "metadata") and "source" in (doc.metadata or {}):
                sub.metadata["source"] = doc.metadata["source"]
            result.append(sub)
    return result


# ==================== 向后兼容 ====================

def combo_split(text, primary_strategy="recursive", secondary_strategy=None,
                chunk_size=500, chunk_overlap=50, **kwargs):
    """
    向后兼容的 combo_split
    内部调用 split_pipeline
    """
    # 从 kwargs 识别守卫
    guards = kwargs.pop("guards", None)

    # 旧版 mermaid 策略 → 转为 guards=["mermaid"] + primary="headers"
    if primary_strategy == "mermaid":
        primary_strategy = "headers"
        if guards is None:
            guards = ["mermaid"]
        elif "mermaid" not in guards:
            guards = list(guards) + ["mermaid"]

    return split_pipeline(
        text,
        guards=guards,
        primary=primary_strategy,
        secondary=secondary_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )


def split_with_mermaid_preserve(text, headers_to_split_on=None, strip_headers=False):
    """旧版 mermaid 保护切分（保留向后兼容，内部走 pipeline）"""
    return split_pipeline(
        text,
        guards=["mermaid"],
        primary="headers",
        headers_to_split_on=headers_to_split_on or [("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=strip_headers,
    )


# ==================== 注册内置策略和守卫 ====================

register_strategy(StrategyPlugin(
    "fixed", "固定窗口切分", split_fixed_size,
    config_schema={
        "chunk_size": {"type": "int", "label": "块大小", "default": 500, "min": 50, "max": 5000},
        "chunk_overlap": {"type": "int", "label": "重叠", "default": 50, "min": 0, "max": 1000},
    },
    default_config={"chunk_size": 500, "chunk_overlap": 50},
))

register_strategy(StrategyPlugin(
    "recursive", "递归切分", split_recursive,
    config_schema={
        "chunk_size": {"type": "int", "label": "块大小", "default": 500, "min": 50, "max": 5000},
        "chunk_overlap": {"type": "int", "label": "重叠", "default": 50, "min": 0, "max": 1000},
        "separators": {"type": "text", "label": "分隔符（逗号分隔）", "default": "\\n\\n,\\n,。,；，, ,"},
    },
    default_config={"chunk_size": 500, "chunk_overlap": 50, "separators": ["\n\n", "\n", "。", "；", "，", " ", ""]},
))

register_strategy(StrategyPlugin(
    "headers", "层级/标题切分", split_by_headers,
    config_schema={
        "headers_to_split_on": {"type": "multi-select", "label": "标题级别",
                                 "options": ["#", "##", "###", "####"],
                                 "default": ["#", "##", "###"]},
        "strip_headers": {"type": "bool", "label": "去除标题", "default": False},
    },
    default_config={"headers_to_split_on": [("#", "h1"), ("##", "h2"), ("###", "h3")], "strip_headers": False},
))

register_strategy(StrategyPlugin(
    "sentence", "按句切分", split_by_sentence,
    config_schema={
        "language": {"type": "select", "label": "语言", "options": ["中文", "English", "自定义"],
                      "default": "中文"},
        "delimiters": {"type": "text", "label": "自定义边界符（直接输入字符）", "default": "。！？"},
    },
    default_config={"language": "中文", "delimiters": "。！？"},
))

register_strategy(StrategyPlugin(
    "semantic", "语义切分", split_semantic,
    config_schema={
        "breakpoint_type": {"type": "select", "label": "断点算法",
                             "options": ["percentile", "gradient", "stddev"],
                             "default": "percentile"},
    },
    default_config={"breakpoint_type": "percentile"},
))

# 注册守卫
for g in [GUARD_MERMAID, GUARD_CODE, GUARD_MATH, GUARD_TABLE, GUARD_HTML]:
    descs = {"mermaid": "保护 ```mermaid 流程图", "code": "保护围栏代码块",
             "math": "保护 LaTeX 公式 $$...$$", "table": "保护 Markdown 表格",
             "html": "保护 HTML 块级标签"}
    register_guard(GuardPlugin(g.name, descs.get(g.name, ""), g))

# 后处理策略（与主策略共享注册表，但标记 role=secondary）
SECONDARY_STRATEGIES = {"recursive": split_recursive, "fixed": split_fixed_size, "semantic": split_semantic}

PRIMARY_MAP = {name: p.fn for name, p in STRATEGY_REGISTRY.items()}
ALL_GUARDS = {name: gp.guard for name, gp in GUARD_REGISTRY.items()}


# ==================== CLI 入口 ====================

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


# ==================== CLI 入口 ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="文本切分工具（三层流水线：守卫栈 → 主策略 → 后处理）")
    parser.add_argument("--input", type=str, required=True, help="输入文件路径 (txt/md)")
    parser.add_argument("--strategy", type=str, default="recursive",
                        choices=["fixed", "recursive", "headers", "sentence", "semantic"],
                        help="主策略")
    parser.add_argument("--guard", type=str, default="",
                        help="守卫栈（多选，逗号分隔）: mermaid,code,math,table,html")
    parser.add_argument("--secondary", type=str, choices=["recursive", "fixed", "semantic", "none"],
                        help="后处理子切策略")
    parser.add_argument("--chunk-size", type=int, default=500, help="块大小")
    parser.add_argument("--overlap", type=int, default=50, help="重叠字符数")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--list-strategies", action="store_true", help="列出可用策略和守卫")

    args = parser.parse_args()

    if args.list_strategies:
        strategies = [
            ("fixed", "固定窗口切分", "按固定字符数切分，可设重叠"),
            ("recursive", "递归切分", "按优先级尝试不同分隔符，性价比最高"),
            ("headers", "层级/标题切分", "基于 Markdown 标题切分，保留结构元数据"),
            ("sentence", "按句切分", "以句子为单位，适合证据抽取"),
            ("semantic", "语义切分", "计算相邻句子相似度，精度最高但成本高"),
        ]
        print("可用主策略:")
        print("-" * 60)
        for name, title, desc in strategies:
            print(f"  {name:<15} {title:<20} {desc}")

        print("\n可用守卫（多选，--guard mermaid,code,math,table,html）:")
        print("-" * 60)
        guards_info = [
            ("mermaid", "保护 ```mermaid 流程图不被切碎"),
            ("code", "保护所有围栏代码块 (```lang ... ```)"),
            ("math", "保护 LaTeX 数学公式 ($$...$$)"),
            ("table", "保护 Markdown 表格不被跨行切断"),
            ("html", "保护 HTML 块级标签 (div/table/pre 等)"),
        ]
        for name, desc in guards_info:
            print(f"  {name:<15} {desc}")

        print("\n可用后处理（--secondary）:")
        print("-" * 60)
        post_info = [
            ("recursive", "递归子切（带 metadata 继承）"),
            ("fixed", "固定窗口子切（带 metadata 继承）"),
            ("semantic", "语义子切（带 metadata 继承）"),
            ("none", "不进行子切"),
        ]
        for name, desc in post_info:
            print(f"  {name:<15} {desc}")
        print("\n注意：headers/semantic 主策略的子切会继承 h1/h2/h3/source 元数据")
        sys.exit(0)

    if not os.path.exists(args.input):
        print(f"[!] 输入文件不存在: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    guard_list = [g.strip() for g in args.guard.split(",") if g.strip()] if args.guard else []
    secondary = args.secondary if args.secondary and args.secondary != "none" else None

    print(f"输入文件: {args.input} ({len(text)} 字符)")
    print(f"守卫: {guard_list or '无'}")
    print(f"主策略: {args.strategy}", end="")
    if secondary:
        print(f" → 后处理: {secondary}")
    else:
        print()

    chunks = split_pipeline(
        text,
        guards=guard_list,
        primary=args.strategy,
        secondary=secondary,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
    )

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
