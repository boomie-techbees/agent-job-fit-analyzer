# Job Fit Analyzer Agent

> Autonomous job fit analysis · Human-in-the-loop review

A real AI agent — not a chatbot, not a script — that autonomously scans job boards, researches companies, and scores roles against a candidate profile. Built as part of a hands-on AI portfolio by [Boomie Odumade](https://linkedin.com/in/odumade) / [TechBees](https://techbees.me).

---

## What It Does

1. **Scrapes** job listings from [We Work Remotely](https://weworkremotely.com) and [RemoteOK](https://remoteok.com) — both permit scraping per their terms
2. **Filters** for roles matching your candidate profile — the example targets senior engineering leadership (CTO, VPE, VP Engineering, Head of Engineering, Director of Engineering), but this is fully configurable
3. **Researches** each company autonomously using web search
4. **Scores** each role against your candidate profile using Claude AI — green/yellow/red on key dimensions with written reasoning
5. **Outputs** a web UI with ranked, color-coded results and a saved Markdown report

You don't paste anything. You don't prompt it. It goes and gets the information, reasons about it, and surfaces results for your review.

---

## Why Human-in-the-Loop

The agent surfaces results — it does **not** apply to jobs automatically. That's an intentional design decision. Autonomous job applications without human review raise real ethical and practical concerns. The agent's job is to do the research and judgment work; yours is to decide what to do with it.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Orchestrator                       │
│            (think → act → observe loop)              │
│                                                      │
│  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │
│  │ Scrapers │→ │  Filter   │→ │   Researcher     │  │
│  │ (WWR,    │  │ (title +  │  │ (web search per  │  │
│  │ RemoteOK)│  │  keyword) │  │  company)        │  │
│  └──────────┘  └───────────┘  └────────┬─────────┘  │
│                                        ↓             │
│                               ┌──────────────────┐   │
│                               │   Scorer         │   │
│                               │ (LLM-powered     │   │
│                               │  fit analysis)   │   │
│                               └────────┬─────────┘   │
│                                        ↓             │
│                               ┌──────────────────┐   │
│                               │  Ranker/Output   │   │
│                               └──────────────────┘   │
└─────────────────────────────────────────────────────┘
         ↓                              ↓
   ┌───────────┐                ┌──────────────┐
   │ Flask UI  │                │ File Report  │
   │ (ranked   │                │ (Markdown)   │
   │  results) │                └──────────────┘
   └───────────┘
```

### What Makes This a Real Agent

| Characteristic | This project |
|---|---|
| Initiates action | ✅ Scrapes job boards autonomously |
| Uses tools | ✅ Web scraper + web search + LLM scoring |
| Adapts mid-task | ✅ Researches more context when listing is ambiguous |
| Auditable reasoning | ✅ Per-dimension scores with written rationale |

### Tech Stack

| Package | Purpose |
|---|---|
| `httpx` | Async HTTP client for scraping |
| `beautifulsoup4` | HTML parsing (We Work Remotely) |
| `duckduckgo-search` | Free web search for company research |
| `anthropic` | Claude API for LLM-powered fit scoring |
| `pydantic` | Type-safe data models |
| `flask` | Web UI |
| `rich` | CLI progress output during agent run |
| `pyyaml` | Loads candidate profile from YAML at runtime |

---

## Project Structure

```
agent-job-fit/
├── agent/
│   ├── orchestrator.py           # Agent loop: think → act → observe
│   ├── scrapers.py               # WWR + RemoteOK scrapers
│   ├── researcher.py             # Company research via DuckDuckGo
│   ├── scorer.py                 # LLM-powered fit scoring
│   ├── models.py                 # Pydantic data models
│   └── profile.py                # Loads candidate profile from YAML
├── web/
│   ├── app.py                    # Flask app
│   └── templates/                # HTML templates
├── reports/                      # Generated reports (auto-created)
├── candidate_profile.example.yaml  # Template — copy and fill in your details
├── candidate_profile.yaml        # Your profile — gitignored, never committed
├── config.py                     # Settings (reads from environment)
├── run_agent.py                  # CLI: run the agent
└── run_web.py                    # CLI: start the web UI
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com)

### Setup

```bash
# Clone the repo
git clone https://github.com/boomie-techbees/job-fit-analyzer
cd job-fit-analyzer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY=your-key-here
```

### Set up your profile

The agent scores jobs against a candidate profile that you define. Your profile is **never committed** — it lives only on your machine.

```bash
# Copy the example profile
cp candidate_profile.example.yaml candidate_profile.yaml

# Open it and fill in your own details
# (the example file has comments explaining every section)
```

The profile covers:
- **Target titles** — the roles you are looking for
- **Fit signals** — green (strong fit), yellow (partial fit), red (poor fit)
- **Background highlights** — key achievements used in scoring context
- **Title patterns** — regex pre-filter that runs before the LLM
- **Scoring dimensions** — the criteria the LLM grades each role on

`candidate_profile.yaml` is in `.gitignore` so your personal details stay local even when you push or fork the repo.

### Run

```bash
# Run the agent (scrape → filter → research → score → rank)
python run_agent.py

# Then start the web UI to view results
python run_web.py
# → Open http://127.0.0.1:5000
```

### What to Expect

- **~24 seconds** for a full run across 276 listings
- Senior leadership roles (as in the example profile) are genuinely rare on these boards — a run typically surfaces 0–3 matches. That's correct behavior, not a bug. Runs targeting broader role types will see more matches.
- Each matched role gets researched and scored via Claude API (~1 API call per role), so costs are minimal
- Results are saved to `reports/` as both JSON and Markdown

---

## Sample Output

```
Phase 1: Scraping job boards
  Scraped 276 total listings (RemoteOK: 97, We Work Remotely: 179)

Phase 2: Filtering for leadership roles
  Filtered to 1 potential leadership roles

Phase 3: Researching 1 companies

Phase 4: Scoring 1 roles against profile

Results: 1 roles analyzed
┌──────┬───────┬────────┬───────┬────────────┬───────┐
│ Rank │ Score │ Signal │ Title │ Company    │ G/Y/R │
├──────┼───────┼────────┼───────┼────────────┼───────┤
│ 1    │    79 │ yellow │ CTO   │ Karmah Ltd │ 4/3/0 │
└──────┴───────┴────────┴───────┴────────────┴───────┘

Completed in 24s.
```

---

## Customizing the Candidate Profile

The scoring profile lives in `candidate_profile.yaml` (gitignored, never committed). See [candidate_profile.example.yaml](./candidate_profile.example.yaml) for the full commented template. Sections include:

- **Target titles** and pre-filter regex patterns
- **Fit signals** — green / yellow / red
- **Background highlights** used in the LLM scoring prompt
- **Scoring dimensions** — add, remove, or reword to match what matters to you

Profile customization via the web UI is a planned v2 feature.

---

## Portfolio Context

This project was built in a single evening session using **Claude Code** as part of a hands-on AI portfolio. It is part of a series of projects comparing AI coding tools (Bolt.new, Lovable, Replit Agent, Cursor, Claude Code) for building real applications.

The goal: demonstrate not just that AI tools can be used, but that they can be evaluated strategically — matching tool to use case, documenting tradeoffs, and building in public.

**Agent vs. ChatGPT/CustomGPT:** A CustomGPT requires you to paste a job description and ask a question. This agent goes and gets the data itself, researches the company, and reasons about fit — unprompted. That's the line.

---

## What's Next

- [x] User-configurable profile via YAML
- [ ] Additional job boards (currently hardcoded to WWR + RemoteOK)
- [ ] Scheduled runs with digest output
- [ ] AWS deployment

---

*Built by [Boomie Odumade](https://linkedin.com/in/odumade) · [TechBees](https://techbees.me) · March 2026*
