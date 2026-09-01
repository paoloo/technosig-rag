from __future__ import annotations
import json, logging
from config import settings
from extraction.patterns import extract_tags
from state.manifest import Manifest
logger = logging.getLogger(__name__)

def extract_entities(text: str): return extract_tags(text)

def extract_pending() -> dict[str, int]:
    manifest = Manifest(settings.manifest_path); pending = manifest.ids_ready_for("extracted")
    for source_id in pending:
        record = manifest.get(source_id); stem = record["bibcode"].replace("/", "_")
        try:
            tags = extract_tags((settings.parsed_dir / f"{stem}.md").read_text())
            (settings.parsed_dir / f"{stem}.entities.json").write_text(json.dumps(tags, indent=2))
            manifest.mark_stage(source_id, "extracted")
        except Exception as exc: manifest.record_error(source_id, f"extraction error: {exc}")
    return manifest.status_summary()
