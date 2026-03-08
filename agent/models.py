"""Data models for jobs, scores, and analysis results."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobSource(str, Enum):
    """Where the job listing was found."""
    WE_WORK_REMOTELY = "We Work Remotely"
    REMOTE_OK = "RemoteOK"


class FitSignal(str, Enum):
    """Traffic-light fit signal for a scoring dimension."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""
    dimension: str
    signal: FitSignal
    reasoning: str


class JobListing(BaseModel):
    """A scraped job listing from a job board."""
    title: str
    company: str
    url: str
    source: JobSource
    description: str = ""
    location: str = ""
    tags: list[str] = Field(default_factory=list)
    posted_date: Optional[str] = None
    salary: Optional[str] = None


class CompanyResearch(BaseModel):
    """Research gathered about a company via web search."""
    company_name: str
    summary: str = ""
    industry: str = ""
    mission: str = ""
    funding_stage: str = ""
    size: str = ""
    raw_search_results: list[str] = Field(default_factory=list)


class JobAnalysis(BaseModel):
    """Complete analysis of a job listing's fit."""
    job: JobListing
    research: CompanyResearch
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    overall_signal: FitSignal = FitSignal.YELLOW
    overall_reasoning: str = ""
    overall_score: float = 0.0  # 0-100 for ranking

    @property
    def green_count(self) -> int:
        return sum(1 for d in self.dimension_scores if d.signal == FitSignal.GREEN)

    @property
    def yellow_count(self) -> int:
        return sum(1 for d in self.dimension_scores if d.signal == FitSignal.YELLOW)

    @property
    def red_count(self) -> int:
        return sum(1 for d in self.dimension_scores if d.signal == FitSignal.RED)


class AgentState(BaseModel):
    """Tracks the agent's progress through its work."""
    started_at: datetime = Field(default_factory=datetime.now)
    phase: str = "initializing"
    jobs_scraped: int = 0
    jobs_filtered: int = 0
    jobs_researched: int = 0
    jobs_scored: int = 0
    analyses: list[JobAnalysis] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def ranked_results(self) -> list[JobAnalysis]:
        """Return analyses sorted by score, best first."""
        return sorted(self.analyses, key=lambda a: a.overall_score, reverse=True)
