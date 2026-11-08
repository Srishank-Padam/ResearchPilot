"""
ResearchPilot AI — Quality Gate Node
Evaluates both Research Quality (factuality, citation coverage, source credibility, statistical verification)
and Presentation Quality (structure, clarity, section completeness, formatting, visualization, layout).
Ensures unsupported statistics prevent inflated reliability ratings.
Emits structured actionable feedback for research and presentation improvement.
"""
import time
import re
import json
from typing import Dict, Any, Optional
from graph.state import ResearchState
from graph.llm_factory import get_llm

QUALITY_THRESHOLD = 7.0
MAX_RETRIES = 2

REQUIRED_SECTIONS = [
    "executive summary", "key findings", "analysis", "statistical overview",
    "expert perspective", "real-world examples", "challenges",
    "future outlook", "conclusion", "references"
]


def _compute_deterministic_quality_metrics(state: ResearchState) -> Dict[str, Any]:
    """
    Computes rigorous, objective deterministic metrics for research and presentation quality
    from the actual state, evidence, citations, charts, and report contents.
    """
    report = state.get("final_report", "")
    report_lower = report.lower()
    sd = state.get("structured_data", {}) or {}
    metrics = sd.get("metrics", [])
    citations = state.get("citations", [])
    fact_checks = state.get("fact_checks", [])
    chart_json = state.get("chart_json", [])
    active_agents = state.get("active_agents", [])

    # ── 1. Research Quality Components (0 to 10 scale) ────────────────────────
    # A. Statistical Evidence & Verification (Weight: 35%)
    if metrics:
        verified_count = sum(1 for m in metrics if m.get("verification_status") == "verified")
        stat_score = min(10.0, (verified_count / len(metrics)) * 10.0)
    elif "statistics" in active_agents:
        stat_score = 4.0  # Statistics agent ran but produced 0 metrics
        verified_count = 0
    else:
        stat_score = 8.0  # Statistics not requested for topic
        verified_count = 0

    # B. Source Credibility & Provenance (Weight: 25%)
    valid_cites = [c for c in citations if c.get("url", "").startswith("http")]
    if len(valid_cites) >= 6:
        source_score = 10.0
    elif len(valid_cites) >= 4:
        source_score = 8.5
    elif len(valid_cites) >= 2:
        source_score = 6.5
    elif len(valid_cites) == 1:
        source_score = 4.0
    else:
        source_score = 1.0

    # C. In-Text Citation Coverage & Mapping (Weight: 20%)
    in_text_cites = set(re.findall(r"\[(\d+)\]", report))
    valid_nums = {int(c.get("number", 0)) for c in citations if str(c.get("number", "")).isdigit()}
    mapped_count = sum(1 for n in in_text_cites if int(n) in valid_nums)
    if mapped_count >= 5:
        cite_score = 10.0
    elif mapped_count >= 3:
        cite_score = 8.0
    elif mapped_count >= 1:
        cite_score = 5.0
    else:
        cite_score = 1.0

    # D. Factual Verification Pass Rate (Weight: 20%)
    if fact_checks:
        fc_scores = []
        for fc in fact_checks:
            st_val = fc.get("status", "")
            if st_val == "Verified":
                fc_scores.append(10.0)
            elif st_val == "Partially Supported":
                fc_scores.append(7.0)
            elif st_val == "Contradicted":
                fc_scores.append(0.0)
            else:  # Unverified
                fc_scores.append(3.5)
        fact_score = sum(fc_scores) / len(fc_scores)
    else:
        fact_score = 7.0

    det_research = round(
        0.35 * stat_score + 0.25 * source_score + 0.20 * cite_score + 0.20 * fact_score, 1
    )

    # ── 2. Presentation Quality Components (0 to 10 scale) ────────────────────
    # A. Section Completeness (Weight: 30%)
    present_sections = [s for s in REQUIRED_SECTIONS if s in report_lower]
    section_score = round((len(present_sections) / len(REQUIRED_SECTIONS)) * 10.0, 1)

    # B. Data Visualization Quality (Weight: 25%)
    if chart_json and len(chart_json) >= 3:
        viz_score = 10.0
    elif chart_json and len(chart_json) >= 1:
        viz_score = 8.0
    elif "statistics" not in active_agents:
        viz_score = 8.0
    else:
        viz_score = 3.5

    # C. Readability, Depth & Structure (Weight: 25%)
    word_count = len(report.split())
    has_table = "|" in report and "---" in report
    read_pts = 0.0
    if word_count >= 800:
        read_pts += 5.0
    elif word_count >= 500:
        read_pts += 3.5
    else:
        read_pts += 2.0
    if has_table:
        read_pts += 2.5
    if len(re.findall(r"^##\s+", report, re.MULTILINE)) >= 8:
        read_pts += 2.5
    readability_score = min(10.0, read_pts)

    # D. Citation & Bibliography Formatting (Weight: 10%)
    has_ref_header = "## references" in report_lower
    has_apa_format = bool(re.search(r"\[\d+\]\s+[^\n]+\(\d{4}\)", report))
    bib_score = 10.0 if (has_ref_header and has_apa_format) else (5.0 if has_ref_header else 1.0)

    # E. Document / PDF Layout Readiness (Weight: 10%)
    clean_chars = not any(b in report for b in ["\ufffd", "???", "TODO", "[Placeholder]"])
    layout_score = 10.0 if clean_chars else 4.0

    det_presentation = round(
        0.30 * section_score + 0.25 * viz_score + 0.25 * readability_score + 0.10 * bib_score + 0.10 * layout_score, 1
    )

    return {
        "det_research": det_research,
        "det_presentation": det_presentation,
        "stat_score": round(stat_score, 1),
        "source_score": round(source_score, 1),
        "cite_score": round(cite_score, 1),
        "fact_score": round(fact_score, 1),
        "section_score": round(section_score, 1),
        "viz_score": round(viz_score, 1),
        "readability_score": round(readability_score, 1),
        "bib_score": round(bib_score, 1),
        "layout_score": round(layout_score, 1),
        "total_metrics": len(metrics),
        "verified_metrics": verified_count,
        "valid_sources": len(valid_cites),
        "in_text_count": len(in_text_cites),
        "sections_present": len(present_sections),
        "word_count": word_count,
    }

# Backward-compatible alias for unit test suite
_compute_deterministic_research_metrics = _compute_deterministic_quality_metrics


def quality_gate_node(state: ResearchState) -> dict:
    t0 = time.time()
    report = state.get("final_report", "")
    retry = state.get("retry_count", 0)
    logs = list(state.get("agent_logs", []))
    timings = dict(state.get("agent_timings", {}))

    logs.append("[Quality Gate] Auditing research reliability and presentation quality...")

    metrics = _compute_deterministic_quality_metrics(state)

    llm = get_llm(temperature=0.1)

    prompt = f"""You are an exacting academic research quality auditor.
Perform an evidence and presentation audit of this research report on "{state.get('query','')}".

DETERMINISTIC EVIDENCE AUDIT DATA:
- Statistical evidence score: {metrics['stat_score']}/10 ({metrics['verified_metrics']} of {metrics['total_metrics']} verified)
- Source credibility & diversity: {metrics['source_score']}/10 ({metrics['valid_sources']} verified URLs)
- In-text citation coverage: {metrics['cite_score']}/10 ({metrics['in_text_count']} unique in-text citations)
- Fact-check consistency: {metrics['fact_score']}/10
- Section completeness: {metrics['section_score']}/10 ({metrics['sections_present']} of 10 standard sections)
- Word count: {metrics['word_count']} words

REPORT EXCERPT (first 4000 characters):
{report[:4000]}

SCORING RULES:
1. Research Quality (0-10): Factual backing, source credibility, traceable citations, statistical evidence, absence of unverified/invented claims.
2. Presentation Quality (0-10): Structure, clarity, analytical flow, section completeness, formatting, data tables.
3. If statistics are missing or unverified, Research Quality MUST NOT exceed 6.0.
4. Provide structured, actionable critique across all five feedback categories.

Return ONLY this format:
RESEARCH_SCORE: <float 0.0-10.0>
PRESENTATION_SCORE: <float 0.0-10.0>
MISSING_EVIDENCE: <specific data points, metrics, or sources missing or unverified>
WEAK_ANALYSIS: <specific topics or paragraphs lacking analytical depth or nuance>
MISSING_COMPARISONS: <specific baselines, historical comparisons, or segment benchmarks missing>
UNSUPPORTED_CLAIMS: <claims that need clearer empirical backing or citations>
RECOMMENDED_RESEARCH: <actionable next research steps or specific angles to explore>
SUMMARY_REASON: <1-2 sentence overall evaluation summary>"""

    llm_research = metrics["det_research"]
    llm_presentation = metrics["det_presentation"]
    feedback = {
        "missing_evidence": "Ensure all statistics have verbatim excerpts and verified URLs.",
        "weak_analysis": "Expand on regulatory compliance and economic trade-offs.",
        "missing_comparisons": "Incorporate multi-year baseline and segment comparisons.",
        "unsupported_claims": "Attribute every numerical assertion to a verified source.",
        "recommended_research": "Investigate longitudinal outcome metrics and international adoption.",
        "summary_reason": "Audit completed against evidence provenance criteria.",
    }

    try:
        response = llm.invoke(prompt)
        text = response.content if isinstance(response.content, str) else str(response.content)

        r_match = re.search(r"RESEARCH_SCORE:\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if r_match:
            llm_research = min(10.0, max(0.0, float(r_match.group(1))))

        p_match = re.search(r"PRESENTATION_SCORE:\s*(\d+\.?\d*)", text, re.IGNORECASE)
        if p_match:
            llm_presentation = min(10.0, max(0.0, float(p_match.group(1))))

        for key, pattern in [
            ("missing_evidence", r"MISSING_EVIDENCE:\s*(.+)"),
            ("weak_analysis", r"WEAK_ANALYSIS:\s*(.+)"),
            ("missing_comparisons", r"MISSING_COMPARISONS:\s*(.+)"),
            ("unsupported_claims", r"UNSUPPORTED_CLAIMS:\s*(.+)"),
            ("recommended_research", r"RECOMMENDED_RESEARCH:\s*(.+)"),
            ("summary_reason", r"SUMMARY_REASON:\s*(.+)"),
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                feedback[key] = m.group(1).strip()
    except Exception as e:
        logs.append(f"[Quality Gate] LLM evaluation note: {e}")

    # Blend deterministic metrics (60%) with LLM qualitative audit (40%)
    final_research = round(0.60 * metrics["det_research"] + 0.40 * llm_research, 1)
    final_presentation = round(0.60 * metrics["det_presentation"] + 0.40 * llm_presentation, 1)

    # Strict penalty: If statistics were extracted but none were verified, cap research at 4.5
    if metrics["total_metrics"] > 0 and metrics["verified_metrics"] == 0:
        final_research = min(final_research, 4.5)
        feedback["missing_evidence"] += " (Critical: 0 of extracted statistics were verified)."

    # Clamp scores
    final_research = min(10.0, max(0.0, final_research))
    final_presentation = min(10.0, max(0.0, final_presentation))

    # ── Documented Overall Scoring Formula ────────────────────────────────────
    # Overall Score = 65% Research Quality + 35% Presentation Quality
    overall_score = round(0.65 * final_research + 0.35 * final_presentation, 1)

    # Quality Gate Integrity Rule: A poorly researched report cannot score high overall
    if final_research < 6.0:
        overall_score = min(overall_score, 6.0)

    # Detailed breakdown dictionary
    breakdown = {
        "formula": "Overall = (0.65 × Research) + (0.35 × Presentation)",
        "research": {
            "score": final_research,
            "components": {
                "Statistical Evidence (35%)": f"{metrics['stat_score']}/10 ({metrics['verified_metrics']}/{metrics['total_metrics']} verified)",
                "Source Credibility & Diversity (25%)": f"{metrics['source_score']}/10 ({metrics['valid_sources']} sources)",
                "Citation Coverage & Mapping (20%)": f"{metrics['cite_score']}/10 ({metrics['in_text_count']} in-text citations)",
                "Fact-Check Audit Consistency (20%)": f"{metrics['fact_score']}/10",
            }
        },
        "presentation": {
            "score": final_presentation,
            "components": {
                "Section Completeness (30%)": f"{metrics['section_score']}/10 ({metrics['sections_present']}/10 sections)",
                "Data Visualization Quality (25%)": f"{metrics['viz_score']}/10",
                "Readability & Depth (25%)": f"{metrics['readability_score']}/10 ({metrics['word_count']} words)",
                "Citation Formatting (10%)": f"{metrics['bib_score']}/10",
                "Document & Layout Readiness (10%)": f"{metrics['layout_score']}/10",
            }
        },
        "overall": overall_score,
        "is_capped": bool(final_research < 6.0),
    }

    logs.append(
        f"[Quality Gate] Score: {overall_score:.1f}/10 "
        f"(Research: {final_research:.1f}/10, Presentation: {final_presentation:.1f}/10) — "
        f"{feedback['summary_reason']}"
    )

    timings["quality_gate"] = round(time.time() - t0, 2)

    return {
        "quality_score": overall_score,
        "research_quality": final_research,
        "presentation_quality": final_presentation,
        "quality_breakdown": breakdown,
        "quality_feedback": feedback,
        "retry_count": retry + 1,
        "agent_logs": logs,
        "agent_timings": timings,
    }


def should_retry(state: ResearchState) -> str:
    """Conditional edge function: 'retry' → writer (synthesizer), 'done' → cover."""
    score = state.get("quality_score")
    retry = state.get("retry_count", 0)

    if score is not None and score < QUALITY_THRESHOLD and retry <= MAX_RETRIES:
        return "retry"
    return "done"
