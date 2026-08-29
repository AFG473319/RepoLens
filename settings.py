import json
import os
from pathlib import Path

import cache


SETTINGS_PATH = Path(__file__).resolve().parent / "settings.json"
DEFAULT_CACHE_DIRECTORY = Path(__file__).resolve().parent / ".repolens_cache"


def _default_settings() -> dict[str, str]:
    """Build the initial application settings from the environment.

    Returns:
        A dictionary containing the GitHub API key from ``GITHUB_API_KEY``
        (or an empty string when it is not set) and the cache directory from
        ``REPOLENS_CACHE_DIR`` (or the project-local default directory when it
        is not set).
    """
    return {
        "github_api_key": os.getenv("GITHUB_API_KEY", "").strip(),
        "cache_directory": os.getenv("REPOLENS_CACHE_DIR", str(DEFAULT_CACHE_DIRECTORY)).strip(),
    }


def load_settings() -> dict[str, str]:
    """Load saved settings and merge them with environment/default values.

    The JSON settings file is optional. If it does not exist, is malformed,
    or cannot be read, this function returns the environment/default settings
    instead. Only recognized string values are accepted from the saved file.

    Returns:
        A dictionary with ``github_api_key`` and ``cache_directory`` values.
    """
    settings = _default_settings()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
            saved = json.load(file)
        if isinstance(saved, dict):
            if isinstance(saved.get("github_api_key"), str):
                settings["github_api_key"] = saved["github_api_key"].strip()
            if isinstance(saved.get("cache_directory"), str) and saved["cache_directory"].strip():
                settings["cache_directory"] = saved["cache_directory"].strip()
    except (OSError, json.JSONDecodeError):
        pass
    return settings


def save_settings(settings: dict[str, str]) -> None:
    """Persist the supported application settings as formatted JSON.

    Args:
        settings: Dictionary containing optional ``github_api_key`` and
            ``cache_directory`` values. Missing values use the empty API key
            or the project-local default cache directory.

    Raises:
        OSError: If the temporary file or final settings file cannot be
            written or replaced.
    """
    if not isinstance(settings, dict):
        raise TypeError("settings must be a dictionary")

    api_key = settings.get("github_api_key", "")
    cache_directory = settings.get("cache_directory", str(DEFAULT_CACHE_DIRECTORY))
    if not isinstance(api_key, str) or not isinstance(cache_directory, str):
        raise TypeError("setting values must be strings")
    cache_directory = cache_directory.strip() or str(DEFAULT_CACHE_DIRECTORY)
    payload = {"github_api_key": api_key.strip(), "cache_directory": cache_directory}
    temporary = SETTINGS_PATH.with_suffix(".tmp")
    try:
        with open(temporary, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
        temporary.replace(SETTINGS_PATH)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def apply_settings(settings: dict[str, str]) -> None:
    """Apply settings to this process and to the active cache configuration.

    Updates the process environment and active cache directory.

    Args:
        settings: Dictionary containing the API key and cache directory.
    """
    if not isinstance(settings, dict):
        raise TypeError("settings must be a dictionary")
    api_key = settings.get("github_api_key", "")
    cache_directory = settings.get("cache_directory", str(DEFAULT_CACHE_DIRECTORY))
    if not isinstance(api_key, str) or not isinstance(cache_directory, str):
        raise TypeError("setting values must be strings")
    os.environ["GITHUB_API_KEY"] = api_key.strip()
    cache_directory = cache_directory.strip() or str(DEFAULT_CACHE_DIRECTORY)
    os.environ["REPOLENS_CACHE_DIR"] = cache_directory
    cache.CACHE_DIR = Path(cache_directory).expanduser()
