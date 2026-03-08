"""Flask web UI for viewing job fit analysis results."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, render_template

from config import FLASK_HOST, FLASK_PORT, REPORTS_DIR

app = Flask(__name__)

# Results are stored as JSON by the agent after each run
RESULTS_FILE = REPORTS_DIR / "latest_results.json"


def _load_results() -> dict:
    """Load the latest analysis results from file."""
    if not RESULTS_FILE.exists():
        return {"analyses": [], "meta": {}}

    with open(RESULTS_FILE) as f:
        return json.load(f)


@app.route("/")
def index():
    """Main results page showing ranked job analyses."""
    data = _load_results()
    analyses = data.get("analyses", [])
    meta = data.get("meta", {})

    # Sort by overall_score descending
    analyses.sort(key=lambda a: a.get("overall_score", 0), reverse=True)

    return render_template(
        "results.html",
        analyses=analyses,
        meta=meta,
        total=len(analyses),
    )


def start():
    """Start the web server."""
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
