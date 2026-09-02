from __future__ import annotations

import numpy as np


def test_visual_page_record_keeps_page_level_provenance(monkeypatch, tmp_path):
    from config import settings
    from visual.extractor import _page_record, _relative_image_path

    monkeypatch.setattr(settings, "visual_page_text_chars", 12)
    record = {
        "source_id": "ADS:1",
        "bibcode": "2026TEST....1A",
        "title": "A visual search",
        "published": "2026",
        "publication": "Journal",
        "doi": "10.1/test",
        "authors": "Researcher",
        "access_level": "full_text",
        "facilities": "ATA",
    }
    image_path = _relative_image_path(record["bibcode"], 3)
    page = _page_record(record, 3, image_path, "0123456789abcdef", 1000, 1400)

    assert page["visual_id"] == "ADS:1::page:3"
    assert page["page_number"] == 3
    assert page["image_path"].endswith("page-0003.jpg")
    assert page["text"] == "0123456789ab"


def test_visual_embedder_uses_shared_query_space(monkeypatch):
    import visual.embedder as embedder

    class FakeModel:
        def encode(self, values, **kwargs):
            assert values == ["drifting narrowband signal"]
            assert kwargs["prompt"] == embedder.settings.visual_embedding_prompt
            assert kwargs["normalize_embeddings"] is True
            return np.array([[0.25, 0.75]], dtype=np.float32)

    monkeypatch.setattr(embedder, "_model", lambda: FakeModel())
    assert embedder.embed_visual_query("drifting narrowband signal") == [0.25, 0.75]


def test_visual_reranker_accepts_text_and_page_images(monkeypatch, tmp_path):
    import visual.reranker as reranker

    monkeypatch.setattr(reranker.settings, "vector_data_dir", tmp_path)

    class FakeCrossEncoder:
        def predict(self, pairs, **kwargs):
            assert isinstance(pairs[0][1], str)
            assert pairs[1][1]["image"].endswith("visual/pages/paper/page-0002.jpg")
            assert kwargs["prompt"] == reranker.settings.visual_rerank_prompt
            return [0.2, 0.9]

    monkeypatch.setattr(reranker, "_model", lambda: FakeCrossEncoder())
    candidates = [
        {"visual_id": "text", "bibcode": "T", "title": "Text", "text": "evidence", "access_level": "full_text"},
        {"visual_id": "page", "bibcode": "V", "title": "Figure", "text": "caption", "access_level": "full_text", "image_path": "visual/pages/paper/page-0002.jpg"},
    ]
    assert reranker.rerank_multimodal("query", candidates, 1)[0]["visual_id"] == "page"


def test_multimodal_search_survives_a_missing_visual_index(monkeypatch):
    import visual.retriever as retriever

    text = [{"chunk_id": "c1", "source_id": "s1", "bibcode": "B", "title": "Paper", "text": "result"}]
    monkeypatch.setattr(retriever, "_text_search", lambda *args, **kwargs: text)
    monkeypatch.setattr(retriever, "_visual_candidates", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("not built")))
    monkeypatch.setattr(retriever, "rerank_multimodal", lambda question, rows, top_k: rows[:top_k])

    result = retriever.multimodal_search("query", k=1)
    assert result[0]["modality"] == "text"
