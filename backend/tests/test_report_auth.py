from fastapi.testclient import TestClient

from app.api import auth_routes
from app.api.auth_routes import require_user
from app.config import settings
from app.main import app


REQUEST = {
    "profile": {"age": 30, "gender": "female", "height_cm": 160, "weight_kg": 72, "goal": "overweight_obesity_weight_management"},
    "ingredientIds": ["cam"],
    "servings": 1,
    "locale": "vi",
}


def _as(user_id: str) -> None:
    app.dependency_overrides[require_user] = lambda: {"id": user_id, "email": None, "name": None, "avatar_url": None}


def test_report_routes_require_login(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "app_env", "production")
    client = TestClient(app)
    assert client.post("/v1/reports", json=REQUEST).status_code == 401
    assert client.get("/v1/reports/rpt_missing").status_code == 401
    assert client.get("/v1/auth/me").status_code == 401


def test_other_users_report_is_hidden():
    client = TestClient(app)
    _as("user-a")
    created = client.post("/v1/reports", json=REQUEST)
    assert created.status_code == 202, created.text
    report_id = created.json()["report_id"]
    assert client.get(f"/v1/reports/{report_id}").status_code == 200

    _as("user-b")
    assert client.get(f"/v1/reports/{report_id}").status_code == 404
    assert client.get(f"/v1/reports/{report_id}/pdf").status_code == 404
    app.dependency_overrides.clear()


def test_rate_limit_per_user(monkeypatch):
    monkeypatch.setattr(settings, "report_rate_limit_per_hour", 1)
    client = TestClient(app)
    _as("user-rate-limited")
    assert client.post("/v1/reports", json=REQUEST).status_code == 202
    limited = client.post("/v1/reports", json=REQUEST)
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "rate_limited"
    app.dependency_overrides.clear()


def test_local_dev_user_when_oauth_not_configured(monkeypatch):
    app.dependency_overrides.clear()
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "google_client_id", None)
    client = TestClient(app)
    response = client.get("/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["id"] == auth_routes.LOCAL_DEV_USER["id"]
