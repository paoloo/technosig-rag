# atadev deployment validation

Validated on 2026-08-31/2026-09-01 at `/mnt/raid1/paolo_tests/tecnosig`.

## Corpus acquisition

- Exact ADS query: `abs:(SETI OR Technosignature)` with `database: astronomy`, sorted by date and bibcode descending.
- ADS results represented in metadata and the manifest: 2,477.
- Validated PDFs: 838/838 files have a `%PDF-` signature and are larger than 1 KiB.
- Primary `atadev` pass: 830 PDFs.
- Berkeley `bl` retry: 102 advertised-but-failed PDF routes attempted; 5 additional PDFs recovered; 97 still unavailable through the advertised routes.
- Final alternate-host/retry pass: 3 additional PDFs recovered; 94 advertised routes remain unavailable after all passes.
- Records with no advertised PDF route: 1,545.
- Final evidence access after text extraction: 676 full text, 1,485 abstract only, 316 metadata only.
- Acquisition and processing errors: 0.

These counts describe access, not paper quality. An ADS result can be a meeting abstract, proposal, book item, or another indexed document type. The query and result count are time-dependent.

## RAG/index

- Parsed, tagged, chunked, embedded, stored, and indexed records: 2,477 at every stage.
- LanceDB rows: 47,120.
- Embedding model: `nomic-embed-text` through the host Ollama GPU service (768 dimensions).
- Generation and citation-audit model: `qwen2.5:14b-instruct`.
- Reranking model: `Qwen/Qwen3-Reranker-0.6B` dedicated cross-encoder.
- Retrieval: dense ANN plus FTS, reciprocal-rank fusion, cross-encoder reranking, and per-paper diversity.
- Gap answers use a second adversarial pass that rejects gaps inferred only from excerpt omission.
- General answers use a second evidence/citation audit.

## Runtime validation

- Unit tests: 9 passed.
- MCP stdio initialization and tool discovery: passed.
- MCP `corpus_status` call: passed.
- Discovered tools: `search_literature`, `answer_research_question`, `explain_rf_data`, `corpus_status`.
- Full-corpus ATA question retrieved ATA-specific full texts and abstracts. The final audited answer correctly concluded that the excerpts did not establish a defensible publishing gap and proposed targeted counterexample searches.
- RF data-product question retrieved the Breakthrough Listen data-format paper and ATA follow-up literature, explaining filterbank axes/metadata, candidate drift, and RFI/beam comparisons.

## Containerized HTTP service

Validated on 2026-09-01:

- Docker Compose service: `tecnosig-rag-mcp`
- Bind address: `10.10.1.161:8000`
- Health endpoint: `GET /healthz` returned `status=ok` and 2,477/2,477 indexed records.
- MCP endpoint: `POST /mcp` negotiated protocol version `2025-06-18` from the Mac.
- Direct tool discovery returned all four expected tools.
- Direct `corpus_status` returned the full validated coverage with zero errors.
- A direct full-text ATA literature search from the Mac completed through the container's LanceDB mount and host Ollama service.
- OpenCode 1.18.20 reported `technosignature-literature` as connected using the remote MCP URL.

The service is bound to the institutional interface and currently has no
application-layer authentication. It must remain on the trusted network until
an HTTPS reverse proxy and institutional authentication are added.

## Dedicated reranker validation

Validated on 2026-09-01:

- Previous cold retrieval-only search with 14B listwise reranking: 16.75 s and an 18 GB Ollama runtime allocation.
- Qwen3 reranker first pinned-model GPU search after container restart: 10.42 s.
- Subsequent representative searches: 0.30-0.88 s.
- Observed reranker GPU memory: about 2.9 GB on a dedicated RTX 6000 Ada.
- Observed MCP container memory after model load: about 1.2 GB.
- The same model on CPU was rejected after a 40.34 s warm query that saturated roughly 53 CPU cores.
- Representative ATA, filterbank-format, and infrared/Dyson-sphere queries returned directly relevant papers.
- A full answer request completed with inline ADS citations; Qwen 2.5 14B remains responsible for synthesis and citation auditing.

## Known limits

- This is a broad ADS query corpus, not a systematic review. Retrieval cannot prove a field-wide absence.
- Publisher authentication and bot defenses prevented some automated downloads on both institutional networks.
- Downloaded legacy scans with neither extractable text nor an ADS abstract remain metadata-only; their files are preserved for manual OCR if a research question requires them.
- Repeated very short metadata/abstract vectors caused harmless empty-cluster warnings during ANN training; index construction completed.
