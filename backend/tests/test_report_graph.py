from __future__ import annotations

import unittest
import uuid
import time
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.agents.report_graph import report_graph
from app.main import app
from app.schemas.report_schema import RecipeProposal


def request_payload(*, allergies: list[str] | None = None, ingredients: list[str] | None = None) -> dict:
    return {
        "profile": {
            "age": 32,
            "gender": "Nữ",
            "height_cm": 165,
            "weight_kg": 75,
            "goal": "overweight_obesity_weight_management",
            "allergies": allergies or [],
            "preferred_food_types": ["Nhiều chất xơ"],
            "disliked_ingredients": [],
            "medical_notes": "",
            "health_restriction_status": "no",
        },
        "ingredientIds": ingredients or ["cam", "sua-dau-nanh", "yen-mach", "hat-chia"],
        "servings": 1,
        "prompt": "Bữa phụ no lâu",
        "locale": "vi-VN",
    }


def graph_input(payload: dict) -> dict:
    token = uuid.uuid4().hex[:10]
    return {
        "request": payload,
        "report_id": f"test_{token}",
        "thread_id": f"thread_{token}",
        "run_id": f"run_{token}",
        "errors": [],
        "warnings": [],
        "retry_count": 0,
        "execution_metadata": {},
    }


class ReportGraphTests(unittest.TestCase):
    def test_golden_nutrition_and_two_page_pdf(self) -> None:
        initial = graph_input(request_payload(ingredients=["cam", "yen-mach", "hat-chia"]))
        result = report_graph.invoke(initial, {"configurable": {"thread_id": initial["thread_id"]}})
        self.assertEqual(result["decision"], "review")
        totals = result["nutrition_calculation"]["totals"]
        self.assertEqual(totals["calories"], 198.67)
        self.assertEqual(totals["protein"], 6.36)
        self.assertEqual(
            [item["ingredient_id"] for item in result["report_document"]["ingredients"]],
            ["cam", "yen-mach", "hat-chia"],
        )
        pdf_path = Path(result["pdf_metadata"]["path"])
        reader = PdfReader(pdf_path)
        self.assertEqual(len(reader.pages), 2)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        for heading in ("NGUYÊN LIỆU", "CÁCH CHẾ BIẾN", "Phân tích dinh dưỡng", "NGƯỠNG ĐÁNH GIÁ"):
            self.assertIn(heading, text)
        self.assertIn(initial["report_id"], text)

    def test_unknown_data_is_review_not_invented(self) -> None:
        initial = graph_input(request_payload(ingredients=["cam", "nguyen-lieu-chua-co"]))
        result = report_graph.invoke(initial, {"configurable": {"thread_id": initial["thread_id"]}})
        self.assertEqual(result["decision"], "review")
        unknown = result["report_document"]["ingredient_nutrition"][1]["nutrition"]
        self.assertTrue(all(value is None for value in unknown.values()))
        self.assertLess(result["report_document"]["data_coverage"], 1)
        self.assertIsNone(result["report_document"]["totals"]["calories"])

    def test_allergy_conflict_rejects_without_pdf(self) -> None:
        initial = graph_input(request_payload(allergies=["Sữa đậu nành"]))
        result = report_graph.invoke(initial, {"configurable": {"thread_id": initial["thread_id"]}})
        self.assertEqual(result["decision"], "reject")
        self.assertFalse(result.get("pdf_metadata"))
        self.assertTrue(any("dị ứng" in error.lower() for error in result["errors"]))


class ReportApiTests(unittest.TestCase):
    @staticmethod
    def _wait(client: TestClient, report_id: str, statuses: set[str]) -> dict:
        payload = client.get(f"/v1/reports/{report_id}").json()
        for _ in range(150):
            if payload["status"] in statuses:
                return payload
            time.sleep(0.02)
            payload = client.get(f"/v1/reports/{report_id}").json()
        return payload

    def test_create_status_events_and_download(self) -> None:
        client = TestClient(app)
        created = client.post("/v1/reports", json=request_payload())
        self.assertEqual(created.status_code, 202)
        report_id = created.json()["report_id"]
        status_response = client.get(f"/v1/reports/{report_id}")
        for _ in range(100):
            if status_response.json()["status"] in {"completed", "review", "failed", "rejected"}:
                break
            time.sleep(0.02)
            status_response = client.get(f"/v1/reports/{report_id}")
        self.assertEqual(status_response.status_code, 200)
        self.assertIn(status_response.json()["status"], {"completed", "review"})
        self.assertEqual(client.get(f"/v1/reports/{report_id}/pdf").status_code, 200)

    def test_idempotency_key_reuses_same_job(self) -> None:
        client = TestClient(app)
        headers = {"Idempotency-Key": f"test-{uuid.uuid4().hex}"}
        first = client.post("/v1/reports", json=request_payload(ingredients=["cam", "yen-mach"]), headers=headers)
        second = client.post("/v1/reports", json=request_payload(ingredients=["cam", "yen-mach"]), headers=headers)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["report_id"], second.json()["report_id"])

    def test_suggested_ingredient_requires_versioned_confirmation(self) -> None:
        calls = {"count": 0}

        def proposal(**kwargs):
            calls["count"] += 1
            selected_ids = [item["ingredient_id"] for item in kwargs["selected"]]
            ingredient_ids = [*selected_ids]
            suggested = []
            if calls["count"] == 1:
                ingredient_ids.append("hat-chia")
                suggested = ["hat-chia"]
            result = RecipeProposal.model_validate(
                {
                    "version": 1,
                    "title": "Sinh tố xác nhận",
                    "ingredients": [
                        {"ingredient_id": item, "amount": 10 if item == "hat-chia" else 100, "unit": "g", "reason": "test"}
                        for item in ingredient_ids
                    ],
                    "suggested_ingredient_ids": suggested,
                    "steps": ["Rửa nguyên liệu.", "Cân nguyên liệu.", "Xay và dùng ngay."],
                    "prep_minutes": 8,
                    "rationale": "Test xác nhận.",
                    "ai_provider": "test",
                    "ai_model": "test",
                    "prompt_version": "test-v1",
                }
            )
            return result, {"mode": "test", "usage": {}, "repairs": 0}

        client = TestClient(app)
        with patch("app.agents.report_graph.generate_recipe_proposal", side_effect=proposal):
            created = client.post("/v1/reports", json=request_payload(ingredients=["cam", "yen-mach"]))
            report_id = created.json()["report_id"]
            waiting = self._wait(client, report_id, {"awaiting_confirmation", "failed"})
            self.assertEqual(waiting["status"], "awaiting_confirmation")
            self.assertTrue(waiting["confirmation_required"])
            confirmed = client.post(
                f"/v1/reports/{report_id}/confirmation",
                json={"proposal_version": 1, "accepted_ingredient_ids": ["hat-chia"]},
            )
            self.assertEqual(confirmed.status_code, 200)
            done = self._wait(client, report_id, {"completed", "review", "failed", "rejected"})
            self.assertIn(done["status"], {"completed", "review"})
            self.assertIn("Hạt chia", [item["name"] for item in done["report"]["ingredients"]])


if __name__ == "__main__":
    unittest.main()
