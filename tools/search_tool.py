"""
ResearchPilot AI — Search Tool (Tavily wrapper)
"""
import os
from dotenv import load_dotenv

load_dotenv()


def web_search_items(query: str, max_results: int = 5) -> list:
    """Search the web using Tavily and return list of dicts: title, url, content."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        results = client.search(query=query, max_results=max_results)
        return results.get("results", [])
    except Exception:
        return []


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily. Falls back gracefully if key missing."""
    items = web_search_items(query=query, max_results=max_results)
    if not items:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return f"[Search unavailable — no TAVILY_API_KEY] Query was: {query}"
        return "No results found."

    output = []
    for i, item in enumerate(items, 1):
        output.append(
            f"[{i}] {item.get('title', 'No title')}\n"
            f"    URL: {item.get('url', '')}\n"
            f"    {item.get('content', '')[:600]}"
        )
    return "\n\n".join(output)

