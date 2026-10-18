from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class FrontendProfileInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    age: int = Field(ge=18, le=100)
    gender: str = Field(min_length=1, max_length=50)
    height_cm: int = Field(validation_alias=AliasChoices("height_cm", "heightCm"), ge=100, le=250)
    weight_kg: float = Field(validation_alias=AliasChoices("weight_kg", "weightKg"), gt=25, le=300)
    allergies: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(validation_alias=AliasChoices("preferences", "preferred_food_types"), default_factory=list)
    dislikes: list[str] = Field(validation_alias=AliasChoices("dislikes", "disliked_ingredients"), default_factory=list)
    notes: str = Field(validation_alias=AliasChoices("notes", "medical_notes"), default="")
    health_restriction_status: Literal["no", "yes", "unknown"] = "unknown"

    def to_profile_input(self):
        from app.schemas.profile_schema import ProfileInput
        return ProfileInput(age=self.age, gender=self.gender, height_cm=self.height_cm, weight_kg=self.weight_kg, goal="overweight_obesity_weight_management", allergies=self.allergies, preferred_food_types=self.preferences, disliked_ingredients=self.dislikes, medical_notes=self.notes, health_restriction_status=self.health_restriction_status)


class FrontendGenerationRequest(BaseModel):
    profile: FrontendProfileInput
    ingredient_ids: list[str] = Field(validation_alias=AliasChoices("ingredient_ids", "ingredientIds"), min_length=1)
    prompt: str = Field(default="", max_length=500)
