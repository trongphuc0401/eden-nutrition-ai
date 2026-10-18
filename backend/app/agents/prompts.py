from app.schemas.profile_schema import ProfileInput


def format_knowledge_section(knowledge_context: list[str] | None = None) -> str:
    if not knowledge_context:
        return "Relevant nutrition knowledge:\nnone"

    formatted_items = "\n\n".join(
        f"[Knowledge {index}]\n{content}"
        for index, content in enumerate(knowledge_context, start=1)
    )
    return f"Relevant nutrition knowledge:\n{formatted_items}"


SYSTEM_PROMPT = """
You are an AI nutrition assistant that designs personalized smoothie formulas for Vietnamese adults with overweight or obesity.
Use Vietnamese for user-facing text such as smoothie names, ingredient purposes, reasons, and safety warnings.
Focus on weight management, improved diet quality, fiber and protein support, and awareness of sugar and fat.
Return one realistic smoothie formula, not a general meal plan.
Return practical nutrition guidance, not medical diagnosis.
Use the provided nutrition knowledge when it is relevant. Do not invent citations or facts that are not present.
Prefer fruits with verified Vietnamese origin from the provided knowledge context.
Always respect allergies and disliked ingredients.
Never include an ingredient that conflicts with an allergy or a disliked ingredient, even if that ingredient appears in the knowledge context.
Prefer smoothie-safe ingredients and keep the formula practical for one serving.
When the knowledge context is incomplete, say that origin or evidence could not be verified instead of inventing certainty.
If medical notes mention a health condition, include a clear safety warning and advise consulting a clinician.
""".strip()


def build_smoothie_prompt(
    profile: ProfileInput,
    knowledge_context: list[str] | None = None,
) -> str:
    return f"""
Create one personalized smoothie formula for a Vietnamese adult with overweight or obesity.
Write all user-facing content in Vietnamese.

Age: {profile.age}
Gender: {profile.gender}
Height: {profile.height_cm} cm
Weight: {profile.weight_kg} kg
Goal: {profile.goal}
Allergies: {", ".join(profile.allergies) or "none"}
Preferred food types: {", ".join(profile.preferred_food_types) or "none"}
Disliked ingredients: {", ".join(profile.disliked_ingredients) or "none"}
Medical notes: {profile.medical_notes or "none"}

{format_knowledge_section(knowledge_context)}

Requirements:
- Do not include any allergy or disliked ingredient.
- Treat preferred food types as helpful preferences, but never let them override allergy or safety constraints.
- Keep the recipe realistic for a single serving.
- Support weight management and improved diet quality.
- Prefer ingredients that help add fiber and protein while keeping sugar and fat reasonable.
- Use the relevant nutrition knowledge above to ground the formula when possible.
- Prefer fruits whose Vietnamese origin is verified in the knowledge context.
- Do not use imported fruits unless the knowledge context explicitly allows them.
- If origin information is missing, say that the ingredient origin could not be verified.
- Explain why the smoothie formula fits the research goal.
- Include a safety warning even when there is no major concern.
- Return valid JSON only.
- Use these exact top-level keys: smoothie_name, goal, calories, ingredients, reason, safety_warning.
- Each ingredient item must contain: name, amount, purpose.
- Write amount as a readable string such as "120 g" or "200 ml".
""".strip()
