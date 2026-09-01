"""NASA ADS search and full-text acquisition with auditable fallbacks."""
from __future__ import annotations
import json, os, re, time, urllib.parse, urllib.request
from pathlib import Path
from config import settings

SEARCH_URL = "https://api.adsabs.harvard.edu/v1/search/query"
GATEWAY = "https://ui.adsabs.harvard.edu/link_gateway/{bibcode}/{source}"
FIELDS = "bibcode,title,abstract,author,date,pub,pubdate,doctype,doi,identifier,property,esources,facility,keyword,entdate"
SOURCE_PRIORITY = ("EPRINT_PDF", "AUTHOR_PDF", "ADS_PDF", "PMC_PDF", "PUB_PDF", "ADS_SCAN")

def _request(url: str, *, token: str = "", timeout: int | None = None):
    headers = {"User-Agent": "tecnosig-rag/1.0 (research corpus acquisition)"}
    if token: headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout or settings.download_timeout_seconds)

def search_all() -> tuple[list[dict], int]:
    token = settings.ads_api_token or os.environ.get("ADS_API_TOKEN", "")
    if not token: raise RuntimeError("ADS_API_TOKEN is required")
    docs, start, total = [], 0, 1
    while start < total:
        params = urllib.parse.urlencode({"q": settings.ads_query, "fq": settings.ads_database_filter,
            "fl": FIELDS, "rows": settings.ads_rows_per_page, "start": start, "sort": "date desc,bibcode desc"})
        with _request(f"{SEARCH_URL}?{params}", token=token) as response: payload = json.load(response)
        total = int(payload["response"]["numFound"]); page = payload["response"]["docs"]; docs.extend(page)
        if not page: break
        start += len(page)
    return docs, total

def safe_stem(bibcode: str) -> str: return re.sub(r"[^A-Za-z0-9._-]", "_", bibcode)

def arxiv_id(doc: dict) -> str | None:
    for identifier in doc.get("identifier", []):
        match = re.search(r"(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+/\d{7}(?:v\d+)?)$", identifier, re.I)
        if match: return match.group(1)
    return None

def candidate_urls(doc: dict) -> list[tuple[str, str]]:
    bibcode = urllib.parse.quote(doc["bibcode"], safe="")
    available = {x.upper() for x in doc.get("esources", [])}
    candidates = [(source, GATEWAY.format(bibcode=bibcode, source=source)) for source in SOURCE_PRIORITY if source in available]
    if aid := arxiv_id(doc):
        # The two arXiv frontends fail independently on institutional hosts.
        # Try the main endpoint before export.arxiv.org, then ADS's gateway.
        candidates.insert(0, ("ARXIV_EXPORT", f"https://export.arxiv.org/pdf/{aid}"))
        candidates.insert(0, ("ARXIV_WWW", f"https://arxiv.org/pdf/{aid}"))
    return candidates

def _is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as handle: return path.stat().st_size > 1024 and handle.read(5) == b"%PDF-"
    except OSError: return False

def download_pdf(doc: dict, destination: Path) -> tuple[str | None, list[dict]]:
    if destination.exists() and _is_pdf(destination): return "existing", []
    attempts, temp = [], destination.with_suffix(".pdf.part")
    for source, url in candidate_urls(doc):
        for retry in range(settings.download_retries + 1):
            try:
                with _request(url) as response, temp.open("wb") as output:
                    content_type = response.headers.get("Content-Type", "")
                    final_url = response.geturl()
                    while chunk := response.read(1024 * 1024): output.write(chunk)
                if _is_pdf(temp):
                    temp.replace(destination); attempts.append({"source": source, "status": "downloaded", "url": final_url}); return source, attempts
                attempts.append({"source": source, "status": "not_pdf", "content_type": content_type, "url": final_url})
                # HTML/login/bot responses are deterministic for this route;
                # retrying the same non-PDF wastes a worker and cannot create a PDF.
                break
            except Exception as exc:
                attempts.append({"source": source, "status": "error", "error": f"{type(exc).__name__}: {exc}"[:500]})
                if retry < settings.download_retries: time.sleep(1 + retry)
            finally: temp.unlink(missing_ok=True)
    return None, attempts
