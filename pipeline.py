from __future__ import annotations
import logging, typer
app = typer.Typer(add_completion=False); logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

@app.command()
def fetch(metadata_only: bool=False, limit: int|None=None):
    from retrieval.fetch import fetch_ads
    typer.echo(fetch_ads(metadata_only=metadata_only, limit=limit))
@app.command()
def process():
    from chunking.chunker import chunk_pending
    from config import settings
    from embedding.embedder import embed_pending
    from extraction.entities import extract_pending
    from indexing.build_index import build_indices
    from parsing.pdf_to_markdown import parse_pending
    from retrieval.fetch import export_corpus
    from state.manifest import Manifest
    from storage.vector_store import store_pending
    for name, fn in (("parse",parse_pending),("extract",extract_pending),("chunk",chunk_pending),("embed",embed_pending),("store",store_pending),("index",build_indices)):
        typer.echo(f"=== {name} ==="); typer.echo(fn())
    export_corpus(Manifest(settings.manifest_path))
@app.command(name="visual-extract")
def visual_extract(limit: int|None=None, force: bool=False):
    from visual.extractor import extract_visual_pages
    typer.echo(extract_visual_pages(limit=limit, force=force))
@app.command(name="visual-embed")
def visual_embed(limit: int|None=None, force: bool=False):
    from visual.embedder import embed_visual_pages
    typer.echo(embed_visual_pages(limit=limit, force=force))
@app.command(name="visual-store")
def visual_store(force: bool=False):
    from visual.store import store_visual_pages
    typer.echo(store_visual_pages(force=force))
@app.command(name="visual-index")
def visual_index():
    from visual.index import build_visual_indices
    typer.echo(build_visual_indices())
@app.command(name="visual-process")
def visual_process(limit: int|None=None):
    visual_extract(limit=limit); visual_embed(limit=limit); visual_store(); visual_index()
@app.command(name="run-all")
def run_all(metadata_only: bool=False, limit: int|None=None): fetch(metadata_only,limit); process()
@app.command()
def status():
    from config import settings
    from state.manifest import Manifest
    typer.echo(Manifest(settings.manifest_path).status_summary())
if __name__ == "__main__": app()
