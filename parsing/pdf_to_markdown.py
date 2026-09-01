"""PDF parsing with honest abstract-only fallback."""
from __future__ import annotations
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import pymupdf4llm
from config import settings
from state.manifest import Manifest
logger = logging.getLogger(__name__)

def parse_one(source_id: str, pdf_path: str, abstract: str = "", title: str = "") -> tuple[str, str]:
    # Recent pymupdf4llm releases activate a neural layout/OCR model by
    # default. Most astronomy PDFs already contain high-quality text, so the
    # classic structured extractor is substantially faster and more faithful
    # than re-OCR. Fall back to layout/OCR only for likely scans.
    pymupdf4llm.use_layout(False)
    text = pymupdf4llm.to_markdown(pdf_path)
    # A one-page meeting abstract may legitimately contain only a few hundred
    # characters. OCR only near-empty extraction, not merely short documents.
    if len(text.strip()) < 50 and abstract:
        logger.info("near-empty PDF %s; indexing supplied ADS abstract", source_id)
        return f"# {title}\n\n## Abstract\n\n{abstract}", "abstract_only"
    if len(text.strip()) < 50:
        logger.info("near-empty PDF %s without ADS abstract; indexing metadata only", source_id)
        return f"# {title}\n\nMetadata-only record {source_id}; the downloaded PDF had no extractable text.", "metadata_only"
    return text, "full_text"

def parse_pending() -> dict[str, int]:
    manifest = Manifest(settings.manifest_path)
    tasks = []
    for source_id in manifest.ids_ready_for("parsed"):
        record = manifest.get(source_id); stem = record["bibcode"].replace("/", "_")
        tasks.append((source_id, stem, record["pdf_path"], record["abstract"] or "", record["title"] or "", record["bibcode"]))
    # PyMuPDF's optional native layout engine is not fork-safe. Spawn gives
    # each worker clean native state; two workers also bound OCR memory use.
    with ProcessPoolExecutor(max_workers=settings.parser_workers, mp_context=multiprocessing.get_context("spawn")) as executor:
      for source_id, stem, text, effective_access, error in executor.map(_parse_task, tasks):
        try:
            if error:
                raise RuntimeError(error)
            if effective_access:
                manifest.set_access_level(source_id, effective_access)
            (settings.parsed_dir / f"{stem}.md").write_text(text)
            manifest.mark_stage(source_id, "parsed")
        except Exception as exc: manifest.record_error(source_id, f"parse error: {exc}")
    return manifest.status_summary()

def _parse_task(task):
    source_id, stem, pdf_path, abstract, title, bibcode = task
    try:
        if pdf_path:
            text, effective_access = parse_one(source_id, pdf_path, abstract, title)
        elif abstract:
            text, effective_access = f"# {title}\n\n## Abstract\n\n{abstract}", None
        else:
            text, effective_access = f"# {title}\n\nMetadata-only ADS record {bibcode}.", None
        return source_id, stem, text, effective_access, None
    except Exception as exc:
        return source_id, stem, "", None, f"{type(exc).__name__}: {exc}"
