from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app


REQUIRED_PATHS = {
    "/health": ["get"],
    "/system-status": ["get"],
    "/profiles/analyze": ["post"],
    "/knowledge/search-preview": ["post"],
    "/smoothies/generate": ["post"],
    "/smoothies/evaluate": ["post"],
    "/smoothies/generate-and-evaluate": ["post"],
    "/research-rules/preview": ["get"],
}

REQUIRED_SCHEMAS = [
    "NutritionEstimateResponse",
    "IngredientNutritionBreakdown",
    "ThresholdCheckResponse",
    "SafetyCheckResponse",
    "EvaluationReportResponse",
    "SmoothieEvaluationRequest",
    "SmoothieEvaluationResponse",
    "GenerateAndEvaluateResponse",
    "SystemStatusResponse",
]


def main() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    for path, methods in REQUIRED_PATHS.items():
        assert path in paths, f"Missing OpenAPI path: {path}"
        for method in methods:
            assert method in paths[path], f"Missing OpenAPI method: {method.upper()} {path}"

    for schema_name in REQUIRED_SCHEMAS:
        assert schema_name in components, f"Missing OpenAPI schema: {schema_name}"

    evaluation_report = components["EvaluationReportResponse"]
    decision_schema = evaluation_report["properties"]["decision"]
    assert decision_schema["enum"] == ["pass", "review", "reject"]

    smoothie_evaluation = components["SmoothieEvaluationResponse"]
    required_fields = set(smoothie_evaluation["required"])
    assert {
        "estimated_nutrition",
        "ingredient_breakdown",
        "threshold_checks",
        "safety_checks",
        "evaluation_report",
        "overall_pass",
    }.issubset(required_fields)

    smoothie_evaluation_request = components["SmoothieEvaluationRequest"]
    assert {"profile", "plan"}.issubset(set(smoothie_evaluation_request["required"]))

    evaluate_body = paths["/smoothies/evaluate"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert evaluate_body["$ref"].endswith("/SmoothieEvaluationRequest")

    system_status = components["SystemStatusResponse"]
    assert "capabilities" in system_status["properties"]
    assert "readiness_status" in system_status["properties"]

    print(
        {
            "required_path_count": len(REQUIRED_PATHS),
            "required_schema_count": len(REQUIRED_SCHEMAS),
            "evaluation_decisions": decision_schema["enum"],
        }
    )


if __name__ == "__main__":
    main()
