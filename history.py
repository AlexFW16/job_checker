import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

HISTORY_FILE = "history.json"
DEFAULT_MAX_AGE_DAYS = 60


def _fingerprint(item: dict) -> str:
    """Stable per-posting key: absolute URL when available, else source+title."""
    url = item.get("url", "")
    if url.startswith("http"):
        parsed = urlparse(url)
        # Paths and queries can contain case-sensitive posting identifiers.
        fingerprint = f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
        if parsed.query:
            fingerprint += f"?{parsed.query}"
        return fingerprint
    title = " ".join(item.get("title", "").lower().split())
    return f"{item.get('source', '')}:{title}"


def load_history(path: str = HISTORY_FILE) -> dict:
    file = Path(path)
    if not file.exists():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("jobs", {}) if isinstance(data, dict) else {}


def save_history(jobs: dict, path: str = HISTORY_FILE, updated: str | None = None) -> None:
    payload = {
        "updated": updated or datetime.now(timezone.utc).isoformat(),
        "jobs": jobs,
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_stale(entry: dict, now: datetime, max_age_days: int) -> bool:
    last_seen = entry.get("last_seen")
    if not last_seen:
        return False
    try:
        seen = datetime.fromisoformat(last_seen)
    except ValueError:
        return False
    return _as_utc(now) - _as_utc(seen) > timedelta(days=max_age_days)


def apply_history(
    results: list[dict],
    history: dict,
    now: datetime | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> tuple[list[dict], dict]:
    """Flag new postings and return an updated history map.

    A posting is ``is_new`` when its fingerprint is absent from the previous
    history. Entries not seen for ``max_age_days`` are purged.
    """
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    updated: dict = {}

    for item in results:
        key = _fingerprint(item)
        previous = history.get(key)
        item["is_new"] = previous is None
        item["first_seen"] = previous["first_seen"] if previous else stamp
        item["last_seen"] = stamp
        updated[key] = {
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "first_seen": item["first_seen"],
            "last_seen": stamp,
        }

    for key, entry in history.items():
        if key not in updated and not _is_stale(entry, now, max_age_days):
            updated[key] = entry

    return results, updated
