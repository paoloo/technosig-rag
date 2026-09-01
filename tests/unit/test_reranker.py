from __future__ import annotations


def test_cross_encoder_rerank_uses_descending_scores(monkeypatch):
    import query.reranker as reranker

    class FakeCrossEncoder:
        def predict(self, pairs, batch_size, show_progress_bar):
            assert [pair[0] for pair in pairs] == ["target"] * 3
            assert batch_size == reranker.settings.rerank_batch_size
            assert show_progress_bar is False
            return [0.2, 0.9, 0.4]

    chunks = [
        {"chunk_id": str(index), "bibcode": f"B{index}", "access_level": "full_text", "title": f"T{index}", "text": f"E{index}"}
        for index in range(3)
    ]
    monkeypatch.setattr(reranker, "_cross_encoder", lambda: FakeCrossEncoder())
    assert [row["chunk_id"] for row in reranker._cross_encoder_rerank("target", chunks, 2)] == ["1", "2"]


def test_rerank_falls_back_to_fused_order(monkeypatch):
    import query.reranker as reranker

    chunks = [
        {"chunk_id": str(index), "bibcode": f"B{index}", "access_level": "full_text", "title": f"T{index}", "text": f"E{index}"}
        for index in range(3)
    ]
    monkeypatch.setattr(reranker.settings, "rerank_backend", "cross-encoder")
    monkeypatch.setattr(reranker, "_cross_encoder_rerank", lambda *_: (_ for _ in ()).throw(RuntimeError("offline")))
    assert reranker.rerank("target", chunks, 2) == chunks[:2]
