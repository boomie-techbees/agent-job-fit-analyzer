"""Loads the candidate profile from candidate_profile.yaml at the project root."""

import re
import sys
from pathlib import Path

import yaml

_PROFILE_PATH = Path(__file__).parent.parent / "candidate_profile.yaml"
_EXAMPLE_PATH = Path(__file__).parent.parent / "candidate_profile.example.yaml"

if not _PROFILE_PATH.exists():
    sys.exit(
        f"\nError: {_PROFILE_PATH.name} not found.\n"
        f"Copy {_EXAMPLE_PATH.name}, fill in your details, "
        f"and rename it to {_PROFILE_PATH.name}:\n\n"
        f"  cp candidate_profile.example.yaml candidate_profile.yaml\n"
    )

with _PROFILE_PATH.open() as _f:
    _data = yaml.safe_load(_f)

CANDIDATE_PROFILE = {
    "identity": _data["identity"],
    "title_targets": _data["title_targets"],
    "strong_fit_signals": _data["strong_fit_signals"],
    "partial_fit_signals": _data["partial_fit_signals"],
    "poor_fit_signals": _data["poor_fit_signals"],
    "background_highlights": _data["background_highlights"],
}

# Title patterns for fast pre-filtering (before LLM scoring).
# Compiled with word boundaries to avoid substring false positives.
TITLE_PATTERNS_RE = [
    re.compile(p, re.IGNORECASE) for p in _data["title_patterns"]
]

TITLE_EXCLUSIONS: list[str] = _data["title_exclusions"]

SCORING_DIMENSIONS: list[dict] = _data["scoring_dimensions"]
