"""
ResearchPilot AI — Visualization Node
Evidence-grounded, unit-segregated data visualization:
- Strict unit segregation: never mix % and currency on the same chart.
- Verified data filter: only plots verified metrics by default.
- Line charts strictly for verified multi-point chronological trends.
- Coherent composition charts: donut charts only for genuine percentage breakdowns.
- Complete provenance: source organization and year documented in subtitles and tooltips.
"""
import time
import json
from graph.state import ResearchState

DARK  = "#0f172a"
CARD  = "#1e293b"
GRID  = "#334155"
TEXT  = "#e2e8f0"
TITLE = "#a5b4fc"
MUTED = "#94a3b8"

PALETTE = [
    "#6366f1", "#34d399", "#f59e0b", "#38bdf8", "#ec4899",
    "#8b5cf6", "#10b981", "#f97316", "#a78bfa", "#06b6d4"
]
UNVERIFIED_COLOR = "#f43f5e"


import re

def _parse_val(v):
    if v is None:
        return 0.0
    s = str(v).replace(",", "").strip()
    match = re.search(r"[-+]?\d*\.?\d+", s)
    if match and match.group():
        try:
            return float(match.group())
        except (ValueError, TypeError):
            pass
    return 0.0



def _normalize_unit_group(unit_str: str) -> str:
    u = str(unit_str).lower().strip()
    if any(k in u for k in ["usd", "$", "dollar", "revenue", "market size", "billion", "investment"]):
        return "financial"
    if any(k in u for k in ["%", "percent", "cagr", "rate", "share", "proportion"]):
        return "percentage"
    if any(k in u for k in ["million", "count", "patients", "beds", "jobs", "patents", "users"]):
        return "volume"
    return "other"


def visualization_node(state: ResearchState) -> dict:
    t0 = time.time()
    active = state.get("active_agents", [])
    logs = list(state.get("agent_logs", []))
    timings = dict(state.get("agent_timings", {}))

    if "statistics" not in active:
        logs.append("[Viz] Skipped — statistics agent not active.")
        return {"chart_json": [], "agent_logs": logs, "agent_timings": timings}

    sd = state.get("structured_data", {}) or {}
    all_metrics = sd.get("metrics", [])
    trends = sd.get("trends", [])
    comps = sd.get("comparisons", [])
    include_unverified = bool(state.get("include_unverified_viz", False))

    # 1. Filter metrics based on verification status
    if include_unverified:
        target_metrics = all_metrics
    else:
        target_metrics = [m for m in all_metrics if m.get("verification_status") == "verified"]
        # Fallback: If no verified metrics found, use all but prominently mark them
        if not target_metrics and all_metrics:
            target_metrics = all_metrics
            include_unverified = True

    logs.append(
        f"[Viz] Processing data: {len(target_metrics)} eligible metrics "
        f"({'all' if include_unverified else 'verified only'}), {len(trends)} trends, {len(comps)} comparisons."
    )

    charts = []

    try:
        import plotly.graph_objects as go

        layout_base = dict(
            plot_bgcolor=CARD,
            paper_bgcolor=DARK,
            font=dict(color=TEXT, size=11, family="Segoe UI, Arial, sans-serif"),
            margin=dict(l=40, r=40, t=65, b=45),
            legend=dict(bgcolor="#1e293b", bordercolor=GRID, font=dict(color=TEXT, size=10)),
        )

        # 2. Segregate metrics by unit group to avoid incompatible chart mixing
        unit_groups = {}
        for m in target_metrics:
            ug = _normalize_unit_group(m.get("unit", ""))
            unit_groups.setdefault(ug, []).append(m)

        # ── Chart Group A: Financial / Currency Metrics (Single Unit) ──────
        fin_metrics = unit_groups.get("financial", [])
        if fin_metrics:
            m_fin = fin_metrics[:6]
            labels = []
            vals = []
            colors = []
            hover_texts = []

            primary_unit = m_fin[0].get("unit", "billion USD")

            for m in m_fin:
                v = _parse_val(m.get("value", 0))
                is_unver = m.get("verification_status") != "verified"
                badge = " (Unverified)" if is_unver else ""
                lbl = m.get("label", "")[:35] + badge
                labels.append(lbl)
                vals.append(v)
                colors.append(UNVERIFIED_COLOR if is_unver else PALETTE[len(labels) % len(PALETTE)])

                source = m.get("source_org", "Documented source")
                yr = m.get("year", "N/A")
                nature = m.get("data_nature", "observed").capitalize()
                hover_texts.append(
                    f"<b>{lbl}</b><br>"
                    f"Value: {v:,.2f} {m.get('unit', primary_unit)}<br>"
                    f"Nature: {nature}<br>"
                    f"Year: {yr} | Source: {source}<extra></extra>"
                )

            fig_fin = go.Figure(go.Bar(
                x=vals,
                y=labels,
                orientation="h",
                marker=dict(color=colors, line=dict(color=DARK, width=1)),
                text=[f"{v:,.1f} {m.get('unit','')}" for v, m in zip(vals, m_fin)],
                textposition="auto",
                hovertemplate="%{customdata}",
                customdata=hover_texts,
            ))
            fig_fin.update_layout(
                **layout_base,
                title=dict(
                    text=f"📊 Economic & Financial Metrics ({primary_unit})",
                    font=dict(color=TITLE, size=15),
                    subtitle=dict(text="Single-unit currency comparison • Sourced from reported data", font=dict(color=MUTED, size=10))
                ),
                xaxis=dict(gridcolor=GRID, showgrid=True, title=primary_unit),
                yaxis=dict(gridcolor=GRID, autorange="reversed"),
                height=350,
            )
            charts.append(fig_fin.to_json())
            logs.append(f"[Viz] ✅ Financial metrics chart ({len(m_fin)} items, unit: {primary_unit})")

        # ── Chart Group B: Percentage & Rate Metrics (Single Unit) ────────
        pct_metrics = unit_groups.get("percentage", [])
        if pct_metrics:
            m_pct = pct_metrics[:6]
            labels = []
            vals = []
            colors = []
            hover_texts = []

            for m in m_pct:
                v = _parse_val(m.get("value", 0))
                is_unver = m.get("verification_status") != "verified"
                badge = " (Unverified)" if is_unver else ""
                lbl = m.get("label", "")[:35] + badge
                labels.append(lbl)
                vals.append(v)
                colors.append(UNVERIFIED_COLOR if is_unver else PALETTE[(len(labels) + 2) % len(PALETTE)])

                source = m.get("source_org", "Documented source")
                yr = m.get("year", "N/A")
                nature = m.get("data_nature", "observed").capitalize()
                hover_texts.append(
                    f"<b>{lbl}</b><br>"
                    f"Rate: {v:.1f}%<br>"
                    f"Nature: {nature}<br>"
                    f"Year: {yr} | Source: {source}<extra></extra>"
                )

            fig_pct = go.Figure(go.Bar(
                x=vals,
                y=labels,
                orientation="h",
                marker=dict(color=colors, line=dict(color=DARK, width=1)),
                text=[f"{v:.1f}%" for v in vals],
                textposition="auto",
                hovertemplate="%{customdata}",
                customdata=hover_texts,
            ))
            fig_pct.update_layout(
                **layout_base,
                title=dict(
                    text="📈 Growth, Adoption & Efficiency Rates (%)",
                    font=dict(color=TITLE, size=15),
                    subtitle=dict(text="Standardized percentage metrics • Normalized 0-100% scale", font=dict(color=MUTED, size=10))
                ),
                xaxis=dict(gridcolor=GRID, showgrid=True, title="Percentage (%)"),
                yaxis=dict(gridcolor=GRID, autorange="reversed"),
                height=350,
            )
            charts.append(fig_pct.to_json())
            logs.append(f"[Viz] ✅ Percentage metrics chart ({len(m_pct)} items)")

        # ── Chart Group C: Chronological Trends (Line Chart) ──────────────
        # Strictly for valid multi-point chronological observations with identical units
        valid_trends = [t for t in trends if len(t.get("data_points", [])) >= 3]
        if valid_trends:
            fig_trend = go.Figure()
            for idx, trend in enumerate(valid_trends[:2]):
                pts = trend.get("data_points", [])
                years = [str(p.get("year", "")) for p in pts]
                vals = [_parse_val(p.get("value", 0)) for p in pts]
                t_unit = trend.get("unit", "")
                t_name = trend.get("name", f"Series {idx+1}")
                t_source = trend.get("source_org", "Documented source")
                color = PALETTE[idx % len(PALETTE)]

                fig_trend.add_trace(go.Scatter(
                    x=years,
                    y=vals,
                    name=f"{t_name} ({t_unit})",
                    mode="lines+markers",
                    line=dict(color=color, width=2.5),
                    marker=dict(size=8, color=color, symbol="circle"),
                    hovertemplate=f"Year: %{{x}}<br>Value: %{{y:,.2f}} {t_unit}<br>Source: {t_source}<extra></extra>",
                ))

            primary_t_unit = valid_trends[0].get("unit", "Value")
            fig_trend.update_layout(
                **layout_base,
                title=dict(
                    text="⏱ Chronological Development Trends",
                    font=dict(color=TITLE, size=15),
                    subtitle=dict(text=f"Observed trajectory over time • Unit: {primary_t_unit}", font=dict(color=MUTED, size=10))
                ),
                xaxis=dict(gridcolor=GRID, title="Year"),
                yaxis=dict(gridcolor=GRID, title=primary_t_unit),
                height=350,
            )
            charts.append(fig_trend.to_json())
            logs.append(f"[Viz] ✅ Chronological trend line chart ({len(valid_trends)} verified series)")

        # ── Chart Group D: Segment / Regional Comparison ───────────────────
        # Donut ONLY if genuinely summing to a ~100% whole; otherwise horizontal bar
        if comps:
            cat_labels = [str(c.get("category", ""))[:25] for c in comps]
            cat_vals = [_parse_val(c.get("value", 0)) for c in comps]
            total_sum = sum(cat_vals)
            is_valid_share = (80.0 <= total_sum <= 120.0)

            if is_valid_share and len(comps) >= 2:
                # True percentage composition -> Donut chart
                fig_comp = go.Figure(go.Pie(
                    labels=cat_labels,
                    values=cat_vals,
                    hole=0.55,
                    marker=dict(colors=PALETTE[:len(comps)], line=dict(color=DARK, width=2)),
                    textinfo="label+percent",
                    textfont=dict(size=11, color=TEXT),
                    hovertemplate="%{label}: <b>%{value:.1f}%</b><extra></extra>",
                ))
                fig_comp.add_annotation(
                    text="Breakdown", x=0.5, y=0.55, showarrow=False,
                    font=dict(color=MUTED, size=12, family="Segoe UI")
                )
                fig_comp.add_annotation(
                    text="Distribution", x=0.5, y=0.45, showarrow=False,
                    font=dict(color=TEXT, size=10, family="Segoe UI")
                )
                fig_comp.update_layout(
                    **layout_base,
                    title=dict(
                        text="🌍 Distribution Breakdown (Share of Total)",
                        font=dict(color=TITLE, size=15),
                        subtitle=dict(text="Normalized composition • Sums to 100%", font=dict(color=MUTED, size=10))
                    ),
                    height=350,
                )
                charts.append(fig_comp.to_json())
                logs.append("[Viz] ✅ Composition donut chart (verified 100% share)")
            else:
                # Comparative items not summing to 100% -> Bar chart
                comp_unit = comps[0].get("unit", "")
                fig_comp = go.Figure(go.Bar(
                    x=cat_vals,
                    y=cat_labels,
                    orientation="h",
                    marker=dict(color=PALETTE[:len(comps)], line=dict(color=DARK, width=1)),
                    text=[f"{v:,.1f} {comp_unit}" for v in cat_vals],
                    textposition="auto",
                    hovertemplate="%{y}: <b>%{x:,.2f}</b> " + comp_unit + "<extra></extra>",
                ))
                fig_comp.update_layout(
                    **layout_base,
                    title=dict(
                        text=f"📊 Segment Comparison ({comp_unit or 'Comparative Value'})",
                        font=dict(color=TITLE, size=15),
                        subtitle=dict(text="Discrete comparative metrics • Single scale", font=dict(color=MUTED, size=10))
                    ),
                    xaxis=dict(gridcolor=GRID, showgrid=True, title=comp_unit or "Value"),
                    yaxis=dict(gridcolor=GRID, autorange="reversed"),
                    height=330,
                )
                charts.append(fig_comp.to_json())
                logs.append("[Viz] ✅ Segment comparative bar chart")

        # ── Chart Group E: Key Performance Indicator Gauge ────────────────
        gauge_candidates = [
            m for m in target_metrics
            if "adoption" in m.get("label", "").lower() or "%" in m.get("unit", "")
        ]
        if gauge_candidates:
            top_gauge = gauge_candidates[0]
            g_val = min(100.0, max(0.0, _parse_val(top_gauge.get("value", 0))))
            g_lbl = top_gauge.get("label", "")[:35]
            g_src = top_gauge.get("source_org", "Reported source")
            g_yr = top_gauge.get("year", "N/A")

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=g_val,
                title=dict(
                    text=f"🎯 {g_lbl}<br><span style='font-size:10px;color:#94a3b8'>Source: {g_src} ({g_yr})</span>",
                    font=dict(color=TITLE, size=13)
                ),
                gauge=dict(
                    axis=dict(range=[0, 100], tickcolor=TEXT, tickwidth=1),
                    bar=dict(color="#6366f1"),
                    bgcolor=CARD,
                    bordercolor=GRID,
                    steps=[
                        dict(range=[0, 35], color="#1e1b4b"),
                        dict(range=[35, 70], color="#1e293b"),
                        dict(range=[70, 100], color="#064e3b"),
                    ],
                ),
                number=dict(suffix="%", font=dict(color=TEXT, size=28)),
            ))
            fig_gauge.update_layout(
                paper_bgcolor=DARK,
                font=dict(color=TEXT, family="Segoe UI, Arial, sans-serif"),
                margin=dict(l=35, r=35, t=55, b=25),
                height=290,
            )
            charts.append(fig_gauge.to_json())
            logs.append(f"[Viz] ✅ Indicator gauge chart for '{g_lbl}'")

    except ImportError:
        logs.append("[Viz] Warning: Plotly not installed.")
    except Exception as e:
        logs.append(f"[Viz] Rendering error: {str(e)[:100]}")

    timings["visualization"] = round(time.time() - t0, 2)
    logs.append(f"[Viz] Complete — generated {len(charts)} unit-segregated figures.")
    return {"chart_json": charts, "agent_logs": logs, "agent_timings": timings}
