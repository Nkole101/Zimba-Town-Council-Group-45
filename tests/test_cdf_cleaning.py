"""Regression checks for Part 1 decisions that could otherwise lose data."""
import importlib.util
from pathlib import Path
import unittest

import pandas as pd

SPEC = importlib.util.spec_from_file_location("clean_cdf", Path(__file__).resolve().parents[1] / "scripts/clean_cdf.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CleaningTests(unittest.TestCase):
    def project(self, name="School", identifier="ZTC-001"):
        return {"project_id": identifier, "project_name": name, "sector": " Education ",
                "constituency": None, "funding_source": "CDF", "funding_amount_zmw": None,
                "status": None, "date_reported": "2026-01-01", "description": "<p>The school is not completed.</p>",
                "source_url": "https://www.zimbacouncil.gov.zm/?p=1"}

    def test_same_url_distinct_projects_survive_and_duplicate_id_does_not(self):
        rows = [self.project(), self.project(identifier="ZTC-003"), self.project("Other school", "ZTC-002")]
        cleaned, audit = module.clean(pd.DataFrame(rows), True)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(audit["duplicates_removed"], 1)
        self.assertTrue(cleaned["funding_amount_zmw"].isna().all())
        self.assertTrue(cleaned["status"].eq("unspecified").all())
        self.assertEqual(cleaned.iloc[0]["description_clean"], "school not completed")
        self.assertEqual(cleaned.iloc[0]["description"], rows[0]["description"])

    def test_invalid_amount_is_not_silently_discarded(self):
        row = self.project()
        row["funding_amount_zmw"] = "bad amount"
        with self.assertRaises(ValueError):
            module.clean(pd.DataFrame([row]), True)

    def test_source_content_variants_are_flagged_not_deleted(self):
        rows = [{"title": "News", "date": "2026-01-01", "body_text": body, "url": "https://www.zimbacouncil.gov.zm/?p=1"} for body in ["First text", "Second text"]]
        cleaned, audit = module.clean(pd.DataFrame(rows), False)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(len(audit["near_duplicate_review"]), 2)


if __name__ == "__main__":
    unittest.main()
