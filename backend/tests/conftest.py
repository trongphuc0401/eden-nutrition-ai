from __future__ import annotations

import pytest

from app.config import settings
from app.services import reference_repository


@pytest.fixture(autouse=True)
def json_reference_data(monkeypatch: pytest.MonkeyPatch):
    """Unit tests run on the bundled JSON seeds unless a test opts into the database snapshot."""
    monkeypatch.setattr(settings, "reference_data_source", "json")
    reference_repository.clear_cache()
    yield
    reference_repository.clear_cache()
