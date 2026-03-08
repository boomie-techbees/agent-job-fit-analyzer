"""Baked-in candidate profile used as the scoring benchmark."""

CANDIDATE_PROFILE = {
    "identity": (
        "Senior engineering leader with 20+ years experience. "
        "Operates as Fractional CTO/VPE through TechBees coaching practice. "
        "Open to fractional, interim, or full-time roles."
    ),
    "title_targets": [
        "CTO",
        "VPE",
        "VP Engineering",
        "VP of Engineering",
        "Head of Engineering",
        "Fractional CTO",
        "Director of Engineering",
    ],
    "strong_fit_signals": [
        "VP or C-level scope",
        "Security, DevSecOps, or compliance in the domain",
        "Civic tech, nonprofit, climate tech, or mission-driven org",
        "Scaling teams or building engineering orgs from early stage",
        "Remote or DC Metro Area",
        "AWS, GCP, or modern cloud infrastructure",
        "Cross-functional alignment with product and executives",
    ],
    "partial_fit_signals": [
        "Director-level but not VP scope",
        "Strong technical domain but no security component",
        "Hybrid or unclear location",
        "Early-stage startup with unclear funding",
    ],
    "poor_fit_signals": [
        "IC (individual contributor) roles",
        "Requires on-site outside DC Metro",
        "Purely frontend or mobile-only stack",
        "No leadership scope",
    ],
    "background_highlights": [
        "Led engineering orgs up to 18 direct reports + contractors",
        "Delivered national-scale systems (230M+ transactions, zero errors)",
        "Security leadership: SOC2, DevSecOps, policy authoring, security reviews",
        "Cost optimization track record ($100K-$275K+ annual savings)",
        "Career ladder and hiring process design",
        "Fractional CTO experience (Great Nonprofits engagement)",
        "MBA (Wharton) + MS Computer Science + BS Mechanical Engineering",
    ],
}

# Title patterns for fast pre-filtering (before LLM scoring).
# These are compiled into regex patterns with word boundaries to avoid
# substring false positives (e.g., "cto" matching "Director").
import re

_RAW_TITLE_PATTERNS = [
    r"\bcto\b",
    r"\bchief technology",
    r"\bchief technical",
    r"\bvp\b.{0,4}eng",           # "VP Engineering", "VP of Eng", "VP, Eng"
    r"\bvice president.{0,4}eng",
    r"\bhead of eng",
    r"\bdirector.{0,4}eng",       # "Director of Engineering", "Director, Eng"
    r"\bengineering director\b",
    r"\bfractional\b.{0,6}cto\b",
    r"\bfractional\b.{0,6}chief",
    r"\bvpe\b",
]

TITLE_PATTERNS_RE = [re.compile(p, re.IGNORECASE) for p in _RAW_TITLE_PATTERNS]

# Titles that are explicitly poor fits — used to reject even if they
# partially match a pattern above (e.g., "Director of Frontend Engineering").
TITLE_EXCLUSIONS = [
    "frontend director",
    "mobile director",
    "individual contributor",
    "staff engineer",
    "senior engineer",
    "principal engineer",
    "software engineer",
    "data engineer",
    "ml engineer",
    "machine learning engineer",
    "devops engineer",
    "sre",
    "site reliability",
]


SCORING_DIMENSIONS = [
    {
        "name": "Leadership Scope",
        "description": "Does this role carry VP/C-level scope with org-wide impact?",
    },
    {
        "name": "Domain Alignment",
        "description": (
            "Does the domain involve security, DevSecOps, compliance, "
            "or infrastructure? Does it match the candidate's strengths?"
        ),
    },
    {
        "name": "Mission Fit",
        "description": (
            "Is this a mission-driven org (civic tech, nonprofit, climate tech) "
            "or does the company mission resonate?"
        ),
    },
    {
        "name": "Team Building",
        "description": (
            "Does the role involve scaling teams, building engineering orgs, "
            "or org design from early stage?"
        ),
    },
    {
        "name": "Location",
        "description": "Is the role remote, DC Metro Area, or requires relocation?",
    },
    {
        "name": "Tech Stack",
        "description": (
            "Does the stack include AWS, GCP, modern cloud infra? "
            "Or is it purely frontend/mobile-only?"
        ),
    },
    {
        "name": "Cross-functional Scope",
        "description": (
            "Does the role involve alignment with product, executives, "
            "and business stakeholders?"
        ),
    },
]
