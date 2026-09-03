import sys
import time
import urllib.parse
from datetime import datetime, timezone

import requests

PER_PAGE = 100
MAX_PAGES = 10

GITHUB_API_BASE = "https://api.github.com"
GITLAB_API_BASE = "https://gitlab.com/api/v4"


# ==============================================================================
# GitHub Helpers & Error Handling
# ==============================================================================

def _primary_rate_limit_exhausted(response) -> bool:
    """True when the response says the GitHub primary rate limit is spent."""
    return response.headers.get("x-ratelimit-remaining") == "0"


def _rate_limited(response) -> bool:
    """True when the response reports a GitHub rate limit, not a permission error.

    429 is always a rate limit. A 403 counts only when it carries
    rate-limit headers (Retry-After for a secondary limit, or
    x-ratelimit-remaining: 0 for an exhausted primary limit); a plain
    403 is a permission problem and is raised as-is.
    """
    if response.status_code == 429:
        return True
    return response.status_code == 403 and (
        bool(response.headers.get("Retry-After"))
        or _primary_rate_limit_exhausted(response)
    )


def _reset_time(headers) -> str | None:
    """Decode x-ratelimit-reset (epoch seconds) into a UTC clock time."""
    value = headers.get("x-ratelimit-reset")
    if not value:
        return None
    try:
        return datetime.fromtimestamp(
            int(value), tz=timezone.utc).strftime("%H:%M UTC")
    except ValueError:
        return None


def _rate_limit_message(response, url: str, api_key: str | None) -> str:
    """Build the friendly error for an exhausted or secondary GitHub limit."""
    if _primary_rate_limit_exhausted(response):
        message = f"GitHub API rate limit exceeded for {url}."
        reset = _reset_time(response.headers)
        if reset:
            message += f" The limit resets at {reset}."
        if api_key:
            message += " Wait for the reset and try again."
        else:
            message += " Wait for the reset, or set an API key to raise the limit."
        return message
    if api_key:
        return (
            f"GitHub API rate limit exceeded for {url}. "
            "Your API key is rate limited — wait and try again later."
        )
    return (
        f"GitHub API rate limit exceeded for {url}. "
        "Wait and try again, or set an API key to raise the limit."
    )


def _retry_after_seconds(headers, default: int = 60) -> int:
    """Parse a Retry-After header into seconds to wait."""
    value = headers.get("Retry-After")
    if not value:
        return default

    try:
        seconds = int(value)
    except ValueError:
        return default
    if seconds > 100:
        return default
    return max(1, seconds)


def _validate_type(data, expected_type):
    """Check that data is an instance of expected_type and return it.

    Fails fast with a clear error when the API returns an unexpected shape.
    """
    if not isinstance(data, expected_type):
        raise TypeError(
            f"Expected {expected_type.__name__} response from API, got {type(data).__name__}"
        )
    return data


def _fetch(
    url: str,
    api_key: str | None = None,
    expected_type: type | None = None,
) -> requests.Response:
    """Fetch a GitHub API URL with retry and optional type validation."""
    headers = {"Authorization": f"token {api_key}"} if api_key else {}
    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(
                    f"Request failed ({type(e).__name__}); retrying in {wait}s "
                    f"(attempt {attempt + 1} of {max_retries})...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            raise

        if _rate_limited(response):
            if not _primary_rate_limit_exhausted(response) and attempt < max_retries:
                wait = _retry_after_seconds(response.headers) * (2 ** attempt)
                print(
                    f"Rate limited by GitHub on {url}; waiting {wait}s before "
                    f"retrying (attempt {attempt + 1} of {max_retries})...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            raise requests.exceptions.HTTPError(
                _rate_limit_message(response, url, api_key))
        elif response.status_code >= 500:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(
                    f"GitHub server error {response.status_code} on {url}; "
                    f"retrying in {wait}s (attempt {attempt + 1} of {max_retries})...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue

        response.raise_for_status()
        if response.status_code == 204:
            return response
        if expected_type is not None:
            _validate_type(response.json(), expected_type)
        return response


def _paginate(owner: str, repo: str, endpoint: str, api_key: str | None = None) -> tuple[list[dict], bool]:
    """Fetch every page of a paginated GitHub list endpoint."""
    separator = "&" if "?" in endpoint else "?"
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}{endpoint}{separator}per_page={PER_PAGE}"

    items: list[dict] = []
    page_count = 0
    while url and page_count < MAX_PAGES:
        page_count += 1
        response = _fetch(url, api_key=api_key, expected_type=list)
        if response.status_code == 204:
            return [], False
        data = response.json()
        items.extend(data)
        url = response.links.get("next", {}).get("url")

    truncated = bool(url)
    if truncated:
        print(
            f"Warning: {owner}/{repo}{endpoint} has more than {MAX_PAGES * PER_PAGE} results; "
            "counts may be approximate.",
            file=sys.stderr,
        )
    return items, truncated


# ==============================================================================
# GitLab Helpers & Error Handling
# ==============================================================================

def _gitlab_project_path(owner: str, repo: str) -> str:
    """Return the URL-encoded path for a GitLab project."""
    owner_clean = owner.strip("/")
    repo_clean = repo.strip("/")
    raw_path = f"{owner_clean}/{repo_clean}"
    return urllib.parse.quote(raw_path, safe="")


def _gitlab_reset_time(headers) -> str | None:
    """Decode RateLimit-Reset (epoch seconds) into a UTC clock time."""
    value = headers.get("RateLimit-Reset")
    if not value:
        return None
    try:
        return datetime.fromtimestamp(
            int(value), tz=timezone.utc).strftime("%H:%M UTC")
    except (ValueError, TypeError):
        return None


def _gitlab_retry_after_seconds(headers, default: int = 60) -> int:
    """Parse Retry-After header for GitLab with cap and floor."""
    value = headers.get("Retry-After")
    if not value:
        return default
    try:
        seconds = int(value)
    except (ValueError, TypeError):
        return default
    if seconds > 100:
        return default
    return max(1, seconds)


def _gitlab_rate_limit_message(response, url: str, api_key: str | None) -> str:
    """Build the friendly error for a rate-limited GitLab request."""
    message = f"GitLab API rate limit exceeded for {url}."
    reset = _gitlab_reset_time(response.headers)
    if reset:
        message += f" The limit resets at {reset}."
    if api_key:
        message += " Your API key is rate limited — wait and try again later."
    else:
        message += " Wait for the reset, or set a GitLab API key to raise the limit."
    return message


def _fetch_gitlab(
    url: str,
    api_key: str | None = None,
    expected_type: type | None = None,
) -> requests.Response:
    """Fetch a GitLab API URL with retry, rate limit, and type validation."""
    headers = {"PRIVATE-TOKEN": api_key} if api_key else {}
    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(
                    f"Request failed ({type(e).__name__}); retrying in {wait}s "
                    f"(attempt {attempt + 1} of {max_retries})...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            raise

        if response.status_code == 429:
            if attempt < max_retries:
                wait = _gitlab_retry_after_seconds(response.headers, default=10) * (2 ** attempt)
                print(
                    f"Rate limited by GitLab on {url}; waiting {wait}s before "
                    f"retrying (attempt {attempt + 1} of {max_retries})...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            raise requests.exceptions.HTTPError(
                _gitlab_rate_limit_message(response, url, api_key)
            )
        elif response.status_code >= 500:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(
                    f"GitLab server error {response.status_code} on {url}; "
                    f"retrying in {wait}s (attempt {attempt + 1} of {max_retries})...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue

        response.raise_for_status()
        if expected_type is not None:
            _validate_type(response.json(), expected_type)
        return response


def _paginate_gitlab(
    project_encoded: str,
    endpoint: str,
    api_key: str | None = None,
) -> tuple[list[dict], bool]:
    """Fetch every page of a paginated GitLab list endpoint."""
    separator = "&" if "?" in endpoint else "?"
    url = f"{GITLAB_API_BASE}/projects/{project_encoded}{endpoint}{separator}per_page={PER_PAGE}"

    items: list[dict] = []
    page_count = 0
    while url and page_count < MAX_PAGES:
        page_count += 1
        response = _fetch_gitlab(url, api_key=api_key, expected_type=list)
        data = response.json()
        items.extend(data)
        url = response.links.get("next", {}).get("url")

    truncated = bool(url)
    if truncated:
        print(
            f"Warning: {project_encoded}{endpoint} has more than {MAX_PAGES * PER_PAGE} results; "
            "counts may be approximate.",
            file=sys.stderr,
        )
    return items, truncated


# ==============================================================================
# Public Dispatcher & Normalization API
# ==============================================================================

def get_repo(
    owner: str,
    repo: str,
    endpoint: str = "",
    api_key: str | None = None,
    platform: str = "github",
) -> dict:
    """Fetch repository metadata from GitHub or GitLab API.

    Normalizes output to include keys expected by analyzer:
    'name', 'description', 'stargazers_count', 'forks_count', 'language'.
    """
    if platform.lower() == "gitlab":
        project_encoded = _gitlab_project_path(owner, repo)
        url = f"{GITLAB_API_BASE}/projects/{project_encoded}{endpoint}"
        raw = _fetch_gitlab(url, api_key=api_key, expected_type=dict).json()

        # Primary language isn't present in GitLab project metadata;
        # fetch languages to identify the primary language for maintainability score.
        language = None
        try:
            languages = get_languages(owner, repo, api_key=api_key, platform="gitlab")
            if languages and isinstance(languages, dict):
                language = max(languages, key=languages.get)
        except Exception:
            language = None

        return {
            "name": raw.get("name"),
            "description": raw.get("description"),
            "stargazers_count": raw.get("star_count", 0),
            "stars": raw.get("star_count", 0),
            "forks_count": raw.get("forks_count", 0),
            "language": language,
        }

    # GitHub
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}{endpoint}"
    return _fetch(url, api_key=api_key).json()


def get_commits(
    owner: str,
    repo: str,
    api_key: str | None = None,
    platform: str = "github",
) -> tuple[list[dict], bool]:
    """Fetch commit history for a repository."""
    if platform.lower() == "gitlab":
        project_encoded = _gitlab_project_path(owner, repo)
        try:
            commits, truncated = _paginate_gitlab(
                project_encoded, "/repository/commits", api_key=api_key
            )
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (404, 409):
                return [], False
            raise

        # Normalize GitLab commits to GitHub nested structure:
        # { "commit": { "author": { "name": ..., "date": ... } } }
        normalized = []
        for c in commits:
            author_name = c.get("author_name") or c.get("committer_name")
            commit_date = c.get("committed_date") or c.get("authored_date")
            normalized.append({
                "commit": {
                    "author": {
                        "name": author_name,
                        "date": commit_date,
                    }
                }
            })
        return normalized, truncated

    # GitHub
    try:
        return _paginate(owner, repo, "/commits", api_key=api_key)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            return [], False
        raise


def get_contributors(
    owner: str,
    repo: str,
    api_key: str | None = None,
    platform: str = "github",
) -> tuple[list[dict], bool]:
    """Fetch contributors for a repository."""
    if platform.lower() == "gitlab":
        project_encoded = _gitlab_project_path(owner, repo)
        try:
            contributors, truncated = _paginate_gitlab(
                project_encoded, "/repository/contributors", api_key=api_key
            )
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (404, 409):
                return [], False
            raise

        # Normalize GitLab contributors:
        # { "login": name, "contributions": commits }
        normalized = [
            {
                "login": c.get("name"),
                "contributions": c.get("commits", 0),
            }
            for c in contributors
        ]
        return normalized, truncated

    # GitHub
    return _paginate(owner, repo, "/contributors", api_key=api_key)


def get_languages(
    owner: str,
    repo: str,
    api_key: str | None = None,
    platform: str = "github",
) -> dict:
    """Fetch language breakdown for a repository."""
    if platform.lower() == "gitlab":
        project_encoded = _gitlab_project_path(owner, repo)
        url = f"{GITLAB_API_BASE}/projects/{project_encoded}/languages"
        try:
            return _fetch_gitlab(url, api_key=api_key, expected_type=dict).json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (404, 409):
                return {}
            raise

    # GitHub
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/languages"
    return _fetch(url, api_key=api_key, expected_type=dict).json()


def get_issues(
    owner: str,
    repo: str,
    api_key: str | None = None,
    platform: str = "github",
) -> tuple[list[dict], bool]:
    """Fetch issues for a repository."""
    if platform.lower() == "gitlab":
        project_encoded = _gitlab_project_path(owner, repo)
        try:
            issues, truncated = _paginate_gitlab(
                project_encoded, "/issues?scope=all", api_key=api_key
            )
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (404, 409):
                return [], False
            raise

        # Normalize GitLab issues:
        # State: "opened" -> "open"
        normalized = []
        for issue in issues:
            item = dict(issue)
            if item.get("state") == "opened":
                item["state"] = "open"
            normalized.append(item)
        return normalized, truncated

    # GitHub
    return _paginate(owner, repo, "/issues?state=all", api_key=api_key)
