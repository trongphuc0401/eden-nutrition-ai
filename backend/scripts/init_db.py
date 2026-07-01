from pathlib import Path
import sys

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


def main() -> None:
    print(f"Creating database tables using DATABASE_URL={settings.database_url}")
    Base.metadata.create_all(bind=engine)
    print("Database tables are ready.")


if __name__ == "__main__":
    main()
