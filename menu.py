from rich.console import Console
from rich_pyfiglet import RichFiglet


def print_banner() -> None:
    """Render the application banner in the terminal.

    Returns:
        ``None``. The formatted banner is written directly to the console.
    """
    console = Console()
    banner = RichFiglet(
        "AFG473319",
        "larry3d",
        colors=["#191970", "#8A2BE2", "#FFBF00"]
    )
    console.print(banner)


def show_menu(choices: list[str]) -> None:
    """Display the available choices as a numbered menu.

    Args:
        choices: List of menu items to display.
    """
    for i, choice in enumerate(choices, start=1):
        print(f"{i}. {choice}")


def get_user_choice(choices: list[str]) -> str:
    """Read and return a valid selection from the numbered menu.

    Args:
        choices: The list of available choices.

    Returns:
        The user's choice as a string.
    """
    valid_inputs = [str(i) for i in range(1, len(choices) + 1)]

    while True:
        user_input = input("> ").strip()
        if user_input in valid_inputs:
            index = int(user_input) - 1
            return choices[index]

        print(f"Invalid choice. Please enter a number between 1 and {len(choices)}.")


def prompt_repo_input() -> tuple[str, str]:
    """Read the owner and name of a GitHub repository.

    Returns:
        A tuple containing the owner and repository name.
    """
    owner = input("Enter the repository owner: ").strip()
    repo = input("Enter the repository name: ").strip()
    return (owner, repo)


def prompt_report_format() -> str:
    """Read the user's preferred report format.

    Returns:
        The selected format in lowercase.
    """
    formats = ["Text", "JSON"]
    show_menu(formats)
    return get_user_choice(formats).lower()


def confirm_clear_cache() -> bool:
    """Confirm whether all tracked cache files should be deleted.

    Returns:
        ``True`` when deletion is confirmed; otherwise ``False``.
    """
    while True:
        answer = input("Clear all cached analyses? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


def confirm_exit() -> bool:
    """Confirm whether the application should exit.

    Returns:
        ``True`` when exit is confirmed; otherwise ``False``.
    """
    user_input = input("Do you really want to exit?(y/n): ")
    return user_input.strip().lower() in ("y", "yes")


def prompt_cache_use(owner: str, repo: str, age_str: str) -> bool:
    """Ask whether to reuse a fresh cache instead of fetching new data.

    Args:
        owner: Repository owner.
        repo: Repository name.
        age_str: Human-readable cache age for display.

    Returns:
        ``True`` when the cache should be reused; otherwise ``False``.
    """
    print(f"\nFound cached analysis for {owner}/{repo} from {age_str}.")
    print("The cache is recent (within 24h) and contains a complete analysis.")
    while True:
        answer = input("Use cached data? (y = use cache, n = fetch fresh) [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")
