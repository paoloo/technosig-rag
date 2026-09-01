from __future__ import annotations
import logging, typer
from chunking.chunker import chunk_pending
from config import settings
from embedding.embedder import embed_pending
from extraction.entities import extract_pending
from indexing.build_index import build_indices
from parsing.pdf_to_markdown import parse_pending
from retrieval.fetch import export_corpus, fetch_ads
from state.manifest import Manifest
from storage.vector_store import store_pending
app = typer.Typer(add_completion=False); logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

@app.command()
def fetch(metadata_only: bool=False, limit: int|None=None): typer.echo(fetch_ads(metadata_only=metadata_only, limit=limit))
@app.command()
def process():
    for name, fn in (("parse",parse_pending),("extract",extract_pending),("chunk",chunk_pending),("embed",embed_pending),("store",store_pending),("index",build_indices)):
        typer.echo(f"=== {name} ==="); typer.echo(fn())
    export_corpus(Manifest(settings.manifest_path))
@app.command(name="run-all")
def run_all(metadata_only: bool=False, limit: int|None=None): fetch(metadata_only,limit); process()
@app.command()
def status(): typer.echo(Manifest(settings.manifest_path).status_summary())
if __name__ == "__main__": app()
