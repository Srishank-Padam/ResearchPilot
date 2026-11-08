"""
ResearchPilot AI — Healthcare Market Report Generator & Verification Runner
Topic: 'Impact of AI on healthcare market growth: adoption rates, investment trends and future outlook'
Executes the full multi-agent pipeline and compiles publication-quality PDF.
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
from tools.pdf_generator import generate_pdf

TOPIC = "Impact of AI on healthcare market growth: adoption rates, investment trends and future outlook"

def run():
    print("=" * 65)
    print("  ResearchPilot AI — Live Pipeline Execution")
    print(f"  Topic: {TOPIC}")
    print("=" * 65)

    initial_state = {
        "query":            TOPIC,
        "todos":            [],
        "research_plan":    "",
        "active_agents":    [],
        "topic_domain":     "healthcare",
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
        print(f"\n[NODE COMPLETED: {node_name.upper()}]")
        for log in node_data.get("agent_logs", [])[-2:]:
            print(f"   {log}")
        for k, v in node_data.items():
            if v is not None:
                final_state[k] = v

    print("\n" + "=" * 65)
    print("  Pipeline Completed!")
    q_score = final_state.get("quality_score", 0.0)
    r_score = final_state.get("research_quality")
    p_score = final_state.get("presentation_quality")
    print(f"  Overall Score   : {q_score:.1f}/10")
    print(f"  Research Score  : {r_score:.1f}/10" if r_score is not None else "  Research: N/A")
    print(f"  Presentation    : {p_score:.1f}/10" if p_score is not None else "  Presentation: N/A")
    print(f"  Active Agents   : {final_state.get('active_agents', [])}")
    print(f"  Charts Generated: {len(final_state.get('chart_json', []))}")
    print(f"  Citations       : {len(final_state.get('citations', []))}")
    print("=" * 65)

    report = final_state.get("final_report", "")
    with open("healthcare_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("\n✅ Saved report Markdown to healthcare_report.md")

    vfs = final_state.get("virtual_files", {})
    csv_content = vfs.get("statistics_data.csv", "")
    if csv_content:
        with open("healthcare_stats.csv", "w", encoding="utf-8") as f:
            f.write(csv_content)
        print("✅ Saved statistical dataset to healthcare_stats.csv")

    charts = final_state.get("chart_json", [])
    cites = final_state.get("citations", [])
    active = final_state.get("active_agents", [])

    print(f"Building Academic PDF with {len(charts)} charts and {len(cites)} citations...")
    pdf_bytes = generate_pdf(
        report=report,
        query=TOPIC,
        quality_score=q_score,
        citations=cites,
        chart_json_list=charts,
        thumbnail_svg=final_state.get("thumbnail_svg"),
        active_agents=active,
        research_score=r_score,
        presentation_score=p_score,
    )

    pdf_path = os.path.abspath("healthcare_report.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"✅ Generated Academic PDF: {pdf_path} (Size: {len(pdf_bytes)} bytes)")

    return pdf_path

if __name__ == "__main__":
    run()

