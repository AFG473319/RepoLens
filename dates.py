from datetime import datetime, timezone


def parse_iso_datetime(value) -> datetime | None:
    """Parse an ISO-8601 timestamp into an aware datetime.

    Accepts a trailing "Z" (as emitted by the GitHub API) and treats
    naive values (e.g. "2024-01-03") as UTC so mixed inputs stay
    comparable. Aware values keep their original offset. Returns None
    when the value is not a string or cannot be parsed.
    """
    if not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
