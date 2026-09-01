"""Real stdio MCP handshake used after deployment."""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parameters = StdioServerParameters(command=sys.executable, args=[str(root / "mcp_server.py")])
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            expected = {"search_literature", "answer_research_question", "explain_rf_data", "corpus_status"}
            missing = expected.difference(names)
            if missing: raise RuntimeError(f"missing MCP tools: {sorted(missing)}")
            status = await session.call_tool("corpus_status", {})
            if status.isError: raise RuntimeError(f"corpus_status failed: {status.content}")
            rendered = " ".join(getattr(part, "text", "") for part in status.content)
            if "2477" not in rendered or "indexed" not in rendered:
                raise RuntimeError(f"unexpected corpus_status payload: {rendered}")
            print({"tools": names, "corpus_status": rendered})

if __name__ == "__main__": asyncio.run(main())
