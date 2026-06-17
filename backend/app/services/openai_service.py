from openai import OpenAI

from app.agents.prompts import SYSTEM_PROMPT, build_smoothie_prompt
from app.config import settings
from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothiePlanResponse


class OpenAIService:
    def __init__(self, client: OpenAI | None = None) -> None:
        if client is not None:
            self.client = client
            return

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required to call OpenAI.")

        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate_smoothie_plan(self, profile: ProfileInput) -> SmoothiePlanResponse:
        response = self.client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_smoothie_prompt(profile)},
            ],
            text_format=SmoothiePlanResponse,
        )

        return response.output_parsed


def generate_smoothie_plan(profile: ProfileInput) -> SmoothiePlanResponse:
    return OpenAIService().generate_smoothie_plan(profile)
