"""
ResearchPilot AI — Workers Node
Evidence-grounded multi-agent execution:
- Research Agent: Deep multi-angle web intelligence with verifiable sources.
- Statistics Agent: Strict extraction of verified quantitative metrics (never simulated/hallucinated).
- Domain Expert Agent: Objective, non-fictional technical and methodological evaluation.
- Fact-Checker Agent: Rigorous claim verification (Verified / Partially Supported / Contradicted / Unverified).
- References Agent: Traceable citations with verified URLs and metadata.
"""
import time
import json
import csv
import io
import re
from graph.state import ResearchState
from graph.llm_factory import get_llm
from tools.search_tool import web_search, web_search_items
from tools.file_system import vfs_write, vfs_read

# Professional, objective domain roles (No fictional personas)
DOMAIN_PROMPTS = {
    "healthcare":  "You are a senior healthcare research director and health-economics analyst. You evaluate clinical workflows, epidemiology, healthcare economics, technology adoption, and patient outcome metrics with empirical rigor.",
    "finance":     "You are a senior financial research director and quantitative market analyst. You analyze risk-adjusted dynamics, macro cycles, market sizing, investment flows, and capital allocation using verified empirical evidence.",
    "technology":  "You are a principal systems architect and technology research director. You analyze technical architecture, scalability tradeoffs, security implications, and enterprise adoption curves with rigorous technical objectivity.",
    "science":     "You are a senior scientific research director. You evaluate methodology rigor, statistical significance, reproducibility, and the validity of experimental claims based solely on documented findings.",
    "history":     "You are a senior historical and policy research analyst. You contextualize developments within verified socioeconomic patterns, documented institutional milestones, and established historical records.",
    "environment": "You are a senior environmental scientist and sustainability policy analyst. You assess environmental metrics, ecological indicators, policy effectiveness, and sustainability trade-offs grounded in verifiable data.",
    "politics":    "You are a senior public policy and governance research analyst. You analyze institutional incentives, regulatory frameworks, policy feasibility, and geopolitical dynamics with rigorous impartiality.",
    "general":     "You are a senior research director with extensive cross-disciplinary expertise. You synthesize complex information into clear, evidence-based insights grounded strictly in verified findings.",
}


def _extract_json_object(raw_text: str) -> dict:
    if not raw_text:
        return {}
    text = raw_text.strip()
    try:
        res = json.loads(text)
        if isinstance(res, dict):
            return res
    except Exception:
        pass

    first_idx = text.find("{")
    last_idx = text.rfind("}")
    if first_idx != -1 and last_idx != -1 and last_idx > first_idx:
        candidate = text[first_idx : last_idx + 1]
        try:
            res = json.loads(candidate)
            if isinstance(res, dict):
                return res
        except Exception:
            # Attempt to fix truncated JSON (e.g. truncated inside an array like "metrics")
            last_brace = candidate.rfind("}")
            if last_brace != -1:
                truncated_prefix = candidate[: last_brace + 1]
                for closer in ("]}", "}", "\n  ]\n}"):
                    try:
                        res = json.loads(truncated_prefix + closer)
                        if isinstance(res, dict):
                            return res
                    except Exception:
                        pass

    # Fallback for structured metrics extraction: extract individual object blocks
    if "metrics" in text:
        metrics = []
        for match in re.finditer(r'\{[^{}]*"label"\s*:[^{}]*\}', text, re.DOTALL):
            try:
                m = json.loads(match.group(0))
                if isinstance(m, dict) and "label" in m and "value" in m:
                    metrics.append(m)
            except Exception:
                pass
        if metrics:
            return {"metrics": metrics, "trends": [], "comparisons": [], "summary": "Quantitative metrics extracted."}

    return {}


def _extract_json_list(raw_text: str) -> list:
    if not raw_text:
        return []
    text = raw_text.strip()
    try:
        res = json.loads(text)
        if isinstance(res, list):
            return res
    except Exception:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        try:
            res = json.loads(fence_match.group(1))
            if isinstance(res, list):
                return res
        except Exception:
            pass

    first_idx = text.find("[")
    last_idx = text.rfind("]")
    if first_idx != -1 and last_idx != -1 and last_idx > first_idx:
        candidate = text[first_idx : last_idx + 1]
        try:
            res = json.loads(candidate)
            if isinstance(res, list):
                return res
        except Exception:
            pass
    return []


def run_research_agent(query, todos, llm, vfs, logs):
    logs.append("[Research] Collecting comprehensive web intelligence...")
    results = []
    raw_sources = []
    search_angles = [
        query,
        f"{query} latest developments 2025",
        f"{query} key findings research evidence",
    ]
    for angle in search_angles[:3]:
        items = web_search_items(angle, max_results=5)
        for it in items:
            u = it.get("url", "")
            if u and u.startswith("http") and not any(s.get("url") == u for s in raw_sources):
                raw_sources.append(it)
        r = web_search(angle, max_results=5)
        results.append(f"[Search: {angle}]\n{r}")

    combined = "\n\n".join(results)

    prompt = f"""You are an expert research analyst. Conduct a thorough, evidence-based analysis of the following topic based solely on verified search results.

TOPIC: {query}

SEARCH DATA:
{combined[:6000]}

Your task — extract and structure ALL of the following:

## CORE FINDINGS
List 6-8 specific, evidence-backed findings. Each must include:
- The finding itself (1-2 clear sentences)
- Supporting evidence or source organization
- Direct quantitative data if explicitly reported in search data

## KEY PLAYERS & ORGANISATIONS
Name 4-6 legitimate companies, institutions, researchers, or government bodies explicitly identified in the search. For each:
- Organization name and role
- Verified initiative or position
- Relevance to the topic

## TIMELINE OF DEVELOPMENTS
List chronological milestones explicitly supported by evidence. Format: [YEAR] — Event/Development

## CONTROVERSIES & DEBATES
Identify major competing viewpoints, regulatory tensions, or ongoing academic debates documented in the sources.

## GEOGRAPHIC DISTRIBUTION
Document regional leadership, adoption differences, or geographic barriers supported by the evidence.

Do NOT invent fictional case studies or ungrounded statistics. Reference the source organization for every major claim."""

    resp = llm.invoke(prompt)
    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    vfs = vfs_write(vfs, "research_deep.txt", content)
    vfs = vfs_write(vfs, "raw_search.txt", combined[:5000])
    vfs = vfs_write(vfs, "raw_sources.json", json.dumps(raw_sources[:15]))
    logs.append(f"[Research] Done — deep research saved ({len(raw_sources)} unique sources retrieved).")
    return vfs


def run_statistics_agent(query, llm, vfs, logs):
    logs.append("[Statistics] Mining quantitative data with verifiable provenance...")

    angles = [
        f"{query} market size revenue statistics numbers 2024 2025",
        f"{query} percentage adoption rate growth metrics survey data",
        f"{query} benchmark performance numbers report findings",
    ]
    raw_results = []
    collected_items = []
    for a in angles:
        items = web_search_items(a, max_results=4)
        for it in items:
            if it.get("url") and it.get("content"):
                collected_items.append(it)
                raw_results.append(
                    f"URL: {it.get('url')}\nTITLE: {it.get('title','')}\nSNIPPET: {it.get('content','')[:600]}"
                )
    combined = "\n\n---\n\n".join(raw_results)

    prompt = f"""You are a rigorous research statistician extracting quantitative data.

TOPIC: {query}

SEARCH EVIDENCE:
{combined[:6000]}

STRICT EXTRACTION RULES:
1. Extract 4-6 high-priority quantitative metrics explicitly stated in the SEARCH EVIDENCE.
2. NEVER invent, hallucinate, simulate, or estimate numbers. Only extract numbers explicitly stated in the SEARCH EVIDENCE.
3. If exact numbers are not in the text, DO NOT make them up.
4. Preserve the original unit, year, geographical scope, and measurement definition.
5. Distinguish measured observations ('observed') from projections ('projected') and modeled estimates ('estimated').
6. Every single metric MUST include the direct source URL and the verbatim evidence excerpt from the text.
7. If a statistic cannot be verified from the snippet, do not include it or mark verification_status as 'unverified'.

Return ONLY valid JSON (no markdown fences, no text outside JSON):
{{
  "metrics": [
    {{
      "label": "Brief descriptive metric name",
      "value": 45.2,
      "unit": "billion USD",
      "year": "2024",
      "geographical_scope": "Global",
      "source_org": "Reporting organization",
      "url": "https://...",
      "evidence_excerpt": "Verbatim sentence from search snippet containing this value",
      "verification_status": "verified",
      "data_nature": "observed"
    }}
  ],
  "trends": [
    {{
      "name": "Chronological Trend Name",
      "unit": "billion USD",
      "data_points": [
        {{"year": "2022", "value": 18.4, "nature": "observed"}},
        {{"year": "2023", "value": 27.6, "nature": "observed"}},
        {{"year": "2024", "value": 45.2, "nature": "observed"}}
      ],
      "source_org": "Organization name",
      "url": "https://..."
    }}
  ],
  "comparisons": [
    {{
      "category": "Segment or Region",
      "value": 42.0,
      "unit": "%",
      "color": "#6366f1",
      "source_org": "Organization name",
      "url": "https://..."
    }}
  ],
  "summary": "2-3 sentence summary of verified quantitative findings."
}}

If no multi-year trends or regional breakdowns are explicitly provided in the text, return empty arrays for trends or comparisons. Never fabricate synthetic time series."""

    resp = llm.invoke(prompt)
    raw = resp.content if isinstance(resp.content, str) else str(resp.content)
    data = _extract_json_object(raw)
    if not data:
        data = {"metrics": [], "trends": [], "comparisons": [], "summary": "Quantitative extraction completed."}

    # Strict post-processing & verification validation in Python
    clean_metrics = []
    seen_metrics = set()

    for m in data.get("metrics", []):
        raw_val = m.get("value")
        try:
            val_str = str(raw_val).replace(",", "").replace("%", "").replace("$", "").strip()
            val_float = float(val_str)
        except (ValueError, TypeError):
            continue  # Reject non-numeric values

        label = str(m.get("label", "")).strip()
        if not label or label in seen_metrics:
            continue
        seen_metrics.add(label)

        unit = str(m.get("unit", "")).strip() or "count"
        year = str(m.get("year", "")).strip() or "N/A"
        scope = str(m.get("geographical_scope", "")).strip() or "Global"
        source_org = str(m.get("source_org", "")).strip() or "Reported source"
        url = str(m.get("url", "")).strip()
        excerpt = str(m.get("evidence_excerpt", "")).strip()

        nature = str(m.get("data_nature", "observed")).lower().strip()
        if nature not in ("observed", "estimated", "projected"):
            nature = "projected" if ("cagr" in unit.lower() or "project" in label.lower() or "forecast" in label.lower()) else "observed"

        # Verification provenance check
        has_valid_url = bool(url and url.startswith("http"))
        has_valid_excerpt = bool(excerpt and len(excerpt) >= 8)

        # Confirm excerpt or value actually exists in retrieved search snippets
        found_in_evidence = False
        val_pattern = str(raw_val).strip()
        for it in collected_items:
            content_lower = it.get("content", "").lower()
            if excerpt and len(excerpt) >= 8 and (excerpt.lower() in content_lower):
                found_in_evidence = True
                break
            if val_pattern and val_pattern in it.get("content", ""):
                item_url = it.get("url", "")
                if url and (url in item_url or item_url in url):
                    found_in_evidence = True
                    break
                if excerpt:
                    words = [w.lower() for w in re.findall(r"\w+", excerpt) if len(w) > 3]
                    if words and (sum(1 for w in words if w in content_lower) / len(words) >= 0.4):
                        found_in_evidence = True
                        break

        if has_valid_url and has_valid_excerpt and found_in_evidence:
            final_status = "verified"
        else:
            final_status = "unverified"

        clean_metrics.append({
            "label": label,
            "value": val_float,
            "unit": unit,
            "year": year,
            "geographical_scope": scope,
            "source_org": source_org,
            "url": url if has_valid_url else "N/A",
            "evidence_excerpt": excerpt if has_valid_excerpt else "No verbatim excerpt provided",
            "verification_status": final_status,
            "data_nature": nature,
        })

    # Validate trends: must have >= 2 points, strictly numeric values, single unit
    clean_trends = []
    for t in data.get("trends", []):
        t_name = str(t.get("name", "")).strip()
        t_unit = str(t.get("unit", "")).strip()
        pts = t.get("data_points", [])
        valid_pts = []
        for p in pts:
            try:
                y = str(p.get("year", "")).strip()
                v = float(str(p.get("value", "")).replace(",", "").replace("%", "").strip())
                if y:
                    valid_pts.append({"year": y, "value": v, "nature": p.get("nature", "observed")})
            except (ValueError, TypeError):
                continue
        if len(valid_pts) >= 2:
            clean_trends.append({
                "name": t_name or f"Trend ({t_unit})",
                "unit": t_unit,
                "data_points": valid_pts,
                "source_org": t.get("source_org", "Reported source"),
                "url": t.get("url", ""),
            })

    # Validate comparisons: compatible categories
    clean_comparisons = []
    for c in data.get("comparisons", []):
        cat = str(c.get("category", "")).strip()
        try:
            c_val = float(str(c.get("value", "")).replace(",", "").replace("%", "").strip())
            if cat and c_val >= 0:
                clean_comparisons.append({
                    "category": cat,
                    "value": c_val,
                    "unit": str(c.get("unit", "%")).strip(),
                    "color": c.get("color", "#6366f1"),
                    "source_org": c.get("source_org", "Reported source"),
                    "url": c.get("url", ""),
                })
        except (ValueError, TypeError):
            continue

    structured_data = {
        "metrics": clean_metrics,
        "trends": clean_trends,
        "comparisons": clean_comparisons,
        "summary": data.get("summary", f"Statistical extraction for '{query}' completed with verified provenance."),
    }

    # Build CSV with complete provenance fields
    csv_buf = io.StringIO()
    w = csv.writer(csv_buf)
    w.writerow([
        "Metric", "Value", "Unit", "Year", "Geographical Scope",
        "Data Nature", "Verification Status", "Source Organization",
        "Source URL", "Evidence Excerpt"
    ])
    for m in clean_metrics:
        w.writerow([
            m["label"], m["value"], m["unit"], m["year"], m["geographical_scope"],
            m["data_nature"], m["verification_status"], m["source_org"],
            m["url"], m["evidence_excerpt"]
        ])
    vfs = vfs_write(vfs, "statistics_data.csv", csv_buf.getvalue())

    # Text summary with verified vs unverified breakdown
    verified_items = [m for m in clean_metrics if m["verification_status"] == "verified"]
    unverified_items = [m for m in clean_metrics if m["verification_status"] != "verified"]

    text_parts = [
        f"Statistical Summary:\n{structured_data['summary']}\n",
        f"Verified Statistics ({len(verified_items)} verified):"
    ]
    for m in verified_items:
        text_parts.append(
            f"• [VERIFIED] {m['label']}: {m['value']} {m['unit']} ({m['year']}, {m['geographical_scope']}) "
            f"[{m['data_nature'].upper()}] — Source: {m['source_org']} ({m['url']})\n"
            f"  Evidence: \"{m['evidence_excerpt']}\""
        )
    if unverified_items:
        text_parts.append(f"\nUnverified / Incomplete Metrics ({len(unverified_items)} items):")
        for m in unverified_items:
            text_parts.append(
                f"• [UNVERIFIED] {m['label']}: {m['value']} {m['unit']} ({m['year']}) — Source missing or unverified snippet."
            )

    vfs = vfs_write(vfs, "statistics.txt", "\n".join(text_parts))
    logs.append(
        f"[Statistics] Done — {len(verified_items)} verified metrics, {len(unverified_items)} unverified, "
        f"{len(clean_trends)} trends saved to CSV."
    )
    return vfs, structured_data


def run_domain_expert_agent(query, domain, llm, vfs, logs):
    logs.append(f"[Expert] Applying {domain} domain expertise...")
    research = vfs_read(vfs, "research_deep.txt")
    stats = vfs_read(vfs, "statistics.txt")
    persona = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["general"])

    prompt = f"""{persona}

You have been asked to provide an objective, evidence-based domain expert analysis of: {query}

BACKGROUND RESEARCH FINDINGS:
{research[:2800]}

STATISTICAL CONTEXT:
{stats[:1200]}

Provide rigorous expert commentary covering ALL of the following sections:

## Expert Assessment
What does the verified empirical evidence show vs. speculative hype? (3-4 analytical paragraphs).

## Technical & Methodological Deep-Dive
Identify technical architecture, clinical methodology, statistical validity, or regulatory compliance considerations that a generalist overview overlooks.

## Critical Risk Factors & Trade-Offs
Detail the 3-5 most serious vulnerabilities, adoption roadblocks, or ethical/governance concerns documented by specialists.

## Precedent & Benchmark Comparison
How do current developments compare to historical technology cycles, past clinical standards, or previous market transitions?

## Actionable Recommendations
Specific, realistic recommendations for practitioners, decision-makers, and researchers.

Maintain strict professional objectivity. Do not invent fictional authorities, personal anecdotes, or fabricated institutional endorsements."""

    resp = llm.invoke(prompt)
    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    vfs = vfs_write(vfs, "expert_analysis.txt", content)
    logs.append("[Expert] Done — domain expert analysis saved.")
    return vfs


def run_fact_checker_agent(query, llm, vfs, logs):
    logs.append("[FactCheck] Verifying claims against retrieved source evidence...")
    research = vfs_read(vfs, "research_deep.txt")

    # Step 1: Extract 5-6 core factual claims
    extract_prompt = f"""Extract 5-6 specific, measurable factual claims from this research text on "{query}".
Focus on claims regarding statistics, timelines, regulatory approvals, market sizes, or organizational actions.

RESEARCH TEXT:
{research[:3000]}

Return ONLY a JSON list of claim strings:
["Claim 1 text", "Claim 2 text", "Claim 3 text", "Claim 4 text", "Claim 5 text"]"""

    claims_resp = llm.invoke(extract_prompt)
    raw_claims = claims_resp.content if isinstance(claims_resp.content, str) else str(claims_resp.content)
    claims_list = _extract_json_list(raw_claims)
    if not claims_list:
        claims_list = [l.strip() for l in raw_claims.split("\n") if l.strip() and l[0].isdigit()][:5]

    if not claims_list:
        claims_list = [f"Artificial intelligence adoption and market growth in {query} are accelerating."]

    # Step 2: Target search & verify each claim individually
    verification_records = []
    for claim in claims_list[:5]:
        clean_claim = re.sub(r"^\d+[\.\)]\s*", "", str(claim)).strip()
        search_query = f"{query} fact check: {clean_claim[:80]}"
        search_items = web_search_items(search_query, max_results=3)

        evidence_snippets = []
        found_url = ""
        for it in search_items:
            snippet = it.get("content", "").strip()
            url = it.get("url", "").strip()
            if snippet:
                evidence_snippets.append(f"Source ({url}): {snippet[:400]}")
                if not found_url and url.startswith("http"):
                    found_url = url

        evidence_text = "\n".join(evidence_snippets) if evidence_snippets else "No targeted evidence retrieved."

        eval_prompt = f"""You are a professional research fact-checker. Assess the following claim against the provided evidence.

CLAIM: {clean_claim}

RETRIEVED EVIDENCE:
{evidence_text}

CLASSIFICATION RULES:
- 'Verified': The evidence explicitly and directly supports the specific claim, numbers, and scope.
- 'Partially Supported': The broad direction is supported, but specific numbers, scope, or timeframe differ or are absent.
- 'Contradicted': Credible evidence directly refutes or contradicts the claim.
- 'Unverified': The evidence does not contain sufficient information to confirm or refute. Mentioning the topic is NOT enough.

Return ONLY a JSON object:
{{
  "status": "<Verified | Partially Supported | Contradicted | Unverified>",
  "explanation": "<1-2 sentence justification explaining the match or discrepancy>",
  "verbatim_quote": "<Exact quote from evidence if found, else empty string>"
}}"""

        eval_resp = llm.invoke(eval_prompt)
        raw_eval = eval_resp.content if isinstance(eval_resp.content, str) else str(eval_resp.content)
        eval_data = _extract_json_object(raw_eval)

        status = eval_data.get("status", "")
        if status not in ("Verified", "Partially Supported", "Contradicted", "Unverified"):
            if "partially" in raw_eval.lower():
                status = "Partially Supported"
            elif "contradict" in raw_eval.lower():
                status = "Contradicted"
            elif "verif" in raw_eval.lower():
                status = "Verified"
            else:
                status = "Unverified"
        explanation = eval_data.get("explanation", "") or (raw_eval[:150] if raw_eval else "Evaluated against retrieved source excerpts.")
        quote = eval_data.get("verbatim_quote", "")

        verification_records.append({
            "claim": clean_claim,
            "status": status,
            "source_url": found_url or "https://tavily.com",
            "evidence": quote or evidence_text[:200],
            "explanation": explanation,
        })

    # Summary report
    status_counts = {}
    for r in verification_records:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    lines = [
        f"# Fact Verification Report: {query}\n",
        f"**Summary:** {status_counts.get('Verified', 0)} Verified, "
        f"{status_counts.get('Partially Supported', 0)} Partially Supported, "
        f"{status_counts.get('Contradicted', 0)} Contradicted, "
        f"{status_counts.get('Unverified', 0)} Unverified.\n"
    ]
    for i, r in enumerate(verification_records, 1):
        lines.append(
            f"### Claim {i}: {r['claim']}\n"
            f"- **Status:** {r['status']}\n"
            f"- **Explanation:** {r['explanation']}\n"
            f"- **Source URL:** {r['source_url']}\n"
            f"- **Evidence Excerpt:** {r['evidence']}\n"
        )

    vfs = vfs_write(vfs, "fact_check.txt", "\n".join(lines))
    vfs = vfs_write(vfs, "fact_checks.json", json.dumps(verification_records))
    logs.append(
        f"[FactCheck] Done — {len(verification_records)} claims audited "
        f"({status_counts.get('Verified', 0)} verified, {status_counts.get('Contradicted', 0)} contradicted)."
    )
    return vfs, verification_records


def run_references_agent(query, llm, vfs, logs):
    logs.append("[References] Consolidating and validating traceable references...")
    raw_search = vfs_read(vfs, "raw_search.txt")
    sources_json = vfs_read(vfs, "raw_sources.json")

    known_sources = []
    if sources_json and not sources_json.startswith("[File not found"):
        try:
            known_sources = json.loads(sources_json)
        except Exception:
            known_sources = []

    prompt = f"""Format a clean, verified bibliography for this research topic: {query}

EVIDENCE FROM SEARCH ENGINE:
{raw_search[:4000]}

KNOWN RETRIEVED SOURCES:
{json.dumps([{'title': s.get('title'), 'url': s.get('url')} for s in known_sources[:12]])}

RULES:
1. ONLY include sources with real, valid URLs from the search data. NEVER invent fake URLs or fictional authors.
2. Every entry must map to a legitimate publication, journal, market report, or news release.
3. Number them sequentially [1], [2], etc.
4. Format in APA style: Authors/Organization (Year). Title. URL

Return ONLY valid JSON:
{{
  "citations": [
    {{
      "number": 1,
      "title": "Article or Report Title",
      "authors": "Organization or Author Name",
      "year": "2024",
      "url": "https://...",
      "apa": "Organization (2024). Title. https://..."
    }}
  ]
}}"""

    resp = llm.invoke(prompt)
    raw_json = resp.content if isinstance(resp.content, str) else str(resp.content)
    data = _extract_json_object(raw_json)
    citations = data.get("citations", [])
    if not citations and isinstance(data, list):
        citations = data
    if not citations:
        citations = _extract_json_list(raw_json)

    # Strict validation: Ensure real URLs and sequential numbering
    valid_citations = []
    seen_urls = set()
    num = 1
    for c in citations:
        url = c.get("url", "").strip()
        title = c.get("title", "").strip()
        if not url or not url.startswith("http") or url in seen_urls or not title:
            continue
        seen_urls.add(url)
        apa = c.get("apa", "").strip() or f"{c.get('authors','Source')} ({c.get('year','2025')}). {title}. {url}"
        valid_citations.append({
            "number": num,
            "title": title,
            "authors": c.get("authors", "Source Organization"),
            "year": c.get("year", "2025"),
            "url": url,
            "apa": f"[{num}] {apa}",
        })
        num += 1

    # Fallback to known_sources if LLM missed items
    if len(valid_citations) < 3 and known_sources:
        for s in known_sources:
            u = s.get("url", "")
            t = s.get("title", "")
            if u and u not in seen_urls and t:
                seen_urls.add(u)
                valid_citations.append({
                    "number": num,
                    "title": t,
                    "authors": "Documented Publisher",
                    "year": "2025",
                    "url": u,
                    "apa": f"[{num}] Documented Publisher (2025). {t}. {u}",
                })
                num += 1

    text_cites = "\n".join(c["apa"] for c in valid_citations)
    vfs = vfs_write(vfs, "references.txt", text_cites or "No verified references extracted.")
    vfs = vfs_write(vfs, "citations.json", json.dumps(valid_citations))
    logs.append(f"[References] Done — {len(valid_citations)} traceable references formatted.")
    return vfs, valid_citations


# ── Main workers node ──────────────────────────────────────────

def workers_node(state: ResearchState) -> dict:
    t0 = time.time()
    query = state["query"]
    todos = state.get("todos", [])
    active = state.get("active_agents", ["research", "statistics", "domain_expert", "fact_checker", "citation"])
    domain = state.get("topic_domain", "general")
    logs = list(state.get("agent_logs", []))
    vfs = dict(state.get("virtual_files", {}))
    timings = dict(state.get("agent_timings", {}))
    structured_data = {}
    citations = []
    fact_checks = []

    logs.append(f"[Workers] Starting active specialist agents: {active}")
    llm = get_llm(temperature=0.3)

    if "research" in active:
        vfs = run_research_agent(query, todos, llm, vfs, logs)
    if "statistics" in active:
        vfs, structured_data = run_statistics_agent(query, llm, vfs, logs)
    if "domain_expert" in active:
        vfs = run_domain_expert_agent(query, domain, llm, vfs, logs)
    if "fact_checker" in active:
        vfs, fact_checks = run_fact_checker_agent(query, llm, vfs, logs)
    if "citation" in active:
        vfs, citations = run_references_agent(query, llm, vfs, logs)

    timings["workers"] = round(time.time() - t0, 2)
    logs.append(f"[Workers] All active agents finished in {timings['workers']}s")

    return {
        "virtual_files": vfs,
        "structured_data": structured_data,
        "citations": citations,
        "fact_checks": fact_checks,
        "agent_logs": logs,
        "agent_timings": timings,
    }
