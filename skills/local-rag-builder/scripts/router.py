"""
local-rag-builder 路由层模块
v0.2.0

路由架构（直接基于 knowledge_base_manager 的多知识库能力）：

① hardcoded(关键词规则) — 直接用 KB 管理的 auto_classify 查规则
  → 命中 → 直接路由到该 KB
② fallback(语义模型) — query × KB 签名 → 选最佳 KB
  → 命中 → 路由到最佳 KB
③ broadcast — 全量广播所有 KB
  → 兜底

入库和查询共享同一个 FallbackRouter。
"""

import os
import re
import json
from typing import Optional

from config import load_config
from utils import KB_DIR, safe_json_load, safe_json_dump

KB_SIGNATURE_FILE = os.path.join(KB_DIR, "kb_signatures.json")
_shared_router = None  # 模块级缓存，避免重复加载 reranker 模型


def _load_signatures():
    return safe_json_load(KB_SIGNATURE_FILE, {})


def _save_signatures(sigs):
    safe_json_dump(sigs, KB_SIGNATURE_FILE)


# ==================== 硬编码路由 ====================

def hardcoded_route(question: str) -> Optional[str]:
    """
    硬编码路由：直接用 knowledge_base_manager.auto_classify()。
    返回命中的 KB 名称，不命中返回 None。

    注意：auto_classify() 在无规则匹配时返回 "default"，
    这里额外验证是否真的有关键词命中。
    """
    from knowledge_base_manager import _load_rules
    rules = _load_rules()
    if not rules:
        return None

    # 快速检查是否有任何关键词命中
    question_lower = question.lower()
    any_hit = False
    for rule in rules.values():
        for kw in rule.get("keywords", []):
            if kw.lower() in question_lower:
                any_hit = True
                break
        if any_hit:
            break

    if not any_hit:
        return None

    from knowledge_base_manager import auto_classify
    return auto_classify(question, rules)


# ==================== 回退语义路由 ====================

class FallbackRouter:
    """回退语义路由：用 rerank 模型对 query 和 KB 签名打分"""

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        if self._model is not None:
            return

        if not self.model_path:
            cfg = load_config()
            router_cfg = cfg.get("router", {})
            fallback_cfg = router_cfg.get("fallback", {})
            self.model_path = fallback_cfg.get("model_path", "")

        if not self.model_path or not os.path.exists(self.model_path):
            from utils import MODELS_DIR, find_model_dirs
            models = find_model_dirs(MODELS_DIR)
            if not models:
                raise ValueError("未找到 rerank/routing 模型")
            self.model_path = models[0]["path"]

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, local_files_only=True
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_path, local_files_only=True
            ).to(device).eval()
        except Exception as e:
            raise RuntimeError(f"加载路由模型失败: {e}")

    def score(self, query: str, kb_signatures: dict[str, str]) -> dict[str, float]:
        if not kb_signatures:
            return {}
        self._load_model()

        import torch
        pairs = [[query, sig["signature"] if isinstance(sig, dict) else sig] for sig in kb_signatures.values()]
        inputs = self._tokenizer(
            pairs, padding=True, truncation=True,
            max_length=512, return_tensors="pt"
        ).to(self._model.device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            scores = outputs.logits.squeeze(-1).tolist()

        if isinstance(scores, float):
            scores = [scores]

        kb_names = list(kb_signatures.keys())
        result = {}
        for i, name in enumerate(kb_names):
            result[name] = round(scores[i] if i < len(scores) else 0.0, 4)
        return result

    def route(self, query: str, signatures: dict[str, str],
              threshold: float = None) -> tuple[Optional[str], dict[str, float]]:
        cfg = load_config()
        router_cfg = cfg.get("router", {})
        fallback_cfg = router_cfg.get("fallback", {})
        if threshold is None:
            threshold = fallback_cfg.get("min_score_threshold", 0.3)

        scores = self.score(query, signatures)
        if not scores:
            return None, scores

        best_kb = max(scores, key=scores.get)
        best_score = scores[best_kb]

        if best_score < threshold:
            return None, scores
        return best_kb, scores


# ==================== 全量广播 ====================

def broadcast_route(question: str, kb_names: list[str]) -> list[str]:
    """全量广播：返回所有存在数据的 KB 列表"""
    valid_kbs = []
    for name in kb_names:
        kb_path = os.path.join(KB_DIR, name)
        if os.path.exists(kb_path) and os.listdir(kb_path):
            valid_kbs.append(name)
    return valid_kbs


# ==================== 主路由入口 ====================

def route_query(question: str) -> dict:
    """
    两步路由（依路由层开关选择模式）：

    路由层开启 → 加权语义（reranker × 规则关键词打分）
    路由层关闭 → 直接关键词匹配

    都没命中 → default KB，不碰 KB 签名（签名可能被污染）
    """
    from knowledge_base_manager import list_knowledge_bases, _load_rules
    cfg = load_config()
    router_cfg = cfg.get("router", {})
    rules = _load_rules()

    if router_cfg.get("enabled", True):
        # ===== 路由层开启：加权语义 =====
        # reranker 对 query × 每条规则的关键词做语义打分 → 选最高分 KB
        classify_threshold = router_cfg.get("classify_threshold", 0.3)
        try:
            fallback = FallbackRouter()
            best_kb, best_score = None, classify_threshold
            if rules:
                for kb_name, rule_obj in rules.items():
                    keywords = rule_obj.get("keywords", [])
                    if not keywords:
                        continue
                    kw_text = " ".join(keywords)
                    scores = fallback.score(question, {kb_name: kw_text})
                    score = scores.get(kb_name, 0.0)
                    if score > best_score:
                        best_score = score
                        best_kb = kb_name
            if best_kb:
                return {"kb_names": [best_kb], "method": "semantic_keyword", "kb_scores": {best_kb: best_score}}
        except (ValueError, RuntimeError):
            pass
    else:
        # ===== 路由层关闭：直接关键词匹配 =====
        hc_result = hardcoded_route(question)
        if hc_result:
            return {"kb_names": [hc_result], "method": "hardcoded", "kb_scores": None}

    # 都没命中 → default
    return {"kb_names": ["default"], "method": "default", "kb_scores": None}


# ==================== KB 签名自动归纳 ====================

def _build_signature_from_texts(texts: list[str], max_chars: int = 500, kb_name: str = "") -> str:
    """
    从文本列表提取签名：用 reranker 语义理解替代硬编码词频统计。
    以 KB 名称+关键词为查询，对 chunks 打分，取高语义相关片段做签名。
    """
    if not texts:
        return ""

    # 清洗：去掉 PDF 乱码/Unicode 控制字符
    def _clean(t):
        t = t.replace('\u00a0', ' ').replace('\u200b', '').replace('\ufeff', '')
        t = re.sub(r'uni00a0|uni200b|unifeff|[\x00-\x08\x0b\x0c\x0e-\x1f]', '', t)
        t = re.sub(r'[^\S\n]{3,}', ' ', t)  # 多个空格合并
        return t.strip()

    # 去重、去太短、清洗
    unique = []
    seen = set()
    for t in texts:
        t = _clean(t)
        if len(t) < 30 or t in seen:
            continue
        seen.add(t)
        unique.append(t)
    if not unique:
        return ""

    # 用语义模型找代表片段：以 KB 名为查询，reranker 打分
    try:
        global _shared_router
        if _shared_router is None:
            _shared_router = FallbackRouter()
            _shared_router._load_model()
        router = _shared_router
        import torch
        query = kb_name if kb_name else "知识库内容概述"
        pairs = [[query, t[:512]] for t in unique[:50]]  # 最多评 50 段
        inputs = router._tokenizer(
            pairs, padding=True, truncation=True, max_length=512, return_tensors="pt"
        ).to(router._model.device)
        with torch.no_grad():
            scores = router._model(**inputs).logits.squeeze(-1).tolist()
        if isinstance(scores, float):
            scores = [scores]
        ranked = sorted(zip(unique[:len(scores)], scores), key=lambda x: -x[1])
    except Exception:
        # reranker 加载失败 → 不生成垃圾签名，避免毒化 auto_classify_rules
        return ""

    # 从高分片段中提取高频有意义词（不做词频，用语义比对的片段做摘要）
    top_texts = [t for t, s in ranked[:5] if s > 0.1] or [t for t, _ in ranked[:3]]
    if not top_texts:
        top_texts = unique[:3]

    # 取每个高分片段的开头和末尾（最可能含关键词的部分）
    kw_candidates = []
    for t in top_texts:
        # 取前 100 字
        kw_candidates.append(t[:100])
        # 如果片段较长，取末尾 80 字（可能含结论）
        if len(t) > 300:
            kw_candidates.append(t[-80:])

    # 词频统计（仅从精选片段中提取，排除噪声）
    noise_words = {  # 精简版
        "实施日期", "换页", "第页", "图例", "来源", "单位", "摘要", "关键词",
        "中图分类号", "文献标识码", "文章编号", "收稿日期", "修回日期",
        "基金项目", "作者简介", "通讯作者", "参考文献", "附录", "表格",
    }
    combined = " ".join(kw_candidates)
    tokens = re.findall(r'[\w\u4e00-\u9fff]+', combined.lower())
    stop_words = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "吗",
        "把", "被", "让", "给", "为", "所", "以", "能", "于", "之", "与",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "can",
        "could", "may", "might", "shall", "should", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "等", "第", "其",
    }
    all_stop = stop_words | noise_words
    freq = {}
    for t in tokens:
        if len(t) < 2 or t in all_stop or t.isdigit():
            continue
        if re.match(r'^[\d]+[a-z]+$', t) or re.match(r'^[a-z]+[\d]+$', t):
            continue
        weight = 3 if re.match(r'[\u4e00-\u9fff]', t) else 1
        freq[t] = freq.get(t, 0) + weight
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    top_words = [w for w, _ in sorted_words[:12] if len(w) >= 2]
    signature = " · ".join(top_words) if top_words else ""

    # 摘要：取最高分片段中最佳的一段
    excerpt = ""
    for t, s in ranked[:3]:
        cleaned = t.strip()[:150]
        if len(cleaned) >= 40:
            excerpt = cleaned
            break
    if not excerpt and top_texts:
        excerpt = top_texts[0][:150]

    if signature and excerpt:
        return f"【摘要】{signature} | {excerpt}"[:max_chars]
    elif signature:
        return f"【摘要】{signature}"[:max_chars]
    elif excerpt:
        return excerpt[:max_chars]
    return ""


def induce_kb_signature(kb_name: str, chunks: list = None) -> str:
    """
    自动归纳 KB 签名。
    chunks 为可选（入库时直接传入），否则从 Chroma 读取。
    """
    from knowledge_base_manager import _load_index

    if chunks is None:
        try:
            from langchain_chroma import Chroma
            from rag_core import get_embeddings

            index = _load_index()
            if kb_name not in index:
                return ""
            persist_dir = index[kb_name]["path"]
            if not os.path.exists(persist_dir) or not os.listdir(persist_dir):
                return ""

            embeddings = get_embeddings(kb_name=kb_name)
            vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
            try:
                all_docs = vectorstore.get()
                texts = all_docs.get("documents", [])
            except Exception:
                all_docs = vectorstore.similarity_search("", k=20)
                texts = [d.page_content for d in all_docs]
        except Exception:
            texts = []
    else:
        texts = [c.page_content if hasattr(c, "page_content") else str(c) for c in chunks]

    if not texts:
        return ""
    return _build_signature_from_texts(texts, kb_name=kb_name)


def update_kb_signature(kb_name: str, chunks: list = None):
    """更新指定 KB 的签名（入库时自动调用）"""
    sig = induce_kb_signature(kb_name, chunks)
    if not sig:
        return
    sigs = _load_signatures()
    sigs[kb_name] = {
        "signature": sig,
        "updated_at": str(__import__("datetime").datetime.now()),
        "auto_updated": True,
    }
    _save_signatures(sigs)


def list_kb_signatures() -> dict:
    """返回所有 KB 签名，兼容新版（string）和旧版（dict）格式"""
    raw = _load_signatures()
    result = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[k] = v
        else:
            result[k] = {"signature": str(v), "version": "plain"}
    return result


def rebuild_all_signatures():
    """重建所有 KB 签名，清理已删除 KB 的残留签名"""
    from knowledge_base_manager import list_knowledge_bases
    kbs = list_knowledge_bases()
    # 加载已有签名，先清理不存在 KB 的旧条目
    sigs = _load_signatures()
    stale = [k for k in sigs if k not in kbs]
    for k in stale:
        del sigs[k]
    if stale:
        _save_signatures(sigs)
    # 逐个重建
    for kb_name in kbs:
        try:
            update_kb_signature(kb_name)
        except Exception as e:
            print(f"  [!] 重建签名失败 {kb_name}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="路由层管理工具")
    parser.add_argument("--route", type=str, help="测试路由")
    parser.add_argument("--signatures", action="store_true", help="列出 KB 签名")
    parser.add_argument("--rebuild-signatures", action="store_true", dest="rebuild", help="重建所有 KB 签名")
    parser.add_argument("--update-signature", type=str, dest="update_sig", help="更新指定 KB 签名")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    if args.signatures:
        sigs = list_kb_signatures()
        if args.json:
            print(json.dumps(sigs, ensure_ascii=False, indent=2))
        else:
            print(f"KB 签名 ({len(sigs)}):")
            for name, info in sigs.items():
                print(f"  {name}: {info.get('signature', '')[:80]}...")

    elif args.rebuild:
        rebuild_all_signatures()
        print("[OK] 所有 KB 签名已重建")

    elif args.update_sig:
        update_kb_signature(args.update_sig)
        sigs = list_kb_signatures()
        info = sigs.get(args.update_sig, {})
        print(f"[OK] 签名已更新: {info.get('signature', '')[:100]}...")

    elif args.route:
        result = route_query(args.route)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"路由结果:")
            print(f"  方法: {result['method']}")
            print(f"  目标 KB: {result['kb_names']}")
            if result.get("kb_scores"):
                print(f"  得分: {result['kb_scores']}")
    else:
        parser.print_help()
