"""引用后处理 — 确定性替换正文引用 + 构建参考文献节

管线：
Python 扫描正文真实引用 → 按首次出现顺序重编号（未用来源不参与、不存在的来源标记删除）
  → LLM 收到 desc + 元信息列表 → 输出格式化文本
  → Python 直接替换参考文献节内容（无真实引用则整节删除）

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

    # 1. 扫描正文真实引用 → 按首次出现顺序去重 → 构建旧→新编号映射
    #    （同一来源多处引用全局映射到同一新编号；全集未用到的来源不参与编号）
    _all_keys = list(all_rag_headers.keys())

    # 1a. 归一化连续列举："引用自来源1、来源2、来源4" → 每个来源补上引用标记
    def _norm_cont(_m):
        return re.sub(r'([、,，])\s*来源\s*(\d+)', r'\1引用自来源\2', _m.group(0))
    article_md = re.sub(r'(?:引用自|引自)\s*来源\s*\d+(?:[、,，]\s*来源\s*\d+)+', _norm_cont, article_md)

    _cite_pat = re.compile(r'(?:引用自|引自)\s*来源\s*(\d+)')
    _cited_old = []
    for _m in _cite_pat.finditer(article_md):
        _n = int(_m.group(1))
        if 1 <= _n <= len(_all_keys) and _n not in _cited_old:
            _cited_old.append(_n)
    _map = {_old: _i for _i, _old in enumerate(_cited_old, 1)}

    # 2. 正文替换：真实引用 → 新编号格式；不存在的来源 → 引用标记直接删除
    def _repl_cite(_m):
        _n = int(_m.group(1))
        _new = _map.get(_n)
        if _new is None:
            return ""  # 不存在的来源，标记直接删除
        if "x" in _inline_template:
            return _inline_template.replace("x", str(_new))
        return _inline_template + str(_new)

    article_md = _cite_pat.sub(_repl_cite, article_md)

    # 3. 构建参考文献节：只用真实引用的来源，按新编号顺序（悬空条目消失）
    _ref_lines = []
    for _i, _old in enumerate(_cited_old, 1):
        _meta = " / ".join(t.strip() for t in all_rag_headers[_all_keys[_old - 1]][:3] if t.strip())
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

    # 5. Python 直接替换参考文献节内容；无任何真实引用时整节删除
    _search = f"## {_cite_name}"
    _ref_start = article_md.find(_search)
    if _ref_start >= 0:
        _ref_end = article_md.find("\n## ", _ref_start + 2)
        if _ref_end < 0:
            _ref_end = len(article_md)
        if _ref_lines:
            article_md = article_md[:_ref_start] + f"## {_cite_name}\n" + _ref_new + article_md[_ref_end:]
        else:
            article_md = article_md[:_ref_start] + article_md[_ref_end:]

    return article_md
