from __future__ import annotations
import json, typer
from query.generator import generate_answer
from query.retriever import hybrid_search
app = typer.Typer(add_completion=False)

@app.command()
def ask(question: str, top_k: int = 10, facility: str | None = None, json_output: bool = False, multimodal: bool = False):
    if multimodal:
        from visual.retriever import multimodal_search
        chunks = multimodal_search(question, k=top_k, facility=facility)
    else:
        chunks = hybrid_search(question, k=top_k, facility=facility)
    answer = generate_answer(question, chunks) if chunks else "No indexed evidence was retrieved."
    sources = [{k:c.get(k) for k in ("bibcode","title","published","doi","access_level","retrieval_score","modality","page_number","image_path")} for c in chunks]
    typer.echo(json.dumps({"answer":answer,"sources":sources}, indent=2) if json_output else answer + "\n\nSources:\n" + "\n".join(f"- ADS:{s['bibcode']} [{s['access_level']}] {s['title']}" for s in sources))

@app.command()
def chat():
    while True:
        try: question = typer.prompt("technosig>")
        except (EOFError, KeyboardInterrupt): break
        if question.lower().strip() in {"exit","quit"}: break
        ask(question)
if __name__ == "__main__": app()
