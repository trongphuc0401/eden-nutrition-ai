"""Create tables and apply SQL migrations. Safe to re-run; used as Render's pre-deploy command."""
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(BACKEND_ROOT))

from app.database import engine
from scripts.init_db import main as init_db

MIGRATIONS_DIR = BACKEND_ROOT / "migrations"


def main() -> None:
    init_db()
    for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
        print(f"Applying {migration.name}")
        with engine.begin() as connection:
            connection.exec_driver_sql(migration.read_text(encoding="utf-8"))
    print("Migrations applied.")


if __name__ == "__main__":
    main()
