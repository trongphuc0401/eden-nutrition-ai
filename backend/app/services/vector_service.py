from sqlalchemy import select, text
from sqlalchemy.orm import Session

from openai import OpenAI

from app.config import settings
from app.models.nutrition_knowledge import NutritionKnowledge
from app.schemas.profile_schema import ProfileInput


def ensure_pgvector_extension(db: Session) -> None:
    db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    db.commit()


def build_knowledge_embedding_text(knowledge: NutritionKnowledge) -> str:
    return "\n".join(
        [
            f"title: {knowledge.title}",
            f"source: {knowledge.source or 'unknown'}",
            f"tags: {', '.join(knowledge.tags or []) or 'none'}",
            f"content: {knowledge.content}",
        ]
    )


def build_profile_search_query(profile: ProfileInput) -> str:
    return "\n".join(
        [
            "Vietnamese adult overweight obesity smoothie nutrition guidance",
            f"goal: {profile.goal}",
            f"allergies: {', '.join(profile.allergies) or 'none'}",
            f"preferred food types: {', '.join(profile.preferred_food_types) or 'none'}",
            f"disliked ingredients: {', '.join(profile.disliked_ingredients) or 'none'}",
            f"medical notes: {profile.medical_notes or 'none'}",
            "focus: weight management, fiber, protein, sugar, fat, seasonal Vietnamese ingredients",
        ]
    )


class VectorService:
    def __init__(self, client: OpenAI | None = None) -> None:
        if client is not None:
            self.client = client
            return

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required to create embeddings.")

        self.client = OpenAI(api_key=settings.openai_api_key)

    def create_embedding(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding

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
    ) -> list[NutritionKnowledge]:
        query_embedding = self.create_embedding(build_profile_search_query(profile))
        statement = (
            select(NutritionKnowledge)
            .where(NutritionKnowledge.embedding.is_not(None))
            .order_by(NutritionKnowledge.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        return list(db.scalars(statement).all())


def format_knowledge_context(knowledge_items: list[NutritionKnowledge]) -> list[str]:
    return [
        f"Title: {item.title}\nSource: {item.source or 'unknown'}\nContent: {item.content}"
        for item in knowledge_items
    ]
