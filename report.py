def generate_text_report(analysis: dict, scores: dict) -> str:
    """Generate a plain text report from analysis and scores.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        Formatted text report as a string.
    """
    pass

def generate_json_report(analysis: dict, scores: dict) -> str:
    """Generate a JSON formatted report.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        JSON string of the report.
    """
    pass

def save_report(report: str, filename: str) -> None:
    """Save a report to a file.

    Args:
        report: Report content as a string.
        filename: Output file path.
    """
    pass

def print_summary(scores: dict) -> None:
    """Print a brief summary of scores to the console.

    Args:
        scores: Dictionary containing calculated scores.
    """
    pass
