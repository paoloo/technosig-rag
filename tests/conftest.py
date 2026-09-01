"""Shared pytest fixtures.

Unit tests (tests/unit/) touch no network and no live services. Integration
tests (tests/integration/) hit the real Ollama daemon and the populated
LanceDB table, so they only make sense run against a deployed environment
(atadev) - `skip_if_no_ollama` lets the suite degrade gracefully to skips
rather than hard failures when run somewhere without those services.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def ollama_available() -> bool:
    try:
        import httpx

        from config import settings

        resp = httpx.get(f"{settings.ollama_host}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture
def skip_if_no_ollama(ollama_available: bool) -> None:
    if not ollama_available:
        pytest.skip("Ollama daemon not reachable - run this suite on atadev")


@pytest.fixture(scope="session")
def lancedb_table_available() -> bool:
    try:
        from storage.vector_store import get_table

        get_table()
        return True
    except Exception:
        return False


@pytest.fixture
def skip_if_no_table(lancedb_table_available: bool) -> None:
    if not lancedb_table_available:
        pytest.skip("LanceDB 'chunks' table not populated - run this suite on atadev")
