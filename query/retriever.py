"""Hybrid dense/FTS retrieval, RRF fusion, reranking, and paper diversity."""
from __future__ import annotations
from config import settings
from embedding.embedder import embed_query
from query.reranker import rerank
from storage.vector_store import get_table
_RRF_K = 60

def hybrid_search(query: str, k: int | None = None, facility: str | None = None, access_level: str | None = None,
                  rerank_results: bool = True) -> list[dict]:
    k = k or settings.top_k; table = get_table(); fetch_k = max(k*5, settings.rerank_fetch_limit)
    dense = table.search(embed_query(query), vector_column_name="vector").limit(fetch_k)
    lexical = table.search(query, query_type="fts").limit(fetch_k)
    clauses = []
    if facility: clauses.append(f"facilities LIKE '%{facility.replace(chr(39), chr(39)*2)}%'")
    if access_level: clauses.append(f"access_level = '{access_level.replace(chr(39), chr(39)*2)}'")
    if clauses:
        clause = " AND ".join(clauses); dense = dense.where(clause); lexical = lexical.where(clause)
    scores, rows = {}, {}
    for result_list in (dense.to_list(), lexical.to_list()):
        for rank, row in enumerate(result_list):
            cid = row["chunk_id"]; scores[cid] = scores.get(cid, 0.0) + 1.0/(_RRF_K+rank+1); rows[cid] = row
    pool = [rows[cid] for cid in sorted(scores, key=scores.get, reverse=True)[:settings.rerank_pool_size]]
    ranked = rerank(query, pool, min(len(pool), k*2)) if settings.rerank_enabled and rerank_results else pool
    output, per_paper = [], {}
    for row in ranked:
        count = per_paper.get(row["source_id"], 0)
        if count >= settings.per_paper_limit: continue
        row["retrieval_score"] = scores.get(row["chunk_id"], 0.0); output.append(row); per_paper[row["source_id"]] = count+1
        if len(output) >= k: break
    return output
