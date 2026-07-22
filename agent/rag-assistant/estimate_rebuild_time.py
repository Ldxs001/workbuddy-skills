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
        # 获取模型名称
        try:
            model_name = model._modules["0"]._modules["0"].config.name_or_path
        except Exception:
            try:
                model_name = model._first_module().auto_model.config._name_or_path
            except Exception:
                model_name = type(model).__name__

        # 从 SQLite 读真实文档 chunk 做测速（不能用 "测试文本"，长度差太多）
        import sqlite3
        kb_path = kbs[kb_name].get("path", "")
        db_path = os.path.join(kb_path, "chroma.sqlite3")
        bench_texts = ["测试文本"] * bench_samples  # 兜底
        if os.path.isfile(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT string_value FROM embedding_metadata WHERE key='chroma:document' ORDER BY RANDOM() LIMIT ?",
                (bench_samples,)
            )
            rows = cur.fetchall()
            conn.close()
            if rows:
                bench_texts = [r[0][:1024] for r in rows]  # 截断到 1024 字符，避免极端长文本

        # 测速：用真实 chunk 编码
        t0 = time.time()
        model.encode(bench_texts, normalize_embeddings=True)
        t1 = time.time()
        elapsed = t1 - t0
        sec_per_doc = elapsed / len(bench_texts)
    except Exception:
        pass

total_sec = int(total * sec_per_doc + n * kb_overhead)
est_min = max(1, total_sec // 60)

print(f"  知识库: {n} 个, 文档总计: {total} 条")
print(f"  嵌入模型: {model_name}")
print(f"  嵌入测速: {sec_per_doc*1000:.0f}ms/条")
print(f"  预计耗时: 约 {est_min} 分钟")
