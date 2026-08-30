import os

import requests

import dotenv
import cache
import menu
import github
import analyzer
import scoring
import report
import settings


def analyze_repository(owner: str, repo: str) -> tuple[dict, dict]:
    """Fetch repository data and return its analysis and scores.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

    Returns:
        A tuple containing the analysis payload and calculated scores.
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

    # Only list endpoints are paginated; repository metadata and languages
    # are returned as single payloads.
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
    """Run the interactive RepoLens command-line application.

    The menu remains active until the user confirms that the application
    should exit.
    """
    dotenv.load_dotenv()
    app_settings = settings.load_settings()
    settings.apply_settings(app_settings)

    while True:
        menu.print_banner()
        choices = ["Analyze a repository", "Settings", "Clear cache", "Exit"]
        menu.show_menu(choices)
        user_choice = menu.get_user_choice(choices)
        
        if user_choice == "Settings":
            try:
                updated_settings = menu.prompt_settings(app_settings)
                settings.save_settings(updated_settings)
                settings.apply_settings(updated_settings)
                app_settings = updated_settings
                print("Settings saved.")
            except OSError as e:
                print(f"Error: could not save settings: {e}")
            continue

        if user_choice == "Clear cache":
            if menu.confirm_clear_cache():
                try:
                    removed = cache.clear_all_cache()
                    print(f"Cleared {removed} cache file{'s' if removed != 1 else ''}.")
                except OSError as e:
                    print(f"Error: could not clear cache: {e}")
            else:
                print("Cache clear cancelled.")
            continue

        if user_choice == "Exit":
            if menu.confirm_exit():
                print("Goodbye!")
                return
            continue
        
        if user_choice == "Analyze a repository":
            try:
                owner, repo = menu.prompt_repo_input()

                # Offer a fresh, complete cache before fetching from GitHub.
                cached_data = cache.load_cache(owner, repo)
                use_cache = False
                if cached_data is not None and cache.is_cache_valid(cached_data) and cache.is_cache_fresh(cached_data):
                    age_str = cache.cache_age_string(cached_data)
                    if menu.prompt_cache_use(owner, repo, age_str):
                        analysis, scores = cached_data["analysis"], cached_data["scores"]
                        print(f"\nUsing cached data for {owner}/{repo} ({age_str}) — skipping GitHub fetch.")
                        use_cache = True

                if not use_cache:
                    report_format = menu.prompt_report_format()

                    print("\nFetching data from GitHub...")
                    analysis, scores = analyze_repository(owner, repo)

                    # Cache only complete payloads; incomplete results should not
                    # replace a usable cache entry.
                    _probe = {
                        "version": cache.CACHE_VERSION,
                        "owner": owner,
                        "repo": repo,
                        "fetched_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                        "analysis": analysis,
                        "scores": scores,
                    }
                    if cache.is_cache_valid(_probe):
                        try:
                            cache.save_cache(owner, repo, analysis, scores)
                        except OSError as e:
                            # Cache failure is non-fatal; warn and continue
                            print(f"Warning: could not write cache: {e}")

                else:
                    # Still need report format when serving from cache
                    report_format = menu.prompt_report_format()
                
                print("\n")
                report.print_summary(scores, analysis)
                
                if report_format.lower() == "json":
                    report_content = report.generate_json_report(analysis, scores)
                    filename = f"{owner}_{repo}_report.json"
                elif report_format.lower() == "html":
                    report_content = report.generate_html_report(analysis, scores)
                    filename = f"{owner}_{repo}_report.html"
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
