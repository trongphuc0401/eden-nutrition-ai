from __future__ import annotations

from app.agents.report_graph import report_graph


def main() -> None:
    state = {
        "request": {
            "profile": {
                "age": 32,
                "gender": "Nữ",
                "height_cm": 165,
                "weight_kg": 75,
                "goal": "overweight_obesity_weight_management",
                "allergies": [],
                "preferred_food_types": ["Nhiều chất xơ"],
                "disliked_ingredients": [],
                "medical_notes": "",
                "health_restriction_status": "no",
            },
            "ingredientIds": ["cam", "yen-mach", "hat-chia"],
            "servings": 1,
            "prompt": "Bữa phụ ít ngọt, dễ chuẩn bị",
            "locale": "vi-VN",
            "allowSuggestions": False,
        },
        "report_id": "smoke-ai-recipe-report",
        "thread_id": "thread-smoke-ai-recipe-report",
        "run_id": "run-smoke-ai-recipe-report",
        "errors": [],
        "warnings": [],
        "retry_count": 0,
        "execution_metadata": {},
    }
    result = report_graph.invoke(state, {"configurable": {"thread_id": state["thread_id"]}})
    print(result["pdf_metadata"]["path"])


if __name__ == "__main__":
    main()
