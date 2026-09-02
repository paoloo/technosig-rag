"""Build vector and lexical indexes for visual page records."""
from __future__ import annotations

from config import settings
from visual.store import get_visual_table


def build_visual_indices() -> dict[str, int]:
    table = get_visual_table()
    count = table.count_rows()
    if count >= 256:
        table.create_index(metric=settings.vector_index_metric, vector_column_name="vector", replace=True)
    table.create_fts_index("text", replace=True)
    return {"indexed_visual_pages": count}
