import math
from datetime import datetime, timezone

RECENCY_BONUS_DAYS = 90
RECENCY_BONUS_POINTS = 10.0


def calculate_activity_score(commits_data: dict) -> float:
    """Calculate repository activity score from commit count and recency.

    Base score is ``min(100, log10(total_commits + 1) * 20)``. A scaled
    recency bonus in ``[0.0, 10.0]`` is added based on ``latest_commit_date``
    (10.0 at 0 days ago, decaying linearly to 0.0 at 90 days ago) and the
    result is capped at 100.0.

    Args:
        commits_data: Analyzed commits dictionary containing
            total_commits and latest_commit_date (ISO-8601 string or None).

    Returns:
        Activity score between 0.0 and 100.0, rounded to 2 decimals.
    """
    total_commits = commits_data.get("total_commits", 0)
    score = min(100.0, math.log10(total_commits + 1) * 20)

    latest_commit_date = commits_data.get("latest_commit_date")
    if latest_commit_date:
        score += _recency_bonus(latest_commit_date)

    return round(min(score, 100.0), 2)


def _parse_commit_date(date_str: str) -> datetime | None:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime.

    Accepts ``Z`` suffix and naive timestamps (assumed UTC). Returns
    ``None`` if the value is not a string or is unparseable.

    Args:
        date_str: ISO-8601 date string to parse.

    Returns:
        Aware datetime in UTC, or None on failure.
    """
    if not isinstance(date_str, str):
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def _days_since(date_str: str, now: datetime | None = None) -> int | None:
    """Return whole days elapsed since ``date_str``.

    Uses integer floor via ``timedelta.days`` (12h ago = 0 days) and
    clamps future dates to 0. Fractional decay is intentionally not used
    to keep bonus stable within a calendar day.

    Args:
        date_str: ISO-8601 timestamp to measure against ``now``.
        now: Reference time (defaults to ``datetime.now(timezone.utc)``).

    Returns:
        Non-negative integer days (future dates clamped to 0), or None
        if ``date_str`` is unparseable.
    """
    dt = _parse_commit_date(date_str)
    if dt is None:
        return None
    current = now if now is not None else datetime.now(timezone.utc)
    days = (current - dt).days
    return max(0, days)


def _recency_bonus(
    date_str: str, now: datetime | None = None, days: int = RECENCY_BONUS_DAYS
) -> float:
    """Calculate scaled recency bonus for a commit date.

    Linear decay from ``RECENCY_BONUS_POINTS`` (10.0) at 0 days ago to
    0.0 at ``days`` (default ``RECENCY_BONUS_DAYS`` = 90). Values beyond
    the window or unparseable dates yield 0.0. Uses integer days from
    ``_days_since`` (floor, future clamped to 0). Rounding is deferred to
    ``calculate_activity_score``.

    Args:
        date_str: ISO-8601 timestamp of the latest commit.
        now: Reference time for calculation (defaults to now, UTC).
        days: Recency window in days.

    Returns:
        Bonus in ``[0.0, 10.0]`` (unrounded; caller rounds final score).
    """
    days_since = _days_since(date_str, now=now)
    if days_since is None:
        return 0.0
    if days_since > days:
        return 0.0
    if days <= 0:
        return 0.0
    # linear decay from RECENCY_BONUS_POINTS to 0 over window
    bonus = RECENCY_BONUS_POINTS * (1 - days_since / days)
    return max(0.0, bonus)


def _committed_within_days(
    date_str: str, days: int = RECENCY_BONUS_DAYS, now: datetime | None = None
) -> bool:
    """Check whether an ISO-8601 timestamp is within the last ``days`` days.

    Inclusive of the boundary (``days_since <= days``). Note that
    ``_recency_bonus`` yields ``0.0`` at exactly ``days`` due to linear
    decay, so a ``True`` here can still mean zero bonus at the edge.

    Args:
        date_str: ISO-8601 date string (e.g. GitHub commit dates).
        days: Recency window in days.
        now: Reference time (defaults to now, UTC).

    Returns:
        True if the timestamp is parseable and at most ``days`` days
        ago (future dates count as 0 days ago); False otherwise.
    """
    days_since = _days_since(date_str, now=now)
    if days_since is None:
        return False
    return days_since <= days


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
    stars = repo_data.get("stars") or 0
    forks = repo_data.get("forks") or 0
    description = repo_data.get("description")
    has_description = bool(description)
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
