# CharityLens

AI-Powered NGO Trust & Transparency Platform for Indian Non-Profits (live, light, SerpAPI-only).

## Overview

Type an NGO name → CharityLens searches the live web (Google organic + Google News) via SerpAPI, and produces a credibility score with an explanation. No offline datasets, no fragile HTML scraping, no heavy dependencies — FastAPI + httpx + a few hundred lines.

## Quick Start

```bash
uv sync                              # creates .venv + uv.lock
export SERPAPI_KEY="<your key from serpapi.com>"
```

**CLI demo:**

```bash
uv run charitylens lookup "Pratham"                 # no state filter
uv run charitylens lookup "Goonj" --state Delhi    # with state
```

**MCP server + web UI:**

```bash
uv run uvicorn mcp_server.main:app --reload
# open http://localhost:8000/ for the web UI
curl -s localhost:8000/tools                          # list the 3 tools
curl -s -X POST localhost:8000/tools/analyze_ngo_credibility \
  -H 'content-type: application/json' -d '{"ngo_name":"Pratham"}'
```

The web UI (`frontend/`) is a static single page (HTML + CSS + JS, no build step) served by FastAPI from the root. It runs `analyze_ngo_credibility` from the browser and shows the score, verdict, signals, explanation, and the raw web/news results.

## uv Commands

| Command | What it does |
|---|---|
| `uv sync` | Create `.venv` + `uv.lock`, install project + dev deps |
| `uv run charitylens lookup "Pratham"` | Run the CLI demo |
| `uv run python -m charitylens lookup "Pratham"` | Same as above (module form) |
| `uv run uvicorn mcp_server.main:app --reload` | Start the MCP server |
| `uv run pytest` | Run the test suite (offline, SerpAPI mocked) |
| `uv run python -c "..."` | Run any Python snippet in the env |
| `uv add <package>` | Add a dependency and update `uv.lock` |
| `uv remove <package>` | Remove a dependency |
| `uv lock` | Regenerate `uv.lock` without installing |
| `uv sync --upgrade` | Update deps to latest matching versions |
| `uv sync --reinstall` | Force reinstall of all packages |

Add dev-only dependencies with `uv add --dev <package>` → they land in `[dependency-groups].dev`.

## Architecture

```
CLI / HTTP  →  FastAPI MCP server  →  tools.py (3 tools)
                                        └─ serpapi_search.py  →  SerpAPI (Google Search + Google News)
```

`routes.py` dispatches by tool name via `inspect.signature`; each tool is an async function returning a dict and never raising — failures are folded into an `error` key.

## Tools

| Tool | Engine | Returns |
|---|---|---|
| `search_ngo_web_info(ngo_name, state, max_results)` | `google` organic | title/link/snippet results |
| `search_adverse_media(ngo_name, state, max_results)` | `tbm=nws` news | articles + keyword sentiment |
| `analyze_ngo_credibility(ngo_name, state, max_results)` | web + news | score 0-100, verdict, signals, explanation |

## Scoring

Base 50; +20 official website detected; +10 any web presence; -30 negative media; +10 neutral coverage; clamped 0-100. Verdict: `trustworthy` (≥70), `caution` (40-69), `investigate` (<40).

## Notes

- Free SerpAPI tier: 250 searches/month, 50/hour (~2 searches per lookup).
- Report is live web-reputation based; it does not check FCRA/registration status.
- Run tests offline: `uv run pytest`. No key needed (SerpAPI calls are mocked).