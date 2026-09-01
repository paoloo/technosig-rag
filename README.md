# Technosignature Literature RAG

This project builds a local, evidence-first research assistant over the NASA ADS technosignature literature. It collects the corpus, recovers accessible PDFs, parses and chunks the papers, stores searchable vectors in LanceDB, and exposes the result through both a command-line workflow and an MCP server.

The collection starts from this ADS query:

```text
abs:(technosignature OR "technological signature" OR "extraterrestrial intelligence")
OR title:(technosignature OR SETI)
OR keyword:(technosignature OR SETI)
```

## Current corpus

The deployed snapshot contains 2,477 ADS records and 47,120 searchable chunks. Of those records, 838 include recovered PDFs, 676 have full-text access, 1,485 are represented by abstracts, and 316 retain metadata only. The latest run completed without pipeline errors.

See [corpus.md](corpus.md) for the PDF inventory and NASA ADS links. Operational checks and measured timings are recorded in [reports/deployment-validation.md](reports/deployment-validation.md).

## How the pipeline fits together

The workflow is intentionally split into restartable stages:

1. `retrieval/` queries ADS and downloads the best available paper copy.
2. `parsing/` converts PDFs and abstracts into normalized text.
3. `extraction/` tags useful entities and scientific context.
4. `chunking/` creates citation-aware passages with stable identifiers.
5. `embedding/` produces vectors and caches them for repeatable rebuilds.
6. `storage/` writes the corpus to LanceDB.
7. `indexing/` builds the vector and full-text indexes.
8. `query/` combines lexical and semantic retrieval, reranks the evidence, and generates a cited answer.

State is persisted after every batch, so an interrupted collection or indexing run can resume without starting over.

## Models used by the deployed service

The service on `dev-coyote1` uses three models, each for a different job:

- `nomic-embed-text` creates query embeddings through Ollama.
- `Qwen3-Reranker-0.6B` reranks the retrieved passages inside the MCP container. It is pinned to revision `e61197ed45024b0ed8a2d74b80b4d909f1255473` for reproducible deployments.
- `qwen2.5:14b-instruct` generates the final answer and audits its citations through Ollama.

The dedicated reranker replaced the previous use of the 14B generative model for ranking. It reduces warm searches to roughly 0.3–0.9 seconds and avoids loading an approximately 18 GB generative runtime just to score passages. Its cache adds about 1.2 GB to the deployment, and it uses roughly 2.9 GB of GPU memory when loaded. The MCP image is currently about 6 GB because it includes PyTorch and CUDA support; the running container settles near 1.2 GB of system RAM after the reranker has loaded.

The corpus and caches occupy about 4.7 GB outside the image. A GPU is not required for storage, indexing, or serving MCP itself, but it is strongly recommended for the reranker. Final answer generation still depends on a reachable Ollama inference service unless callers request evidence-only search results.

## Configure the environment

Create a virtual environment and install the project dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add a NASA ADS token to `.env`, then make sure the Ollama models are available:

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:14b-instruct
```

Collect and process the corpus:

```bash
python pipeline.py fetch
python pipeline.py process
```

Or run the complete workflow with:

```bash
python pipeline.py run-all
```

Use `python pipeline.py status` to inspect progress. The recovery utilities in `scripts/` can reconcile fallback records or retry PDFs without discarding completed work.

## Query the corpus

For a direct command-line query:

```bash
python pipeline.py query "What observational signatures could reveal a Dyson sphere?"
```

The answer includes numbered citations plus the retrieved evidence. Search can still return evidence if the generation model is unavailable; writing and citation-auditing the final response require the Ollama generation endpoint.

## Run the MCP server

For a local stdio client:

```json
{
  "mcpServers": {
    "technosig-rag": {
      "command": "/absolute/path/to/tecnosig-rag/.venv/bin/python",
      "args": ["/absolute/path/to/tecnosig-rag/mcp_server.py"]
    }
  }
}
```

For a persistent HTTP deployment, `compose.yaml` packages the MCP application as a container while keeping the corpus and model cache on the host. Update its host paths and Ollama address for the target machine, then run:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
```

The current institutional deployment is available on the trusted network at:

```text
http://10.10.1.161:8000/mcp
```

An OpenCode client can connect with:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "technosig-rag": {
      "type": "remote",
      "url": "http://10.10.1.161:8000/mcp",
      "enabled": true,
      "timeout": 120000
    }
  }
}
```

The endpoint currently has no application-level authentication. Keep it on a trusted institutional network or place it behind an authenticated reverse proxy before exposing it more broadly.

## Validate a deployment

Run the unit suite locally:

```bash
pytest tests/unit -q
```

Then exercise the live MCP endpoint:

```bash
python scripts/mcp_smoke.py \
  --url http://10.10.1.161:8000/mcp \
  --query "What observational signatures could reveal a Dyson sphere?"
```

When interpreting answers, remember that a metadata-only record is discoverable by title and bibliographic fields but does not contribute body text. An abstract-only record contributes its abstract, while a full-text record contributes parsed paper passages.

## License

The project code is distributed under the terms in [LICENSE](LICENSE). Source papers and metadata remain subject to their original publishers' and NASA ADS terms.
