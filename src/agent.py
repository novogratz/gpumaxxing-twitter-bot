"""GPUMAXXING Content Agent: follows the recurring psychological programming loops strategy."""
import json
import re
import traceback
from datetime import datetime
from typing import Optional
from .config import NEWS_MODEL
from .logger import log
from .history import get_recent_tweets
from .llm_client import run_llm, unwrap_text
from .hotake_agent import generate_hotake

# Module-level side-channels for the most-recent news output.
_last_pattern: Optional[str] = None
_last_source_url: Optional[str] = None
_last_injected_urls: set[str] = set()
_last_injected_url_titles: dict[str, str] = {}


def last_pattern() -> Optional[str]:
    return _last_pattern


def last_source_url() -> Optional[str]:
    return _last_source_url


def generate_tweet() -> Optional[str]:
    """Main entry point for generating original content.
    Follows the GPUMAXXING DAILY CONTENT ENGINE strategy.
    
    Delegates to hotake_agent for now as it aligns better with the 
    new short-form viral strategy than the old news-heavy 'Le Décode' pipeline.
    """
    log.info("[AGENT] Generating content following the GPUMAXXING engine...")
    tweet = generate_hotake()
    
    if tweet:
        # Sync the module-level side-channels from hotake_agent
        from . import hotake_agent as _ha
        global _last_pattern, _last_source_url
        _last_pattern = _ha.last_pattern()
        _last_source_url = _ha.last_source_url()
        
    return tweet

def url_is_reachable(url: str, timeout: int = 5) -> bool:
    """Check if a URL is reachable (returns True if HTTP 200)."""
    if not url:
        return False
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        r = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False
