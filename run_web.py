#!/usr/bin/env python3
"""Start the Job Fit Analyzer web UI.

Usage:
    python run_web.py

Then open http://127.0.0.1:5000 in your browser.
Run the agent first (python run_agent.py) to populate results.
"""

from web.app import start

if __name__ == "__main__":
    start()
