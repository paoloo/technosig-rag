"""Real stdio MCP handshake used after deployment."""
from __future__ import annotations
import asyncio
import argparse
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

@asynccontextmanager
async def _transport(root: Path, url: str | None):
    if url:
        async with streamable_http_client(url) as (reader, writer, _):
            yield reader, writer
    else:
        parameters = StdioServerParameters(command=sys.executable, args=[str(root / "mcp_server.py")])
        async with stdio_client(parameters) as streams:
            yield streams

async def main(url: str | None = None, visual: bool = False) -> None:
    root = Path(__file__).resolve().parents[1]
    async with _transport(root, url) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            expected = {"search_literature", "answer_research_question", "explain_rf_data", "corpus_status"}
            if visual:
                expected.update({"search_multimodal_literature", "answer_with_visual_retrieval"})
            missing = expected.difference(names)
            if missing: raise RuntimeError(f"missing MCP tools: {sorted(missing)}")
            status = await session.call_tool("corpus_status", {})
            if status.isError: raise RuntimeError(f"corpus_status failed: {status.content}")
            rendered = " ".join(getattr(part, "text", "") for part in status.content)
            if "2477" not in rendered or "indexed" not in rendered:
                raise RuntimeError(f"unexpected corpus_status payload: {rendered}")
            if visual and "indexed_pages" not in rendered:
                raise RuntimeError(f"visual index missing from corpus_status: {rendered}")
            print({"tools": names, "corpus_status": rendered})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--visual", action="store_true")
    arguments = parser.parse_args()
    asyncio.run(main(arguments.url, arguments.visual))
