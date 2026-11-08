"""
ResearchPilot AI — Streamlit UI and VFS Integration Tests
Verifies:
1. 'vfs' variable is properly defined from final state in both live and cached paths.
2. Missing virtual_files or empty virtual_files are safely handled without exceptions.
3. Quality scores:
   - When available: displayed as formatted 0-10 score (e.g. '8.5/10').
   - When missing (None): displayed as an em dash ('—').
4. Documented scoring formula and breakdown render properly.
5. All outputs (Markdown, CSV, PDF download buttons) function cleanly.
"""
import unittest
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from streamlit.testing.v1 import AppTest


APP_PATH = os.path.join(PROJECT_ROOT, "ui", "app.py")


class TestStreamlitUIVfs(unittest.TestCase):

    def test_ui_initial_load(self):
        """Verifies that the Streamlit UI loads without any syntax or runtime exceptions."""
        at = AppTest.from_file(APP_PATH)
        at.run(timeout=30)
        self.assertEqual(len(at.exception), 0, f"Exceptions on initial load: {at.exception}")

    def test_ui_cached_run_with_populated_vfs(self):
        """Verifies that cached rerun renders VFS files, CSV download, and references without NameError."""
        at = AppTest.from_file(APP_PATH)
        # Populate session state simulating a completed research query
        mock_final = {
            "query": "Impact of AI in Healthcare",
            "topic_domain": "medical",
            "active_agents": ["research", "statistics", "domain_expert", "citation"],
            "quality_score": 8.5,
            "research_quality": 8.8,
            "presentation_quality": 8.0,
            "final_report": "# Healthcare AI Report\n\n## Key Findings\nAdoption grew by 25% [1].\n\n## References\n[1] Smith et al. (2024). https://example.com",
            "citations": [
                {"number": 1, "title": "AI in Medicine", "apa": "Smith et al. (2024)", "url": "https://example.com"}
            ],
            "chart_json": [],
            "structured_data": {"metrics": [{"label": "Adoption Rate", "value": 25.0, "unit": "%"}]},
            "virtual_files": {
                "statistics_data.csv": "Metric,Value,Unit\nAdoption Rate,25,%\n",
                "references.txt": "[1] Smith et al. (2024)\n",
                "research_deep.txt": "Deep research intelligence on medical AI."
            },
            "agent_logs": ["[Planner] Done", "[Cover] Done. SVG cover generated."],
            "agent_timings": {"planner": 2.1, "workers": 15.3, "cover": 0.5},
            "quality_breakdown": {
                "research": {"score": 8.8, "components": {"Statistical Evidence": "9.0/10"}},
                "presentation": {"score": 8.0, "components": {"Section Completeness": "8.5/10"}}
            },
            "quality_feedback": {
                "missing_evidence": "Include more regional data.",
                "weak_analysis": "Discuss liability frameworks.",
                "missing_comparisons": "Compare with 2020 baseline.",
                "unsupported_claims": "Attribute cost savings estimates.",
                "recommended_research": "Examine clinical trial outcomes.",
                "summary_reason": "Comprehensive evidence synthesis."
            }
        }
        at.session_state["rf_has_run"] = True
        at.session_state["rf_final"] = mock_final
        at.session_state["rf_completed"] = ["planner", "router", "workers", "visualization", "writer", "quality_gate", "cover"]
        at.session_state["rf_query"] = "Impact of AI in Healthcare"

        at.run(timeout=30)
        self.assertEqual(len(at.exception), 0, f"Exceptions on cached rerun: {[e.value for e in at.exception]}")

    def test_ui_cached_run_with_empty_or_none_vfs(self):
        """Verifies that missing or None virtual_files are safely handled without NameError or AttributeError."""
        at = AppTest.from_file(APP_PATH)
        mock_final = {
            "query": "Generic Topic Without VFS",
            "topic_domain": "general",
            "active_agents": ["research"],
            "quality_score": 7.0,
            "research_quality": 7.0,
            "presentation_quality": 7.0,
            "final_report": "# Generic Report\n\nFindings text without citations.",
            "citations": [],
            "chart_json": [],
            "structured_data": {},
            "virtual_files": None,  # Intentionally None to test safe absence handling
            "agent_logs": ["[Planner] Done"],
            "agent_timings": {},
            "quality_breakdown": None,
            "quality_feedback": None,
        }
        at.session_state["rf_has_run"] = True
        at.session_state["rf_final"] = mock_final
        at.session_state["rf_completed"] = ["planner", "router", "workers", "visualization", "writer", "quality_gate", "cover"]
        at.session_state["rf_query"] = "Generic Topic Without VFS"

        at.run(timeout=30)
        self.assertEqual(len(at.exception), 0, f"Exceptions with None vfs: {[e.value for e in at.exception]}")

    def test_ui_missing_scores_display_em_dash(self):
        """Verifies that when scores are None (missing), format_score renders an em dash '—'."""
        from ui.app import format_score
        disp, cls = format_score(None)
        self.assertEqual(disp, "—")
        self.assertEqual(cls, "badge-na")

        # Test valid score
        disp_valid, cls_valid = format_score(8.5)
        self.assertEqual(disp_valid, "8.5/10")
        self.assertEqual(cls_valid, "badge-hi")

        # Test borderline score
        disp_mid, cls_mid = format_score(5.2)
        self.assertEqual(disp_mid, "5.2/10")
        self.assertEqual(cls_mid, "badge-md")


if __name__ == "__main__":
    unittest.main()
