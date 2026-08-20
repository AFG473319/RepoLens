import requests

def get_repo(owner: str, repo: str, endpoint: str = "", api_key = None) -> dict:
    """Fetch repository metadata from GitHub API.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        Repository data as a dictionary.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}{endpoint}"
    if api_key:
        headers = {"Authorization": f"token {api_key}"}
        response = requests.get(url, headers=headers)
    else:
        response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data

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