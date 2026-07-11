"""
rag-assistant 路由层模块
v0.2.0
"""
import os, re, json
from typing import Optional
from config import load_config
from utils import KB_DIR, safe_json_load, safe_json_dump

KB_SIGNATURE_FILE = os.path.join(KB_DIR, "kb_signatures.json")

def _load_signatures():
    return safe_json_load(KB_SIGNATURE_FILE, {})

def _save_signatures(sigs):
    safe_json_dump(sigs, KB_SIGNATURE_FILE)

# ==================== 硬编码路由 ====================

def hardcoded_route(question: str) -> Optional[str]:
    from knowledge_base_manager import _load_rules
    rules = _load_rules()
    if not rules:
        return None
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

# ==================== 主路由入口 ====================

def broadcast_route(question: str, kb_names: list[str]) -> list[str]:
    valid_kbs = []
    for name in kb_names:
        kb_path = os.path.join(KB_DIR, name)
        if os.path.exists(kb_path) and os.listdir(kb_path):
            valid_kbs.append(name)
    return valid_kbs

# ==================== 主路由入口 ====================

def route_query(question: str) -> dict:
    from knowledge_base_manager import list_knowledge_bases
    cfg = load_config()
    router_cfg = cfg.get("router", {})
    if router_cfg.get("enabled", True):
        from rag_core import get_embeddings
        import numpy as np
        classify_threshold = router_cfg.get("classify_threshold", 0.3)
        try:
            emb = get_embeddings()
            qv = np.array(emb.embed_query(question))
            # 有签名 → 嵌入 × 签名
            sigs = list_kb_signatures()
            if sigs:
                best_kb, best_score = None, classify_threshold
                for kb_name, sig_info in sigs.items():
                    if not isinstance(sig_info, dict):
                        continue
                    if sig_info.get("method") not in ("reranker", "word_freq"):
                        continue
                    sig_text = sig_info.get("signature", "")
                    if not sig_text:
                        continue
                    sv = np.array(emb.embed_query(sig_text.replace(" · ", " ")[:200]))
                    sim = float(np.dot(qv, sv) / (np.linalg.norm(qv) * np.linalg.norm(sv)))
                    if sim > best_score:
                        best_score = sim
                        best_kb = kb_name
                if best_kb:
                    return {"kb_names": [best_kb], "method": "embedding_signature", "kb_scores": {best_kb: best_score}}
            # 无签名或签名不匹配 → 嵌入 × 关键词
            from knowledge_base_manager import _load_rules
            rules = _load_rules()
            if rules:
                best_kb, best_score = None, classify_threshold
                for kb_name, rule_obj in rules.items():
                    kws = rule_obj.get("keywords", [])
                    if not kws:
                        continue
                    kv = np.array(emb.embed_query(" ".join(kws)))
                    sim = float(np.dot(qv, kv) / (np.linalg.norm(qv) * np.linalg.norm(kv)))
                    if sim > best_score:
                        best_score = sim
                        best_kb = kb_name
                if best_kb:
                    return {"kb_names": [best_kb], "method": "embedding_keyword", "kb_scores": {best_kb: best_score}}
        except Exception:
            pass
    else:
        hc_result = hardcoded_route(question)
        if hc_result:
            return {"kb_names": [hc_result], "method": "hardcoded", "kb_scores": None}
    return {"kb_names": ["default"], "method": "default", "kb_scores": None}

# ==================== KB 签名自动归纳 ====================

SIGNATURE_MAX_WORDS = 12
FEEDBACK_MAX_WORDS = 30

def _clean_text(t: str) -> str:
    t = t.replace('\u00a0', ' ').replace('\u200b', '').replace('\ufeff', '')
    t = re.sub(r'uni00a0|uni200b|unifeff|[\x00-\x08\x0b\x0c\x0e-\x1f]', '', t)
    t = re.sub(r'[^\S\n]{3,}', ' ', t)
    return t.strip()

def _tokenize(text: str) -> list[str]:
    """jieba 中文 + 正则英文，返回候选词列表"""
    tokens = []
    try:
        import jieba
        for seg in re.split(r'([\u4e00-\u9fff]+)', text):
            if re.match(r'[\u4e00-\u9fff]+', seg):
                tokens.extend(jieba.lcut(seg.lower()))
            else:
                tokens.extend(re.findall(r'[a-zA-Z]{4,}', seg.lower()))
    except ImportError:
        tokens = re.findall(r'[\u4e00-\u9fff]{2,8}|[a-zA-Z]{4,}', text.lower())
    return tokens

_STOP_WORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "吗",
    "把", "被", "让", "给", "为", "所", "以", "能", "于", "之", "与",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "can",
    "could", "may", "might", "shall", "should", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "等", "第", "其",
    "and", "but", "or", "nor", "not", "no", "so", "if", "then", "else",
    "he", "she", "it", "its", "they", "them", "their", "this", "that",
    "these", "those", "which", "who", "whom", "what", "where", "when",
    "why", "how", "all", "each", "every", "both", "few", "many", "some",
    "any", "more", "most", "other", "such", "into", "than", "also",
    "very", "just", "about", "over", "there", "here", "then", "his",
    "her", "our", "your", "upon", "within", "without", "through",
    "进行", "包括", "方面", "随着", "通过", "以及", "其中", "因此", "此外",
    "同时", "基于", "之间", "之后", "之前", "以上", "以下", "主要", "不同",
    "一般", "一定", "一种", "一些", "可以", "需要", "必须", "可能",
    "应该", "能够", "利用", "采用", "具有", "属于", "作为", "用于",
    "涉及", "相关", "分别", "按照", "根据", "由于", "经过", "结合",
    "其中", "方面", "领域", "行业", "类型", "状态", "说明", "使用", "系统",
    "研究", "分析", "提出", "建立", "实现", "方法",
    "要求", "条件", "内容", "部分", "方式", "过程", "结果", "作用", "影响",
    "变化", "情况", "问题", "关系", "结构", "功能", "特点", "特征", "性质",
    "水平", "试验", "检测", "测试", "测量", "检验", "标准", "规则", "规程",
    "参加", "频次", "时间", "技术", "开发",
    "一方面", "另一方面", "此外", "同时", "目前", "当前",
    "实施日期", "换页", "第页", "图例", "来源", "单位", "摘要", "关键词",
    "中图分类号", "文献标识码", "文章编号", "收稿日期", "修回日期",
    "基金项目", "作者简介", "通讯作者", "参考文献", "附录", "表格",
    "page", "abstract", "introduction", "conclusion", "reference",
    "figure", "table", "fig", "eq", "et", "al",
}

def _filter_candidates(tokens: list[str]) -> dict[str, int]:
    """停用词过滤 + 权重统计，返回 {词: 权重}"""
    freq = {}
    for t in tokens:
        if t in _STOP_WORDS or t.isdigit():
            continue
        is_cjk = bool(re.match(r'[\u4e00-\u9fff]', t))
        if (is_cjk and len(t) < 2) or (not is_cjk and len(t) < 4):
            continue
        if re.match(r'^[\d]+[a-z]+$', t) or re.match(r'^[a-z]+[\d]+$', t):
            continue
        weight = 3 if is_cjk else 1
        freq[t] = freq.get(t, 0) + weight
    return freq


def build_kb_signature(kb_name: str, chunks: list = None, idf: dict = None) -> str:
    """
    生成 KB 签名 + 反哺排序（完整流程）。
    
    流程：
      所有 chunk → BCE 质心 → 近质心 chunk → jieba 提候选词
      → 停用词过滤 → BCE 候选词 vs 原始关键词 → 排序
      → 更新 kb_signatures.json (top-12)
      → 更新 auto_classify_rules.json (top-30)
      
    返回: 签名字符串（top-12 用 · 连接）
    """
    from rag_core import get_embeddings
    import numpy as np
    
    # --- 读取 KB 所有 chunk ---
    if chunks is None:
        try:
            from langchain_chroma import Chroma
            from knowledge_base_manager import _load_index
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
            return ""
    else:
        texts = [c.page_content if hasattr(c, "page_content") else str(c) for c in chunks]
    
    if not texts:
        return ""
    
    # --- 清洗去重 ---
    unique = []
    seen = set()
    for t in texts:
        t = _clean_text(t)
        if len(t) < 30 or t in seen:
            continue
        seen.add(t)
        unique.append(t)
    if not unique:
        return ""
    
    # --- 1. BCE 语义质心：取质心最近的 chunk（均匀采样覆盖全 KB）---
    emb = get_embeddings()
    try:
        # 均匀采样：覆盖全域而非前 N 个（Chromadb 按插入序返回，前 N 个可能来自同份文档）
        n_sample = min(100, len(unique))
        if len(unique) > n_sample:
            step = len(unique) // n_sample
            sampled = [unique[i] for i in range(0, len(unique), step)][:n_sample]
        else:
            sampled = unique[:n_sample]
        chunk_vecs = np.array([emb.embed_query(t[:512]) for t in sampled])
        centroid = chunk_vecs.mean(axis=0)
        dists = np.linalg.norm(chunk_vecs - centroid, axis=1)
        nearest_idx = np.argsort(dists)[:20]
        top_texts = [unique[i] for i in nearest_idx]
    except Exception:
        top_texts = unique[:20]
    
    # --- 2. jieba 提候选词 ---
    combined = "\n".join(top_texts)
    tokens = _tokenize(combined)
    freq = _filter_candidates(tokens)
    if not freq:
        return ""
    
    # --- 3. BCE 比对原始关键词排序 ---
    from knowledge_base_manager import _load_rules
    rules = _load_rules()
    rule = rules.get(kb_name, {})
    originals = rule.get("_originals", rule.get("keywords", [kb_name]))
    if not originals:
        originals = [kb_name]
    
    try:
        ref_vec = np.array(emb.embed_query(" ".join(originals)))
        scored = []
        for w in freq:
            wv = np.array(emb.embed_query(w))
            sim = float(np.dot(wv, ref_vec) / (np.linalg.norm(wv) * np.linalg.norm(ref_vec) + 1e-10))
            scored.append((w, sim))
        scored.sort(key=lambda x: -x[1])
    except Exception:
        scored = sorted(freq.items(), key=lambda x: -x[1])
    
    all_ranked = [w for w, _ in scored]
    
    # --- 4. 签名：top-12 ---
    sig_words = all_ranked[:SIGNATURE_MAX_WORDS]
    signature = " · ".join(sig_words)
    
    # --- 5. 保存签名 ---
    sigs = _load_signatures()
    sigs[kb_name] = {
        "signature": signature,
        "updated_at": str(__import__("datetime").datetime.now()),
        "auto_updated": True,
        "method": "word_freq",
    }
    _save_signatures(sigs)
    
    # --- 6. 反哺：保留原始关键词 + top-30 新词 ---
    if signature:
        try:
            from knowledge_base_manager import _save_rules
            entry = rules.get(kb_name, {})
            existing = list(entry.get("keywords", []))
            
            # 首次标记原始关键词
            if "_originals" not in entry:
                entry["_originals"] = list(existing)
            
            originals_set = set(entry["_originals"])
            
            # 从头部的排序候选词中补充，直到满 FEEDBACK_MAX_WORDS
            result = list(originals_set)
            for w in all_ranked:
                if len(result) >= FEEDBACK_MAX_WORDS:
                    break
                if w not in result:
                    result.append(w)
            
            if set(result) != set(existing):
                entry["keywords"] = result
                _save_rules(rules)
        except Exception:
            pass
    
    return signature


def list_kb_signatures() -> dict:
    raw = _load_signatures()
    result = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[k] = v
        else:
            result[k] = {"signature": str(v), "version": "plain"}
    return result


def rebuild_all_signatures():
    """
    重建所有 KB 签名（第一轮 IDF 收集已废弃，直接第二轮单 KB 生成）。
    保留函数签名兼容。
    """
    from knowledge_base_manager import list_knowledge_bases
    kbs = list_knowledge_bases()
    for kb_name in kbs:
        if kb_name == "default":
            continue
        try:
            build_kb_signature(kb_name)
            print(f"  ✅ {kb_name}")
        except Exception as e:
            print(f"  ❌ {kb_name}: {e}")


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
        build_kb_signature(args.update_sig)
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
