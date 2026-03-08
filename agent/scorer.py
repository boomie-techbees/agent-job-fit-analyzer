"""LLM-powered fit scoring engine.

Sends each job listing + company research to Claude for structured
evaluation against the candidate profile. Returns per-dimension
scores with reasoning.
"""

from __future__ import annotations

import json
import logging

import anthropic

from agent.models import (
    CompanyResearch,
    DimensionScore,
    FitSignal,
    JobAnalysis,
    JobListing,
)
from agent.profile import CANDIDATE_PROFILE, SCORING_DIMENSIONS
from config import ANTHROPIC_API_KEY, SCORING_MODEL

logger = logging.getLogger(__name__)

# Signal weights for computing an overall numeric score
SIGNAL_WEIGHT = {
    FitSignal.GREEN: 100,
    FitSignal.YELLOW: 50,
    FitSignal.RED: 0,
}


def _build_scoring_prompt(job: JobListing, research: CompanyResearch) -> str:
    """Build the prompt that asks Claude to score this job."""
    dimensions_text = "\n".join(
        f"- **{d['name']}**: {d['description']}" for d in SCORING_DIMENSIONS
    )

    profile_text = json.dumps(CANDIDATE_PROFILE, indent=2)

    return f"""You are evaluating a job listing for fit against a specific candidate profile.

## Candidate Profile
{profile_text}

## Job Listing
- **Title**: {job.title}
- **Company**: {job.company}
- **Location**: {job.location}
- **Source**: {job.source.value}
- **URL**: {job.url}
- **Tags**: {', '.join(job.tags) if job.tags else 'None'}
- **Salary**: {job.salary or 'Not listed'}
- **Posted**: {job.posted_date or 'Unknown'}

### Description
{job.description[:3000] if job.description else 'No description available.'}

## Company Research
{research.summary if research.summary else 'No research available.'}

## Scoring Dimensions
Evaluate the job on each of these dimensions. For each, assign a signal:
- **green**: Strong fit for this candidate
- **yellow**: Partial fit or unclear
- **red**: Poor fit for this candidate

Dimensions:
{dimensions_text}

## Instructions
1. Score each dimension with a signal (green/yellow/red) and brief reasoning (1-2 sentences).
2. Provide an overall assessment with signal and reasoning.
3. Be honest about uncertainty — if you lack information for a dimension, mark it yellow and say why.

Respond with valid JSON in exactly this format:
{{
    "dimensions": [
        {{"dimension": "Leadership Scope", "signal": "green", "reasoning": "..."}},
        {{"dimension": "Domain Alignment", "signal": "yellow", "reasoning": "..."}},
        ...
    ],
    "overall_signal": "green",
    "overall_reasoning": "One paragraph summary of fit."
}}"""


def score_job(job: JobListing, research: CompanyResearch) -> JobAnalysis:
    """Score a single job listing against the candidate profile.

    Makes one Claude API call per job. Returns a fully populated
    JobAnalysis with per-dimension scores.
    """
    analysis = JobAnalysis(job=job, research=research)

    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set — cannot score jobs")
        analysis.overall_reasoning = "Scoring skipped: no API key configured."
        return analysis

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = _build_scoring_prompt(job, research)

    try:
        response = client.messages.create(
            model=SCORING_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        text = response.content[0].text.strip()

        # Parse JSON — handle markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]  # remove opening fence
            text = text.rsplit("```", 1)[0]  # remove closing fence
            text = text.strip()

        result = json.loads(text)

        # Build dimension scores
        for dim in result.get("dimensions", []):
            try:
                analysis.dimension_scores.append(
                    DimensionScore(
                        dimension=dim["dimension"],
                        signal=FitSignal(dim["signal"]),
                        reasoning=dim["reasoning"],
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.warning("Malformed dimension score: %s", exc)

        # Overall assessment
        try:
            analysis.overall_signal = FitSignal(result.get("overall_signal", "yellow"))
        except ValueError:
            analysis.overall_signal = FitSignal.YELLOW

        analysis.overall_reasoning = result.get("overall_reasoning", "")

        # Compute numeric score for ranking (weighted average of dimensions)
        if analysis.dimension_scores:
            total = sum(
                SIGNAL_WEIGHT[d.signal] for d in analysis.dimension_scores
            )
            analysis.overall_score = total / len(analysis.dimension_scores)

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse scorer response for %s: %s", job.title, exc)
        analysis.overall_reasoning = f"Scoring failed: could not parse LLM response ({exc})"
    except anthropic.APIError as exc:
        logger.error("API error scoring %s: %s", job.title, exc)
        analysis.overall_reasoning = f"Scoring failed: API error ({exc})"

    return analysis
