"""Markdown report generator.

Produces a formatted report from analysis results, saved to the
reports/ directory with a timestamp.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from agent.models import AgentState, FitSignal, JobAnalysis
from config import REPORTS_DIR


def _signal_emoji(signal: FitSignal) -> str:
    """Map signal to a text indicator for Markdown."""
    return {
        FitSignal.GREEN: "[GREEN]",
        FitSignal.YELLOW: "[YELLOW]",
        FitSignal.RED: "[RED]",
    }[signal]


def generate_markdown_report(state: AgentState) -> Path:
    """Generate a Markdown report and save it to the reports directory."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = REPORTS_DIR / f"job_fit_report_{timestamp}.md"

    ranked = state.ranked_results
    lines: list[str] = []

    lines.append("# Job Fit Analysis Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append(f"- Jobs scraped: {state.jobs_scraped}")
    lines.append(f"- Jobs after title filter: {state.jobs_filtered}")
    lines.append(f"- Jobs scored: {state.jobs_scored}")
    lines.append("")

    if not ranked:
        lines.append("*No roles matched the leadership title filter.*")
        lines.append("")
        report_path.write_text("\n".join(lines))
        return report_path

    # Signal distribution
    green = sum(1 for a in ranked if a.overall_signal == FitSignal.GREEN)
    yellow = sum(1 for a in ranked if a.overall_signal == FitSignal.YELLOW)
    red = sum(1 for a in ranked if a.overall_signal == FitSignal.RED)
    lines.append(f"- GREEN: {green} | YELLOW: {yellow} | RED: {red}")
    lines.append("")

    # Results table
    lines.append("## Ranked Results")
    lines.append("")
    lines.append("| Rank | Score | Signal | Title | Company |")
    lines.append("|------|-------|--------|-------|---------|")
    for i, a in enumerate(ranked, 1):
        signal = _signal_emoji(a.overall_signal)
        lines.append(
            f"| {i} | {a.overall_score:.0f} | {signal} | "
            f"[{a.job.title}]({a.job.url}) | {a.job.company} |"
        )
    lines.append("")

    # Detailed analysis for each role
    lines.append("## Detailed Analysis")
    lines.append("")

    for i, a in enumerate(ranked, 1):
        lines.append(f"### {i}. {a.job.title} — {a.job.company}")
        lines.append("")
        lines.append(f"- **Source**: {a.job.source.value}")
        lines.append(f"- **Location**: {a.job.location or 'Unknown'}")
        lines.append(f"- **URL**: {a.job.url}")
        if a.job.salary:
            lines.append(f"- **Salary**: {a.job.salary}")
        lines.append(f"- **Overall**: {_signal_emoji(a.overall_signal)} (Score: {a.overall_score:.0f})")
        lines.append("")
        lines.append(f"**Assessment**: {a.overall_reasoning}")
        lines.append("")

        if a.dimension_scores:
            lines.append("| Dimension | Signal | Reasoning |")
            lines.append("|-----------|--------|-----------|")
            for d in a.dimension_scores:
                signal = _signal_emoji(d.signal)
                # Escape pipe characters in reasoning
                reasoning = d.reasoning.replace("|", "\\|")
                lines.append(f"| {d.dimension} | {signal} | {reasoning} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Errors
    if state.errors:
        lines.append("## Errors")
        for error in state.errors:
            lines.append(f"- {error}")
        lines.append("")

    report_path.write_text("\n".join(lines))
    return report_path


def save_results_json(state: AgentState) -> Path:
    """Save results as JSON for the web UI to consume."""
    results_path = REPORTS_DIR / "latest_results.json"

    data = {
        "meta": {
            "started_at": state.started_at.isoformat(),
            "jobs_scraped": state.jobs_scraped,
            "jobs_filtered": state.jobs_filtered,
            "jobs_researched": state.jobs_researched,
            "jobs_scored": state.jobs_scored,
            "errors": state.errors,
        },
        "analyses": [],
    }

    for a in state.ranked_results:
        data["analyses"].append({
            "job": {
                "title": a.job.title,
                "company": a.job.company,
                "url": a.job.url,
                "source": a.job.source.value,
                "location": a.job.location,
                "tags": a.job.tags,
                "salary": a.job.salary,
                "posted_date": a.job.posted_date,
            },
            "overall_signal": a.overall_signal.value,
            "overall_score": a.overall_score,
            "overall_reasoning": a.overall_reasoning,
            "dimension_scores": [
                {
                    "dimension": d.dimension,
                    "signal": d.signal.value,
                    "reasoning": d.reasoning,
                }
                for d in a.dimension_scores
            ],
        })

    results_path.write_text(json.dumps(data, indent=2))
    return results_path
