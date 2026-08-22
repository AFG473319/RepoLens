# RepoLens

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub API](https://img.shields.io/badge/GitHub-REST%20API-black?logo=github&logoColor=white)](https://docs.github.com/en/rest)

> Analyze GitHub repositories and generate health reports from the command line.

RepoLens fetches repository data from the GitHub API, analyzes key metrics across activity, community, and maintainability, then produces scored health reports in plain text or JSON format.

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Metrics \& Scoring](#metrics--scoring)
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
- **Report Export** — Save reports as formatted `.txt` or structured `.json`
- **Interactive CLI** — User-friendly terminal interface with confirmation prompts
- **Rate Limit Handling** — Built-in retry logic for API rate limits and server errors
- **Optional Authentication** — Support for GitHub personal access tokens to increase rate limits

---

## Prerequisites

- Python 3.10 or higher
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

---

## Configuration

Create a `.env` file in the project root to store your GitHub personal access token:

```env
GITHUB_API_KEY=ghp_your_token_here
```

> **Note:** Using an API key is optional but recommended. Without it, unauthenticated requests are limited to 60 requests/hour. With a token, you get 5,000 requests/hour.

---

## Usage

Run the application from the project root:

```bash
python main.py
```

### Interactive Session

1. Choose **Analyze a repository** from the menu
2. Enter the repository **owner** and **name** (e.g., `torvalds` and `linux`)
3. Select a report format: `text` or `json`
4. View the summary in the terminal
5. The report file is saved to the current directory:
   - `{owner}_{repo}_report.txt`
   - `{owner}_{repo}_report.json`

### Example Output

```text
> 1
Enter the repository owner: torvalds
Enter the repository name: linux
1. Text
2. JSON
> 2

Fetching data from GitHub...

Summary
  Health score: 92.5
  Grade: A

Report saved to torvalds_linux_report.json
```

---

## Metrics & Scoring

RepoLens evaluates repositories across three dimensions, weighted equally:

| Dimension | Weight | Factors |
|-----------|--------|---------|
| **Activity** | 1/3 | Total commits, whether the latest commit is within the last 90 days |
| **Community** | 1/3 | Contributor count, issue closure rate |
| **Maintainability** | 1/3 | Stars, forks, description presence, language detection |

### Score Calculation

- **Activity Score** — Based on commit count (logarithmic scale) with a bonus if the latest commit is within the last 90 days
- **Community Score** — Combines contributor count and ratio of closed to total issues
- **Maintainability Score** — Derived from stars, forks, and repository metadata completeness
- **Health Score** — Average of the three dimension scores

### Grade Scale

| Grade | Range |
|-------|-------|
| A | 90–100 |
| B | 80–89 |
| C | 70–79 |
| D | 60–69 |
| F | 0–59 |

---

## Project Structure

```
RepoLens/
├── main.py            # Entry point and CLI loop
├── menu.py            # User input, menu display, and exit confirmation
├── github.py          # GitHub API integration and retry logic
├── analyzer.py        # Data analysis functions for each data source
├── scoring.py         # Score calculation and letter grading
├── report.py          # Text/JSON report generation and file saving
├── tests/             # Unit tests for all modules
│   ├── test_analyzer.py
│   ├── test_github.py
│   ├── test_main.py
│   ├── test_menu.py
│   ├── test_report.py
│   └── test_scoring.py
├── .env               # Optional: GitHub API key (gitignored)
├── .env.example       # Template for .env
├── requirements.txt   # Python dependencies
├── LICENSE
├── .gitignore
└── README.md
```

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

Run the test suite using Python's built-in `unittest`:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Tests cover every function across all modules using mocked API responses and user input.

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
