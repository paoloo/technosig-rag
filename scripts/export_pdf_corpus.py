"""Export the PDF-backed manifest records as a Markdown corpus inventory."""
from __future__ import annotations

import argparse
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import quote


def _cell(value: str | None) -> str:
    """Make a manifest value safe for a compact Markdown table cell."""
    text = " ".join((value or "").split())
    return text.replace("\\", "\\\\").replace("|", "\\|")


def export_corpus(manifest_path: Path, output_path: Path) -> int:
    uri = f"file:{manifest_path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        rows = connection.execute(
            """
            SELECT bibcode, title, access_level
            FROM papers
            WHERE pdf_path IS NOT NULL AND trim(pdf_path) != ''
            ORDER BY published DESC, bibcode DESC
            """
        ).fetchall()

    access_counts = Counter(row[2] for row in rows)
    lines = [
        "# Technosignature RAG PDF corpus",
        "",
        (
            f"This inventory contains all **{len(rows):,}** NASA ADS records with validated "
            "PDFs in the deployed technosignature RAG corpus."
        ),
        "",
        (
            "Evidence used by the RAG: "
            f"**{access_counts['full_text']:,} full text**, "
            f"**{access_counts['abstract_only']:,} abstract only**, and "
            f"**{access_counts['metadata_only']:,} metadata only**. A PDF can be present but "
            "not contribute full text when it is a scan or has no usable extractable text."
        ),
        "",
        "| # | Title | NASA ADS | Evidence used |",
        "| ---: | --- | --- | --- |",
    ]

    for number, (bibcode, title, access_level) in enumerate(rows, start=1):
        ads_url = f"https://ui.adsabs.harvard.edu/abs/{quote(bibcode, safe='')}/abstract"
        display_title = _cell(title) or _cell(bibcode)
        lines.append(
            f"| {number} | {display_title} | [ADS:{_cell(bibcode)}]({ads_url}) | "
            f"`{_cell(access_level)}` |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to manifest.sqlite3")
    parser.add_argument("--output", type=Path, default=Path("corpus.md"))
    args = parser.parse_args()
    count = export_corpus(args.manifest, args.output)
    print(f"wrote {count} PDF records to {args.output}")


if __name__ == "__main__":
    main()
