"""SQLite manifest for resumable ADS acquisition and RAG processing."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

STAGES = ("fetched", "parsed", "extracted", "chunked", "embedded", "stored", "indexed")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
 source_id TEXT PRIMARY KEY, bibcode TEXT UNIQUE NOT NULL, title TEXT, abstract TEXT,
 authors TEXT, published TEXT, updated TEXT, publication TEXT, doctype TEXT, doi TEXT,
 identifiers TEXT, properties TEXT, esources TEXT, facilities TEXT, keywords TEXT,
 pdf_path TEXT, meta_path TEXT, access_level TEXT NOT NULL, download_source TEXT,
 attempted_sources TEXT, fetched_at TEXT, parsed_at TEXT, extracted_at TEXT,
 chunked_at TEXT, embedded_at TEXT, stored_at TEXT, indexed_at TEXT, last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_papers_bibcode ON papers(bibcode);
CREATE INDEX IF NOT EXISTS idx_papers_access ON papers(access_level);
"""

def _now() -> str: return datetime.now(timezone.utc).isoformat()

@dataclass
class PaperRecord:
    source_id: str
    bibcode: str
    title: str | None = None
    abstract: str | None = None
    authors: str | None = None
    published: str | None = None
    updated: str | None = None
    publication: str | None = None
    doctype: str | None = None
    doi: str | None = None
    identifiers: str | None = None
    properties: str | None = None
    esources: str | None = None
    facilities: str | None = None
    keywords: str | None = None
    pdf_path: str | None = None
    meta_path: str | None = None
    access_level: str = "metadata_only"
    download_source: str | None = None
    attempted_sources: str | None = None

class Manifest:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with self._connect() as conn: conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path); conn.row_factory = sqlite3.Row
        try: yield conn; conn.commit()
        finally: conn.close()

    def upsert_fetched(self, record: PaperRecord) -> None:
        fields = tuple(record.__dataclass_fields__)
        values = tuple(getattr(record, field) for field in fields)
        updates = ", ".join(f"{f}=excluded.{f}" for f in fields if f != "source_id")
        with self._connect() as conn:
            conn.execute(f"INSERT INTO papers ({','.join(fields)},fetched_at) VALUES ({','.join('?' for _ in fields)},?) ON CONFLICT(source_id) DO UPDATE SET {updates},fetched_at=excluded.fetched_at", values + (_now(),))

    def mark_stage(self, source_id: str, stage: str) -> None:
        if stage not in STAGES: raise ValueError(f"unknown stage: {stage}")
        with self._connect() as conn: conn.execute(f"UPDATE papers SET {stage}_at=?,last_error=NULL WHERE source_id=?", (_now(), source_id))

    def mark_all_indexed(self) -> None:
        with self._connect() as conn: conn.execute("UPDATE papers SET indexed_at=? WHERE stored_at IS NOT NULL", (_now(),))

    def record_error(self, source_id: str, message: str) -> None:
        with self._connect() as conn: conn.execute("UPDATE papers SET last_error=? WHERE source_id=?", (message[:4000], source_id))

    def set_access_level(self, source_id: str, access_level: str) -> None:
        if access_level not in {"full_text", "abstract_only", "metadata_only", "inaccessible"}:
            raise ValueError(f"unknown access level: {access_level}")
        with self._connect() as conn:
            conn.execute("UPDATE papers SET access_level=? WHERE source_id=?", (access_level, source_id))

    def reset_processing(self, source_id: str) -> None:
        """Re-run all derived stages when newly acquired full text supersedes an abstract."""
        with self._connect() as conn:
            conn.execute("UPDATE papers SET parsed_at=NULL,extracted_at=NULL,chunked_at=NULL,embedded_at=NULL,stored_at=NULL,indexed_at=NULL,last_error=NULL WHERE source_id=?", (source_id,))

    def ids_ready_for(self, stage: str) -> list[str]:
        idx = STAGES.index(stage)
        if idx == 0: raise ValueError("fetched is the entry stage")
        previous = STAGES[idx - 1]
        with self._connect() as conn: rows = conn.execute(f"SELECT source_id FROM papers WHERE {previous}_at IS NOT NULL AND {stage}_at IS NULL").fetchall()
        return [row[0] for row in rows]

    def get(self, source_id: str):
        with self._connect() as conn: return conn.execute("SELECT * FROM papers WHERE source_id=?", (source_id,)).fetchone()

    def all_fetched_ids(self) -> list[str]:
        with self._connect() as conn: return [r[0] for r in conn.execute("SELECT source_id FROM papers WHERE fetched_at IS NOT NULL")]

    def status_summary(self) -> dict[str, int]:
        with self._connect() as conn:
            counts = {stage: conn.execute(f"SELECT COUNT(*) FROM papers WHERE {stage}_at IS NOT NULL").fetchone()[0] for stage in STAGES}
            counts["total"] = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            for level in ("full_text", "abstract_only", "metadata_only", "inaccessible"):
                counts[level] = conn.execute("SELECT COUNT(*) FROM papers WHERE access_level=?", (level,)).fetchone()[0]
            counts["errors"] = conn.execute("SELECT COUNT(*) FROM papers WHERE last_error IS NOT NULL").fetchone()[0]
        return counts

    def iter_records(self):
        with self._connect() as conn: yield from conn.execute("SELECT * FROM papers ORDER BY published DESC,bibcode DESC").fetchall()
