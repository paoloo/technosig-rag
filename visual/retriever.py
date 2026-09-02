"""Retrieve from isolated text and visual indexes, then rerank them together."""
from __future__ import annotations

from config import settings
from visual.embedder import embed_visual_query
from visual.reranker import rerank_multimodal

_RRF_K = 60


def _text_search(*args, **kwargs):
    from query.retriever import hybrid_search
    return hybrid_search(*args, **kwargs)


def _visual_table():
    from visual.store import get_visual_table
    return get_visual_table()


def _visual_candidates(query: str, fetch_k: int, facility: str | None = None) -> list[dict]:
    table = _visual_table()
    dense = table.search(embed_visual_query(query), vector_column_name="vector").limit(fetch_k)
    lexical = table.search(query, query_type="fts").limit(fetch_k)
    if facility:
        escaped = facility.replace("'", "''")
        dense = dense.where(f"facilities LIKE '%{escaped}%'")
        lexical = lexical.where(f"facilities LIKE '%{escaped}%'")
    scores: dict[str, float] = {}
    rows: dict[str, dict] = {}
    for result_list in (dense.to_list(), lexical.to_list()):
        for rank, row in enumerate(result_list):
            visual_id = row["visual_id"]
            scores[visual_id] = scores.get(visual_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
            rows[visual_id] = row
    output = []
    for visual_id in sorted(scores, key=scores.get, reverse=True)[:fetch_k]:
        row = rows[visual_id]
        row["retrieval_score"] = scores[visual_id]
        row["modality"] = "page_image"
        output.append(row)
    return output


def visual_search(query: str, k: int | None = None, facility: str | None = None) -> list[dict]:
    k = k or settings.top_k
    candidates = _visual_candidates(query, max(k * 5, settings.rerank_pool_size), facility)
    return rerank_multimodal(query, candidates[: settings.rerank_pool_size], k)


def multimodal_search(query: str, k: int | None = None, facility: str | None = None) -> list[dict]:
    """Search stable text chunks and visual pages without mixing their vector spaces."""
    k = k or settings.top_k
    fetch_k = max(k * 4, settings.rerank_pool_size)
    candidates: list[dict] = []
    try:
        text_rows = _text_search(query, k=fetch_k, facility=facility, rerank_results=False)
        for row in text_rows:
            row["modality"] = "text"
        candidates.extend(text_rows)
    except RuntimeError:
        pass
    try:
        candidates.extend(_visual_candidates(query, fetch_k, facility))
    except RuntimeError:
        pass
    if not candidates:
        return []

    ranked = rerank_multimodal(query, candidates[: settings.rerank_pool_size * 2], max(k * 3, k))
    output: list[dict] = []
    per_paper: dict[str, int] = {}
    for row in ranked:
        count = per_paper.get(row["source_id"], 0)
        if count >= settings.per_paper_limit:
            continue
        output.append(row)
        per_paper[row["source_id"]] = count + 1
        if len(output) >= k:
            break
    return output
