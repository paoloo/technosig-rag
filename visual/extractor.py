"""Render citable PDF pages and retain their text and bibliographic context."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from config import settings
from state.manifest import Manifest

logger = logging.getLogger(__name__)


def _stem(bibcode: str) -> str:
    return bibcode.replace("/", "_")


def _relative_image_path(stem: str, page_number: int) -> str:
    return f"visual/pages/{stem}/page-{page_number:04d}.jpg"


def _page_record(record, page_number: int, image_path: str, text: str, width: int, height: int) -> dict:
    return {
        "visual_id": f"{record['source_id']}::page:{page_number}",
        "source_id": record["source_id"],
        "bibcode": record["bibcode"],
        "title": record["title"] or "",
        "published": record["published"] or "",
        "publication": record["publication"] or "",
        "doi": record["doi"] or "",
        "authors": record["authors"] or "",
        "access_level": record["access_level"],
        "facilities": record["facilities"] or "",
        "modality": "page_image",
        "page_number": page_number,
        "image_path": image_path,
        "image_width": width,
        "image_height": height,
        "text": text[: settings.visual_page_text_chars],
    }


def render_paper(record, force: bool = False) -> int:
    """Render one PDF into JPEG pages and a portable JSONL sidecar."""
    import pymupdf

    stem = _stem(record["bibcode"])
    metadata_path = settings.visual_metadata_dir / f"{stem}.jsonl"
    if metadata_path.exists() and not force:
        return sum(1 for line in metadata_path.open() if line.strip())

    pdf_path = Path(record["pdf_path"] or "")
    if not pdf_path.is_file():
        return 0

    page_dir = settings.visual_pages_dir / stem
    page_dir.mkdir(parents=True, exist_ok=True)
    scale = settings.visual_render_dpi / 72.0
    rows: list[dict] = []
    with pymupdf.open(pdf_path) as document:
        for index, page in enumerate(document):
            page_number = index + 1
            image_path = page_dir / f"page-{page_number:04d}.jpg"
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            image_path.write_bytes(pixmap.tobytes("jpeg", jpg_quality=settings.visual_jpeg_quality))
            relative_path = _relative_image_path(stem, page_number)
            rows.append(_page_record(record, page_number, relative_path, page.get_text("text"), pixmap.width, pixmap.height))

    with metadata_path.open("w") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def extract_visual_pages(limit: int | None = None, force: bool = False) -> dict[str, int]:
    manifest = Manifest(settings.manifest_path)
    papers = [record for record in manifest.iter_records() if record["pdf_path"]]
    if limit is not None:
        papers = papers[:limit]
    pages = 0
    completed = 0
    errors = 0
    for record in papers:
        try:
            count = render_paper(record, force=force)
            pages += count
            completed += bool(count)
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning("failed to render %s: %s", record["bibcode"], exc)
    return {"eligible_papers": len(papers), "rendered_papers": completed, "rendered_pages": pages, "errors": errors}


def visual_extraction_status() -> dict[str, int]:
    papers = 0
    pages = 0
    for metadata_path in settings.visual_metadata_dir.glob("*.jsonl"):
        papers += 1
        pages += sum(1 for line in metadata_path.open() if line.strip())
    return {"rendered_papers": papers, "rendered_pages": pages}
