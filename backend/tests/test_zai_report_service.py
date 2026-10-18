from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from app.config import settings
from app.services.zai_report_service import generate_report_narrative


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")


class ZaiReportServiceTests(unittest.TestCase):
    @patch("app.services.zai_report_service.urllib.request.urlopen")
    def test_zai_generates_editorial_copy_only(self, urlopen) -> None:
        urlopen.return_value = _Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "Sinh tố Cam và yến mạch",
                                    "steps": ["Rửa cam.", "Xay các nguyên liệu đã khóa.", "Dùng ngay."],
                                    "usage": "Dùng như bữa phụ.",
                                    "substitutions": "Thay nguyên liệu cần tạo report mới.",
                                    "summary": "Hương vị tươi nhẹ, dễ dùng.",
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }
        )
        with patch.object(settings, "llm_provider", "zai"), patch.object(settings, "zai_api_key", "test-key"):
            narrative = generate_report_narrative(
                goal="Quản lý cân nặng",
                ingredients=[{"name": "Cam", "amount": 120.0, "unit": "g"}],
                fallback={},
            )

        self.assertEqual(narrative["title"], "Sinh tố Cam và yến mạch")
        self.assertEqual(len(narrative["steps"]), 3)
        request_body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(request_body["model"], settings.zai_model)
        self.assertIn("- Cam: 120 g", request_body["messages"][1]["content"])
        self.assertEqual(request_body["response_format"]["type"], "json_object")

    @patch("app.services.zai_report_service.urllib.request.urlopen", side_effect=OSError("offline"))
    def test_zai_failure_falls_back_to_local_copy(self, _urlopen) -> None:
        with patch.object(settings, "llm_provider", "zai"), patch.object(settings, "zai_api_key", "test-key"):
            narrative = generate_report_narrative(
                goal="Quản lý cân nặng",
                ingredients=[{"name": "Cam", "amount": 120.0, "unit": "g"}],
                fallback={},
            )
        self.assertIsNone(narrative)
