import requests

def getRepo(owner: str, repo: str) -> dict:

    url = f"https://api.github.com/repos/{owner}/{repo}"

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()

    return data