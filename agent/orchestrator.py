"""Agent orchestrator — the main think → act → observe loop.

This is the brain of the agent. It coordinates scraping, filtering,
research, and scoring into an autonomous pipeline that reasons about
what to do at each step.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from agent.models import AgentState, FitSignal, JobListing
from agent.profile import TITLE_EXCLUSIONS, TITLE_PATTERNS_RE
from agent.researcher import research_company
from agent.scorer import score_job
from agent.scrapers import scrape_all
from config import SCRAPE_DELAY

logger = logging.getLogger(__name__)
console = Console()


def title_matches(title: str) -> bool:
    """Fast check: does this job title look like a leadership role?"""
    lower = title.lower()

    # Reject obvious non-fits first
    for exclusion in TITLE_EXCLUSIONS:
        if exclusion in lower:
            return False

    # Check for positive matches using word-boundary regex
    return any(pattern.search(lower) for pattern in TITLE_PATTERNS_RE)


class AgentOrchestrator:
    """Runs the full agent pipeline.

    The orchestrator implements a genuine think→act→observe loop:

    1. THINK: Decide what data we need
    2. ACT: Scrape job boards
    3. OBSERVE: How many listings? Any errors?
    4. THINK: Which listings are worth investigating?
    5. ACT: Filter by title relevance
    6. OBSERVE: How many candidates remain?
    7. THINK: What do we know about these companies?
    8. ACT: Research each company
    9. OBSERVE: Did we get useful context?
    10. THINK: How well does each role fit the candidate?
    11. ACT: Score each role with LLM
    12. OBSERVE: Rank results and identify best fits
    """

    def __init__(self) -> None:
        self.state = AgentState()

    async def run(self) -> AgentState:
        """Execute the full agent pipeline."""
        console.print("\n[bold blue]Job Fit Analyzer Agent[/bold blue]")
        console.print("=" * 50)

        # --- Phase 1: Scrape ---
        self.state.phase = "scraping"
        console.print("\n[bold]Phase 1: Scraping job boards[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scraping We Work Remotely & RemoteOK...", total=None)
            all_listings = await scrape_all()
            progress.update(task, description=f"Found {len(all_listings)} raw listings")

        self.state.jobs_scraped = len(all_listings)

        if not all_listings:
            console.print("[red]No listings found. Check network connectivity.[/red]")
            self.state.errors.append("No listings scraped from any source.")
            return self.state

        console.print(f"  Scraped [green]{len(all_listings)}[/green] total listings")

        # --- Phase 2: Filter ---
        self.state.phase = "filtering"
        console.print("\n[bold]Phase 2: Filtering for leadership roles[/bold]")

        candidates = [job for job in all_listings if title_matches(job.title)]
        self.state.jobs_filtered = len(candidates)

        console.print(
            f"  Filtered to [green]{len(candidates)}[/green] "
            f"potential leadership roles (from {len(all_listings)})"
        )

        if not candidates:
            console.print(
                "[yellow]No leadership roles found in current listings. "
                "This is expected — these roles are rare.[/yellow]"
            )
            # Still return the state so the UI can show "no results"
            return self.state

        # Show what we found
        filter_table = Table(title="Filtered Candidates")
        filter_table.add_column("Title", style="cyan")
        filter_table.add_column("Company", style="green")
        filter_table.add_column("Source", style="dim")
        for job in candidates:
            filter_table.add_row(job.title, job.company, job.source.value)
        console.print(filter_table)

        # --- Phase 3: Enrich WWR listings that lack descriptions ---
        self.state.phase = "enriching"
        wwr_without_desc = [
            j for j in candidates
            if j.source.value == "We Work Remotely" and not j.description
        ]

        if wwr_without_desc:
            console.print(
                f"\n[bold]Phase 2b: Fetching full descriptions "
                f"for {len(wwr_without_desc)} WWR listings[/bold]"
            )
            from agent.scrapers import WeWorkRemotelyScraper
            import httpx

            scraper = WeWorkRemotelyScraper()
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": "JobFitAnalyzer/1.0"},
                follow_redirects=True,
            ) as client:
                for job in wwr_without_desc:
                    await scraper.enrich_listing(client, job)
                    await asyncio.sleep(SCRAPE_DELAY)

        # --- Phase 4: Research ---
        self.state.phase = "researching"
        console.print(f"\n[bold]Phase 3: Researching {len(candidates)} companies[/bold]")

        research_map = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Researching...", total=len(candidates))
            for job in candidates:
                progress.update(task, description=f"Researching {job.company}...")
                if job.company not in research_map:
                    research_map[job.company] = research_company(
                        job.company, job.title
                    )
                    time.sleep(SCRAPE_DELAY)  # Be polite to DuckDuckGo
                self.state.jobs_researched += 1
                progress.advance(task)

        # --- Phase 5: Score ---
        self.state.phase = "scoring"
        console.print(f"\n[bold]Phase 4: Scoring {len(candidates)} roles against profile[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scoring...", total=len(candidates))
            for job in candidates:
                progress.update(task, description=f"Scoring {job.title} at {job.company}...")
                research = research_map.get(job.company)
                analysis = score_job(job, research)
                self.state.analyses.append(analysis)
                self.state.jobs_scored += 1
                progress.advance(task)

        # --- Phase 6: Rank & Report ---
        self.state.phase = "complete"
        ranked = self.state.ranked_results

        console.print(f"\n[bold]Results: {len(ranked)} roles analyzed[/bold]")

        if ranked:
            results_table = Table(title="Ranked Results")
            results_table.add_column("Rank", style="bold")
            results_table.add_column("Score", justify="right")
            results_table.add_column("Signal")
            results_table.add_column("Title", style="cyan")
            results_table.add_column("Company", style="green")
            results_table.add_column("G/Y/R", justify="center")

            for i, analysis in enumerate(ranked, 1):
                signal_color = {
                    FitSignal.GREEN: "green",
                    FitSignal.YELLOW: "yellow",
                    FitSignal.RED: "red",
                }[analysis.overall_signal]

                results_table.add_row(
                    str(i),
                    f"{analysis.overall_score:.0f}",
                    f"[{signal_color}]{analysis.overall_signal.value}[/{signal_color}]",
                    analysis.job.title,
                    analysis.job.company,
                    f"{analysis.green_count}/{analysis.yellow_count}/{analysis.red_count}",
                )

            console.print(results_table)

        console.print(f"\nCompleted in {self._elapsed()}.")
        return self.state

    def _elapsed(self) -> str:
        delta = datetime.now() - self.state.started_at
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        return f"{seconds // 60}m {seconds % 60}s"
