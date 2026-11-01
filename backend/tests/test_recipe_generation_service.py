from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import settings
from app.schemas.report_schema import RecipeProposal
from app.services.recipe_generation_service import (
    RecipeGenerationError,
    blocked_ingredient_ids,
    generate_recipe_proposal,
    validate_proposal,
)
from app.services.report_data_service import resolve_ingredients


PROFILE = {
    "age": 32,
    "gender": "Nữ",
    "height_cm": 165,
    "weight_kg": 75,
    "goal": "overweight_obesity_weight_management",
    "allergies": [],
    "disliked_ingredients": [],
    "medical_notes": "",
    "health_restriction_status": "no",
}


class RecipeGenerationTests(unittest.TestCase):
    def test_mock_mode_is_explicit_in_metadata(self) -> None:
        selected, _ = resolve_ingredients(["cam", "yen-mach"])
        with patch.object(settings, "report_recipe_mode", "mock"):
            proposal, metadata = generate_recipe_proposal(
                profile=PROFILE,
                selected=selected,
                servings=1,
                user_prompt="ít ngọt",
                allow_suggestions=True,
                rejected_ids=[],
            )
        self.assertEqual(proposal.ai_provider, "mock")
        self.assertEqual(metadata["mode"], "mock")

    def test_zai_mode_without_key_fails_instead_of_falling_back(self) -> None:
        selected, _ = resolve_ingredients(["cam"])
        with patch.object(settings, "report_recipe_mode", "zai"), patch.object(settings, "zai_api_key", None):
            with self.assertRaises(RecipeGenerationError):
                generate_recipe_proposal(
                    profile=PROFILE,
                    selected=selected,
                    servings=1,
                    user_prompt="",
                    allow_suggestions=False,
                    rejected_ids=[],
                )

    def test_validator_rejects_allergen_and_unknown_catalog_id(self) -> None:
        profile = {**PROFILE, "allergies": ["Đậu nành"]}
        proposal = RecipeProposal.model_validate(
            {
                "title": "Test",
                "ingredients": [
                    {"ingredient_id": "sua-dau-nanh", "amount": 200, "unit": "ml", "reason": "nền"},
                    {"ingredient_id": "tu-tao", "amount": 100, "unit": "g", "reason": "test"},
                ],
                "suggested_ingredient_ids": ["tu-tao"],
                "steps": ["Một", "Hai", "Ba"],
                "prep_minutes": 5,
                "rationale": "Test validator",
                "ai_provider": "test",
                "ai_model": "test",
                "prompt_version": "test",
            }
        )
        errors = validate_proposal(proposal, profile, {"sua-dau-nanh"}, True)
        self.assertTrue(any("bị chặn" in error for error in errors))
        self.assertTrue(any("catalog" in error for error in errors))

    def test_allergen_alias_maps_to_catalog_id(self) -> None:
        self.assertIn("sua-dau-nanh", blocked_ingredient_ids({**PROFILE, "allergies": ["soy"]}))

    def test_validator_rejects_step_that_mentions_unlisted_ingredient_or_amount(self) -> None:
        proposal = RecipeProposal.model_validate(
            {
                "title": "Test",
                "ingredients": [{"ingredient_id": "cam", "amount": 100, "unit": "g", "reason": "trái cây"}],
                "steps": ["Rửa cam.", "Thêm 50 g yến mạch.", "Xay đến khi mịn."],
                "prep_minutes": 5,
                "rationale": "Test validator",
                "ai_provider": "test",
                "ai_model": "test",
                "prompt_version": "test",
            }
        )
        errors = validate_proposal(proposal, PROFILE, {"cam"}, False)
        self.assertTrue(any("ngoài công thức" in error for error in errors))
        self.assertTrue(any("định lượng" in error for error in errors))

    @patch("app.services.recipe_generation_service._call_zai")
    def test_schema_error_is_repaired_within_limit(self, call_zai) -> None:
        call_zai.side_effect = [
            ({"title": "Thiếu dữ liệu"}, {}, "glm-4.7-flash"),
            (
                {
                    "title": "Sinh tố cam",
                    "ingredients": [{"ingredient_id": "cam", "amount": 120, "unit": "g", "reason": "trái cây"}],
                    "suggested_ingredient_ids": [],
                    "steps": ["Rửa cam.", "Cho cam vào máy.", "Xay mịn và dùng ngay."],
                    "prep_minutes": 5,
                    "rationale": "Công thức đơn giản.",
                },
                {"total_tokens": 100},
                "glm-4.5-flash",
            ),
        ]
        selected, _ = resolve_ingredients(["cam"])
        with patch.object(settings, "report_recipe_mode", "zai"), patch.object(settings, "zai_api_key", "test-key"):
            proposal, metadata = generate_recipe_proposal(
                profile=PROFILE,
                selected=selected,
                servings=1,
                user_prompt="",
                allow_suggestions=False,
                rejected_ids=[],
            )
        self.assertEqual(proposal.repair_count, 1)
        self.assertEqual(metadata["repairs"], 1)
        self.assertEqual(proposal.ai_model, "glm-4.5-flash")

    def test_rate_limited_model_falls_back_to_next_free_model(self) -> None:
        import io
        import json as jsonlib
        import time as timelib
        from urllib.error import HTTPError

        from app.services.recipe_generation_service import _call_zai

        calls: list[str] = []

        def fake_urlopen(request, timeout):
            model = jsonlib.loads(request.data)["model"]
            calls.append(model)
            if model == "glm-4.7-flash":
                raise HTTPError(request.full_url, 429, "Too Many Requests", {}, io.BytesIO(b"{}"))
            body = {"choices": [{"message": {"content": '{"title": "ok"}'}}], "usage": {}}
            return io.BytesIO(jsonlib.dumps(body).encode())

        with patch.object(settings, "zai_api_key", "test-key"), patch.object(settings, "zai_model", "glm-4.7-flash"),                 patch("app.services.recipe_generation_service.urllib.request.urlopen", side_effect=fake_urlopen):
            payload, _, model = _call_zai("prompt", timelib.monotonic() + 30)
        self.assertEqual(payload, {"title": "ok"})
        self.assertEqual(model, "glm-4.5-flash")
        self.assertEqual(calls, ["glm-4.7-flash", "glm-4.5-flash"])


if __name__ == "__main__":
    unittest.main()
