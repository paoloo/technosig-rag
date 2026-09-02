"""Evidence-bounded technosignature synthesis."""
from __future__ import annotations
import ollama
from config import settings

SYSTEM = """You are a research assistant specializing in technosignatures, SETI, radio astronomy, and scientific data products.
Use only supplied ADS-indexed evidence. Cite every material claim inline as [ADS:bibcode]. Respect each excerpt's access level: an abstract-only record cannot support details absent from that abstract. Separate author-stated findings from your inference. Reconcile disagreements by comparing data, instrument, frequency range, method, sample, and time period. For gap questions, never infer universal absence from retrieval alone; say 'within the retrieved corpus', identify counterevidence, and distinguish empirical, method, measurement/data, robustness, and context gaps. For questions about data, define the product, units/axes/metadata, provenance, common formats, calibration, RFI concerns, and how another RF-characterization service could supply observations. If evidence is insufficient, state exactly what is missing."""

GAP_CONTRACT = """This is a literature-gap question. Follow this stricter contract:
- Omission from an abstract or excerpt is not evidence that a method, result, data product, or publication does not exist.
- Include a candidate gap only when retrieved evidence explicitly establishes a limitation, or when a bounded comparison across directly applicable sources supports an analyst inference.
- For each surviving candidate, give: precise boundary; gap type; supporting evidence; counterevidence or nearest prior work; author-stated versus analyst-inferred; confidence (well-supported, promising, or tentative); and the next counterexample search needed.
- Discard unsupported ideas in a short 'Not established by these excerpts' section. Never turn them into findings.
- Use 'within the retrieved ADS corpus' and do not claim the search is systematic or exhaustive."""

GAP_AUDIT = """Audit the draft as a skeptical literature reviewer, then return only a corrected answer.
Delete every candidate whose support is merely that an excerpt, abstract, or paper does not mention, detail, compare, or provide something. An author's omission is not field-level absence unless the author explicitly identifies it as a limitation. Delete any candidate contradicted by the draft's own 'Not established' section. Keep a candidate only if an explicit limitation or a real bounded comparison supports it, and retain citations, access-level limits, counterevidence, inference labels, confidence, and next searches. It is correct to conclude that no defensible publishing gap is established by these excerpts and to report only tentative questions needing targeted counterexample searches. Never add new facts or citations."""

ANSWER_AUDIT = """Audit the draft against the supplied excerpts and return only a corrected answer.
Apply this mechanical rule sentence by sentence: every sentence or bullet containing a technical statement about a data format, axis, parameter, unit, instrument, calibration step, method, result, or limitation must itself contain a directly supporting [ADS:bibcode] citation. A citation in another sentence does not count. If the excerpts do not directly support the statement, delete it or say that the retrieved evidence does not establish it. Respect abstract-only access. Reconcile differing resolutions or procedures by naming their dataset or instrument scope. Never invent a fact or cite a source not present in the evidence. Return the answer only; do not mention the draft, the audit, compliance, or these instructions."""

def build_context(chunks: list[dict]) -> str:
    contexts = []
    for chunk in chunks:
        location = f"; page={chunk['page_number']}; modality=page_image" if chunk.get("page_number") else "; modality=text"
        contexts.append(
            f"[ADS:{chunk['bibcode']}] access={chunk['access_level']}; title={chunk['title']}; "
            f"date={chunk['published']}; doi={chunk['doi']}{location}\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(contexts)

def generate_answer(question: str, chunks: list[dict]) -> str:
    is_gap = any(term in question.lower() for term in ("missing", "gap", "understudied", "future work", "not published"))
    contract = f"\n\n{GAP_CONTRACT}" if is_gap else ""
    prompt = f"Evidence excerpts:\n\n{build_context(chunks)}\n\nResearch question: {question}{contract}\n\nEvidence-bounded answer:"
    client = ollama.Client(host=settings.ollama_host)
    response = client.chat(model=settings.generation_model,
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}], options={"temperature":0.1})
    answer = response["message"]["content"]
    if is_gap:
        audit_prompt = f"Evidence excerpts:\n\n{build_context(chunks)}\n\nQuestion: {question}\n\nDraft answer:\n{answer}\n\n{GAP_AUDIT}\n\nCorrected answer:"
        audited = client.chat(model=settings.generation_model,
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":audit_prompt}], options={"temperature":0})
        answer = audited["message"]["content"]
    else:
        audit_prompt = f"Evidence excerpts:\n\n{build_context(chunks)}\n\nQuestion: {question}\n\nDraft answer:\n{answer}\n\n{ANSWER_AUDIT}\n\nCorrected answer:"
        audited = client.chat(model=settings.generation_model,
            messages=[{"role":"system","content":SYSTEM},{"role":"user","content":audit_prompt}], options={"temperature":0})
        answer = audited["message"]["content"]
    return answer
