import json


def generate_text_report(analysis: dict, scores: dict) -> str:
    """Generate a plain text report from analysis and scores.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        Formatted text report as a string.
    """
    report = ""
    report += "RepoLens Analysis Report\n"
    report += "=" * 40 + "\n\n"

    repo = analysis.get("repo", {})
    report += "Repository Info\n"
    report += "  Name: " + str(repo.get("name")) + "\n"
    report += "  Description: " + str(repo.get("description", "No description")) + "\n"
    report += "  Stars: " + str(repo.get("stars")) + "\n"
    report += "  Forks: " + str(repo.get("forks")) + "\n"
    report += "  Language: " + str(repo.get("language")) + "\n\n"

    commits = analysis.get("commits", {})
    report += "Commits\n"
    report += "  Total commits: " + str(commits.get("total_commits")) + "\n"
    report += "  Unique contributors: " + str(commits.get("unique_contributors")) + "\n"
    report += "  Latest commit date: " + str(commits.get("latest_commit_date")) + "\n\n"

    contributors = analysis.get("contributors", {})
    report += "Contributors\n"
    report += "  Total contributors: " + str(contributors.get("total_contributors")) + "\n"
    report += "  Top contributor: " + str(contributors.get("top_contributor")) + "\n"
    report += "  Most contributions: " + str(contributors.get("most_contributions")) + "\n\n"

    languages = analysis.get("languages", {})
    report += "Languages\n"
    report += "  Primary language: " + str(languages.get("primary_language")) + "\n"
    report += "  Language count: " + str(languages.get("language_count")) + "\n\n"

    issues = analysis.get("issues", {})
    report += "Issues\n"
    report += "  Total issues: " + str(issues.get("total_issues")) + "\n"
    report += "  Open issues: " + str(issues.get("open_issues")) + "\n"
    report += "  Closed issues: " + str(issues.get("closed_issues")) + "\n\n"

    report += "Scores\n"
    report += "  Health score: " + str(scores.get("health_score")) + "\n"
    report += "  Activity score: " + str(scores.get("activity_score")) + "\n"
    report += "  Community score: " + str(scores.get("community_score")) + "\n"
    report += "  Maintainability score: " + str(scores.get("maintainability_score")) + "\n"
    report += "  Grade: " + str(scores.get("grade")) + "\n"

    return report


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


def save_report(report: str, filename: str) -> None:
    """
    Save a report to a file.

    Args:
        report: Report content as a string.
        filename: Output file path.
    """
    file_handle = open(filename, "w")
    file_handle.write(report)
    file_handle.close()


def print_summary(scores: dict) -> None:
    """
    Print a brief summary of scores to the console.

    Args:
        scores: Dictionary containing calculated scores.
    """
    print("Summary")
    print("  Health score: " + str(scores.get("health_score")))
    print("  Grade: " + str(scores.get("grade")))
