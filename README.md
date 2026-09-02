# Technosignature Literature RAG

This project builds a local, evidence-first research assistant over the NASA ADS technosignature literature. It collects the corpus, recovers accessible PDFs, parses and chunks the papers, stores searchable vectors in LanceDB, and exposes the result through both a command-line workflow and an MCP server.

This `multimodal` branch extends the stable text-only implementation on `main`. It keeps the validated text database intact and builds a sidecar visual index from rendered PDF pages. Both versions can run together: text-only on port 8000 and multimodal on port 8001. See the [institutional decision table](reports/multimodal-decision.md) for the expected benefits and costs.

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
9. `visual/` renders citable PDF pages, embeds them with Qwen3-VL, and jointly reranks page images and text without modifying the original index.

State is persisted after every batch, so an interrupted collection or indexing run can resume without starting over.

## Models used by the deployed service

The service on `dev-coyote1` uses three models, each for a different job:

- `nomic-embed-text` creates query embeddings through Ollama.
- `Qwen3-Reranker-0.6B` reranks the retrieved passages inside the MCP container. It is pinned to revision `e61197ed45024b0ed8a2d74b80b4d909f1255473` for reproducible deployments.
- `qwen2.5:14b-instruct` generates the final answer and audits its citations through Ollama.

The multimodal branch adds `Qwen3-VL-Embedding-2B` for page-image retrieval and `Qwen3-VL-Reranker-2B` for joint text/image ranking. Their caches and vectors are independent from the text-only models. The answer generator still consumes extracted page text, so every returned page image should be inspected before relying on a visual-only detail.

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

Build a small visual pilot before processing the full PDF collection:

```bash
python pipeline.py visual-process --limit 100
python -m query.cli ask \
  "Find waterfall plots showing drifting narrowband signals" \
  --multimodal
```

The restartable commands `visual-extract`, `visual-embed`, `visual-store`, and `visual-index` can also be run separately. Generated page images, vectors, and the visual LanceDB database live under `data/visual/` and remain outside Git.

## Query the corpus

For a direct command-line query:

```bash
python -m query.cli ask "What observational signatures could reveal a Dyson sphere?"
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

For a persistent HTTP deployment, `compose.yaml` packages the multimodal MCP application as a second container while keeping the corpus and model cache on the host. Update its host paths and Ollama address for the target machine, then run:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://10.10.1.161:8001/healthz
```

The stable and experimental endpoints are:

```text
Text-only:  http://10.10.1.161:8000/mcp
Multimodal: http://10.10.1.161:8001/mcp
```

An OpenCode client can connect with:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "technosig-rag-visual": {
      "type": "remote",
      "url": "http://10.10.1.161:8001/mcp",
      "enabled": true,
      "timeout": 120000
    }
  }
}
```

The endpoint currently has no application-level authentication. Keep it on a trusted institutional network or place it behind an authenticated reverse proxy before exposing it more broadly.

The visual server adds `search_multimodal_literature` and `answer_with_visual_retrieval`. Results include ADS metadata, page numbers, extracted page text, and trusted-network URLs for inspecting retrieved page images.

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

## Citing this project

If this software supports your research, please cite:

> João Paolo Cavalcante Martins Oliveira. (2026). *Technosignature Literature RAG* [Computer software]. SETI Institute. https://github.com/paoloo/technosig-rag

GitHub can also generate a citation in several formats from [CITATION.cff](CITATION.cff). The citation metadata includes the author's [ORCID record](https://orcid.org/0000-0003-4117-953X).

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), follow the [Code of Conduct](CODE_OF_CONDUCT.md), and report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## License

The project code is distributed under the terms in [LICENSE](LICENSE). Source papers and metadata remain subject to their original publishers' and NASA ADS terms.
