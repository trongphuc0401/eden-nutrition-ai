from typing import Literal

from pydantic import BaseModel, Field


NutritionGoal = Literal["overweight_obesity_weight_management"]
HealthRestrictionStatus = Literal["no", "yes", "unknown"]


class ProfileInput(BaseModel):
    age: int = Field(ge=18, le=100)
    gender: str = Field(min_length=1, max_length=50)
    height_cm: int = Field(ge=100, le=250)
    weight_kg: float = Field(gt=25, le=300)
    goal: NutritionGoal
    allergies: list[str] = Field(default_factory=list)
    preferred_food_types: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    medical_notes: str = Field(default="", max_length=500)
    health_restriction_status: HealthRestrictionStatus = "unknown"
