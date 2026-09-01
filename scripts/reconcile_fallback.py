"""Reconcile validated PDFs returned by a fallback host into the manifest."""
from __future__ import annotations
import json, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import settings
from retrieval.ads_client import safe_stem
from retrieval.fetch import export_corpus
from state.manifest import Manifest

def main() -> None:
    changed=[]
    with sqlite3.connect(settings.manifest_path) as connection:
        for meta_path in settings.metadata_dir.glob("*.json"):
            doc=json.loads(meta_path.read_text()); bibcode=doc["bibcode"]
            pdf_path=settings.pdf_dir / f"{safe_stem(bibcode)}.pdf"
            if doc.get("fallback_download_source") and pdf_path.exists():
                row=connection.execute("SELECT access_level FROM papers WHERE bibcode=?",(bibcode,)).fetchone()
                if row and row[0] != "full_text":
                    connection.execute("UPDATE papers SET access_level='full_text',pdf_path=?,download_source=?,attempted_sources=? WHERE bibcode=?",
                        (str(pdf_path),f"bl:{doc['fallback_download_source']}",json.dumps(doc.get("fallback_download_attempts",[])),bibcode)); changed.append(bibcode)
        connection.commit()
    manifest=Manifest(settings.manifest_path); export_corpus(manifest)
    print(json.dumps({"reconciled":len(changed),"bibcodes":changed,"status":manifest.status_summary()},indent=2))
if __name__ == "__main__": main()
