# RepoLens

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub API](https://img.shields.io/badge/GitHub-REST%20API-black?logo=github&logoColor=white)](https://docs.github.com/en/rest)

> Analyze GitHub repositories and generate health reports from the command line.

RepoLens fetches repository data from the GitHub API, analyzes key metrics across activity, community, and maintainability, then produces scored health reports in plain text or JSON format — with a local filesystem cache to avoid repeated API calls.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Caching](#caching)
- [Metrics \& Scoring](#metrics--scoring)
- [API Resilience \& Pagination](#api-resilience--pagination)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Features

- **Repository Analysis** — Fetch metadata, commits, contributors, languages, and issues via the GitHub REST API
- **Multi-dimensional Scoring** — Calculate health, activity, community, and maintainability scores (0–100)
- **Letter Grading** — Convert numeric scores to intuitive letter grades (A–F)
- **Report Export** — Save reports as formatted `.txt` or structured `.json` (both surface `approximate` / `truncated_endpoints` when pagination was capped)
- **Interactive CLI** — User-friendly terminal interface with menus, confirmation prompts, and `rich`/`RichFiglet` banner
- **Filesystem Cache** — Local `.repolens_cache/` with 24 h TTL, atomic writes, and versioned validation — reuses fresh results and skips the GitHub fetch when you confirm
- **Pagination with Truncation Awareness** — Follows `Link: rel="next"` headers up to `MAX_PAGES=10` (`PER_PAGE=100`, 1 000 items cap); warns when counts are approximate lower bounds
- **Resilient Rate-Limit Handling** — Retries secondary rate limits (403/429 with `Retry-After`) with exponential backoff (`Retry-After` capped at 100 s, 1 s floor), raises immediately on exhausted primary limits (`x-ratelimit-remaining: 0`) with reset-time hint
- **Empty-Repo Resilience** — Handles `409 Conflict` for `/commits` and `204 No Content` for `/contributors` on empty repositories
- **Optional Authentication** — Support for GitHub personal access tokens to increase rate limits (60 → 5 000 req/hour)

---

## Prerequisites

- Python 3.10 or higher (PEP 604 `X | Y` unions)
- `pip` package manager
- Git (for cloning the repository)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/AFG473319/RepoLens.git
cd RepoLens

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

No package installation is needed beyond `pip install -r requirements.txt` — all modules are flat at the repo root (`analyzer.py`, `github.py`, etc.).

---

## Configuration

Create a `.env` file in the project root to store your GitHub personal access token (see `.env.example`):

```env
GITHUB_API_KEY=ghp_your_token_here
```

> **Note:** Using an API key is optional but recommended. Without it, unauthenticated requests are limited to 60 requests/hour. With a token, you get 5,000 requests/hour. The key is loaded lazily inside `analyze_repository()` via `python-dotenv`; the app runs fine without a `.env` file.

### Cache location override

By default the cache lives in `.repolens_cache/` at the repo root (gitignored). Override it for tests or custom layouts:

```bash
# PowerShell
$env:REPOLENS_CACHE_DIR="D:\my-cache"
python main.py

# bash
REPOLENS_CACHE_DIR=/tmp/repolens-cache python main.py
```

The legacy directory `.repolens/` is also gitignored for backward compatibility.

---

## Usage

Run the application from the project root:

```bash
python main.py
# or with the committed venv on Windows
.venv\Scripts\python.exe main.py
```

### Interactive Session

1. Choose **Analyze a repository** from the menu
2. Enter the repository **owner** and **name** (e.g., `torvalds` and `linux`) — input is whitespace-stripped
3. **Cache check** — if a fresh, complete cache entry exists (≤ 24 h, `CACHE_VERSION` matches, all required keys present), you will be prompted:
   ```
   Found cached analysis for torvalds/linux from 3 hours ago.
   The cache is recent (within 24h) and contains a complete analysis.
   Use cached data? (y = use cache, n = fetch fresh) [y/n]:
   ```
   - `y` → skips all GitHub fetches and reuses `analysis` + `scores` from `.repolens_cache/{owner}_{repo}.json`
   - `n` → fetches fresh data and overwrites the cache atomically
4. If fetching, select a report format: `Text` or `JSON`
5. View the summary in the terminal — when pagination was capped a warning is printed:
   ```
   Warning: counts are approximate because one or more GitHub endpoints returned more than 1000 results.
   Truncated endpoints: commits, issues
   ```
6. The report file is saved to the current directory:
   - `{owner}_{repo}_report.txt`
   - `{owner}_{repo}_report.json`

### Example Output

```text
> 1
Enter the repository owner: torvalds
Enter the repository name: linux

Found cached analysis for torvalds/linux from 5 hours ago.
The cache is recent (within 24h) and contains a complete analysis.
Use cached data? (y = use cache, n = fetch fresh) [y/n]: n
1. Text
2. JSON
> 2

Fetching data from GitHub...
Fetching repository metadata for torvalds/linux...
Fetching commit history...
Fetching contributors...
Fetching language breakdown...
Fetching issues...

Summary
  Health score: 92.5
  Grade: A

Report saved to torvalds_linux_report.json
```

With a fresh cache hit (`y`):

```text
Using cached data for torvalds/linux (5 hours ago) — skipping GitHub fetch.

Summary
  Health score: 92.5
  Grade: A
```

Write failures (`PermissionError` / `IOError`) are reported without crashing; `requests.RequestException` / `TypeError` from the fetch/validation path is shown as `Error: ...`.

---

## Caching

RepoLens caches the full `analysis` + `scores` payload to avoid burning rate limit on repeated queries.

| Property | Detail |
|----------|--------|
| **Location** | `.repolens_cache/{owner}_{repo}.json` (sanitized via `[^A-Za-z0-9._-]` → `_`, 100-char cap) |
| **Version** | `CACHE_VERSION=1` — mismatched versions are treated as invalid |
| **TTL** | `CACHE_TTL_SECONDS=24*3600` (24 h) |
| **Freshness** | `is_cache_fresh()` compares `fetched_at` (ISO-8601, timezone-aware) to now; future timestamps count as fresh (clock skew) |
| **Validation** | `is_cache_valid()` checks `version`/`owner`/`repo`/`fetched_at` + presence of all required `analysis` keys (`repo`, `commits`, `contributors`, `languages`, `issues`, `approximate`, `truncated_endpoints`) and `scores` keys (`health_score`, `activity_score`, `community_score`, `maintainability_score`, `grade`) with type sanity |
| **Age display** | `cache_age_string()` → `"42s ago"`, `"3 minutes ago"`, `"5 hours ago"`, `"2 days ago"`, or `"on 2026-08-26 14:03 UTC"` |
| **Atomic save** | `save_cache()` writes to `*.tmp` then `replace()`; cleans up on `OSError` |
| **Load behavior** | `load_cache()` returns `None` on miss or corrupt/unreadable JSON |
| **Override** | `REPOLENS_CACHE_DIR` env var (see Configuration) |
| **Clear** | `clear_cache(owner, repo)` removes the file if present |

**Flow in `main.py:96-132`:**

1. `cache.load_cache(owner, repo)` → `is_cache_valid()` + `is_cache_fresh()` → `cache.cache_age_string()` → `menu.prompt_cache_use()` (y/n loop)
2. If cache accepted: `analysis, scores = cached_data["analysis"], cached_data["scores"]` and still prompt for `report_format`
3. If fetching: `analyze_repository()` → probe with `is_cache_valid()` → `cache.save_cache()` (warn on `OSError` but continue)

---

## Metrics & Scoring

RepoLens evaluates repositories across three dimensions, weighted equally:

| Dimension | Weight | Factors |
|-----------|--------|---------|
| **Activity** | 1/3 | Total commits (log10 scale) + 10 pt bonus if latest commit is within the last 90 days (`scoring.py:RECENCY_BONUS_DAYS`) |
| **Community** | 1/3 | Contributor count (`min(50, contributors*2.5)`) + issue closure rate (`closed/total * 50`) |
| **Maintainability** | 1/3 | Stars (`log10`), forks (`log10`), description presence, language detection |

### Score Calculation

- **Activity Score** — `min(100, log10(commits+1)*20)` plus `RECENCY_BONUS_POINTS=10` when `_committed_within_days()` is true
- **Community Score** — `min(50, contributors*2.5) + (closed/total*50)` capped at 100
- **Maintainability Score** — `min(40, log10(stars+1)*10) + min(30, log10(forks+1)*10) + 15 (description) + 15 (language)` capped at 100
- **Health Score** — Average of the three dimension scores (`scoring.py:96-113`)

### Grade Scale

| Grade | Range |
|-------|-------|
| A | 90–100 |
| B | 80–89 |
| C | 70–79 |
| D | 60–69 |
| F | 0–59 |

> **Approximate counts:** When `approximate` is true (`github.py:MAX_PAGES` hit), commit/contributor/issue totals are lower bounds — scores are still computed from the truncated data.

---

## API Resilience & Pagination

Implemented in `github.py`:

- **`_fetch()`** — Retries up to 3 times: connection errors/timeouts, `5xx`, and secondary rate limits (429 or 403 with `Retry-After` / `x-ratelimit-remaining: 0` check). Sleeps `Retry-After * 2^attempt` (exponential backoff) with `_retry_after_seconds()` capping at 100 s and flooring at 1 s; defaults to 60 s when header is missing/unparseable. Primary-limit exhaustion (`x-ratelimit-remaining: 0`) raises immediately with a reset-time hint (`_reset_time()` from `x-ratelimit-reset`) and a tailored message depending on whether `api_key` is set. Validates expected JSON type via `_validate_type()` and treats `204 No Content` as valid (empty contributors).
- **`_paginate()`** — Requests `PER_PAGE=100`, follows `Link` header `rel="next"` up to `MAX_PAGES=10`; returns `(items, truncated)` and prints a `Warning: ... has more than 1000 results; counts may be approximate.` to stderr when truncated.
- **`get_commits()`** — Wraps `_paginate()` and swallows `409 Conflict` for empty repos (returns `([], False)`).
- **`get_contributors()` / `get_issues()`** — Paginated; `get_languages()` / `get_repo()` are single-payload.
- **`analyzer.analyze_issues()`** — Filters out pull requests (`"pull_request" not in issue`) since `/issues?state=all` returns both.

Reports (`report.py`) always include `approximate` (bool) and `truncated_endpoints` (list) — in text as a `Note: ... lower bounds.` block and in JSON as top-level keys — and `print_summary()` echoes the warning.

---

## Project Structure

```
RepoLens/
├── main.py            # analyze_repository() orchestration (dotenv + github → analyzer → scoring, approximate/truncated_endpoints) + main() loop (banner/menu, cache.load_cache → prompt_cache_use → fetch or reuse, print_summary, generate_*_report + save_report with PermissionError/IOError handling)
├── menu.py            # All terminal I/O (only rich imports): print_banner (RichFiglet "AFG473319", larry3d), show_menu/get_user_choice, prompt_repo_input/prompt_report_format, confirm_exit, prompt_cache_use (fresh-cache y/n prompt)
├── github.py          # REST client: _fetch (retry/rate-limit, Retry-After capped at 100s, exponential backoff), _paginate (Link-header, returns (items, truncated), MAX_PAGES=10/PER_PAGE=100), get_repo/get_commits/get_contributors/get_languages/get_issues; 409/204 handling
├── analyzer.py        # Pure payload transforms: analyze_repo/analyze_commits/analyze_contributors/analyze_languages/analyze_issues (filters pull_request keys)
├── scoring.py         # 3 dimensions averaged equally (1/3 each): calculate_activity_score (log10 commits + 10pt if latest commit within 90 days) / calculate_community_score / calculate_maintainability_score; calculate_health_score, grade_score (90/80/70/60 → A/B/C/D/F)
├── report.py          # generate_text_report/generate_json_report (both surface approximate/truncated_endpoints), save_report, print_summary (warns when approximate)
├── cache.py           # Filesystem cache in .repolens_cache/ (CACHE_VERSION=1, TTL 24h): _sanitize/_cache_path, is_cache_valid (version/owner/repo/fetched_at + required keys), is_cache_fresh/cache_age_string, load_cache/save_cache (atomic *.tmp replace)/clear_cache; CACHE_DIR respects REPOLENS_CACHE_DIR
├── tests/             # Unit tests (unittest, mocked)
│   ├── test_analyzer.py
│   ├── test_github.py
│   ├── test_main.py
│   ├── test_menu.py
│   ├── test_report.py
│   └── test_scoring.py
├── .repolens_cache/   # Active cache dir (gitignored) — {owner}_{repo}.json with fetched_at ISO timestamps
├── .env               # Optional: GITHUB_API_KEY (gitignored, loaded lazily in analyze_repository())
├── .env.example       # Template for .env
├── requirements.txt   # Python dependencies
├── LICENSE            # MIT
├── .gitignore
└── README.md
```

Generated reports (`{owner}_{repo}_report.{txt,json,md,html,csv}`) and scratch files (`improvements.md`, `implementation_plan.md`, `_write_features.py`, `feature_ideas.md`, `AGENTS.md`, `.zcode/`) are gitignored.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP requests to the GitHub API |
| `python-dotenv` | Load the `GITHUB_API_KEY` from `.env` |
| `rich` | Terminal output formatting |
| `rich-pyfiglet` | Banner rendering in the CLI |

---

## Testing

Run the test suite using Python's built-in `unittest` (no pytest config):

```bash
# Full suite
python -m unittest discover -s tests -p "test_*.py" -v

# Single module / single test
python -m unittest tests.test_github
python -m unittest tests.test_github.TestGetRepo.test_get_repo_returns_json
```

Tests import flat modules directly (`import github`, `import main`, `import analyzer`) and patch full dotted paths (`"github.requests.get"`, `"github.time.sleep"`, `"main.github"`, `"main.analyzer"`, `"main.menu"`). The suite is fully mocked (`unittest.mock`) — no network access needed — and covers every public function with edge-case assertions (null API fields, empty repos, pagination truncation, rate-limit exhaustion, cache validation/freshness, etc.).

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository and create a new branch for your feature or fix
2. Make your changes and ensure all tests pass
3. Open a pull request describing:
   - What problem the change solves
   - How it was implemented
   - Any additional testing performed

Please adhere to the existing code style and keep functions focused and documented.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [GitHub REST API](https://docs.github.com/en/rest) for providing repository data
- [Rich](https://github.com/Textualize/rich) for beautiful terminal formatting
- [rich-pyfiglet](https://github.com/empicano/ascii-art) for the CLI banner
