import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

CACHE_TTL_SECONDS = 24 * 3600  # 24 hours - fresh enough for active repos, prompt lets user override
CACHE_VERSION = 1
# Cache files are named <owner>_<repo>_repolens_cache.json so that cache
# cleanup can match only files this tool created — the cache directory is
# user-settable and may contain unrelated *.json that must never be deleted.
CACHE_SUFFIX = "_repolens_cache.json"
REGISTRY_PATH = Path(__file__).resolve().parent / "cache_directories.json"

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
    """Sanitize a repository component for safe use in a filename.

    Args:
        name: Owner or repository name to sanitize.

    Returns:
        A filesystem-safe string limited to 100 characters.
    """
    sanitized = _SANITIZE_RE.sub("_", name.strip())
    # prevent empty or dot-only
    if not sanitized or sanitized.strip("._") == "":
        return "_"
    return sanitized[:100]


def _cache_path(owner: str, repo: str, cache_dir: Path | None = None) -> Path:
    """Build the cache-file path for a repository.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        cache_dir: Directory in which to place the cache file. Defaults to
            the configured cache directory.

    Returns:
        The path to the repository's cache file.
    """
    directory = cache_dir if cache_dir is not None else CACHE_DIR
    filename = f"{_sanitize(owner)}_{_sanitize(repo)}{CACHE_SUFFIX}"
    return directory / filename


def _directory_key(directory: Path) -> str:
    """Return the normalized absolute path used to identify a cache directory.

    Args:
        directory: Cache directory to normalize.

    Returns:
        The directory's normalized absolute path as a string.
    """
    return str(directory.expanduser().resolve())


def _load_cache_directories() -> list[Path]:
    """Load unique cache directories from the registry.

    Returns:
        A list of valid, unique cache-directory paths. Missing, malformed,
        or unreadable registries produce an empty list.
    """
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError):
        entries = []
    if not isinstance(entries, list):
        return []
    directories = []
    seen = set()
    for entry in entries:
        if isinstance(entry, str) and entry.strip():
            directory = Path(entry)
            key = _directory_key(directory)
            if key not in seen:
                seen.add(key)
                directories.append(Path(key))
    return directories


def _save_cache_directories(directories: list[Path]) -> None:
    """Persist cache directory paths to the registry atomically.

    Args:
        directories: Cache directories to record.

    Raises:
        OSError: If the registry cannot be written or replaced.
    """
    temporary = REGISTRY_PATH.with_suffix(".tmp")
    try:
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump([_directory_key(directory) for directory in directories], f, indent=2)
        temporary.replace(REGISTRY_PATH)
    except OSError:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass
        raise


def _tracked_cache_directories() -> list[Path]:
    """Return the active cache directory followed by registered directories.

    Returns:
        A deduplicated list of directories searched for cache files.
    """
    directories = [Path(CACHE_DIR)] + _load_cache_directories()
    unique = []
    seen = set()
    for directory in directories:
        key = _directory_key(directory)
        if key not in seen:
            seen.add(key)
            unique.append(Path(key))
    return unique


def _record_cache_directory(directory: Path) -> None:
    """Register a cache directory unless it is already recorded.

    Args:
        directory: Cache directory to add to the registry.

    Raises:
        OSError: If the registry cannot be updated.
    """
    directories = _load_cache_directories()
    if _directory_key(directory) not in {_directory_key(item) for item in directories}:
        _save_cache_directories(directories + [directory])


def _now() -> datetime:
    """Return the current timezone-aware UTC datetime.

    Returns:
        The current UTC time.
    """
    return datetime.now(timezone.utc)


def _parse_iso(date_str: str) -> datetime | None:
    """Parse a cache timestamp into a timezone-aware datetime.

    Args:
        date_str: ISO-8601 timestamp stored in a cache payload.

    Returns:
        The parsed datetime, or ``None`` when the value is invalid.
    """
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


def build_cache_payload(
    owner: str,
    repo: str,
    analysis: dict,
    scores: dict,
    fetched_at: datetime | None = None,
) -> dict:
    """Build the canonical cache payload for an analysis.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        analysis: Analyzed repository data.
        scores: Calculated repository scores.
        fetched_at: Timestamp to store; defaults to the current UTC time.

    Returns:
        A cache payload suitable for validation or persistence.
    """
    timestamp = fetched_at if fetched_at is not None else _now()
    return {
        "version": CACHE_VERSION,
        "owner": owner,
        "repo": repo,
        "fetched_at": timestamp.isoformat(),
        "analysis": analysis,
        "scores": scores,
    }


def is_cache_valid(data: dict) -> bool:
    """Determine whether a cache payload contains all data required for reuse.

    Args:
        data: Cache payload to validate.

    Returns:
        ``True`` when the payload has the expected version, metadata, analysis,
        scores, and value types; otherwise ``False``.
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
    """Determine whether a cache payload falls within the configured TTL.

    Args:
        data: Cache payload containing the ``fetched_at`` timestamp.
        ttl_seconds: Maximum permitted cache age in seconds.
        now: Reference time for the comparison. Defaults to the current UTC
            time.

    Returns:
        ``True`` when the cache is fresh or its timestamp is in the future;
        otherwise ``False``.
    """
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
    """Format a cache payload's age for display in the interactive prompt.

    Args:
        data: Cache payload containing the ``fetched_at`` timestamp.
        now: Reference time for the calculation. Defaults to the current UTC
            time.

    Returns:
        A human-readable age string, or ``"unknown age"`` for an invalid
        timestamp.
    """
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
    """Load a repository cache from the requested or tracked directories.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        cache_dir: Directory to search first. When omitted, the active and
            registered directories are searched.

    Returns:
        The decoded cache payload, or ``None`` when no readable cache exists.
    """
    if cache_dir is not None:
        directories = [cache_dir] + [directory for directory in _load_cache_directories()
                                     if _directory_key(directory) != _directory_key(cache_dir)]
    else:
        directories = _tracked_cache_directories()
    for directory in directories:
        path = _cache_path(owner, repo, directory)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
    return None


def save_cache(owner: str, repo: str, analysis: dict, scores: dict, cache_dir: Path | None = None, fetched_at: datetime | None = None) -> Path:
    """Atomically persist an analysis and its scores for a repository.

    Returns:
        The path of the cache file that was written.
    """
    directory = cache_dir if cache_dir is not None else CACHE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = _cache_path(owner, repo, directory)
    payload = build_cache_payload(owner, repo, analysis, scores, fetched_at)
    # atomic: write temp then replace
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        tmp.replace(path)
        try:
            _record_cache_directory(directory)
        except OSError:
            # Registry persistence must not make a successfully written cache unusable.
            pass
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
    """Remove a repository cache file from the requested or tracked directories.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        cache_dir: Directory to search exclusively. When omitted, all tracked
            directories are searched.

    Returns:
        ``True`` when at least one cache file is removed; otherwise ``False``.
    """
    directories = [cache_dir] if cache_dir is not None else _tracked_cache_directories()
    removed = False
    for directory in directories:
        try:
            path = _cache_path(owner, repo, directory)
            if path.exists():
                path.unlink()
                removed = True
        except OSError:
            continue
    return removed


def clear_all_cache() -> int:
    """Delete tracked cache files and remove the cache-directory registry.

    Returns:
        The number of cache files successfully removed.
    """
    removed = 0
    directories = _tracked_cache_directories()
    for directory in directories:
        try:
            if directory.exists():
                for path in directory.glob(f"*{CACHE_SUFFIX}"):
                    try:
                        path.unlink()
                        removed += 1
                    except OSError:
                        pass
        except OSError:
            pass
    try:
        if REGISTRY_PATH.exists():
            REGISTRY_PATH.unlink()
    except OSError:
        pass
    return removed
