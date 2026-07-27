"""
实时测速 + 预估 HNSW 重建总耗时
由 setup.bat 调用，显示精确的预计耗时。
"""
import sys, os, time, json

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_script_dir, "rag_assistant", "engine"))

from knowledge_base_manager import list_knowledge_bases

kbs = list_knowledge_bases()
total = sum(v.get("doc_count", 0) for v in kbs.values())
n = len(kbs)

# 默认值（bce-embedding-base_v1 在 CPU 上的实测值）
sec_per_doc = 0.14
kb_overhead = 10
model_name = "?"

# 找一个有文档的 KB 做测速（按文档数降序，取最多的那个）
bench_kb = next(iter(sorted(
    [(k, v.get("doc_count", 0)) for k, v in kbs.items()],
    key=lambda x: -x[1]
)), (None, 0))
kb_name, doc_cnt = bench_kb

if kb_name and doc_cnt > 0:
    bench_samples = min(doc_cnt, 10)  # 有多少测多少，最多 10
    try:
        from rag_core import get_embeddings
        emb = get_embeddings(kb_name=kb_name)
        model = emb._model

        # 测速：用真实 chunk 编码
        from sqlite3 import connect
        kb_path = kbs[kb_name].get("path", "")
        db_path = os.path.join(kb_path, "chroma.sqlite3")
        bench_texts = ["测试文本"] * bench_samples  # 兜底
        if os.path.isfile(db_path):
            conn = connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT string_value FROM embedding_metadata WHERE key='chroma:document' ORDER BY RANDOM() LIMIT ?",
                (bench_samples,)
            )
            rows = cur.fetchall()
            conn.close()
            if rows:
                bench_texts = [r[0][:1024] for r in rows]

        t0 = time.time()
        model.encode(bench_texts, normalize_embeddings=True)
        t1 = time.time()
        elapsed = t1 - t0
        sec_per_doc = elapsed / len(bench_texts)
    except Exception:
        pass

# 模型名：优先从 emb._model_path 取，否则正则扫描 rag_config.json
model_name = "?"
try:
    model_name = emb._model_path or model_name
except Exception:
    pass
if model_name == "?":
    try:
        import re, json
        _raw = open(os.path.join(_script_dir, "data", "config", "rag_config.json"), "r", encoding="utf-8").read()
        _m = re.search(r'"embedding"\s*:\s*\{[^}]*?"model_path"\s*:\s*"([^"]+)"', _raw)
        if _m:
            model_name = _m.group(1)
    except Exception:
        pass

total_sec = int(total * sec_per_doc + n * kb_overhead)
est_min = max(1, total_sec // 60)

print(f"  知识库: {n} 个, 文档总计: {total} 条")
print(f"  嵌入模型: {model_name}")
print(f"  嵌入测速: {sec_per_doc*1000:.0f}ms/条")
print(f"  预计耗时: 约 {est_min} 分钟")
