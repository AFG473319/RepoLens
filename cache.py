import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

CACHE_TTL_SECONDS = 24 * 3600  # 24 hours - fresh enough for active repos, prompt lets user override
CACHE_VERSION = 1

# Anchor to repo root (file's parent) so `python main.py` from root works.
# Allow override for tests / custom locations.
def _default_cache_dir() -> Path:
    env = os.getenv("REPOLENS_CACHE_DIR")
    if env:
        return Path(env)
    # Keep cache in project-local hidden dir so it's gitignored and visible to user.
    return Path(__file__).resolve().parent / ".repolens_cache"

CACHE_DIR = _default_cache_dir()

_REQUIRED_ANALYSIS_KEYS = {"repo", "commits", "contributors", "languages", "issues", "approximate", "truncated_endpoints"}
_REQUIRED_SCORES_KEYS = {"health_score", "activity_score", "community_score", "maintainability_score", "grade"}

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize(name: str) -> str:
    """Make owner/repo safe for filesystem (no ../ or slash)."""
    sanitized = _SANITIZE_RE.sub("_", name.strip())
    # prevent empty or dot-only
    if not sanitized or sanitized.strip("._") == "":
        return "_"
    return sanitized[:100]


def _cache_path(owner: str, repo: str, cache_dir: Path | None = None) -> Path:
    directory = cache_dir if cache_dir is not None else CACHE_DIR
    filename = f"{_sanitize(owner)}_{_sanitize(repo)}.json"
    return directory / filename


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(date_str: str) -> datetime | None:
    """Parse ISO-8601 from cache; returns aware datetime or None."""
    if not isinstance(date_str, str):
        return None
    try:
        # cache stores ISO with timezone
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


def is_cache_valid(data: dict) -> bool:
    """Check cache dict has everything needed to skip a fetch.

    Must contain owner/repo, fetched_at, version, analysis and scores
    with all required keys and correct types. This is the 'surely has
    everything' check from the spec.
    """
    if not isinstance(data, dict):
        return False
    if data.get("version") != CACHE_VERSION:
        return False
    if not isinstance(data.get("owner"), str) or not data.get("owner"):
        return False
    if not isinstance(data.get("repo"), str) or not data.get("repo"):
        return False
    fetched_at = _parse_iso(data.get("fetched_at", "")) if isinstance(data.get("fetched_at"), str) else None
    if fetched_at is None:
        return False
    analysis = data.get("analysis")
    scores = data.get("scores")
    if not isinstance(analysis, dict) or not isinstance(scores, dict):
        return False
    if not _REQUIRED_ANALYSIS_KEYS.issubset(analysis.keys()):
        return False
    if not _REQUIRED_SCORES_KEYS.issubset(scores.keys()):
        return False
    # type sanity for nested dicts
    for key in ("repo", "commits", "contributors", "languages", "issues"):
        if not isinstance(analysis.get(key), dict):
            return False
    # scores must be numeric / grade string
    for k in ("health_score", "activity_score", "community_score", "maintainability_score"):
        if not isinstance(scores.get(k), (int, float)):
            return False
    if not isinstance(scores.get("grade"), str):
        return False
    return True


def is_cache_fresh(data: dict, ttl_seconds: int = CACHE_TTL_SECONDS, now: datetime | None = None) -> bool:
    """True if fetched_at is within ttl_seconds of now."""
    fetched_at = _parse_iso(data.get("fetched_at", "")) if isinstance(data.get("fetched_at"), str) else None
    if fetched_at is None:
        return False
    current = now if now is not None else _now()
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age = (current - fetched_at).total_seconds()
    # future timestamps (clock skew) count as fresh
    if age < 0:
        return True
    return age <= ttl_seconds


def cache_age_string(data: dict, now: datetime | None = None) -> str:
    """Human-readable age like '5 hours ago'."""
    fetched_at = _parse_iso(data.get("fetched_at", "")) if isinstance(data.get("fetched_at"), str) else None
    if fetched_at is None:
        return "unknown age"
    current = now if now is not None else _now()
    delta = current - fetched_at
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days < 7:
        return f"{days} day{'s' if days != 1 else ''} ago"
    # for older, show date
    return f"on {fetched_at.strftime('%Y-%m-%d %H:%M UTC')}"


def load_cache(owner: str, repo: str, cache_dir: Path | None = None) -> dict | None:
    """Load cached entry for owner/repo or None if missing/invalid JSON."""
    path = _cache_path(owner, repo, cache_dir)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # corrupt or unreadable -> treat as miss
        return None
    return data


def save_cache(owner: str, repo: str, analysis: dict, scores: dict, cache_dir: Path | None = None, fetched_at: datetime | None = None) -> Path:
    """Atomically save analysis+scores for owner/repo.

    Returns the path written. Creates cache_dir if needed.
    """
    directory = cache_dir if cache_dir is not None else CACHE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = _cache_path(owner, repo, directory)
    payload = {
        "version": CACHE_VERSION,
        "owner": owner,
        "repo": repo,
        "fetched_at": (fetched_at if fetched_at is not None else _now()).isoformat(),
        "analysis": analysis,
        "scores": scores,
    }
    # atomic: write temp then replace
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        tmp.replace(path)
    except OSError:
        # cleanup tmp on failure
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise
    return path


def clear_cache(owner: str, repo: str, cache_dir: Path | None = None) -> bool:
    """Remove cache file if it exists. Returns True if removed."""
    path = _cache_path(owner, repo, cache_dir)
    try:
        if path.exists():
            path.unlink()
            return True
    except OSError:
        pass
    return False
