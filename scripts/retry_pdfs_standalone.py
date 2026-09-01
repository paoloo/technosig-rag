"""Retry unresolved ADS PDF routes from a second institutional network.

Uses only the Python standard library so it can run on a clean SSH host.
Metadata JSON files are updated with `fallback_download_*` fields and copied
back with the validated PDFs for reconciliation on the primary host.
"""
from __future__ import annotations
import argparse, json, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PRIORITY = ("EPRINT_PDF", "AUTHOR_PDF", "ADS_PDF", "PMC_PDF", "PUB_PDF", "ADS_SCAN")

def safe_stem(value): return re.sub(r"[^A-Za-z0-9._-]", "_", value)
def arxiv_id(doc):
    for identifier in doc.get("identifier", []):
        if match := re.search(r"(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+/\d{7}(?:v\d+)?)$", identifier, re.I): return match.group(1)
    return None
def candidates(doc):
    bibcode = urllib.parse.quote(doc["bibcode"], safe=""); available = {x.upper() for x in doc.get("esources", [])}
    result = [(s, f"https://ui.adsabs.harvard.edu/link_gateway/{bibcode}/{s}") for s in PRIORITY if s in available]
    if aid := arxiv_id(doc):
        result.insert(0, ("ARXIV_EXPORT", f"https://export.arxiv.org/pdf/{aid}"))
        result.insert(0, ("ARXIV_WWW", f"https://arxiv.org/pdf/{aid}"))
    return result
def is_pdf(path):
    try:
        with path.open("rb") as f: return path.stat().st_size > 1024 and f.read(5) == b"%PDF-"
    except OSError: return False
def acquire(item):
    path, output_dir, timeout = item; doc = json.loads(path.read_text()); destination = output_dir / f"{safe_stem(doc['bibcode'])}.pdf"; attempts=[]
    for source, url in candidates(doc):
        try:
            request = urllib.request.Request(url, headers={"User-Agent":"tecnosig-rag/1.0 (research corpus acquisition)"})
            temp = destination.with_suffix(".pdf.part")
            with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as output:
                final_url=response.geturl(); content_type=response.headers.get("Content-Type","")
                while chunk := response.read(1024*1024): output.write(chunk)
            if is_pdf(temp):
                temp.replace(destination); attempts.append({"source":source,"status":"downloaded","url":final_url}); doc.update(access_level="full_text",fallback_download_source=source,fallback_download_attempts=attempts); path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)); return doc["bibcode"], True
            attempts.append({"source":source,"status":"not_pdf","content_type":content_type,"url":final_url})
        except Exception as exc: attempts.append({"source":source,"status":"error","error":f"{type(exc).__name__}: {exc}"[:500]})
        finally:
            if 'temp' in locals(): temp.unlink(missing_ok=True)
    doc["fallback_download_attempts"] = attempts; path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)); return doc["bibcode"], False
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("metadata_dir",type=Path); parser.add_argument("output_dir",type=Path); parser.add_argument("--workers",type=int,default=8); parser.add_argument("--timeout",type=int,default=45); args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    paths=[]
    for path in args.metadata_dir.glob("*.json"):
        doc=json.loads(path.read_text())
        if doc.get("access_level") != "full_text" and candidates(doc): paths.append(path)
    with ThreadPoolExecutor(max_workers=args.workers) as pool: results=list(pool.map(acquire, ((p,args.output_dir,args.timeout) for p in paths)))
    summary={"attempted":len(results),"downloaded":sum(ok for _,ok in results),"failed":sum(not ok for _,ok in results),"downloaded_bibcodes":[b for b,ok in results if ok]}
    (args.output_dir.parent / "fallback-summary.json").write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
if __name__ == "__main__": main()
