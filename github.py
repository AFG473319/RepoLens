import sys
import time
from datetime import datetime, timezone

import requests


PER_PAGE = 100
MAX_PAGES = 10


def _primary_rate_limit_exhausted(response) -> bool:
    """True when the response says the primary rate limit is spent."""
    return response.headers.get("x-ratelimit-remaining") == "0"


def _rate_limited(response) -> bool:
    """True when the response reports a rate limit, not a permission error.

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
    """Build the friendly error for an exhausted or secondary limit."""
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
    """Parse a Retry-After header into seconds to wait.

    GitHub sends Retry-After as a delay in seconds; honor it when
    present, with a one-second floor. When the header is missing,
    empty, or unparseable, fall back to ``default``: GitHub's rate
    limit docs direct waiting at least one minute before retrying a
    secondary limit that carried no Retry-After.
    """
    value = headers.get("Retry-After")
    if not value:
        return default

    try:
        return max(1, int(value))
    except ValueError:
        return default


def _fetch(
    url: str,
    api_key: str | None = None,
    expected_type: type | None = None,
) -> requests.Response:
    """Fetch a GitHub API URL with retry and optional type validation.

    Retries transient failures: connection errors, timeouts, 5xx
    server errors, and secondary rate limits (403/429 without an
    exhausted primary limit), sleeping Retry-After and escalating the
    wait exponentially across retries as GitHub's docs direct. An
    exhausted primary rate limit (x-ratelimit-remaining: 0) raises
    immediately — its reset can be up to an hour away, and continued
    requests risk GitHub banning the client.

    Args:
        url: Full API URL to request.
        api_key: Optional GitHub personal access token.
        expected_type: Optional expected type for the JSON response.

    Returns:
        The raw response object, including pagination headers.

    Raises:
        requests.RequestException: If the request ultimately fails.
        TypeError: If the JSON response has an unexpected type.
    """
    headers = {"Authorization": f"token {api_key}"} if api_key else {}
    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise

        if _rate_limited(response):
            if not _primary_rate_limit_exhausted(response) and attempt < max_retries:
                time.sleep(_retry_after_seconds(response.headers) * (2 ** attempt))
                continue
            raise requests.exceptions.HTTPError(
                _rate_limit_message(response, url, api_key))
        elif response.status_code >= 500:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue

        response.raise_for_status()
        if response.status_code == 204:
            # 204 No Content: success with no body (GitHub answers this
            # for /contributors on an empty repository), so there is no
            # JSON to validate.
            return response
        if expected_type is not None:
            _validate_type(response.json(), expected_type)
        return response


def _validate_type(data, expected_type):
    """Check that data is an instance of expected_type and return it.

    Fails fast with a clear error when the GitHub API returns an
    unexpected shape (e.g., an error object instead of a list).

    Args:
        data: Parsed API response.
        expected_type: Expected type (list, dict, ...).

    Returns:
        data unchanged.

    Raises:
        TypeError: If data is not an instance of expected_type.
    """
    if not isinstance(data, expected_type):
        raise TypeError(
            f"Expected {expected_type.__name__} response from API, got {type(data).__name__}"
        )
    return data


def get_repo(owner: str, repo: str, endpoint: str = "", api_key: str | None = None) -> dict:
    """Fetch repository metadata from GitHub API.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        endpoint: Optional API endpoint suffix (e.g., "/commits").
        api_key: Optional GitHub personal access token.

    Returns:
        Repository data as a dictionary.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}{endpoint}"
    return _fetch(url, api_key=api_key).json()


def _paginate(owner: str, repo: str, endpoint: str, api_key: str | None = None) -> list[dict]:
    """Fetch every page of a paginated list endpoint.

    Requests PER_PAGE items at a time and follows the Link header's
    ``rel="next"`` URL until the last page, up to a cap of MAX_PAGES
    pages.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        endpoint: API endpoint suffix (e.g., "/commits").
        api_key: Optional GitHub personal access token.

    Returns:
        List of all items across pages. If more pages remain than
        MAX_PAGES allows, a warning is printed to stderr and the list
        is truncated, so counts will be approximate.

    Raises:
        TypeError: If the response is not a list.
    """
    separator = "&" if "?" in endpoint else "?"
    url = f"https://api.github.com/repos/{owner}/{repo}{endpoint}{separator}per_page={PER_PAGE}"

    items: list[dict] = []
    page_count = 0
    while url and page_count < MAX_PAGES:
        page_count += 1
        response = _fetch(url, api_key=api_key, expected_type=list)
        if response.status_code == 204:
            # 204 No Content: GitHub's documented empty-repository
            # answer for /contributors; there are no items to paginate.
            return []
        data = response.json()
        items.extend(data)
        url = response.links.get("next", {}).get("url")

    if url:
        print(
            f"Warning: {owner}/{repo}{endpoint} has more than {MAX_PAGES * PER_PAGE} results; "
            "counts may be approximate.",
            file=sys.stderr,
        )
    return items


def get_commits(owner: str, repo: str, api_key: str | None = None) -> list[dict]:
    """Fetch commit history for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        List of commit dictionaries. Empty when the repository has no
        commits (GitHub answers 409 Conflict for /commits on empty
        repos).
    """
    try:
        return _paginate(owner, repo, "/commits", api_key=api_key)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 409:
            return []
        raise


def get_contributors(owner: str, repo: str, api_key: str | None = None) -> list[dict]:
    """Fetch contributors for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        List of contributor dictionaries.
    """
    return _paginate(owner, repo, "/contributors", api_key=api_key)


def get_languages(owner: str, repo: str, api_key: str | None = None) -> dict:
    """Fetch language breakdown for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        Dictionary of languages and their byte counts.

    Raises:
        TypeError: If the response is not a dictionary.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    return _fetch(url, api_key=api_key, expected_type=dict).json()


def get_issues(owner: str, repo: str, api_key: str | None = None) -> list[dict]:
    """Fetch issues for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        List of issue dictionaries.
    """
    return _paginate(owner, repo, "/issues?state=all", api_key=api_key)
