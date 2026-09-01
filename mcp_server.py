"""MCP interface for research agents and complementary RF-data servers."""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
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

def _source(chunk): return {k:chunk.get(k) for k in ("bibcode","title","published","publication","doi","authors","access_level","facilities","data_products","signal_features","retrieval_score")}

@mcp.tool()
def search_literature(query: str, top_k: int = 10, facility: str | None = None, full_text_only: bool = False) -> dict:
    """Retrieve evidence excerpts. Use for literature lookup or to ground another MCP server's RF observations."""
    chunks = hybrid_search(query, k=min(max(top_k,1),30), facility=facility, access_level="full_text" if full_text_only else None)
    return {"query":query,"results":[{"source":_source(c),"excerpt":c["text"]} for c in chunks]}

@mcp.tool()
def answer_research_question(question: str, top_k: int = 10, facility: str | None = None) -> dict:
    """Answer with ADS citations and access-level-aware evidence; suitable for gap and data questions."""
    chunks = hybrid_search(question, k=min(max(top_k,1),30), facility=facility)
    return {"question":question,"answer":generate_answer(question,chunks) if chunks else "No indexed evidence retrieved.","sources":[_source(c) for c in chunks]}

@mcp.tool()
def explain_rf_data(data_description: str, scientific_question: str = "") -> dict:
    """Relate an RF signal/data product from another service to literature, assumptions, methods, and caveats."""
    question = f"Explain this RF data product and relevant technosignature methods: {data_description}. Scientific use: {scientific_question}"
    chunks = hybrid_search(question, k=10); return {"answer":generate_answer(question,chunks) if chunks else "No evidence retrieved.","sources":[_source(c) for c in chunks]}

@mcp.tool()
def corpus_status() -> dict:
    """Return ingestion counts, including access levels and processing stages."""
    return Manifest(settings.manifest_path).status_summary()

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
