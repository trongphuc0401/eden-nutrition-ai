import re
import unicodedata

from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothiePlanResponse


TERM_ALIASES: dict[str, list[str]] = {
    "milk": ["milk", "dairy", "yogurt", "yoghurt", "whey", "cheese", "cream", "sữa bò", "sữa chua", "phô mai", "kem sữa"],
    "sua": ["milk", "dairy", "yogurt", "yoghurt", "whey", "cheese", "cream", "sữa bò", "sữa chua", "phô mai", "kem sữa"],
    "banana": ["banana", "chuối", "chuối tây", "chuối tiêu"],
    "chuoi": ["banana", "chuối", "chuối tây", "chuối tiêu"],
    "soy": ["soy", "soybean", "soya", "đậu nành", "sữa đậu nành", "nước đậu nành"],
    "dau nanh": ["soy", "soybean", "soya", "đậu nành", "sữa đậu nành", "nước đậu nành"],
    "peanut": ["peanut", "groundnut", "lạc", "đậu phộng"],
    "lac": ["peanut", "groundnut", "lạc", "đậu phộng"],
    "dau phong": ["peanut", "groundnut", "lạc", "đậu phộng"],
    "tree nut": ["almond", "cashew", "walnut", "hazelnut", "macadamia", "nut", "hạnh nhân", "hạt điều", "óc chó"],
}


def normalize_text(value: str) -> str:
    value = value.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_only = ascii_only.lower()
    ascii_only = re.sub(r"[^a-z0-9]+", " ", ascii_only)
    return re.sub(r"\s+", " ", ascii_only).strip()


def expand_blocked_terms(terms: list[str]) -> list[str]:
    expanded: list[str] = []
    for term in terms:
        normalized = normalize_text(term)
        if not normalized:
            continue
        if normalized not in {"sua"}:
            expanded.append(normalized)
        for alias in TERM_ALIASES.get(normalized, []):
            expanded.append(normalize_text(alias))
    return sorted(set(expanded))


def find_conflicting_ingredients(
    ingredient_names: list[str],
    blocked_terms: list[str],
) -> list[str]:
    normalized_ingredients = [normalize_text(name) for name in ingredient_names]
    normalized_terms = expand_blocked_terms(blocked_terms)
    conflicts: list[str] = []

    for ingredient in normalized_ingredients:
        if not ingredient:
            continue
        for blocked in normalized_terms:
            if blocked and blocked in ingredient:
                conflicts.append(blocked)

    return sorted(set(conflicts))


def filter_knowledge_context(
    knowledge_context: list[str],
    profile: ProfileInput,
) -> list[str]:
    normalized_terms = expand_blocked_terms([*profile.allergies, *profile.disliked_ingredients])
    filtered_context: list[str] = []

    for item in knowledge_context:
        normalized_item = normalize_text(item)
        if any(term in normalized_item for term in normalized_terms):
            continue
        filtered_context.append(item)

    return filtered_context


def validate_smoothie_plan(
    plan: SmoothiePlanResponse,
    profile: ProfileInput,
) -> list[str]:
    conflicts = find_conflicting_ingredients(
        [ingredient.name for ingredient in plan.ingredients],
        [*profile.allergies, *profile.disliked_ingredients],
    )
    violations: list[str] = []

    if conflicts:
        violations.append(
            "Generated smoothie contains blocked ingredient terms: "
            + ", ".join(conflicts)
            + "."
        )

    if profile.medical_notes:
        warning = normalize_text(plan.safety_warning)
        consultation_terms = ["consult", "clinician", "doctor", "tu van", "bac si", "chuyen gia"]
        if not any(term in warning for term in consultation_terms):
            violations.append(
                "Medical notes are present but the safety warning does not advise clinical consultation."
            )

    return violations
