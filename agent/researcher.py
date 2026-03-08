"""Company research via web search.

Gathers context about each company beyond what the job listing says,
so the scorer can make informed judgments about mission fit, funding
stage, and domain alignment.
"""

from __future__ import annotations

import logging

from duckduckgo_search import DDGS

from agent.models import CompanyResearch
from config import MAX_SEARCH_RESULTS

logger = logging.getLogger(__name__)


def research_company(company_name: str, job_title: str = "") -> CompanyResearch:
    """Search the web for context about a company.

    Uses DuckDuckGo to find information about the company's mission,
    industry, size, and funding. The job title is included in the query
    to help disambiguate common company names.
    """
    research = CompanyResearch(company_name=company_name)

    if not company_name or company_name == "Unknown":
        research.summary = "Company name not available — limited research possible."
        return research

    query = f"{company_name} company"
    if job_title:
        query += f" {job_title} engineering"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=MAX_SEARCH_RESULTS))
    except Exception as exc:
        logger.warning("Search failed for %s: %s", company_name, exc)
        research.summary = f"Search failed: {exc}"
        return research

    if not results:
        research.summary = "No search results found."
        return research

    # Collect raw snippets for the scorer to reason over
    snippets: list[str] = []
    for r in results:
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        snippet = f"[{title}]({href}): {body}" if href else f"{title}: {body}"
        snippets.append(snippet)

    research.raw_search_results = snippets
    research.summary = "\n".join(snippets)

    return research


def research_companies_batch(
    companies: list[tuple[str, str]],
) -> dict[str, CompanyResearch]:
    """Research multiple companies sequentially (respects rate limits).

    Args:
        companies: List of (company_name, job_title) tuples.

    Returns:
        Dict mapping company_name to CompanyResearch.
    """
    results: dict[str, CompanyResearch] = {}

    for company_name, job_title in companies:
        if company_name in results:
            continue  # Already researched this company
        results[company_name] = research_company(company_name, job_title)

    return results
