import time

import requests


def get_repo(owner: str, repo: str, endpoint: str = "", api_key=None) -> dict:
    """Fetch repository metadata from GitHub API.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

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

def get_commits(owner: str, repo: str, api_key = None) -> list[dict]:
    """Fetch commit history for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        List of commit dictionaries.
    """

    data = get_repo(owner, repo, "/commits", api_key)

    # Ensure the returned data is actually a list before returning
    if not isinstance(data, list):
        raise TypeError(f"Expected list response from API, got {type(data).__name__}")

    return data

def get_contributors(owner: str, repo: str, api_key = None) -> list[dict]:
    """Fetch contributors for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        List of contributor dictionaries.
    """
    data = get_repo(owner, repo, "/contributors", api_key)
    if not isinstance(data, list):
        raise TypeError(f"Expected list response from API, got {type(data).__name__}")

    return data


def get_languages(owner: str, repo: str, api_key=None) -> dict:
    """Fetch language breakdown for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        Dictionary of languages and their byte counts.
    """
    data = get_repo(owner, repo, "/languages", api_key)
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict response from API, got {type(data).__name__}")

    return data

def get_issues(owner: str, repo: str, api_key=None) -> list[dict]:
    """Fetch open issues for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        List of issue dictionaries.
    """
    data = get_repo(owner, repo, "/issues", api_key)
    if not isinstance(data, list):
        raise TypeError(f"Expected list response from API, got {type(data).__name__}")

    return data