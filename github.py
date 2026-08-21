import sys
import time

import requests


PER_PAGE = 100
MAX_PAGES = 10


def _retry_after_seconds(headers, default: int = 1) -> int:
    """Parse a Retry-After header into seconds to wait.

    GitHub sends Retry-After as a delay in seconds. Returns at least
    ``default`` seconds, falling back to ``default`` when the header
    is missing, empty, or unparseable.
    """
    value = headers.get("Retry-After")
    if not value:
        return default

    try:
        return max(default, int(value))
    except ValueError:
        return default


def _fetch(
    url: str,
    api_key: str | None = None,
    expected_type: type | None = None,
) -> requests.Response:
    """Fetch a GitHub API URL with retry and optional type validation.

    Retries transient failures with exponential backoff: connection
    errors, timeouts, HTTP 429 (rate limit), and 5xx server errors.

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

        if response.status_code == 429:
            retry_after = _retry_after_seconds(response.headers)
            if attempt < max_retries:
                time.sleep(retry_after)
                continue
        elif response.status_code >= 500:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue

        response.raise_for_status()
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
        List of commit dictionaries.
    """
    return _paginate(owner, repo, "/commits", api_key=api_key)


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
