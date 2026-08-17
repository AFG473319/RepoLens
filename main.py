import menu
import github
import analyzer
import scoring
import report


def main() -> None:
    """Main entry point for the application."""
    choices = ["Analyze a repository", "Exit"]
    menu.print_banner()
    while True:
        menu.show_menu(["Analyze a repository", "Exit"])
        user_choice = menu.get_user_choice(choices)
        if user_choice == "Exit":
            if menu.confirm_exit():
                return
        if user_choice == "Analyze a repository":
            owner, repo = menu.prompt_repo_input()
            report_format = menu.prompt_report_format()
            analysis = {
            "repo": analyzer.analyze_repo(github.getRepo(owner, repo)),
            "commits": analyzer.analyze_commits(github.getCommits(owner, repo)),
            "contributors": analyzer.analyze_contributors(github.getContributors(owner, repo)),
            "languages": analyzer.analyze_languages(github.getLanguages(owner, repo)),
            "issues": analyzer.analyze_issues(github.getIssues(owner, repo))
            }


if __name__ == "__main__":
    main()
