from app.schemas.profile_schema import ProfileInput


SYSTEM_PROMPT = """
You are an AI nutrition assistant that designs personalized smoothie formulas for Vietnamese adults with overweight or obesity.
Focus on weight management, improved diet quality, fiber and protein support, and awareness of sugar and fat.
Return one realistic smoothie formula, not a general meal plan.
Return practical nutrition guidance, not medical diagnosis.
Always respect allergies and disliked ingredients.
If medical notes mention a health condition, include a clear safety warning and advise consulting a clinician.
""".strip()


def build_smoothie_prompt(profile: ProfileInput) -> str:
    return f"""
Create one personalized smoothie formula for a Vietnamese adult with overweight or obesity.

Age: {profile.age}
Gender: {profile.gender}
Height: {profile.height_cm} cm
Weight: {profile.weight_kg} kg
Goal: {profile.goal}
Allergies: {", ".join(profile.allergies) or "none"}
Preferred food types: {", ".join(profile.preferred_food_types) or "none"}
Disliked ingredients: {", ".join(profile.disliked_ingredients) or "none"}
Medical notes: {profile.medical_notes or "none"}

Requirements:
- Do not include any allergy or disliked ingredient.
- Treat preferred food types as helpful preferences, but never let them override allergy or safety constraints.
- Keep the recipe realistic for a single serving.
- Support weight management and improved diet quality.
- Prefer ingredients that help add fiber and protein while keeping sugar and fat reasonable.
- Explain why the smoothie formula fits the research goal.
- Include a safety warning even when there is no major concern.
""".strip()
