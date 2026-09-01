from state.manifest import Manifest, PaperRecord

def test_access_levels_and_idempotent_stages(tmp_path):
    m = Manifest(tmp_path / "manifest.sqlite3")
    m.upsert_fetched(PaperRecord(source_id="ADS:X", bibcode="X", title="Paper", access_level="abstract_only"))
    assert m.status_summary()["abstract_only"] == 1
    assert m.ids_ready_for("parsed") == ["ADS:X"]
    m.mark_stage("ADS:X", "parsed")
    assert m.status_summary()["parsed"] == 1
    m.upsert_fetched(PaperRecord(source_id="ADS:X", bibcode="X", title="Updated", access_level="full_text"))
    assert m.status_summary()["total"] == 1
    assert m.status_summary()["parsed"] == 1
    assert m.status_summary()["full_text"] == 1

def test_new_full_text_can_reset_derived_stages(tmp_path):
    m = Manifest(tmp_path / "manifest.sqlite3")
    m.upsert_fetched(PaperRecord(source_id="ADS:Y", bibcode="Y", access_level="abstract_only"))
    m.mark_stage("ADS:Y", "parsed")
    m.mark_stage("ADS:Y", "extracted")
    m.reset_processing("ADS:Y")
    assert m.ids_ready_for("parsed") == ["ADS:Y"]
    assert m.status_summary()["parsed"] == 0
