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
    unique_authors: set[str] = set()
    latest_commit_date = None

    for commit in commits:
        author = commit.get("commit", {}).get("author", {}).get("name")
        if author:
            unique_authors.add(author)

        date = commit.get("commit", {}).get("author", {}).get("date")
        if date and (latest_commit_date is None or date > latest_commit_date):
            latest_commit_date = date

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
    top_contributor = max(
        contributors,
        key=lambda c: c.get("contributions", 0)
    )
    return {
        "total_contributors": total_contributors,
        "top_contributor": top_contributor.get("login"),
        "most_contributions": top_contributor.get("contributions", 0)
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
    # Filter out pull requests — the /issues endpoint returns both,
    # but PRs have a "pull_request" key that issues lack.
    real_issues = [i for i in issues if "pull_request" not in i]

    total_issues = len(real_issues)
    open_count = 0
    closed_count = 0
    for issue in real_issues:
        if issue.get("state") == "open":
            open_count += 1
        elif issue.get("state") == "closed":
            closed_count += 1
    return {
        "total_issues": total_issues,
        "open_issues": open_count,
        "closed_issues": closed_count
    }