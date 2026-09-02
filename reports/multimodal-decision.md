# Text-only versus multimodal RAG

This table is written for pasting into Linear. Values marked **measured** come from the current `dev-coyote1` deployment. Values marked **estimated** must be replaced after the multimodal pilot is indexed and benchmarked.

| Decision area | Stable text-only service (`main`, port 8000) | Multimodal service (`multimodal`, port 8001) | Institutional interpretation |
| --- | --- | --- | --- |
| Research evidence | Searches 47,120 parsed text chunks from 2,477 ADS records | Searches the same text corpus plus rendered, page-level evidence from the 838 available PDFs | Multimodal is more valuable for plots, tables, waterfall diagrams, equations, and instrument schematics; text remains sufficient for ordinary literature synthesis |
| First-stage retrieval | `nomic-embed-text`, 768 dimensions, plus full-text search | Existing text retrieval plus `Qwen3-VL-Embedding-2B`, up to 2,048 dimensions, in a separate visual index | Separate indexes preserve the validated corpus and make A/B evaluation and rollback straightforward |
| Reranking | `Qwen3-Reranker-0.6B` | `Qwen3-VL-Reranker-2B` over both text and page-image candidates | VL reranking can align a text question with visual evidence, but domain evaluation is still required before claiming better scientific retrieval |
| Answer generation | `qwen2.5:14b-instruct` reads retrieved text | The same generator reads text extracted from visually retrieved pages; page images are returned for researcher inspection | Retrieval becomes multimodal, but visual-only claims must still be checked by a person until a validated VL answer model is added |
| Citation precision | ADS bibcode and excerpt | ADS bibcode, page number, excerpt, and page image | Page-level provenance is a meaningful reproducibility improvement for research use |
| GPU capacity | Current reranker uses about 2.8 GiB on GPU 0 (**measured**) | Plan approximately 12–18 GB for both 2B VL models resident, with workload-dependent peaks (**estimated**) | GPU 0 is an RTX 6000 Ada with about 48 GB, so capacity is not the limiting factor |
| Model storage | About 1.2 GB reranker cache plus 274 MB embedding model (**measured**) | About 8.5–10 GB for the two BF16 model caches (**estimated**) | The increase is acceptable on institutional storage, but revisions should be pinned before production use |
| Visual storage | None beyond the original 1.6 GB PDF collection | Approximately 5–20 GB for rendered JPEG pages (**estimated**) | Storage can be reduced later by retaining figures only or lowering render resolution |
| Query latency | Warm retrieval and reranking roughly 0.3–0.9 seconds (**measured**) | Expected to be slower because both models are 2B and images create visual tokens (**estimated**) | Measure cold, warm, and p95 latency on the actual corpus; do not infer production performance from public benchmarks |
| Rebuild cost | Existing index is complete | One-time rendering and embedding of every PDF page; new papers are incremental | This is primarily an ingestion and evaluation cost, not a hardware acquisition problem |
| Failure isolation | Production service and database already validated | Separate source checkout, container, port, model cache usage, and `data/visual` database | The experiment can fail or be removed without modifying the production text database |
| Access and rights | Returns short text excerpts and citations | Can also serve copyrighted page images on the trusted network | Keep port 8001 institutional-only and never publish rendered pages in GitHub |
| Recommended role | Default service for reliable literature questions | Research pilot for visually rich questions and page discovery | Run both for one evaluation cycle; promote multimodal only if visual recall and citation usefulness improve enough to justify latency and maintenance |

## Recommended decision

Keep the text-only service as the production baseline and operate the multimodal service as a research pilot. The pilot should be evaluated with a fixed set of text-only and visually dependent questions, judged by researchers rather than solely by generic model benchmarks.

Promotion criteria should include better Recall@20 or nDCG@10 on visual questions, correct ADS and page citations, acceptable warm and p95 latency, and no regression on text-only questions. The Qwen model cards report strong multimodal retrieval performance and support text, image, screenshot, video, and mixed inputs, but they do not evaluate this technosignature corpus: [Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B), [Qwen3-VL-Reranker-2B](https://huggingface.co/Qwen/Qwen3-VL-Reranker-2B), and the [official implementation](https://github.com/QwenLM/Qwen3-VL-Embedding).
