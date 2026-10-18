from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


class ReportEvalDatasetTests(unittest.TestCase):
    def test_dataset_has_locked_100_case_distribution(self) -> None:
        path = Path(__file__).resolve().parents[1] / "evals" / "report_eval_cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 100)
        self.assertEqual(
            Counter(case["category"] for case in cases),
            {
                "normal": 40,
                "allergy_exclusion": 20,
                "missing_data_unit": 15,
                "model_failure_injection": 15,
                "confirmation_cancel_recovery": 10,
            },
        )
        self.assertEqual(len({case["id"] for case in cases}), 100)


if __name__ == "__main__":
    unittest.main()
