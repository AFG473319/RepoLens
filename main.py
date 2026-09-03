import os

import requests

import dotenv
import cache
import menu
import analyzer
import scoring
import report
import settings
import provider


def analyze_repository(owner: str, repo: str, platform: str = "github") -> tuple[dict, dict]:
    """Fetch repository data and return its analysis and scores.

    Args:
        owner: Repository owner or namespace.
        repo: Repository name.
        platform: Platform name ('github' or 'gitlab'). Defaults to 'github'.

    Returns:
        A tuple containing the analysis payload and calculated scores.
    """
    dotenv.load_dotenv()
    if platform.lower() == "gitlab":
        api_key = os.getenv("GITLAB_API_KEY")
    else:
        api_key = os.getenv("GITHUB_API_KEY")

    platform_display = "GitLab" if platform.lower() == "gitlab" else "GitHub"
    print(f"Fetching repository metadata for {owner}/{repo}...")
    repo_data = provider.get_repo(owner, repo, api_key=api_key, platform=platform)
    print("Fetching commit history...")
    commits_data, commits_truncated = provider.get_commits(owner, repo, api_key=api_key, platform=platform)
    print("Fetching contributors...")
    contributors_data, contributors_truncated = provider.get_contributors(owner, repo, api_key=api_key, platform=platform)
    print("Fetching language breakdown...")
    languages_data = provider.get_languages(owner, repo, api_key=api_key, platform=platform)
    print("Fetching issues...")
    issues_data, issues_truncated = provider.get_issues(owner, repo, api_key=api_key, platform=platform)

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
        choices = [
            "Analyze a GitHub repository",
            "Analyze a GitLab repository",
            "Settings",
            "Clear cache",
            "Exit",
        ]
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
        
        if user_choice in ("Analyze a repository", "Analyze a GitHub repository", "Analyze a GitLab repository"):
            is_gitlab = (user_choice == "Analyze a GitLab repository")
            platform = "gitlab" if is_gitlab else "github"
            platform_display = "GitLab" if is_gitlab else "GitHub"
            try:
                if is_gitlab:
                    owner, repo = menu.prompt_gitlab_repo_input()
                else:
                    owner, repo = menu.prompt_repo_input()

                # Offer a fresh, complete cache before fetching
                cached_data = cache.load_cache(owner, repo, platform=platform)
                use_cache = False
                if cached_data is not None and cache.is_cache_valid(cached_data) and cache.is_cache_fresh(cached_data):
                    age_str = cache.cache_age_string(cached_data)
                    if menu.prompt_cache_use(owner, repo, age_str):
                        analysis, scores = cached_data["analysis"], cached_data["scores"]
                        print(f"\nUsing cached data for {owner}/{repo} ({age_str}) — skipping {platform_display} fetch.")
                        use_cache = True

                if not use_cache:
                    report_format = menu.prompt_report_format(app_settings["default_report_format"])

                    print(f"\nFetching data from {platform_display}...")
                    if platform == "gitlab":
                        analysis, scores = analyze_repository(owner, repo, platform=platform)
                    else:
                        analysis, scores = analyze_repository(owner, repo)

                    # Cache only complete payloads; incomplete results should not
                    # replace a usable cache entry.
                    cache_payload = cache.build_cache_payload(owner, repo, analysis, scores, platform=platform)
                    if cache.is_cache_valid(cache_payload):
                        try:
                            cache.save_cache(owner, repo, analysis, scores, platform=platform)
                        except OSError as e:
                            # Cache failure is non-fatal; warn and continue
                            print(f"Warning: could not write cache: {e}")

                else:
                    # Still need report format when serving from cache
                    report_format = menu.prompt_report_format(app_settings["default_report_format"])
                
                print("\n")
                report.print_summary(scores, analysis)

                generator, extension = report.REPORT_FORMAT_GENERATORS[report_format]
                report_content = generator(owner, repo, analysis, scores)
                sanitized_owner = cache._sanitize(owner)
                sanitized_repo = cache._sanitize(repo)
                if user_choice == "Analyze a repository":
                    filename = f"{owner}_{repo}_report{extension}"
                else:
                    filename = f"{platform}_{sanitized_owner}_{sanitized_repo}_report{extension}"
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
