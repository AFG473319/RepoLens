import os

import requests

import dotenv
import menu
import github
import analyzer
import scoring
import report


def analyze_repository(owner: str, repo: str) -> tuple[dict, dict]:
    """Fetch and analyze a repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        A tuple of (analysis_dict, scores_dict)
    """
    dotenv.load_dotenv()
    api_key = os.getenv("GITHUB_API_KEY")
    
    print(f"Fetching repository metadata for {owner}/{repo}...")
    repo_data = github.get_repo(owner, repo, api_key=api_key)
    print("Fetching commit history...")
    commits_data, commits_truncated = github.get_commits(owner, repo, api_key)
    print("Fetching contributors...")
    contributors_data, contributors_truncated = github.get_contributors(owner, repo, api_key)
    print("Fetching language breakdown...")
    languages_data = github.get_languages(owner, repo, api_key)
    print("Fetching issues...")
    issues_data, issues_truncated = github.get_issues(owner, repo, api_key)

    analysis = {
        "repo": analyzer.analyze_repo(repo_data),
        "commits": analyzer.analyze_commits(commits_data),
        "contributors": analyzer.analyze_contributors(contributors_data),
        "languages": analyzer.analyze_languages(languages_data),
        "issues": analyzer.analyze_issues(issues_data)
    }

    # Only list-based endpoints are paginated (and thus can be
    # truncated); languages and repo metadata return a single payload.
    truncated_endpoints = [
        name
        for name, truncated in (
            ("commits", commits_truncated),
            ("contributors", contributors_truncated),
            ("issues", issues_truncated),
        )
        if truncated
    ]
    analysis["approximate"] = bool(truncated_endpoints)
    analysis["truncated_endpoints"] = truncated_endpoints

    health_score = scoring.calculate_health_score(analysis)
    
    scores = {
        "health_score": health_score,
        "activity_score": scoring.calculate_activity_score(analysis.get("commits", {})),
        "community_score": scoring.calculate_community_score(
            analysis.get("contributors", {}),
            analysis.get("issues", {})
        ),
        "maintainability_score": scoring.calculate_maintainability_score(
            analysis.get("repo", {})
        ),
        "grade": scoring.grade_score(health_score)
    }
    
    return analysis, scores


def main() -> None:
    """Main entry point for the application."""
    while True:
        menu.print_banner()
        choices = ["Analyze a repository", "Exit"]
        menu.show_menu(choices)
        user_choice = menu.get_user_choice(choices)
        
        if user_choice == "Exit":
            if menu.confirm_exit():
                print("Goodbye!")
                return
            continue
        
        if user_choice == "Analyze a repository":
            try:
                owner, repo = menu.prompt_repo_input()
                report_format = menu.prompt_report_format()
                
                print("\nFetching data from GitHub...")
                analysis, scores = analyze_repository(owner, repo)
                
                print("\n")
                report.print_summary(scores, analysis)
                
                if report_format.lower() == "json":
                    report_content = report.generate_json_report(analysis, scores)
                    filename = f"{owner}_{repo}_report.json"
                else:
                    report_content = report.generate_text_report(analysis, scores)
                    filename = f"{owner}_{repo}_report.txt"
                try:
                    report.save_report(report_content, filename)
                    print(f"\nReport saved to {filename}")
                except PermissionError as e:
                    print(f"Error: cannot write {filename}: {e}")
                except IOError as e:
                    print(f"Error: {e}")

            except (requests.RequestException, TypeError) as e:
                print(f"\nError: {e}")
            
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
