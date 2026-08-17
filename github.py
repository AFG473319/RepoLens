import requests

def getRepo(owner: str, repo: str, endpoint: str = "") -> dict:
    """Fetch repository metadata from GitHub API.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        Repository data as a dictionary.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}{endpoint}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data

def getCommits(owner: str, repo: str) -> list[dict]:
    """Fetch commit history for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        List of commit dictionaries.
    """

    data = getRepo(owner, repo, endpoint="/commits")

    # Ensure the returned data is actually a list before returning
    if not isinstance(data, list):
        raise TypeError(f"Expected list response from API, got {type(data).__name__}")

    return data

def getContributors(owner: str, repo: str) -> list[dict]:
    """Fetch contributors for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        List of contributor dictionaries.
    """
    data = getRepo(owner, repo, "/contributors")
    if not isinstance(data, list):
        raise TypeError(f"Expected list response from API, got {type(data).__name__}")

    return data


def getLanguages(owner: str, repo: str) -> dict:
    """Fetch language breakdown for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        Dictionary of languages and their byte counts.
    """
    data = getRepo(owner, repo, "/languages")
    if not isinstance(data, dict):
        raise TypeError(f"Expected list response from API, got {type(data).__name__}")

    return data

def getIssues(owner: str, repo: str) -> list[dict]:
    """Fetch open issues for a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        List of issue dictionaries.
    """
    data = getRepo(owner, repo, "/issues")
    if not isinstance(data, list):
        raise TypeError(f"Expected list response from API, got {type(data).__name__}")

    return data