from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.nutrition_graph import run_nutrition_graph
from app.agents.prompts import build_smoothie_prompt
from app.models.nutrition_knowledge import NutritionKnowledge
from app.schemas.profile_schema import ProfileInput
from app.services.vector_service import build_profile_search_query, format_knowledge_context


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
    knowledge_items = [
        NutritionKnowledge(
            title="Vietnamese guava for weight-management smoothies",
            ingredient_name="guava",
            category="fruit",
            origin_country="Vietnam",
            region="Mekong Delta",
            season_months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            allowed_for_smoothie=True,
            content="Vietnamese guava is a fiber-rich fruit that can support satiety in weight-management smoothies.",
            source="Vietnamese food composition and local fruit seasonality dataset",
            tags=["fiber", "vitamin C", "Vietnamese fruit"],
        ),
        NutritionKnowledge(
            title="Unsweetened soy beverage protein support",
            ingredient_name="soy beverage",
            category="protein beverage",
            origin_country="Vietnam",
            region="multiple regions",
            season_months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            allowed_for_smoothie=True,
            content="Unsweetened soy beverage can add plant protein while avoiding dairy ingredients.",
            source="Nutrition knowledge base",
            tags=["protein", "dairy-free"],
        ),
    ]
    knowledge_context = format_knowledge_context(knowledge_items)

    print("Profile search query:")
    print(build_profile_search_query(profile))
    print("\nPrompt with injected knowledge:")
    print(build_smoothie_prompt(profile, knowledge_context=knowledge_context))
    print("\nLangGraph dry-run result:")
    plan = run_nutrition_graph(profile, knowledge_context=knowledge_context)
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
