import os
import dotenv
import menu
import github
import analyzer
import scoring
import report


def analyze_repository(owner: str, repo: str) -> tuple:
    """Fetch and analyze a repository.
    
    Args:
        owner: GitHub username or organization.
        repo: Repository name.
    
    Returns:
        A tuple of (analysis_dict, scores_dict)
    """
    api_key = None
    if dotenv.load_dotenv():
        api_key = os.getenv("GITHUB_API_KEY")
    repo_data = github.get_repo(owner, repo, api_key=api_key)
    commits_data = github.get_commits(owner, repo, api_key)
    contributors_data = github.get_contributors(owner, repo, api_key)
    languages_data = github.get_languages(owner, repo, api_key)
    issues_data = github.get_issues(owner, repo, api_key)
    
    analysis = {
        "repo": analyzer.analyze_repo(repo_data),
        "commits": analyzer.analyze_commits(commits_data),
        "contributors": analyzer.analyze_contributors(contributors_data),
        "languages": analyzer.analyze_languages(languages_data),
        "issues": analyzer.analyze_issues(issues_data)
    }
    
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
                report.print_summary(scores)
                
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
                    print(f"Error: I don't Have Access To {filename}")
                except IOError as e:
                    print(f"Error: {e}")
                
            except Exception as e:
                print(f"\nError: {e}")
            
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
