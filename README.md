# RepoLens

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub API](https://img.shields.io/badge/GitHub-REST%20API-black?logo=github&logoColor=white)](https://docs.github.com/en/rest)
[![GitLab API](https://img.shields.io/badge/GitLab-REST%20API-fc6d26?logo=gitlab&logoColor=white)](https://docs.gitlab.com/ee/api/)

> Analyze any GitHub or GitLab repository and get a health report from the command line.

RepoLens fetches repository data from the GitHub or GitLab REST API — metadata, commits, contributors, languages, and issues — scores it across three dimensions, and saves the report as **Text**, **JSON**, or an **interactive HTML page**. Fresh results are cached locally so repeat analyses don't burn your rate limit.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Metrics & Scoring](#metrics--scoring)
- [Caching](#caching)
- [Reliability](#reliability)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Features

- **Repository analysis** — pulls metadata, commit history, contributors, language breakdown, and issues in a single run
- **GitHub and GitLab** — one workflow for both platforms; GitLab projects are addressed by namespace and path (nested groups supported), with per-platform normalization of commits, contributors, and issue states
- **Three-dimension scoring** — Activity, Community, and Maintainability (0–100 each), averaged into a health score with an A–F letter grade
- **Three report formats** — `.txt` for quick reading, `.json` for tooling, and a single self-contained `.html` with score bars, expandable grade rulers, metric filtering, a theme toggle, and keyboard shortcuts (no external requests — renders offline and prints cleanly)
- **Interactive CLI** — menus, confirmations, and a figlet banner
- **Settings menu** — set your API keys, cache directory, and default report format without editing files (persisted to `settings.json`)
- **Filesystem cache** — 24 h TTL, keyed per platform and repository, atomic writes, strict validation; reuse is always opt-in via a prompt
- **Truncation awareness** — follows pagination up to 1,000 items per endpoint on either platform and flags counts as lower bounds when capped
- **Rate-limit resilience** — retries transient failures with exponential backoff; exhausted limits fail fast with a reset-time hint
- **Actionable permission errors** — private or invisible GitLab projects fail with a hint about the missing `GITLAB_API_KEY` instead of a bare 403/404
- **Empty-repo handling** — no-commit (`409`) and empty-list (`204`) responses are handled gracefully on both platforms
- **Optional authentication** — bring a personal access token to raise the per-hour request limit

---

## Prerequisites

- Python **3.10 or higher** (uses PEP 604 `X | Y` type unions)
- `pip`
- Git (to clone the repository)

---

## Installation

```bash
git clone https://github.com/AFG473319/RepoLens.git
cd RepoLens

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

All modules live flat at the repo root — no package installation needed beyond the four dependencies in `requirements.txt`.

---

## Configuration

RepoLens works out of the box: without a token you get the unauthenticated limit (GitHub: 60 requests/hour per IP; GitLab: per-IP throttling). Add a personal access token to raise it (GitHub: 5,000/hour; GitLab: depends on your plan). GitLab tokens need the **`read_api`** scope.

**Option 1 — Settings menu (recommended).** Run the app and pick **Settings**. Enter your GitHub or GitLab API key (an existing one is shown masked; press Enter to keep it) and optionally a cache directory, plus a default report format. Choices persist to `settings.json` (gitignored, created on first save).

**Option 2 — `.env` file.** Copy `.env.example` to `.env`:

```env
GITHUB_API_KEY=ghp_your_token_here
GITLAB_API_KEY=glpat-your_token_here
```

`.env` is gitignored — never commit it. The key is read lazily at fetch time; the app runs fine without the file. A key saved through the Settings menu takes precedence over `.env`.

### Cache location

The cache defaults to `.repolens_cache/` at the project root. Override it via the Settings menu or the `REPOLENS_CACHE_DIR` environment variable:

```bash
# PowerShell
$env:REPOLENS_CACHE_DIR="D:\my-cache"; python main.py

# bash
REPOLENS_CACHE_DIR=/tmp/repolens-cache python main.py
```

---

## Usage

```bash
python main.py
```

### Interactive session

1. Choose **Analyze a GitHub repository** or **Analyze a GitLab repository**
2. Enter the **owner** and **name** — for GitHub e.g. `torvalds` and `linux`; for GitLab the full namespace path, e.g. `gitlab-org` and `gitlab` or `group/subgroup` and `project` — input is whitespace-stripped
3. If a fresh, complete cache entry exists (≤ 24 h old) you're asked whether to reuse it — `y` skips all API fetches, `n` refetches and refreshes the cache
4. Pick a report format: type `text`, `json`, or `html`. Pressing Enter uses your saved default from Settings (`html` until changed). Asked on both the fresh-fetch and cache-hit paths
5. Watch the per-endpoint fetch progress, then read the terminal summary
6. The report is saved to the current directory as `{platform}_{owner}_{repo}_report.{txt|json|html}` — e.g. `github_torvalds_linux_report.html` or `gitlab_group_subgroup_project_report.html` — so reports from different platforms can never overwrite each other

### Example session

```text
> 1
Enter the repository owner: torvalds
Enter the repository name: linux

Found cached analysis for torvalds/linux from 5 hours ago.
The cache is recent (within 24h) and contains a complete analysis.
Use cached data? (y = use cache, n = fetch fresh) [y/n]: n
Report format (text, json, html) [html]: html

Fetching data from GitHub...
Fetching repository metadata for torvalds/linux...
Fetching commit history...
Fetching contributors...
Fetching language breakdown...
Fetching issues...

Summary
  Health score: 92.5
  Grade: A

Report saved to github_torvalds_linux_report.html
```

A cache hit (`y`) skips the fetch but still asks for the format:

```text
Using cached data for torvalds/linux (5 hours ago) — skipping GitHub fetch.
Report format (text, json, html) [html]:

Summary
  Health score: 92.5
  Grade: A
```

When pagination was capped, the summary prints a warning naming the platform before the save:

```text
Warning: counts are approximate because one or more GitHub endpoints returned more than 1000 results.
Truncated endpoints: commits, issues
```

### Choosing a format

| Format | File | Best for |
|--------|------|----------|
| Text | `{platform}_{owner}_{repo}_report.txt` | Reading in the terminal |
| JSON | `{platform}_{owner}_{repo}_report.json` | Piping into scripts and dashboards |
| HTML | `{platform}_{owner}_{repo}_report.html` | Browsing and sharing — one self-contained interactive page |

Save failures (e.g. the file is locked by another program) are reported without crashing the app.

---

## Metrics & Scoring

RepoLens evaluates repositories across three dimensions, weighted equally:

| Dimension | Weight | Factors |
|-----------|--------|---------|
| **Activity** | 1/3 | Total commits (log-scaled) + a bonus that decays linearly over the 90 days since the latest commit |
| **Community** | 1/3 | Contributor count + issue closure rate |
| **Maintainability** | 1/3 | Stars and forks (both log-scaled) + presence of a description and a detected language |

### Formulas

- **Activity** = `min(100, log10(commits + 1) × 20)` + up to `10 × (1 − days_since_last_commit / 90)`
- **Community** = `min(50, contributors × 2.5)` + `(closed / total) × 50`
- **Maintainability** = `min(40, log10(stars + 1) × 10)` + `min(30, log10(forks + 1) × 10)` + 15 (description) + 15 (language)
- **Health** = mean of the three dimensions (each capped at 100)

### Grade scale

| Grade | Range |
|-------|-------|
| A | 90–100 |
| B | 80–89 |
| C | 70–79 |
| D | 60–69 |
| F | 0–59 |

> **Approximate counts:** when an endpoint returns more than 1,000 results, its totals are lower bounds — scores are still computed from the truncated data, and every report says so.

---

## Caching

- **Location** — `.repolens_cache/{platform}_{owner}_{repo}_repolens_cache.json` (keyed per platform, so a GitHub and a GitLab project with the same name cache separately)
- **TTL** — 24 hours; stale, incomplete, or corrupt entries are ignored and refetched
- **Reuse** — always opt-in via the prompt; refusing refetches and refreshes the entry
- **Clearing** — the main menu's **Clear cache** removes only RepoLens-created files; unrelated `*.json` in a custom cache directory are never touched
- **Moving** — via the Settings menu or `REPOLENS_CACHE_DIR`

---

## Reliability

- **Retries** — connection errors, timeouts, `5xx` responses, and rate limits (`429`, or `403` carrying rate-limit headers on GitHub) are retried up to 3 times with exponential backoff; `Retry-After` is honored (capped at 100 s, floored at 1 s)
- **Primary limit exhausted** (GitHub) — fails immediately with the reset time instead of retrying a doomed request
- **Permission errors** (GitLab) — `403`/`404` responses fail fast with a hint about project visibility and the `GITLAB_API_KEY` token scope, instead of a bare HTTP error
- **Pagination** — 100 items per page, up to 10 pages per endpoint; beyond that, counts are approximate and every report is labeled as such
- **Empty repositories** — no-commit (`409`) and no-content (`204`) responses are handled without crashing on both platforms
- **Language fetch failures** (GitLab) — reported as a warning instead of silently lowering the Maintainability score, and the report itself notes that language metrics are missing

---

## Project Structure

```
RepoLens/
├── main.py               # CLI entry point: analysis orchestration + menu loop (settings, cache, report dispatch)
├── menu.py               # Terminal I/O: banner, menus, settings/cache/report prompts, confirmations
├── provider.py           # Platform-aware REST client (GitHub + GitLab): retries, rate limits, pagination, normalization
├── analyzer.py           # Pure payload transforms (API JSON → analysis dicts; filters PRs from issues)
├── scoring.py            # Activity / Community / Maintainability scores, health average, letter grades
├── report.py             # Text / JSON / HTML report generators + save + summary printing
├── cache.py              # Filesystem cache (24 h TTL, versioned, atomic writes, per-platform keys)
├── settings.py           # settings.json load/save/apply (API keys, cache directory, default report format)
├── tests/                # unittest suite (fully mocked — no network needed)
├── .env.example          # Template for the optional GitHub / GitLab tokens
├── requirements.txt
├── LICENSE               # MIT
└── README.md
```

Runtime-created and gitignored: `.repolens_cache/`, `settings.json`, `cache_directories.json`, and generated `*_report.*` files.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP requests to the GitHub and GitLab APIs |
| `python-dotenv` | Load `GITHUB_API_KEY` / `GITLAB_API_KEY` from `.env` |
| `rich` | Terminal output formatting |
| `rich-pyfiglet` | Banner rendering in the CLI |

---

## Testing

Run the suite with Python's built-in `unittest` (no pytest config):

```bash
# Full suite
python -m unittest discover -s tests -p "test_*.py" -v

# Single module
python -m unittest tests.test_scoring

# Single test class / case
python -m unittest tests.test_report.TestGenerateHtmlReport
```

The suite is fully mocked — no network access and no rate-limit consumption.

---

## Contributing

Contributions are welcome!

1. Fork the repository and create a new branch for your feature or fix
2. Make your changes and ensure all tests pass
3. Open a pull request describing:
   - What problem the change solves
   - How it was implemented
   - Any additional testing performed

Please adhere to the existing code style and keep functions focused and documented.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [GitHub REST API](https://docs.github.com/en/rest) for providing repository data
- [GitLab REST API](https://docs.gitlab.com/ee/api/) for providing repository data
- [Rich](https://github.com/Textualize/rich) for beautiful terminal formatting
- [rich-pyfiglet](https://pypi.org/project/rich-pyfiglet/) for the CLI banner
