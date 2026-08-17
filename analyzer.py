import github

def analyze_repo(repo_data: dict) -> dict:
    """Analyze a repository and extract key metrics.

    Args:
        repo_data: Raw repository data from GitHub API.

    Returns:
        Dictionary containing analyzed metrics.
    """
    name = repo_data.get("name")
    description = repo_data.get("description")
    stars = repo_data.get("stargazers_count")
    forks = repo_data.get("forks_count")
    language = repo_data.get("language")

    return {
        'name': name,
        'description': description,
        'stars': stars,
        'forks': forks,
        'language': language
    }


def analyze_commits(commits: list[dict]) -> dict:
    """Analyze commit history for patterns and activity.

    Args:
        commits: List of commit dictionaries.

    Returns:
        Dictionary containing commit analysis results.
    """
    total_commits = len(commits)
    unique_authors = []
    for commit in commits:
        author = commit["commit"]["author"]["name"]
        if author not in unique_authors:
            unique_authors.append(author)
    latest_commit_date = commits[0]["commit"]["author"]["date"] if commits else None
    return {
        "total_commits": total_commits,
        "unique_contributors": len(unique_authors),
        "latest_commit_date": latest_commit_date
    }

def analyze_contributors(contributors: list[dict]) -> dict:
    """Analyze contributor distribution and activity.

    Args:
        contributors: List of contributor dictionaries.

    Returns:
        Dictionary containing contributor analysis results.
    """
    if not contributors:
        return {
            "total_contributors": 0,
            "top_contributor": None,
            "most_contributions": 0
        }
    total_contributors = len(contributors)
    top_contributor = contributors[0]
    most_contributions = top_contributor["contributions"]
    for contributor in contributors:
        contributions = contributor["contributions"]
        if contributions > most_contributions:
            top_contributor = contributor
            most_contributions = contributions
    return {
        "total_contributors": total_contributors,
        "top_contributor": top_contributor["login"],
        "most_contributions": most_contributions
    }

def analyze_languages(languages: dict) -> dict:
    """Analyze language distribution in the repository.

    Args:
        languages: Dictionary of languages and byte counts.

    Returns:
        Dictionary containing language analysis results.
    """
    if not languages:
        return {
            "primary_language": None,
            "language_count": 0
        }
    language_count = len(languages)
    primary_language, primary_count = next(iter(languages.items()))
    for language, count in languages.items():
        if count > primary_count:
            primary_count = count
            primary_language = language
    return {
        "primary_language": primary_language,
        "language_count": language_count
    }
        

def analyze_issues(issues: list[dict]) -> dict:
    """Analyze open issues for trends and health indicators.

    Args:
        issues: List of issue dictionaries.

    Returns:
        Dictionary containing issue analysis results.
    """
    total_issues = len(issues)
    open_count = 0
    closed_count = 0
    for issue in issues:
        if issue.get("state") == "open":
            open_count += 1
        elif issue.get("state") == "closed":
            closed_count += 1
    return {
        "total_issues": total_issues,
        "open_issues": open_count,
        "closed_issues": closed_count
    }