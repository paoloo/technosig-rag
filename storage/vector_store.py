from __future__ import annotations
import json, lancedb, numpy as np
from config import settings
from state.manifest import Manifest
TABLE_NAME = "chunks"
def _db(): return lancedb.connect(str(settings.lancedb_dir))
def _table_names(db): return set(db.list_tables().tables)

def _rows_for_paper(source_id: str) -> list[dict]:
    record = Manifest(settings.manifest_path).get(source_id); stem = record["bibcode"].replace("/", "_")
    with (settings.chunks_dir / f"{stem}.jsonl").open() as handle:
        chunks = {(o := json.loads(line))["chunk_id"]: o for line in handle if line.strip()}
    vectors = np.load(settings.embeddings_cache_dir / f"{stem}.npy"); ids = json.loads((settings.embeddings_cache_dir / f"{stem}.ids.json").read_text())
    rows = []
    for cid, vector in zip(ids, vectors):
        r = chunks[cid]
        # Keep the schema stable across empty values and later chunks. LanceDB
        # infers the first row; `v or ""` made chunk 0 a string but chunk 1 an
        # integer, which fails when a multi-chunk paper is added.
        metadata = {k: (", ".join(v) if isinstance(v, list) else ("" if v is None else str(v)))
                    for k, v in r.items() if k != "vector"}
        rows.append(metadata | {"vector": vector.tolist()})
    return rows

def store_pending() -> dict[str, int]:
    manifest = Manifest(settings.manifest_path); pending = manifest.ids_ready_for("stored")
    if not pending: return manifest.status_summary()
    db = _db(); table = db.open_table(TABLE_NAME) if TABLE_NAME in _table_names(db) else None
    for source_id in pending:
        try:
            rows = _rows_for_paper(source_id)
            if rows:
                if table is None: table = db.create_table(TABLE_NAME, data=rows)
                else: table.delete(f"source_id = '{source_id}'"); table.add(rows)
            manifest.mark_stage(source_id, "stored")
        except Exception as exc: manifest.record_error(source_id, f"store error: {exc}")
    return manifest.status_summary()

def get_table():
    db = _db()
    if TABLE_NAME not in _table_names(db): raise RuntimeError("LanceDB chunks table does not exist; run the pipeline first")
    return db.open_table(TABLE_NAME)
