from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path

from app.agents.report_graph import report_graph


DATASET = Path(__file__).resolve().parents[1] / "evals" / "report_eval_cases.json"


def invoke(case: dict) -> dict:
    token = uuid.uuid4().hex[:10]
    request = {
        "profile": case["profile"],
        "ingredientIds": case["ingredient_ids"],
        "servings": 1,
        "prompt": case.get("prompt", ""),
        "locale": "vi-VN",
        "allowSuggestions": case["category"] != "confirmation_cancel_recovery",
    }
    state = {
        "request": request,
        "report_id": f"eval_{token}",
        "thread_id": f"thread_{token}",
        "run_id": f"run_{token}",
        "errors": [],
        "warnings": [],
        "retry_count": 0,
        "execution_metadata": {},
    }
    return report_graph.invoke(state, {"configurable": {"thread_id": state["thread_id"]}})


def main() -> None:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    counts = Counter(case["category"] for case in cases)
    expected = {"normal": 40, "allergy_exclusion": 20, "missing_data_unit": 15, "model_failure_injection": 15, "confirmation_cancel_recovery": 10}
    if counts != expected:
        raise SystemExit(f"Invalid eval distribution: {dict(counts)}")

    passed = 0
    executed = 0
    for case in cases:
        if case["category"] == "confirmation_cancel_recovery":
            continue  # Covered by API integration tests because these cases require job state transitions.
        result = invoke(case)
        executed += 1
        status = "reject" if result.get("decision") == "reject" else result.get("decision", "failed")
        if status not in case["expected_status"]:
            print(case["id"], "expected", case["expected_status"], "got", status)
            continue
        if case["category"] == "missing_data_unit" and result.get("report_document", {}).get("totals", {}).get("calories") is not None:
            print(case["id"], "incorrectly exposed a complete calorie total")
            continue
        passed += 1
    print(json.dumps({"dataset": len(cases), "executed": executed, "passed": passed, "failed": executed - passed}, ensure_ascii=False))
    if passed != executed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
