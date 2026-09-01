"""Fetch the exact ADS technosignature corpus and preserve provenance."""
from __future__ import annotations
import json, logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from config import settings
from retrieval import ads_client
from state.manifest import Manifest, PaperRecord
logger = logging.getLogger(__name__)

def _joined(value) -> str: return json.dumps(value or [], ensure_ascii=False)

def _write_research_artifacts(docs: list[dict], total: int) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw = settings.research_dir / "search" / f"ads-{stamp}.jsonl"
    raw.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs))
    (settings.research_dir / "search-log.md").write_text(
        f"# Search log\n\n- Executed (UTC): {datetime.now(timezone.utc).isoformat()}\n- Source: NASA ADS, astronomy database\n"
        f"- Exact query: `{settings.ads_query}`\n- Filter: `{settings.ads_database_filter}`\n"
        f"- Sort: `date desc,bibcode desc`\n- Results reported: {total}\n- Raw records: `{raw.name}`\n")

def fetch_ads(*, metadata_only: bool = False, limit: int | None = None) -> dict[str, int]:
    docs, total = ads_client.search_all(); _write_research_artifacts(docs, total); manifest = Manifest(settings.manifest_path)
    selected = docs[:limit] if limit else docs
    def acquire(doc):
        if metadata_only: return doc, None, []
        destination = settings.pdf_dir / f"{ads_client.safe_stem(doc['bibcode'])}.pdf"
        source, attempts = ads_client.download_pdf(doc, destination)
        return doc, source, attempts
    with ThreadPoolExecutor(max_workers=settings.download_workers) as executor:
      for index, (doc, source, attempts) in enumerate(executor.map(acquire, selected), 1):
        bibcode, source_id = doc["bibcode"], f"ADS:{doc['bibcode']}"
        previous = manifest.get(source_id)
        stem = ads_client.safe_stem(bibcode); meta_path = settings.metadata_dir / f"{stem}.json"; pdf_path = settings.pdf_dir / f"{stem}.pdf"
        abstract = doc.get("abstract") or ""; access = "full_text" if source else ("abstract_only" if abstract else "metadata_only")
        if source == "existing" and previous and previous["parsed_at"] and previous["pdf_path"]:
            access = previous["access_level"]
        old_meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        preserved_fallback = {key: old_meta[key] for key in ("fallback_download_source", "fallback_download_attempts") if key in old_meta}
        effective_source = previous["download_source"] if source == "existing" and previous else source
        effective_attempts = previous["attempted_sources"] if source == "existing" and previous else json.dumps(attempts, ensure_ascii=False)
        meta_path.write_text(json.dumps({**doc, **preserved_fallback, "ads_query": settings.ads_query, "access_level": access, "download_source": effective_source, "download_attempts": json.loads(effective_attempts or "[]")}, indent=2, ensure_ascii=False))
        manifest.upsert_fetched(PaperRecord(source_id=source_id, bibcode=bibcode,
            title=(doc.get("title") or [""])[0], abstract=abstract, authors=_joined(doc.get("author")),
            published=doc.get("pubdate") or doc.get("date"), updated=doc.get("entdate"), publication=doc.get("pub"),
            doctype=doc.get("doctype"), doi=_joined(doc.get("doi")), identifiers=_joined(doc.get("identifier")),
            properties=_joined(doc.get("property")), esources=_joined(doc.get("esources")), facilities=_joined(doc.get("facility")),
            keywords=_joined(doc.get("keyword")), pdf_path=str(pdf_path) if source else None, meta_path=str(meta_path),
            access_level=access, download_source=effective_source, attempted_sources=effective_attempts))
        if source and previous and not previous["pdf_path"]:
            manifest.reset_processing(source_id)
        if index % 25 == 0: logger.info("acquired %d/%d ADS records", index, len(selected))
    export_corpus(manifest); return manifest.status_summary()

def export_corpus(manifest: Manifest) -> None:
    with (settings.research_dir / "corpus.jsonl").open("w") as handle:
        for row in manifest.iter_records():
            record = dict(row); record["provenance"] = "NASA ADS"; handle.write(json.dumps(record, ensure_ascii=False) + "\n")
