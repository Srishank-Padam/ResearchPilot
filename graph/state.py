"""
ResearchPilot AI — Shared State Schema
All nodes read from and write to this TypedDict.
"""
from typing import TypedDict, List, Dict, Optional, Any


class ResearchState(TypedDict):
    # Core
    query: str
    todos: List[Dict[str, str]]
    research_plan: str

    # Router
    active_agents: List[str]        # ["research","statistics","domain_expert","fact_checker","citation"]
    topic_domain: str               # "healthcare"|"finance"|"technology"|"science"|"history"|"general"

    # Virtual File System
    virtual_files: Dict[str, str]

    # Agent outputs
    structured_data: Dict[str, Any] # For Statistics Agent → Plotly charts
    citations: List[Dict[str, str]]

    # Visualisation
    chart_json: List[str]           # JSON-serialised Plotly figures
    thumbnail_svg: Optional[str]

    # Synthesis & quality
    final_report: str
    quality_score: Optional[float]
    research_quality: Optional[float]
    presentation_quality: Optional[float]
    quality_breakdown: Optional[Dict[str, Any]]
    quality_feedback: Optional[Dict[str, Any]]
    retry_count: int
    agent_logs: List[str]
    fact_checks: Optional[List[Dict[str, Any]]]

    # Timing
    agent_timings: Dict[str, float]

    # UI toggles & visualization controls
    generate_thumbnail: bool
    include_unverified_viz: Optional[bool]
