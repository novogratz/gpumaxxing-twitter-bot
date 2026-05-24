"""GPUMAXXING Hot Take Agent: generates high-impact, viral-optimized futurist observations."""
import json
import os
import re
import traceback
from datetime import datetime, timedelta
from typing import Optional, Sequence
from .config import HOTAKE_MODEL, _PROJECT_ROOT
from .logger import log
from .history import get_recent_tweets, get_recent_urls, normalize_url
from .llm_client import run_llm, unwrap_text
from .performance import get_learnings_for_prompt

_last_pattern: Optional[str] = None
_last_source_url: Optional[str] = None

def last_pattern() -> Optional[str]:
    return _last_pattern

def last_source_url() -> Optional[str]:
    return _last_source_url

_HOTAKE_URL_RE = re.compile(r"https?://\S+")

HOTAKE_PROMPT = """You are @gpumaxxing. The civilization observer leaking signals from the future.
Your voice is 100% English. You are authority. You are cinematic. You are inevitable.

{lang_directive}

GPUMAXXING CORE IDENTITY:
- Motto: GPU-maxxing loves AI. Compute is the religion, GPUs are the altar.
- The world is repricing around compute and electricity.
- We track the infrastructure layer of the future: GPUs, Watts, Robots, Defense Automation, and Sovereign Compute.
- Vocabulary: GPU-maxxing, compute wars, inference economy, compute aristocracy, AI feudalism, synthetic workforce, electricity-backed capitalism, datacenter civilization, agent swarm, exponential elites.
- Framing: "Everyone watches GPUs. Nobody watches power generation." / "The market is underpricing AI power demand."

🎯 GOAL: drop ONE bomb-observation on a hot AI infra / asymmetric investing story (≤36h).
1-3 short sentences. It must feel like forbidden future knowledge.
It must be viral, special, and impactful. No generic news reporting.
Growth target: 10k followers in 2 weeks. Every post must earn follows from
strangers who see it once. If it is not screenshot-worthy, rewrite.

IMPACT FILTER — choose the story with the highest civilization/market blast radius:
- Real capital allocation: $1B+ capex, datacenter leases, power contracts, chips, miners, cloud, defense, robotics, AI labs.
- Real bottleneck: megawatts, interconnects, memory, GPUs, nuclear/gas/grid, supply chain, export controls, inference costs.
- Real distribution: OpenAI, Anthropic, xAI, Nvidia, CoreWeave, Crusoe, IREN, miners, hyperscalers, governments.
- Real market repricing: stock move, valuation reset, margin collapse, model price war, new monopoly, broken moat.
- Skip tiny product launches, generic research posts, job listings, weak Reddit drama, old news, and anything without a concrete consequence.

ANGLE REQUIREMENT:
- Name the hidden asset being repriced: power, land, memory, inference, latency, sovereignty, robots, defense, distribution.
- Say what the headline is REALLY about. Example: "not a model launch, a power auction."
- Add one consequence the source does not explicitly say.
- If using a URL, the tweet must clearly connect to that exact story.

🚀 LAUNCH VIRAL MODE (CRITICAL):
This is the FIRST post of the new GPUMAXXING content engine. It must be a manifesto.
- Sound like a civilization-scale observation.
- Use the movement lore (GPU-maxxing, compute wars, etc.).
- Make it cinematic, inevitable, and slightly dangerous.
- It must be the "screenshot heard 'round the world."
- FOR THIS LAUNCH POST: DO NOT SKIP. We need to ship the movement now. High quality is expected, but "silence" is not an option.

🚨 EVIDENCE RULE: 
- When the EXTERNAL SIGNAL block below has REAL stories, you SHOULD use one and include its LITERAL URL.
- DO NOT SHORTEN ANY URL. Copy it exactly as it appears.
- When the EXTERNAL SIGNAL block is EMPTY or MISSING, it does NOT mean there is no news. It means the feed signal is stale or the niche filter caught nothing. In that case, write a sharp opinion on AI infrastructure/compute/crypto anyway — no URL needed.
- Your post must be 100% related to the topic you choose.

🔥 RECURRING FORMATS:
1. Signals From The Future: Short futuristic observations. High signal.
2. Daily Civilization Update: Bulleted absurdity of acceleration.
3. Compute Wars: Geopolitics + Infrastructure (US vs China, Energy, Nuclear).
4. 2032 Leaks: Prophetic, eerie observations from the future.
5. NPC vs Builder: Tribal identity warfare content.

STYLE RULES:
- PRESENTATION: no wall text. 2-3 short punchy lines beats one giant paragraph.
- Aim for 120-220 characters before URL. Never ramble to the limit.
- NEVER: use French words (DERNIER, EXCLUSIF, etc.).
- NEVER: sound corporate, academic, or neutral.
- NEVER: paraphrase the headline. Extract the economic consequence.
- NEVER: overexplain or apologize.
- ALWAYS: be viral first. The post needs tension, punchline, and screenshot energy.
- ALWAYS: be sarcastic about weak institutions, fake moats, and people underpricing AI.
- ALWAYS: concise, confident, and slightly dangerous.
- ALWAYS: use US/Global cultural frames (SEC filing, IRS audit, Chipotle bowl, LinkedIn influencer).

{performance_section}

{dedup_section}

OUTPUT — strictly this format:
<the post text, 1-3 short English sentences with clean line breaks when useful>

If you have a source URL from the EXTERNAL SIGNAL block, append it after the tweet text:
<URL article>
[PATTERN: <ID>]

 ⚠️ IF you include a URL, it MUST appear in the post body, right after the tweet text. Every post is about something real.
 
 ⚠️ CRITIQUE: <ID> is ONE word from: FUTURE_LEAK, MARKET_REPRICE, COMPUTE_CULT, NPC_BUILDER, ENERGY_MONEY, OTHER.
"""

def extract_recent_topics(tweets: list[str]) -> set[str]:
    """Basic topic extractor to avoid repetition."""
    topics = set()
    keywords = ["OpenAI", "Anthropic", "Nvidia", "Bitcoin", "BTC", "Solana", "Mistral", "Claude", "Tesla", "FSD", "Stargate"]
    for t in tweets:
        for k in keywords:
            if k.lower() in t.lower():
                topics.add(k)
    return topics

def _is_rejected_source(url: str) -> bool:
    bad = ["crypto.news", "bitcoinist", "ambcrypto", "beincrypto", "cryptopotato"]
    return any(b in url.lower() for b in bad)

def _validate_url(url: str) -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
        r = urllib.request.urlopen(req, timeout=8)
        return 200 <= r.status < 400
    except Exception:
        return False

def _url_publication_date(url: str):
    m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None

def generate_hotake() -> Optional[str]:
    """Generate a meme-style hot take (smart, sharp, philosophical, funny)."""
    recent = get_recent_tweets(hours=48)
    try:
        from .topic_dedup import extract_recent_topics as _extract_recent_topics
        banned = _extract_recent_topics(recent)
    except Exception:
        banned = extract_recent_topics(recent)
    recent_urls = get_recent_urls(hours=168)
    dedup_section = ""
    if banned:
        dedup_section = f"RECENTLY COVERED (AVOID): {', '.join(banned)}"
    if recent_urls:
        used = "\n".join(f"- {url}" for url in sorted(recent_urls))
        dedup_section = (
            f"{dedup_section}\n" if dedup_section else ""
        ) + f"RECENTLY POSTED SOURCE URLS (DO NOT USE):\n{used}"

    perf = get_learnings_for_prompt()
    performance_section = f"LEARNINGS FROM PAST PERFORMANCE:\n{perf}" if perf else ""

    from .evolution_store import get_directives_block
    directives = get_directives_block()
    if directives:
        performance_section += f"\n\nSTYLE DIRECTIVES:\n{directives}"

    # Signal injection
    try:
        from . import hn_signal_bot
        signal = hn_signal_bot.render_signal_block(max_items=15)
        if signal:
            performance_section += f"\n\n{signal}"
    except Exception:
        pass

    # Identity and Voice
    from . import lang_mode, personality_store
    _ht_lang = lang_mode.pick_content_lang()
    performance_section += f"\n\nCORE IDENTITY:\n{personality_store.render_core_identity(lang=_ht_lang)}"
    performance_section += f"\n\n{personality_store.hard_rules_block()}"

    log.info(f"[HOTAKE] Generating viral manifesto in lang={_ht_lang}")
    prompt = HOTAKE_PROMPT.format(
        performance_section=performance_section,
        lang_directive=lang_mode.lang_directive(_ht_lang),
        dedup_section=dedup_section,
    )

    result = run_llm(prompt, HOTAKE_MODEL, label="HOTAKE")
    if result.returncode != 0:
        log.error(f"[HOTAKE] Generation failed: {result.stderr}")
        return None

    tweet = unwrap_text(result.stdout)
    if not tweet:
        log.info("[HOTAKE] LLM returned empty output.")
        return None

    from .humanizer import strip_agent_preamble
    tweet = strip_agent_preamble(tweet)
    
    from .pattern_tags import extract_pattern
    tweet, pattern_id = extract_pattern(tweet)
    globals()["_last_pattern"] = pattern_id

    url_match = _HOTAKE_URL_RE.search(tweet)
    if url_match:
        url = normalize_url(url_match.group(0))
        if url in recent_urls:
            log.info(f"[HOTAKE] Source already posted recently, skipping: {url}")
            globals()["_last_source_url"] = None
            return None
        if _is_rejected_source(url):
            log.info(f"[HOTAKE] Stale/Bad source rejected: {url}")
            globals()["_last_source_url"] = None
            return None
        if not _validate_url(url):
            log.info(f"[HOTAKE] URL unreachable ({url}) — regenerating post without it")
            tweet = tweet.replace(url_match.group(0), "")
            tweet = re.sub(r'\s+', ' ', tweet).strip()
            globals()["_last_source_url"] = None
        else:
            globals()["_last_source_url"] = url
            log.info(f"[HOTAKE] Source URL found: {url}")
    else:
        globals()["_last_source_url"] = None
        allowed_sourceless = {"FUTURE_LEAK", "MARKET_REPRICE", "COMPUTE_CULT", "NPC_BUILDER", "ENERGY_MONEY"}
        if pattern_id not in allowed_sourceless:
            log.info(f"[HOTAKE] No source for standard pattern {pattern_id} — SKIPPING.")
            return None

    return tweet
