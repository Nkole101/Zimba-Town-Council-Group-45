"""Offline regressions; all examples are synthetic, never dataset records."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cdf_scraper.py"
spec = importlib.util.spec_from_file_location("cdf", SCRIPT)
cdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdf)


class ParserTests(unittest.TestCase):
    def test_bundled_projects(self):
        cdf.run_self_test()

    def test_ambiguous_and_missing_amounts(self):
        self.assertEqual(cdf.extract_amount("K900,000 for a school and K200,000 for a clinic"), "")
        self.assertEqual(cdf.extract_amount("No cost was reported"), "")
        self.assertEqual(cdf.extract_amount("ZMW 1.2 million"), 1200000)

    def test_status_does_not_invent_completion(self):
        self.assertEqual(cdf.infer_status("The clinic is not completed"), "")
        self.assertEqual(cdf.infer_status("The school will be commissioned"), "")
        self.assertEqual(cdf.infer_status("Construction is ongoing"), "ongoing")

    def test_title_status_does_not_leak_to_other_projects(self):
        raw = '''<title>CDF completed projects</title><article>
        <p>Construction of a school is ongoing under CDF.</p>
        <p>Construction of a health clinic was discussed.</p></article>'''
        rows = cdf.scrape_post(raw, cdf.BASE_URL + "/?p=1")
        self.assertEqual([row["status"] for row in rows], ["ongoing", ""])

    def test_non_cdf_is_excluded(self):
        self.assertEqual(cdf.scrape_post("<article><p>Construction of a school funded by a private donor.</p></article>", cdf.BASE_URL), [])


if __name__ == "__main__":
    unittest.main()
