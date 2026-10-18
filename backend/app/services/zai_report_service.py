from __future__ import annotations

import json
import urllib.request
from typing import Any

from app.config import settings


def zai_is_configured() -> bool:
    return settings.llm_provider.strip().lower() == "zai" and bool(settings.zai_api_key)


def _read_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].removeprefix("json").strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Z.AI must return a JSON object.")
    return payload


def _bounded_text(value: Any, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned[:limit] if cleaned else None


def generate_report_narrative(
    *,
    goal: str,
    ingredients: list[dict[str, Any]],
    fallback: dict[str, Any],
) -> dict[str, Any] | None:
    """Use Z.AI only for Vietnamese editorial copy, never nutrition or amounts."""
    if not zai_is_configured():
        return None

    ingredient_lines = "\n".join(
        f"- {item['name']}: {item['amount']:g} {item['unit']}"
        for item in ingredients
    )
    prompt = f"""Bạn là biên tập viên tiếng Việt cho báo cáo sinh tố dinh dưỡng.
Mục tiêu: {goal}
Nguyên liệu và định lượng đã bị khóa (không được đổi, thêm, hoặc bỏ):
{ingredient_lines}

Viết JSON thuần với các khóa title, steps, usage, substitutions, summary.
- title: tối đa 90 ký tự.
- steps: mảng 3 đến 6 bước, mỗi bước tối đa 180 ký tự.
- usage: tối đa 380 ký tự.
- substitutions: tối đa 300 ký tự, chỉ nhắc thay thế sau khi tính lại report.
- summary: tối đa 500 ký tự, ngôn ngữ dễ hiểu.
Không viết calories, macro, số liệu dinh dưỡng, chẩn đoán y khoa hoặc nguyên liệu/định lượng mới.
"""
    request = urllib.request.Request(
        f"{settings.zai_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": settings.zai_model,
                "messages": [
                    {"role": "system", "content": "Return only valid JSON. Follow the user's fixed ingredients exactly."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.25,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.zai_api_key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            body = json.loads(response.read().decode("utf-8"))
        message = body["choices"][0]["message"]["content"]
        payload = _read_json(message)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, OSError):
        return None

    title = _bounded_text(payload.get("title"), 90)
    usage = _bounded_text(payload.get("usage"), 380)
    substitutions = _bounded_text(payload.get("substitutions"), 300)
    summary = _bounded_text(payload.get("summary"), 500)
    raw_steps = payload.get("steps")
    steps = [_bounded_text(step, 180) for step in raw_steps] if isinstance(raw_steps, list) else []
    steps = [step for step in steps if step][:6]
    if not title or not usage or not substitutions or not summary or not 3 <= len(steps) <= 6:
        return None
    return {
        "title": title,
        "steps": steps,
        "usage": usage,
        "substitutions": substitutions,
        "ai_summary": summary,
        "ai_provider": "zai",
        "ai_model": settings.zai_model,
    }
