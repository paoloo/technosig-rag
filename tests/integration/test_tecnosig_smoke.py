"""Live tests for the deployed technosignature corpus and Ollama service."""
from __future__ import annotations
import re
import pytest
pytestmark = pytest.mark.integration

def test_embedding_and_ata_retrieval(skip_if_no_ollama, skip_if_no_table):
    from embedding.embedder import embed_query
    from query.retriever import hybrid_search
    vector = embed_query("ATA narrowband technosignature drift rate")
    assert len(vector) == 768
    results = hybrid_search("Allen Telescope Array technosignature data", k=5, facility="ATA")
    assert len(results) == 5
    assert all(row["source_id"].startswith("ADS:") and row["bibcode"] for row in results)
    assert all("ATA" in row["facilities"] for row in results)

def test_grounded_data_answer_has_ads_citation(skip_if_no_ollama, skip_if_no_table):
    from query.generator import generate_answer
    from query.retriever import hybrid_search
    question = "What is a filterbank data product in radio technosignature searches?"
    answer = generate_answer(question, hybrid_search(question, k=6))
    assert re.search(r"\[ADS:[^\]]+\]", answer)
