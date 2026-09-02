"""MCP interface for research agents and complementary RF-data servers."""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from urllib.parse import quote
from query.generator import generate_answer
from query.retriever import hybrid_search
from state.manifest import Manifest
from config import settings

mcp = FastMCP(
    "Technosignature Literature",
    host=settings.mcp_host,
    port=settings.mcp_port,
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.mcp_allowed_host_list,
        allowed_origins=settings.mcp_allowed_origin_list,
    ),
)

def _source(chunk): return {k:chunk.get(k) for k in ("bibcode","title","published","publication","doi","authors","access_level","facilities","data_products","signal_features","retrieval_score","modality","visual_id","page_number")}

def _visual_url(chunk: dict) -> str | None:
    visual_id = chunk.get("visual_id")
    return f"{settings.visual_base_url.rstrip('/')}/visual/{quote(visual_id, safe='')}" if visual_id else None

@mcp.tool()
def search_literature(query: str, top_k: int = 10, facility: str | None = None, full_text_only: bool = False) -> dict:
    """Retrieve evidence excerpts. Use for literature lookup or to ground another MCP server's RF observations."""
    chunks = hybrid_search(query, k=min(max(top_k,1),30), facility=facility, access_level="full_text" if full_text_only else None)
    return {"query":query,"results":[{"source":_source(c),"excerpt":c["text"]} for c in chunks]}

@mcp.tool()
def search_multimodal_literature(query: str, top_k: int = 10, facility: str | None = None) -> dict:
    """Retrieve text and visually relevant PDF pages with ADS and page-level provenance."""
    from visual.retriever import multimodal_search
    chunks = multimodal_search(query, k=min(max(top_k, 1), 30), facility=facility)
    return {
        "query": query,
        "results": [
            {"source": _source(chunk), "excerpt": chunk["text"], "image_url": _visual_url(chunk)}
            for chunk in chunks
        ],
    }

@mcp.tool()
def answer_research_question(question: str, top_k: int = 10, facility: str | None = None) -> dict:
    """Answer with ADS citations and access-level-aware evidence; suitable for gap and data questions."""
    chunks = hybrid_search(question, k=min(max(top_k,1),30), facility=facility)
    return {"question":question,"answer":generate_answer(question,chunks) if chunks else "No indexed evidence retrieved.","sources":[_source(c) for c in chunks]}

@mcp.tool()
def answer_with_visual_retrieval(question: str, top_k: int = 10, facility: str | None = None) -> dict:
    """Answer from jointly reranked text and PDF pages, returning page images for independent inspection."""
    from visual.retriever import multimodal_search
    chunks = multimodal_search(question, k=min(max(top_k, 1), 30), facility=facility)
    sources = [_source(chunk) | {"image_url": _visual_url(chunk)} for chunk in chunks]
    return {
        "question": question,
        "answer": generate_answer(question, chunks) if chunks else "No indexed evidence retrieved.",
        "sources": sources,
        "interpretation_note": "Qwen3-VL performs retrieval and reranking. The answer model reads extracted page text; inspect the returned page images before relying on visual-only details.",
    }

@mcp.tool()
def explain_rf_data(data_description: str, scientific_question: str = "") -> dict:
    """Relate an RF signal/data product from another service to literature, assumptions, methods, and caveats."""
    question = f"Explain this RF data product and relevant technosignature methods: {data_description}. Scientific use: {scientific_question}"
    chunks = hybrid_search(question, k=10); return {"answer":generate_answer(question,chunks) if chunks else "No evidence retrieved.","sources":[_source(c) for c in chunks]}

@mcp.tool()
def corpus_status() -> dict:
    """Return ingestion counts, including access levels and processing stages."""
    summary = Manifest(settings.manifest_path).status_summary()
    if settings.visual_enabled:
        from visual.extractor import visual_extraction_status
        summary["visual"] = visual_extraction_status()
        try:
            from visual.store import get_visual_table
            summary["visual"]["indexed_pages"] = get_visual_table().count_rows()
        except RuntimeError:
            summary["visual"]["indexed_pages"] = 0
    return summary

@mcp.custom_route("/visual/{visual_id:path}", methods=["GET"])
async def visual_page(request: Request):
    """Serve a retrieved page image from the trusted-network deployment."""
    from visual.store import get_visual_page
    try:
        row = get_visual_page(request.path_params["visual_id"])
    except RuntimeError:
        row = None
    if not row:
        return JSONResponse({"status": "not_found"}, status_code=404)
    root = settings.visual_pages_dir.resolve()
    image_path = (settings.vector_data_dir / row["image_path"]).resolve()
    if not image_path.is_relative_to(root) or not image_path.is_file():
        return JSONResponse({"status": "not_found"}, status_code=404)
    return FileResponse(image_path, media_type="image/jpeg", filename=f"{row['bibcode']}-page-{row['page_number']}.jpg")

@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> JSONResponse:
    """Lightweight container and load-balancer health check."""
    try:
        summary = Manifest(settings.manifest_path).status_summary()
        healthy = summary.get("indexed", 0) == summary.get("total", -1) and summary.get("errors", 1) == 0
        return JSONResponse({"status": "ok" if healthy else "degraded", "corpus": summary}, status_code=200 if healthy else 503)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=503)

if __name__ == "__main__":
    mcp.run(transport=settings.mcp_transport)
