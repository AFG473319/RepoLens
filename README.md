# RepoLens

Analyze GitHub repositories and generate health reports from the command line.

## Features

- Fetches repository data via the GitHub API
- Analyzes commits, contributors, languages, and issues
- Calculates health, activity, community, and maintainability scores
- Generates text or JSON reports
- Saves reports to files

## Installation

```bash
git clone https://github.com/AFG473319/RepoLens.git
cd RepoLens
pip install requests
```

## Usage

```bash
python main.py
```

Follow the prompts to enter a repository owner/name and choose a report format.

## Project Structure

```
RepoLens/
  main.py       - Entry point and CLI loop
  menu.py       - User input and menu display
  github.py     - GitHub API integration
  analyzer.py   - Data analysis functions
  scoring.py    - Score calculation and grading
  report.py     - Report generation and saving
```

## How It Works

1. `main.py` runs the CLI loop and calls `menu.py` for user input
2. `github.py` fetches repository data from the GitHub API
3. `analyzer.py` extracts metrics from the raw API data
4. `scoring.py` calculates numeric scores and letter grades
5. `report.py` formats the results and saves them to a file

## Testing

Run the test suite with Python's built-in unittest:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Tests cover every function across all modules using mocked API responses and user input.
