from pathlib import Path
from config import Settings
from extraction.patterns import extract_tags

def test_requested_pdf_path(tmp_path):
    s = Settings(vector_data_dir=tmp_path / "tecnosig")
    assert s.pdf_dir == tmp_path / "tecnosig" / "pdfs"
    s.ensure_dirs(); assert s.pdf_dir.is_dir()

def test_ata_and_rf_tags():
    tags = extract_tags("Allen Telescope Array filterbank data were searched with turboSETI over Doppler drift rates after RFI mitigation.")
    assert "ATA" in tags["facilities"]
    assert "filterbank" in tags["data_products"]
    assert "turboSETI" in tags["methods"]
    assert "Doppler drift" in tags["signal_features"]

def test_non_domain_text_does_not_gain_tags():
    assert all(not values for values in extract_tags("An unrelated sentence about gardening.").values())
