import time

import requests


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
    headers = {"Authorization": f"token {api_key}"} if api_key else {}

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 1))
        time.sleep(retry_after)
        response = requests.get(url, headers=headers, timeout=10)
    elif response.status_code >= 500:
        retries = 0
        while response.status_code >= 500 and retries < 3:
            time.sleep(2 ** retries)
            retries += 1
            response = requests.get(url, headers=headers, timeout=10)

    response.raise_for_status()
    return response.json()


def _fetch(owner: str, repo: str, endpoint: str, expected_type, api_key: str | None = None):
    """Fetch data from a GitHub API endpoint and validate the response type.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        endpoint: API endpoint suffix (e.g., "/commits").
        expected_type: Expected type of the response (list or dict).
        api_key: Optional GitHub personal access token.

    Returns:
        Validated response data.

    Raises:
        TypeError: If the response is not of the expected type.
    """
    data = get_repo(owner, repo, endpoint, api_key=api_key)
    if not isinstance(data, expected_type):
        raise TypeError(f"Expected {expected_type.__name__} response from API, got {type(data).__name__}")
    return data


def get_commits(owner: str, repo: str, api_key: str | None = None) -> list[dict]:
    """Fetch commit history for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        List of commit dictionaries.
    """
    return _fetch(owner, repo, "/commits", list, api_key)


def get_contributors(owner: str, repo: str, api_key: str | None = None) -> list[dict]:
    """Fetch contributors for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        List of contributor dictionaries.
    """
    return _fetch(owner, repo, "/contributors", list, api_key)


def get_languages(owner: str, repo: str, api_key: str | None = None) -> dict:
    """Fetch language breakdown for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        Dictionary of languages and their byte counts.
    """
    return _fetch(owner, repo, "/languages", dict, api_key)


def get_issues(owner: str, repo: str, api_key: str | None = None) -> list[dict]:
    """Fetch open issues for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        api_key: Optional GitHub personal access token.

    Returns:
        List of issue dictionaries.
    """
    return _fetch(owner, repo, "/issues?state=all", list, api_key)
