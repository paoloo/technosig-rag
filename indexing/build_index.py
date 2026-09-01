from __future__ import annotations
from config import settings
from state.manifest import Manifest
from storage.vector_store import get_table

def build_indices() -> dict[str, int]:
    table = get_table(); n = table.count_rows()
    if n >= 256: table.create_index(metric=settings.vector_index_metric, vector_column_name="vector", replace=True)
    table.create_fts_index("text", replace=True)
    manifest = Manifest(settings.manifest_path); manifest.mark_all_indexed(); return manifest.status_summary()
