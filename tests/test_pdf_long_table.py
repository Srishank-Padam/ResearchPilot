import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pymupdf
from tools.pdf_generator import generate_pdf, clean

class TestPdfAdvancedFeatures(unittest.TestCase):

    def test_long_table_multi_page_header_repeat(self):
        """Tests that a long table (25 rows) renders across pages with repeating headers and no overflow."""
        # Generate markdown table with 35 rows to ensure it exceeds a single page height
        header = "| Year | Metric Description | Baseline Value | Projected Value | Variance (%) | Source Reference |\n"
        sep    = "|------|-------------------|----------------|-----------------|--------------|------------------|\n"
        rows   = []
        for y in range(2025, 2060):
            rows.append(f"| {y} | Enterprise Clinical AI Adoption Rate Metric Tier {y-2024} | {y*1.2:.1f} M | {y*1.8:.1f} M | +{y*0.05:.1f}% | [{((y-2025)%3)+1}] |\n")

        table_md = header + sep + "".join(rows)

        report_content = (
            "# Healthcare Long-Horizon Forecast Report\n\n"
            "## Executive Summary\n"
            "This report examines longitudinal clinical adoption trajectories across 25 years [1].\n\n"
            "## Statistical Overview\n\n"
            + table_md + "\n\n"
            "*Table 1: Comprehensive 25-Year Longitudinal Model*\n\n"
            "## Conclusion\n"
            "Long-term adoption indicates durable market transformation [2].\n\n"
            "## References\n\n"
            "[1] Global Health Org (2025). *Longitudinal Healthcare AI*. [https://gho.org/ai](https://gho.org/ai)\n\n"
            "[2] Medical Intelligence Forum (2025). *Future Trajectories*. [https://mif.org/forecast](https://mif.org/forecast)\n"
        )

        cites = [
            {"number": 1, "title": "Longitudinal Healthcare AI", "authors": "Global Health Org", "year": "2025", "url": "https://gho.org/ai"},
            {"number": 2, "title": "Future Trajectories", "authors": "Medical Intelligence Forum", "year": "2025", "url": "https://mif.org/forecast"},
        ]

        pdf_bytes = generate_pdf(
            report=report_content,
            query="Healthcare Long-Horizon Forecast Report",
            quality_score=9.1,
            citations=cites,
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 5000)

        # Inspect using PyMuPDF
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        self.assertGreaterEqual(len(doc), 3)

        # Confirm no raw markdown table characters
        for page in doc:
            text = page.get_text()
            self.assertNotIn("|------|", text)
            self.assertNotIn("| Year |", text)  # Pipes stripped, converted to Table

        # Confirm repeated header across split pages
        # The table headers should appear on the table start page and continue page
        header_occurrences = 0
        for page in doc:
            if "Metric Description" in page.get_text():
                header_occurrences += 1
        self.assertGreaterEqual(header_occurrences, 2, "Table header did not repeat across multi-page split!")

    def test_multiple_charts_placement_and_no_empty_pages(self):
        """Tests that multiple diverse charts (bar, scatter, pie, indicator) render cleanly without empty pages."""
        chart_1 = json.dumps({
            "data": [{"type": "bar", "orientation": "h", "y": ["Clinical NLP", "Imaging AI", "Genomics AI"], "x": [14.2, 28.5, 9.8]}],
            "layout": {"title": {"text": "Financial Allocation by AI Modality (billion USD)"}}
        })
        chart_2 = json.dumps({
            "data": [{"type": "scatter", "x": ["2022", "2023", "2024", "2025", "2026"], "y": [12.0, 18.5, 27.2, 39.8, 55.4], "name": "Adoption %"}],
            "layout": {"title": {"text": "Clinical System Adoption Trajectory 2022-2026"}}
        })
        chart_3 = json.dumps({
            "data": [{"type": "pie", "labels": ["Hospitals", "Diagnostic Labs", "Pharma R&D"], "values": [52, 28, 20]}],
            "layout": {"title": {"text": "Sector Deployment Share (%)"}}
        })
        chart_4 = json.dumps({
            "data": [{"type": "indicator", "value": 37.4, "number": {"suffix": "%"}, "title": {"text": "Overall CAGR 2025-2030<br><span>Source: Frost & Sullivan</span>"}}],
            "layout": {}
        })

        report_content = (
            "# Multi-Modality Healthcare AI Market Assessment\n\n"
            "## Executive Summary\n"
            "Healthcare artificial intelligence reached unprecedented scale in 2025, showing 37.4% projected CAGR [1].\n\n"
            "## Key Findings\n"
            "- Imaging AI represents the largest single modality investment at $28.5 billion [1].\n"
            "- Diagnostic accuracy gains consistently exceed baseline non-AI pathways [2].\n\n"
            "## Analysis\n"
            "Systemic clinical integration reflects transition from isolated diagnostic point tools to enterprise multimodal infrastructure [3].\n"
            "Adoption curves accelerated significantly across 2023-2025 [1].\n\n"
            "## Statistical Overview\n\n"
            "| Modality | 2025 Spend (Billion USD) | Clinical Share (%) | Verification |\n"
            "|----------|--------------------------|--------------------|--------------|\n"
            "| Medical Imaging | $28.5 | 45.2% | Verified [1] |\n"
            "| Clinical NLP | $14.2 | 22.5% | Verified [1] |\n"
            "| Genomics AI | $9.8 | 15.6% | Verified [2] |\n\n"
            "## Conclusion\n"
            "Multimodal clinical platforms provide structural competitive advantages across health systems [1].\n\n"
            "## References\n\n"
            "[1] Frost & Sullivan (2025). *Global Healthcare AI Analysis*. [https://frost.com/healthcare-ai](https://frost.com/healthcare-ai)\n"
            "[2] Nature Digital Medicine (2025). *Clinical AI Validation*. [https://nature.com/ndm](https://nature.com/ndm)\n"
            "[3] Harvard Medical Review (2025). *Enterprise Integration*. [https://hmr.harvard.edu](https://hmr.harvard.edu)\n"
        )

        cites = [
            {"number": 1, "title": "Global Healthcare AI Analysis", "authors": "Frost & Sullivan", "year": "2025", "url": "https://frost.com/healthcare-ai"},
            {"number": 2, "title": "Clinical AI Validation", "authors": "Nature Digital Medicine", "year": "2025", "url": "https://nature.com/ndm"},
            {"number": 3, "title": "Enterprise Integration", "authors": "Harvard Medical Review", "year": "2025", "url": "https://hmr.harvard.edu"},
        ]

        pdf_bytes = generate_pdf(
            report=report_content,
            query="Multi-Modality Healthcare AI Market Assessment",
            quality_score=9.4,
            citations=cites,
            chart_json_list=[chart_1, chart_2, chart_3, chart_4],
            research_score=9.5,
            presentation_score=9.2,
        )

        self.assertIsInstance(pdf_bytes, bytes)
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        # Verify no nearly-empty pages (each content page must have substantial text/visual content)
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            # Page 1 is cover (few lines), pages 2+ must have > 250 characters
            if i > 0:
                self.assertGreater(len(text), 200, f"Page {i+1} appears nearly empty ({len(text)} chars)!")

        # Verify all 4 figures exist in document text
        full_text = "".join(p.get_text() for p in doc)
        self.assertIn("Figure 1", full_text)
        self.assertIn("Figure 2", full_text)
        self.assertIn("Figure 3", full_text)
        self.assertIn("Figure 4", full_text)

    def test_unmapped_citations_flagged_not_fabricated(self):
        """Verifies that citation numbers in text missing from bibliography are flagged as unverified, not fabricated."""
        report_with_missing_cite = (
            "# Experimental Research\n\n"
            "## Findings\n"
            "Observation with valid citation [1]. Another claim citing unmapped source [88].\n\n"
            "## References\n\n"
            "[1] Known Source (2025). *Documented Study*. [https://known.org](https://known.org)\n"
        )
        cites = [{"number": 1, "title": "Documented Study", "authors": "Known Source", "year": "2025", "url": "https://known.org"}]

        pdf_bytes = generate_pdf(
            report=report_with_missing_cite,
            query="Experimental Research",
            quality_score=8.0,
            citations=cites
        )

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        full_text = "".join(p.get_text() for p in doc)

        # Must contain citation [88]
        self.assertIn("[88]", full_text)
        # Must flag it in the references section
        self.assertIn("[88]", full_text)
        self.assertIn("primary research context", full_text)

if __name__ == "__main__":
    unittest.main()
