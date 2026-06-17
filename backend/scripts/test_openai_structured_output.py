from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.prompts import build_smoothie_prompt
from app.config import settings
from app.schemas.profile_schema import ProfileInput
from app.services.openai_service import generate_smoothie_plan


def main() -> None:
    profile = ProfileInput(
        age=24,
        gender="male",
        height_cm=170,
        weight_kg=70,
        goal="fat_loss",
        allergies=["milk"],
        disliked_ingredients=["banana"],
        medical_notes="",
    )

    print("Profile input is valid.")
    print("Prompt preview:")
    print(build_smoothie_prompt(profile))

    if not settings.openai_api_key:
        print("OPENAI_API_KEY is not set. Skipping live OpenAI call.")
        return

    plan = generate_smoothie_plan(profile)
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
