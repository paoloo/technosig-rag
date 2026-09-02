"""Qwen3-VL reranking across ordinary text chunks and rendered PDF pages."""
from __future__ import annotations

import logging
from functools import lru_cache

from config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder

    logger.info("loading visual reranker %s on %s", settings.visual_rerank_model, settings.visual_device)
    return CrossEncoder(
        settings.visual_rerank_model,
        device=settings.visual_device,
        revision=settings.visual_rerank_revision or None,
    )


def _document(candidate: dict):
    text = (
        f"[ADS:{candidate['bibcode']}; {candidate.get('access_level', '')}] "
        f"{candidate.get('title', '')}\n{candidate.get('text', '')}"
    )
    image_path = candidate.get("image_path")
    if not image_path:
        return text
    return {"text": text, "image": str(settings.vector_data_dir / image_path)}


def rerank_multimodal(question: str, candidates: list[dict], top_k: int) -> list[dict]:
    if len(candidates) <= top_k:
        return candidates
    try:
        scores = _model().predict(
            [(question, _document(candidate)) for candidate in candidates],
            prompt=settings.visual_rerank_prompt,
            batch_size=settings.visual_rerank_batch_size,
            show_progress_bar=False,
        )
        ranked = sorted(zip(scores, candidates), key=lambda item: float(item[0]), reverse=True)
        return [candidate for _, candidate in ranked[:top_k]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("visual rerank failed; using fused retrieval order: %s", exc)
        return candidates[:top_k]
