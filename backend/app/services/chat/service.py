"""Chat turn orchestration -> Server-Sent Events.

Events (in order): thread, status*, delta*, cards, actions, done  |  error
Each status names the concrete step the agent is doing, so the UI never shows a bare spinner.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from app.config import settings
from app.services.chat.composer import compose, stream_answer
from app.services.chat.intents import classify
from app.services.chat.store import chat_store
from app.services.chat.tools import catalog_ids, data_context, find_ingredients

logger = logging.getLogger(__name__)

STATUS_TEXT = {
    "create_recipe": "Đang chuẩn bị yêu cầu tạo công thức…",
    "nutrition_question": "Đang tra dữ liệu dinh dưỡng{names}…",
    "compare": "Đang so sánh{names} theo dữ liệu trên 100 g…",
    "suitability": "Đang đối chiếu{names} với hồ sơ sức khỏe của bạn…",
    "seasonal": "Đang tổng hợp các nguyên liệu đang vào mùa{names}…",
    "medical_boundary": "Đang kiểm tra phạm vi tư vấn an toàn…",
    "greeting": "Đang chuẩn bị gợi ý…",
    "general": "Đang tìm cách hỗ trợ phù hợp…",
}


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def run_turn(*, owner_id: str, message: str, profile: dict[str, Any], thread_id: str | None,
             selected_ids: list[str], model: str | None = None) -> Iterator[str]:
    try:
        if not thread_id or not chat_store.owns(thread_id, owner_id):
            thread_id = chat_store.create_thread(owner_id, message[:80])
        else:
            chat_store.update_title_if_default(thread_id, owner_id, message[:80])
        history = chat_store.history(thread_id, settings.chat_history_messages)
        chat_store.append(thread_id, "user", message)
        yield sse("thread", {"thread_id": thread_id})

        yield sse("status", {"step": "understand", "text": "Đang hiểu câu hỏi của bạn…"})
        ingredients, unmatched = find_ingredients(message)
        intent = classify(message, ingredients, unmatched, history)
        if intent.kind == "seasonal" and not intent.ingredients:
            from app.services.chat.tools import catalog_ingredients, seasonal_ingredients
            from app.services.report_data_service import slugify
            text_slug = f"-{slugify(message)}-"
            if any(k in text_slug for k in ("mua", "theo-mua", "dang-mua", "vao-mua")):
                intent.ingredients = seasonal_ingredients(datetime.now().month, profile.get("hometown"))
            else:
                intent.ingredients = catalog_ingredients()
        names = f" ({len(intent.ingredients)} nguyên liệu)" if intent.kind == "seasonal" else (f" {', '.join(item['name'] for item in intent.ingredients)}" if intent.ingredients else "")
        yield sse("status", {"step": intent.kind, "text": STATUS_TEXT[intent.kind].format(names=names)})
        if intent.ingredients and intent.kind in ("suitability", "nutrition_question", "compare"):
            yield sse("status", {"step": "profile", "text": "Đang kiểm tra dị ứng và ghi chú sức khỏe trong hồ sơ…"})

        answer = compose(intent, message, profile, catalog_ids(datetime.now().month, profile.get("hometown")), selected_ids)
        text_parts: list[str] = []
        for chunk in stream_answer(answer, message, history, model):
            text_parts.append(chunk)
            yield sse("delta", {"text": chunk})
        if answer.cards:
            yield sse("cards", {"cards": answer.cards})
        if answer.actions:
            yield sse("actions", {"actions": answer.actions})
        context = data_context()
        message_id = chat_store.append(thread_id, "assistant", "".join(text_parts), intent.kind, {
            "ingredient_ids": answer.ingredient_ids, "cards": answer.cards, "actions": answer.actions,
            "from_history": intent.from_history, "model": model, **context,
        })
        yield sse("done", {"message_id": message_id, "intent": intent.kind, "thread_id": thread_id, "model": model, **context})
    except Exception as error:  # the stream must end with a readable event, never a dropped connection
        logger.exception("chat turn failed")
        yield sse("error", {"message": "Trợ lý chưa trả lời được vì lỗi hệ thống. Câu hỏi của bạn vẫn được giữ, bạn có thể thử lại.",
                            "code": type(error).__name__})
