"""
ResearchPilot AI — Terminal Test Runner
Run: python main.py
Tests the full pipeline without Streamlit.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from graph.graph_builder import graph

TEST_QUERY = "Autonomous electric vehicle adoption and battery supply chain trends in 2025"

def main():
    print("=" * 60)
    print("  ResearchPilot AI")
    print(f"  Query: {TEST_QUERY}")
    print("=" * 60)

    initial_state = {
        "query":            TEST_QUERY,
        "todos":            [],
        "research_plan":    "",
        "active_agents":    [],
        "topic_domain":     "general",
        "virtual_files":    {},
        "structured_data":  {},
        "citations":        [],
        "chart_json":       [],
        "thumbnail_svg":    None,
        "final_report":     "",
        "quality_score":        None,
        "research_quality":     None,
        "presentation_quality": None,
        "quality_breakdown":    None,
        "quality_feedback":     None,
        "retry_count":          0,
        "agent_logs":           [],
        "agent_timings":        {},
        "generate_thumbnail":   True,
    }

    final_state = {}
    for update in graph.stream(initial_state):
        node_name = list(update.keys())[0]
        node_data  = update[node_name]
        print(f"\n[NODE: {node_name.upper()}]")

        logs = node_data.get("agent_logs", [])
        for log in logs[-3:]:   # show last 3 logs per node
            print(f"  {log}")

        for k, v in node_data.items():
            if v is not None:
                final_state[k] = v

    def _fmt(val):
        return f"{val:.1f}/10" if val is not None else "Unavailable (—)"

    print("\n" + "=" * 60)
    print(f"  Reliability Score    : {_fmt(final_state.get('quality_score'))}")
    print(f"  Research Quality     : {_fmt(final_state.get('research_quality'))}")
    print(f"  Presentation Quality : {_fmt(final_state.get('presentation_quality'))}")
    print(f"  Scoring Formula      : Overall = (0.65 × Research) + (0.35 × Presentation)")
    print(f"  Active Agents        : {final_state.get('active_agents', [])}")
    print(f"  Domain               : {final_state.get('topic_domain', 'general')}")
    print(f"  Charts               : {len(final_state.get('chart_json', []))}")
    print(f"  Citations            : {len(final_state.get('citations', []))}")

    breakdown = final_state.get("quality_breakdown")
    if breakdown:
        print("\n  [AUDIT BREAKDOWN]")
        print("  Research Components:")
        for k, v in breakdown.get("research", {}).get("components", {}).items():
            print(f"    - {k}: {v}")
        print("  Presentation Components:")
        for k, v in breakdown.get("presentation", {}).get("components", {}).items():
            print(f"    - {k}: {v}")

    fb = final_state.get("quality_feedback")
    if fb:
        print("\n  [ACTIONABLE QUALITY AUDIT FEEDBACK]")
        print(f"  🔍 Missing Evidence      : {fb.get('missing_evidence')}")
        print(f"  🧠 Weak Analysis          : {fb.get('weak_analysis')}")
        print(f"  ⚖️  Missing Comparisons   : {fb.get('missing_comparisons')}")
        print(f"  ⚠️  Unsupported Claims    : {fb.get('unsupported_claims')}")
        print(f"  🚀 Recommended Research   : {fb.get('recommended_research')}")
        print(f"  📝 Auditor Summary        : {fb.get('summary_reason')}")
    print("=" * 60)

    report = final_state.get("final_report", "")
    if report:
        with open("output_report_v2.md", "w", encoding="utf-8") as f:
            f.write(report)
        print("\n✅ Report saved to output_report_v2.md")

    vfs = final_state.get("virtual_files", {})
    csv_content = vfs.get("statistics_data.csv", "")
    if csv_content:
        with open("statistics_data.csv", "w", encoding="utf-8") as f:
            f.write(csv_content)
        print("✅ Statistics data saved to statistics_data.csv")

    try:
        from tools.pdf_generator import generate_pdf
        pdf_bytes = generate_pdf(
            report=report,
            query=TEST_QUERY,
            quality_score=final_state.get("quality_score", 0),
            citations=final_state.get("citations", []),
            chart_json_list=final_state.get("chart_json", []),
            thumbnail_svg=final_state.get("thumbnail_svg"),
            active_agents=final_state.get("active_agents", []),
            research_score=final_state.get("research_quality"),
            presentation_score=final_state.get("presentation_quality"),
        )
        if pdf_bytes:
            with open("output_report_v2.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("✅ Academic PDF saved to output_report_v2.pdf")
    except Exception as e:
        print(f"⚠️ PDF generation note: {e}")


    timings = final_state.get("agent_timings", {})
    if timings:
        print("\n⏱  Timings:")
        for k, v in timings.items():
            print(f"   {k:20s} {v:.2f}s")
        print(f"   {'TOTAL':20s} {sum(timings.values()):.2f}s")

if __name__ == "__main__":
    main()
