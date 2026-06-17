from typing import Any, TypedDict

from app.config import settings
from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothieIngredient, SmoothiePlanResponse
from app.services.openai_service import generate_smoothie_plan


class NutritionGraphState(TypedDict, total=False):
    profile: ProfileInput
    goal_analysis: dict[str, Any]
    smoothie_plan: SmoothiePlanResponse
    safety_notes: list[str]


def analyze_goal(state: NutritionGraphState) -> NutritionGraphState:
    profile = state["profile"]
    state["goal_analysis"] = {
        "goal": profile.goal,
        "target_population": "Vietnamese adults with overweight or obesity",
        "focus": [
            "weight management",
            "improved diet quality",
            "fiber and protein support",
            "reasonable sugar and fat",
        ],
    }
    return state


def generate_smoothie_plan_node(state: NutritionGraphState) -> NutritionGraphState:
    profile = state["profile"]

    if settings.openai_api_key:
        state["smoothie_plan"] = generate_smoothie_plan(profile)
        return state

    state["smoothie_plan"] = SmoothiePlanResponse(
        smoothie_name="Vietnamese Green Guava Protein Smoothie",
        goal=profile.goal,
        calories=280,
        ingredients=[
            SmoothieIngredient(
                name="guava",
                amount="120 g",
                purpose="adds fiber and vitamin C",
            ),
            SmoothieIngredient(
                name="unsweetened soy beverage",
                amount="200 ml",
                purpose="adds plant protein without dairy",
            ),
            SmoothieIngredient(
                name="spinach",
                amount="40 g",
                purpose="adds fiber and micronutrients",
            ),
            SmoothieIngredient(
                name="chia seeds",
                amount="1 tsp",
                purpose="adds fiber and healthy fat in a controlled amount",
            ),
        ],
        reason="This dry-run formula supports the research goal by emphasizing fiber, plant protein, and moderate energy for a single serving.",
        safety_warning="Dry-run result only. Review allergies, medical notes, and nutrition thresholds before real use.",
    )
    return state


def safety_check(state: NutritionGraphState) -> NutritionGraphState:
    profile = state["profile"]
    plan = state["smoothie_plan"]
    blocked_terms = [*profile.allergies, *profile.disliked_ingredients]
    ingredient_names = [ingredient.name.lower() for ingredient in plan.ingredients]
    conflicts = [
        term
        for term in blocked_terms
        if term and any(term.lower() in ingredient for ingredient in ingredient_names)
    ]

    state["safety_notes"] = []
    if conflicts:
        state["safety_notes"].append(
            f"Potential conflict found with allergy or disliked ingredient: {', '.join(conflicts)}."
        )

    if profile.medical_notes:
        state["safety_notes"].append(
            "Medical notes are present. User should consult a qualified clinician before applying this formula."
        )

    if state["safety_notes"]:
        plan.safety_warning = " ".join([plan.safety_warning, *state["safety_notes"]])

    return state
