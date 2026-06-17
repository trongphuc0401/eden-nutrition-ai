from pydantic import BaseModel, Field

from app.schemas.profile_schema import NutritionGoal


class SmoothieIngredient(BaseModel):
    name: str = Field(min_length=1)
    amount: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class SmoothiePlanResponse(BaseModel):
    smoothie_name: str = Field(min_length=1)
    goal: NutritionGoal
    calories: int = Field(ge=50, le=1200)
    ingredients: list[SmoothieIngredient] = Field(min_length=1)
    reason: str = Field(min_length=1)
    safety_warning: str = Field(min_length=1)
