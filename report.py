import json


def generate_text_report(analysis: dict, scores: dict) -> str:
    """Generate a plain text report from analysis and scores.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        Formatted text report as a string.
    """
    report_content = ""
    report_content += "RepoLens Analysis Report\n"
    report_content += "=" * 40 + "\n\n"

    repo = analysis.get("repo", {})
    report_content += "Repository Info\n"
    report_content += "  Name: " + str(repo.get("name")) + "\n"
    report_content += "  Description: " + str(repo.get("description", "No description")) + "\n"
    report_content += "  Stars: " + str(repo.get("stars")) + "\n"
    report_content += "  Forks: " + str(repo.get("forks")) + "\n"
    report_content += "  Language: " + str(repo.get("language")) + "\n\n"

    commits = analysis.get("commits", {})
    report_content += "Commits\n"
    report_content += "  Total commits: " + str(commits.get("total_commits")) + "\n"
    report_content += "  Unique contributors: " + str(commits.get("unique_contributors")) + "\n"
    report_content += "  Latest commit date: " + str(commits.get("latest_commit_date")) + "\n\n"

    contributors = analysis.get("contributors", {})
    report_content += "Contributors\n"
    report_content += "  Total contributors: " + str(contributors.get("total_contributors")) + "\n"
    report_content += "  Top contributor: " + str(contributors.get("top_contributor")) + "\n"
    report_content += "  Most contributions: " + str(contributors.get("most_contributions")) + "\n\n"

    languages = analysis.get("languages", {})
    report_content += "Languages\n"
    report_content += "  Primary language: " + str(languages.get("primary_language")) + "\n"
    report_content += "  Language count: " + str(languages.get("language_count")) + "\n\n"

    issues = analysis.get("issues", {})
    report_content += "Issues\n"
    report_content += "  Total issues: " + str(issues.get("total_issues")) + "\n"
    report_content += "  Open issues: " + str(issues.get("open_issues")) + "\n"
    report_content += "  Closed issues: " + str(issues.get("closed_issues")) + "\n\n"

    report_content += "Scores\n"
    report_content += "  Health score: " + str(scores.get("health_score")) + "\n"
    report_content += "  Activity score: " + str(scores.get("activity_score")) + "\n"
    report_content += "  Community score: " + str(scores.get("community_score")) + "\n"
    report_content += "  Maintainability score: " + str(scores.get("maintainability_score")) + "\n"
    report_content += "  Grade: " + str(scores.get("grade")) + "\n"

    return report_content


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
    """
    Print a brief summary of scores to the console.

    Args:
        scores: Dictionary containing calculated scores.
    """
    print("Summary")
    print("  Health score: " + str(scores.get("health_score")))
    print("  Grade: " + str(scores.get("grade")))
