from pathlib import Path
import sys

from fastapi.testclient import TestClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.main import app


def main() -> None:
    client = TestClient(app)
    payload = {
        "age": 24,
        "gender": "male",
        "height_cm": 170,
        "weight_kg": 78,
        "goal": "overweight_obesity_weight_management",
        "allergies": ["milk"],
        "preferred_food_types": ["Vietnamese tropical fruits", "high-fiber ingredients"],
        "disliked_ingredients": ["banana"],
        "medical_notes": "",
    }

    for method, url in [
        ("GET", "/health"),
        ("POST", "/profiles/analyze"),
        ("POST", "/knowledge/search-preview?limit=3"),
        ("POST", "/smoothies/generate?use_rag=true&knowledge_limit=3"),
    ]:
        if method == "GET":
            response = client.get(url)
        else:
            response = client.post(url, json=payload)

        print(f"{method} {url} -> {response.status_code}")
        print(response.json())
        print()


if __name__ == "__main__":
    main()
