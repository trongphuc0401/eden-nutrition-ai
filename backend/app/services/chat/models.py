"""Free Z.AI models the chat lets users pick from.

Z.AI lists these as free on https://docs.z.ai/guides/overview/pricing (checked 2026-11-01).
glm-4.6v-flash is free too but left out: Z.AI answered every test call with "overloaded" (code 1305).
Only ids on this list are ever sent to Z.AI, so a client cannot pick a paid model.
"""
from __future__ import annotations

from typing import Any

from app.config import settings

FREE_CHAT_MODELS: list[dict[str, Any]] = [
    {"id": "glm-4.7-flash", "label": "GLM-4.7 Flash", "description": "Mới nhất, trả lời tự nhiên nhất"},
    {"id": "glm-4.5-flash", "label": "GLM-4.5 Flash", "description": "Phản hồi nhanh, ổn định"},
]
FREE_MODEL_IDS = {model["id"] for model in FREE_CHAT_MODELS}


def llm_chat_enabled() -> bool:
    return settings.chat_mode.strip().lower() == "zai" and bool(settings.zai_api_key)


def default_chat_model() -> str:
    configured = settings.zai_model.strip().lower()
    return configured if configured in FREE_MODEL_IDS else FREE_CHAT_MODELS[0]["id"]


def resolve_chat_model(requested: str | None) -> str:
    """The requested model when it is on the free list, otherwise the default."""
    if requested and requested.strip().lower() in FREE_MODEL_IDS:
        return requested.strip().lower()
    return default_chat_model()
