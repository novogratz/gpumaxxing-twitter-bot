"""Post bot: publishes AI news tweets and philosophy hot takes."""
import json
import os
import random
import re
import time
import traceback
from datetime import date
from .config import MAX_NEWS_PER_DAY, MAX_HOTAKES_PER_DAY, DAILY_STATE_FILE, get_live_cap
from .logger import log
from .agent import generate_tweet
from .hotake_agent import generate_hotake
from .twitter_client import post_tweet
from .history import save_tweet, get_recent_urls, normalize_url
from .engagement_log import log_post, log_hotake
from .humanizer import humanize


def _live_news_cap() -> int:
    """Live cap from meta_strategy_agent's live_strategy.json, env fallback."""
    return get_live_cap("MAX_NEWS_PER_DAY", MAX_NEWS_PER_DAY)


def _live_hotake_cap() -> int:
    """Live cap from meta_strategy_agent's live_strategy.json, env fallback."""
    return get_live_cap("MAX_HOTAKES_PER_DAY", MAX_HOTAKES_PER_DAY)


THREAD_SEPARATOR = "---THREAD---"
NEWS_POSTS_PER_CYCLE = int(os.environ.get("NEWS_POSTS_PER_CYCLE", "3"))
NEWS_POST_SPACING_SECONDS = int(os.environ.get("NEWS_POST_SPACING_SECONDS", "120"))
ORIGINAL_HASHTAG_PROB = float(os.environ.get("ORIGINAL_HASHTAG_PROB", "0.1"))
_CURATED_HASHTAGS = ("#Crypto", "#AI", "#Bitcoin")
_URL_RE = re.compile(r"https?://\S+")


def _maybe_add_curated_hashtag(text: str) -> str:
    """Add approve hashtags sparingly."""
    if not text or random.random() > ORIGINAL_HASHTAG_PROB:
        return text
    if any(tag.lower() in text.lower() for tag in _CURATED_HASHTAGS):
        return text
    if "#AI" not in text and len(text) + 4 < 280:
        return text + " #AI"
    return text


def _has_recent_source_repeat(text: str, source_url: str | None = None) -> bool:
    """True when a generated post reuses a recently-posted article URL."""
    recent_urls = get_recent_urls(hours=168)
    candidates = {normalize_url(u) for u in _URL_RE.findall(text or "")}
    if source_url:
        candidates.add(normalize_url(source_url))
    candidates.discard("")
    repeated = candidates & recent_urls
    if repeated:
        log.info(f"[POST] Skipping duplicate source already posted recently: {sorted(repeated)[0]}")
        return True
    return False


def _load_daily_state() -> dict:
    """Load persistent daily counters from disk."""
    if os.path.exists(DAILY_STATE_FILE):
        try:
            with open(DAILY_STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"date": None, "news": 0, "hotakes": 0}


def _save_daily_state(state: dict):
    """Persist daily counters to disk."""
    with open(DAILY_STATE_FILE, "w") as f:
        json.dump(state, f)


def _get_counters() -> tuple[int, int]:
    """Get today's counters, resetting if it's a new day."""
    state = _load_daily_state()
    today = date.today().isoformat()
    if state.get("date") != today:
        state = {"date": today, "news": 0, "hotakes": 0}
        _save_daily_state(state)
    return state["news"], state["hotakes"]


def has_post_slot() -> bool:
    """True if any post format can still ship."""
    news_count, hotake_count = _get_counters()
    return news_count < _live_news_cap() or hotake_count < _live_hotake_cap()


def post_slot_status() -> str:
    """Human-readable daily post cap state for logs."""
    news_count, hotake_count = _get_counters()
    return f"{news_count}/{_live_news_cap()} news, {hotake_count}/{_live_hotake_cap()} hot takes"


def _increment_counter(counter_name: str):
    """Increment a daily counter and persist."""
    state = _load_daily_state()
    today = date.today().isoformat()
    if state.get("date") != today:
        state = {"date": today, "news": 0, "hotakes": 0}
    state[counter_name] = state.get(counter_name, 0) + 1
    _save_daily_state(state)


def _get_launch_manifesto() -> str:
    """Return a high-impact manifesto for the new GPUMAXXING engine.
    Used as a fail-safe if the LLM fails on the very first post of the day.
    """
    manifestos = [
        "The market is still pricing AI as a software cycle.\n\nIt’s an infrastructure cycle.\n\nWe are not building apps; we are building a new layer of civilization. Compute is the only sovereign currency.\n\nGPU-maxxing isn’t a strategy. It’s the only way to survive the transition.",
        "Civilization is repricing around compute and electricity faster than institutions can narrate it.\n\nEveryone watches GPUs. Nobody watches the power grid.\n\nThe future belongs to whoever owns the infrastructure of thought.",
        "NPC: debating AI ethics.\n\nBuilder: buying datacenter infrastructure.\n\nThe bottleneck isn't safety. It's megawatts. We are transitioning from electricity-backed capitalism to inference-backed civilization.\n\nChoose your side.",
        "2032 Leak:\n\nThe weirdest part about AGI was how quickly humans stopped making decisions.\n\nWe didn't lose control to a god. We lost it to a global cluster of H100s optimized for efficiency.\n\nCompute wars are the only wars that matter now.",
    ]
    return random.choice(manifestos)


def _run_single_bot_cycle() -> bool:
    """Post a tweet, respecting daily limits."""
    news_count, hotake_count = _get_counters()
    news_cap = _live_news_cap()
    hotake_cap = _live_hotake_cap()
    log.info(f"Today: {news_count}/{news_cap} news, {hotake_count}/{hotake_cap} short-form")

    if news_count >= news_cap and hotake_count >= hotake_cap:
        log.info("Daily limits reached. Skipping.")
        return False

    can_hotake = hotake_count < hotake_cap
    can_news = news_count < news_cap

    # Favor short-form viral content (hotakes)
    if can_hotake and can_news:
        do_hotake = random.random() < 0.75
    else:
        do_hotake = can_hotake

    tweet = None
    if do_hotake:
        log.info("Generating short-form viral tweet...")
        tweet = generate_hotake()
        if tweet:
            tweet = humanize(tweet)
            tweet = _maybe_add_curated_hashtag(tweet)
            
            from .hotake_agent import last_source_url, last_pattern
            src_url = last_source_url()
            pattern = last_pattern() or "LAUNCH_MANIFESTO"
            if _has_recent_source_repeat(tweet, src_url):
                return False
            _increment_counter("hotakes")
            
            # URL stays in body — no self-reply

            log.info(f"[POST] Posting ({len(tweet)} chars): {tweet[:100]}...")
            post_tweet(tweet)
            
            save_tweet(tweet)
            log_hotake(tweet, pattern_id=pattern)
            return True
    else:
        log.info("Generating original content...")
        tweet = generate_tweet()
        if tweet:
            tweet = humanize(tweet)
            
            from .agent import last_source_url, last_pattern
            src_url = last_source_url()
            pattern = last_pattern() or "RECURRING_SERIES"
            if _has_recent_source_repeat(tweet, src_url):
                return False
            _increment_counter("news")

            # URL always stays in body — no self-reply leak pattern

            log.info(f"[POST] Posting ({len(tweet)} chars): {tweet[:100]}...")
            post_tweet(tweet)
            
            save_tweet(tweet)
            log_post(tweet, pattern_id=pattern)
            return True

    # FAIL-SAFE: If it's the first post of the day and LLM failed, ship the manifesto.
    if news_count == 0 and hotake_count == 0:
        log.info("[LAUNCH] LLM failed to generate the first post. Using launch manifesto fail-safe...")
        tweet = _get_launch_manifesto()
        _increment_counter("hotakes")
        log.info(f"[LAUNCH] Posting manifesto ({len(tweet)} chars): {tweet[:100]}...")
        post_tweet(tweet)
        save_tweet(tweet)
        log_hotake(tweet, pattern_id="LAUNCH_FAILSAFE")
        return True

    return False


def run_bot_cycle(posts_per_cycle: int = NEWS_POSTS_PER_CYCLE):
    """Run a burst of posting cycles."""
    shipped_any = False
    for i in range(posts_per_cycle):
        log.info(f"Bot cycle {i + 1}/{posts_per_cycle}...")
        try:
            ok = _run_single_bot_cycle()
            if ok:
                shipped_any = True
                if i < posts_per_cycle - 1:
                    log.info(f"Spacing: sleeping {NEWS_POST_SPACING_SECONDS}s before next post...")
                    time.sleep(NEWS_POST_SPACING_SECONDS)
            else:
                log.info("No more eligible posts this cycle. Breaking.")
                break
        except Exception:
            log.error(f"Cycle {i+1} failed: {traceback.format_exc()}")
            continue

    if shipped_any:
        try:
            from . import health
            health.record_success("post")
        except ImportError:
            pass


def safe_run_bot_cycle():
    """Wrapper that catches errors so the scheduler keeps running."""
    from . import health
    try:
        run_bot_cycle()
        health.record_success("post")
    except Exception:
        log.error(f"Error during bot cycle: {traceback.format_exc()}")
        health.record_failure("post")
