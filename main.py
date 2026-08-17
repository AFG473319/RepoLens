import menu
import github
import analyzer
import scoring
import report


def main() -> None:
    """Main entry point for the application."""
    menu.print_banner()
    menu.show_menu(["Analyze a repository", "Exit"])


if __name__ == "__main__":
    main()
