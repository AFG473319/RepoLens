import math


def calculate_activity_score(commits_data: dict) -> float:
    """Calculate repository activity score based on commit analysis.

    Args:
        commits_data: Analyzed commits dictionary containing
            total_commits and latest_commit_date.

    Returns:
        Activity score between 0.0 and 100.0.
    """
    total_commits = commits_data.get("total_commits", 0)
    score = min(100.0, math.log10(total_commits + 1) * 20)

    if commits_data.get("latest_commit_date"):
        score += 10

    return round(min(score, 100.0), 2)


def calculate_community_score(contributors_data: dict, issues_data: dict) -> float:
    """Calculate community engagement score.

    Args:
        contributors_data: Analyzed contributors dictionary.
        issues_data: Analyzed issues dictionary.

    Returns:
        Community score between 0.0 and 100.0.
    """
    contributors = contributors_data.get("total_contributors", 0)
    issues = issues_data.get("total_issues", 0)
    closed_issues = issues_data.get("closed_issues", 0)

    contributor_score = min(50.0, contributors * 2.5)
    issue_score = 0.0
    if issues > 0:
        issue_score = (closed_issues / issues) * 50.0

    return round(min(contributor_score + issue_score, 100.0), 2)


def calculate_maintainability_score(repo_data: dict) -> float:
    """Calculate maintainability score based on repository metrics.

    Args:
        repo_data: Analyzed repository dictionary.

    Returns:
        Maintainability score between 0.0 and 100.0.
    """
    stars = repo_data.get("stars", 0)
    forks = repo_data.get("forks", 0)
    has_description = repo_data.get("description") is not None
    has_language = repo_data.get("language") is not None

    score = 0.0
    score += min(40.0, math.log10(stars + 1) * 10)
    score += min(30.0, math.log10(forks + 1) * 10)
    if has_description:
        score += 15.0
    if has_language:
        score += 15.0

    return round(min(score, 100.0), 2)


def calculate_health_score(analysis: dict) -> float:
    """Calculate overall repository health score.

    Args:
        analysis: Dictionary containing analyzed metrics.

    Returns:
        Health score between 0.0 and 100.0.
    """
    activity = calculate_activity_score(analysis.get("commits", {}))
    community = calculate_community_score(
        analysis.get("contributors", {}),
        analysis.get("issues", {})
    )
    maintainability = calculate_maintainability_score(analysis.get("repo", {}))

    health = (activity + community + maintainability) / 3
    return round(health, 2)


def grade_score(score: float) -> str:
    """Convert a numeric score to a letter grade.

    Args:
        score: Numeric score between 0.0 and 100.0.

    Returns:
        Letter grade (A, B, C, D, or F).
    """
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
