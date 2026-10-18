from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)
    bootstrap_response = client.get("/frontend/bootstrap")
    assert bootstrap_response.status_code == 200
    sample_profiles = bootstrap_response.json()["sample_profiles"]
    payload = next(item["profile"] for item in sample_profiles if item["expected_result"] == "review")
    out_of_scope_payload = next(
        item["profile"] for item in sample_profiles if item["expected_result"] == "reject_out_of_scope"
    )

    status_response = client.get("/system-status")
    print("GET /system-status ->", status_response.status_code)
    status_body = status_response.json()
    assert status_response.status_code == 200
    assert status_body["readiness_status"] in {"ready", "partial", "not_ready"}
    assert "database_reachable" in status_body
    assert "vector_embedding_item_count" in status_body
    assert len(status_body["capabilities"]) >= 5
    assert any(item["name"] == "guardrail_and_evaluation" for item in status_body["capabilities"])
    print(status_body)
    print()

    response = client.post(
        "/smoothies/generate-and-evaluate?use_rag=true&knowledge_limit=3",
        json=payload,
    )
    print("POST /smoothies/generate-and-evaluate ->", response.status_code)
    body = response.json()
    assert response.status_code == 200
    assert body["generation"]["plan"]["goal"] == "overweight_obesity_weight_management"
    assert len(body["evaluation"]["ingredient_breakdown"]) >= 1
    assert len(body["evaluation"]["threshold_checks"]) >= 4
    assert body["evaluation"]["evaluation_report"]["decision"] in {"pass", "review", "reject"}
    assert body["evaluation"]["evaluation_report"]["score"] >= 0
    assert "overall_pass" in body["evaluation"]
    print(body)

    evaluate_response = client.post(
        "/smoothies/evaluate",
        json={
            "profile": payload,
            "plan": body["generation"]["plan"],
        },
    )
    print()
    print("POST /smoothies/evaluate ->", evaluate_response.status_code)
    evaluate_body = evaluate_response.json()
    assert evaluate_response.status_code == 200
    assert evaluate_body["evaluation_report"]["decision"] in {"pass", "review", "reject"}
    assert "ingredient_breakdown" in evaluate_body
    print(evaluate_body)

    analysis_response = client.post("/profiles/analyze", json=out_of_scope_payload)
    print()
    print("POST /profiles/analyze out-of-scope ->", analysis_response.status_code)
    analysis_body = analysis_response.json()
    assert analysis_response.status_code == 200
    assert analysis_body["research_scope_match"] is False
    assert analysis_body["bmi_category"] == "outside_research_scope"
    print(analysis_body)

    rejected_generation = client.post(
        "/smoothies/generate?use_rag=true&knowledge_limit=3",
        json=out_of_scope_payload,
    )
    print()
    print("POST /smoothies/generate out-of-scope ->", rejected_generation.status_code)
    assert rejected_generation.status_code == 422
    assert "BMI >= 25" in rejected_generation.json()["detail"]
    print(rejected_generation.json())


if __name__ == "__main__":
    main()
