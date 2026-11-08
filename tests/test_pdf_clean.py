import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_pdf_proto import clean, generate_pdf_proto

class TestPdfClean(unittest.TestCase):
    def test_clean_unicode(self):
        text_with_unicode = (
            "# Climate & Medical AI: Impact in 2025\n\n"
            "## Key Findings\n"
            "- Global CO₂ emissions decreased by 4.2% [1].\n"
            "- Temperature anomalies reached +1.5°C across 12 countries.\n"
            "- Mathematical boundary: x ≤ 100 and y ≥ 50.\n"
            "- Punctuation test: “Smart Health”—a multi-agent system–verified with non‑breaking hyphens.\n"
            "- Verification badges: ✅ Verified, ⚠️ Partially Supported, ❌ Contradicted.\n"
        )
        cleaned_sample = clean(text_with_unicode)
        self.assertIn("CO<sub>2</sub>", cleaned_sample)
        self.assertIn("&deg;C", cleaned_sample)
        self.assertIn("&mdash;", cleaned_sample)
        self.assertIn("[Verified]", cleaned_sample)
        self.assertNotIn("✅", cleaned_sample)

    def test_pdf_generation_basic(self):
        pdf = generate_pdf_proto(
            report="# Empty Report\n\nNo findings.",
            query="Empty Test Topic",
            quality_score=0.0,
            citations=[],
            chart_json_list=[],
        )
        self.assertIsInstance(pdf, bytes)
        self.assertGreater(len(pdf), 1000)

if __name__ == "__main__":
    unittest.main()
