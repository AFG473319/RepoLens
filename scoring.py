from datetime import datetime, timezone

def calculate_health_score(analysis: dict) -> float:
    """Calculate overall repository health score.

    Args:
        analysis: Dictionary containing analyzed metrics.

    Returns:
        Health score between 0.0 and 100.0.
    """
    pass

def calculate_activity_score(commits: dict) -> float:
    """
    Calculate repository activity score based on the latest commit.

    Args:
        commits: Analyzed commit metrics.

    Returns:
        Activity score between 0.0 and 100.0.
    """
    timestamp = commits.get("latest_commit_date")

    # No commits = completely inactive
    if not timestamp:
        return 0.0

    try:
        last_commit_date = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return 0.0

    # Make sure both datetimes are timezone-aware
    if last_commit_date.tzinfo is None:
        last_commit_date = last_commit_date.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    days_since = (now - last_commit_date).total_seconds() / 86400

    if days_since < 0:
        # Future-dated commit; don't penalize it
        last_commit_date_score = 100.0
    elif days_since <= 1:
        last_commit_date_score = 100.0
    elif days_since <= 7:
        last_commit_date_score = 90.0
    elif days_since <= 30:
        last_commit_date_score = 75.0
    elif days_since <= 90:
        last_commit_date_score = 50.0
    elif days_since <= 180:
        last_commit_date_score = 30.0
    elif days_since <= 365:
        last_commit_date_score =  15.0
    else:
        last_commit_date_score = 0.0


    total_commits = commits["total_commits"]
    if total_commits > 1000:
        total_commits_score = 100.0
    elif total_commits > 500:
        total_commits_score = 75.0
    elif total_commits > 100:
        total_commits_score = 40.0
    elif total_commits > 50:
        total_commits_score = 20.0
    elif total_commits > 20:
        total_commits_score = 10.0
    else:
        total_commits_score = 0.0

    total_score = (total_commits_score + last_commit_date_score) / 2

    return total_score


    
    
def calculate_community_score(contributors: dict, issues: dict) -> float:
    """
    Calculate community engagement score.

    Args:
        contributors: List of contributor dictionaries.
        issues: List of issue dictionaries.

    Returns:
        Community score between 0.0 and 100.0.
    """
    contributors_count = contributors["total_contributors"]
    if contributors_count > 100:
        contributors_count_score = 100
    else:
        contributors_count_score = contributors_count / 100

    issues_score = (issues["open_issues"] * 2) + (issues["closed_issues"] * 5)
    if issues_score > 100:
        issues_score = 100
    return ((contributors_count_score + issues_score) / 2)

def calculate_maintainability_score(repo_data: dict) -> float:
    """Calculate maintainability score based on repository metrics.

    Args:
        repo_data: Raw repository data from GitHub API.

    Returns:
        Maintainability score between 0.0 and 100.0.
    """
    pass

def grade_score(score: float) -> str:
    """Convert a numeric score to a letter grade.

    Args:
        score: Numeric score between 0.0 and 100.0.

    Returns:
        Letter grade (A, B, C, D, or F).
    """

    if score >= 90: return "A"                                                                        
    elif score >= 80: return "B"                                                                      
    elif score >= 70: return "C"                                                                      
    elif score >= 60: return "D"                                                            