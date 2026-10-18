from __future__ import annotations

import os

# Set before the app is imported: services read these at import time (e.g. persisted report jobs are loaded
# by the report_job_service singleton), and tests must never read or write the shared Supabase database.
os.environ["REPORT_JOB_PERSISTENCE_ENABLED"] = "false"
os.environ["CHAT_PERSISTENCE_ENABLED"] = "false"
os.environ["REFERENCE_DATA_SOURCE"] = "json"

import pytest  # noqa: E402

from app.config import settings  # noqa: E402
from app.services import reference_repository  # noqa: E402


@pytest.fixture(autouse=True)
def json_reference_data(monkeypatch: pytest.MonkeyPatch):
    """Unit tests run on the bundled JSON seeds and in-memory stores, whatever backend/.env says."""
    monkeypatch.setattr(settings, "reference_data_source", "json")
    monkeypatch.setattr(settings, "report_job_persistence_enabled", False)
    monkeypatch.setattr(settings, "chat_persistence_enabled", False)
    monkeypatch.setattr(settings, "chat_mode", "template")
    reference_repository.clear_cache()
    yield
    reference_repository.clear_cache()
