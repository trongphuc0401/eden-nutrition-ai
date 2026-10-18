from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.nutrition_knowledge import NutritionKnowledge
from app.schemas.profile_schema import ProfileInput


VIETNAMESE_ORIGIN_VALUES = ["Vietnam", "Viet Nam", "Việt Nam"]
FRUIT_CATEGORY_VALUES = ["fruit", "trái cây", "trai cay"]


def format_tags(tags: dict | list | None) -> str:
    if not tags:
        return "không có"
    if isinstance(tags, list):
        return ", ".join(str(tag) for tag in tags)
    labels = tags.get("labels")
    if isinstance(labels, list):
        return ", ".join(str(tag) for tag in labels)
    return ", ".join(f"{key}={value}" for key, value in tags.items() if key != "raw_values")


def ensure_pgvector_extension(db: Session) -> None:
    db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    db.commit()


def build_knowledge_embedding_text(knowledge: NutritionKnowledge) -> str:
    return "\n".join(
        [
            f"tiêu đề: {knowledge.title}",
            f"nguyên liệu: {knowledge.ingredient_name or 'không rõ'}",
            f"nhóm: {knowledge.category or 'không rõ'}",
            f"nguồn gốc: {knowledge.origin_country or 'không rõ'}",
            f"vùng: {knowledge.region or 'không rõ'}",
            f"mùa vụ: {', '.join(str(month) for month in knowledge.season_months or []) or 'không rõ'}",
            f"được dùng trong sinh tố: {knowledge.allowed_for_smoothie}",
            f"nguồn dữ liệu: {knowledge.source or 'không rõ'}",
            f"nhãn: {format_tags(knowledge.tags)}",
            f"nội dung: {knowledge.content}",
        ]
    )


def build_profile_search_query(profile: ProfileInput) -> str:
    return "\n".join(
        [
            "Truy vấn dinh dưỡng sinh tố cho người trưởng thành Việt Nam thừa cân hoặc béo phì",
            f"mục tiêu: {profile.goal}",
            f"dị ứng: {', '.join(profile.allergies) or 'không có'}",
            f"sở thích thực phẩm: {', '.join(profile.preferred_food_types) or 'không có'}",
            f"nguyên liệu không thích: {', '.join(profile.disliked_ingredients) or 'không có'}",
            f"ghi chú sức khỏe: {profile.medical_notes or 'không có'}",
            "trọng tâm: quản lý cân nặng, chất xơ, protein, hạn chế đường/chất béo, nguyên liệu Việt Nam theo mùa",
        ]
    )


def _embedding_provider() -> str:
    return (settings.embedding_provider or "openai").strip().lower()


def _embedding_api_key() -> str | None:
    return settings.embedding_api_key or settings.llm_api_key or settings.openai_api_key


def _embedding_model() -> str:
    return settings.embedding_model or settings.openai_embedding_model


def _embedding_base_url() -> str | None:
    if settings.embedding_base_url:
        return settings.embedding_base_url

    provider_urls = {
        "gemini": "https://generativelanguage.googleapis.com/v1beta",
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "cerebras": "https://api.cerebras.ai/v1",
    }
    return provider_urls.get(_embedding_provider())


@dataclass
class _EmbeddingClient:
    provider: str
    api_key: str
    base_url: str
    model: str
    output_dimensionality: int

    def create_embedding(self, text: str) -> list[float]:
        if self.provider == "gemini":
            return self._create_gemini_embedding(text)
        return self._create_openai_compatible_embedding(text)

    def _create_openai_compatible_embedding(self, text: str) -> list[float]:
        payload = {"model": self.model, "input": text}
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["data"][0]["embedding"]

    def _create_gemini_embedding(self, text: str) -> list[float]:
        payload = {
            "content": {"parts": [{"text": text}]},
            "output_dimensionality": self.output_dimensionality,
        }
        request = urllib.request.Request(
            f"{self.base_url}/models/{self.model}:embedContent",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))

        values = (body.get("embedding") or {}).get("values")
        if values is None and body.get("embeddings"):
            values = body["embeddings"][0].get("values")
        if not values:
            raise ValueError("Gemini embedding response did not contain vector values.")
        return values


def _build_embedding_client() -> _EmbeddingClient:
    provider = _embedding_provider()
    api_key = _embedding_api_key()
    base_url = _embedding_base_url()
    if not api_key or not base_url:
        raise ValueError("An embeddings provider API key is required to create embeddings.")
    return _EmbeddingClient(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=_embedding_model(),
        output_dimensionality=settings.embedding_dimensionality,
    )


class VectorService:
    def __init__(self, client: _EmbeddingClient | None = None) -> None:
        self.client = client or _build_embedding_client()

    def create_embedding(self, text: str) -> list[float]:
        return self.client.create_embedding(text)

    def embed_knowledge_item(
        self,
        db: Session,
        knowledge: NutritionKnowledge,
    ) -> NutritionKnowledge:
        knowledge.embedding = self.create_embedding(build_knowledge_embedding_text(knowledge))
        db.add(knowledge)
        db.commit()
        db.refresh(knowledge)
        return knowledge

    def search_knowledge(
        self,
        db: Session,
        profile: ProfileInput,
        limit: int = 5,
        require_vietnamese_fruits: bool = True,
    ) -> list[NutritionKnowledge]:
        query_embedding = self.create_embedding(build_profile_search_query(profile))
        statement = select(NutritionKnowledge).where(NutritionKnowledge.embedding.is_not(None))

        if require_vietnamese_fruits:
            statement = statement.where(
                NutritionKnowledge.allowed_for_smoothie.is_(True),
                or_(
                    NutritionKnowledge.category.not_in(FRUIT_CATEGORY_VALUES),
                    (
                        NutritionKnowledge.category.in_(FRUIT_CATEGORY_VALUES)
                        & NutritionKnowledge.origin_country.in_(VIETNAMESE_ORIGIN_VALUES)
                    ),
                ),
            )

        statement = statement.order_by(
            NutritionKnowledge.embedding.cosine_distance(query_embedding)
        ).limit(limit)
        return list(db.scalars(statement).all())


def format_knowledge_context(knowledge_items: list[NutritionKnowledge]) -> list[str]:
    return [
        "\n".join(
            [
                f"Tiêu đề: {item.title}",
                f"Nguyên liệu: {item.ingredient_name or 'không rõ'}",
                f"Nhóm: {item.category or 'không rõ'}",
                f"Nguồn gốc: {item.origin_country or 'không rõ'}",
                f"Vùng/ghi chú: {item.region or 'không rõ'}",
                f"Tháng mùa vụ: {', '.join(str(month) for month in item.season_months or []) or 'không rõ'}",
                f"Được phép dùng trong sinh tố: {item.allowed_for_smoothie}",
                f"Nguồn dữ liệu: {item.source or 'không rõ'}",
                f"Nội dung: {item.content}",
            ]
        )
        for item in knowledge_items
    ]
