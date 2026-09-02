"""Store visual page vectors in an isolated LanceDB database."""
from __future__ import annotations

import json

import lancedb
import numpy as np

from config import settings

TABLE_NAME = "visual_pages"


def _db():
    return lancedb.connect(str(settings.visual_lancedb_dir))


def _table_names(db) -> set[str]:
    return set(db.list_tables().tables)


def _rows(metadata_path) -> list[dict]:
    with metadata_path.open() as handle:
        records = {row["visual_id"]: row for line in handle if line.strip() for row in [json.loads(line)]}
    vectors = np.load(settings.visual_embeddings_cache_dir / f"{metadata_path.stem}.npy")
    ids = json.loads((settings.visual_embeddings_cache_dir / f"{metadata_path.stem}.ids.json").read_text())
    return [records[visual_id] | {"vector": vector.tolist()} for visual_id, vector in zip(ids, vectors)]


def store_visual_pages(force: bool = False) -> dict[str, int]:
    db = _db()
    table = db.open_table(TABLE_NAME) if TABLE_NAME in _table_names(db) else None
    state_path = settings.visual_lancedb_dir / "ingested.json"
    state = {} if force or not state_path.exists() else json.loads(state_path.read_text())
    stored_papers = 0
    for metadata_path in sorted(settings.visual_metadata_dir.glob("*.jsonl")):
        vectors_path = settings.visual_embeddings_cache_dir / f"{metadata_path.stem}.npy"
        ids_path = settings.visual_embeddings_cache_dir / f"{metadata_path.stem}.ids.json"
        if not vectors_path.exists() or not ids_path.exists():
            continue
        signature = f"{metadata_path.stat().st_mtime_ns}:{vectors_path.stat().st_mtime_ns}:{vectors_path.stat().st_size}"
        if state.get(metadata_path.name) == signature and not force:
            stored_papers += 1
            continue
        rows = _rows(metadata_path)
        if rows:
            source_id = rows[0]["source_id"].replace("'", "''")
            if table is None:
                table = db.create_table(TABLE_NAME, data=rows)
            else:
                table.delete(f"source_id = '{source_id}'")
                table.add(rows)
            state[metadata_path.name] = signature
            state_path.write_text(json.dumps(state, indent=2, sort_keys=True))
            stored_papers += 1
    return {"stored_papers": stored_papers, "stored_pages": table.count_rows() if table is not None else 0}


def get_visual_table():
    db = _db()
    if TABLE_NAME not in _table_names(db):
        raise RuntimeError("LanceDB visual_pages table does not exist; run the visual pipeline first")
    return db.open_table(TABLE_NAME)


def get_visual_page(visual_id: str) -> dict | None:
    escaped = visual_id.replace("'", "''")
    rows = get_visual_table().search().where(f"visual_id = '{escaped}'").limit(1).to_list()
    return rows[0] if rows else None
