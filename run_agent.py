#!/usr/bin/env python3
"""Run the Job Fit Analyzer agent.

Usage:
    python run_agent.py

Requires ANTHROPIC_API_KEY environment variable to be set.
"""

import asyncio
import logging
import sys

from rich.console import Console

from agent.orchestrator import AgentOrchestrator
from agent.report import generate_markdown_report, save_results_json
from config import ANTHROPIC_API_KEY

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)


async def main() -> int:
    # Preflight check
    if not ANTHROPIC_API_KEY:
        console.print(
            "[red bold]Error:[/red bold] ANTHROPIC_API_KEY environment variable not set.\n"
            "Set it with: export ANTHROPIC_API_KEY=your-key-here"
        )
        return 1

    # Run the agent
    orchestrator = AgentOrchestrator()
    state = await orchestrator.run()

    # Generate outputs
    if state.analyses:
        json_path = save_results_json(state)
        console.print(f"\nResults saved to [cyan]{json_path}[/cyan]")

        report_path = generate_markdown_report(state)
        console.print(f"Report saved to [cyan]{report_path}[/cyan]")

        console.print(
            "\nTo view results in the web UI:\n"
            "  [bold]python run_web.py[/bold]\n"
            f"  Then open http://127.0.0.1:5000"
        )
    else:
        console.print(
            "\n[yellow]No roles matched the filter criteria.[/yellow]\n"
            "This is normal — senior leadership roles are rare on these boards.\n"
            "The agent searched for: CTO, VPE, VP Engineering, Head of Engineering, "
            "Director of Engineering, Fractional CTO."
        )
        # Still save empty results so the web UI shows a clean state
        save_results_json(state)
        generate_markdown_report(state)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
