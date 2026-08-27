import json

import github


def generate_text_report(analysis: dict, scores: dict) -> str:
    """Generate a plain text report from analysis and scores.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        Formatted text report as a string.
    """
    repo = analysis.get("repo", {})
    commits = analysis.get("commits", {})
    contributors = analysis.get("contributors", {})
    languages = analysis.get("languages", {})
    issues = analysis.get("issues", {})
    if analysis.get("approximate", False):
        limit = github.MAX_PAGES * github.PER_PAGE
        approximate = (
            "\nNote: This report is approximated because one or more GitHub"
            f" endpoints returned more than {limit} results, so counts are"
            " lower bounds.\n"
        )
        truncated_endpoints = ", ".join(analysis.get("truncated_endpoints", []))
        if truncated_endpoints:
            approximate += f"Truncated endpoints: {truncated_endpoints}\n"
    else:
        approximate = ""

    return (
        "RepoLens Analysis Report\n"
        + "=" * 40 + "\n\n"
        + "Repository Info\n"
        + f"  Name: {repo.get('name', 'Unknown')}\n"
        + f"  Description: {repo.get('description', 'No description')}\n"
        + f"  Stars: {repo.get('stars', 0)}\n"
        + f"  Forks: {repo.get('forks', 0)}\n"
        + f"  Language: {repo.get('language', 'Unknown')}\n\n"
        + "Commits\n"
        + f"  Total commits: {commits.get('total_commits', 0)}\n"
        + f"  Unique contributors: {commits.get('unique_contributors', 0)}\n"
        + f"  Latest commit date: {commits.get('latest_commit_date', 'N/A')}\n\n"
        + "Contributors\n"
        + f"  Total contributors: {contributors.get('total_contributors', 0)}\n"
        + f"  Top contributor: {contributors.get('top_contributor', 'N/A')}\n"
        + f"  Most contributions: {contributors.get('most_contributions', 0)}\n\n"
        + "Languages\n"
        + f"  Primary language: {languages.get('primary_language', 'Unknown')}\n"
        + f"  Language count: {languages.get('language_count', 0)}\n\n"
        + "Issues\n"
        + f"  Total issues: {issues.get('total_issues', 0)}\n"
        + f"  Open issues: {issues.get('open_issues', 0)}\n"
        + f"  Closed issues: {issues.get('closed_issues', 0)}\n\n"
        + "Scores\n"
        + f"  Health score: {scores.get('health_score', 0)}\n"
        + f"  Activity score: {scores.get('activity_score', 0)}\n"
        + f"  Community score: {scores.get('community_score', 0)}\n"
        + f"  Maintainability score: {scores.get('maintainability_score', 0)}\n"
        + f"  Grade: {scores.get('grade', 'N/A')}\n"
        + f"{approximate}"
    )


def generate_json_report(analysis: dict, scores: dict) -> str:
    """
    Generate a JSON formatted report.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        JSON string of the report.
    """
    data = {
        "analysis": analysis,
        "scores": scores
    }
    return json.dumps(data, indent=4)


def save_report(report_content: str, filename: str) -> None:
    """
    Save a report to a file.

    Args:
        report_content: Report content as a string.
        filename: Output file path.
    """
    with open(filename, "w", encoding="utf-8") as file_handle:
        file_handle.write(report_content)


def print_summary(scores: dict) -> None:
    """Print a brief summary of scores to the console.

    Args:
        scores: Dictionary containing calculated scores.
    """
    print("Summary")
    print(f"  Health score: {scores.get('health_score')}")
    print(f"  Grade: {scores.get('grade')}")
