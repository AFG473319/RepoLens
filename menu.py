def print_banner() -> None:
    colors = [
        "\033[91m",
        "\033[93m",
        "\033[92m",
        "\033[96m",
        "\033[94m",
        "\033[95m",
    ]
    reset = "\033[0m"
    banner = [
        " ______     ______     ______   ______     __         ______     __   __     ______    ",
        "/\\\  == \\   /\\\  ___\   /\\\  == \\ /\\\  __ \\   /\\\ \\       /\\\  ___\\   /\\\ \"-.\ \\   /\\\  ___\\   ",
        "\\\ \\  __<   \\\ \\  __\   \\\ \\  _-/ \\\ \\ /\\\ \\  \\\ \\ \\____  \\\ \\  __\   \\\ \\\ \-.  \\  \\\ \\___  \\  ",
        " \\\ \\_\\ \\_\\  \\\ \\_____\\  \\\ \\_\\    \\\ \\_____\\  \\\ \\_____\\  \\\ \\_____\\  \\\ \\_\\\"\_\\  \\\/\_____\\ ",
        "  \\\/_/ /_/   \\\/_____/   \\\/_/     \\\/_____/   \\\/_____/   \\\/_____/   \\\/_/ \\/_/   \\\/_____/ ",
    ]
    for i, line in enumerate(banner):
        color = colors[i % len(colors)]
        print(f"{color}{line}{reset}")


def show_menu(choices: list) -> None:
    for i, choice in enumerate(choices, start=1):
        print(f"{i}. {choice}")

def get_user_choice(choices: list) -> str:
    """Prompt the user for a menu selection.

    Args:
        choices: The list of available choices.

    Returns:
        The user's choice as a string.
    """
    # Create valid string numbers: ['1', '2', ..., 'N']
    valid_inputs = [str(i) for i in range(1, len(choices) + 1)]

    while True:
        user_input = input("> ").strip()
        if user_input in valid_inputs:
            # Convert choice to 0-based index and return the item
            index = int(user_input) - 1
            return choices[index]
        
        print(f"Invalid choice. Please enter a number between 1 and {len(choices)}.")

def prompt_repo_input() -> tuple[str, str]:
    """Prompt the user to enter a repository owner and name.

    Returns:
        A tuple of (owner, repo) strings.
    """
    owner = input("Enter the repository owner: ")
    repo = input("Enter the repository name: ")
    return (owner, repo)

def prompt_report_format() -> str:
    """Prompt the user to select a report format.

    Returns:
        Selected format as a string (e.g. 'text', 'json').
    """
    report_format = input("Enter the report format: ")
    return report_format

def confirm_exit() -> bool:
    """Ask the user to confirm program exit.

    Returns:
        True if the user confirms exit, False otherwise.
    """
    user_input = input("Do you really want to exit?(y/n): ")
    if user_input in ['y', 'yes']:
        return True
    else:
        return False
