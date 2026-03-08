"""Configuration for the Job Fit Analyzer agent."""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SCORING_MODEL = "claude-sonnet-4-5-20250929"  # Fast + capable enough for scoring

# Scraping
REQUEST_TIMEOUT = 30  # seconds
SCRAPE_DELAY = 1.5  # seconds between requests to be polite
USER_AGENT = (
    "JobFitAnalyzer/1.0 (career research tool; "
    "respects robots.txt; contact: github.com/agent-job-fit)"
)

# Search
MAX_SEARCH_RESULTS = 5  # DuckDuckGo results per company

# Scoring
MAX_CONCURRENT_SCORES = 3  # Parallel scoring calls to limit API rate

# Web UI
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
