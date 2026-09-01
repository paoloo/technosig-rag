from __future__ import annotations
import json, logging
from semantic_text_splitter import MarkdownSplitter
from config import settings
from extraction.patterns import extract_tags
from state.manifest import Manifest
logger = logging.getLogger(__name__)

def _splitter():
    try: return MarkdownSplitter.from_tiktoken_model("gpt-3.5-turbo", (settings.chunk_min_tokens, settings.chunk_max_tokens), overlap=settings.chunk_overlap_tokens)
    except TypeError: return MarkdownSplitter.from_tiktoken_model("gpt-3.5-turbo", settings.chunk_max_tokens)

def chunk_pending() -> dict[str, int]:
    manifest = Manifest(settings.manifest_path); splitter = _splitter()
    for source_id in manifest.ids_ready_for("chunked"):
        record = manifest.get(source_id); stem = record["bibcode"].replace("/", "_")
        try:
            pieces = splitter.chunks((settings.parsed_dir / f"{stem}.md").read_text())
            with (settings.chunks_dir / f"{stem}.jsonl").open("w") as output:
                for i, piece in enumerate(pieces):
                    row = {"chunk_id": f"{source_id}::{i}", "source_id": source_id, "bibcode": record["bibcode"],
                        "chunk_index": i, "title": record["title"], "published": record["published"], "publication": record["publication"],
                        "doi": record["doi"], "authors": record["authors"], "access_level": record["access_level"], "text": piece, **extract_tags(piece)}
                    output.write(json.dumps(row, ensure_ascii=False) + "\n")
            manifest.mark_stage(source_id, "chunked")
        except Exception as exc: manifest.record_error(source_id, f"chunk error: {exc}")
    return manifest.status_summary()
