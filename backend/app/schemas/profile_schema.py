from typing import Literal

from pydantic import BaseModel, Field


NutritionGoal = Literal["fat_loss", "muscle_gain", "healthy_living", "energy_boost"]


class ProfileInput(BaseModel):
    age: int = Field(ge=13, le=100)
    gender: str = Field(min_length=1, max_length=50)
    height_cm: int = Field(ge=100, le=250)
    weight_kg: float = Field(gt=25, le=300)
    goal: NutritionGoal
    allergies: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    medical_notes: str = ""
