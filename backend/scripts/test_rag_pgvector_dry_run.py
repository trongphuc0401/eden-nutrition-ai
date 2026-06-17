from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.nutrition_graph import run_nutrition_graph
from app.agents.prompts import build_smoothie_prompt
from app.schemas.profile_schema import ProfileInput
from app.services.vector_service import build_profile_search_query


def main() -> None:
    profile = ProfileInput(
        age=24,
        gender="male",
        height_cm=170,
        weight_kg=70,
        goal="overweight_obesity_weight_management",
        allergies=["milk"],
        preferred_food_types=["Vietnamese tropical fruits", "high-fiber ingredients"],
        disliked_ingredients=["banana"],
        medical_notes="",
    )
    knowledge_context = [
        "Vietnamese guava is a fiber-rich fruit that can support satiety in weight-management smoothies.",
        "Unsweetened soy beverage can add plant protein while avoiding dairy ingredients.",
    ]

    print("Profile search query:")
    print(build_profile_search_query(profile))
    print("\nPrompt with injected knowledge:")
    print(build_smoothie_prompt(profile, knowledge_context=knowledge_context))
    print("\nLangGraph dry-run result:")
    plan = run_nutrition_graph(profile, knowledge_context=knowledge_context)
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
