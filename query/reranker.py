"""Listwise relevance reranking with structured output and safe fallback."""
from __future__ import annotations
import json, logging, ollama
from functools import lru_cache
from config import settings
logger = logging.getLogger(__name__)

def _candidate_text(chunk: dict) -> str:
    return f"[{chunk['bibcode']}; {chunk['access_level']}] {chunk['title']}\n{chunk['text']}"

@lru_cache(maxsize=1)
def _cross_encoder():
    from sentence_transformers import CrossEncoder
    logger.info("loading cross-encoder reranker %s on %s", settings.rerank_model, settings.rerank_device)
    return CrossEncoder(
        settings.rerank_model,
        device=settings.rerank_device,
        revision=settings.rerank_revision or None,
    )

def _cross_encoder_rerank(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    pairs = [(question, _candidate_text(chunk)) for chunk in chunks]
    scores = _cross_encoder().predict(
        pairs,
        batch_size=settings.rerank_batch_size,
        show_progress_bar=False,
    )
    ranked = sorted(zip(scores, chunks), key=lambda item: float(item[0]), reverse=True)
    return [chunk for _, chunk in ranked[:top_k]]

def _ollama_rerank(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    candidates = "\n".join(f"{i+1}. [{c['bibcode']}; {c['access_level']}] {c['title']}\n{c['text']}" for i,c in enumerate(chunks))
    prompt = ("Rank excerpts for answering the research question. Prefer direct evidence, methods/results over passing mentions, "
              "full text over abstracts when otherwise equal, and include contradictory evidence. Return only a JSON array of at most "
              f"{top_k} candidate numbers.\n\nQuestion: {question}\n\nCandidates:\n{candidates}")
    response = ollama.Client(host=settings.ollama_host).chat(model=settings.rerank_model or settings.generation_model,
        messages=[{"role":"user","content":prompt}], options={"temperature":0})
    text = response["message"]["content"]; indices = json.loads(text[text.index("["):text.rindex("]")+1])
    ranked, seen = [], set()
    for index in indices:
        if isinstance(index, int) and 1 <= index <= len(chunks) and chunks[index-1]["chunk_id"] not in seen:
            ranked.append(chunks[index-1]); seen.add(chunks[index-1]["chunk_id"])
    ranked.extend(c for c in chunks if c["chunk_id"] not in seen)
    return ranked[:top_k]

def rerank(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    if len(chunks) <= top_k: return chunks
    try:
        if settings.rerank_backend == "cross-encoder":
            return _cross_encoder_rerank(question, chunks, top_k)
        return _ollama_rerank(question, chunks, top_k)
    except Exception as exc:
        logger.warning("%s rerank failed; using fused order: %s", settings.rerank_backend, exc)
        return chunks[:top_k]
