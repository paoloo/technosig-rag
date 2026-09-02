"""Create Qwen3-VL embeddings for rendered pages and text queries."""
from __future__ import annotations

import json
import logging
from functools import lru_cache

import numpy as np

from config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    logger.info("loading visual embedder %s on %s", settings.visual_embedding_model, settings.visual_device)
    return SentenceTransformer(
        settings.visual_embedding_model,
        device=settings.visual_device,
        revision=settings.visual_embedding_revision or None,
        truncate_dim=settings.visual_embedding_dimensions,
    )


def _load_rows(metadata_path) -> list[dict]:
    with metadata_path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _document(row: dict) -> dict:
    image_path = settings.vector_data_dir / row["image_path"]
    context = f"{row['title']}\nADS:{row['bibcode']}; page {row['page_number']}\n{row['text']}"
    return {"text": context, "image": str(image_path)}


def embed_visual_query(query: str) -> list[float]:
    vector = _model().encode(
        [query],
        prompt=settings.visual_embedding_prompt,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]
    return vector.astype(np.float32).tolist()


def embed_visual_pages(limit: int | None = None, force: bool = False) -> dict[str, int]:
    metadata_paths = sorted(settings.visual_metadata_dir.glob("*.jsonl"))
    if limit is not None:
        metadata_paths = metadata_paths[:limit]
    embedded_papers = 0
    embedded_pages = 0
    errors = 0
    for metadata_path in metadata_paths:
        vectors_path = settings.visual_embeddings_cache_dir / f"{metadata_path.stem}.npy"
        ids_path = settings.visual_embeddings_cache_dir / f"{metadata_path.stem}.ids.json"
        if vectors_path.exists() and ids_path.exists() and not force:
            embedded_papers += 1
            embedded_pages += len(json.loads(ids_path.read_text()))
            continue
        try:
            rows = _load_rows(metadata_path)
            vectors = _model().encode(
                [_document(row) for row in rows],
                prompt=settings.visual_embedding_prompt,
                batch_size=settings.visual_embedding_batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            np.save(vectors_path, np.asarray(vectors, dtype=np.float32))
            ids_path.write_text(json.dumps([row["visual_id"] for row in rows]))
            embedded_papers += 1
            embedded_pages += len(rows)
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning("failed to embed visual pages for %s: %s", metadata_path.name, exc)
    return {"embedded_papers": embedded_papers, "embedded_pages": embedded_pages, "errors": errors}
