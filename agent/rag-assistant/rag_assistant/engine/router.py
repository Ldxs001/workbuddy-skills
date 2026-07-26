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
                    sig_list = sig_info.get("signatures", [])
                    if not sig_text and not sig_list:
                        continue
                    # 多向量路由：每个分象限做一次 cosine，取最高分
                    if sig_list:
                        scores = []
                        for one_sig in sig_list:
                            sv = np.array(emb.embed_query(one_sig.replace(" · ", " ")[:512]))
                            scores.append(float(np.dot(qv, sv) / (np.linalg.norm(qv) * np.linalg.norm(sv))))
                        sim = max(scores)
                    else:
                        sv = np.array(emb.embed_query(sig_text.replace(" · ", " ")[:512]))
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

FEEDBACK_MAX_WORDS = 30
MIN_FEEDBACK_SIMILARITY = 0.3  # 候选词与原始关键词的最低语义相似度阈值

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
    "实施日期", "换页", "第页", "接上", "转下页", "上一页", "下一页", "上页", "下页", "翻页", "第几页", "图例", "来源", "单位", "摘要", "关键词",
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
      所有 chunk → 四分法采样 → 4象限各算质心 → 各取近20chunk
      → 各象限 jieba 提候选词 → 停用词过滤 → BCE vs 原始关键词排序
      → round-robin 合并 → 更新 kb_signatures.json (上限80词)
      → 更新 auto_classify_rules.json (上限30词)
      
    返回: 签名字符串（top-N 用 · 连接）
    """
    from rag_core import get_embeddings
    import numpy as np
    
    # --- 读取 KB 所有 chunk ---
    if chunks is None:
        try:
            from chroma_adapter import Chroma
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
    
    # --- 1. 四分法采样：4象限各自独立 ---
    emb = get_embeddings()
    import random
    try:
        N = len(unique)
        # 动态采样量
        if N < 200:
            n_sample = N
        elif N < 2000:
            n_sample = min(N, max(200, int(N * 0.3)), 400)
        else:
            n_sample = min(N, max(400, int(N * 0.2)), 500)

        if n_sample >= N:
            quad_chunks = [unique]     # 全量：当作 1 个象限
        elif N < 500:
            sampled = random.sample(unique, n_sample)
            quad_chunks = [sampled]    # 全域随机：1 个象限
        else:
            # 四分 + 每份随机
            quarter_size = N // 4
            base = n_sample // 4
            remainder = n_sample % 4
            quad_chunks = []
            for q in range(4):
                start = q * quarter_size
                end = start + quarter_size if q < 3 else N
                pool = unique[start:end]
                take = base + (1 if q < remainder else 0)
                quad_chunks.append([])
                quad_chunks[-1] = random.sample(pool, take)
    except Exception:
        quad_chunks = [unique]
    
    # --- 加载原始关键词（所有象限共享）---
    from knowledge_base_manager import _load_rules, _save_rules
    rules = _load_rules()
    rule = rules.get(kb_name, {})
    originals = rule.get("_originals", rule.get("keywords", [kb_name]))
    if not originals:
        originals = [kb_name]
    if kb_name not in originals:
        originals = [kb_name] + originals
    
    try:
        orig_vecs = [np.array(emb.embed_query(o)) for o in originals if o.strip()]
    except Exception:
        orig_vecs = []
    
    # --- 2. 每象限独立：质心→近邻20→jieba→BCE排序 ---
    all_quad_ranked = []  # 每象限各一个 [(word, score), ...]
    for q_chunks in quad_chunks:
        try:
            q_vecs = np.array([emb.embed_query(t[:512]) for t in q_chunks])
            q_centroid = q_vecs.mean(axis=0)
            q_dists = np.linalg.norm(q_vecs - q_centroid, axis=1)
            q_near = np.argsort(q_dists)[:min(20, len(q_chunks))]
            q_top = [q_chunks[i] for i in q_near]
        except Exception:
            q_top = q_chunks[:min(20, len(q_chunks))]
        
        # jieba 提候选词 + 停用词过滤
        q_text = "\n".join(q_top)
        q_tokens = _tokenize(q_text)
        q_freq = _filter_candidates(q_tokens)
        if not q_freq:
            all_quad_ranked.append([])
            continue
        
        # BCE 比对原始关键词排序
        if orig_vecs:
            q_scored = []
            for w in q_freq:
                wv = np.array(emb.embed_query(w))
                best = max(float(np.dot(wv, ov) / (np.linalg.norm(wv) * np.linalg.norm(ov) + 1e-10)) for ov in orig_vecs)
                q_scored.append((w, best))
            q_scored.sort(key=lambda x: -x[1])
        else:
            q_scored = sorted(q_freq.items(), key=lambda x: -x[1])
        
        all_quad_ranked.append(q_scored)
    
    # 无任何候选词 → 空签名
    if not any(all_quad_ranked):
        return ""
    
    # --- 3. 四段拼接：每象限取前 20 ---
    merged = []
    for q_scored in all_quad_ranked:
        merged.extend(q_scored[:20])   # 最多20，少则取实际值
    
    all_ranked = [w for w, _ in merged]
    
    # --- 4. 签名：上限 80 词（取实际值，不强求）---
    SIGNATURE_CAP = 80
    sig_words = all_ranked[:min(SIGNATURE_CAP, len(all_ranked))]
    signature = " · ".join(sig_words)
    
    # --- 5. 保存签名（含分象限签名，用于多向量路由）---
    # 每象限各自的 top-20 签名
    quad_sigs = []
    for q_scored in all_quad_ranked:
        q_words = [w for w, _ in q_scored[:20]]
        if q_words:
            quad_sigs.append(" · ".join(q_words))
    
    sigs = _load_signatures()
    sigs[kb_name] = {
        "signature": signature,
        "signatures": quad_sigs if len(quad_sigs) > 1 else [],
        "updated_at": str(__import__("datetime").datetime.now()),
        "auto_updated": True,
        "method": "word_freq",
    }
    _save_signatures(sigs)
    
    # --- 6. 反哺：四象限均分名额（30 - count(originals)）/ 4 ---
    if signature:
        try:
            entry = rules.get(kb_name, {})
            existing = list(entry.get("keywords", []))
            
            # 首次标记原始关键词（_save_rules 入口已兜底，这里保留作为内存级保障）
            if "_originals" not in entry:
                entry["_originals"] = list(existing)
            
            originals_set = set(entry["_originals"])
            orig_count = len(originals_set)
            
            # 可分配新词名额 = 30 - 原始关键词数
            x = FEEDBACK_MAX_WORDS - orig_count
            if x > 0:
                y = x // 4  # 每象限上限，向下取整
                
                result = list(originals_set)
                for q_idx in range(len(all_quad_ranked)):
                    q_scored = all_quad_ranked[q_idx]
                    taken = 0
                    for w, score in q_scored:
                        if taken >= y:
                            break
                        if score < MIN_FEEDBACK_SIMILARITY:
                            continue
                        if w in result:
                            continue
                        result.append(w)
                        taken += 1
                
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
