from __future__ import annotations

import json
import urllib.request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
from typing import Any

from app.agents.prompts import SYSTEM_PROMPT, build_smoothie_prompt
from app.config import settings
from app.schemas.profile_schema import ProfileInput
from app.schemas.smoothie_schema import SmoothiePlanResponse
from app.services.guardrail_service import find_conflicting_ingredients, normalize_text


def _provider_name(value: str | None) -> str:
    return (value or "").strip().lower()


def _provider_api_key() -> str | None:
    return settings.llm_api_key or settings.openai_api_key


def _provider_model() -> str:
    return settings.llm_model or settings.openai_model


def _provider_base_url() -> str | None:
    if settings.llm_base_url:
        return settings.llm_base_url

    provider = _provider_name(settings.llm_provider)
    provider_urls = {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "cerebras": "https://api.cerebras.ai/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta",
    }
    return provider_urls.get(provider)


def _extract_json_text(payload: dict[str, Any]) -> str:
    candidates: list[str] = []
    for item in payload.get("candidates", []) or []:
        content = item.get("content") or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if text:
                candidates.append(text)
    if candidates:
        return "".join(candidates)

    output = payload.get("output_text")
    if isinstance(output, str) and output.strip():
        return output

    choices = payload.get("choices", []) or []
    if choices:
        message = (choices[0].get("message") or {}).get("content")
        if isinstance(message, str):
            return message
        if isinstance(message, list):
            return "".join(part.get("text", "") for part in message if isinstance(part, dict))

    raise ValueError("Model response did not contain text.")


def _parse_response_text(text: str) -> SmoothiePlanResponse:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        cleaned = cleaned.removeprefix("json").strip()
    payload = _normalize_plan_payload(json.loads(cleaned))
    return SmoothiePlanResponse.model_validate(payload)


def _normalize_plan_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    if "smoothie_name" not in normalized and "recipe_name" in normalized:
        normalized["smoothie_name"] = normalized.pop("recipe_name")
    if "reason" not in normalized and "explanation" in normalized:
        normalized["reason"] = normalized.pop("explanation")
    if "safety_warning" not in normalized and "warning" in normalized:
        normalized["safety_warning"] = normalized.pop("warning")

    ingredients = normalized.get("ingredients", [])
    if isinstance(ingredients, list):
        normalized["ingredients"] = [_normalize_ingredient(item) for item in ingredients]

    normalized["goal"] = "overweight_obesity_weight_management"
    return normalized


def _smoothie_response_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "smoothie_name": {"type": "STRING"},
            "goal": {"type": "STRING"},
            "calories": {"type": "INTEGER"},
            "ingredients": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "amount": {"type": "STRING"},
                        "purpose": {"type": "STRING"},
                    },
                    "required": ["name", "amount", "purpose"],
                },
            },
            "reason": {"type": "STRING"},
            "safety_warning": {"type": "STRING"},
        },
        "required": ["smoothie_name", "goal", "calories", "ingredients", "reason", "safety_warning"],
    }


def _normalize_ingredient(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"name": str(item), "amount": "1 khẩu phần", "purpose": "nguyên liệu trong công thức"}

    name = item.get("name") or item.get("ingredient_name") or item.get("ingredient") or "không rõ"
    amount = item.get("amount")
    if amount is None:
        amount_value = item.get("quantity") or item.get("qty") or item.get("count")
        unit = item.get("unit")
        if amount_value is not None and unit:
            amount = f"{amount_value} {unit}"
        elif amount_value is not None:
            amount = str(amount_value)
        else:
            amount = "1 khẩu phần"
    elif not isinstance(amount, str):
        unit = item.get("unit")
        amount = f"{amount} {unit}".strip() if unit else str(amount)

    purpose = item.get("purpose") or item.get("reason") or item.get("role") or "nguyên liệu trong công thức"
    return {
        "name": str(name),
        "amount": str(amount),
        "purpose": str(purpose),
    }


def _safe_fallback_plan(profile: ProfileInput) -> SmoothiePlanResponse:
    blocked = " ".join([*profile.allergies, *profile.disliked_ingredients])
    blocked_normalized = normalize_text(blocked)
    use_soy = "dau nanh" not in blocked_normalized and "soy" not in blocked_normalized

    liquid = {
        "name": "nước đậu nành không đường",
        "amount": "200 ml",
        "purpose": "bổ sung protein thực vật, không dùng sữa bò",
    }
    if not use_soy:
        liquid = {
            "name": "nước lọc lạnh",
            "amount": "180 ml",
            "purpose": "làm nền sinh tố an toàn khi cần tránh đậu nành",
        }

    return SmoothiePlanResponse(
        smoothie_name="Sinh tố ổi xanh giàu chất xơ",
        goal="overweight_obesity_weight_management",
        calories=240 if use_soy else 170,
        ingredients=[
            {"name": "ổi", "amount": "120 g", "purpose": "bổ sung chất xơ và vitamin C"},
            liquid,
            {"name": "rau bina", "amount": "40 g", "purpose": "bổ sung chất xơ và vi chất"},
            {"name": "hạt chia", "amount": "1 tsp", "purpose": "tăng chất xơ với lượng chất béo được kiểm soát"},
        ],
        reason="Công thức mẫu này ưu tiên chất xơ, năng lượng vừa phải và tránh các nguyên liệu người dùng không phù hợp.",
        safety_warning="Kết quả mẫu để kiểm thử. Nếu có ghi chú sức khỏe, người dùng nên tư vấn bác sĩ hoặc chuyên gia dinh dưỡng trước khi áp dụng.",
    )


def _plan_is_safe(plan: SmoothiePlanResponse, profile: ProfileInput) -> bool:
    conflicts = find_conflicting_ingredients(
        [ingredient.name for ingredient in plan.ingredients],
        [*profile.allergies, *profile.disliked_ingredients],
    )
    if conflicts:
        return False
    if profile.medical_notes:
        warning = normalize_text(plan.safety_warning)
        consultation_terms = ["consult", "clinician", "doctor", "tu van", "bac si", "chuyen gia"]
        if not any(term in warning for term in consultation_terms):
            return False
    return True


@dataclass
class LLMService:
    def generate_smoothie_plan(
        self,
        profile: ProfileInput,
        knowledge_context: list[str] | None = None,
    ) -> SmoothiePlanResponse:
        provider = _provider_name(settings.llm_provider)
        try:
            if provider == "gemini":
                plan = self._generate_gemini(profile, knowledge_context)
            else:
                plan = self._generate_openai_compatible(profile, knowledge_context, provider)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return _safe_fallback_plan(profile)

        if not _plan_is_safe(plan, profile):
            return _safe_fallback_plan(profile)
        return plan

    def _generate_openai_compatible(
        self,
        profile: ProfileInput,
        knowledge_context: list[str] | None,
        provider: str,
    ) -> SmoothiePlanResponse:
        api_key = _provider_api_key()
        base_url = _provider_base_url()
        if not api_key:
            raise ValueError("LLM API key is required to call the selected provider.")
        if not base_url:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        payload = {
            "model": _provider_model(),
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_smoothie_prompt(profile, knowledge_context=knowledge_context)},
            ],
            "text": {"format": {"type": "json_schema", "name": "SmoothiePlanResponse"}},
        }
        request = urllib.request.Request(
            f"{base_url}/responses",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        return _parse_response_text(_extract_json_text(body))

    def _generate_gemini(
        self,
        profile: ProfileInput,
        knowledge_context: list[str] | None,
    ) -> SmoothiePlanResponse:
        api_key = _provider_api_key()
        base_url = _provider_base_url()
        if not api_key:
            raise ValueError("LLM API key is required to call Gemini.")
        if not base_url:
            raise ValueError("Gemini base URL is not configured.")

        prompt = "\n\n".join(
            [
                SYSTEM_PROMPT,
                build_smoothie_prompt(profile, knowledge_context=knowledge_context),
                "Return only valid JSON matching the SmoothiePlanResponse schema.",
            ]
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": _smoothie_response_schema(),
                "temperature": 0.2,
            },
        }
        request = urllib.request.Request(
            f"{base_url}/models/{_provider_model()}:generateContent?key={api_key}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        return _parse_response_text(_extract_json_text(body))


def generate_smoothie_plan(
    profile: ProfileInput,
    knowledge_context: list[str] | None = None,
) -> SmoothiePlanResponse:
    return LLMService().generate_smoothie_plan(profile, knowledge_context=knowledge_context)
