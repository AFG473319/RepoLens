import menu
import github
import analyzer
import scoring
import report


def main() -> None:
    """Main entry point for the application."""
    choices = ["Analyze a repository", "Exit"]
    menu.print_banner()
    menu.show_menu(["Analyze a repository", "Exit"])
    user_choice = menu.get_user_choice(choices)
    if user_choice == "Exit":
        if menu.confirm_exit():
            return
    if user_choice == "Analyze a repository":
        repository = menu.prompt_repo_input()


if __name__ == "__main__":
    main()
