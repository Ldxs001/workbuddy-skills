"""
批量重建所有 KB 的 HNSW 索引（由 setup.bat 在版本升级时调用）
跳过已有有效 hnswlib 索引的 KB，不做重复工作。
"""
import sys, os, time

_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_script_dir, "rag_assistant", "engine"))

from knowledge_base_manager import list_knowledge_bases, rebuild_kb_hnsw
from chroma_adapter import _hnsw_storage_dir, INDEX_FILE

kbs = list_knowledge_bases()
names = list(kbs.keys())
ok = skip = fail = 0
t0 = time.time()

for i, name in enumerate(names):
    cnt = kbs[name].get("doc_count", 0)
    if cnt == 0:
        print(f"  [{i+1}/{len(names)}] {name} — 0 文档，跳过")
        skip += 1
        continue

    # 检查是否有有效 hnswlib 索引
    raw_path = kbs[name].get("path", "")
    if raw_path:
        storage = _hnsw_storage_dir(raw_path)
        idx_file = os.path.join(storage, INDEX_FILE)
        if os.path.isfile(idx_file) and os.path.getsize(idx_file) > 1024:
            print(f"  [{i+1}/{len(names)}] {name} ({cnt} 文档) — HNSW 索引已就绪，跳过")
            skip += 1
            continue

    print(f"  [{i+1}/{len(names)}] 重建 {name} ({cnt} 文档)...")
    sys.stdout.flush()
    try:
        success, msg = rebuild_kb_hnsw(name)
        if success:
            ok += 1
        else:
            print(f"    [FAIL] {msg}")
            fail += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        fail += 1

elapsed = time.time() - t0
print(f"\n完成: {ok} 重建 / {skip} 跳过 / {fail} 失败 (耗时 {elapsed:.0f} 秒)")
