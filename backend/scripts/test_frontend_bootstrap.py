from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    response = client.get("/frontend/bootstrap")
    print("GET /frontend/bootstrap ->", response.status_code)
    assert response.status_code == 200

    body = response.json()
    assert body["research_goal"] == "overweight_obesity_weight_management"
    assert "nữ" in body["gender_options"]
    assert len(body["sample_profiles"]) >= 4
    assert any(profile["expected_result"] == "reject_out_of_scope" for profile in body["sample_profiles"])
    assert any("BMI dưới 25" in note for note in body["notes"])
    assert any(endpoint["path"] == "/smoothies/generate-and-evaluate" for endpoint in body["endpoints"])

    first_profile = body["sample_profiles"][0]
    assert "Người" in first_profile["label"]
    assert first_profile["profile"]["goal"] == "overweight_obesity_weight_management"
    print(
        {
            "sample_profile_count": len(body["sample_profiles"]),
            "endpoint_count": len(body["endpoints"]),
            "language": "vi",
        }
    )


if __name__ == "__main__":
    main()
