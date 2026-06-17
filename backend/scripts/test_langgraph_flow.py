from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.nutrition_graph import run_nutrition_graph
from app.config import settings
from app.schemas.profile_schema import ProfileInput


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

    if not settings.openai_api_key:
        print("OPENAI_API_KEY is not set. Running LangGraph with dry-run smoothie generation.")

    plan = run_nutrition_graph(profile)
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
