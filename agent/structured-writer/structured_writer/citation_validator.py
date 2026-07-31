"""引用后处理 — 确定性替换正文引用 + 构建参考文献节

管线：
Python 建带编号的元信息
  → LLM 收到 desc + 元信息列表 → 输出格式化文本
  → Python 直接替换参考文献节内容

引用格式由模板 `citation_format` 声明（如 "[x]=1." = 正文 [N] + 条目 N.）。
引用检查（validate）已于 1.1.0b14 移除——引用在生成时由后处理确定性完成，
检查属过渡期补救，无调用点，为死代码。
"""

import re
from typing import Optional


def post_process(article_md: str, citation_config: dict,
                 all_rag_headers: dict, llm_client=None) -> str:
    """引用后处理：提取引用→编号→替换正文→LLM格式化参考文献节

    管线：
    Python 建带编号的元信息
      → LLM 收到 desc + 元信息列表 → 输出格式化文本
      → Python 直接替换参考文献节内容

    参数:
        article_md: 完整文章 markdown
        citation_config: {节名: {enabled, format, desc}}
        all_rag_headers: RAG 累积的文档元数据
        llm_client: LLM 客户端（用于格式化参考文献）

    返回:
        处理后的 article_md
    """
    if not citation_config or not all_rag_headers:
        return article_md

    # 从模板 citation_config 解析
    _cite_fmt = "[x]=1."
    _cite_desc = ""
    _cite_name = ""
    for _cc_name, _cc_val in citation_config.items():
        if _cc_val.get("enabled"):
            _cite_fmt = _cc_val.get("format", "[x]=1.")
            _cite_desc = _cc_val.get("desc", "")
            _cite_name = _cc_name
            break
    _eq = _cite_fmt.find("=")
    _inline_template = _cite_fmt[:_eq].strip() if _eq >= 0 else "[x]"
    _ref_prefix = _cite_fmt[_eq + 1:].strip() if _eq >= 0 else "1."

    # 1. 替换正文：引用自来源N → 用户配置的行内格式（默认 [N]）
    _all_keys = list(all_rag_headers.keys())
    for _i in range(1, len(_all_keys) + 1):
        if "x" in _inline_template:
            _repl = _inline_template.replace("x", str(_i))
        else:
            _repl = _inline_template + str(_i)
        article_md = article_md.replace(f"引用自来源{_i}", _repl)
        article_md = article_md.replace(f"引用自来源 {_i}", _repl)
        article_md = article_md.replace(f"引自来源{_i}", _repl)
        article_md = article_md.replace(f"引自来源 {_i}", _repl)
    article_md = re.sub(r'[\u4e00-\u9fff]{2,}[\s：:]*\[(\d+)\]', r'[\1]', article_md)

    # 2. 构建参考文献节：user 配置前缀 + 元信息 + LLM 格式化
    _ref_lines = []
    for _i, _src in enumerate(_all_keys, 1):
        _meta = " / ".join(t.strip() for t in all_rag_headers[_src][:3] if t.strip())
        if "x" in _ref_prefix or "1" in _ref_prefix:
            _prefix = _ref_prefix.replace("1", str(_i))
        else:
            _prefix = f"{_i}. "  # fallback
        _ref_lines.append(f"{_prefix} {_meta}")
    _ref_new = "\n".join(_ref_lines)

    # 3. 调 LLM 格式化参考文献
    if llm_client and _cite_desc and _ref_lines:
        try:
            _prompt = f"{_cite_desc}\n\n以下是引用元信息，请按上述格式规范化为参考文献条目，保持编号不变：\n\n" + "\n".join(_ref_lines)
            _result = llm_client.chat(
                [{"role": "user", "content": _prompt}],
                max_tokens=None, temperature=0.3
            )
            if _result and _result.strip():
                _clean = _result.strip()
                if "## " in _clean:
                    _clean = _clean.split("## ", 1)[-1]
                    _clean = _clean.split("\n", 1)[-1] if "\n" in _clean else _clean
                _clean_lines = [l for l in _clean.split("\n") if l.strip()]
                if _clean_lines:
                    _ref_new = "\n".join(_clean_lines)
        except Exception:
            pass

    # 4. Python 直接替换参考文献节内容
    _search = f"## {_cite_name}"
    _ref_start = article_md.find(_search)
    if _ref_start >= 0:
        _ref_end = article_md.find("\n## ", _ref_start + 2)
        if _ref_end < 0:
            _ref_end = len(article_md)
        article_md = article_md[:_ref_start] + f"## {_cite_name}\n" + _ref_new + article_md[_ref_end:]

    return article_md
