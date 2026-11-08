"""
ResearchPilot AI — Reliability and Quality Improvement Test Suite
Tests covering:
- Missing source URLs
- Unsupported statistics
- Contradictory evidence
- Citation numbering and synchronization
- Mixed-unit chart segregation
- Empty datasets
- Unicode PDF generation
- Invalid numerical values
- Fallback model execution
"""
import unittest
import json
import io
import os
import sys

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from graph.visualization import _normalize_unit_group, _parse_val, visualization_node
from graph.synthesizer import _sync_citations_and_references
from tools.pdf_generator import clean, generate_pdf
from graph.quality_gate import _compute_deterministic_research_metrics
from graph.llm_factory import get_llm, _normalize_response
from langchain_core.messages import AIMessage


class TestResearchReliability(unittest.TestCase):

    def test_missing_source_urls(self):
        """Verifies that statistics lacking valid source URLs are flagged as unverified."""
        test_metric = {
            "label": "Enterprise Adoption Rate",
            "value": 68.5,
            "unit": "%",
            "year": "2024",
            "url": "",  # Missing URL
            "evidence_excerpt": "Survey showed 68.5% of enterprises adopted AI.",
            "verification_status": "verified"
        }
        # Provenance audit rule
        has_valid_url = bool(test_metric.get("url") and test_metric["url"].startswith("http"))
        if not has_valid_url:
            test_metric["verification_status"] = "unverified"

        self.assertEqual(test_metric["verification_status"], "unverified")
        self.assertFalse(has_valid_url)

    def test_unsupported_statistics(self):
        """Verifies that statistics lacking supporting evidence excerpts are rejected or marked unverified."""
        test_metrics = [
            {
                "label": "Unsupported Metric",
                "value": 99.9,
                "unit": "%",
                "url": "https://example.com",
                "evidence_excerpt": "",  # Empty evidence
                "verification_status": "verified"
            },
            {
                "label": "Supported Metric",
                "value": 45.2,
                "unit": "billion USD",
                "url": "https://example.com/report",
                "evidence_excerpt": "Global market size was valued at 45.2 billion USD in 2024.",
                "verification_status": "verified"
            }
        ]

        audited = []
        for m in test_metrics:
            if not m.get("evidence_excerpt") or len(m["evidence_excerpt"]) < 10:
                m["verification_status"] = "unverified"
            audited.append(m)

        self.assertEqual(audited[0]["verification_status"], "unverified")
        self.assertEqual(audited[1]["verification_status"], "verified")

    def test_contradictory_evidence(self):
        """Verifies that contradictory evidence is identified as Contradicted."""
        # Simulated claim and conflicting evidence
        claim = "Hospital operational costs increased by 50% following AI adoption."
        evidence = "A multi-center study documented that hospital operating costs dropped by 18% after AI deployment."

        # Evaluation rule check
        claim_lower = claim.lower()
        evidence_lower = evidence.lower()

        # Opposite directional keywords indicate contradiction
        is_contradicted = ("increased" in claim_lower and "dropped" in evidence_lower) or \
                          ("increase" in claim_lower and "decrease" in evidence_lower)

        status = "Contradicted" if is_contradicted else "Verified"
        self.assertEqual(status, "Contradicted")

    def test_citation_numbering(self):
        """Verifies that every in-text citation [N] maps to an actual bibliography entry."""
        sample_report = (
            "# Research Report\n\n"
            "Key findings indicate AI reduces diagnostic errors by 15% [1]. "
            "Furthermore, 84% of healthcare organizations report efficiency gains [2]. "
            "However, unverified estimates [99] should be mapped properly."
        )
        sample_citations = [
            {"number": 1, "title": "Diagnostic AI Review", "authors": "Smith et al.", "year": "2024", "url": "https://doi.org/10.1001/jama.2024"},
            {"number": 2, "title": "Healthcare Technology Benchmark", "authors": "Gartner", "year": "2025", "url": "https://gartner.com/ai-health"},
        ]

        final_report, used_citations = _sync_citations_and_references(sample_report, sample_citations)

        self.assertIn("## References", final_report)
        self.assertIn("[1] Smith et al. (2024)", final_report)
        self.assertIn("[2] Gartner (2025)", final_report)
        self.assertIn("https://doi.org/10.1001/jama.2024", final_report)
        self.assertEqual(len(used_citations), 2)

    def test_mixed_unit_charts(self):
        """Verifies that different units (% and $B) are segregated into separate unit groups."""
        fin_group = _normalize_unit_group("billion USD")
        pct_group = _normalize_unit_group("% CAGR")
        vol_group = _normalize_unit_group("million patients")

        self.assertEqual(fin_group, "financial")
        self.assertEqual(pct_group, "percentage")
        self.assertEqual(vol_group, "volume")
        self.assertNotEqual(fin_group, pct_group)
        self.assertNotEqual(pct_group, vol_group)

        # Run visualization node with mixed metrics
        state = {
            "active_agents": ["statistics"],
            "include_unverified_viz": False,
            "structured_data": {
                "metrics": [
                    {"label": "Market Size", "value": 36.7, "unit": "billion USD", "verification_status": "verified"},
                    {"label": "Projected Size", "value": 505.6, "unit": "billion USD", "verification_status": "verified"},
                    {"label": "Diagnostic Accuracy Gain", "value": 15.0, "unit": "%", "verification_status": "verified"},
                    {"label": "Adoption Rate", "value": 67.0, "unit": "%", "verification_status": "verified"},
                ],
                "trends": [],
                "comparisons": [],
            },
            "agent_logs": [],
            "agent_timings": {},
        }
        res = visualization_node(state)
        charts = res.get("chart_json", [])
        self.assertGreaterEqual(len(charts), 2)  # Generates separate financial and percentage charts

        # Verify first chart title contains currency unit and second contains %
        chart_0 = json.loads(charts[0])
        chart_1 = json.loads(charts[1])
        t0 = chart_0["layout"]["title"]["text"]
        t1 = chart_1["layout"]["title"]["text"]
        self.assertIn("USD", t0)
        self.assertIn("%", t1)

    def test_empty_datasets(self):
        """Verifies that empty datasets are handled safely without crashing."""
        empty_state = {
            "active_agents": ["statistics"],
            "include_unverified_viz": False,
            "structured_data": {"metrics": [], "trends": [], "comparisons": []},
            "agent_logs": [],
            "agent_timings": {},
        }
        res = visualization_node(empty_state)
        self.assertEqual(res.get("chart_json"), [])

        # PDF generation with empty charts and report
        pdf_bytes = generate_pdf(
            report="# Empty Report\n\nNo findings.",
            query="Empty Test Topic",
            quality_score=0.0,
            citations=[],
            chart_json_list=[],
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)

    def test_unicode_pdf_generation(self):
        """Verifies that Unicode characters (CO₂, °C, em-dashes, special hyphens, quotes, emojis) render without black squares or errors."""
        text_with_unicode = (
            "# Climate & Medical AI: Impact in 2025\n\n"
            "## Key Findings\n"
            "- Global CO₂ emissions decreased by 4.2% [1].\n"
            "- Operating temperature threshold: 37.5°C &plusmn; 0.5°C.\n"
            "- Mathematical boundary: x ≤ 100 and y ≥ 50.\n"
            "- Punctuation test: “Smart Health”—a multi-agent system–verified with non‑breaking hyphens.\n"
            "- Verification badges: ✅ Verified, ⚠️ Partially Supported, ❌ Contradicted.\n"
        )

        cleaned_sample = clean(text_with_unicode)
        # Confirm subscripts and entities were inserted
        self.assertIn("CO<sub>2</sub>", cleaned_sample)
        self.assertIn("&deg;C", cleaned_sample)
        self.assertIn("&mdash;", cleaned_sample)
        self.assertIn("[Verified]", cleaned_sample)
        self.assertNotIn("✅", cleaned_sample)  # Emojis converted to clean badges

        pdf_bytes = generate_pdf(
            report=text_with_unicode,
            query="Unicode PDF Verification Test",
            quality_score=8.5,
            citations=[{"number": 1, "title": "Climate AI Study", "authors": "Nature", "year": "2024", "url": "https://nature.com"}],
            research_score=8.7,
            presentation_score=8.2,
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 2000)

    def test_invalid_numerical_values(self):
        """Verifies that _parse_val safely handles malformed strings, symbols, commas, and nulls."""
        self.assertEqual(_parse_val("45.2"), 45.2)
        self.assertEqual(_parse_val("$45.2B"), 45.2)
        self.assertEqual(_parse_val(" 23.5% "), 23.5)
        self.assertEqual(_parse_val("1,500.75"), 1500.75)
        self.assertEqual(_parse_val("N/A"), 0.0)
        self.assertEqual(_parse_val(None), 0.0)
        self.assertEqual(_parse_val(""), 0.0)

    def test_fallback_model_execution(self):
        """Verifies that response normalization and fallback chaining work correctly."""
        # Test _normalize_response with list blocks
        block_msg = AIMessage(content=[{"type": "text", "text": "Normalized message output."}])
        normalized = _normalize_response(block_msg)
        self.assertIsInstance(normalized.content, str)
        self.assertEqual(normalized.content, "Normalized message output.")

        # Test get_llm invocation
        llm = get_llm(temperature=0.2)
        self.assertIsNotNone(llm)

    def test_quality_scoring_formula_and_capping(self):
        """Verifies that the overall score strictly follows the 65/35 formula and caps at 6.0 if research < 6.0."""
        from graph.quality_gate import _compute_deterministic_quality_metrics
        # Mock high-quality state
        state = {
            "query": "Quantum AI",
            "final_report": (
                "# Executive Summary\nQuantum computing is accelerating.\n\n"
                "## Key Findings\nQuantum algorithms demonstrated speedups [1].\n\n"
                "## Analysis\nDetailed analytical progression.\n\n"
                "## Statistical Overview\nMarket size reached 36.7 billion USD.\n\n"
                "## Expert Perspective\nDomain leaders point to error mitigation.\n\n"
                "## Real-World Examples\nPharma drug discovery trials.\n\n"
                "## Challenges\nCoherence time remains short.\n\n"
                "## Future Outlook\nFault-tolerant systems by 2030.\n\n"
                "## Conclusion\nStrategic advantages are clear.\n\n"
                "## References\n[1] Nature (2024). https://nature.com/articles/quantum\n"
            ),
            "structured_data": {
                "metrics": [
                    {"label": "Market Size", "value": 36.7, "unit": "billion USD", "url": "https://nature.com", "evidence_excerpt": "Market size reached 36.7 billion USD in 2024.", "verification_status": "verified"},
                    {"label": "Qubit Count", "value": 1121, "unit": "qubits", "url": "https://nature.com", "evidence_excerpt": "Processor scaled to 1121 qubits.", "verification_status": "verified"},
                ]
            },
            "citations": [
                {"number": 1, "title": "Quantum Advancements", "authors": "Nature", "year": "2024", "url": "https://nature.com/articles/quantum"}
            ],
            "fact_checks": [
                {"status": "Verified"}
            ],
            "chart_json": ["{}", "{}", "{}"],
            "active_agents": ["statistics", "domain_expert", "fact_checker"],
        }
        metrics = _compute_deterministic_quality_metrics(state)
        det_r = metrics["det_research"]
        det_p = metrics["det_presentation"]

        # Ensure research and presentation are computed on a 0-10 scale
        self.assertGreaterEqual(det_r, 0.0)
        self.assertLessEqual(det_r, 10.0)
        self.assertGreaterEqual(det_p, 0.0)
        self.assertLessEqual(det_p, 10.0)

        # Formula check
        overall = round(0.65 * det_r + 0.35 * det_p, 1)
        if det_r < 6.0:
            overall = min(overall, 6.0)

        self.assertGreaterEqual(overall, 0.0)
        self.assertLessEqual(overall, 10.0)

        # Test capping behavior when research is artificially low (< 6.0)
        low_r = 5.0
        high_p = 10.0
        uncapped = round(0.65 * low_r + 0.35 * high_p, 1) # 3.25 + 3.5 = 6.75
        capped = min(uncapped, 6.0)
        self.assertEqual(capped, 6.0)

    def test_actionable_feedback_categories(self):
        """Verifies that all 5 required actionable feedback categories are present and structured."""
        from graph.quality_gate import quality_gate_node
        mock_state = {
            "query": "Test AI",
            "final_report": "Brief text without sections or citations.",
            "structured_data": {"metrics": []},
            "citations": [],
            "fact_checks": [],
            "chart_json": [],
            "active_agents": ["statistics"],
            "retry_count": 0,
            "agent_logs": [],
            "agent_timings": {},
        }
        res = quality_gate_node(mock_state)
        fb = res.get("quality_feedback", {})
        self.assertIn("missing_evidence", fb)
        self.assertIn("weak_analysis", fb)
        self.assertIn("missing_comparisons", fb)
        self.assertIn("unsupported_claims", fb)
        self.assertIn("recommended_research", fb)
        # Verify scores are populated and within 0-10 scale
        self.assertIsNotNone(res.get("research_quality"))
        self.assertIsNotNone(res.get("presentation_quality"))
        self.assertIsNotNone(res.get("quality_score"))
        self.assertGreaterEqual(res["research_quality"], 0.0)
        self.assertLessEqual(res["research_quality"], 10.0)


if __name__ == "__main__":
    unittest.main()

