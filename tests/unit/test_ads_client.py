from retrieval.ads_client import arxiv_id, candidate_urls, safe_stem

def test_arxiv_direct_precedes_gateway():
    doc = {"bibcode":"2024ApJ...1A", "identifier":["arXiv:2401.01234"], "esources":["PUB_PDF","EPRINT_PDF"]}
    candidates = candidate_urls(doc)
    assert candidates[0][0] == "ARXIV_WWW"
    assert candidates[1][0] == "ARXIV_EXPORT"
    assert any(source == "EPRINT_PDF" for source, _ in candidates)

def test_safe_bibcode_filename():
    assert "/" not in safe_stem("A/B:C")
