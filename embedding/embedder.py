"""Phase 5: embed chunks via Ollama's embeddings API.

Runs against whatever OLLAMA_HOST is configured (on atadev, the box's
already-running shared daemon). Vectors are cached per-paper as .npy so a
rerun after an interruption skips papers the manifest already marks
'embedded' instead of recomputing.
"""

from __future__ import annotations

import json
import logging

import numpy as np
import ollama

from config import settings
from state.manifest import Manifest

logger = logging.getLogger(__name__)


def _client() -> ollama.Client:
    return ollama.Client(host=settings.ollama_host)


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = _client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), settings.embedding_batch_size):
        batch = texts[start : start + settings.embedding_batch_size]
        try:
            vectors.extend(client.embed(model=settings.embedding_model, input=batch)["embeddings"])
        except (AttributeError, TypeError, KeyError):
            vectors.extend(client.embeddings(model=settings.embedding_model, prompt=text)["embedding"] for text in batch)
    return vectors


def embed_query(text: str) -> list[float]:
    return _client().embeddings(model=settings.embedding_model, prompt=text)["embedding"]


def embed_pending() -> dict[str, int]:
    manifest = Manifest(settings.manifest_path)
    pending = manifest.ids_ready_for("embedded")
    logger.info("embedding %d papers", len(pending))

    for source_id in pending:
        record = manifest.get(source_id)
        stem = record["bibcode"].replace("/", "_")
        chunks_path = settings.chunks_dir / f"{stem}.jsonl"
        vec_path = settings.embeddings_cache_dir / f"{stem}.npy"
        ids_path = settings.embeddings_cache_dir / f"{stem}.ids.json"
        try:
            # Iterate physical JSONL records. str.splitlines() also splits on
            # Unicode U+2028/U+2029 inside valid JSON strings and corrupts a
            # small number of extracted papers.
            with chunks_path.open() as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
            texts = [r["text"] for r in rows]
            chunk_ids = [r["chunk_id"] for r in rows]
            vectors = embed_texts(texts)
            np.save(vec_path, np.array(vectors, dtype=np.float32))
            ids_path.write_text(json.dumps(chunk_ids))
            manifest.mark_stage(source_id, "embedded")
            logger.info("embedded %s: %d chunks", source_id, len(texts))
        except Exception as exc:  # noqa: BLE001
            manifest.record_error(source_id, f"embed error: {exc}")
            logger.warning("failed to embed %s: %s", source_id, exc)

    return manifest.status_summary()
