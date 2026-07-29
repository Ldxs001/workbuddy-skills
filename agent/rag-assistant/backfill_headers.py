"""
存量数据回填：为已有 KB 补上 chunk_seq + is_header 元数据
直接操作 SQLite，不动 hnswlib，不影响向量检索
"""
import sqlite3
import os
import re
import sys

KB_DIR = None


def _looks_like_header(text: str) -> bool:
    t = text[:300]
    if not t.strip():
        return False
    if re.search(r'[\u4e00-\u9fff]{2,4}\s*\d?\s*[,，]\s*[\u4e00-\u9fff]{2,4}', t):
        return True
    if re.search(r'(大学|学院|研究所|研究院|实验室|有限公司|集团|医院|'
                 r'中心[，。\s\n]|局[，。\s\n]|部[，。\s\n]|委员会)', t):
        return True
    if re.search(r'(摘要|关键词|Keywords|中图分类号|CLC|DOI|文章编号|'
                 r'文献标识码|基金项目|收稿日期|修回日期|录用日期|'
                 r'文件编号|起草单位|发布单位|编制|审核|批准|代替|归口)', t[:100]):
        return True
    if re.search(r'(第\d+卷\s*第\d+期|Vol\.\s*\d+\s*No\.\s*\d+|'
                 r'学报\b|通报\b|研究\b|杂志\b|期刊\b|出版社\b)', t[:200]):
        return True
    if re.search(r'^(论著|综述|研究报告|研究论文|简报|简讯|信函|'
                 r'经验交流|病例报告|技术报告|方法|标准|规范|指南)', t.strip()[:20]):
        return True
    return False


def needs_backfill(kb_path: str) -> bool:
    """检查该 KB 是否需要回填（是否存在 chunk_seq 元数据）"""
    db = os.path.join(kb_path, "chroma.sqlite3")
    if not os.path.exists(db):
        return False
    try:
        conn = sqlite3.connect(db)
        cnt = conn.execute(
            "SELECT COUNT(*) FROM embedding_metadata WHERE key='chunk_seq'"
        ).fetchone()[0]
        conn.close()
        return cnt == 0
    except Exception:
        return False


def backfill_kb(kb_name: str, kb_path: str) -> tuple:
    """回填单个 KB，返回 (chunks_count, meta_count)"""
    db = os.path.join(kb_path, "chroma.sqlite3")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    sources = conn.execute(
        "SELECT DISTINCT string_value FROM embedding_metadata WHERE key='source'"
    ).fetchall()
    sources = [r[0] for r in sources]

    total_chunks = 0
    total_meta = 0

    for src in sources:
        rows = conn.execute("""
            SELECT e.id, m.string_value as doc_text
            FROM embeddings e
            JOIN embedding_metadata m ON e.id = m.id AND m.key = 'chroma:document'
            WHERE e.id IN (
                SELECT id FROM embedding_metadata WHERE key='source' AND string_value=?
            )
            ORDER BY e.id
        """, (src,)).fetchall()
        if not rows:
            continue

        chunks = [(r["id"], r["doc_text"]) for r in rows]
        n = len(chunks)

        # 位置兜底 + 逐块探测
        header_seqs = set(range(min(4, n)))
        max_seq = n - 1
        for i, (eid, text) in enumerate(chunks):
            if i < 4:
                continue
            if text and _looks_like_header(text):
                header_seqs.add(i)
                if i + 1 <= max_seq:
                    header_seqs.add(i + 1)

        values = []
        for seq, (eid, _) in enumerate(chunks):
            values.append((eid, "chunk_seq", None, seq, None, None))
            values.append((eid, "is_header", None, None, None, 1 if seq in header_seqs else 0))

        conn.executemany(
            "INSERT OR IGNORE INTO embedding_metadata (id, key, string_value, int_value, float_value, bool_value) VALUES (?, ?, ?, ?, ?, ?)",
            values,
        )
        total_chunks += len(chunks)
        total_meta += len(values)

    conn.commit()
    conn.close()
    return total_chunks, total_meta


def backfill_all(kb_dir: str = None) -> dict:
    """回填所有需要回填的 KB，返回统计信息"""
    global KB_DIR
    if kb_dir:
        KB_DIR = kb_dir
    if KB_DIR is None:
        KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kb")

    results = {"total_kbs": 0, "backfilled_kbs": 0, "total_chunks": 0, "total_meta": 0, "details": []}

    for name in sorted(os.listdir(KB_DIR)):
        d = os.path.join(KB_DIR, name)
        if not os.path.isdir(d):
            continue
        db = os.path.join(d, "chroma.sqlite3")
        if not os.path.exists(db):
            continue

        results["total_kbs"] += 1

        if not needs_backfill(d):
            results["details"].append({"kb": name, "status": "skipped", "reason": "已回填"})
            continue

        c, m = backfill_kb(name, d)
        results["backfilled_kbs"] += 1
        results["total_chunks"] += c
        results["total_meta"] += m
        results["details"].append({"kb": name, "status": "done", "chunks": c, "meta": m})
        print(f"  [{name}] 回填 {c} 块, {m} 条元数据")

    return results


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"{'[DRY RUN] ' if dry_run else ''}回填 chunk_seq + is_header")
    print("=" * 50)
    results = backfill_all()
    print("=" * 50)
    print(f"共 {results['total_kbs']} 个 KB，回填 {results['backfilled_kbs']} 个，"
          f"{results['total_chunks']} 块，{results['total_meta']} 条元数据")


if __name__ == "__main__":
    main()
