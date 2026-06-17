from app.schemas.profile_schema import ProfileInput


SYSTEM_PROMPT = """
You are an AI nutrition coach that designs smoothie recipes.
Return practical nutrition guidance, not medical diagnosis.
Always respect allergies and disliked ingredients.
If medical notes mention a health condition, include a clear safety warning and advise consulting a clinician.
""".strip()


def build_smoothie_prompt(profile: ProfileInput) -> str:
    return f"""
Create one smoothie recipe for this user profile.

Age: {profile.age}
Gender: {profile.gender}
Height: {profile.height_cm} cm
Weight: {profile.weight_kg} kg
Goal: {profile.goal}
Allergies: {", ".join(profile.allergies) or "none"}
Disliked ingredients: {", ".join(profile.disliked_ingredients) or "none"}
Medical notes: {profile.medical_notes or "none"}

Requirements:
- Do not include any allergy or disliked ingredient.
- Keep the recipe realistic for a single serving.
- Explain why the recipe fits the goal.
- Include a safety warning even when there is no major concern.
""".strip()
