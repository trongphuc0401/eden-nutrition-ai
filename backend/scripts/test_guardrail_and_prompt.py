from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.prompts import build_smoothie_prompt
from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothieIngredient, SmoothiePlanResponse
from app.services.guardrail_service import (
    expand_blocked_terms,
    filter_knowledge_context,
    validate_smoothie_plan,
)


def main() -> None:
    profile = ProfileInput(
        age=32,
        gender="female",
        height_cm=162,
        weight_kg=74,
        goal="overweight_obesity_weight_management",
        allergies=["milk"],
        preferred_food_types=["Vietnamese tropical fruits"],
        disliked_ingredients=["banana"],
        medical_notes="prediabetes",
    )

    print("Expanded blocked terms:")
    print(expand_blocked_terms([*profile.allergies, *profile.disliked_ingredients]))
    print()

    knowledge_context = [
        "Ingredient: milk yogurt smoothie base\nOrigin country: Vietnam\nContent: dairy base",
        "Ingredient: guava\nOrigin country: Vietnam\nContent: fiber-rich fruit",
    ]
    filtered_context = filter_knowledge_context(knowledge_context, profile)
    print("Filtered knowledge context:")
    print(filtered_context)
    print()

    print("Prompt preview:")
    print(build_smoothie_prompt(profile, knowledge_context=filtered_context))
    print()

    violating_plan = SmoothiePlanResponse(
        smoothie_name="Bad Example",
        goal=profile.goal,
        calories=250,
        ingredients=[
            SmoothieIngredient(name="banana", amount="100 g", purpose="fruit base"),
            SmoothieIngredient(name="milk yogurt", amount="150 ml", purpose="protein"),
        ],
        reason="Example only",
        safety_warning="No warning.",
    )
    print("Guardrail violations:")
    print(validate_smoothie_plan(violating_plan, profile))


if __name__ == "__main__":
    main()
