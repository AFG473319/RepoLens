import json


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

    return (
        "RepoLens Analysis Report\n"
        + "=" * 40 + "\n\n"
        + "Repository Info\n"
        + f"  Name: {repo.get('name')}\n"
        + f"  Description: {repo.get('description', 'No description')}\n"
        + f"  Stars: {repo.get('stars')}\n"
        + f"  Forks: {repo.get('forks')}\n"
        + f"  Language: {repo.get('language')}\n\n"
        + "Commits\n"
        + f"  Total commits: {commits.get('total_commits')}\n"
        + f"  Unique contributors: {commits.get('unique_contributors')}\n"
        + f"  Latest commit date: {commits.get('latest_commit_date')}\n\n"
        + "Contributors\n"
        + f"  Total contributors: {contributors.get('total_contributors')}\n"
        + f"  Top contributor: {contributors.get('top_contributor')}\n"
        + f"  Most contributions: {contributors.get('most_contributions')}\n\n"
        + "Languages\n"
        + f"  Primary language: {languages.get('primary_language')}\n"
        + f"  Language count: {languages.get('language_count')}\n\n"
        + "Issues\n"
        + f"  Total issues: {issues.get('total_issues')}\n"
        + f"  Open issues: {issues.get('open_issues')}\n"
        + f"  Closed issues: {issues.get('closed_issues')}\n\n"
        + "Scores\n"
        + f"  Health score: {scores.get('health_score')}\n"
        + f"  Activity score: {scores.get('activity_score')}\n"
        + f"  Community score: {scores.get('community_score')}\n"
        + f"  Maintainability score: {scores.get('maintainability_score')}\n"
        + f"  Grade: {scores.get('grade')}\n"
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
