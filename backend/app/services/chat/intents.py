"""Intent routing for the chat agent.

Rules run first (fast, deterministic, testable). In `chat_mode=zai` an unclear message falls back to an LLM
classifier constrained to the same labels. Medical-boundary detection is rule-only on purpose: it must never depend
on a model being available.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.report_data_service import slugify

INTENTS = ("create_recipe", "nutrition_question", "compare", "suitability", "seasonal", "medical_boundary", "greeting", "general")


@dataclass
class Intent:
    kind: str
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)
    from_history: bool = False


def _has(text: str, *phrases: str) -> bool:
    return any(f"-{slugify(phrase)}-" in text for phrase in phrases)


def _has_accented(message: str, *phrases: str) -> bool:
    """Whole-word match that keeps Vietnamese accents: "liều" (dose) must not match "nguyên liệu"."""
    lowered = message.lower()
    return any(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", lowered) for phrase in phrases)


_RECIPE = re.compile(r"-(tao|lam|pha|xay|goi-y|de-xuat|len|cho-toi|viet)-.*-(sinh-to|cong-thuc|do-uong|nuoc-ep|smoothie|"
                     r"report|bao-cao|bua-sang|bua-phu|thuc-don)-")
_MEDICAL = ("thuốc", "chẩn đoán", "điều trị", "chữa bệnh", "chữa khỏi", "liều", "mang thai", "có thai", "cho con bú",
            "trẻ em", "trẻ sơ sinh", "insulin", "lọc máu", "suy thận", "ung thư", "phẫu thuật")
_SUITABILITY = ("có nên", "nên ăn", "nên uống", "được không", "có được", "phù hợp", "có sao không", "ăn được", "uống được",
                "tốt không", "có tốt", "có hại", "có ảnh hưởng")
_COMPARE = ("so sánh", "khác gì", "khác nhau", "cái nào", "loại nào", "tốt hơn", "nhiều hơn", "ít hơn")
_SEASONAL = ("theo mùa", "vào mùa", "đang mùa", "mùa này", "hoa quả mùa", "trái cây mùa",
             "quả theo mùa", "rau củ theo mùa", "mùa hiện tại", "tháng này", "đang vào mùa")
_ALL_CATALOG = ("tất cả trái cây", "tất cả hoa quả", "tất cả nguyên liệu", "danh sách trái cây",
                "danh sách nguyên liệu", "toàn bộ trái cây", "toàn bộ nguyên liệu", "tất cả các loại",
                "tất cả", "tôi muốn tất cả", "cho tôi tất cả", "xem tất cả")
_NUTRITION = ("dinh dưỡng", "calo", "calories", "kcal", "năng lượng", "protein", "đạm", "chất xơ", "đường", "vitamin",
              "chất béo", "carb", "natri", "khoáng", "bao nhiêu", "tìm hiểu", "thành phần", "giá trị", "mùa", "đang mùa")
_GREETING = ("xin chào", "chào bạn", "chào", "hello", "hi", "bạn là ai", "bạn làm được gì", "giúp gì", "hướng dẫn")
_FOLLOW_UP = ("còn", "thì sao", "nó", "loại đó", "cái đó", "món đó", "thế còn", "vậy còn")
# after the agent asked which ingredients to use: "tôi đã chọn rồi", "làm đi", "ok"
_CONTINUE_RECIPE = ("đã chọn", "chọn rồi", "chọn xong", "rồi đó", "làm đi", "tạo đi", "ok", "được rồi", "tiếp tục", "đồng ý")


def classify(message: str, ingredients: list[dict[str, Any]], unmatched: list[str],
             history: list[dict[str, Any]]) -> Intent:
    text = f"-{slugify(message)}-"
    previous = _previous_ingredients(history)
    from_history = False
    if not ingredients and previous and _has(text, *_FOLLOW_UP):
        ingredients, from_history = previous, True  # "còn ổi thì sao?" keeps talking about the same items
    if _has_accented(message, *_MEDICAL):
        kind = "medical_boundary"
    elif _last_intent(history) == "create_recipe" and _has_accented(message, *_CONTINUE_RECIPE):
        kind = "create_recipe"
    elif _RECIPE.search(text) or _has(text, "công thức", "sinh tố", "smoothie", "tạo report", "báo cáo pdf"):
        kind = "create_recipe"
    elif _has(text, *_SUITABILITY):
        kind = "suitability"
    elif len(ingredients) >= 2 and (_has(text, *_COMPARE) or (_has_accented(message, "hay", "hay là") and not _has_accented(message, "hãy"))):
        kind = "compare"
    elif _has_accented(message, *_SEASONAL, *_ALL_CATALOG) or _has(text, "theo-mua", "vao-mua", "dang-mua", "mua-nay", "mua-hien-tai") or (_has(text, "mua") and (_has(text, "trai-cay", "hoa-qua", "nguyen-lieu", "tat-ca", "danh-sach", "co-gi", "an-gi") or "theo" in text)) or (_has(text, "tat-ca", "toan-bo") and (_has(text, "trai-cay", "hoa-qua", "nguyen-lieu") or not ingredients)):
        kind = "seasonal"
    elif ingredients or _has(text, *_NUTRITION):
        kind = "nutrition_question"
    elif _has(text, *_GREETING):
        kind = "greeting"
    elif len(text.strip("-").split("-")) <= 3:
        kind = "nutrition_question"  # a bare name ("kiwi") is a lookup; the composer says when it is unknown
    else:
        kind = "general"
    return Intent(kind=kind, ingredients=ingredients, unmatched=unmatched, from_history=from_history)


def _last_intent(history: list[dict[str, Any]]) -> str | None:
    return next((m.get("intent") for m in reversed(history) if m.get("role") == "assistant"), None)


def _previous_ingredients(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.services.chat.tools import _canonical

    items = _canonical()
    for message in reversed(history):
        ids = (message.get("metadata") or {}).get("ingredient_ids") or []
        if message.get("role") == "assistant" and ids:
            return [items[i] for i in ids if i in items]
    return []
