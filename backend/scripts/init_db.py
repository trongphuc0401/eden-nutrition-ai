from pathlib import Path
import sys
from urllib.parse import urlsplit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.database import Base, engine
from app.models import (  # noqa: F401
    ClinicalSafetyRule,
    NutritionKnowledge,
    NutritionThreshold,
    SmoothiePlan,
    User,
    UserProfile,
)
from sqlalchemy import text


def mask_database_url(raw_url: str) -> str:
    normalized = raw_url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlsplit(normalized)
    if not parsed.hostname:
        return "<invalid DATABASE_URL>"
    username = parsed.username or ""
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{username}:***@{parsed.hostname}{port}{parsed.path}"


def main() -> None:
    print(f"Creating database tables using DATABASE_URL={mask_database_url(settings.database_url)}")
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    print("Database tables are ready.")


if __name__ == "__main__":
    main()
