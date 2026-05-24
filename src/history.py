import json
import os
import re
from datetime import datetime, timedelta
from .config import HISTORY_FILE

_URL_RE = re.compile(r"https?://\S+")


def normalize_url(url: str) -> str:
    """Normalize URLs enough for post dedupe without changing the target."""
    if not url:
        return ""
    url = url.strip().rstrip(").,!?;:'\"")
    return url[:-1] if url.endswith("/") else url


def load_history() -> list[dict]:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_tweet(tweet: str):
    history = load_history()
    urls = [normalize_url(u) for u in _URL_RE.findall(tweet or "")]
    history.append({
        "text": tweet,
        "timestamp": datetime.now().isoformat(),
        "urls": [u for u in urls if u],
    })
    # Keep only the last 500 entries to avoid file bloat
    history = history[-500:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_recent_tweets(hours: int = 24) -> list[str]:
    """Return tweet texts from the last N hours."""
    history = load_history()
    cutoff = datetime.now() - timedelta(hours=hours)
    recent = []
    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts > cutoff:
                recent.append(entry["text"])
        except (KeyError, ValueError):
            continue
    return recent


def get_recent_urls(hours: int = 168) -> set[str]:
    """Return normalized URLs used in tweets from the last N hours."""
    history = load_history()
    cutoff = datetime.now() - timedelta(hours=hours)
    urls = set()
    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts <= cutoff:
                continue
        except (KeyError, ValueError, TypeError):
            continue

        for url in entry.get("urls") or []:
            norm = normalize_url(url)
            if norm:
                urls.add(norm)

        # Backfill older history rows that predate the explicit `urls` field.
        for url in _URL_RE.findall(entry.get("text") or ""):
            norm = normalize_url(url)
            if norm:
                urls.add(norm)
    return urls
